"""Estado de producción de los nudos de la edición 1.

Cada especificación declara su `estado` (docs/formato-spec.md), que avanza así:
borrador → modelado → cuerda-ok → novato-ok → publicado. Aquí se comprueba que el estado
declarado no diga más de lo que muestran los hechos, y se arma la tabla de
`python -m nudos estado`, con lo que le falta a cada nudo para el estado siguiente.

Que el nudo construya sin fallas no se comprueba aquí, porque construir los 36 tarda
minutos: lo comprueban las pruebas (tests/test_estado.py) y `python -m nudos construir`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from . import RAIZ, SPECS
from .exportar import leer_publicados
from .ficha import faltan_textos
from .spec import ESTADOS, Filtro, Spec, cargar

EDICION = RAIZ / "config" / "edicion-1.yaml"
SIN_ESPECIFICACION = "sin especificación"


def leer_edicion(ruta: Path = EDICION) -> dict[str, list[str]]:
    """Los nudos de la edición, por tanda, en orden: {tanda: [slug, ...]}."""
    with open(ruta, encoding="utf-8") as f:
        return {tanda: list(slugs) for tanda, slugs in yaml.safe_load(f).items()}


def ultimo_filtro(spec: Spec, n: int) -> Filtro | None:
    """El último registro del filtro n, que es el que vale: si una prueba no pasa, se
    corrige la ficha y se repite."""
    registros = [(f.fecha, i, f) for i, f in enumerate(spec.filtros) if f.filtro == n]
    return max(registros)[2] if registros else None


def _filtro(spec: Spec, n: int) -> list[str]:
    f = ultimo_filtro(spec, n)
    if f is None:
        return [f"falta el filtro {n}"]
    if f.resultado != "aprobado":
        return [f"el último filtro {n} ({f.fecha:%d/%m}) no pasó: corrige la ficha y repítelo"]
    return []


def faltan_para(spec: Spec, estado: str, publicados: list[str]) -> list[str]:
    """Lo que le falta a la especificación para estar en «estado», con lo de los anteriores."""
    requisitos = {
        "borrador": lambda: [],
        "modelado": lambda: [f"le falta a la ficha: {', '.join(f)}" for f in [faltan_textos(spec)] if f],
        "cuerda-ok": lambda: _filtro(spec, 1),
        "novato-ok": lambda: _filtro(spec, 2),
        "publicado": lambda: [] if spec.slug in publicados else ["no está en publicados.txt"],
    }
    faltan: list[str] = []
    for e in ESTADOS[:ESTADOS.index(estado) + 1]:
        faltan += requisitos[e]()
    return faltan


@dataclass(frozen=True)
class Nudo:
    slug: str
    tanda: str
    nombre: str                # el de la especificación; sin ella, el slug
    declarado: str             # el `estado` de la especificación, o SIN_ESPECIFICACION
    alcanzado: str             # el más alto que muestran los hechos, o SIN_ESPECIFICACION
    bloquea: tuple[str, ...]   # lo que le falta para el estado siguiente al declarado
    problemas: tuple[str, ...]


def nudo(slug: str, tanda: str, publicados: list[str]) -> Nudo:
    if not (SPECS / f"{slug}.yaml").is_file():
        return Nudo(slug, tanda, slug, SIN_ESPECIFICACION, SIN_ESPECIFICACION, (), ())
    spec = cargar(slug)
    alcanzado = max((e for e in ESTADOS if not faltan_para(spec, e, publicados)), key=ESTADOS.index)
    problemas = []
    if ESTADOS.index(spec.estado) > ESTADOS.index(alcanzado):
        problemas.append(f"dice «{spec.estado}», pero " + "; ".join(faltan_para(spec, spec.estado, publicados)))
    repetidos = sorted({f.codigo for f in spec.filtros if f.filtro == 2
                        and sum(g.filtro == 2 and g.codigo == f.codigo for g in spec.filtros) > 1})
    if repetidos:
        problemas.append(f"{', '.join(repetidos)} hizo más de una vez el filtro 2: si no pasa, "
                         "se repite con otra persona")
    siguiente = ESTADOS.index(spec.estado) + 1
    bloquea = () if siguiente == len(ESTADOS) or problemas else tuple(
        f for f in faltan_para(spec, ESTADOS[siguiente], publicados)
        if f not in faltan_para(spec, spec.estado, publicados))
    if spec.estado == "borrador" and not bloquea and not problemas:
        # Un borrador con todo el texto pasa a modelado cuando Gabriel lo revisa (skill nudo-nuevo).
        bloquea = ("falta que Gabriel revise el borrador",)
    return Nudo(slug, tanda, spec.nombre, spec.estado, alcanzado, bloquea, tuple(problemas))


def nudos(publicados: list[str] | None = None, edicion: dict[str, list[str]] | None = None) -> list[Nudo]:
    """Los nudos de la edición, en el orden de config/edicion-1.yaml."""
    publicados = leer_publicados() if publicados is None else publicados
    edicion = leer_edicion() if edicion is None else edicion
    return [nudo(slug, tanda, publicados) for tanda, slugs in edicion.items() for slug in slugs]


def probadores() -> dict[str, tuple[str, list[str]]]:
    """Qué nudos probó cada código en el filtro 2, para no repetirlo en uno que ya conoce:
    {código: (rol, [slug, ...])}."""
    out: dict[str, tuple[str, list[str]]] = {}
    for ruta in sorted(SPECS.glob("*.yaml")):
        for f in cargar(ruta).filtros:
            if f.filtro == 2:
                rol, slugs = out.setdefault(f.codigo, (f.rol, []))
                if ruta.stem not in slugs:
                    slugs.append(ruta.stem)
    return dict(sorted(out.items()))


def tabla(lista: list[Nudo]) -> str:
    """La tabla del estado, por tanda, para la terminal."""
    ancho = max(len(n.nombre) for n in lista)
    cuenta = {e: sum(n.declarado == e for n in lista) for e in (*reversed(ESTADOS), SIN_ESPECIFICACION)}
    lineas = [f"Edición 1: {len(lista)} nudos. "
              + ", ".join(f"{c} {e}" for e, c in cuenta.items() if c) + "."]
    tanda = None
    for n in lista:
        if n.tanda != tanda:
            tanda = n.tanda
            lineas += ["", tanda]
        detalle = "; ".join(n.problemas) if n.problemas else "; ".join(n.bloquea)
        marca = "!!" if n.problemas else "  "
        lineas.append(f"{marca}{n.nombre:<{ancho}}  {n.declarado:<18}  {detalle}".rstrip())
    return "\n".join(lineas)
