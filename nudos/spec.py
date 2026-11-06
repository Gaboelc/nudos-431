"""Especificación de un nudo: lectura y validación de `specs/<slug>.yaml`.

El formato está descrito en `docs/formato-spec.md`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from . import SPECS
from .cruces import SecuenciaError, leer_secuencia

_NOMBRE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REF = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)(?:\[([^\]]*)\])?$")
DISTANCIA_MIN = 0.05   # entre puntos de control seguidos, en diámetros

_CAMPOS = {"slug", "nombre", "familia", "abok", "encuadre", "segmentos", "pasos", "error",
           "terminado"}
_CAMPOS_PASO = {"titulo", "texto", "trazado", "secuencia", "resaltar"}
_CAMPOS_ERROR = {"paso", "invierte", "titulo", "texto", "encuadre"}
_CAMPOS_TERMINADO = {"encuadre"}


class SpecError(ValueError):
    """La especificación tiene un error. El mensaje dice dónde."""


@dataclass(frozen=True)
class Paso:
    n: int
    titulo: str
    texto: str
    puntos: np.ndarray                 # (N, 2) puntos de control, en orden de la cuerda
    secuencia: tuple[str, ...]
    resaltar: tuple[int, int] | None   # índices de puntos de control


@dataclass(frozen=True)
class Encuadre:
    x: tuple[float, float]
    y: tuple[float, float]


@dataclass(frozen=True)
class Error:
    """El error más común: un paso con algunos cruces invertidos."""
    paso: int
    invierte: tuple[str, ...]          # etiquetas de los cruces que quedan al revés
    titulo: str
    texto: str
    encuadre: Encuadre | None          # zona que se muestra del error y del paso correcto


@dataclass(frozen=True)
class Terminado:
    """Cómo se muestra el nudo terminado (el último paso), por delante y por detrás."""
    encuadre: Encuadre | None = None


@dataclass(frozen=True)
class Spec:
    slug: str
    nombre: str
    familia: str
    abok: int | None
    encuadre: Encuadre | None
    pasos: tuple[Paso, ...]
    error: Error | None = None
    terminado: Terminado = Terminado()


def cargar(slug_o_ruta: str | Path) -> Spec:
    """Carga una especificación por su slug o por la ruta del archivo."""
    ruta = Path(slug_o_ruta)
    if ruta.suffix not in (".yaml", ".yml"):
        ruta = SPECS / f"{slug_o_ruta}.yaml"
    if not ruta.exists():
        raise SpecError(f"no existe {ruta}")
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f)
    spec = desde_datos(datos, origen=ruta.name)
    if spec.slug != ruta.stem:
        raise SpecError(f"{ruta.name}: el slug «{spec.slug}» no coincide con el nombre del archivo")
    return spec


def desde_datos(datos, origen: str = "especificación") -> Spec:
    def falla(msg: str) -> SpecError:
        return SpecError(f"{origen}: {msg}")

    if not isinstance(datos, dict):
        raise falla("el archivo debe ser un mapa YAML")
    sobran = set(datos) - _CAMPOS
    if sobran:
        raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
    slug = _texto(datos, "slug", falla)
    if not _NOMBRE.match(slug):
        raise falla(f"slug «{slug}»: usa minúsculas, números y guiones")
    abok = datos.get("abok")
    if abok is not None and (not isinstance(abok, int) or isinstance(abok, bool)):
        raise falla("abok debe ser un número entero")
    segmentos = _segmentos(datos.get("segmentos"), falla)
    pasos = datos.get("pasos")
    if not isinstance(pasos, list) or not pasos:
        raise falla("falta la lista de pasos")
    pasos = tuple(_paso(i + 1, p, segmentos, falla) for i, p in enumerate(pasos))
    return Spec(
        slug=slug,
        nombre=_texto(datos, "nombre", falla),
        familia=_texto(datos, "familia", falla),
        abok=abok,
        encuadre=_encuadre(datos.get("encuadre"), falla),
        pasos=pasos,
        error=_error(datos.get("error"), pasos, falla),
        terminado=_terminado(datos.get("terminado"), falla),
    )


def _error(datos, pasos: tuple[Paso, ...], falla) -> Error | None:
    if datos is None:
        return None

    def ef(msg: str) -> SpecError:
        return falla(f"error: {msg}")

    if not isinstance(datos, dict):
        raise ef("debe ser un mapa")
    sobran = set(datos) - _CAMPOS_ERROR
    if sobran:
        raise ef(f"campos desconocidos: {', '.join(sorted(sobran))}")
    n = datos.get("paso")
    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= len(pasos):
        raise ef(f"«paso» es el número del paso que se muestra con el error, de 1 a {len(pasos)}")
    invierte = datos.get("invierte")
    if not isinstance(invierte, list) or not invierte:
        raise ef("«invierte» es la lista de cruces que quedan al revés, por ejemplo [1]")
    etiquetas = tuple(str(e) for e in invierte)
    if len(set(etiquetas)) != len(etiquetas):
        raise ef("un cruce aparece dos veces en «invierte»")
    del_paso = {t[:-1] for t in pasos[n - 1].secuencia}
    faltan = [e for e in etiquetas if e not in del_paso]
    if faltan:
        raise ef(f"el paso {n} no tiene el cruce {', '.join(faltan)}")
    return Error(
        paso=n,
        invierte=etiquetas,
        titulo=_texto(datos, "titulo", ef),
        texto=_texto(datos, "texto", ef),
        encuadre=_encuadre(datos.get("encuadre"), ef),
    )


def _terminado(datos, falla) -> Terminado:
    if datos is None:
        return Terminado()
    if not isinstance(datos, dict):
        raise falla("terminado: debe ser un mapa")
    sobran = set(datos) - _CAMPOS_TERMINADO
    if sobran:
        raise falla(f"terminado: campos desconocidos: {', '.join(sorted(sobran))}")
    return Terminado(encuadre=_encuadre(datos.get("encuadre"), lambda m: falla(f"terminado: {m}")))


def _texto(datos: dict, clave: str, falla) -> str:
    valor = datos.get(clave)
    if not isinstance(valor, str) or not valor.strip():
        raise falla(f"falta «{clave}»")
    return valor.strip()


def _segmentos(datos, falla) -> dict[str, np.ndarray]:
    if not isinstance(datos, dict) or not datos:
        raise falla("falta el mapa de segmentos")
    out = {}
    for nombre, puntos in datos.items():
        if not isinstance(nombre, str) or not _NOMBRE.match(nombre):
            raise falla(f"segmento «{nombre}»: usa minúsculas, números y guiones")
        try:
            arr = np.asarray(puntos, dtype=float)
        except (TypeError, ValueError):
            arr = None
        if arr is None or arr.ndim != 2 or arr.shape[1] != 2 or len(arr) == 0:
            raise falla(f"segmento {nombre}: los puntos deben ser pares [x, y]")
        out[nombre] = arr
    return out


def _encuadre(datos, falla) -> Encuadre | None:
    if datos is None:
        return None
    try:
        x, y = datos["x"], datos["y"]
        x = (float(x[0]), float(x[1]))
        y = (float(y[0]), float(y[1]))
    except (TypeError, KeyError, IndexError, ValueError):
        raise falla("encuadre lleva x: [mín, máx] e y: [mín, máx]") from None
    if x[0] >= x[1] or y[0] >= y[1]:
        raise falla("en el encuadre, el mínimo va antes que el máximo")
    return Encuadre(x, y)


def _paso(n: int, datos, segmentos: dict[str, np.ndarray], falla) -> Paso:
    def pf(msg: str) -> SpecError:
        return falla(f"paso {n}: {msg}")

    if not isinstance(datos, dict):
        raise pf("debe ser un mapa")
    sobran = set(datos) - _CAMPOS_PASO
    if sobran:
        raise pf(f"campos desconocidos: {', '.join(sorted(sobran))}")
    trazado = datos.get("trazado")
    if not isinstance(trazado, list) or not trazado:
        raise pf("falta el trazado")

    partes: list[tuple[str, list[int]]] = []
    for ref in trazado:
        nombre, sel = _ref(ref, pf)
        if nombre not in segmentos:
            raise pf(f"el segmento «{nombre}» no existe")
        if isinstance(sel, int):
            raise pf(f"«{ref}»: en el trazado va un segmento o un tramo [a:b], no un punto")
        if any(nombre == usado for usado, _ in partes):
            raise pf(f"el segmento {nombre} aparece dos veces")
        indices = list(range(len(segmentos[nombre])))[sel]
        if not indices:
            raise pf(f"«{ref}» no tiene puntos")
        partes.append((nombre, indices))

    puntos = np.vstack([segmentos[nombre][indices] for nombre, indices in partes])
    if len(puntos) < 2:
        raise pf("el trazado necesita al menos dos puntos")
    cerca = np.linalg.norm(np.diff(puntos, axis=0), axis=1) < DISTANCIA_MIN
    if cerca.any():
        p = puntos[int(np.argmax(cerca))]
        raise pf(f"hay dos puntos seguidos casi iguales cerca de ({p[0]:g}, {p[1]:g})")

    if "secuencia" not in datos:
        raise pf("falta «secuencia» (escribe \"\" si el paso no tiene cruces)")
    try:
        secuencia = leer_secuencia(str(datos["secuencia"]))
    except SecuenciaError as e:
        raise pf(str(e)) from None

    return Paso(
        n=n,
        titulo=_texto(datos, "titulo", pf),
        texto=_texto(datos, "texto", pf),
        puntos=puntos,
        secuencia=secuencia,
        resaltar=_resaltar(datos.get("resaltar"), partes, segmentos, len(puntos), pf),
    )


def _ref(texto, pf):
    """«seg» → (seg, slice(None)); «seg[a:b]» → (seg, slice); «seg[i]» → (seg, i)."""
    m = _REF.match(texto.strip()) if isinstance(texto, str) else None
    if not m:
        raise pf(f"referencia mal escrita: «{texto}»")
    nombre, dentro = m.group(1), m.group(2)
    if dentro is None:
        return nombre, slice(None)
    try:
        if ":" in dentro:
            a, b = dentro.split(":", 1)
            return nombre, slice(int(a) if a.strip() else None, int(b) if b.strip() else None)
        return nombre, int(dentro)
    except ValueError:
        raise pf(f"referencia mal escrita: «{texto}»") from None


def _resaltar(datos, partes, segmentos, total: int, pf) -> tuple[int, int] | None:
    if datos is None:
        return None
    if not isinstance(datos, dict) or set(datos) != {"desde", "hasta"}:
        raise pf("resaltar lleva «desde» y «hasta»")
    a = _punto(datos["desde"], partes, segmentos, total, pf)
    b = _punto(datos["hasta"], partes, segmentos, total, pf)
    if b <= a:
        raise pf("en resaltar, «hasta» debe ir después de «desde»")
    return a, b


def _punto(ref, partes, segmentos, total: int, pf) -> int:
    """Índice, dentro del paso, del punto al que apunta una referencia."""
    if ref == "fin":
        return total - 1
    nombre, sel = _ref(ref, pf)
    if not isinstance(sel, int):
        raise pf(f"«{ref}»: en resaltar va un punto, como segmento[0] o segmento[-1]")
    base = 0
    for usado, indices in partes:
        if usado == nombre:
            largo = len(segmentos[nombre])
            original = sel + largo if sel < 0 else sel
            if original not in indices:
                raise pf(f"«{ref}» no está en el tramo de {nombre} que usa este paso")
            return base + indices.index(original)
        base += len(indices)
    raise pf(f"«{ref}»: el segmento {nombre} no está en el trazado de este paso")
