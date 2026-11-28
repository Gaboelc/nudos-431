"""Atar con el motor (T17): el modo 3 del plan. La cuerda sigue una guía cuadro a cuadro.

La guía (`nudos/animar.py`) dice, en cada cuadro, dónde va cada nodo, cuáles lleva una mano y
cuántos nodos tiene la cuerda: la mano da cuerda o la recoge en el chicote. El motor la sigue
con Euler implícito (`Sistema.paso` con `dt`), con las manos como nodos que se mueven solos y
el resto tirado hacia la guía por resortes suaves, con su peso, la mesa, el anfitrión, el roce
y la memoria de la forma de la guía. Como cada subpaso se recorta con la CCD, la cuerda nunca
se atraviesa; lo que decide de qué lado queda cada cruce es la guía.

- `seguir` da los cuadros de un paso a otro.
- `encajar` asienta el último cuadro en la pose de la ficha y comprueba que llegó.
- `comprobar` revisa los cuadros guardados: en cada uno, nada a menos de dmin, y entre uno y el
  siguiente, el movimiento en línea recta libre según la CCD, que es lo que dibuja Blender.

Unidades: diámetros y newtons, como el resto del motor.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import math

import numpy as np

from .asentar import contacto, material_de
from .contacto import rigidez_barrera
from .integrador import Sistema
from .varilla import Varilla

FPS = 60              # los cuadros por segundo del video (T18)
SUBPASOS = 2          # dt = 1/120 s
RESORTE_MANO = 200.0  # N/d: la mano que lleva la punta
RESORTE = 5.0         # N/d por nodo: lo que tira la guía de cada nodo
# Entre dos estados guardados, la comprobación pide que ningún par pase a menos de esta parte de
# dmin. Los dos estados quedan a más de dmin, pero cuando la cuerda está apretada contra otra
# (a 0,001 de dmin) la recta entre dos de ellos puede bajar unas milésimas; cruzarse sería
# llegar a cero.
DMIN_MOVIMIENTO = 0.95
MANO_ATRAS = 1.0      # d: si la mano que da cuerda queda más atrás de la guía, el paso falla
SUBDIVIDIR = 4        # veces que un subpaso se puede partir en dos (ver `_subpaso`)
VISCOSIDAD = 0.2      # N·s/d por nodo: el roce con el aire, para que nada salte
SALTO = 0.35          # d: lo más que se puede mover un nodo de un cuadro al siguiente (T18)
HOLGURA_MANO = 0.8    # una mano que no puede avanzar sin acercar dos tramos a menos de dmin
                      # avanza esta parte de lo que puede, y espera
ENDEREZAR = 0.5       # s: lo que tarda la cuerda suelta (T21) en olvidar la forma que tenía al
                      # soltarse
RAYLEIGH = 0.03       # s: con largo fijo (T21), la cuerda tarda esto en cambiar de forma: lo suelto
                      # que se zafa de otro tramo se reacomoda en unos cuadros, no en uno


@dataclass
class CuadroGuia:
    """Un cuadro de la guía. `G` (N, 3) es dónde va cada nodo; `k` (N,), la rigidez de su
    resorte (0: libre); `manos`, los nodos que se mueven solos, a su lugar en G; `largos`
    (N − 1,), los largos de reposo de cada tramo; `curvatura` (N − 2, 3), la memoria.
    `cambio` es cuántos nodos tiene de más (o de menos) que el cuadro de antes, en el chicote:
    un nodo nuevo nace partiendo el último tramo, y uno que sobra es el anterior a la mano."""
    G: np.ndarray
    k: np.ndarray
    manos: np.ndarray
    largos: np.ndarray
    curvatura: np.ndarray | None
    cambio: int = 0
    recoge: bool = False      # la mano recoge cuerda: el último tramo se acorta con ella (T18)
    # Con largo fijo (T21): los largos de reposo son los de la guía, sin el tramo de la mano
    # medido en cada cuadro, y la cuerda suelta (`suelto`, de 0 a 1 por nodo) lleva su propia
    # viscosidad (`viscosidad`, por nodo) y su propia memoria: la forma que tenía al soltarse,
    # que se va enderezando en ENDEREZAR s. Así un lazo que se suelta no salta, y lo que cuelga
    # se dobla con su rigidez, sin quebrarse en un codo.
    largo_fijo: bool = False
    viscosidad: np.ndarray | None = None
    suelto: np.ndarray | None = None


@dataclass
class Cuadros:
    """Los cuadros de un tramo del video: la cuerda en cada uno (listas de (N, 3), N puede
    cambiar) y, en los que cambian de largo, cómo se partió el último tramo (la fracción desde
    el penúltimo nodo), para que `comprobar` compare el mismo número de nodos."""
    X: list = field(default_factory=list)
    partido: dict = field(default_factory=dict)   # cuadro → fracciones de los tramos partidos
    quitado: dict = field(default_factory=dict)   # cuadro → cuántos nodos se quitaron
    medio: dict = field(default_factory=dict)     # cuadro → la cuerda en los subpasos de antes
    anadido: dict = field(default_factory=dict)   # cuadro → los nodos que salieron de la mano (T21d),
                                                   # donde esperaban
    esperas: int = 0                               # subpasos en que una mano tuvo que esperar
    newton: int = 0



def _varilla(largos, material, curvatura) -> Varilla:
    return Varilla(np.asarray(largos, float), material, curvatura=curvatura)


def _mesa_y_anfitrion(X, solido):
    return contacto(X, np.array([0, len(X)]), [1.0], solido)


def _partir(x, v, frac):
    """La cuerda con el último tramo partido en `frac` (desde el penúltimo nodo): la forma no
    cambia, así que tampoco puede acercar nada."""
    p = x[-2] + frac * (x[-1] - x[-2])
    x = np.vstack([x[:-1], p, x[-1:]])
    v = np.vstack([v[:-1], (v[-2] + v[-1]) / 2, v[-1:]])
    return x, v


def seguir(x0, guia, solido=None, material=None, resorte: float = RESORTE,
           subpasos: int = SUBPASOS, fps: int = FPS, registro=None) -> Cuadros:
    """Los cuadros de la cuerda que parte de x0 y sigue la guía (una lista de CuadroGuia, la
    primera es la de x0). `registro(i, x)` se llama en cada cuadro."""
    material = material or material_de(1.0)
    dt = 1.0 / (fps * subpasos)
    x = np.array(x0, float)
    v = np.zeros_like(x)
    out = Cuadros(X=[x.copy()])
    malla = _mesa_y_anfitrion(x, solido)
    kappa = rigidez_barrera(max(1.0, resorte * 1.0))
    previo = guia[0]
    # La memoria de la cuerda suelta (T21): la curvatura que tenía cada nodo al soltarse, que
    # se va enderezando.
    memoria_suelta = None
    suelto_antes = np.zeros(len(x))
    decae = math.exp(-1.0 / (fps * ENDEREZAR))
    for i, g in enumerate(guia[1:], start=1):
        if g.cambio > 0:
            atras = float(np.linalg.norm(x[-1] - previo.G[-1]))
            if atras > MANO_ATRAS:
                from ..libre import TrazadoError
                raise TrazadoError(f"cuadro {i}: la mano quedó {atras:.2f} d atrás de la guía: "
                                   "no puede pasar sin acercar dos tramos a menos de dmin")
            for _ in range(g.cambio):
                l_ult = np.linalg.norm(x[-1] - x[-2])
                frac = float(np.clip(g.largos[-2] / max(l_ult, 1e-9), 0.1, 0.9))
                x, v = _partir(x, v, frac)
                out.partido.setdefault(i, []).append(frac)
            malla = _mesa_y_anfitrion(x, solido)
        elif g.cambio < 0:
            for _ in range(-g.cambio):
                x = np.vstack([x[:-2], x[-1:]])
                v = np.vstack([v[:-2], v[-1:]])
            out.quitado[i] = -g.cambio
            malla = _mesa_y_anfitrion(x, solido)
        if g.largo_fijo and len(g.G) > len(x):
            # Con largo fijo, en una plantilla (T21d), la cuerda sale de la mano: los nodos que se
            # agregan entran quietos donde los pone la guía, que es donde esperaban sin verse.
            nuevos = np.array(g.G[len(x):], float)
            out.anadido[i] = nuevos.copy()
            x = np.vstack([x, nuevos])
            v = np.vstack([v, np.zeros_like(nuevos)])
            malla = _mesa_y_anfitrion(x, solido)
        if len(x) != len(g.G):
            raise ValueError(f"cuadro {i}: la cuerda tiene {len(x)} nodos y la guía {len(g.G)}")
        if g.cambio < 0 and malla.margen(x) <= 0:
            from ..libre import TrazadoError
            raise TrazadoError(f"cuadro {i}: al recoger la cuerda, dos tramos quedan a menos de dmin")
        # El tramo que sale de la mano mide lo que mide: la mano da justo la cuerda que hace
        # falta. Con el largo de la guía, ese tramo quedaba estirado o encogido (la mano no está
        # justo en la guía) y el nodo de al lado saltaba hasta 0,16 d en un subpaso.
        largos = np.array(g.largos, float)
        if (g.cambio or len(x) > 2) and not g.largo_fijo:
            largos[-1] = max(float(np.linalg.norm(x[-1] - x[-2])), 0.05)
        if g.recoge:
            # Al recoger, el tramo de la mano se acorta con ella: con el largo que mide en cada
            # cuadro, la mano lo comprimía al acercarse, y la cuerda casi no se encoge, así que
            # empujaba al nodo de al lado. La mano nunca lo alcanzaba, la cuerda de adelante se
            # arrugaba y el último tramo llegaba a medir 2,3 d, con la punta en codo (T18).
            largos[-1] = max(min(largos[-1], float(g.largos[-1])), 0.05)
        curvatura = g.curvatura
        if g.suelto is not None and np.any(np.asarray(g.suelto, float)[1:-1] > 0):
            p = np.clip(np.asarray(g.suelto, float), 0.0, 1.0)
            actual = Varilla.curvatura_de(x)
            if memoria_suelta is None:
                memoria_suelta = actual.copy()
            memoria_suelta = memoria_suelta * decae
            recien = (suelto_antes[1:-1] <= 0) & (p[1:-1] > 0)
            memoria_suelta[recien] = actual[recien]
            w = p[1:-1, None]
            de_guia = np.zeros((len(x) - 2, 3)) if curvatura is None else np.asarray(curvatura, float)
            curvatura = w * memoria_suelta + (1 - w) * de_guia
            suelto_antes = p
        else:
            suelto_antes = np.zeros(len(x))
        var = _varilla(largos, material, curvatura)
        visc = VISCOSIDAD if g.viscosidad is None else np.asarray(g.viscosidad, float)
        # Solo donde hay cuerda suelta: con la cuerda toda guiada (la gaza pequeña del as de guía,
        # con el firme corriendo), frenaba el estiramiento detrás de la mano y la cuerda se
        # alargaba un 1,5 %.
        rayleigh = RAYLEIGH if g.largo_fijo and np.any(suelto_antes > 0) else 0.0
        # La mano del firme (el nodo 0) sostiene; las demás tiran de su nodo con un resorte
        # fuerte: así el contacto puede apartarlas un poco y ninguna se traba contra la cuerda
        # que ya está, que es lo que hace una mano de verdad.
        todas = np.asarray(g.manos, int)
        manos = todas[todas == 0]
        tiran = todas[todas != 0]
        if len(previo.G) == len(g.G):
            G0 = previo.G
        else:
            # Con un nodo más o menos, las manos vienen igual de donde estaban: la del firme
            # es el primero y la que da cuerda, el último.
            G0 = g.G.copy()
            G0[0], G0[-1] = previo.G[0], previo.G[-1]
        k = np.array(g.k, float)
        k[tiran] = RESORTE_MANO

        def armar(metas, var=var, k=k, manos=manos):
            return Sistema([var], malla, fijos=manos, kappa=kappa, roce=True,
                           resortes=(k, metas), tol_fuerza=1e-6)

        def metas_en(t, todas=todas, G0=G0, g=g):
            metas = g.G.copy()
            metas[todas] = G0[todas] + t * (g.G[todas] - G0[todas])
            return metas

        for j in range(1, subpasos + 1):
            m0, m1 = metas_en((j - 1) / subpasos), metas_en(j / subpasos)
            y = x.copy()
            if len(manos):
                y[manos] = m1[manos]
                a = malla.paso_libre(x, y)
                if a < 1.0:
                    out.esperas += 1
                    y[manos] = x[manos] + HOLGURA_MANO * a * (m1[manos] - x[manos])
            try:
                x, v = _subpaso(armar, m0, m1, malla, x, y, v, dt, out, i, ultimo=j == subpasos,
                                visc=visc, rayleigh=rayleigh)
            except RuntimeError as e:   # ipctk, con un par dentro de la barrera
                from ..libre import TrazadoError
                corto = float(np.min(np.linalg.norm(np.diff(y, axis=0), axis=1)))
                raise TrazadoError(
                    f"cuadro {i}: el motor no pudo seguir la guía ({e}); el par más cercano "
                    f"queda a {malla.margen(y):+.3f} de dmin y el tramo más corto mide "
                    f"{corto:.3f}") from e
        out.X.append(x.copy())
        if registro is not None:
            registro(i, x)
        previo = g
    return out


def _ajustar(a, i: int, partido: dict, quitado: dict, anadido=None) -> np.ndarray:
    """El cuadro de antes del cuadro i con los nodos que cambiaron al seguir: el último tramo
    partido donde la mano dio cuerda, el nodo de al lado de la mano quitado donde la recogió, o
    los que salieron de la mano (T21d) donde esperaban."""
    a = np.asarray(a, float)
    for frac in partido.get(i, ()):
        a, _ = _partir(a, np.zeros_like(a), frac)
    for _ in range(quitado.get(i, 0)):
        a = np.vstack([a[:-2], a[-1:]])
    if anadido and i in anadido:
        a = np.vstack([a, anadido[i]])
    return a


def repartir_saltos(X: list, partido: dict, quitado: dict, medio: dict, desde: int = 0):
    """Donde un nodo salta más de SALTO de un cuadro al siguiente (la punta que se zafa de un
    contacto, T18), el cuadro se reparte en los subpasos que dio el motor para llegar a él
    (`medio`): son estados de la cuerda de verdad, y van en línea recta y libres de uno al
    siguiente. El salto queda en varios cuadros, un instante más lento. También donde la mano da
    o recoge cuerda: el cuadro de antes se parte o se recorta como al seguir, y el cambio de
    nodos queda en el primero de los cuadros nuevos. Solo en los cuadros desde `desde`. Da los
    cuadros, `partido`, `quitado` y `medio` con los índices nuevos, y de qué cuadro viejo sale
    cada uno nuevo."""
    out, origen = [X[0]], [0]
    nuevo_de = {0: 0}
    p2, q2, m2 = {}, {}, {}

    def cambio_en(k, i):
        if i in partido:
            p2[k] = partido[i]
        if i in quitado:
            q2[k] = quitado[i]

    for i in range(1, len(X)):
        a, b = _ajustar(X[i - 1], i, partido, quitado), np.asarray(X[i], float)
        cadena = medio.get(i, ())
        primero = True
        if (i >= desde and len(a) == len(b) and cadena
                and float(np.max(np.linalg.norm(b - a, axis=1))) > SALTO):
            previo = a
            for j_y, y in enumerate([*cadena, b]):
                y = np.asarray(y, float)
                # Un subpaso que todavía salta de más se reparte sobre su recta, que es la que
                # `comprobar` verifica libre entre dos estados seguidos.
                partes = int(math.ceil(float(np.max(np.linalg.norm(y - previo, axis=1))) / SALTO))
                nuevos = [previo + (j / partes) * (y - previo) for j in range(1, partes)]
                if j_y < len(cadena):
                    nuevos.append(y)
                for z in nuevos:
                    if primero:
                        cambio_en(len(out), i)
                        primero = False
                    out.append(z)
                    origen.append(i)
                previo = y
        k = len(out)
        out.append(b)
        origen.append(i)
        nuevo_de[i] = k
        if primero:
            cambio_en(k, i)
            if i in medio:
                m2[k] = medio[i]
    return out, p2, q2, m2, nuevo_de


def saltos(X: list, partido=None, quitado=None, anadido=None) -> list[float]:
    """Lo más que se mueve un nodo de cada cuadro al siguiente. Donde la cuerda cambia de nodos,
    el cuadro de antes se parte o se recorta igual que al seguir (como en `comprobar`): ahí, al
    dar o recoger cuerda, es donde saltaba la punta (T18). Sin decir cómo cambió, ese cuadro no
    se mide."""
    partido, quitado = partido or {}, quitado or {}
    out = []
    for i in range(1, len(X)):
        a, b = _ajustar(X[i - 1], i, partido, quitado, anadido), np.asarray(X[i], float)
        if len(a) == len(b):
            out.append(float(np.max(np.linalg.norm(b - a, axis=1))))
    return out


def _subpaso(armar, m0, m1, malla, x, y, v, dt, out, i, ultimo, nivel=0, visc=VISCOSIDAD, rayleigh=0.0):
    """Un subpaso de x a y (con la mano del firme ya movida) y lo que da el motor, con las
    manos que tiran yendo de sus metas m0 a m1. Si ir en línea recta de y a lo que da el motor
    acercaría dos tramos a menos de DMIN_MOVIMIENTO·dmin (el motor no los acerca: cada iteración
    de Newton se recorta con la CCD, pero da varias), el subpaso se parte en dos mitades, con
    las metas también a mitad de camino, hasta SUBDIVIDIR veces. Así cada estado guardado va en
    línea recta y libre al siguiente, y `comprobar` lo puede ver. Los estados intermedios van a
    out.medio."""
    sis = armar(m1)
    r = sis.paso(y, v, dt=dt, viscosidad=visc, rayleigh=rayleigh)
    out.newton += r.iteraciones
    if nivel < SUBDIVIDIR and malla.paso_libre(y, r.x, malla.dmin * DMIN_MOVIMIENTO) < 1.0:
        manos = sis.fijos
        mm = (m0 + m1) / 2
        mitad = x.copy()
        mitad[manos] = x[manos] + 0.5 * (y[manos] - x[manos])
        x1, v1 = _subpaso(armar, m0, mm, malla, x, mitad, v, dt / 2, out, i, False, nivel + 1, visc,
                          rayleigh)
        y2 = x1.copy()
        y2[manos] = y[manos]
        a = malla.paso_libre(x1, y2)
        if a < 1.0:
            y2[manos] = x1[manos] + HOLGURA_MANO * a * (y[manos] - x1[manos])
        return _subpaso(armar, mm, m1, malla, x1, y2, v1, dt / 2, out, i, ultimo, nivel + 1, visc,
                        rayleigh)
    out.medio.setdefault(i, []).append(np.array(y, float))
    if not ultimo:
        out.medio.setdefault(i, []).append(r.x.copy())
    return r.x, r.v


def encajar(x, B, solido=None, material=None, cuadros: int = 24, resorte_max: float = 50.0,
            manos=None):
    """Asienta x en la pose B (las dos con los mismos nodos): pasos cuasiestáticos con la
    memoria de B, con las manos en su lugar de B y resortes hacia B que suben de a poco. Da los
    cuadros del encaje (sin x) y la distancia más grande que queda a B."""
    material = material or material_de(1.0)
    B = np.asarray(B, float)
    x = np.array(x, float)
    malla = _mesa_y_anfitrion(x, solido)
    manos = np.array([0, len(x) - 1] if manos is None else manos, int)
    largos = np.linalg.norm(np.diff(B, axis=0), axis=1)
    var = _varilla(largos, material, Varilla.curvatura_de(B))
    kappa = rigidez_barrera(max(1.0, resorte_max))
    out = []
    for j in range(1, cuadros + 1):
        k = resorte_max * (j / cuadros) ** 2
        y = x.copy()
        y[manos] = B[manos]
        a = malla.paso_libre(x, y)
        if a < 1.0:
            y[manos] = x[manos] + HOLGURA_MANO * a * (B[manos] - x[manos])
        sis = Sistema([var], malla, fijos=manos, kappa=kappa, roce=False,
                      resortes=(np.full(len(x), k), B), tol_fuerza=1e-6)
        x = sis.paso(y, amortiguacion=2.0).x
        out.append(x.copy())
    return out, float(np.max(np.linalg.norm(x - B, axis=1)))


def recta(x, B, cuadros: int):
    """Los cuadros en línea recta de x a B (sin x, con B)."""
    x, B = np.asarray(x, float), np.asarray(B, float)
    return [x + (j / cuadros) * (B - x) for j in range(1, cuadros)] + [B.copy()]


def comprobar(X: list, solido=None, partido=None, quitado=None, medio=None, anadido=None) -> list[str]:
    """Las fallas de una lista de cuadros: un cuadro con un par a menos de dmin (de la cuerda
    o con la mesa y el anfitrión), o un cuadro al siguiente en que el movimiento en línea recta
    acerca dos tramos a menos de DMIN_MOVIMIENTO·dmin (la CCD). Donde la cuerda cambia de nodos, el cuadro de antes
    se parte o se recorta igual que al seguir, o gana los nodos que salieron de la mano
    (`anadido`, T21d) donde esperaban. Con `medio` (los subpasos de `seguir`), el movimiento se
    comprueba de subpaso en subpaso, que es lo que el motor dio."""
    partido, quitado, medio, anadido = partido or {}, quitado or {}, medio or {}, anadido or {}
    fallas = []
    malla = None
    for i, x in enumerate(X):
        if malla is None or malla.N != len(x):
            malla = _mesa_y_anfitrion(x, solido)
        m = malla.margen(x)
        if m < -1e-9:
            fallas.append(f"cuadro {i}: un par queda a {m + malla.dmin:.3f}, menos de dmin")
        if i == 0:
            continue
        a = np.asarray(X[i - 1], float)
        for frac in partido.get(i, ()):
            a, _ = _partir(a, np.zeros_like(a), frac)
        for _ in range(quitado.get(i, 0)):
            a = np.vstack([a[:-2], a[-1:]])
        if i in anadido:
            a = np.vstack([a, anadido[i]])
        if len(a) != len(x):
            fallas.append(f"cuadro {i}: cambia de {len(X[i - 1])} a {len(x)} nodos sin decir cómo")
            continue
        cadena = [a, *medio.get(i, ()), x]
        dm = malla.dmin * DMIN_MOVIMIENTO
        if min(malla.paso_libre(p, q, dm) for p, q in zip(cadena[:-1], cadena[1:])) < 1.0:
            fallas.append(f"cuadro {i}: entre el cuadro {i - 1} y este, dos tramos pasan a menos "
                          f"de {dm:.2f} d")
    return fallas
