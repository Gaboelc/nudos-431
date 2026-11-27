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


def _seguir_cruces(borradores, h, refs_A, refs_B, libre):
    """Los cruces de la guía vista desde arriba en cada cuadro, seguidos de un cuadro al
    siguiente, con su encima decidido para toda su vida: el de B si el cruce llega hasta el
    final, el de A si está desde el principio, el del tramo que más se mueve si no. Un cruce de
    A que llega a B con el encima al revés es una TrazadoError. Da, por cuadro, la lista de
    (sa, sb, seno, primera encima)."""
    por_cuadro = [encontrar_cruces(b.G, h) if libre else [] for b in borradores]
    pistas = []          # [primer cuadro, último cuadro, [(cuadro, k)], (sa, sb) del último]
    activas = []
    for f, cruces in enumerate(por_cuadro):
        nuevas = []
        libres = list(range(len(activas)))
        for k, c in enumerate(cruces):
            mejor, dmin = None, 1.0
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
    del 2 al 3… (o solo los que terminan en los pasos de `pasos`), cada uno en un proceso. Un
    nudo libre ata con largo fijo, entre las poses de `poses_video()` (T21); una plantilla,
    todavía entre las de `poses()` (T18)."""
    from .procesos import mapa
    if spec.plantilla is None:
        PV = poses_video(modelo)
        args = [(spec, A, B) for A, B in zip(PV[:-1], PV[1:]) if pasos is None or B.n in pasos]
        return [f.result() for f in mapa(_animar_largo_paso, args)]
    P = poses(modelo)
    args = [(spec, B.n, A.puntos, B.puntos, B.h, B.resaltado, B.esperada)
            for A, B in zip(P[:-1], P[1:]) if pasos is None or B.n in pasos]
    return [f.result() for f in mapa(_animar_paso, args)]


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
# Cada pausa muestra el tramo que dibuja la ficha, exacto, con un depósito de firme detrás (fuera
# del encuadre) y una cola de más delante de la punta: la que los pasos que siguen todavía van a
# usar. Entre dos pausas, la mano toma la cuerda cerca de la punta y la lleva por el aire hasta el
# camino nuevo, la enhebra por él y tira de la cola; lo que todavía no pasó queda suelto y
# cuelga con su peso.
DEPOSITO_FINAL = 0.0   # d de firme fuera del encuadre en el último paso, además de lo que el firme
                       # gana en el nudo (en el as de guía, 16,6 d al formar la gaza pequeña)
COLA_RADIO = 2.0       # d: el radio con que la cola de más dobla hacia su dirección
COLA_LIBRE = 1.5       # d: lo más cerca que la cola acostada pasa de la cuerda, vista desde arriba
COLA_JUNTO = 1.05      # d: lo que puede acercarse en su comienzo, junto a la punta de la ficha
COLA_ARRANQUE = 2.0    # d: lo que tarda en apartarse hasta COLA_LIBRE
COLA_SUBE = 1.0        # d: lo que tarda en empinarse la cola que no cabe en la mesa (la mano
                       # la levanta enseguida)
COLA_PENDIENTE = 1.73  # y lo que sube por cada d que avanza (60°): sale del cuadro, en la mano
TOL_FICHA = 0.02       # d: el tramo de la ficha, a esto de la ficha
PINZA = 1.5            # d: la mano toma la cuerda a esto de la punta, así que la punta se ve
PUNTA_GUIA = 2.0       # d: lo que lleva la mano, desde la punta
ENTRADA = 2.5          # d: la punta entra al camino nuevo esto antes de su primer cruce nuevo
ENTRADA_MIN = 1.5      # d: y al menos esto después de donde el paso se separa del anterior
VEL_AIRE = 10.0        # d/s: la mano que trae la punta por el aire (no enseña nada: rápido)
VEL_TIRAR = 10.0       # d/s: la mano que tira de la cola, ya enhebrada
SUAVIZAR = 1.0         # d: los cambios de velocidad de la mano se reparten en esto (dos veces)
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
    o + largo, la ficha remuestreada) y la cola de más (después de o + largo)."""
    n: int
    X: np.ndarray
    h: float
    o: float
    largo: float
    cola: float
    ficha: np.ndarray
    h_ficha: float
    resaltado: tuple | None    # en σ
    esperada: tuple | None
    modo: str | None = None    # cómo se llega desde la pose anterior: «punta» o «firme»
    r1: int | None = None      # en «punta», el primer nodo de la ficha que cambia
    arco: bool = False         # la cola no cabía en la mesa y va levantada

    @property
    def puntos(self) -> np.ndarray:
        return self.X

    def tramo_ficha(self) -> tuple[int, int]:
        """El primer y el último nodo dentro del tramo de la ficha."""
        a = int(math.ceil(self.o / self.h - 1e-9))
        b = min(len(self.X) - 1, int(math.floor((self.o + self.largo) / self.h + 1e-9)))
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
    """La cola de más que sale de la punta de la ficha Xf, con la dirección de su último tramo:
    acostada sobre la mesa en la primera dirección (seguir derecho, o doblar de a 15° a un lado y
    al otro) que, vista desde arriba, no pasa a menos de COLA_LIBRE de la cuerda; si ninguna cabe,
    en arco: se empina hasta COLA_PENDIENTE y sale del cuadro hacia arriba, como en una mano que
    la sostiene. Da los puntos (M, 3), su largo desde la punta (en el espacio) y si va en arco."""
    from scipy.spatial import cKDTree
    p0, t0, z0 = Xf[-1, :2], _direccion(Xf, hf, True, largo=hf), float(Xf[-1, 2])
    # La pendiente con que llega la punta (la que baja de un cruce): la cola la sigue, sin codo.
    pend0 = float((Xf[-1, 2] - Xf[-2, 2]) / max(np.linalg.norm(Xf[-1, :2] - Xf[-2, :2]), 1e-9))
    lejos = int(round(3.0 / hf))
    duros = [Xf[:max(0, len(Xf) - 1 - lejos)]] + [np.asarray(o, float) for o in otros if len(o)]
    duros = np.vstack(duros)
    giros = [0.0] + [s * math.radians(a) for a in range(15, 181, 15) for s in (1.0, -1.0)]

    def en_el_espacio(pts, z):
        P = np.column_stack([pts, z])
        return P, np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])

    def a_la_mesa(u):
        """La altura de la cola acostada: sale con la pendiente de la punta y se apoya en la
        mesa (una cúbica de Hermite)."""
        if abs(z0 - 0.5) < 1e-6 and abs(pend0) < 1e-6:
            return np.full(len(u), 0.5)
        Ld = max(0.4, 2.0 * abs(z0 - 0.5) / max(abs(pend0), 0.5))
        t = np.clip(u / Ld, 0.0, 1.0)
        z = ((2 * t ** 3 - 3 * t ** 2 + 1) * z0 + (t ** 3 - 2 * t ** 2 + t) * pend0 * Ld
             + (-2 * t ** 3 + 3 * t ** 2) * 0.5)
        return np.maximum(z, 0.5)      # nunca dentro de la mesa

    plano = cKDTree(duros[:, :2]) if len(duros) else None
    for g in giros:
        pts, u = _camino_cola(p0, t0, largo, g)
        pide = COLA_JUNTO + (COLA_LIBRE - COLA_JUNTO) * np.clip(u / COLA_ARRANQUE, 0, 1)
        if plano is None or np.all(plano.query(pts)[0] >= pide):
            return (*en_el_espacio(pts, a_la_mesa(u)), False)
    espacio = cKDTree(duros) if len(duros) else None
    # La punta puede estar apoyada sobre otra cuerda, más cerca que COLA_JUNTO: el arco arranca
    # pidiendo lo que ya tiene y en COLA_ARRANQUE llega a COLA_JUNTO.
    junto = min(COLA_JUNTO, float(espacio.query(Xf[-1])[0]) - 1e-3) if espacio is not None else COLA_JUNTO
    for g in giros:
        pts, u = _camino_cola(p0, t0, largo, g)
        pendiente = pend0 + (COLA_PENDIENTE - pend0) * _suave(np.clip(u / COLA_SUBE, 0, 1))
        z = z0 + np.concatenate([[0.0], np.cumsum(np.diff(u) * (pendiente[:-1] + pendiente[1:]) / 2)])
        P, l = en_el_espacio(pts, np.maximum(z, 0.5))
        pide = junto + (COLA_JUNTO - junto) * np.clip(u / COLA_ARRANQUE, 0, 1)
        if espacio is None or np.all(espacio.query(P)[0] >= pide):
            return P, l, True
    raise TrazadoError("la cola de más no cabe ni sobre la mesa ni en arco")


def _pose_video(Xf, hf, o, largo, cola, N, h):
    """La cuerda del video de una pose: el depósito sigue derecho al firme de la ficha, la ficha
    va remuestreada en la grilla del video y la cola sale de su punta (`_cola`)."""
    sig = np.arange(N) * h
    X = np.empty((N, 3))
    dep = sig < o - 1e-9
    if dep.any():
        d = _direccion(Xf, hf, False, largo=hf)
        X[dep, :2] = Xf[0, :2] + (o - sig[dep])[:, None] * d
        X[dep, 2] = Xf[0, 2]
    fin = o + largo
    co = sig > fin + 1e-9
    for j in np.flatnonzero(~dep & ~co):
        X[j] = _en(Xf, hf, sig[j] - o)
    arco = False
    if co.any():
        C, l, arco = _cola(Xf, hf, cola + h, [X[dep]])
        uu = sig[co] - fin
        for i in range(3):
            X[co, i] = np.interp(uu, l, C[:, i])
    return X, arco


def poses_video(modelo) -> list[PoseVideo]:
    """Las poses de los pasos en el video con largo fijo (T21b), de un nudo libre (con o sin
    anfitrión). El depósito R es lo que el firme gana en todo el nudo (los pasos «firme» de
    `alinear`), y la cuerda mide lo que el paso más largo necesita con lo que todavía le falta al
    firme: en el as de guía, el último paso, 109,8 d (550 nodos), con colas de más de 22,1,
    22,1, 25,1, 22,9, 14,8, 7,1 y 0 d."""
    spec = modelo.spec
    if spec.plantilla is not None:
        raise ValueError("las plantillas atan todavía con las poses de T18 (la madeja es T21d)")
    P = modelo.pasos
    h = float(P[-1].h)
    L = [(len(r.puntos) - 1) * float(r.h) for r in P]
    modos, r1s, gan = [None], [None], [0.0]
    for k in range(1, len(P)):
        A, B = np.asarray(P[k - 1].puntos, float), np.asarray(P[k].puntos, float)
        r = int(round(P[k].resaltado[0] / P[k].h)) if P[k].resaltado else 0
        modo, valor = alinear(A, B, r)
        modos.append(modo)
        r1s.append(int(valor) if modo == "punta" else None)
        gan.append(gan[-1] + (L[k] - L[k - 1] if modo == "firme" else 0.0))
    G = gan[-1]
    N = int(round((DEPOSITO_FINAL + max(L[k] + G - gan[k] for k in range(len(P)))) / h)) + 1
    total = (N - 1) * h
    out = []
    for k, r in enumerate(P):
        Xf = np.asarray(r.puntos, float)
        o = DEPOSITO_FINAL + G - gan[k]
        cola = max(0.0, total - o - L[k])
        try:
            X, arco = _pose_video(Xf, float(r.h), o, L[k], cola, N, h)
        except TrazadoError as e:
            raise TrazadoError(f"Paso {r.n}: {e}") from e
        res = (o + r.resaltado[0], o + r.resaltado[1]) if r.resaltado else None
        out.append(PoseVideo(r.n, X, h, o, L[k], cola, Xf, float(r.h), res, r.esperada,
                             modos[k], r1s[k], arco))
    return out


def poses_atado(modelo) -> list:
    """Las poses de las pausas del video, entre las que se ata: con largo fijo en un nudo libre
    (`poses_video`, T21) y las de T18 en una plantilla (`poses`, hasta la madeja de T21d)."""
    return poses(modelo) if modelo.spec.plantilla is not None else poses_video(modelo)


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
    """Las fallas de las poses del video: otra cantidad de nodos, el tramo de la ficha a más de
    TOL_FICHA de ella, la cola o el depósito que pasan por debajo de la cuerda (lo agregado solo
    pasa por encima) o un par a menos de dmin."""
    from .fisica.asentar import contacto
    fallas = []
    N = len(poses[0].X)
    for p in poses:
        X, h = p.X, p.h
        if len(X) != N:
            fallas.append(f"Paso {p.n}: la cuerda tiene {len(X)} nodos y no {N}.")
            continue
        a, b = p.tramo_ficha()
        d = _distancia_a(p.ficha, X[max(0, a - 1):b + 2])
        if d > TOL_FICHA:
            fallas.append(f"Paso {p.n}: el tramo de la ficha queda a {d:.3f} d de ella.")
        s = np.arange(N) * h
        lo, hi = p.o - 1e-6, p.o + p.largo + 1e-6
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
    tau = np.concatenate([[0.0], np.cumsum(np.diff(u) / ((v[:-1] + v[1:]) / 2))])
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


def _cuadro_largo(G, h, k, manos, suelto=True) -> CuadroGuia:
    N = len(G)
    k, curvatura = _aflojar(G, h, np.asarray(k, float), _curvatura_segura(G))
    if suelto:
        p, visc = _suelto_y_visc(k, manos)
    else:
        p, visc = None, None
    return CuadroGuia(G=G, k=k, manos=np.asarray(manos, int), largos=np.full(N - 1, float(h)),
                      curvatura=curvatura, largo_fijo=True, viscosidad=visc, suelto=p)


def _asentado(B: PoseVideo) -> list[CuadroGuia]:
    """El final de cada tramo: la guía en la pose de llegada y los resortes subiendo hasta
    RESORTE_FIN en ASENTAR s (reemplaza a `encajar`). La mano ya soltó."""
    out = []
    nA = max(1, int(round(ASENTAR * FPS)))
    for i in range(1, nA + 1):
        kk = RESORTE + (RESORTE_FIN - RESORTE) * (i / nA) ** 2
        out.append(_cuadro_largo(B.X.copy(), B.h, np.full(len(B.X), kk), [0], suelto=False))
    return out


def _tramo_largo_punta(A: PoseVideo, B: PoseVideo, solido=None) -> Tramo:
    """La guía del paso A al B con largo fijo, cuando B sigue el camino de A desde el firme y
    cambia hacia la punta (T21c). La mano toma la cuerda a PINZA de la punta, la lleva por el aire
    hasta el camino nuevo, la enhebra por él (los tramos de encima suben con `alturas`, como en
    T17) y tira de la cola hasta su lugar. Cada nodo que ya pasó la entrada sigue el camino que
    hizo la punta; lo que todavía no pasó queda suelto (sin resorte, con su peso) y se recoge solo
    al tirar. La pierna que va del nudo a la entrada vuelve a su lugar cuando queda poca cuerda
    por pasar."""
    h, N, o = B.h, len(B.X), B.o
    s_tip = (N - 1) * h
    u_fin = s_tip - o
    s0 = (B.r1 - 1) * B.h_ficha
    sig = np.arange(N) * h
    # El camino de llegada, desde σ = o: la ficha de B y su cola, en u = σ − o.
    nV = int(math.floor(u_fin / h + 1e-9)) + 1
    V = np.array([_en(B.X, h, o + i * h) for i in range(nV)])
    # Los cruces de A que cuentan son los del tramo que ya está donde va a quedar (hasta s0): lo
    # que sigue (la punta vieja y la cola de más) cambia de lugar, y un cruce suyo por encima
    # puede ser, en B, uno por debajo en el mismo lugar de la cuerda (la cola en arco del paso 6
    # del as de guía pasa sobre el firme por donde el paso 7 pasa debajo). Lo de B, sin el
    # depósito, que no entra en el camino.
    refs_A = [(a - o, b - o, e) for a, b, e in _referencia(A.X, h)
              if min(a, b) >= o - 1e-9 and max(a, b) - o < s0 - h]
    refs_B = [(a - o, b - o, e) for a, b, e in _referencia(B.X, h) if min(a, b) >= o - 1e-9]
    # Los cruces que la punta tiene que enhebrar: los del camino nuevo de la ficha. Los de la cola
    # de más van en arco, por encima de todo.
    nuevos = [c for c in refs_B if s0 - h <= max(c[0], c[1]) <= B.largo + 1e-6]
    primero = min((max(a, b) for a, b, _ in nuevos), default=None)
    s_ent = s0 + ENTRADA_MIN if primero is None else max(primero - ENTRADA, s0 + ENTRADA_MIN)
    s_ent = min(s_ent, u_fin)
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
    cerca = [max(a, b) for a, b, _ in nuevos]

    def vel(u):
        if u < s_ent:
            return VEL_AIRE
        if u <= B.largo:
            return VEL_CRUCE if min((abs(u - c) for c in cerca), default=math.inf) < CERCA_CRUCE else VEL
        return VEL_TIRAR

    U = _recorrido_largo(u_ini, u_fin, vel)
    F = len(U) - 1
    baja = max(1.0, ARRANQUE_LARGO * FPS)
    lifts = [float(_suave5((F - f) / baja)) for f in range(F + 1)]
    mira = ANTES_CRUCE + RAMPA
    uV = np.arange(nV) * h
    borr = []
    for f, ut in enumerate(U):
        n_v = int(math.floor(min(u_fin, max(s_ent, ut) + mira) / h + 1e-9)) + 1
        mv = np.zeros(n_v)
        mv[min(n_v, int(s0 / h)):] = 1.0
        G = V[:n_v].copy()
        # La mano lleva la punta levantada ALTO_MANO, y lo de detrás baja en DETRAS_MANO: va en
        # la guía antes de las alturas, para que el tramo de encima de un cruce suba por encima
        # de la punta levantada (como en T17). Si no, quedaban tocándose y la punta se trababa.
        u = uV[:n_v]
        uh = ut - PINZA
        mano = (u >= s_ent - 1e-9) & (u <= ut + 1e-9)
        w = np.where(u >= uh, 1.0, _suave(1 - (uh - u) / DETRAS_MANO))
        G[mano, 2] += ALTO_MANO * lifts[f] * w[mano]

        def hol(a, b, um=float(ut), lift=lifts[f]):
            nueva = max(a, b)
            if nueva < s0 - 1e-9:
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
    prefijo = sig <= o + s0 + 1e-9
    de_v = prefijo & (sig >= o - 1e-9)
    punta = sig >= s_tip - PUNTA_GUIA - 1e-9
    pierna_toda = ~prefijo & (sig <= o + s_ent + 1e-9)
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
        sel = (punta | enhebrado) & ~prefijo
        for j in np.flatnonzero(sel):
            u = uj[j]
            if u >= s_ent - 1e-9:
                p = _en(Vf, h, u)          # ya con la punta levantada
            elif u >= u_ini:
                p = np.array([np.interp(u - u_ini, lq, Q[:, i]) for i in range(3)])
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
        guia.append(_cuadro_largo(G, h, k, manos))
    fases = {"aire": (0, int(np.searchsorted(U, s_ent))),
             "enhebrar": (int(np.searchsorted(U, s_ent)), int(np.searchsorted(U, B.largo))),
             "tirar": (int(np.searchsorted(U, B.largo)), F)}
    guia += _asentado(B)
    fases["asentar"] = (F + 1, len(guia) - 1)
    return Tramo(B.n, "punta", A.X.copy(), B.X.copy(), guia, fases)


VEL_DESLIZAR = 8.0     # d/s: el firme que corre a lo largo de sí mismo


def _tramo_largo_firme(A: PoseVideo, B: PoseVideo) -> Tramo:
    """La guía del paso A al B con largo fijo cuando B sigue igual hacia la punta y la cuerda que
    gana entra por el firme (la gaza pequeña del as de guía, que se forma en el medio): cada nodo
    va en línea recta de su lugar en A al de B, con las alturas de los cruces y arranque y frenado
    de quinto grado. El firme, que es recto, corre así a lo largo de sí mismo desde el depósito;
    la gaza todavía se infla en vez de formarse (un rizo de su ángulo deja su extremo a 14-17 d de
    donde llega el firme, T21c)."""
    h, N = B.h, len(B.X)
    S, Bx = A.X, B.X
    mov = np.linalg.norm(Bx - S, axis=1)
    medio = mov[np.linalg.norm(Bx - np.array([_en(S, h, s + A.o - B.o) for s in np.arange(N) * h]),
                               axis=1) > 0.25]
    seg = max(ACOMODAR_MIN, float(medio.max()) / VEL if len(medio) else 0.0, (A.o - B.o) / VEL_DESLIZAR)
    nf = max(int(round(seg * FPS)), 2)
    refs_A, refs_B = _referencia(S, h), _referencia(Bx, h)
    borr = []
    for f in range(nf + 1):
        u = float(_suave5(f / nf))
        env = math.sin(math.pi * u)
        borr.append(_Borrador(G=S + u * (Bx - S), n=N, manos=[0, N - 1], hasta=(N - 1) * h, mov=mov,
                              holgura=lambda a, b, env=env: (HOLGURA * env, 1.0),
                              exacto=Bx if f == nf else (S if f == 0 else None)))
    cruces = _seguir_cruces(borr, h, refs_A, refs_B, True)
    guia = []
    for b, cr in zip(borr, cruces):
        G = b.G.copy()
        G[:, 2] = alturas(G, h, cr, b.holgura)
        if b.exacto is not None:
            G = b.exacto.copy()
        guia.append(_cuadro_largo(G, h, np.full(N, RESORTE), [0, N - 1], suelto=False))
    fases = {"acomodar": (0, nf)}
    guia += _asentado(B)
    fases["asentar"] = (nf + 1, len(guia) - 1)
    return Tramo(B.n, "firme", S.copy(), Bx.copy(), guia, fases)


def animar_largo(A: PoseVideo, B: PoseVideo, solido=None) -> Animado:
    """El tramo de la pose A a la B con largo fijo (T21): la guía, los cuadros del motor, el
    acercamiento final a la pose exacta y la comprobación de todos los cuadros: nada a menos de
    dmin ni atravesándose, la cantidad de nodos fija, el largo a ±0,5 % y, en un nudo libre, la
    secuencia declarada del tramo de la ficha al terminar."""
    import time

    from .cruces import secuencia_obtenida
    from .fisica.atar import comprobar, recta, seguir
    t0 = time.time()
    tr = _tramo_largo_punta(A, B, solido) if B.modo == "punta" else _tramo_largo_firme(A, B)
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
