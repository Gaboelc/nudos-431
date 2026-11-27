"""El diseño sonoro de los videos (T23c): qué suena, cuándo y dónde, desde el motor y la cámara.

Parte de los tres efectos que Gabriel aprobó en T18 (nudos/audio.py: el clic de cada tarjeta, el
golpe del apretado y el roce de la cuerda) y los afina:

- **El roce** sigue la presión de cada contacto y la rapidez con que se desliza: la rapidez da
  cuántos granos suenan por segundo, y la presión, su fuerza. La presión sale de cuánto se acercan
  los ejes (de dos partes de la cuerda, de la cuerda y el anfitrión, de la cuerda y la mesa), que
  es como empuja el contacto del motor (IPC): más cuanto más cerca.
- **El «tac»:** cuando un tramo de cuerda cae sobre la mesa, más fuerte cuanto más rápido llega y
  cuanto más largo se apoya.
- **El crujido** al apretar: granos graves y resonantes mientras la cuerda se desliza apretada
  contra sí misma o contra el anfitrión.
- **Los soplidos,** suaves: en cada movimiento de cámara que se nota (más agudo cuanto más rápido
  se mueve la imagen, y de un lado al otro, como se mueve) y cuando entra una tarjeta.

Cada sonido es un `Sonido`: su audio mono, ya a su nivel; cuándo empieza, y dónde se ve en el
cuadro, de −1 (izquierda) a 1 (derecha), con la cámara de cada cuadro. nudos/mezcla.py los pone
en estéreo, en una sala chica, con la voz y la música.

De dónde salen:
- `del_motor(cuadros, fps, h, mallas)`: el roce, los tacs y el crujido, de las posiciones de
  cada cuadro (como las de nudos/video.py: `X`, `fase` y `camara`).
- `de_la_camara(cuadros, fps)`: los soplidos de la cámara.
- `de_eventos(eventos)`: las tarjetas (un soplido y el clic, justo cuando aparece la tarjeta) y el
  golpe. `eventos_de_cuadros()` los saca de los cuadros de hoy (T18): una tarjeta en cada cambio de
  título y el golpe en el último cuadro del apretado. T22 da los suyos.

Todo se sintetiza aquí, sin grabaciones, con una semilla fija: sale igual cada vez. Los tics de
los cruces que se probaron en T23c (uno por cada cruce nuevo, agudo por encima y grave por
debajo) se quitaron: Gabriel no los quiso al oírlos (26 nov).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import audio as A

SR = A.SR
SEMILLA = 431

# El pico de cada sonido, en dBFS, en la mezcla antes del máster (con la voz a −16 LUFS y la
# música sola a −22; ver nudos/mezcla.py). El máster sube o baja todo junto. Con la música, el roce
# de T18 (los granos 8 dB bajo el clic) quedaba unos 17 dB bajo ella y casi no se oía: aquí va 5 dB
# más arriba. Son una primera estimación medida, sin oír: se ajustan aquí.
NIVELES = {"clic": -15.0, "golpe": -9.0, "soplido": -24.0, "soplido_tarjeta": -26.0, "tac": -17.0,
           "crujido": -20.0, "grano": -20.0, "roce_pico": -12.0}
SALA = {"clic": 0.10, "golpe": 0.18, "soplido": 0.25, "tac": 0.20, "crujido": 0.15, "roce": 0.18}

# Los contactos (en d, el diámetro de la cuerda).
DIAMETRO = 1.0             # dos ejes a esta distancia apenas se tocan
RADIO = 0.5
CONTACTO = A.CONTACTO      # dos ejes a menos de esto se tocan
TOCA_SOLIDO = A.TOCA_SOLIDO
SOBRE_LA_MESA = A.SOBRE_LA_MESA
SEPARACION = A.SEPARACION
QUIETA = A.QUIETA

TAC_RAPIDEZ = 1.5          # d/s: un nodo que llega a la mesa más lento no suena
TAC_MIN = 0.5              # d²/s: el impacto (Σ rapidez de caída × largo) más chico que suena
TAC_REF = 6.0              # d²/s: un impacto así suena a su nivel
TAC_ENTRE = 0.12           # s: dos tacs más cerca que esto son uno

CRUJIDO = dict(f=(170, 620), q=(8.0, 16.0), cuerpo=(85, 170), cuerpo_amp=0.35, ruido=0.12, gan=1.0)
CRUJIDO_MIN = 0.4          # d²/s: el apretado (Σ presión² × deslizamiento × largo) desde el que cruje

SOPLIDO_MIN = 0.18         # medio cuadro por segundo: la imagen que se mueve más lento no sopla
SOPLIDO_PLENO = 1.6        # medio cuadro por segundo: así sopla a su nivel
SOPLIDO_PICO_MIN = 0.35    # un movimiento cuyo máximo no llega a esto no sopla

ANCHO_TARJETA = {"horizontal": -0.35, "previa": -0.35, "vertical": 0.0}   # dónde están las tarjetas de T18


@dataclass
class Sonido:
    """Un sonido puesto en el video: su audio mono a SR (ya a su nivel), cuándo empieza (s),
    dónde se ve (x de −1 a 1; un arreglo del largo del audio si se mueve), cuánto va a la sala,
    su bus («efectos» o «foley») y qué es."""
    t: float
    audio: np.ndarray
    x: float | np.ndarray = 0.0
    sala: float = 0.15
    bus: str = "efectos"
    tipo: str = ""
    golpe: float = 0.0     # s desde `t` hasta su ataque (lo que tiene que caer en sincronía)

    @property
    def ataque(self) -> float:
        return self.t + self.golpe


@dataclass
class Evento:
    """Algo que pasa en el video y suena: «tarjeta» (aparece una tarjeta: un soplido y el clic,
    justo en `t`) o «golpe» (el nudo queda apretado). `x` dice dónde, de −1 a 1."""
    tipo: str
    t: float
    x: float = 0.0
    fuerza: float = 1.0


@dataclass
class Contactos:
    """Lo que el motor deja oír, por cuadro: por canal («cuerda», «anfitrion», «mesa»), el roce
    (Σ rapidez de deslizamiento × largo, d²/s), el largo que roza moviéndose (d), su presión media
    (de 0 a 1) y dónde (el centro de lo que roza, pesado por roce y presión; NaN si nada); el
    apretado de la cuerda contra sí misma (Σ presión² × deslizamiento × largo) y los tacs (cuadro,
    impacto en d²/s y dónde). El apretado suma también la cuerda apretada contra el anfitrión."""
    roce: dict
    largo: dict
    presion: dict
    donde: dict
    apretado: np.ndarray
    tacs: list = field(default_factory=list)


def db(x: float) -> float:
    return 10 ** (x / 20)


# --------------------------------------------------------------------------
# Dónde se ve cada cosa
# --------------------------------------------------------------------------
def _camaras(cuadros) -> list[tuple[np.ndarray, np.ndarray, float, float] | None]:
    """Por cuadro: (R, pos, tan(fov/2), aspecto) de su cámara, o None si no tiene."""
    from .prueba_atar import _mirar
    out = []
    for c in cuadros:
        cam = getattr(c, "camara", None)
        if not cam:
            out.append(None)
            continue
        M = _mirar(np.asarray(cam["pos"], float), np.asarray(cam["target"], float))
        out.append((M[:3, :3], M[:3, 3], math.tan(math.radians(cam["fov"]) / 2), float(cam["aspecto"])))
    return out


def _proyectar(P, cam) -> np.ndarray:
    """Los puntos P (n, 3) en el cuadro: (n, 2) con x e y de −1 a 1 (y hacia arriba)."""
    R, pos, th, asp = cam
    q = (np.atleast_2d(np.asarray(P, float)) - pos) @ R
    z = np.minimum(q[:, 2], -1e-6)
    return np.column_stack([q[:, 0] / (-z * th * asp), q[:, 1] / (-z * th)])


def pantalla(P, cam) -> float:
    """La x en el cuadro (de −1 a 1) del punto P con la cámara de un cuadro (`_camaras`); 0 sin
    cámara."""
    if cam is None or P is None or not np.all(np.isfinite(P)):
        return 0.0
    return float(np.clip(_proyectar(P, cam)[0, 0], -1.0, 1.0))


def _x_por_muestra(xs_cuadro: np.ndarray, fps: float, n: int) -> np.ndarray:
    """La x de cada cuadro, llevada a cada muestra; los cuadros sin dato toman el más cercano."""
    xs = np.asarray(xs_cuadro, float)
    ok = np.isfinite(xs)
    if not ok.any():
        return np.zeros(n)
    k = np.arange(len(xs))
    xs = np.interp(k, k[ok], xs[ok])
    return np.interp(np.arange(n) / SR * fps, k, xs)


# --------------------------------------------------------------------------
# Lo que mide el motor en cada cuadro
# --------------------------------------------------------------------------
def _pares(A0, B0) -> tuple[np.ndarray, np.ndarray]:
    """Los nodos de dos cuadros seguidos, emparejados: al dar o recoger cuerda cambia la punta;
    al entrar cuerda por el firme, el firme (como en nudos/audio.py)."""
    A0, B0 = np.asarray(A0, float), np.asarray(B0, float)
    if len(A0) == len(B0):
        return A0, B0
    n = min(len(A0), len(B0))
    ini = np.median(np.linalg.norm(B0[:n] - A0[:n], axis=1))
    fin = np.median(np.linalg.norm(B0[-n:] - A0[-n:], axis=1))
    return (A0[:n], B0[:n]) if ini <= fin else (A0[-n:], B0[-n:])


def _presion(brecha, toca: float, lejos: float) -> np.ndarray:
    """De 0 (apenas se toca, a `lejos`) a 1 (apretado, a `toca` o menos)."""
    return np.clip((lejos - np.asarray(brecha, float)) / (lejos - toca), 0.0, 1.0)


def medir(cuadros, fps: float, h: float, solidos=()) -> Contactos:
    """Lo que el motor deja oír en cada cuadro (ver `Contactos`). `solidos` son muestras de la
    superficie del anfitrión con su normal (`blender._muestras_solidos`)."""
    from scipy.spatial import cKDTree
    sep = int(np.ceil(SEPARACION / h))
    K = len(cuadros)
    canales = ("cuerda", "anfitrion", "mesa")
    roce = {c: np.zeros(K) for c in canales}
    largo = {c: np.zeros(K) for c in canales}
    presion = {c: np.zeros(K) for c in canales}
    donde = {c: np.full((K, 3), np.nan) for c in canales}
    apretado = np.zeros(K)
    tacs = []
    arboles = [(cKDTree(P), N, P) for P, N in solidos]

    def sumar(k, canal, rel, p, puntos):
        roce[canal][k] = float(rel.sum() * h)
        largo[canal][k] = float((rel > QUIETA).sum() * h)
        if rel.sum() > 1e-9:
            presion[canal][k] = float((p * rel).sum() / rel.sum())
            w = rel * (0.25 + p)
            donde[canal][k] = (puntos * w[:, None]).sum(axis=0) / w.sum()

    for k in range(1, K):
        A0, B0 = _pares(cuadros[k - 1].X, cuadros[k].X)
        v = (B0 - A0) * fps
        rapidez = np.linalg.norm(v, axis=1)
        # El tac: lo que llega a la mesa desde arriba, cayendo.
        llega = (A0[:, 2] >= SOBRE_LA_MESA) & (B0[:, 2] < SOBRE_LA_MESA) & (-v[:, 2] > TAC_RAPIDEZ)
        if llega.any():
            tacs.append((k, float((-v[llega, 2]).sum() * h), B0[llega].mean(axis=0)))
        if rapidez.max() < QUIETA:
            continue
        N = len(B0)
        # Con otra parte de la cuerda: el vecino más cercano que no es la misma parte.
        d, idx = cKDTree(B0).query(B0, k=32, distance_upper_bound=CONTACTO)
        valido = np.isfinite(d) & (idx < N) & (np.abs(idx - np.arange(N)[:, None]) > sep)
        tiene = valido.any(axis=1)
        if tiene.any():
            col = np.argmax(valido, axis=1)
            j = idx[np.arange(N), col][tiene]
            dist = d[np.arange(N), col][tiene]
            rel = np.linalg.norm(v[tiene] - v[j], axis=1)
            p = _presion(dist, DIAMETRO, CONTACTO)
            sumar(k, "cuerda", rel, p, B0[tiene])
            apretado[k] = float((p ** 2 * rel).sum() * h)
        # Con el anfitrión: el eje cerca del plano tangente del punto más cercano de su superficie.
        alto = np.full(N, np.inf)
        for arbol, normales, P in arboles:
            _, q = arbol.query(B0)
            hh = np.einsum("ij,ij->i", B0 - P[q], normales[q])
            alto = np.where((hh > 0) & (hh < alto), hh, alto)
        toca = alto < TOCA_SOLIDO
        if toca.any():
            p = _presion(alto[toca], RADIO, TOCA_SOLIDO)
            sumar(k, "anfitrion", rapidez[toca], p, B0[toca])
            apretado[k] += float((p ** 2 * rapidez[toca]).sum() * h)
        # Con la mesa: lo que está apoyado y se arrastra.
        mesa = B0[:, 2] < SOBRE_LA_MESA
        if mesa.any():
            sumar(k, "mesa", np.linalg.norm(v[mesa, :2], axis=1),
                  _presion(B0[mesa, 2], RADIO, SOBRE_LA_MESA), B0[mesa])
    return Contactos(roce, largo, presion, donde, apretado, tacs)


# --------------------------------------------------------------------------
# Los sonidos
# --------------------------------------------------------------------------
def tac(rng) -> np.ndarray:
    """La cuerda que cae sobre la mesa de madera: un golpe sordo, la madera y un chasquido."""
    d = int(0.10 * SR)
    t = np.arange(d) / SR
    ruido = rng.standard_normal(d)
    cuerpo = A._resonador(ruido * np.exp(-t / 0.004), rng.uniform(170, 240), 2.5)
    madera = A._resonador(ruido * np.exp(-t / 0.002), rng.uniform(900, 1300), 6.0)
    s = cuerpo / np.abs(cuerpo).max() * np.exp(-t / 0.030)
    s += 0.45 * madera / np.abs(madera).max() * np.exp(-t / 0.012)
    s += 0.20 * A._filtro(ruido, "high", 3500) * np.exp(-t / 0.0015)
    s *= np.minimum(1.0, t / 0.0004)
    return s / np.abs(s).max()


def _ruido_por_bandas(n: int, centro_hz: np.ndarray, rng) -> np.ndarray:
    """Ruido cuyo color sigue `centro_hz` muestra por muestra: un banco de bandas fijas que se
    funden según el centro (sin filtros que cambian en cada muestra)."""
    from scipy.signal import butter, sosfilt
    bandas = np.geomspace(250, 4000, 7)
    ruido = rng.standard_normal(n)
    pos = np.interp(np.log(np.clip(centro_hz, bandas[0], bandas[-1])), np.log(bandas), np.arange(len(bandas)))
    out = np.zeros(n)
    for i, fc in enumerate(bandas):
        w = np.clip(1.0 - np.abs(pos - i), 0.0, 1.0)
        if not w.any():
            continue
        sos = butter(2, [fc / 1.45, min(fc * 1.45, SR / 2.2)], btype="band", fs=SR, output="sos")
        out += w * sosfilt(sos, ruido)
    return out


def soplido(env: np.ndarray, rng, agudo: float = 1.0) -> np.ndarray:
    """Un soplido con la envolvente `env` (de 0 a 1, por muestra): más fuerte y más agudo donde
    la envolvente sube."""
    centro = 350.0 + 1500.0 * agudo * np.clip(env, 0, 1)
    s = _ruido_por_bandas(len(env), centro, rng) * np.clip(env, 0, 1) ** 1.5
    pico = np.abs(s).max()
    return s / pico if pico > 0 else s


def _tarjeta(ev: Evento, rng) -> list[Sonido]:
    """El soplido de la tarjeta (sube hasta que aparece y se apaga en 80 ms) y el clic, justo
    cuando aparece."""
    antes, despues = 0.22, 0.10
    n = int((antes + despues) * SR)
    t = np.arange(n) / SR - antes
    env = np.where(t < 0, (1 + t / antes) ** 2, np.exp(-t / 0.035))
    s = soplido(env, rng, agudo=0.9) * db(NIVELES["soplido_tarjeta"]) * ev.fuerza
    clic = A.clic(rng) * db(NIVELES["clic"]) * ev.fuerza
    return [Sonido(ev.t - antes, s, ev.x, SALA["soplido"], "efectos", "soplido", golpe=antes),
            Sonido(ev.t, clic, ev.x, SALA["clic"], "efectos", "clic")]


def de_eventos(eventos, semilla: int = SEMILLA) -> list[Sonido]:
    """Los sonidos de las tarjetas y del golpe."""
    rng = np.random.default_rng(semilla + 1)
    out = []
    for ev in sorted(eventos, key=lambda e: e.t):
        if ev.tipo == "tarjeta":
            out += _tarjeta(ev, rng)
        elif ev.tipo == "golpe":
            out.append(Sonido(ev.t, A.golpe(rng) * db(NIVELES["golpe"]) * ev.fuerza, ev.x, SALA["golpe"],
                              "efectos", "golpe"))
        else:
            raise ValueError(f"no sé cómo suena un evento «{ev.tipo}»")
    return out


def eventos_de_cuadros(cuadros, fps: float, x_tarjeta: float = ANCHO_TARJETA["horizontal"]) -> list[Evento]:
    """Los eventos de los cuadros de hoy (T18): una tarjeta en cada cambio de título, justo en el
    primer cuadro del título nuevo, y el golpe en el último cuadro del apretado, donde se ve el
    nudo."""
    ev = [Evento("tarjeta", k / fps, x_tarjeta) for k in range(1, len(cuadros))
          if cuadros[k].titulo != cuadros[k - 1].titulo]
    apretar = [k for k, c in enumerate(cuadros) if c.fase == "apretar"]
    if apretar:
        k = apretar[-1]
        X = np.asarray(cuadros[k].X, float)
        ev.append(Evento("golpe", k / fps, pantalla(X.mean(axis=0), _camaras([cuadros[k]])[0])))
    return ev


def del_motor(cuadros, fps: float, h: float, mallas=(), semilla: int = SEMILLA) -> list[Sonido]:
    """El roce (un sonido por canal, que se mueve por el cuadro con lo que roza), los tacs y el
    crujido del apretado."""
    from .blender import _muestras_solidos
    rng = np.random.default_rng(semilla)
    K = len(cuadros)
    n = int(np.ceil(K / fps * SR))
    cams = _camaras(cuadros)
    con = medir(cuadros, fps, h, _muestras_solidos(list(mallas)) if mallas else ())
    out: list[Sonido] = []
    # El roce: la rapidez da los granos por segundo; la presión, su fuerza.
    for canal, p in A.CANALES.items():
        r = con.roce[canal]
        tasa = np.where(r > QUIETA, np.clip(60.0 * r ** 0.6, 0, p["tope"]), 0.0)
        tasa = np.convolve(tasa, [0.25, 0.5, 0.25], mode="same")
        if not tasa.any():
            continue
        rapidez = r / np.maximum(con.largo[canal], h)
        amp = np.clip((rapidez / 5.0) ** 0.25, 0.6, 1.25) * (0.55 + 0.6 * con.presion[canal])
        x = A._granos(tasa, amp, fps, A._prototipos(rng, 48, p), rng, n)
        x = A._filtro(A._filtro(x, "high", 90), "low", 9000) * p["gan"] * db(NIVELES["grano"])
        x = A._limitar(x, NIVELES["roce_pico"])
        xs = np.array([pantalla(con.donde[canal][k], cams[k]) if np.isfinite(con.donde[canal][k]).all()
                       else np.nan for k in range(K)])
        out.append(Sonido(0.0, x, _x_por_muestra(xs, fps, n), SALA["roce"], "foley", "roce"))
    # Los tacs: los impactos de un mismo momento se suman en uno.
    ultimo = -1e9
    for k, imp, P in con.tacs:
        if imp < TAC_MIN:
            continue
        if (k - ultimo) / fps < TAC_ENTRE:
            continue
        ultimo = k
        fuerza = float(np.clip((imp / TAC_REF) ** 0.5, 0.35, 1.2))
        out.append(Sonido(k / fps, tac(rng) * db(NIVELES["tac"]) * fuerza, pantalla(P, cams[k]), SALA["tac"],
                          "foley", "tac"))
    # El crujido: la cuerda que se desliza apretada contra sí misma o contra el anfitrión, mientras
    # se aprieta.
    apretar = np.array([c.fase == "apretar" for c in cuadros])
    drive = np.where(apretar, con.apretado, 0.0)
    if (drive > CRUJIDO_MIN).any():
        ref = max(float(np.percentile(drive[drive > CRUJIDO_MIN], 90)), CRUJIDO_MIN * 2)
        u = np.clip(drive / ref, 0, 1.3)
        tasa = np.where(drive > CRUJIDO_MIN, 35.0 + 90.0 * u ** 0.5, 0.0)
        protos = A._prototipos(rng, 32, {**CRUJIDO, "tope": 140.0})
        x = A._granos(tasa, np.clip(u ** 0.5, 0.3, 1.1), fps, protos, rng, n, jitter=0.15)
        x = A._filtro(x, "high", 70) * db(NIVELES["crujido"])
        lugar = np.where(np.isfinite(con.donde["cuerda"]), con.donde["cuerda"], con.donde["anfitrion"])
        xs = np.array([pantalla(lugar[k], cams[k]) if np.isfinite(lugar[k]).all() else np.nan for k in range(K)])
        out.append(Sonido(0.0, x, _x_por_muestra(xs, fps, n), SALA["crujido"], "foley", "crujido"))
    return out


def velocidad_imagen(cuadros, fps: float) -> tuple[np.ndarray, np.ndarray]:
    """Por cuadro, cuánto se mueve la imagen por la cámara (no por la cuerda), en medios cuadros
    por segundo, y hacia dónde en x: los mismos puntos de la cuerda vistos con la cámara de un
    cuadro y la del siguiente."""
    cams = _camaras(cuadros)
    K = len(cuadros)
    rap, dx = np.zeros(K), np.zeros(K)
    for k in range(K - 1):
        if cams[k] is None or cams[k + 1] is None:
            continue
        X = np.asarray(cuadros[k].X, float)
        P = X[::max(1, len(X) // 40)]
        a, b = _proyectar(P, cams[k]), _proyectar(P, cams[k + 1])
        dentro = (np.abs(a) < 1.2).all(axis=1)
        if not dentro.any():
            continue
        dd = (b - a)[dentro] * fps
        rap[k] = float(np.linalg.norm(dd, axis=1).mean())
        dx[k] = float(dd[:, 0].mean())
    if K > 1:
        rap[-1], dx[-1] = rap[-2], dx[-2]
    return rap, dx


def de_la_camara(cuadros, fps: float, semilla: int = SEMILLA) -> list[Sonido]:
    """Un soplido suave en cada movimiento de cámara que se nota: sube y baja con la rapidez de la
    imagen, y va de un lado al otro como se mueve."""
    rng = np.random.default_rng(semilla + 2)
    rap, dx = velocidad_imagen(cuadros, fps)
    activo = rap > SOPLIDO_MIN
    out = []
    k = 0
    K = len(cuadros)
    while k < K:
        if not activo[k]:
            k += 1
            continue
        j = k
        while j < K and activo[j]:
            j += 1
        tramo = rap[k:j]
        if tramo.max() >= SOPLIDO_PICO_MIN:
            # La envolvente por muestra, con un margen para que entre y salga suave.
            m0, m1 = max(0, k - 3), min(K, j + 3)
            r = rap[m0:m1]
            env_c = np.clip((r - SOPLIDO_MIN) / (SOPLIDO_PLENO - SOPLIDO_MIN), 0, 1)
            n = int((m1 - m0) / fps * SR)
            tt = np.arange(n) / SR * fps
            env = np.interp(tt, np.arange(m1 - m0), env_c)
            fuerza = float(np.clip(tramo.max() / SOPLIDO_PLENO, 0.4, 1.0))
            s = soplido(env, rng, agudo=fuerza) * db(NIVELES["soplido"]) * fuerza
            # De un lado al otro: la imagen va hacia `sentido`, y el soplido con ella.
            sentido = 1.0 if dx[k:j].sum() >= 0 else -1.0
            avance = np.cumsum(r) / max(r.sum(), 1e-9)
            xs = sentido * (np.interp(tt, np.arange(m1 - m0), avance) - 0.5) * 0.9
            out.append(Sonido(m0 / fps, s, xs, SALA["soplido"], "efectos", "soplido_camara"))
        k = j
    return out
