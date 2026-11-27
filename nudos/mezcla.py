"""La mezcla del sonido de los videos (T23c): la voz, la música, los efectos y el foley, en estéreo.

`pista(duracion, capitulos=..., golpe=..., slug=..., dichos=..., eventos=..., sonidos=...)` es lo
que usa T22: da la pista de un video, lista para el AAC.

- **La voz** (`Dicho`: una locución de nudos/voz.py y cuándo empieza) va en el centro y casi seca:
  cada locución a NIVEL_VOZ.
- **La música** (nudos/musica.py) es la canción del nudo para esos capítulos, con su acorde final
  en el golpe. Sola queda a NIVEL_MUSICA, y baja sola mientras habla la voz (`bajo_la_voz`):
  durante cada frase, lo justo para quedar SEPARACION dB bajo esa frase, medido con la sonoridad
  de corto plazo de la norma.
- **Los efectos y el foley** (nudos/foley.py: las tarjetas, el golpe, el roce, los tacs, el
  crujido, los soplidos y los tics) van cada uno donde se ve en el cuadro, en una sala chica:
  reverberación por convolución con una respuesta sintetizada (`sala_chica`).
- **El máster:** todo junto a OBJETIVO LUFS con el pico real en TECHO dBTP (BS.1770, con
  nudos/sonoridad.py), medio dB bajo el −1 que se pide porque el AAC sube los picos, y un ruido a
  −80 dB para que el AAC de ffmpeg no se corte en los silencios. `pegar()` lo pone en un video en
  AAC de 256 kbps, sin volver a codificar la imagen.

`pista_de_cuadros(cuadros, fps, h, ...)` arma todo desde los cuadros de hoy (T18): las tarjetas en
cada cambio de título, el golpe al final del apretado, el foley del motor y los soplidos de la
cámara.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SR = 48000
SEPARACION = 15.0       # dB: la música, por lo menos esto debajo de la voz mientras habla
MARGEN = 1.0            # dB de más, para que la medida no quede justo en el límite
ANTES = 0.15            # s: la música empieza a bajar antes de que entre la voz
SOSTEN = 0.45           # s: no vuelve a subir entre palabras ni en pausas más cortas que esto
RAMPA = 0.20            # s: lo que tarda en bajar o subir

NIVEL_VOZ = -16.0       # LUFS de cada locución, antes del máster
NIVEL_MUSICA = -22.0    # LUFS de la música sola, antes del máster: 6 LU bajo la voz entre frases
OBJETIVO = -14.0        # LUFS del máster
TECHO = -1.5            # dBTP del máster: el AAC sube los picos unas décimas (de −1,1 a −1,0 en el as de
                        # guía), y así el video queda bajo −1
TEMBLOR = 1e-4          # el ruido de fondo, a −80 dB (ver nudos/audio.py)
ANCHO = 0.8             # cuánto se abre el estéreo: lo que está en el borde del cuadro va a 0,8
SALA_VOZ = 0.03         # lo que la voz manda a la sala


def _mono(x) -> np.ndarray:
    x = np.asarray(x, np.float64)
    return x.mean(axis=1) if x.ndim > 1 else x


def _estereo(x) -> np.ndarray:
    x = np.asarray(x, np.float64)
    return np.column_stack([x, x]) if x.ndim == 1 else x[:, :2]


# --------------------------------------------------------------------------
# La música bajo la voz
# --------------------------------------------------------------------------
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


def frases(activa: np.ndarray) -> list[tuple[int, int]]:
    """Los tramos seguidos de habla, en tramos de 10 ms: (desde, hasta)."""
    d = np.diff(np.concatenate([[0], activa.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def ganancia_bajo_voz(voz, musica, sr: int, separacion: float = SEPARACION) -> np.ndarray:
    """La ganancia de la música, muestra por muestra. En cada frase de la voz baja lo justo para
    que la sonoridad de corto plazo de la música (0,4 s) quede `separacion` dB (y MARGEN) bajo la
    de la frase, desde ANTES s antes de que empiece; entre frases vuelve a 1."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d

    from . import sonoridad as so
    hop = 0.01
    vz, mus = _mono(voz), np.asarray(musica, np.float64)
    activa = habla(vz, sr, hop)
    n = len(mus)
    if not activa.any():
        return np.ones(n)
    # La sonoridad de corto plazo de la música, de la ventana centrada en cada tramo de 10 ms.
    _, m_corto = so.corto(mus, sr, ventana=0.4, salto=hop)
    centro = np.arange(len(activa)) - int(round(0.2 / hop))
    m_en = np.full(len(activa), -np.inf)
    ok = (centro >= 0) & (centro < len(m_corto))
    m_en[ok] = m_corto[centro[ok]]
    a, b = int(round(ANTES / hop)), int(round(RAMPA / 2 / hop)) + 1
    g_db = np.zeros(len(activa))
    for i0, i1 in frases(activa):
        v = so.lufs(vz[i0 * int(hop * sr):i1 * int(hop * sr)], sr)
        if not np.isfinite(v):
            v = so.lufs(vz, sr)
        j0, j1 = max(0, i0 - a), min(len(activa), i1 + b)
        tope = np.max(m_en[j0:j1]) if np.isfinite(m_en[j0:j1]).any() else -np.inf
        bajar = max(0.0, tope - (v - separacion - MARGEN)) if np.isfinite(tope) else 0.0
        g_db[j0:j1] = np.minimum(g_db[j0:j1], -bajar)
    # Las rampas, por fuera de cada tramo: se extiende la bajada media rampa a cada lado y se
    # promedia una rampa, así que adentro queda entera y afuera sube o baja en RAMPA s.
    k = max(1, int(round(RAMPA / hop)))
    g_db = uniform_filter1d(minimum_filter1d(g_db, size=k + 1), size=k)
    t = (np.arange(n) / sr) / hop
    return 10 ** (np.interp(t, np.arange(len(g_db)), g_db) / 20)


def bajo_la_voz(musica, voz, sr: int, separacion: float = SEPARACION) -> np.ndarray:
    """La música bajada bajo la voz y la voz encima, en el centro. Devuelve estéreo."""
    mus = _estereo(musica)
    vz = _mono(voz)
    n = max(len(mus), len(vz))
    mus = np.pad(mus, ((0, n - len(mus)), (0, 0)))
    vz = np.pad(vz, (0, n - len(vz)))
    g = ganancia_bajo_voz(vz, mus, sr, separacion)
    return mus * g[:, None] + vz[:, None]


# --------------------------------------------------------------------------
# El estéreo y la sala
# --------------------------------------------------------------------------
def sala_chica(sr: int = SR) -> np.ndarray:
    """La respuesta de una sala chica, estéreo: 0,35 s de reverberación, las primeras reflexiones
    muy cerca."""
    from .musica import sala
    return sala(sr, rt60=0.35, predelay=0.005, semilla=11)


def panear(x, pos) -> np.ndarray:
    """Un audio mono en estéreo, con potencia constante: `pos` de −1 (izquierda) a 1 (derecha),
    fija o una por muestra. En el centro, cada canal lleva el audio entero."""
    x = np.asarray(x, np.float64)
    p = np.clip(np.asarray(pos, float) * ANCHO, -1, 1)
    ang = (p + 1) * np.pi / 4
    return np.column_stack([x * np.cos(ang) * np.sqrt(2), x * np.sin(ang) * np.sqrt(2)])


def _colocar(n: int, sonidos) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Por bus, lo seco y lo que va a la sala (n, 2)."""
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for s in sonidos:
        i = int(round(s.t * SR))
        a = np.asarray(s.audio, np.float64)
        x = s.x
        if i < 0:
            a = a[-i:]
            x = x[-i:] if np.ndim(x) else x
            i = 0
        L = min(len(a), n - i)
        if L <= 0:
            continue
        x = x[:L] if np.ndim(x) else x
        y = panear(a[:L], x)
        seco, envio = out.setdefault(s.bus, (np.zeros((n, 2)), np.zeros((n, 2))))
        seco[i:i + L] += y
        envio[i:i + L] += y * s.sala
    return out


def _con_sala(seco: np.ndarray, envio: np.ndarray, ir: np.ndarray) -> np.ndarray:
    from scipy.signal import oaconvolve
    if not np.abs(envio).max() > 0:
        return seco
    mojado = np.column_stack([oaconvolve(envio[:, c], ir[:, c])[:len(seco)] for c in range(2)])
    return seco + mojado


# --------------------------------------------------------------------------
# La pista
# --------------------------------------------------------------------------
@dataclass
class Dicho:
    """Una locución (nudos/voz.py) y cuándo empieza en el video (s)."""
    t: float
    locucion: object


@dataclass
class Pista:
    audio: np.ndarray                 # (n, 2) float32 a SR, a OBJETIVO LUFS y con el pico en TECHO dBTP
    buses: dict                       # «voz», «musica», «efectos», «foley»: (n, 2) antes del máster
    lufs: float
    pico: float                       # dBTP
    ganancia: float                   # dB del máster
    sonidos: list = field(default_factory=list)
    musica: object = None             # la Musica, con sus capítulos ya en el pulso
    frases: list = field(default_factory=list)   # (inicio, fin) en s de cada frase de la voz

    @property
    def segundos(self) -> float:
        return len(self.audio) / SR


def pista(duracion: float, *, capitulos=None, golpe: float | None = None, slug: str | None = None,
          cancion=None, musica=None, dichos=(), eventos=(), sonidos=(), instrumentos=None,
          aviso=print) -> Pista:
    """La pista estéreo de un video de `duracion` s.

    - `capitulos`: los de nudos/musica.py (`Capitulo(nombre, inicio, fin)`, en s); con ellos suena
      la canción del nudo (`slug`) o `cancion`, con su acorde final en `golpe`. O `musica`, una ya
      hecha. Sin ninguno, no hay música.
    - `dichos`: las locuciones y cuándo empieza cada una (`Dicho`).
    - `eventos`: las tarjetas y el golpe (`foley.Evento`).
    - `sonidos`: los del motor y la cámara (`foley.del_motor`, `foley.de_la_camara`).
    """
    from . import foley as F
    from . import sonoridad as so
    n = int(np.ceil(duracion * SR))
    # La voz: cada locución a NIVEL_VOZ, en el centro.
    voz = np.zeros(n)
    for d in dichos:
        a = np.asarray(d.locucion.audio, np.float64)
        nivel = so.lufs(np.column_stack([a, a]), SR)     # como suena en el centro del estéreo
        if np.isfinite(nivel):
            a = a * 10 ** ((NIVEL_VOZ - nivel) / 20)
        i = int(round(d.t * SR))
        L = min(len(a), n - i)
        if L > 0 and i >= 0:
            voz[i:i + L] += a[:L]
    if np.abs(voz).max() > 0:
        from scipy.signal import butter, sosfilt
        voz = sosfilt(butter(2, 70, btype="high", fs=SR, output="sos"), voz)
    # La música, a su nivel, y bajo la voz.
    if musica is None and capitulos:
        from . import musica as M
        musica = M.musica(capitulos, golpe, slug=slug, cancion=cancion, instrumentos=instrumentos, aviso=aviso)
    mus = np.zeros((n, 2))
    if musica is not None:
        m = _estereo(musica.mezcla)[:n]
        mus[:len(m)] = m
        nivel = so.lufs(mus, SR)
        if np.isfinite(nivel):
            mus *= 10 ** ((NIVEL_MUSICA - nivel) / 20)
        if np.abs(voz).max() > 0:
            mus *= ganancia_bajo_voz(voz, mus, SR)[:, None]
    # Los efectos y el foley, cada uno en su lugar, en la sala chica.
    todos = list(F.de_eventos(eventos)) + list(sonidos)
    colocados = _colocar(n, todos)
    ir = sala_chica()
    buses = {"voz": _con_sala(panear(voz, 0.0), panear(voz, 0.0) * SALA_VOZ, ir), "musica": mus}
    for bus in ("efectos", "foley"):
        seco, envio = colocados.get(bus, (np.zeros((n, 2)), np.zeros((n, 2))))
        buses[bus] = _con_sala(seco, envio, ir)
    x = sum(buses.values())
    # El máster: la sonoridad, el pico real y, si el limitador le quitó, una vuelta más.
    actual = so.lufs(x, SR)
    ganancia = OBJETIVO - actual if np.isfinite(actual) else 0.0
    y = so.limitar_pico(x * 10 ** (ganancia / 20), SR, TECHO)
    falta = OBJETIVO - so.lufs(y, SR)
    if np.isfinite(falta) and falta > 0.1:
        ganancia += falta
        y = so.limitar_pico(x * 10 ** (ganancia / 20), SR, TECHO)
    rng = np.random.default_rng(431)
    y = y + rng.normal(0.0, TEMBLOR, y.shape)
    hab = habla(voz, SR) if np.abs(voz).max() > 0 else np.zeros(0, bool)
    return Pista(y.astype(np.float32), {k: v.astype(np.float32) for k, v in buses.items()},
                 so.lufs(y, SR), so.pico_real(y, SR), float(ganancia), todos, musica,
                 [(a * 0.01, b * 0.01) for a, b in frases(hab)])


def pista_de_cuadros(cuadros, fps: float, h: float, mallas=(), *, formato: str = "horizontal",
                     capitulos=None, golpe: float | None = None, slug: str | None = None, cancion=None,
                     dichos=(), tics: bool | None = None, instrumentos=None, aviso=print) -> Pista:
    """La pista de los cuadros de hoy (T18, `video.cuadros_de`): las tarjetas en cada cambio de
    título, el golpe al final del apretado, el foley del motor y los soplidos de la cámara, con
    la música de `capitulos` (si los hay) y las locuciones de `dichos`. Sin `golpe`, el del
    apretado."""
    from . import foley as F
    eventos = F.eventos_de_cuadros(cuadros, fps, F.ANCHO_TARJETA.get(formato, 0.0))
    if golpe is None:
        golpe = next((e.t for e in eventos if e.tipo == "golpe"), None)
    sonidos = F.del_motor(cuadros, fps, h, mallas, tics=tics) + F.de_la_camara(cuadros, fps)
    return pista(len(cuadros) / fps, capitulos=capitulos, golpe=golpe, slug=slug, cancion=cancion,
                 dichos=dichos, eventos=eventos, sonidos=sonidos, instrumentos=instrumentos, aviso=aviso)


def pegar(video, p: Pista, salida=None) -> None:
    """Pone la pista en un video ya armado, en AAC estéreo de 256 kbps, sin volver a codificar la
    imagen. Sin `salida`, reemplaza el video."""
    from . import audio
    audio.pegar(video, p.audio, salida, kbps=256)
