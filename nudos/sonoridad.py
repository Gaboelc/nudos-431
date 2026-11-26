"""La sonoridad y el pico de un audio (T23), según la recomendación UIT-R BS.1770-4.

- `lufs()`: la sonoridad integrada en LUFS, con la ponderación K y las dos compuertas (la
  absoluta de −70 LUFS y la relativa de 10 LU bajo el promedio). Un tono de 1 kHz a 0 dBFS en un
  solo canal da −3,01 LUFS, como pide la norma.
- `pico_real()`: el pico real en dBTP, medido con la señal sobremuestreada cuatro veces (anexo 2
  de la norma), que ve los picos entre muestra y muestra.
- `a_lufs()`: lleva un audio a una sonoridad, y `limitar_pico()`, a un pico real como máximo.

Se escribió aquí en vez de usar pyloudnorm (Gabriel, 26 nov: no se agrega esa dependencia): son
pocas líneas y las pruebas lo comparan con los valores de la norma.
"""
from __future__ import annotations

import numpy as np

BLOQUE = 0.400          # s: el bloque de la compuerta
SALTO = 0.100           # s: los bloques se solapan un 75 %
ABSOLUTA = -70.0        # LUFS
RELATIVA = -10.0        # LU bajo el promedio de lo que pasa la absoluta

# La ponderación K a 48 kHz, con los coeficientes de la norma.
_K48 = (
    (np.array([1.53512485958697, -2.69169618940638, 1.19839281085285]),
     np.array([1.0, -1.69065929318241, 0.73248077421585])),
    (np.array([1.0, -2.0, 1.0]),
     np.array([1.0, -1.99004745483398, 0.99007225036621])),
)


def _filtros_k(sr: int):
    """Los dos filtros de la ponderación K: un estante alto de +4 dB en 1,5 kHz y un pasa altos
    en 38 Hz. A 48 kHz, los de la norma; a otra frecuencia, diseñados igual (como pyloudnorm)."""
    if sr == 48000:
        return _K48
    w = 2 * np.pi * 1500.0 / sr
    A = 10 ** (4.0 / 40)
    alfa = np.sin(w) / (2 * (1 / np.sqrt(2)))
    c, r = np.cos(w), 2 * np.sqrt(A) * alfa
    estante = (np.array([A * ((A + 1) + (A - 1) * c + r), -2 * A * ((A - 1) + (A + 1) * c),
                         A * ((A + 1) + (A - 1) * c - r)]),
               np.array([(A + 1) - (A - 1) * c + r, 2 * ((A - 1) - (A + 1) * c),
                         (A + 1) - (A - 1) * c - r]))
    w = 2 * np.pi * 38.0 / sr
    alfa, c = np.sin(w) / (2 * 0.5), np.cos(w)
    pasa = (np.array([(1 + c) / 2, -(1 + c), (1 + c) / 2]), np.array([1 + alfa, -2 * c, 1 - alfa]))
    return tuple((b / a[0], a / a[0]) for b, a in (estante, pasa))


def _canales(x) -> np.ndarray:
    x = np.asarray(x, np.float64)
    return x[:, None] if x.ndim == 1 else x


def lufs(x, sr: int) -> float:
    """La sonoridad integrada, en LUFS. x es (n,) o (n, canales); los canales pesan igual (los
    de un estéreo). Un audio más corto que un bloque o en silencio da −inf."""
    from scipy.signal import lfilter
    y = _canales(x)
    for b, a in _filtros_k(sr):
        y = lfilter(b, a, y, axis=0)
    n, salto = int(round(BLOQUE * sr)), int(round(SALTO * sr))
    if len(y) < n:
        return float("-inf")
    # La energía de cada bloque, con una suma acumulada.
    acum = np.vstack([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, axis=0)])
    inicios = np.arange(0, len(y) - n + 1, salto)
    z = ((acum[inicios + n] - acum[inicios]) / n).sum(axis=1)
    with np.errstate(divide="ignore"):
        l = -0.691 + 10 * np.log10(z)
    z = z[l > ABSOLUTA]
    if not len(z):
        return float("-inf")
    umbral = -0.691 + 10 * np.log10(z.mean()) + RELATIVA
    z = z[-0.691 + 10 * np.log10(z) > umbral]
    return float(-0.691 + 10 * np.log10(z.mean()))


def corto(x, sr: int, ventana: float = 0.4, salto: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """La sonoridad en ventanas (la «momentánea» de la norma con 0,4 s), sin compuertas: los
    centros de cada ventana en s y su sonoridad en LUFS."""
    from scipy.signal import lfilter
    y = _canales(x)
    for b, a in _filtros_k(sr):
        y = lfilter(b, a, y, axis=0)
    n, h = int(round(ventana * sr)), int(round(salto * sr))
    if len(y) < n:
        return np.zeros(0), np.zeros(0)
    acum = np.vstack([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, axis=0)])
    inicios = np.arange(0, len(y) - n + 1, h)
    z = ((acum[inicios + n] - acum[inicios]) / n).sum(axis=1)
    with np.errstate(divide="ignore"):
        return (inicios + n / 2) / sr, -0.691 + 10 * np.log10(np.maximum(z, 1e-20))


def pico_real(x, sr: int | None = None) -> float:
    """El pico real en dBTP: el máximo de la señal sobremuestreada 4 veces."""
    from scipy.signal import resample_poly
    y = _canales(x)
    if not len(y):
        return float("-inf")
    s = resample_poly(y, 4, 1, axis=0)
    p = max(float(np.abs(s).max()), float(np.abs(y).max()))
    return 20 * np.log10(p) if p > 0 else float("-inf")


def a_lufs(x, sr: int, objetivo: float) -> np.ndarray:
    """x con la ganancia que lo lleva a `objetivo` LUFS (sin tocar su forma)."""
    actual = lufs(x, sr)
    if not np.isfinite(actual):
        return np.asarray(x, np.float64).copy()
    return np.asarray(x, np.float64) * 10 ** ((objetivo - actual) / 20)


def limitar_pico(x, sr: int, techo_dbtp: float = -1.0, rampa: float = 0.030) -> np.ndarray:
    """Un limitador con anticipación: donde el pico real pasaría de `techo_dbtp`, la ganancia
    baja en `rampa` s antes del pico, se sostiene y vuelve en otro tanto. Mide los picos
    sobremuestreados, así que el pico real queda bajo el techo, no solo el de las muestras."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    from scipy.signal import resample_poly
    y = _canales(x)
    if not len(y):
        return np.asarray(x, np.float64).copy()
    tope = 10 ** ((techo_dbtp - 0.1) / 20)          # 0,1 dB de margen por el redondeo
    sobre = np.abs(resample_poly(y, 4, 1, axis=0)).max(axis=1)
    sobre = np.pad(sobre, (0, max(0, 4 * len(y) - len(sobre))))[:4 * len(y)]
    env = np.maximum(sobre.reshape(-1, 4).max(axis=1), np.abs(y).max(axis=1))
    g = np.minimum(1.0, tope / np.maximum(env, 1e-12))
    k = max(2, int(rampa * sr))
    # Cada valle se sostiene k muestras hacia adelante, y el promedio de las k siguientes lo
    # suaviza: en el pico, la ganancia es a lo más la que pide.
    g = minimum_filter1d(g, size=k, origin=(k - 1) // 2)
    g = uniform_filter1d(g, size=k, origin=-((k - 1) // 2))
    out = y * g[:, None]
    # El seguro: lo poco que quede por encima se recorta suave.
    pico = 10 ** (techo_dbtp / 20)
    if pico_real(out) > techo_dbtp:
        out = np.tanh(out / pico) * pico * 0.995
    return out[:, 0] if np.asarray(x).ndim == 1 else out
