"""Especificación de un nudo: lectura y validación de `specs/<slug>.yaml`.

El formato está descrito en `docs/formato-spec.md`.
"""
from __future__ import annotations

import datetime as dt
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
# Código anónimo de un probador: letras y números, como P01. Así no cabe un nombre.
_CODIGO = re.compile(r"^[A-Z]{1,3}[0-9]{2,3}$")
RESULTADOS = ("aprobado", "no aprobado")

_CAMPOS = {"slug", "nombre", "otros_nombres", "familia", "abok", "usos", "materiales",
           "verificacion", "seguridad", "encuadre", "anfitrion", "segmentos", "pasos", "error",
           "terminado", "filtros"}
_CAMPOS_PASO = {"titulo", "texto", "trazado", "secuencia", "resaltar"}
_CAMPOS_ERROR = {"paso", "invierte", "titulo", "texto", "encuadre"}
_CAMPOS_TERMINADO = {"encuadre"}
_CAMPOS_FILTRO = {"filtro", "fecha", "resultado", "rol", "codigo", "ficha"}
_CAMPOS_ANFITRION = {"tipo", "radio", "desde", "hasta"}
TIPOS_ANFITRION = ("poste",)


class SpecError(ValueError):
    """La especificación tiene un error. El mensaje dice dónde."""


@dataclass(frozen=True)
class Paso:
    n: int
    titulo: str
    texto: str
    # (N, 2) puntos de control, en orden de la cuerda. Sobre la mesa son [x, y]; sobre el
    # anfitrión son [x, ángulo en grados] (ver Anfitrion). `sobre` dice cuáles son cuáles.
    puntos: np.ndarray
    secuencia: tuple[str, ...]
    resaltar: tuple[int, int] | None   # índices de puntos de control
    sobre: np.ndarray | None = None    # (N,) True si el punto va sobre el anfitrión


@dataclass(frozen=True)
class Anfitrion:
    """El objeto rígido alrededor del que se ata el nudo.

    Poste: un cilindro horizontal a lo largo de x, con el eje en y = 0. Se apoya sobre la
    cuerda que pasa por debajo, así que su eje queda a la altura radio + 1 (un diámetro de
    cuerda sobre la mesa). Sobre el poste, un punto es [x, ángulo]: el ángulo va en grados
    alrededor del eje, 0 arriba, 90 hacia quien ata, 180 abajo y 270 atrás. Se escribe sin
    volver a 0, de modo que una vuelta completa por arriba va, por ejemplo, de 90 a -270."""
    tipo: str
    radio: float
    desde: float     # extremos del poste a lo largo de x
    hasta: float


@dataclass(frozen=True)
class Segmento:
    puntos: np.ndarray   # (N, 2)
    sobre: bool          # True: [x, ángulo] sobre el anfitrión; False: [x, y] sobre la mesa


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
class Filtro:
    """Una prueba humana de la ficha impresa.
    Filtro 1: Gabriel ata cada paso con cuerda real. Filtro 2: alguien que nunca ha hecho
    el nudo lo ata solo con la ficha. Del probador solo se guardan el rol y un código."""
    filtro: int
    fecha: dt.date
    resultado: str               # «aprobado» o «no aprobado»
    rol: str | None = None       # obligatorio en el filtro 2
    codigo: str | None = None    # obligatorio en el filtro 2
    ficha: str | None = None     # commit de la ficha que se probó


@dataclass(frozen=True)
class Spec:
    slug: str
    nombre: str
    familia: str
    abok: int | None
    encuadre: Encuadre | None
    pasos: tuple[Paso, ...]
    anfitrion: Anfitrion | None = None
    error: Error | None = None
    terminado: Terminado = Terminado()
    # Texto de la ficha. Es opcional al cargar, para poder modelar un nudo antes de
    # escribirlo; la ficha no se genera si falta algo (nudos/ficha.py).
    otros_nombres: tuple[str, ...] = ()
    usos: str | None = None              # para qué sirve
    materiales: str | None = None
    verificacion: tuple[str, ...] = ()   # criterios que se pueden observar en el nudo
    seguridad: str | None = None         # solo cuando aplica
    filtros: tuple[Filtro, ...] = ()


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
    anfitrion = _anfitrion(datos.get("anfitrion"), falla)
    segmentos = _segmentos(datos.get("segmentos"), anfitrion, falla)
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
        anfitrion=anfitrion,
        error=_error(datos.get("error"), pasos, falla),
        terminado=_terminado(datos.get("terminado"), falla),
        otros_nombres=_lista_textos(datos, "otros_nombres", falla),
        usos=_texto_opcional(datos, "usos", falla),
        materiales=_texto_opcional(datos, "materiales", falla),
        verificacion=_lista_textos(datos, "verificacion", falla),
        seguridad=_texto_opcional(datos, "seguridad", falla),
        filtros=_filtros(datos.get("filtros"), falla),
    )


def _filtros(datos, falla) -> tuple[Filtro, ...]:
    if datos is None:
        return ()
    if not isinstance(datos, list):
        raise falla("«filtros» es una lista")
    out = []
    for i, f in enumerate(datos, 1):
        def ff(msg: str) -> SpecError:
            return falla(f"filtro {i}: {msg}")
        if not isinstance(f, dict):
            raise ff("debe ser un mapa")
        sobran = set(f) - _CAMPOS_FILTRO
        if sobran:
            raise ff(f"campos desconocidos: {', '.join(sorted(sobran))}")
        n = f.get("filtro")
        if n not in (1, 2) or isinstance(n, bool):
            raise ff("«filtro» es 1 o 2")
        fecha = f.get("fecha")
        if not isinstance(fecha, dt.date) or isinstance(fecha, dt.datetime):
            raise ff("«fecha» va como AAAA-MM-DD")
        if f.get("resultado") not in RESULTADOS:
            raise ff(f"«resultado» es {' o '.join(RESULTADOS)}")
        rol = _texto_opcional(f, "rol", ff)
        codigo = f.get("codigo")
        if codigo is not None and (not isinstance(codigo, str) or not _CODIGO.match(codigo)):
            raise ff("«codigo» es un código anónimo como P01, nunca un nombre")
        if n == 2 and (rol is None or codigo is None):
            raise ff("en el filtro 2 van el rol y el código del probador")
        ficha = f.get("ficha")
        if ficha is not None and (not isinstance(ficha, str) or not re.fullmatch(r"[0-9a-f]{7,40}", ficha)):
            raise ff("«ficha» es el commit de la ficha que se probó, por ejemplo e1dbffd")
        out.append(Filtro(n, fecha, f["resultado"], rol, codigo, ficha))
    return tuple(out)


def _texto_opcional(datos: dict, clave: str, falla) -> str | None:
    if datos.get(clave) is None:
        return None
    return _texto(datos, clave, falla)


def _lista_textos(datos: dict, clave: str, falla) -> tuple[str, ...]:
    valor = datos.get(clave)
    if valor is None:
        return ()
    if (not isinstance(valor, list) or not valor
            or not all(isinstance(v, str) and v.strip() for v in valor)):
        raise falla(f"«{clave}» es una lista de textos")
    return tuple(" ".join(v.split()) for v in valor)


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


def _anfitrion(datos, falla) -> Anfitrion | None:
    if datos is None:
        return None

    def af(msg: str) -> SpecError:
        return falla(f"anfitrion: {msg}")

    if not isinstance(datos, dict):
        raise af("debe ser un mapa")
    sobran = set(datos) - _CAMPOS_ANFITRION
    if sobran:
        raise af(f"campos desconocidos: {', '.join(sorted(sobran))}")
    if datos.get("tipo") not in TIPOS_ANFITRION:
        raise af(f"«tipo» es uno de: {', '.join(TIPOS_ANFITRION)}")
    numeros = {}
    for clave in ("radio", "desde", "hasta"):
        v = datos.get(clave)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise af(f"falta «{clave}», en diámetros de cuerda")
        numeros[clave] = float(v)
    if numeros["radio"] < 0.5:
        raise af("el radio del poste es de al menos medio diámetro de cuerda")
    if numeros["desde"] >= numeros["hasta"]:
        raise af("«desde» va antes que «hasta»")
    return Anfitrion(datos["tipo"], **numeros)


def _segmentos(datos, anfitrion: Anfitrion | None, falla) -> dict[str, Segmento]:
    if not isinstance(datos, dict) or not datos:
        raise falla("falta el mapa de segmentos")
    out = {}
    for nombre, puntos in datos.items():
        if not isinstance(nombre, str) or not _NOMBRE.match(nombre):
            raise falla(f"segmento «{nombre}»: usa minúsculas, números y guiones")
        sobre = isinstance(puntos, dict)
        if sobre:
            if set(puntos) != {"poste"}:
                raise falla(f"segmento {nombre}: un segmento sobre el anfitrión se escribe "
                            "{poste: [[x, ángulo], ...]}")
            if anfitrion is None:
                raise falla(f"segmento {nombre}: va sobre el poste y la especificación no "
                            "declara «anfitrion»")
            puntos = puntos["poste"]
        try:
            arr = np.asarray(puntos, dtype=float)
        except (TypeError, ValueError):
            arr = None
        if arr is None or arr.ndim != 2 or arr.shape[1] != 2 or len(arr) == 0:
            forma = "[x, ángulo]" if sobre else "[x, y]"
            raise falla(f"segmento {nombre}: los puntos deben ser pares {forma}")
        out[nombre] = Segmento(arr, sobre)
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
        indices = list(range(len(segmentos[nombre].puntos)))[sel]
        if not indices:
            raise pf(f"«{ref}» no tiene puntos")
        partes.append((nombre, indices))

    puntos = np.vstack([segmentos[nombre].puntos[indices] for nombre, indices in partes])
    sobre = np.concatenate([np.full(len(indices), segmentos[nombre].sobre) for nombre, indices in partes])
    if len(puntos) < 2:
        raise pf("el trazado necesita al menos dos puntos")
    # Entre dos puntos sobre el poste, la segunda coordenada son grados: 1° cuenta como
    # 0,02 diámetros, más o menos lo que mide en la superficie de un poste delgado.
    paso_xy = np.diff(puntos, axis=0) * np.where((sobre[1:] & sobre[:-1])[:, None], [1.0, 0.02], 1.0)
    cerca = (np.linalg.norm(paso_xy, axis=1) < DISTANCIA_MIN) & (sobre[1:] == sobre[:-1])
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
        sobre=sobre if sobre.any() else None,
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
            largo = len(segmentos[nombre].puntos)
            original = sel + largo if sel < 0 else sel
            if original not in indices:
                raise pf(f"«{ref}» no está en el tramo de {nombre} que usa este paso")
            return base + indices.index(original)
        base += len(indices)
    raise pf(f"«{ref}»: el segmento {nombre} no está en el trazado de este paso")
