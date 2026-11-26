"""La voz de los videos (T23a).

`locuciones(textos, voz)` da cada texto dicho por una voz, con el tiempo de cada palabra, y nunca
genera dos veces lo mismo: cada locución se guarda con la huella de su texto, su voz, el modelo y
los ajustes, fuera de git (`NUDOS_VOZ`; por omisión, `%LOCALAPPDATA%\\nudos\\voz`).

**Los proveedores:**
- `QwenTTS`, Qwen3-TTS 1.7B (Apache-2.0), en su propio entorno (nudos/ia.py, sonido/qwen_tts.py).
  Una voz «diseñada» sale de una descripción: VoiceDesign la crea una vez diciendo
  TEXTO_REFERENCIA, y desde ahí Base la clona en cada texto, así que suena igual en todo el
  video. Una voz con `referencia` (una muestra grabada) se clona directo.
- `ElevenLabs`, por su API, si la voz local no convence: la clave va en ELEVENLABS_API_KEY y
  `voz.id` es el voice_id. Da el tiempo de cada letra.
- `Falso`, para las pruebas: tonos con el ritmo de las sílabas, sin red ni tarjeta, con los
  tiempos exactos de cada palabra.

**La pronunciación** (`para_decir`): los números y las medidas van en letras («Paso 4 de 7» →
«Paso cuatro de siete», «1,5 m» → «un metro y medio»), sin comillas ni paréntesis, y las palabras
que el modelo diga mal se corrigen en PRONUNCIACION. Cada palabra recuerda cómo se ve, para los
subtítulos.

**El tiempo de cada palabra:** ElevenLabs lo da. Con el modelo local, hasta tener un alineador
forzado (Gabriel no autorizó el de Qwen el 26 nov; se vuelve a pedir en el punto de control), se
estima (`estimar_tiempos`): las pausas del audio se emparejan con la puntuación del texto y cada
tramo se reparte por sílabas. La locución dice cuáles son («estimados» o «proveedor»).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

SR = 48000            # la de la mezcla (nudos/audio.py)
VERSION = "1"         # súbela si cambia cómo se pide o se procesa una locución

TEXTO_REFERENCIA = ("Hola. Hoy vamos a aprender un nudo paso a paso. Toma la cuerda con calma, "
                    "mira bien cada cruce y sigue conmigo hasta el final.")


class VozError(RuntimeError):
    """La voz no se pudo generar así."""


# --------------------------------------------------------------------------
# Las voces
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Voz:
    nombre: str
    proveedor: str = "qwen"          # «qwen», «elevenlabs» o «falso»
    descripcion: str = ""            # Qwen: cómo es la voz, para VoiceDesign
    referencia: str = ""             # una muestra grabada para clonar (Qwen), en vez de descripción
    texto_referencia: str = ""       # lo que dice la muestra
    id: str = ""                     # ElevenLabs: el voice_id
    semilla: int = 431
    etiqueta: str = ""               # cómo se presenta en la prueba, en español

    def huella(self) -> dict:
        d = asdict(self)
        d.pop("etiqueta")
        if self.referencia:
            d["referencia"] = _huella_archivo(self.ruta_referencia())
        return d

    def ruta_referencia(self) -> Path:
        """La muestra, relativa a la raíz del repositorio si no es absoluta."""
        from . import RAIZ
        p = Path(self.referencia)
        return p if p.is_absolute() else RAIZ / p


def _huella_archivo(ruta: Path) -> str:
    if not ruta.exists():
        raise VozError(f"no está la muestra de voz {ruta}")
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]


# Las cuatro voces de la prueba a ciegas (T23a): latinoamericanas, creadas por descripción, así que
# no son de nadie. La descripción va en inglés, que es como mejor la sigue VoiceDesign.
VOCES_PRUEBA = (
    Voz("guia", descripcion=(
        "A warm, calm male voice in his mid-thirties. Native Latin American Spanish speaker with a "
        "neutral Central American accent. Friendly, patient and clear, like a camp instructor explaining "
        "a knot step by step. Moderate, relaxed pace, gentle smile in the voice."),
        semilla=4311, etiqueta="Hombre de unos 35 años, cálido y tranquilo, como un instructor de campamento"),
    Voz("maestra", descripcion=(
        "A clear, friendly female voice around thirty. Native Latin American Spanish speaker with a "
        "neutral accent. Warm and encouraging, very articulate, relaxed pace, like a teacher guiding a "
        "beginner through each step."),
        semilla=4312, etiqueta="Mujer de unos 30 años, clara y cercana, como una maestra"),
    Voz("joven", descripcion=(
        "A young male voice around twenty-five. Native Latin American Spanish speaker with a neutral "
        "accent. Bright and upbeat but calm, natural and conversational, medium pace."),
        semilla=4313, etiqueta="Hombre de unos 25 años, alegre y conversador"),
    Voz("narradora", descripcion=(
        "A mature female voice in her mid-forties. Native Latin American Spanish speaker with a neutral "
        "accent. Calm, confident and reassuring, like a documentary narrator. Steady, unhurried pace."),
        semilla=4314, etiqueta="Mujer de unos 45 años, serena y segura, como de documental"),
)

# La voz de los videos: Gabriel eligió la D de la prueba a ciegas, «joven», el 26 nov. Su muestra
# (la que VoiceDesign creó con la semilla 4313) va en el repositorio, para que las locuciones de
# los 36 nudos la clonen siempre igual aunque se borre el caché.
VOZ = Voz("joven", referencia="sonido/voces/joven.wav", texto_referencia=TEXTO_REFERENCIA,
          etiqueta="Hombre de unos 25 años, alegre y conversador")


# --------------------------------------------------------------------------
# La pronunciación
# --------------------------------------------------------------------------
# Las palabras que el modelo dice mal, en minúsculas, y cómo pedírselas. Se llena al oír.
PRONUNCIACION: dict[str, str] = {
    "prusik": "prúsik",
}

UNIDADES = {"m": ("metro", "metros"), "cm": ("centímetro", "centímetros"),
            "mm": ("milímetro", "milímetros"), "km": ("kilómetro", "kilómetros"),
            "kg": ("kilo", "kilos")}

_BASICOS = ("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince "
            "dieciséis diecisiete dieciocho diecinueve veinte veintiuno veintidós veintitrés "
            "veinticuatro veinticinco veintiséis veintisiete veintiocho veintinueve").split()
_DECENAS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta",
            9: "noventa"}
_CENTENAS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos",
             6: "seiscientos", 7: "setecientos", 8: "ochocientos", 9: "novecientos"}


def numero(n: int, apocope: bool = False) -> str:
    """n en letras, de 0 a 999 999. Con `apocope`, «uno» queda «un» (antes de un sustantivo
    masculino: «un metro», «veintiún metros»)."""
    if n < 0 or n > 999_999:
        raise ValueError(f"{n} está fuera de lo que se dice en letras")
    if n < 30:
        s = _BASICOS[n]
    elif n < 100:
        d, u = divmod(n, 10)
        s = _DECENAS[d] + ("" if u == 0 else " y " + _BASICOS[u])
    elif n < 1000:
        c, r = divmod(n, 100)
        s = "cien" if n == 100 else _CENTENAS[c] + ("" if r == 0 else " " + numero(r))
    else:
        m, r = divmod(n, 1000)
        s = ("mil" if m == 1 else numero(m, apocope=True) + " mil") + ("" if r == 0 else " " + numero(r))
    if apocope:
        s = re.sub(r"veintiuno$", "veintiún", s)
        s = re.sub(r"\buno$", "un", s)
    return s


@dataclass
class Palabra:
    texto: str          # como se ve, con su puntuación
    dicha: str          # como se le pide al modelo
    inicio: float = 0.0
    fin: float = 0.0


_PIEZA = re.compile(
    r"(?P<dec_u>(?P<du_e>\d+),(?P<du_d>\d+)\s*(?P<du_u>mm|cm|km|kg|m)\b)"
    r"|(?P<ent_u>(?P<eu_e>\d+)\s*(?P<eu_u>mm|cm|km|kg|m)\b)"
    r"|(?P<dec>(?P<d_e>\d+),(?P<d_d>\d+))"
    r"|(?P<ent>\d+)"
    r"|(?P<pal>[^\W\d_]+(?:['’\-][^\W\d_]+)*)"
    r"|(?P<pun>[.,;:¿?¡!…])")


def _decir_pieza(m: re.Match) -> str:
    if m.group("dec_u"):
        e, d, u = int(m.group("du_e")), m.group("du_d"), m.group("du_u")
        sing, plur = UNIDADES[u]
        if d == "5":
            return f"{numero(e, apocope=True)} {sing if e == 1 else plur} y medio"
        return f"{numero(e)} coma {numero(int(d))} {plur}"
    if m.group("ent_u"):
        e, u = int(m.group("eu_e")), m.group("eu_u")
        sing, plur = UNIDADES[u]
        return f"{numero(e, apocope=True)} {sing if e == 1 else plur}"
    if m.group("dec"):
        return f"{numero(int(m.group('d_e')))} coma {numero(int(m.group('d_d')))}"
    if m.group("ent"):
        return numero(int(m.group("ent")))
    p = m.group("pal")
    return PRONUNCIACION.get(p.casefold(), p)


def para_decir(texto: str) -> list[Palabra]:
    """Las palabras del texto, como se ven y como se dicen. La puntuación va pegada a la palabra
    de antes (la de apertura, ¿ y ¡, a la de después); las comillas y los paréntesis no se dicen."""
    out: list[Palabra] = []
    abre = ""
    for m in _PIEZA.finditer(unicodedata.normalize("NFC", texto)):
        if m.group("pun"):
            s = m.group("pun")
            if s in "¿¡":
                abre += s
            elif out:
                out[-1].texto += s
                out[-1].dicha += s
            continue
        vista = m.group(0)
        out.append(Palabra(abre + vista, abre + _decir_pieza(m)))
        abre = ""
    return out


def texto_dicho(palabras: list[Palabra]) -> str:
    return " ".join(p.dicha for p in palabras)


_FUERTES = set("aeoáéó")
_ACENTUADAS_DEBILES = set("íú")
_VOCALES = set("aeiouáéíóúü")


def silabas(palabra: str) -> int:
    """Las sílabas de una palabra en español, contando sus núcleos vocálicos (con diptongos e
    hiatos). Aproximado, para repartir el tiempo; los números ya vienen en letras."""
    w = unicodedata.normalize("NFC", palabra.casefold())
    w = re.sub(r"[^a-záéíóúüñy]", "", w)
    if not w:
        return 0
    w = re.sub(r"y$", "i", w) if len(w) > 1 else "i"
    w = w.replace("y", "ll")                 # la y entre vocales es consonante
    w = re.sub(r"([gq])u([eiéí])", r"\1\2", w)   # «que», «guía»: esa u no suena
    n, prev = 0, ""
    for c in w:
        if c in _VOCALES:
            if prev and prev in _VOCALES:
                hiato = ((c in _FUERTES and prev in _FUERTES) or c in _ACENTUADAS_DEBILES
                         or prev in _ACENTUADAS_DEBILES)
                if hiato:
                    n += 1
            else:
                n += 1
        prev = c
    return max(1, n)


# --------------------------------------------------------------------------
# El tiempo de cada palabra, estimado
# --------------------------------------------------------------------------
PAUSA_MIN = 0.12       # s: un silencio más largo que esto dentro del habla es una pausa
UMBRAL_HABLA = -38.0   # dB respecto del percentil 95 de la energía


def _energia(x, sr: int, hop: float = 0.01, ventana: float = 0.025) -> np.ndarray:
    h, n = int(hop * sr), int(ventana * sr)
    if len(x) < n:
        return np.full(1, -120.0)
    acum = np.concatenate([[0.0], np.cumsum(np.asarray(x, np.float64) ** 2)])
    ini = np.arange(0, len(x) - n + 1, h)
    e = (acum[ini + n] - acum[ini]) / n
    return 10 * np.log10(np.maximum(e, 1e-12))


def tramos_de_habla(x, sr: int) -> tuple[float, float, list[tuple[float, float]]]:
    """Dónde empieza y termina el habla, y las pausas de adentro (inicio, fin), en s."""
    from scipy.ndimage import median_filter
    e = _energia(x, sr)
    ref = np.percentile(e, 95)
    voz = median_filter((e > ref + UMBRAL_HABLA).astype(np.uint8), size=5).astype(bool)
    if not voz.any():
        return 0.0, len(x) / sr, []
    idx = np.flatnonzero(voz)
    a, b = idx[0], idx[-1] + 1
    pausas = []
    k = a
    while k < b:
        if not voz[k]:
            j = k
            while j < b and not voz[j]:
                j += 1
            if (j - k) * 0.01 >= PAUSA_MIN:
                pausas.append((k * 0.01 + 0.0125, j * 0.01 + 0.0125))
            k = j
        else:
            k += 1
    return a * 0.01, b * 0.01 + 0.025, pausas


def _peso_corte(p: Palabra) -> float:
    """Cuánta pausa se espera después de la palabra: fuerte con punto, media con coma."""
    if re.search(r"[.?!…:;]$", p.texto):
        return 1.0
    if p.texto.endswith(","):
        return 0.6
    return 0.0


def estimar_tiempos(x, sr: int, palabras: list[Palabra]) -> list[Palabra]:
    """Pone inicio y fin a cada palabra: empareja las pausas del audio con los cortes del texto
    (en orden, por programación dinámica) y reparte cada tramo de habla por sílabas."""
    if not palabras:
        return []
    ini, fin, pausas = tramos_de_habla(x, sr)
    sil = np.array([max(1, silabas(p.dicha)) for p in palabras], float) + 0.35
    cortes = [i for i, p in enumerate(palabras[:-1]) if _peso_corte(p) > 0]
    # El tiempo esperado de cada corte, si el habla fuera pareja.
    total = sil.sum()
    acum = np.cumsum(sil)
    esperado = {i: ini + (fin - ini) * acum[i] / total for i in cortes}
    usados: list[tuple[int, tuple[float, float]]] = []
    if cortes and pausas:
        # Emparejar en orden: cada pausa va a un corte o se deja (un respiro sin puntuación), y
        # cada corte recibe a lo más una pausa. Cuesta la distancia al tiempo esperado; dejar una
        # pausa cuesta DEJAR, y un corte con punto prefiere tener la suya.
        DEJAR = 0.35
        P, C = len(pausas), len(cortes)
        costo = np.zeros((P + 1, C + 1))
        costo[1:, 0] = DEJAR * np.arange(1, P + 1)
        paso = np.zeros((P + 1, C + 1), dtype=np.int8)     # 0: sin corte, 1: pausa en corte, 2: sin pausa
        for p in range(1, P + 1):
            mitad = sum(pausas[p - 1]) / 2
            for c in range(1, C + 1):
                op = (costo[p, c - 1],
                      costo[p - 1, c - 1] + abs(mitad - esperado[cortes[c - 1]])
                      - 0.25 * _peso_corte(palabras[cortes[c - 1]]),
                      costo[p - 1, c] + DEJAR)
                k = int(np.argmin(op))
                costo[p, c], paso[p, c] = op[k], k
        p, c = P, C
        while p > 0 and c > 0:
            if paso[p, c] == 1:
                usados.append((cortes[c - 1], pausas[p - 1]))
                p, c = p - 1, c - 1
            elif paso[p, c] == 2:
                p -= 1
            else:
                c -= 1
        usados.reverse()
    # Los tramos de habla: entre el inicio, las pausas emparejadas y el fin.
    limites = [(-1, ini)] + [(i, q[0]) for i, q in usados]
    reanudar = [ini] + [q[1] for _, q in usados]
    out = [Palabra(p.texto, p.dicha) for p in palabras]
    for t in range(len(limites)):
        desde = limites[t][0] + 1
        hasta = usados[t][0] if t < len(usados) else len(palabras) - 1
        t0 = reanudar[t]
        t1 = usados[t][1][0] if t < len(usados) else fin
        pesos = sil[desde:hasta + 1]
        bordes = t0 + (t1 - t0) * np.concatenate([[0.0], np.cumsum(pesos) / pesos.sum()])
        for k, i in enumerate(range(desde, hasta + 1)):
            out[i].inicio, out[i].fin = round(float(bordes[k]), 3), round(float(bordes[k + 1]), 3)
    return out


# --------------------------------------------------------------------------
# Las locuciones y su caché
# --------------------------------------------------------------------------
@dataclass
class Locucion:
    texto: str
    audio: np.ndarray            # float32, mono, a SR
    palabras: list[Palabra]
    tiempos: str                 # «estimados», «proveedor» o «alineados»
    huella: str
    voz: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def segundos(self) -> float:
        return len(self.audio) / SR


def carpeta_cache() -> Path:
    base = os.environ.get("NUDOS_VOZ") or str(Path(os.environ.get("LOCALAPPDATA", Path.home()))
                                               / "nudos" / "voz")
    return Path(base)


def _huella(*partes) -> str:
    h = hashlib.sha256()
    for p in partes:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False, default=str).encode())
    return h.hexdigest()[:20]


def _a_sr(x: np.ndarray, sr: int) -> np.ndarray:
    from math import gcd
    from scipy.signal import resample_poly
    x = np.asarray(x, np.float64)
    if sr == SR:
        return x.astype(np.float32)
    g = gcd(SR, sr)
    return resample_poly(x, SR // g, sr // g).astype(np.float32)


def _leer_wav(ruta: Path) -> tuple[np.ndarray, int]:
    import warnings
    from scipy.io import wavfile
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")       # el bloque «fact» de los WAV en coma flotante
        sr, x = wavfile.read(ruta)
    if x.dtype.kind == "i":
        x = x / float(np.iinfo(x.dtype).max)
    x = np.asarray(x, np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x, int(sr)


def _escribir_wav(ruta: Path, x, sr: int) -> None:
    from scipy.io import wavfile
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp.wav")
    wavfile.write(tmp, sr, np.asarray(x, np.float32))
    tmp.replace(ruta)


class Proveedor:
    """Lo común: generar(pedidos) da, por cada (palabras, voz), el audio, su frecuencia y, si el
    proveedor los sabe, los tiempos de cada palabra. `preparar` deja lista cada voz (Qwen diseña
    su muestra) y `huella_voz` dice qué de la voz decide cómo suena."""
    nombre = ""

    def huella(self) -> dict:
        return {"proveedor": self.nombre}

    def preparar(self, voces: list[Voz], aviso=print) -> None:
        pass

    def huella_voz(self, voz: Voz) -> dict:
        return voz.huella()

    def generar(self, pedidos: list[tuple[list[Palabra], Voz]], aviso=print
                ) -> list[tuple[np.ndarray, int, list[Palabra] | None]]:
        raise NotImplementedError


class Falso(Proveedor):
    """Para las pruebas: cada sílaba es un tono de 0,16 s con armónicos, las palabras van
    separadas por 50 ms, y después de un punto o una coma hay una pausa. Da los tiempos exactos.
    El tono depende de la voz."""
    nombre = "falso"
    SILABA, ENTRE, PUNTO, COMA = 0.16, 0.05, 0.32, 0.18
    sr = 24000

    def __init__(self):
        self.llamadas = 0

    def generar(self, pedidos, aviso=print):
        self.llamadas += 1
        out = []
        for palabras, voz in pedidos:
            f0 = 110 + int(hashlib.sha256(voz.nombre.encode()).hexdigest(), 16) % 120
            partes, t, tiempos = [np.zeros(int(0.2 * self.sr))], 0.2, []
            for p in palabras:
                n = max(1, silabas(p.dicha))
                d = n * self.SILABA
                tt = np.arange(int(d * self.sr)) / self.sr
                env = np.minimum(1, np.minimum(tt, d - tt) / 0.02) * (0.6 + 0.4 * np.abs(np.sin(np.pi * n * tt / d)))
                s = sum(np.sin(2 * np.pi * f0 * k * tt) / k for k in (1, 2, 3)) * env * 0.3
                tiempos.append(Palabra(p.texto, p.dicha, round(t, 3), round(t + d, 3)))
                pausa = self.ENTRE + (self.PUNTO if _peso_corte(p) == 1.0 else self.COMA if _peso_corte(p) else 0)
                partes += [s, np.zeros(int(pausa * self.sr))]
                t += len(s) / self.sr + int(pausa * self.sr) / self.sr
            partes.append(np.zeros(int(0.2 * self.sr)))
            out.append((np.concatenate(partes), self.sr, tiempos))
        return out


class QwenTTS(Proveedor):
    """Qwen3-TTS 1.7B, en su entorno (sonido/qwen_tts.py). La muestra de cada voz diseñada se
    guarda en el caché con su propia huella, y todas las locuciones la clonan."""
    nombre = "qwen3-tts-1.7b"
    AJUSTES = {"temperature": 0.8, "top_p": 0.9, "repetition_penalty": 1.05}

    def huella(self):
        return {"proveedor": self.nombre, "ajustes": self.AJUSTES, "script": "qwen_tts.py/1"}

    def muestra(self, voz: Voz) -> tuple[Path, str]:
        """La muestra que se clona: la grabada, o la que VoiceDesign creó de la descripción."""
        if voz.referencia:
            return voz.ruta_referencia(), voz.texto_referencia
        if not voz.descripcion:
            raise VozError(f"la voz «{voz.nombre}» no tiene ni descripción ni muestra")
        h = _huella("muestra", self.huella(), voz.descripcion, voz.semilla, TEXTO_REFERENCIA)
        return carpeta_cache() / "muestras" / f"{h}.wav", TEXTO_REFERENCIA

    def preparar(self, voces, aviso=print):
        from . import ia
        diseno = {}
        for voz in voces:
            ruta, _ = self.muestra(voz)
            if not ruta.exists():
                if voz.referencia:
                    raise VozError(f"no está la muestra de voz {ruta}")
                diseno[str(ruta)] = {"tipo": "disenar", "texto": TEXTO_REFERENCIA, "instruccion": voz.descripcion,
                                     "semilla": voz.semilla, "salida": str(ruta)}
        if diseno:
            aviso(f"  diseñando {len(diseno)} voces con VoiceDesign")
            ia.correr("qwen-tts", "qwen_tts.py", {"tareas": list(diseno.values())}, aviso=aviso)

    def huella_voz(self, voz):
        # La muestra decide cómo suena: si se vuelve a diseñar distinta, las locuciones cambian.
        return {**voz.huella(), "muestra": _huella_archivo(self.muestra(voz)[0])}

    def generar(self, pedidos, aviso=print):
        from . import ia
        tareas, salidas = [], []
        tmp = carpeta_cache() / "tmp"
        for k, (palabras, voz) in enumerate(pedidos):
            ruta, texto_ref = self.muestra(voz)
            salida = tmp / f"{os.getpid()}-{k}.wav"
            salidas.append(salida)
            tareas.append({"tipo": "clonar", "texto": texto_dicho(palabras), "referencia": str(ruta),
                           "texto_referencia": texto_ref, "semilla": voz.semilla, "salida": str(salida),
                           "ajustes": self.AJUSTES})
        if tareas:
            ia.correr("qwen-tts", "qwen_tts.py", {"tareas": tareas}, aviso=aviso)
        out = []
        for s in salidas:
            x, sr = _leer_wav(s)
            s.unlink(missing_ok=True)
            out.append((x, sr, None))
        return out


class ElevenLabs(Proveedor):
    """ElevenLabs por su API, con el tiempo de cada letra (`/with-timestamps`). La clave va en
    ELEVENLABS_API_KEY y nunca se guarda; `voz.id` es el voice_id."""
    nombre = "elevenlabs"
    URL = "https://api.elevenlabs.io/v1/text-to-speech/{id}/with-timestamps?output_format=pcm_24000"
    MODELO = "eleven_multilingual_v2"
    sr = 24000

    def __init__(self, abrir=None):
        import urllib.request
        self.abrir = abrir or urllib.request.urlopen

    def huella(self):
        return {"proveedor": self.nombre, "modelo": self.MODELO}

    def generar(self, pedidos, aviso=print):
        import urllib.request
        clave = os.environ.get("ELEVENLABS_API_KEY")
        if not clave:
            raise VozError("falta ELEVENLABS_API_KEY")
        out = []
        for palabras, voz in pedidos:
            if not voz.id:
                raise VozError(f"la voz «{voz.nombre}» de ElevenLabs no tiene id")
            texto = texto_dicho(palabras)
            cuerpo = json.dumps({"text": texto, "model_id": self.MODELO, "seed": voz.semilla}).encode()
            req = urllib.request.Request(self.URL.format(id=voz.id), data=cuerpo, method="POST",
                                         headers={"xi-api-key": clave, "Content-Type": "application/json"})
            with self.abrir(req, timeout=120) as r:
                datos = json.loads(r.read().decode())
            pcm = np.frombuffer(base64.b64decode(datos["audio_base64"]), dtype="<i2").astype(np.float64) / 32768
            al = datos.get("alignment") or {}
            out.append((pcm, self.sr, palabras_de_letras(palabras, texto, al.get("characters", []),
                                                          al.get("character_start_times_seconds", []),
                                                          al.get("character_end_times_seconds", []))))
        return out


def palabras_de_letras(palabras: list[Palabra], texto: str, letras, inicios, fines) -> list[Palabra] | None:
    """Los tiempos de cada palabra a partir de los de cada letra del texto dicho."""
    if "".join(letras) != texto or not letras:
        return None
    out, pos = [], 0
    for p in palabras:
        i = texto.index(p.dicha, pos)
        j = i + len(p.dicha) - 1
        out.append(Palabra(p.texto, p.dicha, round(float(inicios[i]), 3), round(float(fines[j]), 3)))
        pos = j + 1
    return out


PROVEEDORES = {"qwen": QwenTTS, "elevenlabs": ElevenLabs, "falso": Falso}


def decir(pedidos: list[tuple[str, Voz]], proveedor: Proveedor | None = None, aviso=print) -> list[Locucion]:
    """Cada (texto, voz) dicho, desde el caché si ya se generó. Lo que falta se pide junto al
    proveedor, que es el mismo para todas las voces (Qwen carga sus modelos una sola vez)."""
    if not pedidos:
        return []
    nombres = {v.proveedor for _, v in pedidos}
    if proveedor is None and len(nombres) > 1:
        raise VozError(f"las voces de un mismo pedido usan un solo proveedor, no {sorted(nombres)}")
    prov = proveedor or PROVEEDORES[nombres.pop()]()
    cache = carpeta_cache()
    voces = list({v.nombre: v for _, v in pedidos}.values())
    prov.preparar(voces, aviso=aviso)
    hv = {v.nombre: prov.huella_voz(v) for v in voces}
    piezas = [para_decir(t) for t, _ in pedidos]
    huellas = [_huella(VERSION, prov.huella(), hv[v.nombre], texto_dicho(p))
               for (_, v), p in zip(pedidos, piezas)]
    faltan, vistas = [], set()
    for k, h in enumerate(huellas):
        if h not in vistas and not (cache / f"{h}.json").exists():
            faltan.append(k)
        vistas.add(h)
    if faltan:
        aviso(f"  {len(faltan)} de {len(pedidos)} locuciones por generar ({prov.nombre})")
        hechos = prov.generar([(piezas[k], pedidos[k][1]) for k in faltan], aviso=aviso)
        for k, (x, sr, tiempos) in zip(faltan, hechos):
            x = np.asarray(x, np.float64)
            if not len(x) or not np.isfinite(x).all():
                raise VozError(f"{prov.nombre} devolvió un audio vacío para «{pedidos[k][0][:40]}»")
            fuente = "proveedor" if tiempos else "estimados"
            tiempos = tiempos or estimar_tiempos(x, sr, piezas[k])
            _escribir_wav(cache / f"{huellas[k]}.wav", x, sr)
            meta = {"texto": pedidos[k][0], "dicho": texto_dicho(piezas[k]), "voz": hv[pedidos[k][1].nombre],
                    "proveedor": prov.huella(), "sr": sr, "segundos": round(len(x) / sr, 3),
                    "tiempos": fuente, "palabras": [asdict(p) for p in tiempos]}
            (cache / f"{huellas[k]}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    out = []
    for (t, v), h in zip(pedidos, huellas):
        meta = json.loads((cache / f"{h}.json").read_text(encoding="utf-8"))
        x, sr = _leer_wav(cache / f"{h}.wav")
        out.append(Locucion(t, _a_sr(x, sr), [Palabra(**p) for p in meta["palabras"]], meta["tiempos"], h,
                            v.nombre, {"sr_original": sr}))
    return out


def locuciones(textos: list[str], voz: Voz, proveedor: Proveedor | None = None, aviso=print) -> list[Locucion]:
    """Cada texto dicho por una voz (ver `decir`)."""
    return decir([(t, voz) for t in textos], proveedor, aviso)
