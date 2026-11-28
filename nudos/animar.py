"""La animación entre pasos (T17): la guía que sigue el motor al atar.

Entre la pose de un paso de la ficha (A) y la del siguiente (B), la guía dice cuadro a cuadro
dónde va cada nodo, sin física. La planea esto, y el motor la sigue (`nudos/fisica/atar.py`):

- **Alinear** (`alinear`): lo que no cambia al comienzo de la cuerda se alinea desde el firme, y
  lo que no cambia al final, desde la punta. Si el final coincide (la gaza pequeña del as de
  guía se forma en el medio), la cuerda que falta entra por el extremo del firme («firme»); si
  no, la mano da cuerda o la recoge en el chicote («punta»).
- **Los movimientos**, en este orden: recoger lo que el paso siguiente vuelve a trazar,
  acomodar lo que solo cambia de forma (en línea recta, de A a B) y enhebrar la cuerda nueva
  (la mano lleva la punta por el camino de B y cada nodo nuevo sale de ella).
- **Las alturas** (`alturas`, en un nudo libre): en cada cuadro se buscan los cruces de la guía
  vista desde arriba, y el tramo que va encima sube sobre el otro con una holgura: el de B si el
  cruce está en B, el de A si solo está en A, y el que más se mueve si aparece y desaparece. Si
  un cruce de A sigue en B con el encima al revés, la cuerda tendría que atravesarse: la guía
  falla. Cuando la cuerda nueva pasa por debajo de un tramo, sube el tramo: es la mano que lo
  levanta.
- **En una plantilla**, B ya trae sus alturas sobre los palos: la guía no las toca, y lo atado
  lleva la tensión de atado (`tensiones_de_amarre`) mientras avanza la mano.

Los tiempos (la mano a VEL, más lenta cerca de los cruces) salen en cuadros de 1/FPS s.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .cruces import encontrar_cruces
from .fisica.atar import FPS, RESORTE, VISCOSIDAD as VISCOSIDAD_GUIA, CuadroGuia
from .fisica.varilla import Varilla
from .libre import TrazadoError, _suave

VEL = 5.0             # d/s: la mano
VEL_CRUCE = 2.5       # d/s: a menos de CERCA_CRUCE de un cruce de la cuerda nueva
CERCA_CRUCE = 2.0
VEL_RAPIDA = 10.0     # d/s: en una plantilla, después de los primeros LENTO d de cuerda nueva.
# Con más, la mano daría más de un nodo por cuadro, y los nodos nuevos se amontonaban en
# la punta hasta doblar la cuerda (medido en el amarre a 30 d/s).
LENTO = 10.0
ARRANQUE = 0.3        # s: lo que tarda la mano en llegar a su velocidad y en frenar
ALINEAR = 0.5         # d: dos nodos a menos de esto están en el mismo lugar
SUFIJO_FIRME = 10.0   # d: con tanto final igual, la cuerda entra por el firme
HOLGURA = 1.0         # d: la cuerda que cruza pasa esto por encima de la otra
ALTO_MANO = 1.0       # d: la mano lleva la punta así de levantada
DETRAS_MANO = 3.0     # d: lo que la cuerda tarda en apoyarse detrás de la mano
ANTES_CRUCE = 4.0     # d: el tramo de encima sube antes de que llegue la punta
DESPUES_CRUCE = 3.0
ACOMODAR_MIN = 0.5    # s
MARGEN_MANO = 0.5     # d: en una plantilla, la mano va así de afuera de la madera
LIBRE_MANO = 1.1      # d: sin acercarse más que esto a la cuerda que ya está
VECINOS_MANO = 2.0    # d: lo que hay detrás de la mano a lo largo de la cuerda no cuenta
ANTICIPA = 15         # cuadros: un cruce nuevo se prepara antes de aparecer
RAMPA = 1.5           # d: lo que tarda en subir o bajar un tramo, a lo largo de la cuerda
RADIO_GUIA = 1.5      # d: en un nudo libre, la cuerda no sigue a la guía en curvas más cerradas
                      # (T18; el lazo más chico de las fichas, la gaza pequeña, mide 1,55)


@dataclass
class Tramo:
    """La guía de un paso al siguiente (n es el paso de destino)."""
    n: int
    modo: str                  # «punta» o «firme»
    x0: np.ndarray             # de dónde parte la cuerda (A, o A con el firme alargado)
    B: np.ndarray
    guia: list[CuadroGuia]
    fases: dict = field(default_factory=dict)   # nombre → (primer cuadro, último)
    visible: list | None = None   # en una plantilla (T21d), dónde sale la cuerda de la mano (σ)


# --------------------------------------------------------------------------
# Alinear
# --------------------------------------------------------------------------
def alinear(A, B, r: int):
    """El modo y, en «punta», el primer nodo r1 ≥ r de B que no coincide con A (lo que se
    recoge y se vuelve a dar); en «firme», cuántos nodos entran por el firme."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    n = min(len(A), len(B))
    cola = np.linalg.norm(A[::-1][:n] - B[::-1][:n], axis=1) > ALINEAR
    q = int(np.argmax(cola)) if cola.any() else n
    h = float(np.mean(np.linalg.norm(np.diff(B, axis=0), axis=1)))
    if q * h >= SUFIJO_FIRME and len(B) >= len(A):
        return "firme", len(B) - len(A)
    r1 = max(1, min(r, len(A)))
    while r1 < min(len(A), len(B)) and np.linalg.norm(A[r1] - B[r1]) <= ALINEAR:
        r1 += 1
    return "punta", r1


def _en(X, h, s) -> np.ndarray:
    """El punto de la cuerda X en la posición s a lo largo de ella, contada en nodos (s/h): el
    nodo i está en i·h, aunque sus tramos no midan justo h (la cuerda asentada, elevada)."""
    u = float(np.clip(s / h, 0.0, len(X) - 1))
    i = int(min(math.floor(u), len(X) - 2))
    t = u - i
    return X[i] + t * (X[i + 1] - X[i])


# --------------------------------------------------------------------------
# Las alturas
# --------------------------------------------------------------------------
def _referencia(X, h, desplazar: int = 0):
    """Los cruces de una pose vista desde arriba: (sa, sb, la primera encima), con las
    posiciones corridas `desplazar` nodos (A en el modo «firme»)."""
    s = np.arange(len(X)) * h
    out = []
    for c in encontrar_cruces(X, h):
        za, zb = np.interp(c.sa, s, X[:, 2]), np.interp(c.sb, s, X[:, 2])
        out.append((c.sa + desplazar * h, c.sb + desplazar * h, bool(za > zb)))
    return out


def _buscar(refs, sa, sb, tol=1.5):
    for ra, rb, enc in refs:
        if abs(ra - sa) < tol and abs(rb - sb) < tol:
            return enc
    return None


# --------------------------------------------------------------------------
# Los tiempos
# --------------------------------------------------------------------------
def _recorrido(s0, s1, velocidad) -> np.ndarray:
    """Las posiciones de la mano en cada cuadro al ir de s0 a s1 (a lo largo de su camino),
    con la velocidad `velocidad(s)` en d/s, arrancando y frenando en ARRANQUE s."""
    if abs(s1 - s0) < 1e-9:
        return np.array([s1])
    ss = np.linspace(s0, s1, max(2, int(abs(s1 - s0) / 0.01)))
    v = np.array([velocidad(x) for x in ss])
    dt = np.abs(np.diff(ss)) / ((v[:-1] + v[1:]) / 2)
    t = np.concatenate([[0.0], np.cumsum(dt)])
    T = t[-1]
    # Arranque y frenado: el tiempo se estira cerca de las puntas.
    a = min(ARRANQUE, T / 3)
    if a > 0:
        T2 = T + 2 * a
        tt = np.linspace(0.0, T2, max(2, int(round(T2 * FPS)) + 1))
        # u(tt) en [0, T]: la posición en el tiempo sin arranque, con una curva suave.
        u = np.empty_like(tt)
        for k, x in enumerate(tt):
            if x < 2 * a:
                u[k] = x * x / (4 * a)
            elif x > T2 - 2 * a:
                y = T2 - x
                u[k] = T - y * y / (4 * a)
            else:
                u[k] = x - a
        return np.interp(u, t, ss)
    return np.array([s0, s1])


def _radios(P) -> np.ndarray:
    """El radio de curvatura en cada nodo interior de P (N, 2): el largo medio de sus dos
    tramos sobre el ángulo que gira la cuerda en él."""
    d1, d2 = P[1:-1] - P[:-2], P[2:] - P[1:-1]
    l1, l2 = np.linalg.norm(d1, axis=1), np.linalg.norm(d2, axis=1)
    cruz = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    punto = (d1 * d2).sum(axis=1)
    giro = np.abs(np.arctan2(cruz, punto))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(giro > 1e-9, (l1 + l2) / 2 / np.maximum(giro, 1e-12), np.inf)


def radio_minimo(X, mov=None) -> float:
    """El radio de curvatura más chico de la cuerda vista desde arriba (en los nodos que se
    mueven, si se da `mov`)."""
    R = _radios(np.asarray(X, float)[:, :2])
    if mov is not None:
        R = R[np.asarray(mov)[1:-1] > 0.05]
    return float(R.min()) if len(R) else math.inf


def _suave_t(n: int) -> np.ndarray:
    u = np.linspace(0, 1, n)
    return u * u * (3 - 2 * u)


# --------------------------------------------------------------------------
# La guía
# --------------------------------------------------------------------------
def tramo(n, A, B, h, resaltado, plantilla=None, solido=None) -> Tramo:
    """La guía del paso n − 1 (A) al paso n (B). `resaltado` es el del paso n (a lo largo de
    la cuerda). `plantilla`, en un nudo de plantilla, es una función (N, hasta) → tensión de
    atado por tramo (N,); sin ella, el nudo es libre y la guía planea las alturas."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    r = int(round(resaltado[0] / h)) if resaltado else 0
    modo, valor = alinear(A, B, r)
    libre = plantilla is None
    if modo == "firme":
        return _tramo_firme(n, A, B, h, valor, libre)
    return _tramo_punta(n, A, B, h, valor, plantilla, solido)


def _cuadro(G, h, manos, plantilla=None, hasta=None, ultimo=None, cambio=0, recoge=False):
    N = len(G)
    largos = np.full(N - 1, float(h))
    if ultimo is not None:
        largos[-1] = ultimo
    k = np.full(N, RESORTE)
    curvatura = Varilla.curvatura_de(G)
    if plantilla is not None:
        from .fisica.asentar import material_de
        T = plantilla(N, hasta)[:N - 1]
        largos = largos / (1 + T / material_de(1.0).EA)
    else:
        k, curvatura = _aflojar(G, h, k, curvatura)
    return CuadroGuia(G=G, k=k, manos=np.asarray(manos, int), largos=largos,
                      curvatura=curvatura, cambio=cambio, recoge=recoge)


def _aflojar(G, h, k, curvatura):
    """Donde la guía, vista desde arriba, dobla más cerrado que RADIO_GUIA, la cuerda no la
    sigue: el resorte hacia la guía se afloja y la memoria no pide más curva que esa (T18). Al
    formar un lazo en medio de la cuerda, la recta de A a B pasa por una cúspide (la cuerda
    doblada sobre sí misma); el motor no puede doblarla así, se cargaba y la soltaba de golpe:
    la gaza pequeña del as de guía saltaba 0,6 d en un cuadro (T17)."""
    R = _radios(np.asarray(G, float)[:, :2])
    f = np.clip(R / RADIO_GUIA, 0.0, 1.0) ** 2
    # La cúspide afloja también a sus vecinos, a 1,5 d a cada lado.
    w = max(1, int(round(1.5 / h)))
    f = np.minimum.reduce([np.roll(np.pad(f, w, mode="edge"), j)[w:-w] for j in range(-w, w + 1)])
    k = k.copy()
    k[1:-1] *= f
    tope = 2 * math.tan(h / (2 * RADIO_GUIA))
    norma = np.linalg.norm(curvatura, axis=1)
    escala = np.where(norma > tope, tope / np.maximum(norma, 1e-12), 1.0)
    return k, curvatura * escala[:, None]


@dataclass
class _Borrador:
    """Un cuadro de la guía antes de sus alturas. G puede llevar nodos de más: los que la guía
    mira más allá de la mano. Solo quedan los primeros `n`."""
    G: np.ndarray
    n: int
    manos: list
    hasta: float
    ultimo: float | None = None
    cambio: int = 0
    mov: np.ndarray | None = None      # cuánto se mueve cada nodo: decide los cruces nuevos
    holgura: object = None             # (sa, sb) → (holgura, peso)
    exacto: np.ndarray | None = None   # el cuadro es exactamente esto (A al empezar, B al final)
    recoge: bool = False               # la mano recoge cuerda


def _rampa(x) -> float:
    return float(_suave(np.clip(x, 0.0, 1.0)))


def _seguir_cruces(borradores, h, refs_A, refs_B, libre, salto: float = 1.0):
    """Los cruces de la guía vista desde arriba en cada cuadro, seguidos de un cuadro al
    siguiente (si se corren menos de `salto` a lo largo de las dos cuerdas), con su encima
    decidido para toda su vida: el de B si el cruce llega hasta el final, el de A si está desde
    el principio, el del tramo que más se mueve si no. Un cruce de A que llega a B con el encima
    al revés es una TrazadoError. Da, por cuadro, la lista de (sa, sb, seno, primera encima)."""
    por_cuadro = [encontrar_cruces(b.G, h) if libre else [] for b in borradores]
    pistas = []          # [primer cuadro, último cuadro, [(cuadro, k)], (sa, sb) del último]
    activas = []
    for f, cruces in enumerate(por_cuadro):
        nuevas = []
        libres = list(range(len(activas)))
        for k, c in enumerate(cruces):
            mejor, dmin = None, salto
            for j in libres:
                ta, tb = activas[j][3]
                d = abs(c.sa - ta) + abs(c.sb - tb)
                if d < dmin:
                    mejor, dmin = j, d
            if mejor is None:
                p = [f, f, [(f, k)], (c.sa, c.sb)]
                pistas.append(p)
            else:
                libres.remove(mejor)
                p = activas[mejor]
                p[1], p[3] = f, (c.sa, c.sb)
                p[2].append((f, k))
            nuevas.append(p)
        activas = nuevas
    ultimo = len(borradores) - 1
    enc = {}
    extra = [[] for _ in borradores]
    for f0, f1, ocur, _ in pistas:
        c0 = por_cuadro[f0][ocur[0][1]]
        c1 = por_cuadro[f1][ocur[-1][1]]
        e_b = _buscar(refs_B, c1.sa, c1.sb) if f1 == ultimo else None
        e_a = _buscar(refs_A, c0.sa, c0.sb) if f0 == 0 else None
        if e_a is not None and e_b is not None and e_a != e_b:
            raise TrazadoError(
                f"el cruce de {c1.sa:.1f} y {c1.sb:.1f} d a lo largo de la cuerda está al revés en "
                "los dos pasos: atarlo pide que la cuerda se atraviese")
        e = e_b if e_b is not None else e_a
        if e is None:
            mov = borradores[f0].mov
            s = np.arange(len(mov)) * h
            e = bool(np.interp(c0.sa, s, mov) >= np.interp(c0.sb, s, mov))
        for f, k in ocur:
            enc[(f, k)] = e
        # Un cruce que aparece en medio del tramo se prepara antes: el tramo de encima sube
        # durante ANTICIPA cuadros antes de que los dos se toquen vistos desde arriba, y uno
        # que desaparece baja después. Si no, el tramo saltaría de golpe.
        if f0 > 0:
            for f in range(max(0, f0 - ANTICIPA), f0):
                extra[f].append((c0.sa, c0.sb, c0.seno, e, (f - f0 + ANTICIPA) / ANTICIPA))
        if f1 < ultimo:
            for f in range(f1 + 1, min(ultimo, f1 + ANTICIPA) + 1):
                extra[f].append((c1.sa, c1.sb, c1.seno, e, (f1 + ANTICIPA - f) / ANTICIPA))
    return [[(c.sa, c.sb, c.seno, enc[(f, k)], 1.0) for k, c in enumerate(cr)] + extra[f]
            for f, cr in enumerate(por_cuadro)]


def alturas(G, h, cruces, holgura=None) -> np.ndarray:
    """La altura de la guía G (N, 3): la suya, con el tramo de encima de cada cruce (sa, sb,
    seno, primera encima, peso) subido sobre el otro, con la holgura y por el peso que diga
    `holgura(sa, sb)`. El peso deja subir de a poco un tramo cuando un cruce aparece."""
    z = G[:, 2].copy()
    if not cruces:
        return z
    s = np.arange(len(G)) * h
    plan = []
    for sa, sb, seno, enc, w in cruces:
        so, su = (sa, sb) if enc else (sb, sa)
        hol, peso = holgura(sa, sb) if holgura is not None else (0.0, 1.0)
        peso *= _rampa(w)
        if peso > 0:
            plan.append((so, su, seno, hol, peso))
    for _ in range(4):
        for so, su, seno, hol, peso in plan:
            sube = peso * (np.interp(su, s, z) + 1.0 + hol - np.interp(so, s, z))
            if sube <= 1e-9:
                continue
            # El ancho de la subida no llega al tramo de abajo: en un lazo que se cierra, las
            # dos pasadas están cerca a lo largo de la cuerda y subirían juntas.
            w = min(float(np.clip(2.6 / max(seno, 0.25), 2.6, 5.0)) + hol, abs(so - su) / 2)
            b = _suave((1.0 - np.abs(s - so) / w) / 0.65)
            z = z + sube * b
    return z


def _terminar(borradores, h, refs_A, refs_B, plantilla) -> list[CuadroGuia]:
    libre = plantilla is None
    cruces = _seguir_cruces(borradores, h, refs_A, refs_B, libre)
    guia = []
    for b, cr in zip(borradores, cruces):
        G = b.G.copy()
        if libre:
            G[:, 2] = alturas(G, h, cr, b.holgura)
        G = G[:b.n]
        if b.exacto is not None:
            G = b.exacto.copy()
        guia.append(_cuadro(G, h, b.manos, plantilla, b.hasta, b.ultimo, b.cambio, b.recoge))
    return guia


def _tramo_firme(n, A, B, h, delta, libre) -> Tramo:
    """La cuerda entra por el firme: A alargada detrás de su primer nodo, y cada nodo de B va
    en línea recta desde su lugar en A (corrido delta nodos)."""
    d = A[0] - A[1]
    d = d / np.linalg.norm(d)
    ext = np.array([A[0] + d * h * (delta - i) for i in range(delta)]).reshape(-1, 3)
    S = np.vstack([ext, A])
    mov = np.linalg.norm(B - S, axis=1)
    nf = max(int(round(max(ACOMODAR_MIN, float(mov.max()) / VEL) * FPS)), 2)
    refs_A, refs_B = _referencia(A, h, delta), _referencia(B, h)
    borr = []
    for u in _suave_t(nf + 1):
        env = math.sin(math.pi * u)
        borr.append(_Borrador(S + u * (B - S), len(B), [0, len(B) - 1], (len(B) - 1) * h,
                              mov=mov, holgura=lambda a, b, env=env: (HOLGURA * env, 1.0),
                              exacto=B if u == 1.0 else (S if u == 0.0 else None)))
    plantilla = None if libre else (lambda N, s: np.zeros(N))
    guia = _terminar(borr, h, refs_A, refs_B, plantilla)
    return Tramo(n, "firme", S, B, guia, {"acomodar": (0, nf)})


def _afuera(solido, P) -> np.ndarray:
    """MARGEN_MANO hacia afuera de la madera desde el punto P, si está junto a un palo de la
    cruz (a menos de un diámetro de cuerda de su superficie); si no, nada. Así la mano que da
    vueltas no se arrastra sobre la cuerda que ya está en el palo."""
    if solido is None or not hasattr(solido, "zb"):
        return np.zeros(3)
    out = np.zeros(3)
    for eje, zc in ((1, solido.zb), (0, solido.zt)):
        otro = 1 - eje
        d = np.array([0.0, 0.0, P[2] - zc])
        d[otro] = P[otro]
        r = float(np.linalg.norm(d))
        if r < solido.radio + 1.5 and abs(P[eje]) < solido.largo / 2:
            out = d / max(r, 1e-9) * MARGEN_MANO
    return out


def _afuera_libre(solido, B, h, s, mm) -> np.ndarray:
    """`_afuera`, pero solo hasta donde la mano no se acerca a la cuerda que ya está (los
    nodos de B detrás de ella) a menos de LIBRE_MANO: entre los dos palos, los ahorcados pasan
    justos, y afuera de la madera está la vuelta de al lado."""
    P = _en(B, h, s)
    off = _afuera(solido, P)
    if not off.any():
        return off
    detras = B[:max(0, mm - int(VECINOS_MANO / h))]
    if not len(detras):
        return off
    for f in (1.0, 0.5, 0.25):
        if np.min(np.linalg.norm(detras - (P + f * off), axis=1)) >= LIBRE_MANO:
            return f * off
    return np.zeros(3)


def _tramo_punta(n, A, B, h, r1, plantilla, solido=None) -> Tramo:
    libre = plantilla is None
    borr: list[_Borrador] = []
    fases = {}
    refs_A, refs_B = _referencia(A, h), _referencia(B, h)
    nuevos = [c for c in refs_B if max(c[0], c[1]) >= (r1 - 1) * h]

    def nodos(s):
        return int(math.floor(s / h + 0.5)) + 1

    def con_mano(G, s_mano, lift, mano):
        """Sube la punta (el nodo `mano`, en la posición s_mano) y lo que va detrás de ella,
        ALTO_MANO por `lift`. En una plantilla, no: la cuerda va pegada a la madera y a las
        vueltas que ya están, y subirla la empuja contra ellas; ahí la mano va hacia afuera
        de la madera (`_afuera`)."""
        if lift <= 0 or not libre:
            return G
        arco = np.arange(len(G)) * h
        arco[mano] = s_mano
        arco[mano + 1:] = np.inf
        dist = (s_mano - arco) / DETRAS_MANO
        G[:, 2] += ALTO_MANO * lift * _suave(1 - np.clip(dist, 0, 1)) * (dist >= -1e-9)
        return G

    def cerca(s):
        return min((min(abs(s - a), abs(s - b)) for a, b, _ in nuevos), default=math.inf)

    def sin_holgura(a, b):
        return 0.0, 1.0

    # 1. Recoger lo que el paso siguiente vuelve a trazar.
    if r1 < len(A):
        vel_r = VEL if libre else VEL_RAPIDA
        S_rec = _recorrido((len(A) - 1) * h, (r1 - 1) * h, lambda s: vel_r)
        n_prev = len(A)
        for k, s in enumerate(S_rec):
            m = len(A) if k == 0 else max(nodos(s), r1)
            G = A[:m].copy()
            G[-1] = _en(A, h, s)
            G = con_mano(G, s, min(1.0, k / (ARRANQUE * FPS)), m - 1)
            borr.append(_Borrador(G, m, [0, m - 1], s, s - (m - 2) * h, m - n_prev,
                                  mov=np.zeros(m), holgura=sin_holgura, recoge=True,
                                  exacto=A if k == 0 else None))
            n_prev = m
        fases["recoger"] = (0, len(borr) - 1)
        inicio = borr[-1].G.copy()
    else:
        inicio = A.copy()
        borr.append(_Borrador(A.copy(), len(A), [0, len(A) - 1], (len(A) - 1) * h,
                              mov=np.zeros(len(A)), holgura=sin_holgura, exacto=A))

    # 2. Acomodar: cada nodo de los que quedan, de donde está a su lugar en B.
    m = len(inicio)
    meta = B[:m].copy()
    mov = np.linalg.norm(meta - inicio, axis=1)
    if mov.max() > 0.05:
        nf = max(int(round(max(ACOMODAR_MIN, float(mov.max()) / VEL) * FPS)), 2)
        f0 = len(borr)
        for u in _suave_t(nf + 1)[1:]:
            env = math.sin(math.pi * u)
            borr.append(_Borrador(inicio + u * (meta - inicio), m, [0, m - 1], (m - 1) * h,
                                  mov=mov, holgura=lambda a, b, env=env: (HOLGURA * env, 1.0)))
        fases["acomodar"] = (f0, len(borr) - 1)

    # 3. Enhebrar la cuerda nueva por el camino de B.
    s0, s1 = (m - 1) * h, (len(B) - 1) * h
    if s1 > s0 + 1e-9:
        def vel(s):
            if not libre:
                return VEL if s - s0 < LENTO else VEL_RAPIDA
            return VEL_CRUCE if cerca(s) < CERCA_CRUCE else VEL
        S_enh = _recorrido(s0, s1, vel)
        f0 = len(borr)
        n_prev = m
        for k, s in enumerate(S_enh[1:], start=1):
            fin = k == len(S_enh) - 1
            mm = len(B) if fin else max(nodos(s), m)
            # La guía mira más allá de la mano, para que el tramo que va encima ya esté
            # arriba cuando llegue la punta.
            mira = min(len(B), mm + int((ANTES_CRUCE + RAMPA) / h))
            G = B[:mira].copy()
            lift = min(1.0, k / (ARRANQUE * FPS), (len(S_enh) - 1 - k) / (ARRANQUE * FPS))
            G[mm - 1] = _en(B, h, s) + _afuera_libre(solido, B, h, s, mm) * lift
            G = con_mano(G, s, lift, mm - 1)

            def hol(a, b, sm=s, lift=lift):
                nueva = max(a, b)
                if nueva < s0 - 1e-9:
                    return 0.0, 1.0
                d = sm - nueva       # > 0: la punta ya pasó el cruce
                antes = _rampa((d + ANTES_CRUCE + RAMPA) / RAMPA)
                despues = _rampa((DESPUES_CRUCE + RAMPA - d) / RAMPA)
                return HOLGURA * lift * antes * despues, (antes if d < 0 else 1.0)

            mv = np.zeros(mira)
            mv[m:] = 1.0
            borr.append(_Borrador(G, mm, [0, mm - 1], s, s - (mm - 2) * h, mm - n_prev,
                                  mov=mv, holgura=hol, exacto=B if fin else None))
            n_prev = mm
        fases["enhebrar"] = (f0, len(borr) - 1)
    guia = _terminar(borr, h, refs_A, refs_B, plantilla)
    return Tramo(n, "punta", A, B, guia, fases)


# --------------------------------------------------------------------------
# Un tramo con el motor, comprobado
# --------------------------------------------------------------------------
LIMITE_ENCAJE = 0.3   # d: lo más lejos de la ficha que puede quedar la cuerda antes de la recta
RECTA = 0.2           # s: de donde quedó a la pose exacta de la ficha
ENCAJE = 0.4          # s


@dataclass
class Animado:
    """Los cuadros de un tramo (del paso n − 1 al n), ya comprobados."""
    n: int
    modo: str
    X: list                    # (N, 3) por cuadro; el primero es la pose de partida
    partido: dict
    quitado: dict
    fases: dict                # nombre → (primer cuadro, último)
    fallas: list
    medidas: dict
    visible: list | None = None   # en una plantilla (T21d), hasta dónde se ve la cuerda en cada cuadro (σ)


def animar_tramo(n, A, B, h, resaltado, solido=None, plantilla=None, esperada=None) -> Animado:
    """El tramo del paso n − 1 (A) al n (B) con el motor: la guía, los cuadros, el encaje, la
    recta hasta la pose exacta de B y la comprobación de todos los cuadros. `esperada` es la
    secuencia declarada de B, numerada: en un nudo libre se compara con la del último cuadro
    del motor, antes de la recta."""
    import time

    from .cruces import secuencia_obtenida
    from .fisica.atar import comprobar, encajar, recta, seguir
    t0 = time.time()
    tr = tramo(n, A, B, h, resaltado, plantilla, solido)
    c = seguir(tr.x0, tr.guia, solido)
    t_seguir = time.time() - t0
    fallas = []
    medidas = {"cuadros_guia": len(tr.guia), "esperas": c.esperas, "newton": c.newton,
               "segundos_motor": 0.0}
    enc, d = encajar(c.X[-1], B, solido, cuadros=max(1, round(ENCAJE * FPS)))
    medidas["distancia_encaje"] = d
    if d > LIMITE_ENCAJE:
        fallas.append(f"Paso {n}: después del encaje la cuerda queda a {d:.2f} d de la ficha; "
                      f"el máximo es {LIMITE_ENCAJE}.")
    if esperada is not None and plantilla is None:
        x = enc[-1]
        obtenida = secuencia_obtenida(x, h, encontrar_cruces(x, h))
        if list(obtenida) != list(esperada):
            fallas.append(f"Paso {n}: al terminar de atarlo, la secuencia es {' '.join(obtenida)} "
                          f"y la declarada, {' '.join(esperada)}.")
    from .fisica.atar import repartir_saltos
    X, partido, quitado, medio, nuevo_de = repartir_saltos(c.X, c.partido, c.quitado, c.medio)
    medidas["cuadros_repartidos"] = len(X) - len(c.X)
    n_seguir = len(X)
    X = X + enc + recta(enc[-1], B, max(1, round(RECTA * FPS)))
    fallas += [f"Paso {n}: {f}" for f in comprobar(X, solido, partido, quitado, medio)]
    fases = {nombre: (nuevo_de[f0], nuevo_de[f1]) for nombre, (f0, f1) in tr.fases.items()}
    fases["encaje"] = (n_seguir, len(X) - 1)
    medidas["segundos_motor"] = round(time.time() - t0, 1)
    medidas["segundos_seguir"] = round(t_seguir, 1)
    from .fisica.atar import SALTO, saltos
    sal = saltos(X, partido, quitado)
    medidas["salto_max"] = round(max(sal, default=0.0), 3)
    grandes = [v for v in sal if v > SALTO]
    if grandes:
        fallas.append(f"Paso {n}: en {len(grandes)} cuadros un nodo salta más de {SALTO} d (hasta "
                      f"{max(sal):.2f}).")
    return Animado(n, tr.modo, X, partido, quitado, fases, fallas, medidas)


# --------------------------------------------------------------------------
# Un nudo entero
# --------------------------------------------------------------------------
def de_plantilla(spec, n: int):
    """En un nudo de plantilla, su sólido y la tensión de atado del paso n como función
    (N, hasta) → (N,), como la arma `plantillas.pasos.construir_paso` con el motor: la del paso
    en lo atado hasta donde va la mano (sin pasar el hito del paso), más en los ahorcados, y
    nada en lo que sigue suelto sobre la mesa. Sin plantilla, (None, None)."""
    if spec.plantilla is None:
        return None, None
    from .fisica.asentar import tensiones_de_amarre
    from .libre import catmull_rom, remuestrear
    from .plantillas.pasos import _CuerdaDeAmarre, geometria
    g = geometria(spec)
    c = g.cuerda()
    paso = spec.pasos[n - 1]
    previo = spec.pasos[n - 2].hasta if n > 1 else None
    t = c.trazo(paso.hasta, previo)
    D, ctrl = catmull_rom(t.puntos)
    _, h, s_ctrl = remuestrear(D, ctrl)
    hitos = c.c.hitos if isinstance(c, _CuerdaDeAmarre) else {}
    s_hitos = {k: float(s_ctrl[i]) for k, i in hitos.items() if i <= t.fin}
    s_fin = float(s_ctrl[t.fin])
    tension = getattr(g.plantilla, "TENSION", "ajustada")

    def T(N, hasta):
        return tensiones_de_amarre(N, s_hitos, h, min(float(hasta), s_fin), tension)

    return g.solido, T


def _animar_paso(spec, n, A, B, h, resaltado, esperada) -> Animado:
    solido, plantilla = de_plantilla(spec, n)
    if solido is None and spec.plantilla is None:
        from .libre import _en_la_mesa
        solido = _en_la_mesa(spec.anfitrion, n).get("anfitrion") if spec.anfitrion else None
    return animar_tramo(n, A, B, h, resaltado, solido, plantilla, esperada)


COLA_MANO = 4.0       # d: en una plantilla, la cola que queda en la mano en cada pausa (T18)
APRETAR = 1.5         # s: el nudo terminado se aprieta en esto (T18)


@dataclass
class Pose:
    """La pose de un paso en el video: la de la ficha o, en una plantilla, la de la ficha
    hasta el hito del paso más COLA_MANO de cola en la mano (T18)."""
    n: int
    puntos: np.ndarray
    h: float
    resaltado: tuple | None
    esperada: tuple | None


def poses(modelo) -> list[Pose]:
    """Las poses de los pasos en el video. En una plantilla, la ficha deja unos 20 d de cola
    sobre la mesa en cada paso, y atarlos pedía recogerlos y volver a darlos en cada paso (27 s
    de los 94 del amarre en T17): en el video, cada pausa salvo la última muestra la cuerda hasta
    el hito, con la cola en la mano."""
    out = []
    P = modelo.pasos
    for k, r in enumerate(P):
        X = np.asarray(r.puntos, float)
        if modelo.spec.plantilla is not None and k < len(P) - 1 and r.resaltado:
            fin = int(round(r.resaltado[1] / r.h)) + int(math.ceil(COLA_MANO / r.h)) + 1
            X = X[:min(len(X), max(fin, 2))]
        out.append(Pose(r.n, X, r.h, r.resaltado, r.esperada))
    return out


def animar(spec, modelo, pasos=None) -> list[Animado]:
    """Los tramos animados de un nudo ya construido con el motor (`modelo`): del paso 1 al 2,
    del 2 al 3… (o solo los que terminan en los pasos de `pasos`), cada uno en un proceso, con
    largo fijo (T21): un nudo libre, entre las poses de `poses_video()`; una plantilla, entre las
    de `poses_plantilla()`, con la cuerda que sale de la mano (T21d)."""
    from .procesos import mapa
    if spec.plantilla is None:
        PV = poses_video(modelo)
        args = [(spec, A, B) for A, B in zip(PV[:-1], PV[1:]) if pasos is None or B.n in pasos]
        return [f.result() for f in mapa(_animar_largo_paso, args)]
    PP = poses_plantilla(modelo)
    args = [(spec, A, B) for A, B in zip(PP[:-1], PP[1:]) if pasos is None or B.n in pasos]
    return [f.result() for f in mapa(_animar_plantilla_paso, args)]


def animar_apretado(spec, modelo) -> Animado | None:
    """El nudo terminado apretándose, del último paso a `modelo.apretado`, en APRETAR s (T18).

    En un nudo libre son los pasos del modo 2 del motor (`apretar`, el mismo cálculo que da el
    apretado de la ficha), repartidos en el tiempo con arranque y frenado suaves. En una
    plantilla, el apretado de la ficha se asienta desde el trazado con la tensión «apretada», no
    desde el último paso: el video va en línea recta del último paso al apretado, que es poco
    (la tensión cambia, no el camino). En los dos, `comprobar` revisa todos los cuadros. Sin
    apretado (o igual al último paso), None."""
    from .fisica.atar import FPS as _FPS, SALTO, comprobar, saltos
    final, apretado = modelo.pasos[-1], modelo.apretado
    if apretado is None or apretado is final or len(apretado.puntos) != len(final.puntos):
        return None
    A = np.asarray(final.puntos, float)
    Z = np.asarray(apretado.puntos, float)
    if float(np.max(np.linalg.norm(Z - A, axis=1))) < 1e-6:
        return None
    solido, _ = de_plantilla(spec, final.n)
    estados = [A]
    if spec.plantilla is None:
        from .apretar import _con_motor
        tray: list = []
        paso = spec.pasos[-1]
        if _con_motor(spec, paso, final, paso.secuencia, trayectoria=tray) is None:
            raise TrazadoError("el apretado del video necesita el motor (NUDOS_MOTOR=1)")
        estados += [np.asarray(x, float) for x in tray]
        if spec.anfitrion is not None and solido is None:
            from .libre import _en_la_mesa
            solido = _en_la_mesa(spec.anfitrion, final.n).get("anfitrion")
    estados.append(Z)
    # Los estados, repartidos en APRETAR s por lo que avanzan, con arranque y frenado suaves.
    d = np.array([0.0] + [float(np.max(np.linalg.norm(b - a, axis=1)))
                          for a, b in zip(estados[:-1], estados[1:])])
    s = np.cumsum(d) / max(float(d.sum()), 1e-12)
    nf = max(2, int(round(APRETAR * _FPS)))
    X = [A]
    for u in _suave_t(nf + 1)[1:]:
        k = int(np.clip(np.searchsorted(s, u, side="right") - 1, 0, len(estados) - 2))
        t = 0.0 if s[k + 1] <= s[k] else (u - s[k]) / (s[k + 1] - s[k])
        X.append(estados[k] + float(np.clip(t, 0, 1)) * (estados[k + 1] - estados[k]))
    fallas = [f"Apretado: {f}" for f in comprobar(X, solido)]
    sal = saltos(X)
    if max(sal, default=0.0) > SALTO:
        fallas.append(f"Apretado: un nodo salta {max(sal):.2f} d de un cuadro al siguiente; "
                      f"el máximo es {SALTO}.")
    medidas = {"estados": len(estados), "salto_max": round(max(sal, default=0.0), 3),
               "distancia": round(float(np.max(np.linalg.norm(Z - A, axis=1))), 3)}
    return Animado(final.n + 1, "apretar", X, {}, {}, {"apretar": (1, len(X) - 1)}, fallas, medidas)


# ==========================================================================
# El video con largo fijo (T21)
# ==========================================================================
# Una sola cuerda para todo el video: el nodo j es siempre el mismo punto de la cuerda, σ = j·h.
# Cada pausa muestra el nudo que dibuja la ficha con un depósito de firme detrás (fuera del
# encuadre) y la cuerda de más que los pasos que siguen todavía van a usar: acostada sobre la mesa
# después de la punta, o, si ahí no cabe sin cruzar el nudo, esperando en una bolsa (un tramo
# libre de la ficha, inflado). Entre dos pausas, la mano toma la cuerda cerca de la punta y la
# lleva por el aire hasta el camino nuevo, la enhebra por él y tira de la cola; lo que todavía no
# pasó queda suelto y cuelga con su peso. Si la punta ya está en el camino nuevo, la mano tira y
# la bolsa se achica mientras la cuerda pasa (`_Cinta`).
DEPOSITO_FINAL = 0.0   # d de firme fuera del encuadre en el último paso, además de lo que el firme
                       # gana en el nudo (en el as de guía, 16,6 d al formar la gaza pequeña)
COLA_RADIO = 2.0       # d: el radio con que la cola de más dobla hacia su dirección
COLA_LIBRE = 1.5       # d: lo más cerca que la cola acostada pasa de la cuerda, vista desde arriba
COLA_JUNTO = 1.05      # d: lo que puede acercarse en su comienzo, junto a la punta de la ficha
COLA_ARRANQUE = 2.0    # d: lo que tarda en apartarse hasta COLA_LIBRE
TOL_FICHA = 0.02       # d: el tramo de la ficha, a esto de la ficha (fuera de la bolsa)
# La bolsa (T21c). Antes, la cola que no cabía en la mesa subía en arco fuera del cuadro: en el
# paso 3 del as de guía, 25 d en diagonal sobre el nudo (Gabriel, 27 nov).
BOLSA_MARGEN = 0.75    # d: la bolsa empieza y termina a esto de un cruce, que no se mueve
BOLSA_PUNTA = 3.0      # d: y a esto de la punta de la ficha, que queda como la dibuja la ficha
BOLSA_RAMPA = 3.0      # d: lo que puede meterse en la cuerda que el paso no movió (la del paso
                       # anterior): la bolsa se llena con la cuerda que la punta trae
BOLSA_MIN = 4.0        # d: el tramo libre más corto que puede hacer de bolsa
BOLSA_VECINOS = 2.0    # d: lo que sigue a la bolsa a lo largo de la cuerda no cuenta para su holgura
COINCIDE = 0.25        # d: los pasos de un grupo comparten la bolsa donde quedan a menos de esto
TOL_CINTA = 0.3        # d: la punta de A está en el camino de B, vista desde arriba,
ALTO_CINTA = 1.0       # y a lo sumo esto más alta o más baja: en el paso 6 del as de guía la punta
                       # descansa en la mesa y el paso 7 pasa por ahí sobre un cruce (0,67 d más
                       # alto sin el motor); la mano la levanta al arrancar
PINZA = 1.5            # d: la mano toma la cuerda a esto de la punta, así que la punta se ve
PUNTA_GUIA = 2.0       # d: lo que lleva la mano, desde la punta
ENTRADA = 2.5          # d: la punta entra al camino nuevo esto antes de su primer cruce nuevo
ENTRADA_MIN = 1.5      # d: y al menos esto después de donde el paso se separa del anterior
MEZCLA = 2.0           # d: lo que tarda el aire en juntarse con el camino a la entrada
VEL_AIRE = 10.0        # d/s: la mano que trae la punta por el aire (no enseña nada: rápido)
VEL_TIRAR = 10.0       # d/s: la mano que tira de la cola, ya enhebrada
SUAVIZAR = 2.5         # d: los cambios de velocidad de la mano se reparten en esto (dos veces);
                       # con 1 d, la punta llegaba a frenar 80 d/s² al pasar de 10 a 2,5 d/s
ARRANQUE_LARGO = 0.5   # s: lo que tardan el arranque y el frenado (de quinto grado)
VISC_LIBRE = 0.0       # N·s/d: el aire casi no frena la cuerda suelta, que cuelga y cae
FLOJO = 3.0            # d: con menos cuerda por pasar, la de la entrada vuelve a su lugar
ENTRA = 1.0            # d: lo que tarda en entrar el resorte de la cuerda que pasa la entrada
ASENTAR = 0.4          # s: al final, los resortes suben hasta RESORTE_FIN
RESORTE_FIN = 50.0     # N/d
ACERCAR_FIN = 0.15     # s: de donde quedó la cuerda a la pose exacta
LIMITE_FIN = 0.3       # d: lo más lejos de la pose que puede quedar antes de acercarla


def _suave5(x):
    """El paso de quinto grado: velocidad y aceleración nulas en las dos puntas."""
    x = np.clip(x, 0.0, 1.0)
    return x ** 3 * (x * (6 * x - 15) + 10)


def _integral5(x):
    """La integral de `_suave5` desde 0 (vale 1/2 en 1)."""
    x = np.clip(x, 0.0, 1.0)
    return x ** 4 * (x * (x - 3) + 2.5)


@dataclass
class PoseVideo:
    """La pose de un paso en el video con largo fijo (T21b). La cuerda entera X (N, 3) mide lo
    mismo en todos los pasos: el depósito de firme (σ < o), el tramo que dibuja la ficha (de o a
    `fin`, la ficha remuestreada) y la cola de más acostada (después de `fin`). Si la cola no cabe
    en la mesa, no hay cola: la cuerda de más espera en la bolsa, dentro del tramo de la ficha, y
    `mapa` dice dónde queda en el video cada punto de la ficha (T21c)."""
    n: int
    X: np.ndarray
    h: float
    o: float
    largo: float               # el de la ficha
    cola: float                # la cola acostada después de la punta de la ficha
    ficha: np.ndarray
    h_ficha: float
    resaltado: tuple | None    # en σ
    esperada: tuple | None
    modo: str | None = None    # cómo se llega desde la pose anterior: «punta» o «firme»
    r1: int | None = None      # en «punta», el primer nodo de la ficha que cambia
    bolsa: tuple | None = None         # (a, b, sobra): la bolsa en σ y la cuerda de más que guarda
    bolsa_ficha: tuple | None = None   # (a, b): la misma, en σ de la ficha
    enhebra: bool = True               # en «punta», si la punta pasa por algún cruce nuevo
    mapa: tuple | None = None          # (s de la ficha, σ): sin bolsa, σ = o + s
    visible: float | None = None       # en una plantilla (T21d), hasta dónde se ve la cuerda (σ): lo
                                       # de después está todavía en la mano

    @property
    def puntos(self) -> np.ndarray:
        return self.X

    def en_video(self, s: float) -> float:
        """El σ del video del punto de la ficha a s de su comienzo."""
        if self.mapa is None:
            return self.o + float(s)
        return float(np.interp(s, self.mapa[0], self.mapa[1]))

    @property
    def fin(self) -> float:
        """El σ de la punta de la ficha."""
        return self.en_video(self.largo)

    def tramo_ficha(self) -> tuple[int, int]:
        """El primer y el último nodo dentro del tramo de la ficha."""
        a = int(math.ceil(self.o / self.h - 1e-9))
        b = min(len(self.X) - 1, int(math.floor(self.fin / self.h + 1e-9)))
        return a, b


def _direccion(X, h, punta: bool, largo: float = 0.6) -> np.ndarray:
    """La dirección (vista desde arriba) con que sale la cuerda por la punta o por el firme."""
    m = max(1, min(len(X) - 1, int(round(largo / h))))
    d = (X[-1] - X[-1 - m]) if punta else (X[0] - X[m])
    d = np.asarray(d[:2], float)
    return d / max(float(np.linalg.norm(d)), 1e-12)


def _camino_cola(p0, t0, largo: float, giro: float, radio: float = COLA_RADIO, paso: float = 0.05):
    """Una cola sobre la mesa desde p0 con la dirección t0: dobla `giro` radianes con `radio` y
    sigue recta. Da los puntos (M, 2) y su largo desde p0."""
    u = np.arange(0.0, largo + paso, paso)
    izq = np.array([-t0[1], t0[0]]) * (1.0 if giro >= 0 else -1.0)
    a_fin = abs(giro)
    arco = a_fin * radio
    a = np.minimum(u, arco) / radio
    pts = p0 + radio * (np.sin(a)[:, None] * t0 + (1 - np.cos(a))[:, None] * izq)
    d = math.cos(a_fin) * t0 + math.sin(a_fin) * izq
    recto = u > arco
    pts[recto] += (u[recto] - arco)[:, None] * d
    return pts, u


def _cola(Xf, hf, largo: float, otros):
    """La cola de más que sale de la punta de la ficha Xf, con la dirección de su último tramo,
    acostada sobre la mesa en la primera dirección (seguir derecho, o doblar de a 15° a un lado y
    al otro) que, vista desde arriba, no pasa a menos de COLA_LIBRE de la cuerda. Da los puntos
    (M, 3) y su largo desde la punta (en el espacio), o None si no cabe en ninguna: entonces la
    cuerda de más espera en una bolsa (`_bolsas`)."""
    from scipy.spatial import cKDTree
    p0, t0, z0 = Xf[-1, :2], _direccion(Xf, hf, True, largo=hf), float(Xf[-1, 2])
    # La pendiente con que llega la punta (la que baja de un cruce): la cola la sigue, sin codo.
    pend0 = float((Xf[-1, 2] - Xf[-2, 2]) / max(np.linalg.norm(Xf[-1, :2] - Xf[-2, :2]), 1e-9))
    # La altura a la que descansa la cuerda suelta sobre la mesa (con el motor, unos 0,55 d: el
    # contacto con la mesa equilibra su peso), la de lo que la ficha tiene apoyado. Con 0,5, al
    # soltar la cola el contacto la subía a 0,6 en un cuadro y volvía a bajar.
    sobre_mesa = Xf[Xf[:, 2] < 0.6, 2]
    apoyo = float(np.clip(np.median(sobre_mesa), 0.5, 0.6)) if len(sobre_mesa) else 0.5
    lejos = int(round(3.0 / hf))
    duros = [Xf[:max(0, len(Xf) - 1 - lejos)]] + [np.asarray(o, float) for o in otros if len(o)]
    duros = np.vstack(duros)
    giros = [0.0] + [s * math.radians(a) for a in range(15, 181, 15) for s in (1.0, -1.0)]

    def a_la_mesa(u):
        """La altura de la cola acostada: sale con la pendiente de la punta y se apoya en la
        mesa (una cúbica de Hermite)."""
        if abs(z0 - apoyo) < 1e-6 and abs(pend0) < 1e-6:
            return np.full(len(u), apoyo)
        Ld = max(0.4, 2.0 * abs(z0 - apoyo) / max(abs(pend0), 0.5))
        t = np.clip(u / Ld, 0.0, 1.0)
        z = ((2 * t ** 3 - 3 * t ** 2 + 1) * z0 + (t ** 3 - 2 * t ** 2 + t) * pend0 * Ld
             + (-2 * t ** 3 + 3 * t ** 2) * apoyo)
        return np.maximum(z, apoyo)    # nunca más abajo de donde descansa

    plano = cKDTree(duros[:, :2]) if len(duros) else None
    for g in giros:
        pts, u = _camino_cola(p0, t0, largo, g)
        pide = COLA_JUNTO + (COLA_LIBRE - COLA_JUNTO) * np.clip(u / COLA_ARRANQUE, 0, 1)
        if plano is None or np.all(plano.query(pts)[0] >= pide):
            P = np.column_stack([pts, a_la_mesa(u)])
            return P, _largos_acum(P)
    return None


def _largos_acum(P) -> np.ndarray:
    """El largo de la polilínea P desde su comienzo hasta cada punto."""
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])


def _uniforme(P, M: int) -> np.ndarray:
    """La polilínea P en M puntos repartidos igual a lo largo de ella."""
    l = _largos_acum(P)
    u = np.linspace(0.0, l[-1], M)
    return np.column_stack([np.interp(u, l, P[:, i]) for i in range(P.shape[1])])


# --------------------------------------------------------------------------
# La bolsa: la cuerda de más que no cabe acostada después de la punta (T21c)
# --------------------------------------------------------------------------
def _tramos_libres(Xf, hf) -> list[tuple[float, float, bool]]:
    """Los tramos de la ficha entre dos cruces seguidos a lo largo de la cuerda y el del último
    cruce a la punta (en σ de la ficha, y si llega a la punta), del más cercano a la punta al más
    lejano. El firme, antes del primer cruce, no cuenta: la cuerda que esperara ahí tendría que
    pasar por todo el nudo."""
    cruces = encontrar_cruces(np.asarray(Xf, float), hf)
    if not cruces:
        return []
    L = (len(Xf) - 1) * hf
    s = sorted({float(v) for c in cruces for v in (c.sa, c.sb)})
    tramos = [(a, b, False) for a, b in zip(s[:-1], s[1:])] + [(s[-1], L, True)]
    return tramos[::-1]


def _tramo_fino(Xf, hf, a: float, b: float, paso: float):
    """Los puntos de la ficha de a a b (en σ de la ficha), cada `paso` de σ, y su σ."""
    sf = np.append(np.arange(a, b, paso), b)
    return np.array([_en(Xf, hf, s) for s in sf]), sf


def _inflar(P, sobra: float) -> np.ndarray | None:
    """El tramo P (M, 3) de la ficha, inflado para que mida `sobra` más con las mismas puntas y
    la misma dirección en ellas, como queda una cuerda floja: cada trocito se alarga igual (salvo
    junto a las puntas), la cuerda gira lo mismo que en la ficha pero más despacio y un giro de
    más, ψ(t) = Σ a_k sen(kπt), la trae de vuelta a su punta doblando lo menos posible (la suma de
    la curvatura al cuadrado, como una elástica: Newton con la condición de la punta). La gaza
    grande del as de guía sale como una gota más honda y la vuelta del collar, como una lengua.
    La altura de cada punto es la de la ficha. None si no se cierra."""
    P = np.asarray(P, float)
    d = np.diff(P[:, :2], axis=0)
    l = np.linalg.norm(d, axis=1)
    th = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    # P va cada un cuarto de nodo de la ficha, que dobla solo en sus nodos: estirada, la cuerda
    # quedaba con codos cada nodo (y el radio de la lengua del collar, en 1,13 y no en 1,6). El
    # giro, repartido en un tramo de la ficha.
    th = np.convolve(np.pad(th, (2, 1), mode="edge"), np.ones(4) / 4, mode="valid")
    s = np.concatenate([[0.0], np.cumsum(l)])
    medio = (s[:-1] + s[1:]) / 2
    Lp = float(s[-1])
    # Lo que está junto a las puntas (a 1 d) no se alarga: el tramo sale de la ficha como ella.
    w = _suave5(np.minimum(medio, Lp - medio) / min(1.0, Lp / 4))
    if w.sum() <= 1e-12:
        return None
    w = w / w.sum()
    pa, pb = P[0, :2], P[-1, :2]
    K = 8
    k = np.arange(1, K + 1)
    meta = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))) + sobra
    extra = sobra
    a = np.zeros(K)
    Y = None
    for _ in range(4):          # el largo se mide en el espacio: se corrige lo que suben los cruces
        ell = l + extra * w
        t = (np.cumsum(ell) - ell / 2) / float(ell.sum())
        base = np.sin(np.pi * np.outer(t, k))           # (M − 1, K)
        Bd = np.diff(base, axis=0)
        dth = np.diff(th)
        lm = (ell[:-1] + ell[1:]) / 2
        H = 2 * Bd.T @ (Bd / lm[:, None]) + 1e-9 * np.eye(K)
        for _ in range(100):
            ang = th + base @ a
            c, sn = np.cos(ang), np.sin(ang)
            r = pa + np.array([np.sum(ell * c), np.sum(ell * sn)]) - pb
            g = 2 * Bd.T @ ((dth + Bd @ a) / lm)
            J = np.vstack([-(ell * sn) @ base, (ell * c) @ base])   # (2, K)
            # El paso de Newton de la energía con la punta en su lugar (KKT).
            M = np.block([[H, J.T], [J, np.zeros((2, 2))]])
            try:
                sol = np.linalg.solve(M, np.concatenate([-g, -r]))
            except np.linalg.LinAlgError:
                return None
            paso_a = sol[:K]
            n = float(np.linalg.norm(paso_a))
            if n > 0.5:
                paso_a *= 0.5 / n
            a = a + paso_a
            if float(np.linalg.norm(r)) < 1e-7 and n < 1e-6:
                break
        ang = th + base @ a
        r = pa + np.array([np.sum(ell * np.cos(ang)), np.sum(ell * np.sin(ang))]) - pb
        if float(np.linalg.norm(r)) > 1e-5:
            return None
        Y = np.empty_like(P)
        Y[0, :2] = pa
        Y[1:, :2] = pa + np.cumsum(ell[:, None] * np.column_stack([np.cos(ang), np.sin(ang)]), axis=0)
        Y[:, 2] = P[:, 2]
        Y[-1, :2] = pb
        actual = float(np.sum(np.linalg.norm(np.diff(Y, axis=0), axis=1)))
        if abs(actual - meta) < 1e-4:
            break
        extra += meta - actual
    return Y


def _bolsa_cabe(Y, P, resto, h: float) -> float | None:
    """Si el tramo inflado Y (del tramo P de la ficha) dobla como mucho tan cerrado como P o
    RADIO_GUIA, y si, visto desde arriba, no se acerca al resto de la cuerda ni a sí mismo (lejos
    a lo largo de él) más que COLA_LIBRE o que lo que ya se acercaba P."""
    from scipy.spatial import cKDTree
    if radio_minimo(_por_largo(Y, h)[0]) < min(RADIO_GUIA, radio_minimo(_por_largo(P, h)[0])) - 1e-6:
        return False
    if len(resto):
        arbol = cKDTree(np.asarray(resto, float)[:, :2])
        dY, dP = arbol.query(Y[:, :2])[0], arbol.query(P[:, :2])[0]
        if np.any(dY < np.minimum(COLA_LIBRE, dP) - 0.01):
            return False
    k = max(1, len(Y) // 300)
    Ys, Ps = Y[::k, :2], P[::k, :2]
    l = _largos_acum(Y[::k])
    lejos = np.abs(l[:, None] - l[None, :]) > max(4.0, math.pi * COLA_LIBRE)
    if lejos.any():
        dY = np.linalg.norm(Ys[:, None] - Ys[None], axis=2)[lejos]
        dP = np.linalg.norm(Ps[:, None] - Ps[None], axis=2)[lejos]
        if np.any(dY < np.minimum(COLA_LIBRE, dP) - 0.01):
            return False
    return True


def _en_comun(g, A0: float, B0: float, Xf, hf, o, L) -> tuple[float, float]:
    """El tramo más largo de [A0, B0] (σ del video, sin bolsa) donde todos los pasos del grupo g
    tienen la cuerda en el mismo lugar (a menos de COINCIDE)."""
    if len(g) < 2 or B0 <= A0:
        return A0, B0
    s = np.append(np.arange(A0, B0, 0.1), B0)
    ok = np.ones(len(s), bool)
    for j, k in zip(g[:-1], g[1:]):
        for i, x in enumerate(s):
            sj, sk = x - o[j], x - o[k]
            if not (0.0 <= sj <= L[j] and 0.0 <= sk <= L[k]):
                ok[i] = False
            elif np.linalg.norm(_en(Xf[j], hf[j], sj) - _en(Xf[k], hf[k], sk)) > COINCIDE:
                ok[i] = False
    mejor, i = (A0, A0), 0
    while i < len(s):
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(s) and ok[j + 1]:
            j += 1
        if s[j] - s[i] > mejor[1] - mejor[0]:
            mejor = (float(s[i]), float(s[j]))
        i = j + 1
    return mejor


def _bolsas(g, Xf, hf, o, L, cola, dep, h, desde: float = -math.inf) -> dict:
    """La bolsa del grupo de pasos g, que se siguen sin que la punta pase por un cruce nuevo (así
    que la cuerda de más no puede cambiar de lugar): el mismo tramo de cuerda en todos, el tramo
    libre más cercano a la punta del último paso que todos comparten, que empieza después de
    `desde` (σ del video sin bolsa: la cuerda de más llega con la punta, así que va en lo que el
    primer paso del grupo tiende) y donde la bolsa cabe (`_inflar`, `_bolsa_cabe`). Da, por paso
    con cuerda de más, (a, b, Y, sf): la bolsa en σ de la ficha, el tramo inflado y su σ de la
    ficha."""
    k1 = g[-1]
    con = [k for k in g if cola[k] > 1e-9]
    for a, b, a_punta in _tramos_libres(Xf[k1], hf[k1]):
        A0 = max(o[k1] + a + BOLSA_MARGEN, desde)
        B0 = o[k1] + b - (BOLSA_PUNTA if a_punta else BOLSA_MARGEN)
        A0, B0 = _en_comun(g, A0, B0, Xf, hf, o, L)
        if B0 - A0 < BOLSA_MIN:
            continue
        res = {}
        for k in con:
            a_f, b_f = A0 - o[k], B0 - o[k]
            P, sf = _tramo_fino(Xf[k], hf[k], a_f, b_f, hf[k1] / 4)
            Y = _inflar(P, cola[k])
            if Y is None:
                break
            s_f = np.arange(len(Xf[k])) * hf[k]
            cerca = (s_f >= a_f - BOLSA_VECINOS) & (s_f <= b_f + BOLSA_VECINOS)
            resto = np.vstack([Xf[k][~cerca]] + ([dep[k]] if len(dep[k]) else []))
            if not _bolsa_cabe(Y, P, resto, h):
                break
            res[k] = (a_f, b_f, Y, sf)
        else:
            return res
    raise TrazadoError("la cuerda de más no cabe acostada después de la punta ni en una bolsa")


def _deposito(Xf, hf, o: float, N: int, h: float) -> np.ndarray:
    """El firme que sigue derecho detrás del de la ficha, fuera del encuadre (σ < o)."""
    sig = np.arange(N) * h
    sig = sig[sig < o - 1e-9]
    d = _direccion(Xf, hf, False, largo=hf)
    X = np.empty((len(sig), 3))
    X[:, :2] = Xf[0, :2] + (o - sig)[:, None] * d
    X[:, 2] = Xf[0, 2]
    return X


def _pose_video(Xf, hf, o, largo, cola, N, h, bolsa=None):
    """La cuerda del video de una pose: el depósito sigue derecho al firme de la ficha, la ficha
    va remuestreada en la grilla del video y la cola sale de su punta, acostada (`_cola`). Con
    `bolsa` (a, b, Y, sf), no hay cola: el tramo de a a b de la ficha va inflado (Y, en los puntos
    sf de la ficha) y mide `cola` más. Da la cuerda y el mapa σ de la ficha → σ (None sin
    bolsa)."""
    sig = np.arange(N) * h
    X = np.empty((N, 3))
    dep = sig < o - 1e-9
    X[dep] = _deposito(Xf, hf, o, N, h)
    mapa = None
    fin = o + largo
    if bolsa is not None:
        a, b, Y, sf = bolsa
        l = _largos_acum(Y)
        sv = o + a + (b - a + cola) * l / l[-1]
        mapa = (np.concatenate([[0.0], sf, [largo]]),
                np.concatenate([[o], sv, [o + largo + cola]]))
        fin = o + largo + cola
    co = sig > fin + 1e-9
    for j in np.flatnonzero(~dep & ~co):
        if mapa is None:
            X[j] = _en(Xf, hf, sig[j] - o)
            continue
        s = float(np.interp(sig[j], mapa[1], mapa[0]))
        if a <= s <= b:
            X[j] = [np.interp(s, sf, Y[:, i]) for i in range(3)]
        else:
            X[j] = _en(Xf, hf, s)
    if co.any():
        C = _cola(Xf, hf, cola + h, [X[dep]])
        if C is None:
            raise TrazadoError("la cola de más no cabe acostada")
        C, l = C
        uu = sig[co] - fin
        for i in range(3):
            X[co, i] = np.interp(uu, l, C[:, i])
    return X, mapa


def _enhebra(Xf, hf, r1) -> bool:
    """Si en el paso, que sigue al anterior hasta su nodo r1 de la ficha, la punta pasa por algún
    cruce nuevo."""
    s0 = (r1 - 1) * hf
    return any(max(c.sa, c.sb) >= s0 - hf for c in encontrar_cruces(Xf, hf))


def poses_video(modelo) -> list[PoseVideo]:
    """Las poses de los pasos en el video con largo fijo (T21b), de un nudo libre (con o sin
    anfitrión). El depósito R es lo que el firme gana en todo el nudo (los pasos «firme» de
    `alinear`), y la cuerda mide lo que el paso más largo necesita con lo que todavía le falta al
    firme: en el as de guía, el último paso, 109,8 d (550 nodos), con 22,1, 22,1, 25,1, 22,9,
    14,8, 7,1 y 0 d de más.

    La cuerda de más va acostada después de la punta si cabe sin cruzar el nudo. Si no, espera en
    una bolsa (T21c), y también en los pasos de antes a los que se llega sin que la punta pase por
    un cruce nuevo: ahí no hay por dónde tirar de ella. En el as de guía, la gaza grande de los
    pasos 1 a 3 (que se achica al subir el chicote por la gaza pequeña en el paso 4) y la vuelta
    del chicote alrededor del firme en el paso 6 (que se aprieta al bajarlo en el 7)."""
    spec = modelo.spec
    if spec.plantilla is not None:
        raise ValueError("una plantilla ata con `poses_plantilla` (T21d)")
    P = modelo.pasos
    h = float(P[-1].h)
    L = [(len(r.puntos) - 1) * float(r.h) for r in P]
    Xf = [np.asarray(r.puntos, float) for r in P]
    hf = [float(r.h) for r in P]
    modos, r1s, gan, enhebra = [None], [None], [0.0], [True]
    for k in range(1, len(P)):
        r = int(round(P[k].resaltado[0] / P[k].h)) if P[k].resaltado else 0
        modo, valor = alinear(Xf[k - 1], Xf[k], r)
        modos.append(modo)
        r1s.append(int(valor) if modo == "punta" else None)
        gan.append(gan[-1] + (L[k] - L[k - 1] if modo == "firme" else 0.0))
        enhebra.append(modo == "punta" and _enhebra(Xf[k], hf[k], int(valor)))
    G = gan[-1]
    N = int(round((DEPOSITO_FINAL + max(L[k] + G - gan[k] for k in range(len(P)))) / h)) + 1
    total = (N - 1) * h
    o = [DEPOSITO_FINAL + G - gan[k] for k in range(len(P))]
    cola = [max(0.0, total - o[k] - L[k]) for k in range(len(P))]
    dep = [_deposito(Xf[k], hf[k], o[k], N, h) for k in range(len(P))]
    acostada = [cola[k] <= 1e-9 or _cola(Xf[k], hf[k], cola[k] + h, [dep[k]]) is not None
                for k in range(len(P))]
    grupos, g = [], []
    for k in range(len(P)):
        if enhebra[k] and g:
            grupos.append(g)
            g = []
        g.append(k)
    grupos.append(g)
    bolsas = {}
    for g in grupos:
        if all(acostada[k] for k in g):
            continue
        k0 = g[0]
        desde = (o[k0] + (r1s[k0] - 1) * hf[k0] - BOLSA_RAMPA if k0 > 0 and enhebra[k0]
                 else -math.inf)
        try:
            bolsas.update(_bolsas(g, Xf, hf, o, L, cola, dep, h, desde))
        except TrazadoError as e:
            raise TrazadoError(f"Pasos {', '.join(str(P[k].n) for k in g)}: {e}") from e
    out = []
    for k, r in enumerate(P):
        b = bolsas.get(k)
        try:
            X, mapa = _pose_video(Xf[k], hf[k], o[k], L[k], cola[k], N, h, b)
        except TrazadoError as e:
            raise TrazadoError(f"Paso {r.n}: {e}") from e
        p = PoseVideo(r.n, X, h, o[k], L[k], 0.0 if b else cola[k], Xf[k], hf[k], None, r.esperada,
                      modos[k], r1s[k], mapa=mapa, enhebra=enhebra[k])
        if b:
            p.bolsa = (p.en_video(b[0]), p.en_video(b[1]), cola[k])
            p.bolsa_ficha = (b[0], b[1])
        if r.resaltado:
            # Si la ficha resalta hasta su punta, el video resalta hasta la de la cuerda: la cola
            # acostada es el mismo chicote, y es la punta la que va adelante al enhebrar (en el
            # paso 4 del as de guía, lo resaltado iba detrás, por el fondo de la gaza grande).
            fin = total if r.resaltado[1] >= L[k] - hf[k] else p.en_video(r.resaltado[1])
            p.resaltado = (p.en_video(r.resaltado[0]), fin)
        out.append(p)
    return out


def poses_atado(modelo) -> list:
    """Las poses de las pausas del video, entre las que se ata, con largo fijo (T21): las de
    `poses_video` en un nudo libre y las de `poses_plantilla` en una plantilla (T21d)."""
    return poses_plantilla(modelo) if modelo.spec.plantilla is not None else poses_video(modelo)


def _distancia_a(P, Q) -> float:
    """Lo más lejos que queda un punto de P de la polilínea Q."""
    P, Q = np.asarray(P, float), np.asarray(Q, float)
    a, ab = Q[:-1], np.diff(Q, axis=0)
    L2 = np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-18)
    peor = 0.0
    for i in range(0, len(P), 128):
        p = P[i:i + 128]
        t = np.clip(np.einsum("pij,ij->pi", p[:, None, :] - a[None], ab) / L2, 0.0, 1.0)
        d = np.linalg.norm(p[:, None, :] - (a[None] + t[..., None] * ab[None]), axis=2).min(axis=1)
        peor = max(peor, float(d.max()))
    return peor


def comprobar_poses(poses: list[PoseVideo], solido=None) -> list[str]:
    """Las fallas de las poses del video: otra cantidad de nodos, el tramo de la ficha (fuera de
    la bolsa) a más de TOL_FICHA de ella, otros cruces que los de la ficha en ese tramo (la bolsa
    no cruza nada), la cola o el depósito que pasan por debajo de la cuerda (lo agregado solo pasa
    por encima) o un par a menos de dmin."""
    from .fisica.asentar import contacto
    fallas = []
    N = len(poses[0].X)
    for p in poses:
        X, h = p.X, p.h
        if len(X) != N:
            fallas.append(f"Paso {p.n}: la cuerda tiene {len(X)} nodos y no {N}.")
            continue
        a, b = p.tramo_ficha()
        F = p.ficha
        if p.bolsa_ficha is not None:
            s_f = np.arange(len(F)) * p.h_ficha
            F = F[(s_f < p.bolsa_ficha[0] - 1e-9) | (s_f > p.bolsa_ficha[1] + 1e-9)]
        d = _distancia_a(F, X[max(0, a - 1):b + 2])
        if d > TOL_FICHA:
            fallas.append(f"Paso {p.n}: el tramo de la ficha queda a {d:.3f} d de ella.")
        n_v = len(encontrar_cruces(X[a:b + 1], h))
        n_f = len(encontrar_cruces(p.ficha, p.h_ficha))
        if n_v != n_f:
            fallas.append(f"Paso {p.n}: el tramo de la ficha tiene {n_v} cruces en el video y {n_f} "
                          "en la ficha.")
        s = np.arange(N) * h
        lo, hi = p.o - 1e-6, p.fin + 1e-6
        for c in encontrar_cruces(X, h):
            en_a, en_b = lo <= c.sa <= hi, lo <= c.sb <= hi
            if en_a and en_b:
                continue
            za, zb = np.interp(c.sa, s, X[:, 2]), np.interp(c.sb, s, X[:, 2])
            if en_a == en_b or (zb > za) != en_a:
                fallas.append(f"Paso {p.n}: lo agregado a la ficha pasa por debajo en "
                              f"{c.sa:.1f} y {c.sb:.1f} d.")
        malla = contacto(X, np.array([0, N]), [1.0], solido)
        m = malla.margen(X)
        if m < -1e-9:
            fallas.append(f"Paso {p.n}: dos tramos quedan a {m + malla.dmin:.3f} d, menos de dmin.")
    return fallas


# --------------------------------------------------------------------------
# El tiempo de la mano
# --------------------------------------------------------------------------
def _recorrido_largo(u0: float, u1: float, vel) -> np.ndarray:
    """Las posiciones de la mano a lo largo de su camino en cada cuadro, de u0 a u1, con la
    velocidad `vel(u)` suavizada (dos promedios de SUAVIZAR d) y un arranque y un frenado de
    quinto grado: la velocidad y la aceleración son continuas, sin cambios en seco (T21)."""
    if u1 - u0 < 1e-9:
        return np.array([u1])
    paso = 0.02
    u = np.append(np.arange(u0, u1, paso), u1)
    v = np.array([vel(x) for x in u], float)
    k = max(1, int(round(SUAVIZAR / paso)))
    for _ in range(2):
        v = np.convolve(np.pad(v, (k // 2, k - 1 - k // 2), mode="edge"), np.ones(k) / k, mode="valid")
    return _al_tiempo(u, v)


def _al_tiempo(u, v, x=None) -> np.ndarray:
    """Las posiciones de la mano en cada cuadro por los puntos u de su camino, con la velocidad v
    en cada uno, y un arranque y un frenado de quinto grado de ARRANQUE_LARGO. Con `x`, v es la
    velocidad a lo largo de x (el largo de verdad del camino en cada punto) y no de u."""
    x = u if x is None else x
    tau = np.concatenate([[0.0], np.cumsum(np.diff(x) / ((v[:-1] + v[1:]) / 2))])
    Tc = float(tau[-1])
    Ta = min(ARRANQUE_LARGO, Tc)
    T = Tc + Ta
    n = max(2, int(math.ceil(T * FPS - 1e-9)) + 1)
    t = np.linspace(0.0, T, n)
    W = np.empty(n)
    ini, fin = t < Ta, t > T - Ta
    med = ~ini & ~fin
    W[ini] = Ta * _integral5(t[ini] / Ta)
    W[med] = Ta / 2 + (t[med] - Ta)
    W[fin] = Tc - Ta * _integral5((T - t[fin]) / Ta)
    return np.interp(W, tau, u)


# --------------------------------------------------------------------------
# La guía con largo fijo
# --------------------------------------------------------------------------
def _hermite(p0, p1, m0, m1, n: int = 60) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n)[:, None]
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * p0 + (t ** 3 - 2 * t ** 2 + t) * m0
            + (-2 * t ** 3 + 3 * t ** 2) * p1 + (t ** 3 - t ** 2) * m1)


def _por_largo(P, paso: float = 0.05):
    """La curva P remuestreada cada `paso` a lo largo de ella, con su largo en cada punto."""
    l = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    u = np.append(np.arange(0.0, l[-1], paso), l[-1])
    return np.column_stack([np.interp(u, l, P[:, i]) for i in range(3)]), u


def _aire(p0, t0, p1, t1, alto: float) -> np.ndarray:
    """El camino de la punta por el aire: sale de p0 con la dirección t0 y subiendo, pasa a
    `alto` sobre la mesa a mitad de camino y llega a p1 horizontal, con la dirección t1."""
    pm = (np.asarray(p0, float) + p1) / 2
    pm[2] = alto
    escala = max(float(np.linalg.norm((p1 - p0)[:2])), 2.0)
    m0 = np.r_[0.5 * t0[:2], 1.0]
    m0 = m0 / np.linalg.norm(m0) * 0.6 * escala
    horiz = np.r_[(p1 - p0)[:2], 0.0]
    nh = float(np.linalg.norm(horiz))
    horiz = horiz / nh if nh > 1e-9 else np.r_[t1[:2], 0.0]
    mm = horiz * 0.8 * escala
    m1 = np.r_[t1[:2], 0.0] * 0.6 * escala
    a, b = _hermite(p0, pm, m0, mm), _hermite(pm, p1, mm, m1)
    return np.vstack([a, b[1:]])


def _suelto_y_visc(k, manos):
    """Cuánto va suelto cada nodo (0 a 1) y su viscosidad, según su resorte: lo suelto (sin
    resorte) lleva su propia memoria (`seguir`) y casi no tiene roce con el aire; lo que la guía
    lleva, como en T17. La memoria suelta se extiende un nodo a cada lado de lo suelto, donde la
    curvatura de la guía no sirve."""
    w = np.clip(np.asarray(k, float) / RESORTE, 0.0, 1.0)
    w[np.asarray(manos, int)] = 1.0
    p = 1.0 - w
    p = np.maximum.reduce([p, np.r_[p[1:], 0.0], np.r_[0.0, p[:-1]]])
    return p, VISC_LIBRE + (VISCOSIDAD_GUIA - VISC_LIBRE) * w


def _curvatura_segura(G) -> np.ndarray:
    """`Varilla.curvatura_de`, con cero donde la guía tiene dos puntos juntos (un nodo suelto
    puede tener su lugar de llegada justo donde está el que ya pasó la entrada)."""
    G = np.asarray(G, float)
    e, f = G[1:-1] - G[:-2], G[2:] - G[1:-1]
    D = np.linalg.norm(e, axis=1) * np.linalg.norm(f, axis=1) + np.einsum("ij,ij->i", e, f)
    out = np.zeros((len(G) - 2, 3))
    ok = D > 1e-9
    out[ok] = 2 * np.cross(e[ok], f[ok]) / D[ok, None]
    return out


def _cuadro_largo(G, h, k, manos, suelto=True, largos=None) -> CuadroGuia:
    N = len(G)
    k, curvatura = _aflojar(G, h, np.asarray(k, float), _curvatura_segura(G))
    if suelto:
        p, visc = _suelto_y_visc(k, manos)
    else:
        p, visc = None, None
    largos = np.full(N - 1, float(h)) if largos is None else np.asarray(largos, float)
    return CuadroGuia(G=G, k=k, manos=np.asarray(manos, int), largos=largos,
                      curvatura=curvatura, largo_fijo=True, viscosidad=visc, suelto=p)


def _largos_de(A: PoseVideo, B: PoseVideo, w: float) -> np.ndarray:
    """Los largos de reposo de un cuadro del tramo de A a B: los de cada tramo de A, que van
    hacia los de B. En las fichas del motor la cuerda queda un 0,1 % más corta que h (está
    asentada), y la cola de más mide h: con h de reposo, al soltarse la cola, lo guiado la
    empujaba a lo largo y la cola saltaba 0,33 d en un cuadro."""
    LA = np.linalg.norm(np.diff(A.X, axis=0), axis=1)
    LB = np.linalg.norm(np.diff(B.X, axis=0), axis=1)
    return LA + w * (LB - LA)


def _asentado(A: PoseVideo, B: PoseVideo) -> list[CuadroGuia]:
    """El final de cada tramo: la guía en la pose de llegada y los resortes subiendo hasta
    RESORTE_FIN en ASENTAR s (reemplaza a `encajar`). La mano ya soltó."""
    out = []
    nA = max(1, int(round(ASENTAR * FPS)))
    largos = _largos_de(A, B, 1.0)
    for i in range(1, nA + 1):
        kk = RESORTE + (RESORTE_FIN - RESORTE) * (i / nA) ** 2
        out.append(_cuadro_largo(B.X.copy(), B.h, np.full(len(B.X), kk), [0], suelto=False,
                                 largos=largos))
    return out


CINTA_M = 400          # puntos de la curva que se achica (`_Cinta`)
JUNTA_CINTA = 3.0      # d: lo que tarda la curva en juntarse con el camino en p*


@dataclass
class _Cinta:
    """La bolsa de A que se achica mientras la mano tira de la punta por el camino de B (T21c),
    cuando la punta de A ya está en ese camino (`_cinta`), así que no hay aire: es el chicote que
    sube por la gaza pequeña del as de guía mientras la gaza grande se achica, y el que baja por
    ella mientras se aprieta el collar. Lo que ya pasó por p* sigue el camino; lo de antes, de s1
    a p*, es una curva que va de la forma de A a la de B y mide lo que queda de cuerda de ese
    lado."""
    u_ini: float          # la punta de A, en el camino de B (u = σ − o de B)
    s_ent: float          # p*, en u
    s1: float             # σ donde empieza la curva que se achica
    s2: float             # σ de A que está en p*
    A: np.ndarray         # (CINTA_M, 3): el tramo de A de s1 a s2, repartido igual a lo largo de él
    B: np.ndarray         # el de B, de s1 a p*
    pesos: np.ndarray
    largos: np.ndarray    # lo que mide la mezcla de A y B con cada peso (sin crecer)

    def curva(self, largo: float):
        """La mezcla de A y B que mide `largo` y su largo hasta cada punto."""
        w = float(np.interp(largo, self.largos[::-1], self.pesos[::-1]))
        S = (1 - w) * self.A + w * self.B
        return S, _largos_acum(S)


def _cinta(A: PoseVideo, B: PoseVideo, V) -> _Cinta | None:
    """Si la punta de A ya está en el camino V de B (a menos de TOL_CINTA vista desde arriba y de
    ALTO_CINTA de alto, yendo para el mismo lado) y B la lleva más adelante, la mano tira de ella
    sin levantarla por el aire. Lo que A tiene desde s2 hasta la punta ya está en el camino,
    corrido lo que la punta va a avanzar; la curva que se achica va del comienzo de la bolsa de A
    (s1) hasta p*, donde s2 entra al camino."""
    h, N, o = B.h, len(B.X), B.o
    if A.bolsa is None:
        return None              # sin bolsa no hay cuerda de más de este lado de la punta
    s_tip = (N - 1) * h

    def en_camino(p, q) -> bool:
        return (float(np.linalg.norm((p - q)[:2])) < TOL_CINTA
                and abs(float(p[2] - q[2])) < ALTO_CINTA)

    p = A.X[-1]
    seg = np.diff(V, axis=0)
    L2 = np.maximum(np.einsum("ij,ij->i", seg[:, :2], seg[:, :2]), 1e-18)
    t = np.clip(np.einsum("ij,ij->i", (p - V[:-1])[:, :2], seg[:, :2]) / L2, 0.0, 1.0)
    q = V[:-1] + t[:, None] * seg
    # El más cercano desde arriba, pero entre dos pasadas por el mismo lugar (un cruce), la de la
    # altura más parecida.
    d = np.linalg.norm((q - p)[:, :2], axis=1) + 0.3 * np.abs(q[:, 2] - p[2])
    i = int(np.argmin(d))
    if not en_camino(p, q[i]):
        return None
    u_ini = (i + float(t[i])) * h
    m = max(1, int(round(0.6 / h)))
    ta = (A.X[-1] - A.X[-1 - m])[:2]
    tv = (_en(V, h, min(u_ini + 0.3, (len(V) - 1) * h)) - _en(V, h, max(u_ini - 0.3, 0.0)))[:2]
    if float(np.dot(ta, tv)) < 0.5 * float(np.linalg.norm(ta) * np.linalg.norm(tv)):
        return None
    delta = s_tip - o - u_ini
    if delta < h:
        return None
    j = N - 1
    while j > 0 and (j - 1) * h - o - delta >= 0 and \
            en_camino(A.X[j - 1], _en(V, h, (j - 1) * h - o - delta)):
        j -= 1
    s2 = j * h
    # La curva que se achica empieza donde empieza la bolsa de A. Lo de antes va de A a B nodo a
    # nodo, como en «punta»: las fichas de dos pasos, asentadas cada una por su lado, difieren
    # en todo el nudo (en el paso 4 del as de guía, el chicote que sube empuja la gaza pequeña
    # más de 0,5 d), y la curva no puede tragarse los cruces.
    i1 = int(math.floor(A.bolsa[0] / h + 1e-9))
    return _cinta_de(A, B, u_ini, s2 - o - delta, j, i1)


def _cinta_de(A: PoseVideo, B: PoseVideo, u_ini: float, s_ent: float, j: int, i1: int) -> _Cinta | None:
    """La cinta con la punta de A en u_ini del camino de B, p* en s_ent (u) y la curva que se
    achica de los nodos i1 a j de A (j: el que está en p*) a la cuerda de B de i1 a p*."""
    h, o = B.h, B.o
    s2 = j * h
    sB = o + s_ent
    if i1 * h > min(sB, s2) - 1.0:
        return None
    nB = int(math.floor(sB / h + 1e-9))
    TB = B.X[i1:nB + 1]
    if sB - nB * h > 1e-6:
        TB = np.vstack([TB, _en(B.X, h, sB)])
    TA, TB = _uniforme(A.X[i1:j + 1], CINTA_M), _uniforme(TB, CINTA_M)
    pesos = np.linspace(0.0, 1.0, 201)
    largos = np.array([float(np.sum(np.linalg.norm(np.diff((1 - w) * TA + w * TB, axis=0), axis=1)))
                       for w in pesos])
    return _Cinta(u_ini, s_ent, i1 * h, s2, TA, TB, pesos, np.minimum.accumulate(largos))


LAZO_MIN = 4.0         # d: con menos cuerda de más que esto entre el nudo y la punta, la mano la
                       # lleva por el aire con lo de detrás suelto (`_tramo_largo_punta`)


def _entrada(refs_B, s0: float, u_ficha: float, u_fin: float, h: float) -> float:
    """La entrada al camino de B (en u): ENTRADA antes del primer cruce nuevo, y al menos
    ENTRADA_MIN después de donde B se separa de A (s0)."""
    cerca = [max(a, b) for a, b, _ in refs_B if s0 - h <= max(a, b) <= u_ficha + 1e-6]
    primero = min(cerca, default=None)
    s_ent = s0 + ENTRADA_MIN if primero is None else max(primero - ENTRADA, s0 + ENTRADA_MIN)
    return min(s_ent, u_fin)


def _lazo(A: PoseVideo, B: PoseVideo, V):
    """El lazo (T21c): la punta de A está lejos, al final de la cola acostada, y vuelve junto
    al nudo para entrar al camino de B (a pasar bajo el firme en el paso 5 del as de guía). Por el
    aire y con la cola suelta, la cola se amontonaba en un rollo junto al nudo (Gabriel, 27 nov).
    La pose intermedia A' guarda toda esa cuerda en una bolsa: el camino de B desde donde se separa
    de A hasta la entrada, inflado (`_inflar`), con la punta en la entrada y levantada por la mano.
    Da (A', la cinta de A' a B), o None si la cuerda de más es poca o la bolsa no cabe."""
    import dataclasses
    h, N, o = B.h, len(B.X), B.o
    s_tip = (N - 1) * h
    u_fin = s_tip - o
    s0 = B.en_video((B.r1 - 1) * B.h_ficha) - o
    refs_B = [(a - o, b - o, e) for a, b, e in _referencia(B.X, h) if min(a, b) >= o - 1e-9]
    s_ent = _entrada(refs_B, s0, B.fin - o, u_fin, h)
    i1 = int(math.ceil((o + s0) / h - 1e-9))
    sa = i1 * h
    if sa > o + s_ent - 1.0:
        return None
    P, _ = _tramo_fino(V, h, sa - o, s_ent, h / 4)
    largo = s_tip - sa
    sobra = largo - float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
    if sobra < LAZO_MIN:
        return None
    Y = _inflar(P, sobra)
    if Y is None:
        return None
    sig = np.arange(N) * h
    uV = np.arange(len(V)) * h
    # Lo que la bolsa no puede pisar: el nudo de B y el camino que la punta va a hacer.
    resto = np.vstack([B.X[sig < sa - BOLSA_VECINOS], V[uV > s_ent + BOLSA_VECINOS]])
    if not _bolsa_cabe(Y, P, resto, h):
        return None
    Xp = B.X.copy()
    l = _largos_acum(Y)
    ell = (sig[i1:] - sa) * l[-1] / largo
    Xp[i1:] = np.column_stack([np.interp(ell, l, Y[:, i]) for i in range(3)])
    # La mano lleva la punta levantada, y lo de detrás baja en DETRAS_MANO.
    uh = s_tip - PINZA
    Xp[:, 2] += ALTO_MANO * np.where(sig >= uh, 1.0, _suave(1 - (uh - sig) / DETRAS_MANO))
    Ap = dataclasses.replace(B, X=Xp, cola=0.0, bolsa=(sa, s_tip, sobra), bolsa_ficha=None)
    cinta = _cinta_de(Ap, B, s_ent, s_ent, N - 1, i1)
    return None if cinta is None else (Ap, cinta)


BARRIDO_RADIO = 15.0   # d: el barrido dura lo que tarda en girar, a VEL_AIRE, la cuerda a esto de
                       # donde empieza a girar (la punta, lejos, va más rápido). Con 10, lo que se
                       # ve de la cola pasaba a 19 d/s en el medio del giro
DOBLAR_RADIO = 10.0    # d: lo mismo para la cola que se dobla en la bolsa del lazo
BARRIDO_MAX = 0.9 * math.pi   # lo que puede girar la cola: más que eso ya no es un barrido
BARRIDO_SUAVE = 9      # cuadros: lo que sube cada tramo sobre un cruce, parejo en este tiempo
BARRIDO_SALTO = 5.0    # d: con la cola casi paralela al firme, el cruce corre por los dos hasta
                       # 1,7 d por cuadro; con el seguimiento de siempre (1 d), cada cuadro era un
                       # cruce nuevo, con la cola encima, y la guía la subía 8 d


def _mezcla_angular(A: PoseVideo, B: PoseVideo, ia: int, maximo: float = math.inf,
                    asentar: bool = True, fase: str = "barrer", modo: str = "barrido",
                    radio: float = BARRIDO_RADIO) -> Tramo | None:
    """La guía de A a B que mezcla los ángulos de la cuerda desde el nodo ia (T21c): cada tramo
    gira de su ángulo en A al de B (visto desde arriba) y se alarga de su largo en A al de B, y la
    cuerda se arma tramo a tramo desde ia, así que no se estira ni se encoge (mezclando los
    lugares nodo a nodo, la cola que se dobla queda más corta que la cuerda a mitad de camino, y
    el motor la arrugaba). Lo de antes de ia va nodo a nodo. Lo que se cruza sube con `alturas`
    (el firme, sobre la cola que pasa por debajo). None si algún tramo gira más que `maximo`.
    Sin `asentar`, no lleva el asentado del final (lo sigue otro tramo)."""
    h, N = B.h, len(B.X)
    dA, dB = np.diff(A.X[ia:, :2], axis=0), np.diff(B.X[ia:, :2], axis=0)
    lA, lB = np.linalg.norm(dA, axis=1), np.linalg.norm(dB, axis=1)
    tA = np.unwrap(np.arctan2(dA[:, 1], dA[:, 0]))
    tB = np.unwrap(np.arctan2(dB[:, 1], dB[:, 0]))
    tB = tB - 2 * math.pi * round((tB[0] - tA[0]) / (2 * math.pi))
    giro = tB - tA
    if float(np.max(np.abs(giro))) > maximo:
        return None
    zA, zB = A.X[ia:, 2], B.X[ia:, 2]
    seg = max(ACOMODAR_MIN, float(np.max(np.abs(giro))) * radio / VEL_AIRE)
    nf = max(int(round(seg * FPS)), 2)
    S, Bx = A.X, B.X
    mov = np.linalg.norm(Bx - S, axis=1)
    refs_A, refs_B = _referencia(S, h), _referencia(Bx, h)
    c = int(round(((N - 1) * h - PINZA) / h))
    manos = [0, c - 1, c, c + 1]
    borr = []
    for f in range(nf + 1):
        w = float(_suave5(f / nf))
        env = math.sin(math.pi * w)
        G = S + w * (Bx - S)
        th = tA + w * giro
        ll = lA + w * (lB - lA)
        G[ia + 1:, :2] = G[ia, :2] + np.cumsum(ll[:, None] * np.column_stack([np.cos(th), np.sin(th)]), axis=0)
        G[ia:, 2] = zA + w * (zB - zA)
        borr.append(_Borrador(G=G, n=N, manos=manos, hasta=(N - 1) * h, mov=mov,
                              holgura=lambda a, b, env=env: (HOLGURA * env, 1.0),
                              exacto=Bx if f == nf else (S if f == 0 else None)))
    cruces = _seguir_cruces(borr, h, refs_A, refs_B, True, salto=BARRIDO_SALTO)
    # Lo que sube cada tramo, parejo en el tiempo: el máximo de BARRIDO_SUAVE cuadros, promediado.
    # Con la cola casi paralela al firme, el cruce aparecía y desaparecía junto a la punta del
    # firme, que saltaba (un pico de 3300 d/s²).
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    base = np.array([b.G[:, 2] for b in borr])
    sube = np.array([alturas(b.G, h, cr, b.holgura) for b, cr in zip(borr, cruces)]) - base
    sube = uniform_filter1d(maximum_filter1d(sube, BARRIDO_SUAVE, axis=0, mode="nearest"),
                            BARRIDO_SUAVE, axis=0, mode="nearest")
    guia = []
    for f, b in enumerate(borr):
        G = b.G.copy()
        G[:, 2] = base[f] + sube[f]
        if b.exacto is not None:
            G = b.exacto.copy()
        guia.append(_cuadro_largo(G, h, np.full(N, RESORTE), manos, suelto=False,
                                  largos=_largos_de(A, B, float(_suave5(f / nf)))))
    fases = {fase: (0, nf)}
    if asentar:
        guia += _asentado(A, B)
        fases["asentar"] = (nf + 1, len(guia) - 1)
    return Tramo(B.n, modo, S.copy(), Bx.copy(), guia, fases)


def _tramo_largo_barrido(A: PoseVideo, B: PoseVideo) -> Tramo | None:
    """La guía del paso A al B por un barrido (T21c): la cola gira entera, como un
    limpiaparabrisas, hasta su lugar en B (`_mezcla_angular`), y pasa por debajo (o por encima)
    de lo que cruza, que sube mientras pasa. Es pasar el chicote por debajo del firme en el paso
    5 del as de guía: la cola de 23 d está acostada arriba a la izquierda y termina a la derecha.
    Traer la punta junto al nudo la amontonaba en un rollo, y con dos puntas casi paralelas junto
    al nudo la bolsa del lazo se cruzaba a sí misma (Gabriel, 27 nov). None si la cola gira más
    que BARRIDO_MAX (no es un barrido) o si A y B no tienen el mismo depósito."""
    h, N, o = B.h, len(B.X), B.o
    if abs(A.o - o) > 1e-9:
        return None
    s0 = B.en_video((B.r1 - 1) * B.h_ficha) - o
    ia = int(math.ceil((o + s0) / h - 1e-9))
    if ia > N - 4:
        return None
    return _mezcla_angular(A, B, ia, maximo=BARRIDO_MAX)


def _tramo_largo_enhebrar(A: PoseVideo, B: PoseVideo, solido=None) -> Tramo:
    """La guía de un paso «punta» en que la punta pasa por algún cruce nuevo, por la primera
    manera que sirve: si la punta de A ya está en el camino de B, la cinta (la bolsa de A se achica
    mientras la mano tira); si no, el lazo (la cola se dobla en una bolsa junto a la entrada y
    después se achica), el barrido (la cola gira entera por debajo de lo que cruza) y, si nada de
    eso cabe o hay un anfitrión (que ni la bolsa ni el barrido conocen), por el aire con lo de
    detrás suelto (`_tramo_largo_punta`)."""
    h, N, o = B.h, len(B.X), B.o
    nV = int(math.floor(((N - 1) * h - o) / h + 1e-9)) + 1
    V = np.array([_en(B.X, h, o + i * h) for i in range(nV)])
    cinta = _cinta(A, B, V)
    if cinta is None and solido is None:
        tr = _tramo_largo_lazo(A, B) or _tramo_largo_barrido(A, B)
        if tr is not None:
            return tr
    return _tramo_largo_punta(A, B, solido, cinta=cinta)


def _tramo_largo_lazo(A: PoseVideo, B: PoseVideo) -> Tramo | None:
    """La guía del paso A al B por el lazo (`_lazo`): la mano trae la punta hasta la entrada y la
    cola se dobla, guiada, hasta la bolsa (`_mezcla_angular`, sin estirarse), y después tira por el
    camino y la bolsa se achica, como la gaza grande al subir el chicote por la gaza pequeña (la
    cinta de `_tramo_largo_punta`). Es volver por encima del firme en el paso 6 del as de guía.
    None si no va por el lazo: la punta ya está en el camino (cinta) o la cuerda de más es poca o
    no cabe."""
    h, N, o = B.h, len(B.X), B.o
    nV = int(math.floor(((N - 1) * h - o) / h + 1e-9)) + 1
    V = np.array([_en(B.X, h, o + i * h) for i in range(nV)])
    if _cinta(A, B, V) is not None:
        return None
    lazo = _lazo(A, B, V)
    if lazo is None:
        return None
    Ap, cinta = lazo
    t1 = _mezcla_angular(A, Ap, int(round(Ap.bolsa[0] / h)), asentar=False, fase="aire", modo="lazo",
                         radio=DOBLAR_RADIO)
    t2 = _tramo_largo_punta(Ap, B, cinta=cinta)
    n1 = len(t1.guia)
    fases = {"aire": (0, n1 - 1)}
    fases.update({k: (a + n1, b + n1) for k, (a, b) in t2.fases.items()})
    return Tramo(B.n, "lazo", A.X.copy(), B.X.copy(), t1.guia + t2.guia, fases)


def _tramo_largo_punta(A: PoseVideo, B: PoseVideo, solido=None, cinta=None) -> Tramo:
    """La guía del paso A al B con largo fijo, cuando B sigue el camino de A desde el firme y
    cambia hacia la punta (T21c). La mano toma la cuerda a PINZA de la punta, la lleva por el aire
    hasta el camino nuevo, la enhebra por él (los tramos de encima suben con `alturas`, como en
    T17) y tira de la cola hasta su lugar. Cada nodo que ya pasó la entrada sigue el camino que
    hizo la punta; lo que todavía no pasó queda suelto (sin resorte, con su peso) y se recoge solo
    al tirar. La pierna que va del nudo a la entrada vuelve a su lugar cuando queda poca cuerda
    por pasar.

    Si la punta de A ya está en el camino de B (`_cinta`, o la que se le da), no hay aire: la
    mano la toma ahí y tira, y la cuerda que todavía no pasó es la bolsa de A, que se achica
    guiada hasta la forma de B (la gaza grande del as de guía al subir el chicote por la gaza
    pequeña)."""
    h, N, o = B.h, len(B.X), B.o
    s_tip = (N - 1) * h
    u_fin = s_tip - o
    u_ficha = B.fin - o                       # la punta de la ficha de B, en u
    s0 = B.en_video((B.r1 - 1) * B.h_ficha) - o
    sig = np.arange(N) * h
    # El camino de llegada, desde σ = o: la ficha de B y su cola, en u = σ − o.
    nV = int(math.floor(u_fin / h + 1e-9)) + 1
    V = np.array([_en(B.X, h, o + i * h) for i in range(nV)])
    cinta = cinta or _cinta(A, B, V)
    # Los cruces de A que cuentan son los del tramo que ya está donde va a quedar (hasta s0): lo
    # que sigue (la punta vieja y la cola de más) cambia de lugar, y un cruce suyo por encima
    # puede ser, en B, uno por debajo en el mismo lugar de la cuerda. Lo de B, sin el depósito,
    # que no entra en el camino.
    refs_A = [(a - o, b - o, e) for a, b, e in _referencia(A.X, h)
              if min(a, b) >= o - 1e-9 and max(a, b) - o < s0 - h]
    refs_B = [(a - o, b - o, e) for a, b, e in _referencia(B.X, h) if min(a, b) >= o - 1e-9]
    # Los cruces que la punta tiene que enhebrar: los del camino nuevo de la ficha (con la cinta,
    # los que todavía tiene por delante; por los de atrás la cuerda solo corre).
    umbral = cinta.u_ini if cinta else s0
    nuevos = [c for c in refs_B if umbral - h <= max(c[0], c[1]) <= u_ficha + 1e-6]
    cerca = [max(a, b) for a, b, _ in nuevos]
    if cinta is None:
        s_ent = _entrada(refs_B, s0, u_ficha, u_fin, h)
        # El aire: de la punta, donde está, a la entrada, levantada ALTO_MANO.
        m = max(1, int(round(0.6 / h)))
        t_ini = A.X[-1] - A.X[-1 - m]
        t_ini = t_ini / max(float(np.linalg.norm(t_ini)), 1e-12)
        E = _en(V, h, s_ent) + np.array([0.0, 0.0, ALTO_MANO])
        t_ent = _en(V, h, min(s_ent + 0.5, u_fin)) - _en(V, h, max(s_ent - 0.5, 0.0))
        t_ent[2] = 0.0
        t_ent = t_ent / max(float(np.linalg.norm(t_ent)), 1e-12)
        nudo = A.X[sig <= o + s0 + 1e-9]
        alto = max(float(np.max(nudo[:, 2])) + 1.5, float(A.X[-1, 2]) + 1.0, float(E[2]) + 0.5)
        Q, lq = _por_largo(_aire(A.X[-1], t_ini, E, t_ent, alto))
        u_ini = s_ent - float(lq[-1])
    else:
        s_ent, u_ini = cinta.s_ent, cinta.u_ini

    def vel(u):
        if u < s_ent:
            return VEL_AIRE
        if u <= u_ficha:
            return VEL_CRUCE if min((abs(u - c) for c in cerca), default=math.inf) < CERCA_CRUCE else VEL
        return VEL_TIRAR

    U = _recorrido_largo(u_ini, u_fin, vel)
    F = len(U) - 1
    baja = max(1.0, ARRANQUE_LARGO * FPS)
    # Con la cinta, la mano levanta la punta al arrancar (en A está sobre la mesa); sin ella, la
    # punta ya sube por el aire.
    lifts = [float(_suave5((F - f) / baja)) * (float(_suave5(f / baja)) if cinta else 1.0)
             for f in range(F + 1)]
    mira = ANTES_CRUCE + RAMPA
    uV = np.arange(nV) * h
    mueve = min(s0, cinta.s1 - o) if cinta else s0
    borr = []
    for f, ut in enumerate(U):
        n_v = int(math.floor(min(u_fin, max(s_ent, ut) + mira) / h + 1e-9)) + 1
        mv = np.zeros(n_v)
        mv[min(n_v, max(0, int(mueve / h))):] = 1.0
        G = V[:n_v].copy()
        # La mano lleva la punta levantada ALTO_MANO, y lo de detrás baja en DETRAS_MANO: va en
        # la guía antes de las alturas, para que el tramo de encima de un cruce suba por encima
        # de la punta levantada (como en T17). Si no, quedaban tocándose y la punta se trababa.
        # Lo que viene por delante, por donde va a pasar la punta, también va levantado: cortado
        # en la punta, la punta caía entre un nodo levantado y otro no, y su altura iba y venía
        # 1 d cada vez que pasaba un nodo.
        u = uV[:n_v]
        uh = ut - PINZA
        mano = u >= s_ent - 1e-9
        w = np.where(u >= uh, 1.0, _suave(1 - (uh - u) / DETRAS_MANO))
        G[mano, 2] += ALTO_MANO * lifts[f] * w[mano]

        def hol(a, b, um=float(ut), lift=lifts[f]):
            nueva = max(a, b)
            if nueva < umbral - 1e-9:
                return 0.0, 1.0
            d = um - nueva
            antes = _rampa((d + ANTES_CRUCE + RAMPA) / RAMPA)
            despues = _rampa((DESPUES_CRUCE + RAMPA - d) / RAMPA)
            return HOLGURA * lift * antes * despues, (antes if d < 0 else 1.0)

        borr.append(_Borrador(G=G, n=n_v, manos=[], hasta=float(ut), mov=mv,
                              holgura=hol, exacto=V.copy() if f == F else None))
    cruces = _seguir_cruces(borr, h, refs_A, refs_B, True)
    c_pinza = int(round((s_tip - PINZA) / h))
    manos = [0, c_pinza - 1, c_pinza, c_pinza + 1]
    prefijo = sig <= (cinta.s1 if cinta else o + s0) + 1e-9
    de_v = prefijo & (sig >= o - 1e-9)
    punta = sig >= s_tip - PUNTA_GUIA - 1e-9
    pierna_toda = ~prefijo & (sig <= o + s_ent + 1e-9)
    if cinta:
        # Lo que A ya tiene en el camino puede quedar hasta TOL_CINTA de él: esa diferencia se va
        # en el arranque, sin saltar en el primer cuadro.
        en_v = sig >= cinta.s2 - 1e-9
        corrido = np.zeros((N, 3))
        corrido[en_v] = A.X[en_v] - np.array([_en(V, h, u_ini - (s_tip - s)) for s in sig[en_v]])
        junta_A = A.X[int(round(cinta.s2 / h))] - _en(V, h, s_ent)
    guia = []
    for f, (b, cr) in enumerate(zip(borr, cruces)):
        ut = float(U[f])
        if b.exacto is not None:
            Vf = b.exacto
        else:
            Vf = b.G.copy()
            Vf[:, 2] = alturas(Vf, h, cr, b.holgura)
        w_f = float(_suave5(f / max(F, 1)))
        G = B.X.copy()
        G[de_v] = [_en(Vf, h, s - o) for s in sig[de_v]]
        G[prefijo] += (A.X[prefijo] - B.X[prefijo]) * (1 - w_f)
        uj = ut - (s_tip - sig)
        enhebrado = (uj >= s_ent - 1e-9) & ~prefijo
        if cinta:
            queda = 1.0 - float(_suave5(f / baja))
            for j in np.flatnonzero(enhebrado):
                G[j] = _en(Vf, h, uj[j]) + corrido[j] * queda
            # La bolsa que se achica: de s1 a p*, con lo que todavía no pasó.
            s2 = s_tip - ut + s_ent + o
            curva = ~prefijo & ~enhebrado
            if curva.any():
                largo = s2 - cinta.s1
                S, lS = cinta.curva(largo)
                ell = (sig[curva] - cinta.s1) * lS[-1] / largo
                pos = np.column_stack([np.interp(ell, lS, S[:, i]) for i in range(3)])
                # En p* se junta con el camino (levantado por la mano y con lo que A tenía corrido).
                junta = _en(Vf, h, s_ent) + junta_A * queda - S[-1]
                pos += junta * _suave5(1 - (largo - (sig[curva] - cinta.s1)) / JUNTA_CINTA)[:, None]
                G[curva] = pos
            k = np.full(N, RESORTE)
            guia.append(_cuadro_largo(G, h, k, manos, largos=_largos_de(A, B, w_f)))
            continue
        sel = (punta | enhebrado) & ~prefijo
        # El aire llega a la entrada levantado ALTO_MANO sobre la ficha, pero el camino puede ir ahí
        # más alto (sube sobre un cruce): los últimos MEZCLA d del aire se acomodan a él en cada
        # cuadro. Si no, la punta y, 1,5 d después, la mano saltaban al entrar.
        junta = _en(Vf, h, s_ent) - E
        for j in np.flatnonzero(sel):
            u = uj[j]
            if u >= s_ent - 1e-9:
                p = _en(Vf, h, u)          # ya con la punta levantada
            elif u >= u_ini:
                p = np.array([np.interp(u - u_ini, lq, Q[:, i]) for i in range(3)])
                p = p + junta * float(_suave5((u - (s_ent - MEZCLA)) / MEZCLA))
            else:
                p = _en(A.X, h, s_tip - (u_ini - u))
            G[j] = p
        k = np.zeros(N)
        k[prefijo] = RESORTE
        k[sel] = RESORTE
        recien = enhebrado & ~punta
        k[recien] *= _suave(np.clip((uj[recien] - s_ent) / ENTRA, 0.0, 1.0))
        pierna = pierna_toda & ~sel
        if pierna.any():
            k[pierna] = RESORTE * _rampa((FLOJO - (u_fin - ut)) / FLOJO)
            G[pierna] = [_en(Vf, h, s - o) for s in sig[pierna]]
        guia.append(_cuadro_largo(G, h, k, manos, largos=_largos_de(A, B, w_f)))
    i_ent, i_ficha = int(np.searchsorted(U, s_ent)), int(np.searchsorted(U, u_ficha))
    if cinta:
        fases = {"enhebrar": (0, i_ficha), "tirar": (i_ficha, F)}
    else:
        fases = {"aire": (0, i_ent), "enhebrar": (i_ent, i_ficha), "tirar": (i_ficha, F)}
    guia += _asentado(A, B)
    fases["asentar"] = (F + 1, len(guia) - 1)
    return Tramo(B.n, "cinta" if cinta else "punta", A.X.copy(), B.X.copy(), guia, fases)


VEL_DESLIZAR = 8.0     # d/s: el firme que corre a lo largo de sí mismo

GAZA_BOCA = 1.3        # d: la bolsa sale entre esto antes y esto después del cruce que se forma
GAZA_BOLSA = 8.0       # d: lo que mide la bolsa cuando se voltea
GAZA_CUELLO = 1.5      # d: desde la boca, en esto la bolsa pasa de no girar a girar entera
GAZA_ARRIBA = 6.0      # d: lo que se rehace empieza esto antes del cruce, en el firme,
GAZA_ABAJO = 3.0       # y termina esto después; lo de más allá va de A a B nodo a nodo
GAZA_QUIETO = 1.0      # d: lo más que puede moverse de A a B lo de más allá
GAZA_FASES = {"bolsa": (0.0, 0.40), "voltear": (0.30, 0.62), "crecer": (0.55, 1.0)}
GAZA_TIEMPO = 1.75     # el paso dura esto por lo que tarda el firme en correr a VEL_DESLIZAR
GAZA_TRAMOS = (0.6, 1.4)   # lo más corto y lo más largo que puede quedar un tramo de la guía, en h
GAZA_HOLGURA = 0.3     # d: el volteo ya separa los dos tramos del cruce; con HOLGURA, el que va
                       # encima subía más sobre el que ya se levantaba, y se estiraba


def _desde_punta(P, n: int, h: float) -> np.ndarray | None:
    """n nodos cada h a lo largo de la polilínea P, desde su último punto hacia el primero."""
    Q = np.asarray(P, float)[::-1]
    c = _largos_acum(Q)
    x = np.arange(n) * h
    if x[-1] > c[-1] + 1e-9:
        return None
    return np.column_stack([np.interp(x, c, Q[:, i]) for i in range(3)])[::-1]


def _voltear(Y, alfa: float, zt: float, primera_encima: bool) -> np.ndarray:
    """La bolsa Y (de la boca del lado del firme a la del chicote, acostada) girada `alfa` sobre su
    eje, que va de la mitad de la boca a su centro. El tramo que en B queda encima sube y pasa por
    arriba del otro, que se corre por la mesa: cada tajada sube lo que bajaría ese otro tramo. Desde
    la boca, en GAZA_CUELLO, el giro va de nada a entero: ahí se forma el cruce."""
    if alfa <= 0:
        return Y.copy()
    Mm = (Y[0, :2] + Y[-1, :2]) / 2
    eje = np.mean(Y[:, :2], axis=0) - Mm
    eje /= np.linalg.norm(eje)
    nrm = np.array([-eje[1], eje[0]])
    arriba = Y[0] if primera_encima else Y[-1]
    lado = 1.0 if float((arriba[:2] - Mm) @ nrm) > 0 else -1.0
    x = (Y[:, :2] - Mm) @ eje
    y = ((Y[:, :2] - Mm) @ nrm) * lado
    giro = alfa * _suave5(np.clip(x / GAZA_CUELLO, 0.0, 1.0))
    sube = y * np.sin(giro)
    L = np.zeros(len(Y))
    abajo = y < 0
    if abajo.any():
        o = np.argsort(x[abajo])
        L = np.interp(x, x[abajo][o], np.maximum(0.0, -sube[abajo][o]))
    out = Y.copy()
    out[:, :2] = Mm + x[:, None] * eje + (y * np.cos(giro) * lado)[:, None] * nrm
    out[:, 2] = zt + sube + L
    return out


def _area(P) -> float:
    """El área con signo de la polilínea P cerrada, vista desde arriba (positiva si gira a la
    izquierda)."""
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _tramo_largo_gaza(A: PoseVideo, B: PoseVideo) -> Tramo | None:
    """La guía del paso A al B cuando la cuerda que entra por el firme forma una gaza con un cruce
    nuevo, como la gaza pequeña del as de guía (T21c). Un lazo no sale de una cuerda acostada sin
    levantarla: en línea recta, nodo a nodo, el firme se ondulaba y la gaza nacía de un gancho.
    1. La cuerda que entra sale en una bolsa acostada (`_inflar`) junto al cruce, sin cruzarse.
    2. La bolsa se voltea (`_voltear`): el tramo que en B va encima pasa por arriba del otro, como se
       forma un ojo con la mano, y en su cuello queda el cruce.
    3. La bolsa volteada va hasta el lazo de B mientras el firme sigue corriendo y lo agranda.
    Los nodos van cada h a lo largo de esa curva desde un punto fijo del otro lado del cruce, así
    que el firme corre a lo largo de sí mismo; de ahí en adelante cada nodo va de A a B, y un
    ajuste suave deja el primer cuadro en A y el último en B. None si B no suma una sola gaza con
    la cuerda que entra por el firme, si la bolsa no se infla o no queda del lado del lazo, o si la
    guía estira o encoge algún tramo más de GAZA_TRAMOS."""
    h, N = B.h, len(B.X)
    entra = A.o - B.o
    if entra < BOLSA_MIN:
        return None
    refs_A, refs_B = _referencia(A.X, h), _referencia(B.X, h)
    nuevos = [r for r in refs_B if _buscar(refs_A, r[0], r[1]) is None]
    if len(nuevos) != 1 or len(refs_B) != len(refs_A) + 1:
        return None
    sa, sb, primera_encima = nuevos[0]
    s_lo, s_hi = min(sa, sb), max(sa, sb)
    if s_lo == sb:
        primera_encima = not primera_encima
    ell = s_hi - s_lo
    j_bot = int(math.ceil((s_hi + GAZA_ABAJO) / h - 1e-9))
    s_top, s_m1, s_m2, s_bot = s_lo - GAZA_ARRIBA, s_lo - GAZA_BOCA, s_hi + GAZA_BOCA, j_bot * h
    if abs(ell - entra) > 3.0 or s_top < h or j_bot >= N - 1:
        return None
    if float(np.max(np.linalg.norm(A.X[j_bot:] - B.X[j_bot:], axis=1))) > GAZA_QUIETO:
        return None
    zt = float(np.median(B.X[:, 2]))

    def tramo_B(a, b, paso=0.05):
        return np.array([_en(B.X, h, s) for s in np.append(np.arange(a, b, paso), b)])

    def tangente(s):
        d = _en(B.X, h, s + 0.3)[:2] - _en(B.X, h, s - 0.3)[:2]
        return np.append(d / np.linalg.norm(d), 0.0)

    firme, chicote, lazo_B = tramo_B(s_top, s_m1), tramo_B(s_m2, s_bot), tramo_B(s_m1, s_m2)
    encima_B = tramo_B(0.0, s_top)[:-1]
    z_firme, z_chicote, z_encima = firme[:, 2].copy(), chicote[:, 2].copy(), encima_B[:, 2].copy()
    M1, M2 = firme[-1].copy(), chicote[0].copy()
    boca = float(np.linalg.norm(M2[:2] - M1[:2]))
    base = _hermite(M1, M2, tangente(s_m1) * boca, tangente(s_m2) * boca, 60)
    base[:, 2] = zt
    base = _uniforme(base, 60)
    sobra = GAZA_BOLSA - float(_largos_acum(base)[-1])
    lejos = (B.X[0] - B.X[3]) / np.linalg.norm(B.X[0] - B.X[3])
    bolsas = {}

    def bolsa(u):
        k = round(u, 3)
        if k not in bolsas:
            Y = _inflar(base, u * sobra) if u > 0 else base.copy()
            bolsas[k] = None if Y is None else _uniforme(Y, 240)
        return bolsas[k]

    def fase(t, nombre):
        a, b = GAZA_FASES[nombre]
        return float(_suave5(min(1.0, max(0.0, (t - a) / (b - a)))))

    def curva(t):
        u3 = fase(t, "crecer")
        Y = bolsa(fase(t, "bolsa"))
        if Y is None:
            return None
        Y = _voltear(Y, math.pi * fase(t, "voltear"), zt, primera_encima)
        if u3 > 0:
            Y = (1 - u3) * _uniforme(Y, 400) + u3 * _uniforme(lazo_B, 400)
        fi, ch, en = firme.copy(), chicote.copy(), encima_B.copy()
        fi[:, 2] = (1 - u3) * zt + u3 * z_firme
        ch[:, 2] = (1 - u3) * zt + u3 * z_chicote
        en[:, 2] = (1 - u3) * zt + u3 * z_encima
        Y[0, 2], Y[-1, 2] = fi[-1, 2], ch[0, 2]
        w = float(_suave5(t))
        G = (1 - w) * A.X + w * B.X
        R = np.vstack([en, fi[:-1], Y, ch[1:]])
        R = R + (G[j_bot] - R[-1]) * np.array([1.0, 1.0, 0.0])
        # Su altura llega a la del nodo de más allá a lo largo del tramo del chicote.
        k = len(ch) - 1
        R[-k:, 2] += (G[j_bot, 2] - R[-1, 2]) * np.linspace(0.0, 1.0, k)
        nodos = _desde_punta(np.vstack([R[0] + lejos * (N * h), R]), j_bot + 1, h)
        if nodos is None:
            return None
        G[:j_bot + 1] = nodos
        return G

    seg = max(ACOMODAR_MIN, GAZA_TIEMPO * entra / VEL_DESLIZAR)
    nf = max(int(round(seg * FPS)), 2)
    G0, G1 = curva(0.0), curva(1.0)
    if G0 is None or G1 is None:
        return None
    # La bolsa queda del lado del lazo y, volteada, gira hacia donde gira el lazo.
    Mm = (M1[:2] + M2[:2]) / 2
    if float((np.mean(bolsa(1.0)[:, :2], axis=0) - Mm) @ (np.mean(lazo_B[:, :2], axis=0) - Mm)) <= 0:
        return None
    if _area(np.vstack([bolsa(1.0), [M1]])) * _area(lazo_B) >= 0:
        return None
    D0, D1 = A.X - G0, B.X - G1
    mov = np.linalg.norm(B.X - A.X, axis=1)
    manos = [0, N - 1]
    borr = []
    for f in range(nf + 1):
        t = f / nf
        G = curva(t)
        if G is None:
            return None
        w = float(_suave5(t))
        env = math.sin(math.pi * w)
        borr.append(_Borrador(G=G + (1 - w) * D0 + w * D1, n=N, manos=manos, hasta=(N - 1) * h, mov=mov,
                              holgura=lambda a, b, env=env: (GAZA_HOLGURA * env, 1.0),
                              exacto=B.X if f == nf else (A.X if f == 0 else None)))
    cruces = _seguir_cruces(borr, h, refs_A, refs_B, True)
    s = np.arange(N) * h
    guia = []
    for f, (b, cr) in enumerate(zip(borr, cruces)):
        G = b.G.copy()
        # La bolsa levantada se cruza con la cuerda vista desde arriba, ya separada: solo suben los
        # cruces que lo piden, con el encima de la altura que tienen, y si están a la misma altura,
        # el del seguimiento (el de B para la gaza, cuyo cruce corre por la cuerda mientras crece).
        subir = []
        for ca, cb, seno, enc, w in cr:
            za, zb = np.interp(ca, s, G[:, 2]), np.interp(cb, s, G[:, 2])
            if abs(za - zb) >= 1.0 + b.holgura(ca, cb)[0]:
                continue
            subir.append((ca, cb, seno, enc if abs(za - zb) < 0.3 else bool(za > zb), w))
        G[:, 2] = np.maximum(G[:, 2], alturas(G, h, subir, b.holgura))
        if b.exacto is not None:
            G = b.exacto.copy()
        tramos = np.linalg.norm(np.diff(G, axis=0), axis=1) / h
        if tramos.min() < GAZA_TRAMOS[0] or tramos.max() > GAZA_TRAMOS[1]:
            return None
        guia.append(_cuadro_largo(G, h, np.full(N, RESORTE), manos, suelto=False,
                                  largos=_largos_de(A, B, float(_suave5(f / nf)))))
    a2, a3 = (int(round(GAZA_FASES[k][0] * nf)) for k in ("voltear", "crecer"))
    fases = {"bolsa": (0, a2 - 1), "voltear": (a2, a3 - 1), "crecer": (a3, nf)}
    guia += _asentado(A, B)
    fases["asentar"] = (nf + 1, len(guia) - 1)
    return Tramo(B.n, "gaza", A.X.copy(), B.X.copy(), guia, fases)


def _tramo_largo_firme(A: PoseVideo, B: PoseVideo, mano: bool = False, asentar: bool = True,
                       vel: float = VEL) -> Tramo:
    """La guía del paso A al B con largo fijo cuando B sigue igual hacia la punta y la cuerda que
    gana entra por el firme: cada nodo va en línea recta de su lugar en A al de B, con las alturas
    de los cruces y arranque y frenado de quinto grado. Si esa cuerda forma una gaza, como la gaza
    pequeña del as de guía, va antes por `_tramo_largo_gaza`: aquí la gaza se inflaba, el firme se
    ondulaba al correr y la gaza nacía de un gancho (T21c).

    Con `mano`, es un paso «punta» en el que la punta no pasa por ningún cruce nuevo (acercar el
    chicote a la gaza pequeña del as de guía): la mano toma la cuerda a PINZA de la punta y la
    lleva levantada hasta ALTO_MANO a mitad de camino, y lo de detrás baja en DETRAS_MANO. Por el
    aire y con lo de detrás suelto, el chicote se doblaba en un gancho (T21c). Sin `asentar`, no
    lleva el asentado del final (lo sigue otro tramo, como en `_tramo_largo_lazo`), y `vel` es la
    de lo que más se mueve."""
    h, N = B.h, len(B.X)
    S, Bx = A.X, B.X
    sig = np.arange(N) * h
    if mano:
        c = int(round(((N - 1) * h - PINZA) / h))
        manos = [0, c - 1, c, c + 1]
        uh = (N - 1) * h - PINZA
        alza = np.where(sig >= uh, 1.0, _suave(1 - (uh - sig) / DETRAS_MANO))
    else:
        manos = [0, N - 1]
        alza = np.zeros(N)
    mov = np.linalg.norm(Bx - S, axis=1)
    medio = mov[np.linalg.norm(Bx - np.array([_en(S, h, s + A.o - B.o) for s in np.arange(N) * h]),
                               axis=1) > 0.25]
    seg = max(ACOMODAR_MIN, float(medio.max()) / vel if len(medio) else 0.0, (A.o - B.o) / VEL_DESLIZAR)
    nf = max(int(round(seg * FPS)), 2)
    refs_A, refs_B = _referencia(S, h), _referencia(Bx, h)
    borr = []
    for f in range(nf + 1):
        u = float(_suave5(f / nf))
        env = math.sin(math.pi * u)
        G = S + u * (Bx - S)
        G[:, 2] += ALTO_MANO * env * alza
        borr.append(_Borrador(G=G, n=N, manos=manos, hasta=(N - 1) * h, mov=mov,
                              holgura=lambda a, b, env=env: (HOLGURA * env, 1.0),
                              exacto=Bx if f == nf else (S if f == 0 else None)))
    cruces = _seguir_cruces(borr, h, refs_A, refs_B, True)
    guia = []
    for f, (b, cr) in enumerate(zip(borr, cruces)):
        G = b.G.copy()
        G[:, 2] = alturas(G, h, cr, b.holgura)
        if b.exacto is not None:
            G = b.exacto.copy()
        guia.append(_cuadro_largo(G, h, np.full(N, RESORTE), manos, suelto=False,
                                  largos=_largos_de(A, B, float(_suave5(f / nf)))))
    fases = {"acomodar": (0, nf)}
    if asentar:
        guia += _asentado(A, B)
        fases["asentar"] = (nf + 1, len(guia) - 1)
    return Tramo(B.n, "mano" if mano else "firme", S.copy(), Bx.copy(), guia, fases)


def animar_largo(A: PoseVideo, B: PoseVideo, solido=None) -> Animado:
    """El tramo de la pose A a la B con largo fijo (T21): la guía, los cuadros del motor, el
    acercamiento final a la pose exacta y la comprobación de todos los cuadros: nada a menos de
    dmin ni atravesándose, la cantidad de nodos fija, el largo a ±0,5 % y, en un nudo libre, la
    secuencia declarada del tramo de la ficha al terminar."""
    import time

    from .cruces import secuencia_obtenida
    from .fisica.atar import comprobar, recta, seguir
    t0 = time.time()
    # Si la punta no pasa por ningún cruce nuevo, la mano la lleva y todo va guiado nodo a nodo;
    # con un anfitrión no, que la recta lo atravesaría.
    # Si el firme forma una gaza, se forma volteando una bolsa (sin un anfitrión, que la bolsa no
    # conoce); si no, lo que cambia va guiado nodo a nodo.
    if B.modo == "punta" and (B.enhebra or solido is not None):
        tr = _tramo_largo_enhebrar(A, B, solido)
    else:
        tr = ((_tramo_largo_gaza(A, B) if B.modo == "firme" and solido is None else None)
              or _tramo_largo_firme(A, B, mano=B.modo == "punta"))
    c = seguir(tr.x0, tr.guia, solido)
    fallas = []
    medidas = {"cuadros_guia": len(tr.guia), "esperas": c.esperas, "newton": c.newton,
               "segundos_seguir": round(time.time() - t0, 1)}
    x = c.X[-1]
    d = float(np.max(np.linalg.norm(x - B.X, axis=1)))
    medidas["distancia_final"] = round(d, 4)
    if d > LIMITE_FIN:
        fallas.append(f"Paso {B.n}: al final la cuerda queda a {d:.2f} d de la pose; el máximo es "
                      f"{LIMITE_FIN}.")
    if B.esperada is not None:
        a, b = B.tramo_ficha()
        xs = x[a:b + 1]
        obtenida = secuencia_obtenida(xs, B.h, encontrar_cruces(xs, B.h))
        if list(obtenida) != list(B.esperada):
            fallas.append(f"Paso {B.n}: al terminar de atarlo, la secuencia es {' '.join(obtenida)} "
                          f"y la declarada, {' '.join(B.esperada)}.")
    n_motor = len(c.X)
    X = list(c.X) + recta(x, B.X, max(1, int(round(ACERCAR_FIN * FPS))))
    fallas += [f"Paso {B.n}: {f}" for f in comprobar(X, solido, medio=c.medio)]
    if any(len(y) != len(B.X) for y in X):
        fallas.append(f"Paso {B.n}: la cuerda cambia de cantidad de nodos.")
    nominal = (len(B.X) - 1) * B.h
    largos = np.array([float(np.sum(np.linalg.norm(np.diff(y, axis=0), axis=1))) for y in X]) / nominal
    medidas["largo"] = (round(float(largos.min()), 4), round(float(largos.max()), 4))
    if largos.min() < 0.995 or largos.max() > 1.005:
        fallas.append(f"Paso {B.n}: el largo de la cuerda va de {largos.min():.4f} a {largos.max():.4f} "
                      "del nominal; el máximo es ±0,5 %.")
    fases = dict(tr.fases)
    fases["acercar"] = (n_motor, len(X) - 1)
    medidas["segundos_motor"] = round(time.time() - t0, 1)
    return Animado(B.n, tr.modo, X, {}, {}, fases, fallas, medidas)


def _solido_libre(spec, n: int):
    if spec.anfitrion is None:
        return None
    from .libre import _en_la_mesa
    return _en_la_mesa(spec.anfitrion, n).get("anfitrion")


def _animar_largo_paso(spec, A: PoseVideo, B: PoseVideo) -> Animado:
    return animar_largo(A, B, _solido_libre(spec, B.n))


# ==========================================================================
# Las plantillas con largo fijo: la cuerda sale de la mano (T21d)
# ==========================================================================
# En un amarre, la cuerda pasa por debajo de un palo que descansa sobre ella en la mesa, y ahí solo
# cabe la punta: una madeja en la mano no pasa, ni lo que saliera del cuadro por la mano (en las
# vueltas del amarre cuadrado, seis veces, con 2,8 a 3,3 m por atar). Gabriel eligió, el 27 nov, que
# la cuerda salga de la mano: la mano lleva lo que falta sin que se vea, y la cuerda nueva sale de ella
# mientras rodea los palos y queda quieta donde la dibuja el paso, como un cable que se tiende desde
# un carrete. La cuerda del video tiene siempre los mismos nodos, y lo que todavía está en la mano
# espera, sin dibujarse y sin chocar, en el lugar donde va a quedar: nada salta al aparecer, el largo
# de toda la cuerda no cambia y la trenza y el resaltado van pegados a ella. Cada pausa muestra la
# ficha hasta el hito y COLA_MANO de cola en la mano, por el camino del paso siguiente, así que nada
# se recoge ni se acomoda.
UNION_HITO = 12.0      # d: en la pausa, esto antes del hito la ficha pasa al camino del paso siguiente,
UNION_LARGO = 10.0     # en esto. Junto al hito, la ficha dobla hacia lo que cae a la mesa (hasta 1 d y
                       # 39° de diferencia con el paso siguiente), y lo atado se corre a lo largo de la
                       # cuerda de un paso al siguiente (en el amarre, hasta 0,7 d en los 40 d antes del
                       # hito). Con 2,5 d, los tramos de la unión quedaban de 0,8 a 1,2·h
VEL_PLANTILLA = 5.0    # d/s: la mano, en los primeros LENTO_PLANTILLA d de cada paso y al llegar
LENTO_PLANTILLA = 6.0  # d
VEL_REPETIR = 20.0     # d/s: lo demás de un paso (T21: en vez de la cámara rápida de T18)
VEL_SERIE = 30.0       # d/s: lo demás de un paso que repite el anterior (`hasta: vueltas`, `ahorcados`)
A_LATERAL = 200.0      # d/s²: en una curva, la mano va despacio para no pasar de esto (un brinco: 360)
A_LARGO = 35.0         # d/s²: los cambios de rapidez de la mano (una frenada en seco: 50)


def _en_v(X, h, s) -> np.ndarray:
    """`_en` para varios s a la vez."""
    X = np.asarray(X, float)
    u = np.clip(np.asarray(s, float) / h, 0.0, len(X) - 1)
    i = np.minimum(np.floor(u).astype(int), len(X) - 2)
    return X[i] + (u - i)[:, None] * (X[i + 1] - X[i])


def visibles(visible, h: float, N: int) -> int:
    """Cuántos nodos se ven con la cuerda hasta σ = `visible` (todos sin él)."""
    if visible is None:
        return N
    return min(N, int(math.floor(float(visible) / h + 1e-9)) + 1)


def cuerda_visible(X, h: float, visible) -> tuple[np.ndarray, np.ndarray]:
    """Lo que se ve de la cuerda X (N, 3) hasta σ = `visible`, donde sale de la mano (T21d), y el σ
    de cada punto: los nodos hasta ahí y la punta, entre el último y el siguiente. Si la punta queda
    a menos de 0,3·h del último nodo, lo reemplaza: un tramo tan corto doblaría la malla. Sin
    `visible`, toda la cuerda."""
    X = np.asarray(X, float)
    N = len(X)
    if visible is None:
        return X, np.arange(N) * h
    vis = float(visible)
    n = visibles(vis, h, N)
    s = np.arange(n) * h
    if n >= N or vis - s[-1] <= 1e-6:
        return X[:n], s
    # La punta va por una curva suave (de Catmull-Rom) entre los nodos de alrededor: en línea
    # recta, doblaba de golpe en cada nodo, y en una curva rápida temblaba.
    t = (vis - s[-1]) / h
    a, b = X[max(n - 2, 0)], X[min(n + 1, N - 1)]
    p0, p1 = X[n - 1], X[n]
    p = 0.5 * ((2 * p0) + (-a + p1) * t + (2 * a - 5 * p0 + 4 * p1 - b) * t * t
               + (-a + 3 * p0 - 3 * p1 + b) * t ** 3)
    if vis - s[-1] < 0.3 * h and n >= 2:
        return np.vstack([X[:n - 1], p]), np.append(s[:-1], vis)
    return np.vstack([X[:n], p]), np.append(s, vis)


def _serie(spec, n: int) -> bool:
    """En una plantilla, si el paso n repite el anterior (`vueltas`, `ahorcados`), como en
    `video._es_serie`."""
    if spec.plantilla is None or n > len(spec.pasos):
        return False
    hasta = spec.pasos[n - 1].hasta or ""
    return "-" not in hasta and hasta not in ("inicio", "cierre")


def poses_plantilla(modelo) -> list[PoseVideo]:
    """Las poses de los pasos de una plantilla en el video con largo fijo (T21d). La cuerda es la
    del último paso (en el amarre cuadrado, 462,5 d y 2314 nodos), en su grilla, y σ va desde el
    nodo 0. En la pausa de cada paso se ve la ficha hasta el hito y COLA_MANO de cola en la mano por
    el camino del paso siguiente; desde UNION_HITO d antes del hito, la ficha pasa a ese camino (la
    cola va tensa, y la ficha dobla ahí hacia lo que cae a la mesa). El último paso se ve entero. Lo que todavía está en la mano (después de `visible`)
    espera donde lo va a dejar el paso que lo tiende: lo que no se ve de una pose es lo mismo que en
    la siguiente."""
    P = modelo.pasos
    K = len(P)
    h = float(P[-1].h)
    Xf = [np.asarray(r.puntos, float) for r in P]
    hf = [float(r.h) for r in P]
    N = len(Xf[-1])
    L = (N - 1) * h
    sig = np.arange(N) * h
    hitos = [float(r.resaltado[1]) if r.resaltado and k < K - 1 else L for k, r in enumerate(P)]
    vis = [min(L, hitos[k] + COLA_MANO) if k < K - 1 else L for k in range(K)]
    for k in range(K - 1):
        if not hitos[k] < vis[k] <= hitos[k + 1] - UNION_HITO:
            raise TrazadoError(f"Paso {P[k + 1].n}: agrega {hitos[k + 1] - hitos[k]:.1f} d, menos que la "
                               f"cola en la mano ({COLA_MANO} d) y la unión ({UNION_HITO} d)")
    VIS = []
    for k in range(K):
        s = sig[:visibles(vis[k], h, N)]
        X = _en_v(Xf[k], hf[k], s)
        if k < K - 1:
            a = hitos[k] - UNION_HITO
            w = _suave5((s - a) / UNION_LARGO)
            X = X + w[:, None] * (_en_v(Xf[k + 1], hf[k + 1], s) - X)
            # Lo que queda de diferencia, repartido igual a lo largo de la curva mezclada: la trenza
            # no se aprieta ni se estira en un lugar.
            i0 = max(1, visibles(a - 0.5, h, N) - 1)
            i1 = min(len(X) - 2, visibles(a + UNION_LARGO + 0.5, h, N))
            X[i0:i1 + 1] = _uniforme(X[i0:i1 + 1], i1 - i0 + 1)
        VIS.append(X)
    out = []
    for k, r in enumerate(P):
        X = np.empty((N, 3))
        X[:len(VIS[k])] = VIS[k]
        for k2 in range(k + 1, K):
            X[len(VIS[k2 - 1]):len(VIS[k2])] = VIS[k2][len(VIS[k2 - 1]):]
        res = (float(r.resaltado[0]), float(r.resaltado[1])) if r.resaltado else None
        out.append(PoseVideo(r.n, X, h, 0.0, hitos[k], vis[k] - hitos[k], Xf[k], hf[k], res, r.esperada,
                             "mano", visible=vis[k]))
    return out


def comprobar_poses_plantilla(poses: list[PoseVideo], solido=None) -> list[str]:
    """Las fallas de las poses de una plantilla (T21d): otra cantidad de nodos, la ficha (hasta
    UNION_HITO antes del hito) a más de TOL_FICHA, tramos de la cuerda de menos de 0,9·h o de más
    de 1,1·h (un hueco o un amontonamiento en lo que espera en la mano), lo que se ve a menos de
    dmin o metido en la madera, y lo de la mano distinto en la pose siguiente."""
    from .fisica.asentar import contacto
    fallas = []
    N = len(poses[0].X)
    for i, p in enumerate(poses):
        X, h = p.X, p.h
        if len(X) != N:
            fallas.append(f"Paso {p.n}: la cuerda tiene {len(X)} nodos y no {N}.")
            continue
        ultimo = i == len(poses) - 1
        fin = p.largo - (0.0 if ultimo else UNION_HITO)
        F = p.ficha[np.arange(len(p.ficha)) * p.h_ficha <= fin + 1e-9]
        d = _distancia_a(F, X[:visibles(fin, h, N) + 1])
        if d > TOL_FICHA:
            fallas.append(f"Paso {p.n}: la ficha queda a {d:.3f} d de ella.")
        l = np.linalg.norm(np.diff(X, axis=0), axis=1)
        if l.min() < 0.9 * h or l.max() > 1.1 * h:
            fallas.append(f"Paso {p.n}: la cuerda tiene tramos de {l.min() / h:.2f} a {l.max() / h:.2f} h.")
        n = visibles(p.visible, h, N)
        Xv = X[:n]
        malla = contacto(Xv, np.array([0, n]), [1.0], solido)
        m = malla.margen(Xv)
        if m < -1e-9:
            fallas.append(f"Paso {p.n}: dos tramos quedan a {m + malla.dmin:.3f} d, menos de dmin.")
        if solido is not None and hasattr(solido, "penetracion"):
            pen = float(solido.penetracion(Xv))
            if pen > 0.1:
                fallas.append(f"Paso {p.n}: la cuerda entra {pen:.2f} d en la madera.")
        if not ultimo and np.max(np.abs(X[n:] - poses[i + 1].X[n:])) > 1e-9:
            fallas.append(f"Paso {p.n}: lo que está en la mano no es lo mismo en el paso siguiente.")
    return fallas


def _curvaturas(P) -> np.ndarray:
    """La curvatura de la polilínea P (M, 3) en cada punto, en el espacio (1/d)."""
    d = np.diff(np.asarray(P, float), axis=0)
    l = np.linalg.norm(d, axis=1)
    t = d / np.maximum(l, 1e-12)[:, None]
    giro = np.arccos(np.clip(np.einsum("ij,ij->i", t[:-1], t[1:]), -1.0, 1.0))
    k = giro / np.maximum((l[:-1] + l[1:]) / 2, 1e-12)
    return np.r_[k[0], k, k[-1]]


def _recorrido_plantilla(V, h: float, u0: float, u1: float, rapida: float) -> np.ndarray:
    """Dónde sale la cuerda de la mano (σ) en cada cuadro, de u0 a u1 por la cuerda V de la pose de
    llegada: a VEL_PLANTILLA en los primeros LENTO_PLANTILLA d, a `rapida` en lo demás y otra vez a
    VEL_PLANTILLA al llegar, más despacio en las curvas (para no pasar de A_LATERAL), con los
    cambios de rapidez repartidos (A_LARGO) y un arranque y un frenado de quinto grado, como
    `_recorrido_largo`."""
    if u1 - u0 < 1e-9:
        return np.array([u1])
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    paso = 0.02
    u = np.append(np.arange(u0, u1, paso), u1)
    s = np.arange(len(V)) * h
    w = 2 * max(1, int(round(1.0 / h))) + 1
    k = uniform_filter1d(maximum_filter1d(_curvaturas(V), w, mode="nearest"), w, mode="nearest")
    ku = np.interp(u, s, k)
    # Las rapideces van a lo largo del largo de verdad del camino, y no de σ: los tramos de la
    # unión miden hasta 1,1·h, y en sus bordes la punta cambiaba de rapidez de golpe.
    x = np.interp(u, s, _largos_acum(V))
    # Al llegar, a VEL_PLANTILLA lo que dura el frenado de quinto grado: montado sobre el de
    # A_LARGO, la rapidez cambiaba hasta 46 d/s².
    lento = (u - u0 < LENTO_PLANTILLA) | (u1 - u < VEL_PLANTILLA * ARRANQUE_LARGO)
    v = np.where(lento, VEL_PLANTILLA, rapida)
    v = np.maximum(np.minimum(v, np.sqrt(A_LATERAL / np.maximum(ku, 1e-9))), VEL_CRUCE)
    dx = np.diff(x)
    for i in range(1, len(v)):
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * A_LARGO * dx[i - 1]))
    for i in range(len(v) - 2, -1, -1):
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * A_LARGO * dx[i]))
    return _al_tiempo(u, v, x)


def _cuadro_plantilla(G, largos, k: float = RESORTE_FIN) -> CuadroGuia:
    """Un cuadro de la guía de una plantilla: todo guiado, sostenido por el nodo 0, con los largos
    de reposo de las poses y la forma de la guía de memoria. Los resortes van firmes (RESORTE_FIN):
    la cuerda queda quieta donde la deja la mano, y con los de siempre, al arrancar cada paso el
    motor la acomodaba unos 0,04 d y la punta frenaba en seco."""
    G = np.asarray(G, float)
    return CuadroGuia(G=G, k=np.full(len(G), float(k)), manos=np.array([0]),
                      largos=np.asarray(largos, float), curvatura=_curvatura_segura(G), largo_fijo=True)


def _tramo_plantilla(A: PoseVideo, B: PoseVideo, serie: bool = False) -> Tramo:
    """La guía del paso A al B de una plantilla (T21d): la cuerda sale de la mano por el camino de
    B y queda quieta donde la dibuja B (lo que todavía está en la mano ya espera ahí), y lo que ya
    se veía va de A a B nodo a nodo, en todo el paso. Cada cuadro guía solo lo que se ve, hasta el
    último nodo antes de la mano. Con los resortes firmes, no hace falta asentar al final."""
    h = B.h
    U = _recorrido_plantilla(B.X, h, A.visible, B.visible, VEL_SERIE if serie else VEL_REPETIR)
    F = len(U) - 1
    guia, vis = [], []
    for f, u in enumerate(U):
        w = float(_suave5(f / max(F, 1)))
        n = visibles(u, h, len(B.X))
        G = A.X[:n] + w * (B.X[:n] - A.X[:n])
        guia.append(_cuadro_plantilla(G, _largos_de(A, B, w)[:n - 1]))
        vis.append(float(u))
    return Tramo(B.n, "mano", A.X[:len(guia[0].G)].copy(), B.X.copy(), guia, {"tender": (0, F)}, visible=vis)


def animar_plantilla(A: PoseVideo, B: PoseVideo, solido=None, serie: bool = False) -> Animado:
    """El tramo de la pose A a la B de una plantilla con largo fijo (T21d): la guía, los cuadros del
    motor (solo lo que se ve: la cuerda crece desde la mano), el acercamiento final a la pose exacta
    y la comprobación de todos los cuadros: nada a menos de dmin ni atravesándose y, con lo que la
    mano todavía lleva esperando donde lo deja B, la cantidad de nodos fija y el largo de toda la
    cuerda a ±0,5 %. Da los cuadros con toda la cuerda y hasta dónde se ve en cada uno."""
    import time

    from .fisica.atar import SALTO, comprobar, recta, saltos, seguir
    t0 = time.time()
    tr = _tramo_plantilla(A, B, serie)
    c = seguir(tr.x0, tr.guia, solido)
    medidas = {"cuadros_guia": len(tr.guia), "esperas": c.esperas, "newton": c.newton,
               "segundos_seguir": round(time.time() - t0, 1)}
    tr.guia = None     # unos 70 MB en un paso largo del amarre: no hacen falta más
    fallas = []
    x = c.X[-1]
    n = len(x)
    d = float(np.max(np.linalg.norm(x - B.X[:n], axis=1)))
    medidas["distancia_final"] = round(d, 4)
    if d > LIMITE_FIN:
        fallas.append(f"Paso {B.n}: al final la cuerda queda a {d:.2f} d de la pose; el máximo es "
                      f"{LIMITE_FIN}.")
    n_motor = len(c.X)
    Y = list(c.X) + recta(x, B.X[:n], max(1, int(round(ACERCAR_FIN * FPS))))
    fallas += [f"Paso {B.n}: {f}" for f in comprobar(Y, solido, medio=c.medio, anadido=c.anadido)]
    sal = saltos(Y, anadido=c.anadido)
    medidas["salto_max"] = round(max(sal, default=0.0), 3)
    if max(sal, default=0.0) > SALTO:
        fallas.append(f"Paso {B.n}: un nodo salta {max(sal):.2f} d de un cuadro al siguiente; el máximo "
                      f"es {SALTO}.")
    # Toda la cuerda: lo que la mano todavía lleva espera donde lo deja B.
    X = [np.vstack([y, B.X[len(y):]]) for y in Y]
    vis = list(tr.visible) + [float(B.visible)] * (len(Y) - n_motor)
    nominal = (len(B.X) - 1) * B.h
    largos = np.array([float(np.sum(np.linalg.norm(np.diff(y, axis=0), axis=1))) for y in X]) / nominal
    medidas["largo"] = (round(float(largos.min()), 4), round(float(largos.max()), 4))
    if largos.min() < 0.995 or largos.max() > 1.005:
        fallas.append(f"Paso {B.n}: el largo de la cuerda va de {largos.min():.4f} a {largos.max():.4f} "
                      "del nominal; el máximo es ±0,5 %.")
    fases = dict(tr.fases)
    fases["acercar"] = (n_motor, len(X) - 1)
    medidas["segundos_motor"] = round(time.time() - t0, 1)
    return Animado(B.n, tr.modo, X, {}, {}, fases, fallas, medidas, visible=vis)


def _animar_plantilla_paso(spec, A: PoseVideo, B: PoseVideo) -> Animado:
    solido, _ = de_plantilla(spec, B.n)
    return animar_plantilla(A, B, solido, _serie(spec, B.n))
