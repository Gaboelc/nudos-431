"""El audio de los videos (T18). Gabriel eligió el 26 nov el de la segunda prueba.

Tres sonidos, todos sintetizados aquí, sin grabaciones ni bancos de sonido: son propios, no
tienen licencia de nadie y salen iguales cada vez.

- **El clic,** cuando aparece el título de un paso: un tono corto de 2,6 kHz, con otro una
  octava arriba y otro una abajo (pico CLIC_DB).
- **El golpe,** cuando el nudo termina de apretarse: un tono grave que baja de 150 a 55 Hz y un
  chasquido (pico GOLPE_DB).
- **El roce:** granos cortos (un impulso o un soplo de ruido por un resonador), como los tirones
  de la trenza al deslizar. Suena solo donde la cuerda roza algo, medido en cada cuadro: otra
  parte de la cuerda, el anfitrión o la mesa. Cuanto más largo el roce y más rápido, más granos
  por segundo. Cada grano tiene su pico (GRANO_DB), así que el volumen sale de cuántos hay: subir
  el volumen y limitarlo aplanaba todos los granos al mismo techo, y un ruido continuo sonaba a
  ruido (las dos pruebas del 26 nov).

`pista()` da el audio de los cuadros de un video y `pegar()` lo pone en un video ya armado, sin
volver a dibujarlo.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

SR = 48000
VERSION = "1"             # súbela si cambia cómo suena: los videos vuelven a pegar su audio
SEMILLA = 431
CLIC_DB = -8.0            # pico del clic
GOLPE_DB = -5.5           # pico del golpe
GRANO_DB = -16.0          # pico de un grano de roce típico: 8 dB por debajo del clic
ROCE_PICO = -10.0         # el seguro del roce, para los pocos granos que coinciden
CONTACTO = 1.12           # d: dos ejes de cuerda a menos de esto se tocan
TOCA_SOLIDO = 0.62        # d: el eje de la cuerda a menos de esto del anfitrión lo toca
SOBRE_LA_MESA = 0.58      # d: un nodo más bajo que esto está apoyado en la mesa
SEPARACION = 2.5          # d a lo largo de la cuerda: más cerca, es la misma parte que dobla
QUIETA = 0.05             # d/s: más lento que esto no roza
TEMBLOR = 1e-4            # el ruido de fondo, a −80 dB (ver `pista`)

# Cada canal de roce: el resonador del grano (Hz) y su Q, el cuerpo (Hz) y su peso, la parte de
# granos de ruido (el resto son impulsos), la ganancia y el tope de granos por segundo.
CANALES = {
    "cuerda": dict(f=(1200, 4200), q=(2.0, 4.5), cuerpo=(260, 600), cuerpo_amp=0.45, ruido=0.45,
                   gan=1.0, tope=500.0),
    "anfitrion": dict(f=(550, 1800), q=(4.0, 9.0), cuerpo=(140, 320), cuerpo_amp=0.6, ruido=0.3,
                      gan=1.0, tope=500.0),
    "mesa": dict(f=(1600, 4800), q=(2.5, 4.5), cuerpo=(300, 700), cuerpo_amp=0.25, ruido=0.4,
                 gan=0.5, tope=300.0),
}


def db(x: float) -> float:
    return 10 ** (x / 20)


def _filtro(x, tipo: str, f, orden: int = 2):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(orden, f, btype=tipo, fs=SR, output="sos"), x)


def _resonador(exc, f: float, q: float):
    from scipy.signal import iirpeak, lfilter
    b, a = iirpeak(f, q, fs=SR)
    return lfilter(b, a, exc)


# --------------------------------------------------------------------------
# Dónde roza la cuerda
# --------------------------------------------------------------------------
def contactos(cuadros, fps: float, h: float, solidos=()) -> tuple[dict, dict]:
    """Por canal y por cuadro: el roce (la suma de la velocidad de deslizamiento por el largo que
    roza, en d²/s) y el largo que roza moviéndose (d). `solidos` son muestras de la superficie
    del anfitrión con su normal (`blender._muestras_solidos`)."""
    from scipy.spatial import cKDTree
    sep = int(np.ceil(SEPARACION / h))
    K = len(cuadros)
    roce = {c: np.zeros(K) for c in CANALES}
    largo = {c: np.zeros(K) for c in CANALES}
    arboles = [(cKDTree(P), N, P) for P, N in solidos]
    for k in range(1, K):
        A, B = np.asarray(cuadros[k - 1].X, float), np.asarray(cuadros[k].X, float)
        if len(A) != len(B):
            # Al dar o recoger cuerda cambia la punta; al entrar cuerda por el firme, el firme.
            n = min(len(A), len(B))
            ini = np.median(np.linalg.norm(B[:n] - A[:n], axis=1))
            fin = np.median(np.linalg.norm(B[-n:] - A[-n:], axis=1))
            A, B = (A[:n], B[:n]) if ini <= fin else (A[-n:], B[-n:])
        v = (B - A) * fps
        rapidez = np.linalg.norm(v, axis=1)
        if rapidez.max() < QUIETA:
            continue
        N = len(B)
        # Con otra parte de la cuerda: el vecino más cercano que no es la misma parte.
        d, idx = cKDTree(B).query(B, k=32, distance_upper_bound=CONTACTO)
        valido = np.isfinite(d) & (idx < N) & (np.abs(idx - np.arange(N)[:, None]) > sep)
        tiene = valido.any(axis=1)
        if tiene.any():
            j = idx[np.arange(N), np.argmax(valido, axis=1)]
            rel = np.linalg.norm(v[tiene] - v[j[tiene]], axis=1)
            roce["cuerda"][k] = rel.sum() * h
            largo["cuerda"][k] = (rel > QUIETA).sum() * h
        # Con el anfitrión: el eje cerca del plano tangente del punto más cercano de su superficie.
        toca = np.zeros(N, bool)
        for arbol, normales, P in arboles:
            _, q = arbol.query(B)
            hh = np.einsum("ij,ij->i", B - P[q], normales[q])
            toca |= (hh > 0) & (hh < TOCA_SOLIDO)
        roce["anfitrion"][k] = rapidez[toca].sum() * h
        largo["anfitrion"][k] = (toca & (rapidez > QUIETA)).sum() * h
        # Con la mesa: lo que está apoyado y se arrastra.
        mesa = B[:, 2] < SOBRE_LA_MESA
        vm = np.linalg.norm(v[mesa, :2], axis=1)
        roce["mesa"][k] = vm.sum() * h
        largo["mesa"][k] = (vm > QUIETA).sum() * h
    return roce, largo


# --------------------------------------------------------------------------
# Los sonidos
# --------------------------------------------------------------------------
def _prototipos(rng, n: int, c: dict) -> list[np.ndarray]:
    """n granos de un canal, de 16 ms, con el pico en 1."""
    L = int(0.016 * SR)
    t = np.arange(L) / SR
    cola = np.ones(L)
    m = int(0.003 * SR)
    cola[-m:] = np.linspace(1, 0, m)
    out = []
    for _ in range(n):
        if rng.random() < c["ruido"]:
            exc = rng.standard_normal(L) * np.exp(-t / rng.uniform(0.0006, 0.0025))
        else:
            exc = np.zeros(L)
            exc[0] = 1.0
            exc[1] = -rng.uniform(0.2, 0.7)
        g = _resonador(exc, float(np.exp(rng.uniform(*np.log(c["f"])))), rng.uniform(*c["q"]))
        g /= max(np.abs(g).max(), 1e-12)
        cu = _resonador(exc, float(np.exp(rng.uniform(*np.log(c["cuerpo"])))), 1.6)
        g = g + c["cuerpo_amp"] * cu / max(np.abs(cu).max(), 1e-12)
        g *= cola
        out.append(g / max(np.abs(g).max(), 1e-12))
    return out


def _granos(tasa, amp, fps: float, protos, rng, n_muestras: int, jitter: float = 0.45) -> np.ndarray:
    """Los granos de un canal: la fase avanza tasa/fps por cuadro y suelta un grano cada vez que
    pasa un entero, corrido al azar hasta medio período."""
    pista = np.zeros(n_muestras + int(0.03 * SR))
    fase = rng.random()
    for k in range(len(tasa)):
        r = tasa[k]
        if r <= 0:
            continue
        f1 = fase + r / fps
        enteros = np.arange(np.floor(fase) + 1, np.floor(f1) + 1)
        if len(enteros):
            ts = k / fps + (enteros - fase) / r + rng.uniform(-jitter, jitter, len(enteros)) / r
            for tt in ts:
                g = protos[rng.integers(len(protos))]
                a = amp[k] * np.clip(rng.lognormal(0, 0.3), 0.5, 1.6) * (1 if rng.random() < 0.5 else -1)
                i = int(max(tt, 0.0) * SR)
                j = min(len(pista), i + len(g))
                pista[i:j] += a * g[:j - i]
        fase = f1
    return pista[:n_muestras]


def clic(rng) -> np.ndarray:
    d = int(0.07 * SR)
    t = np.arange(d) / SR
    f = 2600 * (1 + 0.04 * rng.standard_normal())
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.009)
    s += 0.35 * np.sin(2 * np.pi * f / 2 * t) * np.exp(-t / 0.013)    # el cuerpo, una octava abajo
    s += 0.30 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.004)    # la presencia, una arriba
    s += 0.25 * _filtro(rng.standard_normal(d), "high", 3000) * np.exp(-t / 0.0015)
    s *= np.minimum(1.0, t / 0.0003)
    return s / np.abs(s).max()


def golpe(rng) -> np.ndarray:
    d = int(0.45 * SR)
    t = np.arange(d) / SR
    f = 95 * np.exp(-t / 0.18) + 55
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)
    s += 0.6 * _filtro(rng.standard_normal(d), "band", [700, 3500], 4) * np.exp(-t / 0.018)
    return s / np.abs(s).max()


def _limitar(x, pico_db: float) -> np.ndarray:
    """Donde un pico pasa de pico_db, la ganancia baja desde 15 ms antes hasta 15 ms después y
    vuelve suave."""
    from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
    tope = db(pico_db)
    env = maximum_filter1d(np.abs(x), size=int(0.006 * SR))
    g = np.minimum(1.0, tope / np.maximum(env, 1e-12))
    g = minimum_filter1d(g, size=int(0.03 * SR))
    g = uniform_filter1d(g, size=int(0.01 * SR))
    return np.clip(x * g, -tope, tope)


def _poner(pista, s, t: float, nivel: float) -> None:
    i = int(t * SR)
    j = min(len(pista), i + len(s))
    if 0 <= i < len(pista):
        pista[i:j] += nivel * s[:j - i]


def pista(cuadros, fps: float, h: float, mallas=(), semilla: int = SEMILLA) -> np.ndarray:
    """El audio de los cuadros de un video, en float32 a SR muestras por segundo, del largo del
    video: el roce, un clic cada vez que cambia el título y el golpe en el último cuadro del
    apretado. `mallas` son las del anfitrión, como las exporta render/escena.js."""
    from .blender import _muestras_solidos
    rng = np.random.default_rng(semilla)
    n = int(np.ceil(len(cuadros) / fps * SR))
    roce_k, largo_k = contactos(cuadros, fps, h, _muestras_solidos(list(mallas)) if mallas else ())
    roce = np.zeros(n)
    for c, p in CANALES.items():
        # La tasa crece menos que el roce: los roces grandes (el apretado, arrastrar toda la gaza)
        # no tapan a los chicos.
        tasa = np.where(roce_k[c] > QUIETA, np.clip(60.0 * roce_k[c] ** 0.6, 0, p["tope"]), 0.0)
        tasa = np.convolve(tasa, [0.25, 0.5, 0.25], mode="same")
        rapidez = roce_k[c] / np.maximum(largo_k[c], h)
        amp = np.clip((rapidez / 5.0) ** 0.25, 0.6, 1.25)
        roce += p["gan"] * _granos(tasa, amp, fps, _prototipos(rng, 48, p), rng, n)
    roce = _limitar(_filtro(_filtro(roce, "high", 90), "low", 9000) * db(GRANO_DB), ROCE_PICO)
    efectos = np.zeros(n)
    for k in range(1, len(cuadros)):
        if cuadros[k].titulo != cuadros[k - 1].titulo:
            _poner(efectos, clic(rng), k / fps, db(CLIC_DB))
    apretar = [k for k, c in enumerate(cuadros) if c.fase == "apretar"]
    if apretar:
        _poner(efectos, golpe(rng), apretar[-1] / fps, db(GOLPE_DB))
    x = roce + efectos
    pico = float(np.abs(x).max())
    if pico > db(-1.0):
        x = np.tanh(x / pico * 2.0) / np.tanh(2.0) * db(-1.0)
    # Un ruido a −80 dB: con segundos de ceros exactos (las pausas), el AAC de ffmpeg 9.1 deja de
    # entregar audio y el video no se arma (26 nov).
    x = x + rng.normal(0.0, TEMBLOR, len(x))
    return x.astype(np.float32)


# --------------------------------------------------------------------------
# En el video
# --------------------------------------------------------------------------
def escribir(x, ruta: Path) -> None:
    from scipy.io import wavfile
    wavfile.write(ruta, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def pegar(video: Path, x, salida: Path | None = None, kbps: int = 192) -> None:
    """Pone el audio x en el video ya armado (reemplaza el que tenga), sin volver a codificar la
    imagen. Sin `salida`, reemplaza el video."""
    salida = salida or video
    wav = salida.with_suffix(".tmp.wav")
    tmp = salida.with_suffix(".tmp.mp4")
    escribir(x, wav)
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "format=duration", "-of", "csv=p=0", str(video)],
                           capture_output=True, text=True, timeout=60, check=True)
        dur = float(r.stdout.strip())
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", f"{kbps}k",
                        "-t", f"{dur:.3f}", "-movflags", "+faststart", str(tmp)], check=True, timeout=900)
        tmp.replace(salida)
    finally:
        wav.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)
