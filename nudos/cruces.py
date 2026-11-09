"""Cruces de una cuerda y su secuencia de encima/debajo.

Una secuencia recorre la cuerda desde el firme y anota cada paso por un cruce:
«1U» es pasar por debajo en el cruce 1 y «1O» pasar por encima. En un paso, cada
etiqueta aparece dos veces, una con O y otra con U.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

_TOKEN = re.compile(r"^(\d+)([OU])$")


class SecuenciaError(ValueError):
    """La secuencia de cruces está mal escrita."""


def leer_secuencia(texto: str) -> tuple[str, ...]:
    tokens = tuple(texto.split())
    letras: dict[str, list[str]] = {}
    for t in tokens:
        m = _TOKEN.match(t)
        if not m:
            raise SecuenciaError(f"«{t}» no es un paso por un cruce; se escribe como 1O o 1U")
        letras.setdefault(m.group(1), []).append(m.group(2))
    for et, vistas in letras.items():
        if sorted(vistas) != ["O", "U"]:
            raise SecuenciaError(
                f"el cruce {et} aparece como {' '.join(et + v for v in vistas)}; cada cruce "
                "se pasa dos veces, una por encima (O) y otra por debajo (U)")
    return tokens


def etiqueta(token: str) -> str:
    return token[:-1]


def encima(token: str) -> bool:
    return token[-1] == "O"


def numerada(secuencia) -> list[str]:
    """La secuencia con las etiquetas renumeradas en orden de aparición."""
    nuevas: dict[str, str] = {}
    out = []
    for t in secuencia:
        nueva = nuevas.setdefault(etiqueta(t), str(len(nuevas) + 1))
        out.append(nueva + t[-1])
    return out


def consistencia(secuencias: list[tuple[int, tuple[str, ...]]]) -> list[str]:
    """Cada cruce conserva su encima/debajo en todos los pasos donde aparece.

    `secuencias` es una lista de (número de paso, secuencia). Se compara la
    primera pasada de cada cruce, que es la misma pasada física mientras el
    cruce exista."""
    lados: dict[str, dict[bool, list[int]]] = {}
    for n, sec in secuencias:
        primera: dict[str, bool] = {}
        for t in sec:
            primera.setdefault(etiqueta(t), encima(t))
        for et, arriba in primera.items():
            lados.setdefault(et, {True: [], False: []})[arriba].append(n)
    errores = []
    for et in sorted(lados, key=int):
        arriba, abajo = lados[et][True], lados[et][False]
        if arriba and abajo:
            errores.append(
                f"Cruce {et}: la primera pasada va por encima en {_pasos(arriba)} y por "
                f"debajo en {_pasos(abajo)}. Un cruce no cambia de encima a debajo entre "
                "pasos; si de verdad cambia, es otro cruce y lleva otra etiqueta.")
    return errores


def _pasos(ns: list[int]) -> str:
    if len(ns) == 1:
        return f"el paso {ns[0]}"
    return "los pasos " + ", ".join(map(str, ns[:-1])) + f" y {ns[-1]}"


@dataclass(frozen=True)
class Cruce:
    sa: float                 # posición a lo largo de la cuerda de la primera pasada
    sb: float                 # posición de la segunda pasada
    xy: tuple[float, float]   # dónde está sobre la mesa
    seno: float               # |sen| del ángulo entre los dos tramos


def encontrar_cruces(X: np.ndarray, h: float) -> list[Cruce]:
    """Cruces de la proyección sobre la mesa de una cuerda muestreada cada h."""
    P = X[:, :2]
    A, B = P[:-1], P[1:]
    i, j = np.triu_indices(len(A), k=2)
    lo, hi = np.minimum(A, B), np.maximum(A, B)
    ok = ((lo[i, 0] <= hi[j, 0]) & (lo[j, 0] <= hi[i, 0]) &
          (lo[i, 1] <= hi[j, 1]) & (lo[j, 1] <= hi[i, 1]))
    i, j = i[ok], j[ok]
    r, s = B[i] - A[i], B[j] - A[j]
    qp = A[j] - A[i]
    rxs = r[:, 0] * s[:, 1] - r[:, 1] * s[:, 0]
    nz = np.abs(rxs) > 1e-12
    i, j, r, s, qp, rxs = i[nz], j[nz], r[nz], s[nz], qp[nz], rxs[nz]
    t = (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / rxs
    u = (qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]) / rxs
    hit = (t >= 0) & (t < 1) & (u >= 0) & (u < 1)
    out: list[Cruce] = []
    for k in np.nonzero(hit)[0]:
        sa, sb = (i[k] + t[k]) * h, (j[k] + u[k]) * h
        if any(abs(c.sa - sa) < 0.3 and abs(c.sb - sb) < 0.3 for c in out):
            continue
        seno = abs(rxs[k]) / (np.linalg.norm(r[k]) * np.linalg.norm(s[k]))
        p = A[i[k]] + t[k] * r[k]
        out.append(Cruce(float(sa), float(sb), (float(p[0]), float(p[1])), float(seno)))
    return out


def _ocurrencias(cruces: list[Cruce]) -> list[tuple[float, int, int]]:
    occ = ([(c.sa, k, 0) for k, c in enumerate(cruces)] +
           [(c.sb, k, 1) for k, c in enumerate(cruces)])
    occ.sort()
    return occ


def _canonica(etiquetas) -> list[int]:
    vistas: dict = {}
    return [vistas.setdefault(e, len(vistas)) for e in etiquetas]


def emparejar(cruces: list[Cruce], secuencia) -> list[str] | None:
    """La etiqueta de la secuencia que corresponde a cada cruce geométrico, o
    None si el orden de los cruces en la cuerda no coincide con la secuencia."""
    occ = _ocurrencias(cruces)
    if _canonica(k for _, k, _ in occ) != _canonica(etiqueta(t) for t in secuencia):
        return None
    etiquetas: list[str] = [""] * len(cruces)
    for (_, k, cual), t in zip(occ, secuencia):
        if cual == 0:
            etiquetas[k] = etiqueta(t)
    return etiquetas


def encimas(cruces: list[Cruce], secuencia) -> list[bool]:
    """Para cada cruce geométrico, si su primera pasada va por encima. Supone que
    `emparejar` ya confirmó que el orden coincide."""
    out = [False] * len(cruces)
    for (_, k, cual), t in zip(_ocurrencias(cruces), secuencia):
        if cual == 0:
            out[k] = encima(t)
    return out


def secuencia_obtenida(X: np.ndarray, h: float, cruces: list[Cruce], alturas=None) -> list[str]:
    """La secuencia que resulta de la altura de la cuerda en cada cruce, numerada
    en orden de aparición. `alturas` da, para cada cruce, la de sus dos pasadas cuando no
    es la altura sobre la mesa (sobre un poste es la distancia al eje)."""
    s = np.arange(len(X)) * h
    nums: dict[int, int] = {}
    out = []
    for _, k, cual in _ocurrencias(cruces):
        c = cruces[k]
        if alturas is None:
            za = np.interp(c.sa, s, X[:, 2])
            zb = np.interp(c.sb, s, X[:, 2])
        else:
            za, zb = alturas[k]
        primera_encima = za > zb
        arriba = primera_encima if cual == 0 else not primera_encima
        n = nums.setdefault(k, len(nums) + 1)
        out.append(f"{n}{'O' if arriba else 'U'}")
    return out
