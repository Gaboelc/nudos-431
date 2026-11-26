"""La música de los videos (T23b): folk acústico de campamento, a 100 pulsos por minuto, en sol
mayor y en 4/4, con un arreglo distinto en cada capítulo. Es propia: la compuso Claude.

`musica(capitulos, golpe)` da la pista de un video a partir de sus capítulos (y del instante del
golpe del nudo apretado, en el cierre). Cada capítulo empieza en un pulso (`al_pulso`), con su
propio primer compás; si no dura compases enteros, el último es más corto. Hay dos candidatas:

- **«codigo» (A):** `componer()` escribe las notas: la guitarra punteada (Travis), el bajo, el
  shaker, las palmas, el bombo apagado, y el motivo de la serie en kalimba, que abre y cierra
  cada video. Las notas se humanizan con una semilla fija, así que la misma semilla da la misma
  música. La guitarra y el bajo los toca FluidSynth con GeneralUser GS (programas 25 y 32 de
  General MIDI); la kalimba, el glockenspiel y la percusión salen de muestras del VCSL (CC0) con
  un muestreador propio (`Banco`). Sin los bancos, `Sintetico` toca todo con síntesis simple: así
  corren las pruebas.
- **«ace-step» (B):** ACE-Step 1.5 (MIT) genera en la tarjeta una pieza por arreglo, con el mismo
  pulso y tono, y `armar_ace()` la corta a compás (librosa, en su entorno) en los capítulos.

**Los arreglos** (ARREGLOS): constante y despejado bajo la voz en los pasos; más ralo en los
errores; más lleno en la aplicación; el motivo abre en la apertura y cierra en el cierre, con el
acorde final en el golpe.

Todo se guarda con su huella fuera de git (`NUDOS_MUSICA`; por omisión,
`%LOCALAPPDATA%\\nudos\\musica`).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path

import numpy as np

SR = 48000
BPM = 100
PULSO = 60.0 / BPM          # 0,6 s
POR_COMPAS = 4
SEMILLA = 431
VERSION = "1"               # súbela si cambia la composición o el sonido

CAPITULOS = ("apertura", "materiales", "pasos", "verificacion", "errores", "aplicacion", "seguridad", "cierre")


class MusicaError(RuntimeError):
    """La música no se puede armar así."""


@dataclass
class Capitulo:
    nombre: str
    inicio: float      # s
    fin: float


@dataclass
class Nota:
    t: float           # s
    dur: float         # s
    nota: int          # MIDI
    vel: int           # 1 a 127


@dataclass
class Musica:
    mezcla: np.ndarray                  # (n, 2) float32 a SR
    capitulos: list[Capitulo]           # ya en el pulso
    pulsos: np.ndarray                  # s
    compases: np.ndarray                # s: el primer pulso de cada compás
    candidata: str
    huella: str = ""
    pistas: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# El pulso
# --------------------------------------------------------------------------
def al_pulso(t: float, origen: float = 0.0) -> float:
    """El pulso más cercano a t."""
    return origen + round((t - origen) / PULSO) * PULSO


def en_pulso(capitulos: list[Capitulo]) -> list[Capitulo]:
    """Los capítulos con sus cortes en el pulso más cercano (desde el inicio del primero), cada
    uno de dos pulsos por lo menos y uno detrás del otro."""
    if not capitulos:
        return []
    origen = capitulos[0].inicio
    out, t = [], origen
    for i, c in enumerate(capitulos):
        if c.nombre not in CAPITULOS:
            raise MusicaError(f"«{c.nombre}» no es un capítulo; puede ser {', '.join(CAPITULOS)}")
        fin = al_pulso(c.fin, origen)
        fin = max(fin, t + 2 * PULSO)
        out.append(Capitulo(c.nombre, round(t, 6), round(fin, 6)))
        t = fin
    return out


def rejilla(capitulos: list[Capitulo]) -> tuple[np.ndarray, np.ndarray]:
    """Los pulsos y los comienzos de compás: cada capítulo empieza un compás nuevo."""
    pulsos, compases = [], []
    for c in capitulos:
        n = int(round((c.fin - c.inicio) / PULSO))
        for k in range(n):
            t = c.inicio + k * PULSO
            pulsos.append(t)
            if k % POR_COMPAS == 0:
                compases.append(t)
    return np.round(np.array(pulsos), 6), np.round(np.array(compases), 6)


# --------------------------------------------------------------------------
# La composición
# --------------------------------------------------------------------------
# Las voces de la guitarra en posición abierta: (bajo, bajo alterno, agudos de grave a agudo).
ACORDES = {
    "G": (43, 50, (59, 62, 67)), "C": (48, 43, (55, 60, 64)), "D": (50, 45, (57, 62, 66)),
    "Em": (40, 47, (55, 59, 64)), "Am": (45, 52, (57, 60, 64)), "D/F#": (42, 50, (57, 62, 66)),
    "Bm": (47, 54, (59, 62, 66)),
}
RAIZ_BAJO = {"G": 31, "C": 36, "D": 38, "Em": 28, "Am": 33, "D/F#": 30, "Bm": 35}

# El motivo de la serie, en corcheas (índice de corchea, nota, duración en corcheas), dos compases:
# sube por el acorde de sol y contesta. «abre» termina en re (queda abierto); «cierra», en sol.
MOTIVO = {
    "abre": [(0, 74, 2), (2, 79, 2), (4, 83, 2), (6, 81, 1), (7, 79, 1), (8, 76, 2), (10, 74, 6)],
    "cierra": [(0, 74, 2), (2, 79, 2), (4, 83, 2), (6, 81, 1), (7, 79, 1), (8, 81, 2), (10, 79, 6)],
}

ARREGLOS = {
    # acordes por compás (se repiten), y qué toca cada instrumento.
    "apertura": dict(acordes=("G", "D/F#", "Em", "C"), guitarra="arpegio", bajo="larga", shaker="desde2",
                     bombo=None, palmas=False, motivo="abre", glock=None),
    "materiales": dict(acordes=("G", "C", "G", "D"), guitarra="arpegio", bajo="larga", shaker="suave",
                       bombo=None, palmas=False, motivo=None, glock=None),
    "pasos": dict(acordes=("G", "C", "Em", "D", "G", "C", "D", "G", "C", "G", "Am", "D", "C", "G", "D", "G"),
                  guitarra="travis", bajo="raiz_quinta", shaker="suave", bombo="suave", palmas=False,
                  motivo=None, glock=None),
    "verificacion": dict(acordes=("Em", "C", "G", "D"), guitarra="travis", bajo="raiz_quinta", shaker="suave",
                         bombo=None, palmas=False, motivo=None, glock="pregunta"),
    "errores": dict(acordes=("Am", "Em", "C", "D"), guitarra="lenta", bajo="larga", shaker=None,
                    bombo=None, palmas=False, motivo=None, glock=None),
    "aplicacion": dict(acordes=("G", "D", "Em", "C"), guitarra="travis", bajo="caminante", shaker="lleno",
                       bombo="lleno", palmas=True, motivo=None, glock="contracanto"),
    "seguridad": dict(acordes=("C", "G", "D", "Em"), guitarra="lenta", bajo="larga", shaker=None,
                      bombo=None, palmas=False, motivo=None, glock=None),
    "cierre": dict(acordes=("G", "C", "D", "G"), guitarra="travis", bajo="raiz_quinta", shaker="suave",
                   bombo=None, palmas=False, motivo="cierra", glock=None),
}

INSTRUMENTOS = ("guitarra", "bajo", "kalimba", "glock", "shaker", "palmas", "bombo")
TEMBLOR = {"guitarra": 0.007, "bajo": 0.006, "kalimba": 0.005, "glock": 0.004, "shaker": 0.004,
           "palmas": 0.006, "bombo": 0.003}       # s: cuánto se corre cada golpe, al azar


def componer(capitulos: list[Capitulo], golpe: float | None = None, semilla: int = SEMILLA
             ) -> dict[str, list[Nota]]:
    """Las notas de cada instrumento. Los capítulos ya van en el pulso (`en_pulso`). `golpe` es
    el instante del nudo apretado: ahí suena el acorde final y la música se queda sonando."""
    rng = np.random.default_rng(semilla)
    notas: dict[str, list[Nota]] = {i: [] for i in INSTRUMENTOS}
    corchea = PULSO / 2

    def pon(inst: str, t: float, dur: float, nota: int, vel: float) -> None:
        if golpe is not None and t >= golpe - 1e-6 and inst != "final":
            return
        notas[inst].append(Nota(t, dur, int(nota), int(np.clip(vel, 1, 127))))

    for ci, c in enumerate(capitulos):
        arr = ARREGLOS[c.nombre]
        n_pulsos = int(round((c.fin - c.inicio) / PULSO))
        compases = [(k, min(POR_COMPAS, n_pulsos - k * POR_COMPAS))
                    for k in range((n_pulsos + POR_COMPAS - 1) // POR_COMPAS)]
        ultimo_cap = ci == len(capitulos) - 1
        for k, largo in compases:
            t0 = c.inicio + k * POR_COMPAS * PULSO
            acorde = arr["acordes"][k % len(arr["acordes"])]
            sig = arr["acordes"][(k + 1) % len(arr["acordes"])]
            bajo, alterno, agudos = ACORDES[acorde]
            final_de_cap = k == len(compases) - 1
            # La guitarra.
            g = arr["guitarra"]
            if g == "travis":
                patron = [("b", agudos[2]), ("a", agudos[0]), ("t", None), ("a", agudos[1]),
                          ("b", None), ("a", agudos[0]), ("t", None), ("a", agudos[2] if k % 2 else agudos[1])]
                for e in range(2 * largo):
                    tipo, alto = patron[e]
                    t = t0 + e * corchea
                    if tipo == "b":
                        pon("guitarra", t, 2 * PULSO, bajo, 74 if e == 0 else 66)
                        if alto is not None and e == 0:
                            pon("guitarra", t + 0.004, 1.5 * PULSO, alto, 64)
                    elif tipo == "t":
                        pon("guitarra", t, 2 * PULSO, alterno, 62)
                    else:
                        pon("guitarra", t, 1.5 * PULSO, alto, 56 + 4 * (e == 3))
            elif g == "arpegio":
                for e, nota in enumerate([bajo, agudos[0], agudos[1], agudos[2]][:largo]):
                    pon("guitarra", t0 + e * PULSO, (4 - e) * PULSO, nota, 50 + 3 * e)
            elif g == "lenta":
                pon("guitarra", t0, 4 * PULSO, bajo, 56)
                for e, nota in enumerate(agudos[:max(0, largo - 1)], start=1):
                    pon("guitarra", t0 + e * PULSO, (4 - e) * PULSO + 0.4, nota, 46 + 2 * e)
            # El bajo.
            raiz = RAIZ_BAJO[acorde]
            b = arr["bajo"]
            if b == "larga":
                pon("bajo", t0, largo * PULSO * 0.95, raiz, 58)
            elif b == "raiz_quinta":
                pon("bajo", t0, 1.8 * PULSO, raiz, 66)
                if largo >= 3:
                    pon("bajo", t0 + 2 * PULSO, 1.6 * PULSO if largo == 4 else 0.9 * PULSO, raiz + 7, 58)
                if largo == 4 and k % 2 == 1 and not final_de_cap:
                    destino = RAIZ_BAJO[sig]
                    paso = destino - 1 if destino > raiz else destino + 2
                    pon("bajo", t0 + 3.5 * PULSO, 0.45 * PULSO, paso, 52)
            elif b == "caminante":
                for e, (off, iv, v) in enumerate([(0, 0, 70), (1.5, 0, 56), (2, 7, 64), (3, 12, 58)]):
                    if off < largo:
                        pon("bajo", t0 + off * PULSO, 0.45 * PULSO if off % 1 else 0.9 * PULSO, raiz + iv, v)
            # El shaker: corcheas, con el acento en el contratiempo.
            s = arr["shaker"]
            if s and not (s == "desde2" and k == 0):
                base = {"suave": 34, "desde2": 34, "lleno": 50}[s]
                for e in range(2 * largo):
                    pon("shaker", t0 + e * corchea, corchea, 1 if e % 2 else 0, base + (10 if e % 2 else 0))
                if final_de_cap and not ultimo_cap:
                    pon("shaker", t0 + (largo - 1) * PULSO, PULSO, 2, base + 8)     # el redoble al cambiar
            # El bombo apagado y las palmas.
            if arr["bombo"]:
                v = 40 if arr["bombo"] == "suave" else 62
                pon("bombo", t0, PULSO, 0, v)
                if largo >= 3:
                    pon("bombo", t0 + 2 * PULSO, PULSO, 0, v - 6)
            if arr["palmas"]:
                for off in (1, 3):
                    if off < largo:
                        pon("palmas", t0 + off * PULSO, PULSO, 0, 66)
            # El glockenspiel.
            gl = arr["glock"]
            if gl == "pregunta" and k % 2 == 0:
                frase = [(0, 83), (1, 86)] if (k // 2) % 2 == 0 else [(0, 81), (1, 79)]
                for off, nota in frase:
                    if off < largo:
                        pon("glock", t0 + off * PULSO, 2 * PULSO, nota, 52)
            elif gl == "contracanto":
                # Dos blancas por compás, la tercera y la quinta del acorde, arriba de la guitarra.
                tercera, quinta = {"G": (83, 86), "D": (78, 81), "Em": (79, 83), "C": (76, 79),
                                   "Am": (76, 81), "D/F#": (78, 81), "Bm": (78, 83)}[acorde]
                for off, nota in ((0, tercera), (2, quinta)):
                    if off < largo:
                        pon("glock", t0 + off * PULSO, 2 * PULSO, nota, 50 if off == 0 else 44)
        # El motivo, en los dos primeros compases del capítulo. En el cierre con golpe, su primer
        # compás llega justo al golpe, que pone el acorde final en lugar de la respuesta.
        if arr["motivo"]:
            inicio = c.inicio
            frase = MOTIVO[arr["motivo"]]
            if arr["motivo"] == "cierra" and golpe is not None:
                inicio = max(c.inicio, golpe - POR_COMPAS * PULSO)
                frase = [f for f in frase if f[0] < 8]
            for e, nota, d in frase:
                t = inicio + e * corchea
                if t < c.fin - 1e-6:
                    pon("kalimba", t, d * corchea + 0.8, nota, 80 if e == 0 else 72)
    # El acorde final, con el golpe: guitarra rasgueada hacia abajo, bajo y kalimba en sol.
    if golpe is not None:
        bajo, alterno, agudos = ACORDES["G"]
        for i, nota in enumerate([bajo, alterno, *agudos]):
            notas["guitarra"].append(Nota(golpe + 0.018 * i, 4.5, nota, 84 - 2 * i))
        notas["bajo"].append(Nota(golpe, 4.0, RAIZ_BAJO["G"], 74))
        notas["kalimba"].append(Nota(golpe + 0.03, 3.0, 79, 76))
        notas["kalimba"].append(Nota(golpe + 0.03, 3.0, 91, 54))
    # La humanización: cada golpe se corre un poco y cambia de fuerza.
    for inst, lista in notas.items():
        for n in lista:
            n.t = max(0.0, n.t + float(np.clip(rng.normal(0, TEMBLOR[inst]), -2.5 * TEMBLOR[inst],
                                               2.5 * TEMBLOR[inst])))
            n.vel = int(np.clip(round(n.vel + rng.normal(0, 5)), 1, 127))
        lista.sort(key=lambda n: (n.t, n.nota))
    return notas


# --------------------------------------------------------------------------
# Los instrumentos
# --------------------------------------------------------------------------
def _a_estereo(x) -> np.ndarray:
    x = np.asarray(x, np.float64)
    return np.column_stack([x, x]) if x.ndim == 1 else x[:, :2]


def _a_sr(x, sr: int) -> np.ndarray:
    from math import gcd
    from scipy.signal import resample_poly
    if sr == SR:
        return np.asarray(x, np.float64)
    g = gcd(SR, sr)
    return resample_poly(np.asarray(x, np.float64), SR // g, sr // g, axis=0)


def _leer_wav(ruta: Path) -> tuple[np.ndarray, int]:
    import warnings
    from scipy.io import wavfile
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sr, x = wavfile.read(ruta)
    if x.dtype.kind == "i":
        x = x / float(2 ** (8 * x.dtype.itemsize - 1))
    elif x.dtype.kind == "u":
        x = (x - 128) / 128.0
    return np.asarray(x, np.float64), int(sr)


def _transponer(x: np.ndarray, semitonos: float) -> np.ndarray:
    """La muestra más aguda o más grave, cambiando su velocidad (como un muestreador)."""
    from scipy.signal import resample_poly
    if abs(semitonos) < 1e-6:
        return x
    r = Fraction(2 ** (-semitonos / 12)).limit_denominator(240)
    return resample_poly(x, r.numerator, r.denominator, axis=0)


_NOTA = re.compile(r"_([A-G]#?)(\d)(?=_)")
_NOMBRES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def nota_de(nombre: str) -> int | None:
    m = _NOTA.search(nombre)
    return None if m is None else 12 * (int(m.group(2)) + 1) + _NOMBRES[m.group(1)]


def altura(x: np.ndarray, esperada: float, sr: int = SR) -> float:
    """La altura real de una muestra (en notas MIDI con decimales), buscando el pico del espectro
    a menos de 80 centésimas de la esperada, justo después del ataque. Si no hay un pico claro,
    da la esperada."""
    m = x.mean(axis=1) if x.ndim > 1 else x
    i = int(np.argmax(np.abs(m)))
    seg = m[i + int(0.02 * sr): i + int(0.02 * sr) + int(0.6 * sr)]
    if len(seg) < int(0.1 * sr):
        return esperada
    n = 8 * len(seg)
    esp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    fr = np.fft.rfftfreq(n, 1 / sr)
    f0 = 440.0 * 2 ** ((esperada - 69) / 12)
    banda = (fr > f0 * 2 ** (-0.8 / 12)) & (fr < f0 * 2 ** (0.8 / 12))
    if not banda.any() or esp[banda].max() < 0.1 * esp[(fr > 50)].max():
        return esperada
    k = np.flatnonzero(banda)[np.argmax(esp[banda])]
    if 0 < k < len(esp) - 1:      # el pico, interpolado con una parábola
        a, b, c = np.log(esp[k - 1:k + 2] + 1e-12)
        k = k + 0.5 * (a - c) / (a - 2 * b + c)
    return 69 + 12 * np.log2(k * sr / n / 440.0)


class Banco:
    """Un muestreador de golpes sueltos (sin bucles): kalimba, glockenspiel y percusión del VCSL.
    Cada nota toma la muestra más cercana (con su capa de fuerza, si tiene) y la transpone; las
    muestras repetidas se turnan. Los nombres del VCSL van una octava abajo de lo que suena (el
    do central es C3), y la kalimba, una mbira, no está afinada a 440 Hz: `afinado` mide la altura
    real de cada muestra y la corrige."""

    def __init__(self, carpeta: Path, afinado: bool, capas: dict[str, int] | None = None,
                 tipos: dict[int, str] | None = None, octava: int = 12):
        self.carpeta = Path(carpeta)
        self.afinado = afinado
        self.muestras: list[dict] = []
        for ruta in sorted(self.carpeta.glob("*.wav")):
            x, sr = _leer_wav(ruta)
            x = _a_sr(_a_estereo(x), sr)
            capa = next((v for k, v in (capas or {}).items() if k in ruta.name.lower()), 64)
            etiqueta = nota_de(ruta.name)
            nota = None
            if afinado and etiqueta is not None:
                etiqueta += octava
                nota = altura(x, etiqueta)
            self.muestras.append({"x": x, "etiqueta": etiqueta, "nota": nota, "capa": capa, "nombre": ruta.name})
        if not self.muestras:
            raise MusicaError(f"no hay muestras en {self.carpeta}")
        # Cada banco viene grabado a su nivel (el glockenspiel, muy bajo): todo el banco se lleva
        # a un pico de 0,7, sin cambiar la diferencia entre sus capas de fuerza.
        pico = max(float(np.abs(m["x"]).max()) for m in self.muestras)
        for m in self.muestras:
            m["x"] = m["x"] * (0.7 / max(pico, 1e-9))
        self.tipos = tipos or {}
        self.turno: dict = {}

    def tocar(self, nota: int, vel: int) -> np.ndarray:
        if self.afinado:
            afinadas = [m for m in self.muestras if m["nota"] is not None]
            dist = min(abs(m["etiqueta"] - nota) for m in afinadas)
            cand = [m for m in afinadas if abs(m["etiqueta"] - nota) == dist]
        else:
            patron = self.tipos.get(nota, "")
            cand = [m for m in self.muestras if patron.lower() in m["nombre"].lower()] or self.muestras
        capa = min({m["capa"] for m in cand}, key=lambda c: abs(c - vel))
        cand = [m for m in cand if m["capa"] == capa]
        clave = (nota, capa)
        i = self.turno.get(clave, 0)
        self.turno[clave] = i + 1
        m = cand[i % len(cand)]
        x = _transponer(m["x"], nota - m["nota"]) if self.afinado else m["x"]
        return x * (vel / 127.0) ** 1.6


def _sumar(pista: np.ndarray, x: np.ndarray, t: float) -> None:
    i = int(round(t * SR))
    if i >= len(pista):
        return
    j = min(len(pista), i + len(x))
    pista[i:j] += x[:j - i]


class Sintetico:
    """Todo con síntesis simple (sin bancos ni programas aparte), para las pruebas: cuerdas
    pulsadas que decaen, una kalimba de parciales inarmónicos y golpes de ruido filtrado."""
    nombre = "sintetico"

    def huella(self) -> dict:
        return {"instrumentos": self.nombre}

    def pista(self, inst: str, notas: list[Nota], dur: float) -> np.ndarray:
        n = int(np.ceil(dur * SR))
        out = np.zeros((n + 5 * SR, 2))
        rng = np.random.default_rng(7)
        for nt in notas:
            v = (nt.vel / 127) ** 1.6
            if inst in ("shaker", "palmas", "bombo"):
                L = int(0.12 * SR)
                t = np.arange(L) / SR
                if inst == "bombo":
                    s = np.sin(2 * np.pi * (55 + 60 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.09)
                else:
                    s = rng.standard_normal(L) * np.exp(-t / (0.02 if inst == "palmas" else 0.04))
            else:
                L = int(min(nt.dur + 0.5, 4.0) * SR)
                t = np.arange(L) / SR
                f = 440.0 * 2 ** ((nt.nota - 69) / 12)
                if inst in ("kalimba", "glock"):
                    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d)
                            for r, a, d in ((1, 1, 0.9), (2.76 if inst == "glock" else 5.4, 0.25, 0.15)))
                else:
                    s = sum(np.sin(2 * np.pi * f * h * t) / h ** 1.5 for h in (1, 2, 3, 4)) * np.exp(-t / 0.6)
                s *= np.minimum(1, t / 0.003)
            _sumar(out, _a_estereo(s * v * 0.5), nt.t)
        return out


class Muestreado:
    """La guitarra y el bajo por FluidSynth con GeneralUser GS; lo demás, con los bancos del VCSL."""
    nombre = "muestreado"
    PROGRAMAS = {"guitarra": 25, "bajo": 32}
    VCSL = {"kalimba": ("Kalimba, Tanzania", True, None, None),
            "glock": ("Glockenspiel", True, {"soft": 40, "medium": 72, "loud": 105}, None),
            "shaker": ("Shaker, Small", False, None, {0: "HighFaster_Down", 1: "HighFaster_Up", 2: "Roll_Fast"}),
            "palmas": ("Claps", False, None, {0: "Clap_rr"}),
            "bombo": ("Bass Drum 1", False, {"_v2_": 30, "_v3_": 50, "_v5_": 75, "_v7_": 100}, None)}

    def __init__(self):
        from . import ia
        base = ia.carpeta() / "musica"
        self.fluidsynth = next(iter(sorted(base.glob("fluidsynth/*/bin/fluidsynth.exe"))), None)
        self.sf2 = base / "bancos" / "GeneralUser-GS" / "GeneralUser-GS.sf2"
        self.vcsl = base / "bancos" / "vcsl"
        if self.fluidsynth is None or not self.sf2.exists() or not self.vcsl.exists():
            raise MusicaError(f"faltan FluidSynth o los bancos en {base} (ver nudos/ia.py)")
        self.bancos: dict[str, Banco] = {}

    def huella(self) -> dict:
        h = hashlib.sha256()
        for ruta in sorted([self.sf2, *self.vcsl.rglob("*.wav")]):
            h.update(f"{ruta.name}:{ruta.stat().st_size}".encode())
        return {"instrumentos": self.nombre, "bancos": h.hexdigest()[:16], "fluidsynth": self.fluidsynth.parent.parent.name}

    def pista(self, inst: str, notas: list[Nota], dur: float) -> np.ndarray:
        if inst in self.PROGRAMAS:
            return self._fluidsynth(self.PROGRAMAS[inst], notas, dur)
        if inst not in self.bancos:
            carpeta, afinado, capas, tipos = self.VCSL[inst]
            self.bancos[inst] = Banco(self.vcsl / carpeta, afinado, capas, tipos)
        banco = self.bancos[inst]
        out = np.zeros((int(np.ceil(dur * SR)) + 8 * SR, 2))
        for nt in notas:
            _sumar(out, banco.tocar(nt.nota, nt.vel), nt.t)
        return out

    def _fluidsynth(self, programa: int, notas: list[Nota], dur: float) -> np.ndarray:
        with tempfile.TemporaryDirectory(prefix="nudos-fs-") as tmp:
            mid, wav = Path(tmp) / "pista.mid", Path(tmp) / "pista.wav"
            mid.write_bytes(midi(notas, programa))
            cmd = [str(self.fluidsynth), "-n", "-i", "-q", "-T", "wav", "-O", "float", "-r", str(SR),
                   "-R", "0", "-C", "0", "-g", "0.6", "-o", "synth.cpu-cores=1", "-o", "synth.polyphony=512",
                   "-F", str(wav), str(self.sf2), str(mid)]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not wav.exists():
                raise MusicaError(f"FluidSynth falló: {r.stderr[-800:]}")
            x, sr = _leer_wav(wav)
        x = _a_sr(_a_estereo(x), sr)
        n = int(np.ceil(dur * SR)) + 8 * SR
        return np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]


def midi(notas: list[Nota], programa: int, canal: int = 0, ppq: int = 960) -> bytes:
    """Un archivo MIDI de formato 0 con las notas, a BPM fijo."""
    def vlq(n: int) -> bytes:
        out = [n & 0x7F]
        n >>= 7
        while n:
            out.append((n & 0x7F) | 0x80)
            n >>= 7
        return bytes(reversed(out))
    por_s = ppq / PULSO
    eventos = []
    # Una nota que se repite antes de que la anterior se apague cortaría la nueva al apagarse:
    # la anterior termina un tic antes.
    siguiente: dict[int, int] = {}
    tramos = []
    for nt in sorted(notas, key=lambda n: n.t, reverse=True):
        a = int(round(nt.t * por_s))
        b = max(a + 1, int(round((nt.t + nt.dur) * por_s)))
        if nt.nota in siguiente:
            b = max(a + 1, min(b, siguiente[nt.nota] - 1))
        siguiente[nt.nota] = a
        tramos.append((a, b, nt))
    for a, b, nt in tramos:
        eventos.append((a, 1, bytes([0x90 | canal, nt.nota, nt.vel])))
        eventos.append((b, 0, bytes([0x80 | canal, nt.nota, 0])))
    eventos.sort(key=lambda e: (e[0], e[1]))
    pista = bytearray()
    pista += vlq(0) + b"\xff\x51\x03" + int(round(PULSO * 1e6)).to_bytes(3, "big")
    pista += vlq(0) + bytes([0xC0 | canal, programa])
    pista += vlq(0) + bytes([0xB0 | canal, 7, 110])           # volumen
    t = 0
    for tick, _, datos in eventos:
        pista += vlq(tick - t) + datos
        t = tick
    pista += vlq(0) + b"\xff\x2f\x00"
    return (b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big")
            + ppq.to_bytes(2, "big") + b"MTrk" + len(pista).to_bytes(4, "big") + bytes(pista))


# --------------------------------------------------------------------------
# La mezcla de la música
# --------------------------------------------------------------------------
# La sonoridad de cada instrumento donde suena, en LU respecto de la guitarra; su lugar en el
# estéreo (−1 izquierda, 1 derecha), y cuánto va a la sala. La ponderación K oye poco los graves,
# así que el bajo y el bombo van más abajo de lo que se sienten.
MEZCLA = {"guitarra": (0.0, -0.18, 0.22), "bajo": (-6.0, 0.0, 0.08), "kalimba": (-1.0, 0.28, 0.30),
          "glock": (-9.0, 0.35, 0.30), "shaker": (-16.0, 0.45, 0.18), "palmas": (-11.0, -0.25, 0.25),
          "bombo": (-12.0, 0.0, 0.10)}
NIVEL = -18.0      # LUFS de la música sola (la mezcla final la baja bajo la voz)


def sala(sr: int = SR, rt60: float = 1.1, predelay: float = 0.012, semilla: int = 5) -> np.ndarray:
    """Una respuesta de sala sintetizada, estéreo: unas pocas reflexiones tempranas y una cola de
    ruido que decae más rápido en los agudos (bandas con su propio RT60)."""
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(semilla)
    n = int((predelay + rt60 * 1.2) * sr)
    t = np.arange(n) / sr
    ir = np.zeros((n, 2))
    bandas = [(None, 300, 1.15), (300, 1200, 1.0), (1200, 4000, 0.8), (4000, None, 0.55)]
    for lo, hi, f in bandas:
        ruido = rng.standard_normal((n, 2))
        if lo and hi:
            sos = butter(2, [lo, hi], btype="band", fs=sr, output="sos")
        elif lo:
            sos = butter(2, lo, btype="high", fs=sr, output="sos")
        else:
            sos = butter(2, hi, btype="low", fs=sr, output="sos")
        cola = sosfilt(sos, ruido, axis=0) * np.exp(-6.91 * np.maximum(t - predelay, 0) / (rt60 * f))[:, None]
        cola[t < predelay] = 0
        ir += cola
    for k, (dt, g) in enumerate([(0.007, 0.5), (0.011, 0.4), (0.017, 0.33), (0.023, 0.25)]):
        i = int(dt * sr)
        ir[i, k % 2] += g
        ir[i + int(0.0013 * sr), (k + 1) % 2] += g * 0.7
    return ir / np.sqrt((ir ** 2).sum(axis=0)).max()


def _panear(x: np.ndarray, pan: float) -> np.ndarray:
    a = (pan + 1) * np.pi / 4
    m = x.mean(axis=1) if x.ndim > 1 else x
    lado = (x[:, 0] - x[:, 1]) / 2 if x.ndim > 1 else 0
    return np.column_stack([m * np.cos(a) * np.sqrt(2) + lado * 0.6, m * np.sin(a) * np.sqrt(2) - lado * 0.6])


def mezclar(pistas: dict[str, np.ndarray], dur: float, nivel: float = NIVEL) -> np.ndarray:
    from scipy.signal import butter, fftconvolve, sosfilt

    from . import sonoridad as so
    n = int(np.ceil(dur * SR))
    seco = np.zeros((n, 2))
    envio = np.zeros((n, 2))
    for inst, x in pistas.items():
        if not np.abs(x).max() > 0:
            continue
        rel, pan, rev = MEZCLA[inst]
        y = _panear(np.asarray(x)[:n], pan)
        if inst == "bombo":
            y = sosfilt(butter(2, 1800, btype="low", fs=SR, output="sos"), y, axis=0)
        # La sonoridad donde suena (las compuertas de la norma dejan fuera los silencios).
        actual = so.lufs(y, SR)
        if np.isfinite(actual):
            y = y * 10 ** ((NIVEL + rel - actual) / 20)
        y = np.pad(y, ((0, n - len(y)), (0, 0)))
        seco += y
        envio += y * rev
    ir = sala()
    mojado = np.column_stack([fftconvolve(envio[:, c], ir[:, c])[:n] for c in range(2)])
    x = seco + mojado
    x = sosfilt(butter(2, 35, btype="high", fs=SR, output="sos"), x, axis=0)
    # El final se apaga en 1,5 s.
    f = min(n, int(1.5 * SR))
    x[n - f:] *= np.linspace(1, 0, f)[:, None] ** 2
    x = so.limitar_pico(so.a_lufs(x, SR, nivel), SR, -1.0)
    return x.astype(np.float32)


# --------------------------------------------------------------------------
# La pista de un video
# --------------------------------------------------------------------------
def carpeta_cache() -> Path:
    base = os.environ.get("NUDOS_MUSICA") or str(Path(os.environ.get("LOCALAPPDATA", Path.home()))
                                                  / "nudos" / "musica")
    return Path(base)


def _huella(*partes) -> str:
    h = hashlib.sha256()
    for p in partes:
        h.update(json.dumps(p, sort_keys=True, default=str).encode())
    return h.hexdigest()[:20]


def musica(capitulos: list[Capitulo], golpe: float | None = None, semilla: int = SEMILLA,
           candidata: str = "codigo", instrumentos=None, aviso=print) -> Musica:
    """La música de un video: sus capítulos (en segundos desde el inicio del video) y el golpe
    del nudo apretado. Da la mezcla estéreo a SR, del largo del último capítulo."""
    caps = en_pulso(capitulos)
    pulsos, compases = rejilla(caps)
    dur = caps[-1].fin
    # El golpe no se corre al pulso: el acorde final suena con el golpe que se ve.
    if candidata == "ace-step":
        return armar_ace(caps, golpe, semilla, aviso=aviso)
    inst = instrumentos or Muestreado()
    h = _huella(VERSION, [asdict(c) for c in caps], golpe, semilla, inst.huella(), _codigo())
    ruta = carpeta_cache() / f"codigo-{h}.wav"
    if not ruta.exists():
        notas = componer(caps, golpe, semilla)
        pistas = {i: inst.pista(i, notas[i], dur) for i in INSTRUMENTOS if notas[i]}
        x = mezclar(pistas, dur)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        _escribir(ruta, x)
    x, _ = _leer_wav(ruta)
    return Musica(x.astype(np.float32), caps, pulsos, compases, "codigo", h)


def _codigo() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]


def _escribir(ruta: Path, x) -> None:
    from scipy.io import wavfile
    tmp = ruta.with_suffix(".tmp.wav")
    wavfile.write(tmp, SR, np.asarray(x, np.float32))
    tmp.replace(ruta)


# --------------------------------------------------------------------------
# La candidata B: ACE-Step 1.5
# --------------------------------------------------------------------------
ESTILO = ("warm acoustic folk, campfire song, fingerpicked steel-string acoustic guitar, soft acoustic bass, "
          "light shaker, cheerful and calm, gentle, major key, instrumental, no vocals")
PIEZAS_ACE = {
    # Una pieza por arreglo: lo que se le pide a ACE-Step.
    "abre": ESTILO + ", opens with a short bright kalimba melody, intro",
    "pasos": ESTILO + ", steady and sparse, unobtrusive background for a spoken tutorial, no lead melody",
    "ralo": "sparse " + ESTILO + ", only gentle guitar arpeggios and soft bass, thoughtful, no percussion",
    "lleno": ESTILO + ", fuller arrangement, hand claps on two and four, soft kick drum, glockenspiel countermelody",
    "cierra": ESTILO + ", kalimba melody returns, ending with a final ringing G major chord, outro",
}
PIEZA_DE = {"apertura": "abre", "materiales": "pasos", "pasos": "pasos", "verificacion": "pasos",
            "errores": "ralo", "seguridad": "ralo", "aplicacion": "lleno", "cierre": "cierra"}
MEDIDA_ACE = "2"   # cómo mide sonido/ace_step.py los pulsos y compases: si cambia, vuelve a medir
# La sonoridad de cada capítulo respecto de NIVEL: cada pieza sale a su nivel, y así los errores
# quedan más bajos y el cierre más arriba, como en la candidata compuesta.
NIVEL_ACE = {"apertura": 0.0, "materiales": -1.0, "pasos": -1.0, "verificacion": -1.0, "errores": -4.5,
             "seguridad": -4.5, "aplicacion": 0.5, "cierre": 1.5}


def piezas_ace(caps: list[Capitulo], semilla: int, aviso=print) -> dict[str, dict]:
    """Las piezas que hacen falta, generadas por ACE-Step (desde el caché si ya están), con sus
    pulsos y compases medidos por librosa."""
    from . import ia
    largo: dict[str, float] = {}
    for c in caps:
        p = PIEZA_DE[c.nombre]
        largo[p] = largo.get(p, 0.0) + (c.fin - c.inicio)
    cache = carpeta_cache() / "ace-step"
    tareas, out = [], {}
    for p, d in largo.items():
        # Lo que usan sus capítulos, más 10 s de margen (la entrada y el final de la pieza), en
        # decenas de segundos y entre 30 s y 4 min.
        dur = float(min(240, max(30, np.ceil((d + 10) / 10) * 10)))
        pedido = {"caption": PIEZAS_ACE[p], "bpm": BPM, "keyscale": "G major", "timesignature": "4",
                  "duration": dur, "seed": semilla + sorted(PIEZAS_ACE).index(p)}
        h = _huella("ace-step-1.5-turbo", pedido)
        ruta = cache / f"{p}-{h}.wav"
        out[p] = {"ruta": ruta, "json": ruta.with_suffix(".json"), **pedido}
        # Sin su JSON, se genera; si la pieza ya está y falta el JSON (o cambió cómo se mide),
        # el script solo la vuelve a medir.
        info = json.loads(ruta.with_suffix(".json").read_text(encoding="utf-8")) if ruta.with_suffix(".json").exists() else {}
        if info.get("medida") != MEDIDA_ACE:
            tareas.append({**pedido, "salida": str(ruta), "medida": MEDIDA_ACE})
    if tareas:
        aviso(f"  ACE-Step: {len(tareas)} piezas por generar")
        repo = ia.carpeta() / "ace-step" / "ACE-Step-1.5"
        ia.correr("ace-step", "ace_step.py", {"repo": str(repo), "tareas": tareas}, aviso=aviso, cwd=repo)
    for p, info in out.items():
        info.update(json.loads(info["json"].read_text(encoding="utf-8")))
    return out


def armar_ace(caps: list[Capitulo], golpe: float | None, semilla: int, aviso=print) -> Musica:
    """Corta las piezas de ACE-Step a compás y las pone en sus capítulos: cada capítulo toma su
    pieza desde un compás (la apertura desde el principio, el cierre hasta el final), y entre
    capítulos hay un fundido de 60 ms en el pulso."""
    from . import sonoridad as so
    piezas = piezas_ace(caps, semilla, aviso)
    dur = caps[-1].fin
    n = int(np.ceil(dur * SR))
    x = np.zeros((n, 2))
    usado: dict[str, float] = {}
    fundido = int(0.06 * SR)
    for i, c in enumerate(caps):
        p = PIEZA_DE[c.nombre]
        info = piezas[p]
        audio, sr = _leer_wav(info["ruta"])
        audio = _a_sr(_a_estereo(audio), sr)
        compases = np.array(info.get("compases") or [0.0])
        largo = c.fin - c.inicio
        if c.nombre == "cierre":
            # El final de la pieza, con su último compás fuerte en el golpe si lo hay.
            fin_pieza = len(audio) / SR
            ancla = compases[compases <= fin_pieza - 2.0]
            ancla = ancla[-1] if len(ancla) else max(0.0, fin_pieza - largo)
            desde = ancla - ((golpe - c.inicio) if golpe is not None else max(0.0, largo - (fin_pieza - ancla)))
        elif c.nombre == "apertura":
            desde = float(compases[0])
        else:
            prev = usado.get(p, float(compases[min(1, len(compases) - 1)]))
            sig = compases[compases >= prev - 1e-6]
            desde = float(sig[0]) if len(sig) else prev
        desde = max(0.0, desde)
        a, b = int(round(desde * SR)), int(round((desde + largo) * SR))
        trozo = audio[a:b]
        trozo = np.pad(trozo, ((0, (b - a) - len(trozo)), (0, 0)))
        trozo = so.a_lufs(trozo, SR, NIVEL + NIVEL_ACE[c.nombre]) if so.lufs(trozo, SR) > -60 else trozo
        if i > 0:
            trozo[:fundido] *= np.linspace(0, 1, fundido)[:, None]
        if i < len(caps) - 1:
            trozo[-fundido:] *= np.linspace(1, 0, fundido)[:, None]
        k = int(round(c.inicio * SR))
        x[k:k + len(trozo)] += trozo[:n - k]
        usado[p] = desde + largo
    f = min(n, int(1.5 * SR))
    x[n - f:] *= np.linspace(1, 0, f)[:, None] ** 2
    x = so.limitar_pico(so.a_lufs(x, SR, NIVEL), SR, -1.0).astype(np.float32)
    pulsos, compases = rejilla(caps)
    return Musica(x, caps, pulsos, compases, "ace-step",
                  _huella({p: str(v["ruta"].name) for p, v in piezas.items()}, [asdict(c) for c in caps]))
