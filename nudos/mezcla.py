"""La mezcla del sonido de los videos (T23c): la voz, la música y los efectos, en estéreo.

- `bajo_la_voz()`: la música baja sola mientras habla la voz (*ducking*), con anticipación, y
  queda SEPARACION dB por debajo de ella.
"""
from __future__ import annotations

import numpy as np

SEPARACION = 15.0       # dB: la música, por lo menos esto debajo de la voz mientras habla
ANTES = 0.15            # s: la música empieza a bajar antes de que entre la voz
SOSTEN = 0.45           # s: no vuelve a subir entre palabras ni en pausas más cortas que esto
RAMPA = 0.20            # s: lo que tarda en bajar o subir


def _mono(x) -> np.ndarray:
    x = np.asarray(x, np.float64)
    return x.mean(axis=1) if x.ndim > 1 else x


def habla(voz, sr: int, hop: float = 0.01) -> np.ndarray:
    """Por cada tramo de 10 ms, si la voz está hablando (con sus pausas cortas)."""
    from scipy.ndimage import binary_dilation, binary_erosion
    m = _mono(voz)
    h = int(hop * sr)
    n = len(m) // h
    if n == 0:
        return np.zeros(0, bool)
    e = 10 * np.log10(np.maximum((m[:n * h].reshape(n, h) ** 2).mean(axis=1), 1e-14))
    ref = np.percentile(e[e > -120], 95) if (e > -120).any() else -120
    activa = e > ref - 30
    k = max(1, int(SOSTEN / hop))
    # Cerrar los huecos cortos (entre palabras), sin agrandar los tramos.
    activa = binary_erosion(binary_dilation(activa, np.ones(k)), np.ones(k)) | activa
    return activa


def ganancia_bajo_voz(voz, musica, sr: int, separacion: float = SEPARACION) -> np.ndarray:
    """La ganancia de la música, muestra por muestra: baja lo justo para quedar `separacion` dB
    bajo la voz donde habla (medido con la sonoridad de cada una), y vuelve donde calla."""
    from scipy.ndimage import uniform_filter1d

    from . import sonoridad as so
    hop = 0.01
    activa = habla(voz, sr, hop)
    if not activa.any():
        return np.ones(len(_mono(musica)))
    v = so.lufs(voz, sr)
    m = so.lufs(musica, sr)
    profundidad = max(0.0, m - v + separacion + 1.0) if np.isfinite(m) and np.isfinite(v) else separacion
    # Anticipar la entrada: cada tramo activo empieza ANTES s antes (y la rampa termina a tiempo).
    a = max(1, int((ANTES + RAMPA / 2) / hop))
    activa = np.convolve(activa.astype(float), np.ones(a + 1))[a:a + len(activa)] > 0
    g_db = -profundidad * activa.astype(float)
    g_db = uniform_filter1d(g_db, size=max(1, int(RAMPA / hop)))
    t = (np.arange(len(_mono(musica))) / sr) / hop
    g = 10 ** (np.interp(t, np.arange(len(g_db)), g_db) / 20)
    return g


def bajo_la_voz(musica, voz, sr: int, separacion: float = SEPARACION) -> np.ndarray:
    """La música bajada bajo la voz y la voz encima, en el centro. Devuelve estéreo."""
    mus = np.asarray(musica, np.float64)
    mus = np.column_stack([mus, mus]) if mus.ndim == 1 else mus
    vz = _mono(voz)
    n = max(len(mus), len(vz))
    mus = np.pad(mus, ((0, n - len(mus)), (0, 0)))
    vz = np.pad(vz, (0, n - len(vz)))
    g = ganancia_bajo_voz(vz, mus, sr, separacion)
    return mus * g[:, None] + vz[:, None]
