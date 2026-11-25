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
from .fisica.atar import FPS, RESORTE, CuadroGuia
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


def _cuadro(G, h, manos, plantilla=None, hasta=None, ultimo=None, cambio=0):
    N = len(G)
    largos = np.full(N - 1, float(h))
    if ultimo is not None:
        largos[-1] = ultimo
    if plantilla is not None:
        from .fisica.asentar import material_de
        T = plantilla(N, hasta)[:N - 1]
        largos = largos / (1 + T / material_de(1.0).EA)
    return CuadroGuia(G=G, k=np.full(N, RESORTE), manos=np.asarray(manos, int), largos=largos,
                      curvatura=Varilla.curvatura_de(G), cambio=cambio)


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
        guia.append(_cuadro(G, h, b.manos, plantilla, b.hasta, b.ultimo, b.cambio))
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
                                  mov=np.zeros(m), holgura=sin_holgura,
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
    X = c.X + enc + recta(enc[-1], B, max(1, round(RECTA * FPS)))
    fallas += [f"Paso {n}: {f}" for f in comprobar(X, solido, c.partido, c.quitado, c.medio)]
    fases = dict(tr.fases)
    fases["encaje"] = (len(c.X), len(X) - 1)
    medidas["segundos_motor"] = round(time.time() - t0, 1)
    medidas["segundos_seguir"] = round(t_seguir, 1)
    saltos = [float(np.max(np.linalg.norm(b - a, axis=1))) for a, b in zip(X[:-1], X[1:])
              if len(a) == len(b)]
    medidas["salto_max"] = round(max(saltos, default=0.0), 3)
    return Animado(n, tr.modo, X, c.partido, c.quitado, fases, fallas, medidas)


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


def animar(spec, modelo, pasos=None) -> list[Animado]:
    """Los tramos animados de un nudo ya construido con el motor (`modelo`): del paso 1 al 2,
    del 2 al 3… (o solo los que terminan en los pasos de `pasos`), cada uno en un proceso."""
    from .procesos import mapa
    P = modelo.pasos
    args = [(spec, B.n, A.puntos, B.puntos, B.h, B.resaltado, B.esperada)
            for A, B in zip(P[:-1], P[1:]) if pasos is None or B.n in pasos]
    return [f.result() for f in mapa(_animar_paso, args)]
