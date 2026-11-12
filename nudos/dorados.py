"""Pruebas doradas de la skill nudo-nuevo: un borrador contra la especificación validada.

La skill corre a ciegas sobre las entradas de un nudo ya validado, y su borrador se guarda
en tests/dorados/ (ver T9 en el plan). Aquí se compara con la especificación validada. No
importa cómo se llama cada cruce: las secuencias se comparan con los cruces numerados en
el orden en que aparecen.

Tampoco importa cómo se dividen los pasos. Gabriel lo decidió el 12 de noviembre de 2026:
la división es una decisión de cómo enseñar el nudo, no de cómo leer los cruces. Se exige:
- que cada paso del borrador sea un paso de la especificación validada, en el mismo orden;
- que cada cruce del borrador sea siempre el mismo cruce de la validada, en todos los pasos;
- el mismo nudo terminado, es decir, la misma secuencia en el último paso, y
- el mismo error común: la misma secuencia, con los mismos cruces al revés.
"""
from __future__ import annotations

from .spec import Spec

_AL_REVES = {"O": "U", "U": "O"}


def renumerar(secuencias: list[tuple[str, ...]]) -> tuple[list[tuple[str, ...]], dict[str, str]]:
    """Las secuencias, con los cruces numerados 1, 2, 3… en el orden en que aparecen por
    primera vez entre todas, y qué número le tocó a cada etiqueta."""
    numeros: dict[str, str] = {}
    out = []
    for secuencia in secuencias:
        out.append(tuple(numeros.setdefault(t[:-1], str(len(numeros) + 1)) + t[-1]
                         for t in secuencia))
    return out, numeros


def _sola(secuencia: tuple[str, ...]) -> tuple[str, ...]:
    """Una secuencia renumerada por sí sola."""
    return renumerar([secuencia])[0][0]


def _texto(secuencia: tuple[str, ...]) -> str:
    return " ".join(secuencia) or "sin cruces"


def _del_error(spec: Spec) -> tuple[str, ...]:
    """La secuencia del error común: la de su paso, con los cruces de «invierte» al revés."""
    e = spec.error
    return tuple(t[:-1] + _AL_REVES[t[-1]] if t[:-1] in e.invierte else t
                 for t in spec.pasos[e.paso - 1].secuencia)


def diferencias(borrador: Spec, validada: Spec) -> list[str]:
    """En qué difiere el borrador de la especificación validada; vacío si no difiere."""
    out = []
    if [c.grosor for c in borrador.cuerdas] != [c.grosor for c in validada.cuerdas]:
        out.append("las cuerdas no son las mismas o van en otro orden")
    validados = [_sola(q.secuencia) for q in validada.pasos]
    nombres: dict[str, str] = {}   # etiqueta del borrador → etiqueta de la validada
    desde = 0                      # el paso validado que le tocó al paso anterior
    for p in borrador.pasos:
        s = _sola(p.secuencia)
        iguales = [k for k in range(desde, len(validada.pasos))
                   if validados[k] == s and validada.pasos[k].pasadas == p.pasadas]
        if not iguales:
            out.append(f"paso {p.n}: {_texto(s)} no es ningún paso de la especificación "
                       f"validada desde su paso {desde + 1}")
            continue
        desde = iguales[0]
        for x, y in zip(p.secuencia, validada.pasos[desde].secuencia):
            antes = nombres.setdefault(x[:-1], y[:-1])
            if antes != y[:-1]:
                out.append(f"paso {p.n}: el cruce {x[:-1]} del borrador es el {y[:-1]} de la "
                           f"especificación validada, y en un paso anterior era el {antes}")
                nombres[x[:-1]] = y[:-1]
    ultimo_a, ultimo_b = _sola(borrador.pasos[-1].secuencia), _sola(validada.pasos[-1].secuencia)
    if ultimo_a != ultimo_b:
        out.append(f"el nudo terminado es {_texto(ultimo_a)} en vez de {_texto(ultimo_b)}")
    ea, eb = borrador.error, validada.error
    if (ea is None) != (eb is None):
        out.append("el error común está en una sola de las dos")
    elif ea is not None:
        sa, sb = _sola(_del_error(borrador)), _sola(_del_error(validada))
        invierte = sorted(nombres.get(e, f"«{e}»") for e in ea.invierte)
        if sa != sb:
            out.append(f"el error común es {_texto(sa)} en vez de {_texto(sb)}")
        elif invierte != sorted(eb.invierte):
            out.append(f"el error común invierte los cruces {', '.join(invierte)} de la "
                       f"especificación validada en vez de {', '.join(sorted(eb.invierte))}")
    return out
