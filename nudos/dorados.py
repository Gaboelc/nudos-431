"""Pruebas doradas de la skill nudo-nuevo: un borrador contra la especificación validada.

La skill corre a ciegas sobre las entradas de un nudo ya validado, y su borrador se guarda
en tests/dorados/ (ver T9 en el plan). Aquí se compara con la especificación validada:
los mismos pasos, la misma secuencia de cruces en cada uno y el mismo error común. No
importa cómo se llama cada cruce: en los dos, los cruces se numeran en el orden en que
aparecen por primera vez.
"""
from __future__ import annotations

from .spec import Spec


def renumerar(secuencias: list[tuple[str, ...]]) -> tuple[list[tuple[str, ...]], dict[str, str]]:
    """Las secuencias de los pasos, con los cruces numerados 1, 2, 3… en el orden en que
    aparecen por primera vez, y qué número le tocó a cada etiqueta."""
    numeros: dict[str, str] = {}
    out = []
    for secuencia in secuencias:
        out.append(tuple(numeros.setdefault(t[:-1], str(len(numeros) + 1)) + t[-1]
                         for t in secuencia))
    return out, numeros


def _texto(secuencia: tuple[str, ...]) -> str:
    return " ".join(secuencia) or "sin cruces"


def diferencias(borrador: Spec, validada: Spec) -> list[str]:
    """En qué difiere el borrador de la especificación validada; vacío si no difiere."""
    a, num_a = renumerar([p.secuencia for p in borrador.pasos])
    b, num_b = renumerar([p.secuencia for p in validada.pasos])
    out = []
    if len(a) != len(b):
        out.append(f"el borrador tiene {len(a)} pasos y la especificación validada {len(b)}")
    if [c.grosor for c in borrador.cuerdas] != [c.grosor for c in validada.cuerdas]:
        out.append("las cuerdas no son las mismas o van en otro orden")
    for n, (pa, pb, x, y) in enumerate(zip(borrador.pasos, validada.pasos, a, b), 1):
        if x != y:
            out.append(f"paso {n}: {_texto(x)} en vez de {_texto(y)}")
        elif pa.pasadas != pb.pasadas:
            out.append(f"paso {n}: los cruces se reparten de otra manera entre las cuerdas")
    ea, eb = borrador.error, validada.error
    if (ea is None) != (eb is None):
        out.append("el error común está en una sola de las dos")
    elif ea is not None:
        if ea.paso != eb.paso:
            out.append(f"el error común va junto al paso {ea.paso} en vez del {eb.paso}")
        invierte_a = sorted(num_a.get(e, f"«{e}»") for e in ea.invierte)
        invierte_b = sorted(num_b.get(e, f"«{e}»") for e in eb.invierte)
        if invierte_a != invierte_b:
            out.append(f"el error común invierte los cruces {', '.join(invierte_a)} en vez de "
                       f"{', '.join(invierte_b)}")
    return out
