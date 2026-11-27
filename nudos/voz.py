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

**El tiempo de cada palabra**, para los subtítulos palabra por palabra y la sincronía: ElevenLabs lo
da. Con el modelo local lo da el alineador forzado (`QwenAlineador`: Qwen3-ForcedAligner-0.6B,
Apache-2.0, en su entorno; nudos/ia.py, sonido/alinear.py), que Gabriel autorizó el 26 nov. Si el
alineador no está instalado, falla o no calza con el texto, se estima (`estimar_tiempos`): las
pausas del audio se emparejan con la puntuación del texto y cada tramo se reparte por sílabas. La
locución dice cuáles son («proveedor», «alineados» o «estimados»). Una locución del caché con
tiempos estimados se alinea en cuanto hay alineador, sin volver a generarla.
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
    limpiar: bool = False            # cada locución pasa por `limpiar()`: para una voz clonada de una
                                     # grabación con ruido de fondo, que el clon reproduce

    def huella(self) -> dict:
        d = asdict(self)
        d.pop("etiqueta")
        if not self.limpiar:
            d.pop("limpiar")             # así no cambia la huella de las voces de antes
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


# --------------------------------------------------------------------------
# El tiempo de cada palabra, alineado
# --------------------------------------------------------------------------
def _trozos(dicha: str) -> int:
    """Cuántos trozos ve el alineador en una palabra dicha: los pedazos entre espacios que tienen
    alguna letra, número o apóstrofo («treinta y cinco» son tres; «gaza,» es uno)."""
    return sum(1 for s in dicha.split()
               if any(c == "'" or unicodedata.category(c)[0] in "LN" for c in s))


MIN_PALABRA = 0.04     # s: una palabra alineada más corta que esto se reparte con su vecina


def palabras_alineadas(palabras: list[Palabra], trozos: list[dict], segundos: float) -> list[Palabra] | None:
    """Los tiempos de cada palabra a partir de los trozos que alineó el modelo (cada uno con su
    «inicio» y su «fin» en s). None si no calzan: otro número de trozos, tiempos que van hacia
    atrás o que se salen del audio.

    El modelo da los tiempos en pasos de 80 ms y a veces deja una palabra sin duración (sobre
    todo la última, pegada al final del audio): esa palabra comparte el tramo de su vecina,
    repartido por sílabas."""
    cuantos = [_trozos(p.dicha) for p in palabras]
    if not palabras or sum(cuantos) != len(trozos):
        return None
    out, k, antes = [], 0, 0.0
    for p, n in zip(palabras, cuantos):
        if n == 0:                       # sin nada que decir: dura cero, donde terminó la anterior
            out.append(Palabra(p.texto, p.dicha, antes, antes))
            continue
        a = float(trozos[k]["inicio"])
        b = max(a, float(trozos[k + n - 1]["fin"]))
        if a < antes - 0.02 or b > segundos + 0.05:
            return None
        out.append(Palabra(p.texto, p.dicha, a, b))
        antes, k = b, k + n
    con_voz = [i for i, n in enumerate(cuantos) if n]
    for j, i in enumerate(con_voz):
        if out[i].fin - out[i].inicio >= MIN_PALABRA or len(con_voz) < 2:
            continue
        v = con_voz[j - 1] if j > 0 else con_voz[j + 1]
        a, b = min(out[i].inicio, out[v].inicio), max(out[i].fin, out[v].fin)
        primero, segundo = (out[v], out[i]) if v < i else (out[i], out[v])
        s1, s2 = silabas(primero.dicha) + 0.35, silabas(segundo.dicha) + 0.35
        medio = a + (b - a) * s1 / (s1 + s2)
        primero.inicio, primero.fin, segundo.inicio, segundo.fin = a, medio, medio, b
    for p in out:
        p.inicio, p.fin = round(p.inicio, 3), round(p.fin, 3)
    return out


class Alineador:
    """Lo común: `alinear(pedidos)` da, por cada (audio, frecuencia, palabras), las palabras con
    sus tiempos, o None si no pudo."""
    nombre = ""

    def huella(self) -> dict:
        return {"alineador": self.nombre}

    def alinear(self, pedidos: list[tuple[np.ndarray, int, list[Palabra]]], aviso=print
                ) -> list[list[Palabra] | None]:
        raise NotImplementedError


class QwenAlineador(Alineador):
    """Qwen3-ForcedAligner-0.6B, en su entorno (sonido/alinear.py). Una sola llamada alinea
    todo lo que falta: el modelo tarda unos segundos en cargar y casi nada en cada locución."""
    nombre = "qwen3-forcedaligner-0.6b"
    ENTORNO = "qwen-asr"

    def huella(self):
        return {"alineador": self.nombre, "script": "alinear.py/1"}

    @classmethod
    def disponible(cls) -> bool:
        from . import ia
        return (ia.carpeta() / ia.ENTORNOS[cls.ENTORNO]).exists()

    def alinear(self, pedidos, aviso=print):
        from . import ia
        tmp = carpeta_cache() / "tmp"
        tareas, rutas = [], []
        for k, (x, sr, palabras) in enumerate(pedidos):
            ruta = tmp / f"alinear-{os.getpid()}-{k}.wav"
            _escribir_wav(ruta, x, sr)
            rutas.append(ruta)
            tareas.append({"audio": str(ruta), "texto": texto_dicho(palabras), "idioma": "Spanish"})
        try:
            res = ia.correr(self.ENTORNO, "alinear.py", {"tareas": tareas}, aviso=aviso)
        finally:
            for r in rutas:
                r.unlink(missing_ok=True)
        return [palabras_alineadas(p, trozos, len(x) / sr)
                for (x, sr, p), trozos in zip(pedidos, res["alineadas"])]


def _el_alineador(alineador) -> Alineador | None:
    """None (por omisión): el de Qwen si está instalado. False: ninguno."""
    if alineador is False:
        return None
    if alineador is None:
        return QwenAlineador() if QwenAlineador.disponible() else None
    return alineador


def _alinear_cache(cache: Path, pendientes: list[tuple[str, list[Palabra]]], al: Alineador, aviso=print) -> None:
    """Alinea las locuciones del caché que no traen tiempos del proveedor ni se alinearon ya
    con este alineador, y deja el resultado en su JSON. Si una no calza, se queda con los tiempos
    estimados y no se vuelve a intentar con el mismo alineador; si el alineador falla, se vuelve
    a intentar la próxima vez."""
    from . import ia
    hal = al.huella()
    faltan = []
    for h, piezas in pendientes:
        meta = json.loads((cache / f"{h}.json").read_text(encoding="utf-8"))
        if meta["tiempos"] != "proveedor" and meta.get("alineador") != hal:
            faltan.append((h, piezas, meta))
    if not faltan:
        return
    aviso(f"  alineando {len(faltan)} locuciones ({al.nombre})")
    audios = [_leer_wav(cache / f"{h}.wav") for h, _, _ in faltan]
    try:
        res = al.alinear([(x, sr, p) for (_, p, _), (x, sr) in zip(faltan, audios)], aviso=aviso)
    except ia.IAError as e:
        aviso(f"  el alineador falló; quedan los tiempos estimados: {str(e).splitlines()[0]}")
        return
    for (h, _, meta), palabras in zip(faltan, res):
        meta["alineador"] = hal
        if palabras:
            meta["tiempos"], meta["palabras"] = "alineados", [asdict(p) for p in palabras]
        else:
            aviso(f"  «{meta['texto'][:40]}» no calzó con el alineador; quedan los tiempos estimados")
        (cache / f"{h}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def decir(pedidos: list[tuple[str, Voz]], proveedor: Proveedor | None = None, aviso=print,
          alineador: Alineador | None | bool = None) -> list[Locucion]:
    """Cada (texto, voz) dicho, desde el caché si ya se generó. Lo que falta se pide junto al
    proveedor, que es el mismo para todas las voces (Qwen carga sus modelos una sola vez). Lo que
    no trae tiempos del proveedor se alinea (`alineador`: por omisión, el de Qwen si está
    instalado; False, ninguno)."""
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
            if pedidos[k][1].limpiar:
                x = np.asarray(limpiar(x, sr), np.float64)
            fuente = "proveedor" if tiempos else "estimados"
            tiempos = tiempos or estimar_tiempos(x, sr, piezas[k])
            _escribir_wav(cache / f"{huellas[k]}.wav", x, sr)
            meta = {"texto": pedidos[k][0], "dicho": texto_dicho(piezas[k]), "voz": hv[pedidos[k][1].nombre],
                    "proveedor": prov.huella(), "sr": sr, "segundos": round(len(x) / sr, 3),
                    "tiempos": fuente, "palabras": [asdict(p) for p in tiempos]}
            (cache / f"{huellas[k]}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    al = _el_alineador(alineador)
    if al is not None:
        unicas = {h: p for h, p in zip(huellas, piezas)}
        _alinear_cache(cache, list(unicas.items()), al, aviso)
    out = []
    for (t, v), h in zip(pedidos, huellas):
        meta = json.loads((cache / f"{h}.json").read_text(encoding="utf-8"))
        x, sr = _leer_wav(cache / f"{h}.wav")
        out.append(Locucion(t, _a_sr(x, sr), [Palabra(**p) for p in meta["palabras"]], meta["tiempos"], h,
                            v.nombre, {"sr_original": sr}))
    return out


def locuciones(textos: list[str], voz: Voz, proveedor: Proveedor | None = None, aviso=print,
               alineador: Alineador | None | bool = None) -> list[Locucion]:
    """Cada texto dicho por una voz (ver `decir`)."""
    return decir([(t, voz) for t in textos], proveedor, aviso, alineador)


# --------------------------------------------------------------------------
# Las grabaciones: la voz de Gabriel
# --------------------------------------------------------------------------
# Lo que el reconocimiento de voz debería reconocer: los nombres de los nudos y las palabras de las
# fichas. Ayuda poco con las que suenan igual: en las grabaciones de Gabriel siguió escribiendo «gasa»
# por «gaza» y «arcaos» por «ahorcados». Por eso la muestra para clonar se compara con la ficha.
CONTEXTO = ("Nudos de cuerda: as de guía, ballestrinque, nudo simple, nudo ocho, ocho doble, nudo de "
            "pescador, amarre cuadrado, amarre diagonal, vuelta de escota, cote, rizo. Chicote, firme, gaza, "
            "seno, vuelta, ahorcados, palo, travesaño, argolla, mosquetón.")
REDUCCION = 12.0       # dB: lo más que `limpiar` baja el ruido de fondo
# «Este» y «esto» también son palabras de verdad («este nudo»), pero aquí solo descartan tramos
# para la muestra, y sobran tramos.
MULETILLAS = {"eh", "em", "mm", "mmm", "ah", "este", "esto"}
EXTENSIONES = (".m4a", ".mp3", ".wav", ".ogg", ".opus", ".aac", ".flac")


def leer_grabacion(ruta) -> np.ndarray:
    """Una grabación en cualquier formato que lea ffmpeg (m4a, mp3, wav…), en mono y a SR."""
    import subprocess
    p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True)
    if p.returncode != 0:
        raise VozError(f"no se pudo leer {ruta}: {p.stderr.decode(errors='replace').strip()[:200]}")
    return np.frombuffer(p.stdout, np.float32).copy()


def limpiar(x, sr: int = SR, reduccion: float = REDUCCION) -> np.ndarray:
    """Una grabación de celular lista para la mezcla o para clonarla: sin los graves que no son voz
    (pasa altos de 70 Hz) y con el ruido de fondo hasta `reduccion` dB más bajo. Es una compuerta
    espectral suave: el espectro del ruido sale del 10 % de los cuadros más callados, y cada banda
    baja más cuanto más cerca está del ruido. La ganancia se suaviza en el tiempo y en la
    frecuencia, para que no queden pitidos, y nunca baja más que `reduccion`."""
    from scipy.ndimage import uniform_filter
    from scipy.signal import butter, istft, sosfiltfilt, stft
    x = np.asarray(x, np.float64)
    if len(x) < sr // 10:
        return x.astype(np.float32)
    x = sosfiltfilt(butter(4, 70, "high", fs=sr, output="sos"), x)
    n = 2048 if sr >= 32000 else 1024
    _, _, Z = stft(x, sr, nperseg=n, noverlap=3 * n // 4)
    P = np.abs(Z) ** 2
    e = P.sum(axis=0)
    ruido = P[:, e <= np.percentile(e, 10)].mean(axis=1, keepdims=True)
    snr = P / np.maximum(ruido, 1e-20)
    G = np.sqrt(np.clip(1 - 2.0 / np.maximum(snr, 1e-9), 0, 1))     # sobresustracción: 2 veces el ruido
    G = np.maximum(uniform_filter(G, size=(3, 5)), 10 ** (-reduccion / 20))
    _, y = istft(Z * G, sr, nperseg=n, noverlap=3 * n // 4)
    return y[:len(x)].astype(np.float32)


@dataclass
class Transcripcion:
    texto: str
    palabras: list[Palabra]      # como las escribió el modelo, con su inicio y su fin
    segundos: float
    tiempos: str                 # «alineados», o «sin» si el alineador no calzó


def transcribir(audios: list[np.ndarray], contexto: str = CONTEXTO, aviso=print) -> list[Transcripcion]:
    """Lo que dice cada grabación (mono, a SR), con el tiempo de cada palabra: Qwen3-ASR escribe el
    texto (sonido/transcribir.py) y el alineador lo pone en el tiempo (sonido/alinear.py). Cada una
    se guarda en el caché con la huella de su audio, así que nada se transcribe dos veces."""
    from . import ia
    carpeta = carpeta_cache() / "transcripciones"
    huellas = [_huella("transcribir/1", hashlib.sha256(np.asarray(x, np.float32).tobytes()).hexdigest(), contexto)
               for x in audios]
    faltan = [k for k, h in enumerate(huellas) if not (carpeta / f"{h}.json").exists()]
    if faltan:
        aviso(f"  transcribiendo {len(faltan)} grabaciones (Qwen3-ASR)")
        tmp = carpeta_cache() / "tmp"
        rutas = [tmp / f"transcribir-{os.getpid()}-{k}.wav" for k in faltan]
        for r, k in zip(rutas, faltan):
            _escribir_wav(r, audios[k], SR)
        try:
            res = ia.correr("qwen-asr", "transcribir.py", {"tareas": [
                {"audio": str(r), "idioma": "Spanish", "contexto": contexto} for r in rutas]}, aviso=aviso)
        finally:
            for r in rutas:
                r.unlink(missing_ok=True)
        textos = [h["texto"].strip() for h in res["hechas"]]
        piezas = [[Palabra(t, t) for t in texto.split()] for texto in textos]
        alineadas = QwenAlineador().alinear([(audios[k], SR, p) for k, p in zip(faltan, piezas)], aviso=aviso)
        for k, texto, p, al in zip(faltan, textos, piezas, alineadas):
            meta = {"texto": texto, "segundos": round(len(audios[k]) / SR, 3), "tiempos": "alineados" if al else "sin",
                    "palabras": [asdict(w) for w in (al or p)]}
            carpeta.mkdir(parents=True, exist_ok=True)
            (carpeta / f"{huellas[k]}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                                        encoding="utf-8")
    out = []
    for h in huellas:
        meta = json.loads((carpeta / f"{h}.json").read_text(encoding="utf-8"))
        out.append(Transcripcion(meta["texto"], [Palabra(**w) for w in meta["palabras"]], meta["segundos"],
                                 meta["tiempos"]))
    return out


def _clave(palabra: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", palabra.casefold()) if c.isalnum())


def _tropieza(palabras: list[Palabra], ventana: int = 3) -> bool:
    """Si hay un tropiezo: una muletilla, o una palabra que se repite a menos de `ventana` palabras
    («no se cierra ni se, ni se corre», «por por una argolla»)."""
    claves = [_clave(p.texto) for p in palabras]
    for i, c in enumerate(claves):
        if c in MULETILLAS or (c and c in claves[max(0, i - ventana):i]):
            return True
    return False


def tramos_limpios(t: Transcripcion, largo: tuple[float, float] = (8.0, 14.0), pausa: float = 0.3,
                   ideal: float = 11.0, fuente: str | None = None) -> list[tuple[float, int, int]]:
    """Los tramos de una transcripción que sirven de muestra: entre pausas de por lo menos `pausa`
    s, de `largo` s y sin tropiezos. Con `fuente`, el texto que se leyó (la especificación del
    nudo), solo los tramos que dicen palabra por palabra un pedazo de él: así el texto de la
    muestra es justo lo que se oye, sin tropiezos que no se repiten («de distinto todo grosor») ni
    palabras mal reconocidas. Da (puntaje, primera palabra, última + 1), del mejor al peor: mejor
    cuanto más cerca de `ideal` s y si empieza y termina con una oración."""
    w = t.palabras
    if t.tiempos != "alineados" or not w:
        return []
    leido = None
    if fuente:
        leido = " " + " ".join(c for c in (_clave(x) for x in texto_dicho(para_decir(fuente)).split()) if c) + " "
    corte = [0] + [i for i in range(1, len(w)) if w[i].inicio - w[i - 1].fin >= pausa] + [len(w)]
    out = []
    for a in corte[:-1]:
        for b in corte:
            if b <= a:
                continue
            dur = w[b - 1].fin - w[a].inicio
            if dur > largo[1]:
                break
            if dur < largo[0] or _tropieza(w[a:b]):
                continue
            if leido is not None and (" " + " ".join(c for c in (_clave(p.texto) for p in w[a:b]) if c) + " ") not in leido:
                continue
            puntos = -abs(dur - ideal)
            puntos += 2.0 if (a == 0 or w[a - 1].texto.endswith((".", ":"))) else 0.0
            puntos += 2.0 if w[b - 1].texto.endswith((".", ":")) else 0.0
            out.append((puntos, a, b))
    return sorted(out, reverse=True)


def recorte(x, desde: float, hasta: float, margen: float = 0.12, fundido: float = 0.03) -> np.ndarray:
    """Un tramo de una grabación (a SR), con `margen` s de aire a cada lado y fundidos cortos."""
    a, b = max(0, int((desde - margen) * SR)), min(len(x), int((hasta + margen) * SR))
    y = np.array(x[a:b], np.float64)
    k = min(int(fundido * SR), len(y) // 2)
    if k:
        rampa = np.linspace(0, 1, k)
        y[:k] *= rampa
        y[-k:] *= rampa[::-1]
    return y.astype(np.float32)


def locucion_grabada(x, palabras: list[Palabra], texto: str = "", voz: str = "grabada") -> Locucion:
    """Una grabación como si fuera una locución, para ponerla en la mezcla (nudos/mezcla.py)."""
    x = np.asarray(x, np.float32)
    texto = texto or " ".join(p.texto for p in palabras)
    return Locucion(texto, x, palabras, "alineados", _huella("grabada", hashlib.sha256(x.tobytes()).hexdigest()), voz)
