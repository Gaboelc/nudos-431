"""La música de los videos (T23b): folk acústico de campamento, propio, compuesto en código.

Gabriel eligió el 26 nov la candidata compuesta en código, sobre la de ACE-Step 1.5 (que quedó en
el commit b4583a0). Pidió además más canciones parecidas, distintas entre sí: hay cinco
(CANCIONES), y cada nudo tiene la suya en `config/musica.yaml`.

`musica(capitulos, golpe, slug=...)` da la pista de un video a partir de sus capítulos (en s) y
del instante del golpe del nudo apretado. Cada capítulo empieza en un pulso de su canción
(`en_pulso`), con su propio primer compás; si no dura compases enteros, el último es más corto.

**Cada canción** (`Cancion`) tiene su tono, su pulso, su compás (4/4 o 3/4), su guitarra (de
acero o de nailon) y cómo la toca, su bajo, su percusión, el instrumento que pregunta en la
verificación y el que acompaña en la aplicación, y la progresión de acordes de cada capítulo, en
grados («I», «vi», «V/3» con la tercera en el bajo, «bVII»). Las voces de la guitarra salen de
cada acorde, con la menor distancia al anterior.

**El motivo de la serie** es el mismo en todas, transportado a su tono: sube por el acorde
(5, 1, 3, 2-1) y contesta; en la apertura queda abierto (en la quinta) y en el cierre llega al
golpe, donde suena el acorde final. Va en MOTIVO (Gabriel lo elige: la kalimba sonaba «tuc tuc
tuc»).

**Los arreglos** (`arreglo`): constante y despejado bajo la voz en los pasos; más ralo en los
errores; más lleno en la aplicación.

**El sonido:** las notas se humanizan con una semilla fija (la misma semilla da la misma música).
Los instrumentos melódicos los toca FluidSynth con GeneralUser GS («gm:<programa>» de General
MIDI); el glockenspiel y la percusión, un muestreador propio (`Banco`) con muestras del VCSL (CC0).
Sin los bancos, `Sintetico` toca todo con síntesis simple: así corren las pruebas.

Todo se guarda con su huella fuera de git (`NUDOS_MUSICA`; por omisión,
`%LOCALAPPDATA%\\nudos\\musica`).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path

import numpy as np

from . import RAIZ

SR = 48000
SEMILLA = 431
VERSION = "2"               # súbela si cambia la composición o el sonido
REPARTO = RAIZ / "config" / "musica.yaml"

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


@dataclass(frozen=True)
class Cancion:
    clave: str
    nombre: str
    tonica: int                  # la clase de altura del tono (0 do, 2 re, 5 fa, 7 sol, 9 la)
    bpm: int
    compas: int                  # pulsos por compás: 4 o 3
    guitarra: int                # programa General MIDI: 25 acero, 24 nailon
    patron: str                  # cómo toca la guitarra en los pasos (ver `_guitarra`)
    bajo: str                    # cómo toca el bajo en los pasos (ver `_bajo`)
    percusion: dict              # nivel («suave», «lleno») → las voces de percusión que suenan
    pregunta: str                # el instrumento de la pregunta de la verificación
    contracanto: tuple           # (instrumento, cómo toca) en la aplicación
    progresiones: dict           # capítulo → grados, uno por compás (se repiten)
    descripcion: str = ""

    @property
    def pulso(self) -> float:
        return 60.0 / self.bpm


@dataclass
class Musica:
    mezcla: np.ndarray                  # (n, 2) float32 a SR
    capitulos: list[Capitulo]           # ya en el pulso
    pulsos: np.ndarray                  # s
    compases: np.ndarray                # s: el primer pulso de cada compás
    cancion: str
    huella: str = ""
    pistas: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# Las canciones
# --------------------------------------------------------------------------
_COMUNES = {"materiales": ("I", "IV", "I", "V"), "seguridad": ("IV", "I", "V", "vi"), "cierre": ("IV", "V", "I", "I")}

CANCIONES = {
    "fogata": Cancion(
        "fogata", "Fogata", tonica=7, bpm=100, compas=4, guitarra=25, patron="travis", bajo="raiz_quinta",
        percusion={"suave": ("shaker", "bombo"), "lleno": ("shaker", "bombo", "palmas")},
        pregunta="vcsl:glock", contracanto=("vcsl:glock", "blancas"),
        progresiones={**_COMUNES, "apertura": ("I", "V/3", "vi", "IV"),
                      "pasos": ("I", "IV", "vi", "V", "I", "IV", "V", "I", "IV", "I", "ii", "V", "IV", "I", "V", "I"),
                      "verificacion": ("vi", "IV", "I", "V"), "errores": ("ii", "vi", "IV", "V"),
                      "aplicacion": ("I", "V", "vi", "IV"), "cierre": ("I", "IV", "V", "I")},
        descripcion="Sol mayor, 100 pulsos por minuto: guitarra de acero punteada, shaker y palmas. "
                    "La que eligió Gabriel."),
    "sendero": Cancion(
        "sendero", "Sendero", tonica=2, bpm=104, compas=4, guitarra=25, patron="rodado", bajo="sincopado",
        percusion={"suave": ("cajon",), "lleno": ("cajon", "shaker_grande")},
        pregunta="vcsl:glock", contracanto=("gm:105", "rodado"),
        progresiones={**_COMUNES, "apertura": ("I", "IV", "I", "V"), "materiales": ("I", "V", "IV", "I"),
                      "pasos": ("I", "V", "vi", "IV", "I", "V", "IV", "I", "vi", "IV", "I", "V", "IV", "V", "I", "I"),
                      "verificacion": ("IV", "I", "V", "vi"), "errores": ("vi", "iii", "IV", "V"),
                      "aplicacion": ("I", "bVII", "IV", "I"), "seguridad": ("IV", "I", "V", "V")},
        descripcion="Re mayor, 104: arpegio rodado de acero, cajón y banjo en la práctica."),
    "rocio": Cancion(
        "rocio", "Rocío", tonica=0, bpm=92, compas=3, guitarra=24, patron="vals", bajo="vals",
        percusion={"suave": ("shaker",), "lleno": ("cajon", "shaker")},
        pregunta="gm:11", contracanto=("gm:12", "arpegio"),
        progresiones={**_COMUNES, "apertura": ("I", "vi", "IV", "V"), "materiales": ("I", "IV", "V", "I"),
                      "pasos": ("I", "vi", "IV", "V", "I", "IV", "V", "I", "vi", "IV", "I", "V", "ii", "V", "I", "I"),
                      "verificacion": ("vi", "IV", "I", "V"), "errores": ("ii", "vi", "IV", "V"),
                      "aplicacion": ("I", "V", "vi", "IV", "I", "IV", "V", "I"), "seguridad": ("IV", "I", "V", "vi")},
        descripcion="Do mayor, 92, en tres por cuatro: vals de guitarra de nailon, vibráfono y marimba."),
    "lumbre": Cancion(
        "lumbre", "Lumbre", tonica=9, bpm=96, compas=4, guitarra=25, patron="rasgueo", bajo="raiz_quinta",
        percusion={"suave": ("shaker_grande",), "lleno": ("shaker_grande", "bombo", "palmas")},
        pregunta="vcsl:glock", contracanto=("gm:11", "blancas"),
        progresiones={**_COMUNES, "apertura": ("I", "V", "vi", "IV"),
                      "pasos": ("I", "IV", "vi", "V", "I", "IV", "V", "V", "vi", "IV", "I", "V", "IV", "V", "I", "I"),
                      "verificacion": ("IV", "V", "iii", "vi"), "errores": ("vi", "IV", "vi", "V"),
                      "aplicacion": ("I", "V", "IV", "V"), "seguridad": ("IV", "I", "ii", "V")},
        descripcion="La mayor, 96: guitarra de acero rasgueada suave, shaker grande y vibráfono."),
    "amanecer": Cancion(
        "amanecer", "Amanecer", tonica=5, bpm=94, compas=4, guitarra=24, patron="lento", bajo="raiz_quinta",
        percusion={"suave": ("cajon",), "lleno": ("cajon", "shaker")},
        pregunta="gm:12", contracanto=("vcsl:glock", "blancas"),
        progresiones={**_COMUNES, "apertura": ("I", "iii", "IV", "V"),
                      "pasos": ("I", "V/3", "vi", "iii", "IV", "I", "ii", "V", "I", "V/3", "vi", "iii", "IV", "V", "I", "I"),
                      "verificacion": ("ii", "V", "I", "vi"), "errores": ("vi", "iii", "IV", "V"),
                      "aplicacion": ("IV", "V", "iii", "vi", "ii", "V", "I", "I")},
        descripcion="Fa mayor, 94: guitarra de nailon a medio tiempo, cajón muy suave, marimba y glockenspiel."),
}

# El instrumento del motivo de la serie (el mismo en todas las canciones). La kalimba del VCSL
# (una mbira) sonaba «tuc tuc tuc» (Gabriel, 26 nov); las opciones se escuchan en prueba-musica.
MOTIVO = "vcsl:glock"
MOTIVOS_PRUEBA = {"glockenspiel": "vcsl:glock", "celesta": "gm:8", "caja de música": "gm:10", "vibráfono": "gm:11"}

# El motivo en corcheas: (índice de corchea, semitonos desde la tónica, duración en corcheas), en
# dos compases. «abre» termina en la quinta (queda abierto); «cierra», en la tónica.
FRASES = {
    4: {"abre": [(0, -5, 2), (2, 0, 2), (4, 4, 2), (6, 2, 1), (7, 0, 1), (8, -3, 2), (10, -5, 6)],
        "cierra": [(0, -5, 2), (2, 0, 2), (4, 4, 2), (6, 2, 1), (7, 0, 1), (8, 2, 2), (10, 0, 6)]},
    3: {"abre": [(0, -5, 2), (2, 0, 2), (4, 4, 2), (6, 2, 1), (7, 0, 1), (8, -3, 2), (10, -5, 2)],
        "cierra": [(0, -5, 2), (2, 0, 2), (4, 4, 2), (6, 2, 1), (7, 0, 1), (8, 2, 2), (10, 0, 4)]},
}

# Dónde suena bien cada instrumento (notas MIDI).
RANGO = {"vcsl:glock": (79, 100), "vcsl:kalimba": (62, 90), "gm:8": (72, 96), "gm:10": (72, 96),
         "gm:11": (60, 86), "gm:12": (55, 84), "gm:105": (55, 81)}


# --------------------------------------------------------------------------
# La armonía
# --------------------------------------------------------------------------
ESCALA = (0, 2, 4, 5, 7, 9, 11)
GRADOS = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}


def acorde(cifra: str, tonica: int) -> tuple[int, bool, int]:
    """(raíz, menor, bajo) de un grado, en clases de altura. «V/3»: con la tercera en el bajo;
    «bVII»: medio tono abajo del de la escala; en minúsculas, menor."""
    bemol = cifra.startswith("b")
    c = cifra[1:] if bemol else cifra
    c, _, inversion = c.partition("/")
    if c.upper() not in GRADOS:
        raise MusicaError(f"«{cifra}» no es un grado")
    menor = c.islower()
    raiz = (tonica + ESCALA[GRADOS[c.upper()]] - int(bemol)) % 12
    tercera = (raiz + (3 if menor else 4)) % 12
    return raiz, menor, (tercera if inversion == "3" else raiz)


def _en(pc: int, lo: int, hi: int) -> list[int]:
    return [n for n in range(lo, hi + 1) if n % 12 == pc % 12]


def voces(raiz: int, menor: bool, bajo_pc: int, previas: tuple | None = None) -> tuple[int, int, tuple]:
    """Las voces de la guitarra: el bajo (de mi2 a re#3), el bajo alterno (la quinta o, con otro
    bajo, la raíz) y tres agudos del acorde entre sol3 y si4, los más cercanos a los anteriores."""
    bajo = _en(bajo_pc, 40, 51)[0]
    quinta = (raiz + 7) % 12
    alterno = _en(quinta if bajo_pc == raiz else raiz, bajo + 3, bajo + 14)[0]
    tonos = sorted(n for pc in (raiz, raiz + (3 if menor else 4), quinta) for n in _en(pc, 55, 71))
    triples = [tuple(tonos[i:i + 3]) for i in range(len(tonos) - 2)]
    if previas:
        agudos = min(triples, key=lambda t: sum(abs(a - b) for a, b in zip(t, previas)))
    else:
        agudos = min(triples, key=lambda t: abs(t[2] - 66))
    return bajo, alterno, agudos


def raiz_bajo(pc: int) -> int:
    """La nota del bajo (de mi1 a re#2)."""
    return _en(pc, 28, 39)[0]


def tonos_en(raiz: int, menor: bool, lo: int, hi: int) -> list[int]:
    return sorted(n for pc in (raiz, raiz + (3 if menor else 4), raiz + 7) for n in _en(pc, lo, hi))


def al_rango(notas: list[int], instrumento: str) -> list[int]:
    """Las notas, movidas de octava en octava hasta caber en el rango del instrumento."""
    lo, hi = RANGO.get(instrumento, (48, 96))
    k = 0
    while max(notas) + k > hi and min(notas) + k - 12 >= lo - 5:
        k -= 12
    while min(notas) + k < lo and max(notas) + k + 12 <= hi + 5:
        k += 12
    return [n + k for n in notas]


# --------------------------------------------------------------------------
# El pulso
# --------------------------------------------------------------------------
def al_pulso(t: float, origen: float = 0.0, pulso: float = 0.6) -> float:
    """El pulso más cercano a t."""
    return origen + round((t - origen) / pulso) * pulso


def en_pulso(capitulos: list[Capitulo], pulso: float = 0.6) -> list[Capitulo]:
    """Los capítulos con sus cortes en el pulso más cercano (desde el inicio del primero), cada
    uno de dos pulsos por lo menos y uno detrás del otro."""
    if not capitulos:
        return []
    origen = capitulos[0].inicio
    out, t = [], origen
    for c in capitulos:
        if c.nombre not in CAPITULOS:
            raise MusicaError(f"«{c.nombre}» no es un capítulo; puede ser {', '.join(CAPITULOS)}")
        fin = max(al_pulso(c.fin, origen, pulso), t + 2 * pulso)
        out.append(Capitulo(c.nombre, round(t, 6), round(fin, 6)))
        t = fin
    return out


def rejilla(capitulos: list[Capitulo], pulso: float = 0.6, compas: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Los pulsos y los comienzos de compás: cada capítulo empieza un compás nuevo."""
    pulsos, compases = [], []
    for c in capitulos:
        n = int(round((c.fin - c.inicio) / pulso))
        for k in range(n):
            t = c.inicio + k * pulso
            pulsos.append(t)
            if k % compas == 0:
                compases.append(t)
    return np.round(np.array(pulsos), 6), np.round(np.array(compases), 6)


# --------------------------------------------------------------------------
# La composición
# --------------------------------------------------------------------------
VOCES = ("guitarra", "bajo", "motivo", "pregunta", "contracanto", "shaker", "shaker_grande", "palmas", "bombo",
         "cajon")
TEMBLOR = {"guitarra": 0.007, "bajo": 0.006, "motivo": 0.004, "pregunta": 0.004, "contracanto": 0.006,
           "shaker": 0.004, "shaker_grande": 0.005, "palmas": 0.006, "bombo": 0.003, "cajon": 0.004}  # s, al azar


def arreglo(can: Cancion, capitulo: str) -> dict:
    """Qué toca cada instrumento en un capítulo."""
    lleno = {"raiz_quinta": "caminante", "sincopado": "caminante", "vals": "vals_lleno"}.get(can.bajo, can.bajo)
    return {
        "apertura": dict(guitarra="arpegio", bajo="larga", perc="suave", desde=1, motivo="abre"),
        "materiales": dict(guitarra="arpegio", bajo="larga", perc="suave"),
        "pasos": dict(guitarra=can.patron, bajo=can.bajo, perc="suave"),
        "verificacion": dict(guitarra=can.patron, bajo=can.bajo, perc="suave", pregunta=True),
        "errores": dict(guitarra="lenta", bajo="larga", perc=None),
        "aplicacion": dict(guitarra=can.patron, bajo=lleno, perc="lleno", contracanto=True),
        "seguridad": dict(guitarra="lenta", bajo="larga", perc=None),
        "cierre": dict(guitarra=can.patron, bajo=can.bajo, perc="suave", motivo="cierra"),
    }[capitulo]


def instrumentos_de(can: Cancion, motivo: str = MOTIVO) -> dict[str, str]:
    """El instrumento de cada voz: «gm:<programa>» (FluidSynth) o «vcsl:<banco>» (muestras)."""
    return {"guitarra": f"gm:{can.guitarra}", "bajo": "gm:32", "motivo": motivo, "pregunta": can.pregunta,
            "contracanto": can.contracanto[0], "shaker": "vcsl:shaker", "shaker_grande": "vcsl:shaker_grande",
            "palmas": "vcsl:palmas", "bombo": "vcsl:bombo", "cajon": "vcsl:cajon"}


def _guitarra(pon, patron: str, t0: float, largo: int, C: int, P: float, bajo: int, alterno: int,
              agudos: tuple, k: int) -> None:
    a0, a1, a2 = agudos
    co = P / 2
    if patron in ("travis", "rodado", "rasgueo", "lento") and C != 4:
        patron = "vals"
    if patron == "travis":
        figura = [("b", a2), ("a", a0), ("t", None), ("a", a1), ("b", None), ("a", a0), ("t", None),
                  ("a", a2 if k % 2 else a1)]
        for e in range(2 * largo):
            tipo, alto = figura[e]
            t = t0 + e * co
            if tipo == "b":
                pon("guitarra", t, 2 * P, bajo, 74 if e == 0 else 66)
                if alto is not None:
                    pon("guitarra", t + 0.004, 1.5 * P, alto, 64)
            elif tipo == "t":
                pon("guitarra", t, 2 * P, alterno, 62)
            else:
                pon("guitarra", t, 1.5 * P, alto, 56 + 4 * (e == 3))
    elif patron == "rodado":
        figura = [(bajo, 70), (a0, 54), (a1, 56), (a2, 60), (alterno, 64), (a2, 56), (a1, 54), (a0, 52)]
        for e in range(2 * largo):
            nota, v = figura[e]
            pon("guitarra", t0 + e * co, 2 * P if e in (0, 4) else 1.4 * P, nota, v)
    elif patron == "rasgueo":
        golpes = [(0, "D", 1.0), (2, "D", 0.8), (3, "U", 0.6), (5, "U", 0.65), (6, "D", 0.8), (7, "U", 0.6)]
        golpes = [g for g in golpes if g[0] < 2 * largo]
        for i, (e, sentido, f) in enumerate(golpes):
            t = t0 + e * co
            sig = t0 + (golpes[i + 1][0] if i + 1 < len(golpes) else 2 * largo) * co
            cuerdas = [bajo, alterno, a0, a1, a2] if sentido == "D" else [a2, a1, a0]
            for j, nota in enumerate(cuerdas):
                pon("guitarra", t + j * (0.010 if sentido == "D" else 0.008), sig - t + 0.05, nota,
                    (52 + 4 * (j == 0 and sentido == "D")) * f)
    elif patron == "lento":
        pon("guitarra", t0, 2 * P, bajo, 68)
        if largo >= 2:
            pon("guitarra", t0 + P, 1.6 * P, a1, 52)
            pon("guitarra", t0 + P + 0.004, 1.6 * P, a2, 50)
        if largo >= 3:
            pon("guitarra", t0 + 2 * P, 2 * P, alterno, 60)
        if largo >= 4:
            pon("guitarra", t0 + 3 * P, 1.2 * P, a1, 50)
            pon("guitarra", t0 + 3 * P + 0.004, 1.2 * P, a2, 48)
            pon("guitarra", t0 + 3.5 * P, 1.0 * P, a0, 44)
    elif patron == "vals":
        figura = [(bajo, 68), (a0, 50), (a1, 54), (a2, 58), (a1, 54), (a0, 50)]
        for e in range(min(2 * largo, 2 * C)):
            nota, v = figura[e % 6]
            pon("guitarra", t0 + e * co, C * P if e == 0 else 1.2 * P, nota, v)
    elif patron == "arpegio":
        for e, nota in enumerate([bajo, a0, a1, a2][:largo]):
            pon("guitarra", t0 + e * P, (C - e) * P, nota, 50 + 3 * e)
    elif patron == "lenta":
        pon("guitarra", t0, C * P, bajo, 56)
        for e, nota in enumerate([a0, a1, a2][:max(0, largo - 1)], start=1):
            pon("guitarra", t0 + e * P, (C - e) * P + 0.4, nota, 46 + 2 * e)
    else:
        raise MusicaError(f"la guitarra no sabe tocar «{patron}»")


def _bajo(pon, patron: str, t0: float, largo: int, C: int, P: float, raiz: int, sig: int, k: int,
          final: bool) -> None:
    if C == 3 and patron in ("raiz_quinta", "sincopado"):
        patron = "vals"
    if C == 3 and patron == "caminante":
        patron = "vals_lleno"
    if patron == "larga":
        pon("bajo", t0, largo * P * 0.95, raiz, 58)
    elif patron == "raiz_quinta":
        pon("bajo", t0, 1.8 * P, raiz, 66)
        if largo >= 3:
            pon("bajo", t0 + 2 * P, 1.6 * P if largo == 4 else 0.9 * P, raiz + 7, 58)
        if largo == 4 and k % 2 == 1 and not final:
            pon("bajo", t0 + 3.5 * P, 0.45 * P, sig - 1 if sig > raiz else sig + 2, 52)
    elif patron == "sincopado":
        for off, iv, v, d in ((0, 0, 68, 1.4), (1.5, 0, 54, 0.45), (2, 7, 60, 0.9)):
            if off < largo:
                pon("bajo", t0 + off * P, d * P, raiz + iv, v)
        if largo == 4 and k % 2 == 1 and not final:
            pon("bajo", t0 + 3.5 * P, 0.45 * P, sig - 1 if sig > raiz else sig + 2, 50)
    elif patron == "caminante":
        for off, iv, v in ((0, 0, 70), (1.5, 0, 56), (2, 7, 64), (3, 12, 58)):
            if off < largo:
                pon("bajo", t0 + off * P, 0.45 * P if off % 1 else 0.9 * P, raiz + iv, v)
    elif patron == "vals":
        pon("bajo", t0, min(largo, C) * P * 0.93, raiz + (7 if k % 2 else 0), 64 if k % 2 == 0 else 58)
    elif patron == "vals_lleno":
        for off, iv, v in ((0, 0, 68), (1, 7, 56), (2, 12, 54)):
            if off < largo:
                pon("bajo", t0 + off * P, 0.9 * P, raiz + iv, v)
    else:
        raise MusicaError(f"el bajo no sabe tocar «{patron}»")


def _percusion(pon, voz: str, nivel: str, t0: float, largo: int, C: int, P: float, k: int, redoble: bool) -> None:
    co = P / 2
    fuerte = nivel == "lleno"
    if voz == "shaker":
        base = 50 if fuerte else 34
        for e in range(2 * largo):
            pon("shaker", t0 + e * co, co, 1 if e % 2 else 0, base + (10 if e % 2 else 0))
        if redoble:
            pon("shaker", t0 + (largo - 1) * P, P, 2, base + 8)
    elif voz == "shaker_grande":
        base = 52 if fuerte else 36
        for e in range(2 * largo):
            pon("shaker_grande", t0 + e * co, co, 1 if e % 2 else 0, base + (8 if e % 2 == 0 else 0))
    elif voz == "cajon":
        base = 58 if fuerte else 32
        if C == 4:
            golpes = [(0, 0, 8), (1, 2, 4), (2, 0, 0), (3, 2, 4), (3.5, 1, -14)]
        else:
            golpes = [(0, 0, 8), (1, 2, -4), (2, 2, -6)]
        for off, tipo, dv in golpes:
            if off < largo:
                pon("cajon", t0 + off * P, P, tipo, base + dv)
    elif voz == "bombo":
        v = 62 if fuerte else 40
        pon("bombo", t0, P, 0, v)
        if C == 4 and largo >= 3:
            pon("bombo", t0 + 2 * P, P, 0, v - 6)
    elif voz == "palmas":
        for off in ((1, 3) if C == 4 else (1, 2)):
            if off < largo:
                pon("palmas", t0 + off * P, P, 0, 66 if C == 4 else 52)


def _contracanto(pon, instrumento: str, estilo: str, t0: float, largo: int, C: int, P: float, raiz: int,
                 menor: bool) -> None:
    lo, hi = RANGO.get(instrumento, (64, 88))
    tonos = tonos_en(raiz, menor, lo, hi)
    if not tonos:
        return
    tercera = next((n for n in tonos if n % 12 == (raiz + (3 if menor else 4)) % 12), tonos[0])
    quinta = next((n for n in tonos if n % 12 == (raiz + 7) % 12 and n > tercera), tercera + 3)
    if estilo == "blancas":
        for off, nota, v in ((0, tercera, 50), (2, quinta, 44)):
            if off < largo and (C == 4 or off == 0):
                pon("contracanto", t0 + off * P, (2 if C == 4 else 3) * P, nota, v)
    elif estilo == "rodado":
        tres = sorted(tonos_en(raiz, menor, 62, 79))[:3] or [tercera, quinta, tercera + 12]
        for e in range(2 * largo):
            pon("contracanto", t0 + e * P / 2, 0.9 * P, tres[e % 3], 58 if e % 3 == 0 else 50)
    elif estilo == "arpegio":
        base = [n for n in tonos if n >= 67][:3] or tonos[:3]
        for off in range(largo):
            pon("contracanto", t0 + off * P, P, base[[0, 1, 2, 1][off % 4] % len(base)], 56 if off == 0 else 50)


def componer(capitulos: list[Capitulo], golpe: float | None = None, semilla: int = SEMILLA,
             cancion: Cancion | None = None, motivo: str = MOTIVO) -> dict[str, list[Nota]]:
    """Las notas de cada voz. Los capítulos ya van en el pulso de la canción (`en_pulso`). `golpe`
    es el instante del nudo apretado: ahí suena el acorde final y la música se queda sonando."""
    can = cancion or CANCIONES["fogata"]
    rng = np.random.default_rng(semilla)
    P, C = can.pulso, can.compas
    notas: dict[str, list[Nota]] = {v: [] for v in VOCES}

    def pon(voz: str, t: float, dur: float, nota: int, vel: float) -> None:
        if golpe is not None and t >= golpe - 1e-6:
            return
        notas[voz].append(Nota(t, dur, int(nota), int(np.clip(vel, 1, 127))))

    tonica_motivo = _en(can.tonica, 76, 87)[0]
    previas = None
    for ci, c in enumerate(capitulos):
        arr = arreglo(can, c.nombre)
        prog = can.progresiones[c.nombre]
        n_pulsos = int(round((c.fin - c.inicio) / P))
        compases = [(k, min(C, n_pulsos - k * C)) for k in range(math.ceil(n_pulsos / C))]
        for k, largo in compases:
            t0 = c.inicio + k * C * P
            raiz, menor, bajo_pc = acorde(prog[k % len(prog)], can.tonica)
            sig_raiz, _, sig_bajo = acorde(prog[(k + 1) % len(prog)], can.tonica)
            bajo, alterno, agudos = voces(raiz, menor, bajo_pc, previas)
            previas = agudos
            final = k == len(compases) - 1
            _guitarra(pon, arr["guitarra"], t0, largo, C, P, bajo, alterno, agudos, k)
            _bajo(pon, arr["bajo"], t0, largo, C, P, raiz_bajo(bajo_pc), raiz_bajo(sig_bajo), k, final)
            if arr["perc"] and k >= arr.get("desde", 0):
                for voz in can.percusion[arr["perc"]]:
                    _percusion(pon, voz, arr["perc"], t0, largo, C, P, k,
                               redoble=final and ci < len(capitulos) - 1)
            if arr.get("pregunta") and k % 2 == 0:
                frase = [(0, 4), (1, 7)] if (k // 2) % 2 == 0 else [(0, 2), (1, 0)]
                altas = al_rango([tonica_motivo + d for _, d in frase], can.pregunta)
                for (off, _), nota in zip(frase, altas):
                    if off < largo:
                        pon("pregunta", t0 + off * P, 2 * P, nota, 52)
            if arr.get("contracanto"):
                _contracanto(pon, can.contracanto[0], can.contracanto[1], t0, largo, C, P, raiz, menor)
        # El motivo, en los dos primeros compases del capítulo. En el cierre con golpe, su primer
        # compás llega justo al golpe, que pone el acorde final en lugar de la respuesta.
        if arr.get("motivo"):
            frase = FRASES[C][arr["motivo"]]
            inicio = c.inicio
            if arr["motivo"] == "cierra" and golpe is not None:
                inicio = max(c.inicio, golpe - C * P)
                frase = [f for f in frase if f[0] < 2 * C]
            alturas = al_rango([tonica_motivo + d for _, d, _ in frase], motivo)
            for (e, _, d), nota in zip(frase, alturas):
                t = inicio + e * P / 2
                if t < c.fin - 1e-6:
                    pon("motivo", t, d * P / 2 + 0.8, nota, 80 if e == 0 else 72)
    # El acorde final, con el golpe: la guitarra rasgueada hacia abajo, el bajo y el motivo en la tónica.
    if golpe is not None:
        raiz, menor, bajo_pc = acorde("I", can.tonica)
        bajo, alterno, agudos = voces(raiz, menor, bajo_pc, previas)
        for i, nota in enumerate([bajo, alterno, *agudos]):
            notas["guitarra"].append(Nota(golpe + 0.018 * i, 4.5, nota, 84 - 2 * i))
        notas["bajo"].append(Nota(golpe, 4.0, raiz_bajo(bajo_pc), 74))
        for nota, v in zip(al_rango([tonica_motivo, tonica_motivo + 12], motivo), (76, 54)):
            notas["motivo"].append(Nota(golpe + 0.03, 3.0, nota, v))
    # La humanización: cada golpe se corre un poco y cambia de fuerza.
    for voz, lista in notas.items():
        for n in lista:
            n.t = max(0.0, n.t + float(np.clip(rng.normal(0, TEMBLOR[voz]), -2.5 * TEMBLOR[voz], 2.5 * TEMBLOR[voz])))
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
    """Un muestreador de golpes sueltos (sin bucles): el glockenspiel y la percusión del VCSL. Cada
    nota toma la muestra más cercana (con su capa de fuerza, si tiene) y la transpone; las muestras
    repetidas se turnan. Los nombres del VCSL van una octava abajo de lo que suena (el do central
    es C3), y la kalimba, una mbira, no está afinada a 440 Hz: `afinado` mide la altura real de
    cada muestra y la corrige."""

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


PERCUSION = ("vcsl:shaker", "vcsl:shaker_grande", "vcsl:palmas", "vcsl:bombo", "vcsl:cajon")


class Sintetico:
    """Todo con síntesis simple (sin bancos ni programas aparte), para las pruebas: cuerdas
    pulsadas que decaen, campanas de parciales inarmónicos y golpes de ruido filtrado."""
    nombre = "sintetico"

    def huella(self) -> dict:
        return {"instrumentos": self.nombre}

    def pista(self, instrumento: str, notas: list[Nota], dur: float, pulso: float) -> np.ndarray:
        n = int(np.ceil(dur * SR))
        out = np.zeros((n + 5 * SR, 2))
        rng = np.random.default_rng(7)
        for nt in notas:
            v = (nt.vel / 127) ** 1.6
            if instrumento in PERCUSION:
                L = int(0.12 * SR)
                t = np.arange(L) / SR
                if instrumento == "vcsl:bombo":
                    s = np.sin(2 * np.pi * (55 + 60 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.09)
                else:
                    s = rng.standard_normal(L) * np.exp(-t / (0.02 if instrumento == "vcsl:palmas" else 0.04))
            else:
                L = int(min(nt.dur + 0.5, 4.0) * SR)
                t = np.arange(L) / SR
                f = 440.0 * 2 ** ((nt.nota - 69) / 12)
                if instrumento in ("vcsl:glock", "vcsl:kalimba", "gm:8", "gm:10", "gm:11", "gm:12"):
                    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d)
                            for r, a, d in ((1, 1, 0.9), (2.76, 0.25, 0.15)))
                else:
                    s = sum(np.sin(2 * np.pi * f * h * t) / h ** 1.5 for h in (1, 2, 3, 4)) * np.exp(-t / 0.6)
                s *= np.minimum(1, t / 0.003)
            _sumar(out, _a_estereo(s * v * 0.5), nt.t)
        return out


class Muestreado:
    """Los instrumentos melódicos por FluidSynth con GeneralUser GS; el glockenspiel y la percusión,
    con los bancos del VCSL."""
    nombre = "muestreado"
    VCSL = {"glock": ("Glockenspiel", True, {"soft": 40, "medium": 72, "loud": 105}, None),
            "kalimba": ("Kalimba, Tanzania", True, None, None),
            "shaker": ("Shaker, Small", False, None, {0: "HighFaster_Down", 1: "HighFaster_Up", 2: "Roll_Fast"}),
            "shaker_grande": ("Shaker, Large", False, None, {0: "Shake1D", 1: "Shake1U", 2: "LShaker_Hit"}),
            "palmas": ("Claps", False, None, {0: "Clap_rr"}),
            "bombo": ("Bass Drum 1", False, {"_v2_": 30, "_v3_": 50, "_v5_": 75, "_v7_": 100}, None),
            "cajon": ("Cajon", False, {"_pp_": 25, "_p_": 40, "_mp_": 60, "_f_": 85, "_fff_": 110},
                      {0: "hit1", 1: "hit2", 2: "hit3"})}

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
        return {"instrumentos": self.nombre, "bancos": h.hexdigest()[:16],
                "fluidsynth": self.fluidsynth.parent.parent.name}

    def pista(self, instrumento: str, notas: list[Nota], dur: float, pulso: float) -> np.ndarray:
        tipo, _, cual = instrumento.partition(":")
        if tipo == "gm":
            return self._fluidsynth(int(cual), notas, dur, pulso)
        if cual not in self.bancos:
            carpeta, afinado, capas, tipos = self.VCSL[cual]
            self.bancos[cual] = Banco(self.vcsl / carpeta, afinado, capas, tipos)
        banco = self.bancos[cual]
        out = np.zeros((int(np.ceil(dur * SR)) + 8 * SR, 2))
        for nt in notas:
            _sumar(out, banco.tocar(nt.nota, nt.vel), nt.t)
        return out

    def _fluidsynth(self, programa: int, notas: list[Nota], dur: float, pulso: float) -> np.ndarray:
        with tempfile.TemporaryDirectory(prefix="nudos-fs-") as tmp:
            mid, wav = Path(tmp) / "pista.mid", Path(tmp) / "pista.wav"
            mid.write_bytes(midi(notas, programa, pulso=pulso))
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


def midi(notas: list[Nota], programa: int, canal: int = 0, ppq: int = 960, pulso: float = 0.6) -> bytes:
    """Un archivo MIDI de formato 0 con las notas, al pulso dado."""
    def vlq(n: int) -> bytes:
        out = [n & 0x7F]
        n >>= 7
        while n:
            out.append((n & 0x7F) | 0x80)
            n >>= 7
        return bytes(reversed(out))
    por_s = ppq / pulso
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
    pista += vlq(0) + b"\xff\x51\x03" + int(round(pulso * 1e6)).to_bytes(3, "big")
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
# La sonoridad de cada voz donde suena, en LU respecto de la guitarra; su lugar en el estéreo (−1
# izquierda, 1 derecha), y cuánto va a la sala. La ponderación K oye poco los graves, así que el
# bajo y el bombo van más abajo de lo que se sienten.
MEZCLA = {"guitarra": (0.0, -0.18, 0.22), "bajo": (-6.0, 0.0, 0.08), "motivo": (-1.0, 0.28, 0.30),
          "pregunta": (-8.0, 0.35, 0.30), "contracanto": (-7.0, 0.32, 0.25), "shaker": (-16.0, 0.45, 0.18),
          "shaker_grande": (-15.0, 0.40, 0.18), "palmas": (-11.0, -0.25, 0.25), "bombo": (-12.0, 0.0, 0.10),
          "cajon": (-11.0, -0.10, 0.15)}
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
    for voz, x in pistas.items():
        if not np.abs(x).max() > 0:
            continue
        rel, pan, rev = MEZCLA[voz]
        y = _panear(np.asarray(x)[:n], pan)
        if voz == "bombo":
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
# La canción de cada nudo y la pista de un video
# --------------------------------------------------------------------------
def reparto() -> dict[str, str]:
    """slug → canción, de config/musica.yaml."""
    import yaml
    if not REPARTO.exists():
        return {}
    datos = yaml.safe_load(REPARTO.read_text(encoding="utf-8")) or {}
    return dict(datos.get("canciones") or {})


def cancion_de(slug: str) -> Cancion:
    """La canción de un nudo: la de config/musica.yaml o, si no está ahí, una fija por su nombre."""
    clave = reparto().get(slug)
    if clave is None:
        claves = sorted(CANCIONES)
        clave = claves[int(hashlib.sha256(slug.encode()).hexdigest(), 16) % len(claves)]
    if clave not in CANCIONES:
        raise MusicaError(f"{slug}: «{clave}» no es una canción; puede ser {', '.join(CANCIONES)}")
    return CANCIONES[clave]


def carpeta_cache() -> Path:
    base = os.environ.get("NUDOS_MUSICA") or str(Path(os.environ.get("LOCALAPPDATA", Path.home()))
                                                  / "nudos" / "musica")
    return Path(base)


def _huella(*partes) -> str:
    h = hashlib.sha256()
    for p in partes:
        h.update(json.dumps(p, sort_keys=True, default=str).encode())
    return h.hexdigest()[:20]


def _codigo() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]


def _escribir(ruta: Path, x) -> None:
    from scipy.io import wavfile
    tmp = ruta.with_suffix(".tmp.wav")
    wavfile.write(tmp, SR, np.asarray(x, np.float32))
    tmp.replace(ruta)


def musica(capitulos: list[Capitulo], golpe: float | None = None, semilla: int = SEMILLA,
           cancion: Cancion | str | None = None, slug: str | None = None, motivo: str = MOTIVO,
           instrumentos=None, aviso=print) -> Musica:
    """La música de un video: sus capítulos (en segundos desde el inicio del video), el golpe del
    nudo apretado (no se corre al pulso: el acorde final suena con el golpe que se ve) y su
    canción (o el slug del nudo, para tomar la suya). Da la mezcla estéreo a SR, del largo del
    último capítulo."""
    if isinstance(cancion, str):
        cancion = CANCIONES[cancion]
    can = cancion or (cancion_de(slug) if slug else CANCIONES["fogata"])
    caps = en_pulso(capitulos, can.pulso)
    pulsos, compases = rejilla(caps, can.pulso, can.compas)
    dur = caps[-1].fin
    inst = instrumentos or Muestreado()
    h = _huella(VERSION, [asdict(c) for c in caps], golpe, semilla, asdict(can), motivo, inst.huella(), _codigo())
    ruta = carpeta_cache() / f"{can.clave}-{h}.wav"
    if not ruta.exists():
        notas = componer(caps, golpe, semilla, can, motivo)
        de = instrumentos_de(can, motivo)
        pistas = {v: inst.pista(de[v], notas[v], dur, can.pulso) for v in VOCES if notas[v]}
        x = mezclar(pistas, dur)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        _escribir(ruta, x)
    x, _ = _leer_wav(ruta)
    return Musica(x.astype(np.float32), caps, pulsos, compases, can.clave, h)
