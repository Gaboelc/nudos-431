"""Especificación de un nudo: lectura y validación de `specs/<slug>.yaml`.

El formato está descrito en `docs/formato-spec.md`.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import yaml

from . import SPECS
from .cruces import SecuenciaError, leer_secuencias
from .plantillas import TIPOS as TIPOS_PLANTILLA

_NOMBRE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REF = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)(?:\[([^\]]*)\])?$")
DISTANCIA_MIN = 0.05   # entre puntos de control seguidos, en diámetros
# Código anónimo de un probador: letras y números, como P01. Así no cabe un nombre.
_CODIGO = re.compile(r"^[A-Z]{1,3}[0-9]{2,3}$")
RESULTADOS = ("aprobado", "no aprobado")
# Estado de producción, en el orden en que avanza (nudos/estado.py).
ESTADOS = ("borrador", "modelado", "cuerda-ok", "novato-ok", "publicado")

_CAMPOS = {"slug", "nombre", "otros_nombres", "familia", "abok", "usos", "materiales",
           "verificacion", "precauciones", "alternativas", "seguridad", "encuadre", "anfitrion",
           "cuerdas", "segmentos", "plantilla", "pasos", "error", "terminado", "filtros",
           "estado"}
_CAMPOS_ALTERNATIVA = {"nudo", "cuando"}
_CAMPOS_PASO = {"titulo", "texto", "trazado", "secuencia", "resaltar"}
_CAMPOS_PASO_PLANTILLA = {"titulo", "texto", "hasta"}
_CAMPOS_ERROR = {"paso", "invierte", "variante", "titulo", "texto", "encuadre", "otros"}
_CAMPOS_OTRO_ERROR = {"titulo", "texto"}
_CAMPOS_TERMINADO = {"encuadre"}
_CAMPOS_FILTRO = {"filtro", "fecha", "resultado", "rol", "codigo", "ficha"}
# Campos de cada tipo de anfitrión, además de «tipo»; todos son medidas en diámetros.
_MEDIDAS_ANFITRION = {"poste": ("radio", "desde", "hasta"), "cruz": ("radio", "largo"),
                      "tubo": ("radio", "largo")}
TIPOS_ANFITRION = tuple(_MEDIDAS_ANFITRION)
# Los anfitriones que solo se usan con una plantilla, con la plantilla de ejemplo.
_SOLO_CON_PLANTILLA = {"cruz": "amarre-cuadrado", "tubo": "cabeza-de-turco"}
# Cómo se nombra el anfitrión en los mensajes.
_DEL_ANFITRION = {"poste": "del poste", "cruz": "de los palos", "tubo": "del tubo"}
# Una medida de la plantilla dentro del texto, como {vueltas}.
_MEDIDA = re.compile(r"\{([^{}]*)\}")
_CAMPOS_CUERDA = {"nombre", "grosor", "color"}
# Colores de cuerda de render/escena.js. El ámbar no está: es el del tramo que se mueve.
# Azul y crema siguen distinguiéndose en gris (oscuro y claro, con el ámbar en medio).
COLORES = ("azul", "crema")


class SpecError(ValueError):
    """La especificación tiene un error. El mensaje dice dónde."""


@dataclass(frozen=True)
class Paso:
    n: int
    titulo: str
    texto: str
    # (N, 2) puntos de control, en orden de la cuerda. Sobre la mesa son [x, y]; sobre el
    # anfitrión son [x, ángulo en grados] (ver Anfitrion). `sobre` dice cuáles son cuáles.
    # Con varias cuerdas van una tras otra, en el orden de Spec.cuerdas; `cuerda` dice de cuál es cada punto.
    puntos: np.ndarray
    # Con varias cuerdas, las secuencias de todas, una tras otra en el mismo orden;
    # `pasadas` dice cuántos pasos por cruces lleva cada una.
    secuencia: tuple[str, ...]
    resaltar: tuple[int, int] | None   # índices de puntos de control, de una misma cuerda
    sobre: np.ndarray | None = None    # (N,) True si el punto va sobre el anfitrión
    cuerda: np.ndarray | None = None   # (N,) índice en Spec.cuerdas; None con una sola cuerda
    pasadas: tuple[int, ...] | None = None
    # En un nudo de plantilla, hasta dónde llega el paso (un hito de la plantilla). Ahí no
    # hay puntos de control ni secuencia: `puntos` queda vacío y la plantilla calcula la cuerda.
    hasta: str | None = None


@dataclass(frozen=True)
class Cuerda:
    """Una de las cuerdas de un nudo de varias. Cada una se recorre desde su firme."""
    nombre: str
    grosor: float   # diámetro, relativo al de la cuerda de siempre, que mide 1
    color: str      # uno de COLORES


@dataclass(frozen=True)
class Anfitrion:
    """El objeto rígido alrededor del que se ata el nudo.

    Poste: un cilindro horizontal a lo largo de x, con el eje en y = 0. Se apoya sobre la
    cuerda que pasa por debajo, así que su eje queda a la altura radio + 1 (un diámetro de
    cuerda sobre la mesa). Sobre el poste, un punto es [x, ángulo]: el ángulo va en grados
    alrededor del eje, 0 arriba, 90 hacia quien ata, 180 abajo y 270 atrás. Se escribe sin
    volver a 0, de modo que una vuelta completa por arriba va, por ejemplo, de 90 a -270.

    Cruz: dos palos del mismo radio, cruzados en ángulo recto en x = y = 0, para los
    amarres. El de abajo va a lo largo de y y se apoya en la cuerda que pasa por debajo,
    con el eje a la altura radio + 1, como el poste. El de arriba va a lo largo de x y se
    apoya sobre el de abajo. Cada palo mide `largo` y está centrado en el cruce.

    Tubo: un cilindro horizontal a lo largo de x, centrado en x = 0 y con el eje en y = 0,
    para la cabeza de turco. El nudo lo rodea entero y se apoya sobre él: debajo de cada
    cruce hay dos capas de cuerda, así que el eje queda a la altura radio + 2. Mide `largo`."""
    tipo: str
    radio: float
    desde: float | None = None   # poste: extremos a lo largo de x
    hasta: float | None = None
    largo: float | None = None   # cruz: largo de cada palo; tubo: su largo


@dataclass(frozen=True)
class Segmento:
    puntos: np.ndarray   # (N, 2)
    sobre: bool          # True: [x, ángulo] sobre el anfitrión; False: [x, y] sobre la mesa


@dataclass(frozen=True)
class Encuadre:
    x: tuple[float, float]
    y: tuple[float, float]


@dataclass(frozen=True)
class OtroError:
    """Un error común que no se ve en una imagen, como no mantener la cuerda tensa."""
    titulo: str
    texto: str


@dataclass(frozen=True)
class Error:
    """El error más común: un paso con algunos cruces invertidos o, en un nudo de
    plantilla, una variante del método que la plantilla sabe construir."""
    paso: int
    invierte: tuple[str, ...]          # etiquetas de los cruces que quedan al revés
    titulo: str
    texto: str
    encuadre: Encuadre | None          # zona que se muestra del error y del paso correcto
    variante: str | None = None        # solo en un nudo de plantilla; entonces `invierte` va vacío
    otros: tuple[OtroError, ...] = ()  # errores comunes sin imagen


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
class Alternativa:
    """Otro nudo que conviene en lugar de este, y cuándo."""
    nudo: str
    cuando: str


@dataclass(frozen=True)
class Spec:
    slug: str
    nombre: str
    familia: str
    abok: int | None
    encuadre: Encuadre | None
    pasos: tuple[Paso, ...]
    anfitrion: Anfitrion | None = None
    cuerdas: tuple[Cuerda, ...] = ()   # vacío en un nudo de una sola cuerda
    plantilla: object | None = None    # una de nudos/plantillas; None en un nudo de segmentos
    error: Error | None = None
    terminado: Terminado = Terminado()
    # Texto de la ficha. Es opcional al cargar, para poder modelar un nudo antes de
    # escribirlo; la ficha no se genera si falta algo (nudos/ficha.py).
    otros_nombres: tuple[str, ...] = ()
    usos: str | None = None              # para qué sirve
    materiales: str | None = None
    verificacion: tuple[str, ...] = ()   # criterios que se pueden observar en el nudo
    precauciones: tuple[str, ...] = ()   # cuidados y peligros al usarlo
    alternativas: tuple[Alternativa, ...] = ()
    seguridad: str | None = None         # solo cuando aplica
    filtros: tuple[Filtro, ...] = ()
    estado: str = "borrador"             # uno de ESTADOS; sin «estado», borrador


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
    cuerdas = _cuerdas(datos.get("cuerdas"), falla)
    if cuerdas and anfitrion is not None:
        # Se agrega con el primer nudo de varias cuerdas que se ate sobre un anfitrión.
        raise falla("por ahora, un nudo de varias cuerdas no lleva anfitrión")
    plantilla = _plantilla(datos.get("plantilla"), anfitrion, cuerdas, falla)
    pasos = datos.get("pasos")
    if not isinstance(pasos, list) or not pasos:
        raise falla("falta la lista de pasos")
    if plantilla is None:
        if anfitrion is not None and anfitrion.tipo in _SOLO_CON_PLANTILLA:
            raise falla(f"el anfitrión {anfitrion.tipo} va con una plantilla, como "
                        f"{_SOLO_CON_PLANTILLA[anfitrion.tipo]}")
        segmentos = _segmentos(datos.get("segmentos"), anfitrion, falla)
        duenos: dict[str, tuple[int, int]] = {}
        pasos = tuple(_paso(i + 1, p, segmentos, cuerdas, duenos, falla) for i, p in enumerate(pasos))
    else:
        if "segmentos" in datos:
            raise falla("un nudo de plantilla no lleva «segmentos»: la plantilla calcula la cuerda")
        pasos = _pasos_plantilla(pasos, plantilla, falla)
    spec = Spec(
        slug=slug,
        nombre=_texto(datos, "nombre", falla),
        familia=_texto(datos, "familia", falla),
        abok=abok,
        encuadre=_encuadre(datos.get("encuadre"), falla),
        pasos=pasos,
        anfitrion=anfitrion,
        cuerdas=cuerdas,
        plantilla=plantilla,
        error=_error(datos.get("error"), pasos, plantilla, falla),
        terminado=_terminado(datos.get("terminado"), falla),
        otros_nombres=_lista_textos(datos, "otros_nombres", falla),
        usos=_texto_opcional(datos, "usos", falla),
        materiales=_texto_opcional(datos, "materiales", falla),
        verificacion=_lista_textos(datos, "verificacion", falla),
        precauciones=_lista_textos(datos, "precauciones", falla),
        alternativas=_alternativas(datos.get("alternativas"), falla),
        seguridad=_texto_opcional(datos, "seguridad", falla),
        filtros=_filtros(datos.get("filtros"), falla),
        estado=_estado(datos.get("estado"), falla),
    )
    return spec if plantilla is None else _con_medidas(spec, plantilla.medidas(), falla)


def _plantilla(datos, anfitrion: Anfitrion | None, cuerdas: tuple[Cuerda, ...], falla):
    if datos is None:
        return None

    def pf(msg: str) -> SpecError:
        return falla(f"plantilla: {msg}")

    if not isinstance(datos, dict):
        raise pf("debe ser un mapa con «tipo» y las medidas de la plantilla")
    clase = TIPOS_PLANTILLA.get(datos.get("tipo"))
    if clase is None:
        raise pf(f"«tipo» es uno de: {', '.join(TIPOS_PLANTILLA)}")
    plantilla = clase.leer(datos, pf)
    if anfitrion is None or anfitrion.tipo != clase.ANFITRION:
        raise pf(f"la plantilla {clase.tipo} va sobre el anfitrión {clase.ANFITRION}")
    if cuerdas:
        raise pf("por ahora, un nudo de plantilla es de una sola cuerda")
    return plantilla


def _pasos_plantilla(datos: list, plantilla, falla) -> tuple[Paso, ...]:
    """Cada paso dice `hasta` dónde llega; tienen que avanzar por la cuerda y el último
    llega al final. Los puntos y la secuencia los calcula la plantilla."""
    hitos = plantilla.hitos()
    pasos: list[Paso] = []
    for n, p in enumerate(datos, 1):
        def pf(msg: str) -> SpecError:
            return falla(f"paso {n}: {msg}")
        if not isinstance(p, dict):
            raise pf("debe ser un mapa")
        ajenos = sorted(set(p) & {"trazado", "secuencia", "resaltar"})
        if ajenos:
            raise pf(f"en un nudo de plantilla, el paso no lleva «{ajenos[0]}»: la plantilla "
                     "lo calcula desde «hasta»")
        sobran = set(p) - _CAMPOS_PASO_PLANTILLA
        if sobran:
            raise pf(f"campos desconocidos: {', '.join(sorted(sobran))}")
        hasta = p.get("hasta")
        if not isinstance(hasta, str) or hasta not in hitos:
            raise pf(f"«hasta» es uno de: {', '.join(hitos)}")
        if pasos and hitos[hasta] <= hitos[pasos[-1].hasta]:
            raise pf(f"«hasta: {hasta}» no avanza; el paso {n - 1} ya llega a {pasos[-1].hasta}")
        pasos.append(Paso(n=n, titulo=_texto(p, "titulo", pf), texto=_texto(p, "texto", pf),
                          puntos=np.empty((0, 2)), secuencia=(), resaltar=None, hasta=hasta))
    final = max(hitos, key=hitos.get)
    if hitos[pasos[-1].hasta] != hitos[final]:
        raise falla(f"paso {len(pasos)}: el último paso llega a «{final}», el final de la cuerda")
    return tuple(pasos)


def _con_medidas(spec: Spec, medidas: dict[str, str], falla) -> Spec:
    """Reemplaza {vueltas} y las demás medidas de la plantilla en todo el texto, en letras."""
    def poner(texto: str | None) -> str | None:
        if texto is None:
            return None

        def una(m: re.Match) -> str:
            if m.group(1) not in medidas:
                raise falla(f"«{m.group(0)}» no es una medida de la plantilla; puede ser "
                            + " o ".join(f"{{{k}}}" for k in medidas))
            return medidas[m.group(1)]
        return _MEDIDA.sub(una, texto)

    error = spec.error
    if error is not None:
        error = replace(error, titulo=poner(error.titulo), texto=poner(error.texto),
                        otros=tuple(OtroError(poner(o.titulo), poner(o.texto)) for o in error.otros))
    return replace(
        spec,
        pasos=tuple(replace(p, titulo=poner(p.titulo), texto=poner(p.texto)) for p in spec.pasos),
        error=error,
        usos=poner(spec.usos),
        materiales=poner(spec.materiales),
        verificacion=tuple(map(poner, spec.verificacion)),
        precauciones=tuple(map(poner, spec.precauciones)),
        alternativas=tuple(replace(a, cuando=poner(a.cuando)) for a in spec.alternativas),
        seguridad=poner(spec.seguridad),
    )


def _alternativas(datos, falla) -> tuple[Alternativa, ...]:
    if datos is None:
        return ()
    if not isinstance(datos, list) or not datos:
        raise falla("«alternativas» es una lista de otros nudos, cada uno con «nudo» y «cuando»")
    out = []
    for i, a in enumerate(datos, 1):
        def af(msg: str) -> SpecError:
            return falla(f"alternativa {i}: {msg}")
        if not isinstance(a, dict):
            raise af("debe ser un mapa con «nudo» y «cuando»")
        sobran = set(a) - _CAMPOS_ALTERNATIVA
        if sobran:
            raise af(f"campos desconocidos: {', '.join(sorted(sobran))}")
        out.append(Alternativa(_texto(a, "nudo", af), " ".join(_texto(a, "cuando", af).split())))
    return tuple(out)


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


def _estado(datos, falla) -> str:
    if datos is None:
        return "borrador"
    if datos not in ESTADOS:
        raise falla(f"«estado» es {', '.join(ESTADOS[:-1])} o {ESTADOS[-1]}")
    return datos


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


def _error(datos, pasos: tuple[Paso, ...], plantilla, falla) -> Error | None:
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
    variante = None
    etiquetas: tuple[str, ...] = ()
    if plantilla is None:
        if "variante" in datos:
            raise ef("«variante» es el error de un nudo de plantilla; aquí los cruces al revés "
                     "van en «invierte»")
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
    else:
        if "invierte" in datos:
            raise ef("en un nudo de plantilla, el error es una «variante» del método, no "
                     "cruces al revés")
        variante = datos.get("variante")
        if not plantilla.VARIANTES:
            raise ef(f"con estas medidas, la plantilla {plantilla.tipo} no sabe construir "
                     "ningún error común")
        if not isinstance(variante, str) or variante not in plantilla.VARIANTES:
            raise ef(f"«variante» es una de: {', '.join(plantilla.VARIANTES)}")
        desde, hitos = plantilla.VARIANTES[variante], plantilla.hitos()
        if hitos[pasos[n - 1].hasta] < hitos[desde]:
            raise ef(f"la variante {variante} se ve desde «{desde}», y el paso {n} llega "
                     f"solo a {pasos[n - 1].hasta}")
    return Error(
        paso=n,
        invierte=etiquetas,
        titulo=_texto(datos, "titulo", ef),
        texto=_texto(datos, "texto", ef),
        encuadre=_encuadre(datos.get("encuadre"), ef),
        variante=variante,
        otros=_otros_errores(datos.get("otros"), ef),
    )


def _otros_errores(datos, falla) -> tuple[OtroError, ...]:
    if datos is None:
        return ()
    if not isinstance(datos, list) or not datos:
        raise falla("«otros» es una lista de errores sin imagen, cada uno con «titulo» y «texto»")
    out = []
    for i, o in enumerate(datos, 1):
        def of(msg: str) -> SpecError:
            return falla(f"otro error {i}: {msg}")
        if not isinstance(o, dict):
            raise of("debe ser un mapa con «titulo» y «texto»")
        sobran = set(o) - _CAMPOS_OTRO_ERROR
        if sobran:
            raise of(f"campos desconocidos: {', '.join(sorted(sobran))}")
        out.append(OtroError(_texto(o, "titulo", of), _texto(o, "texto", of)))
    return tuple(out)


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
    tipo = datos.get("tipo")
    if tipo not in TIPOS_ANFITRION:
        raise af(f"«tipo» es uno de: {', '.join(TIPOS_ANFITRION)}")
    sobran = set(datos) - {"tipo", *_MEDIDAS_ANFITRION[tipo]}
    if sobran:
        raise af(f"campos desconocidos: {', '.join(sorted(sobran))}")
    numeros = {}
    for clave in _MEDIDAS_ANFITRION[tipo]:
        v = datos.get(clave)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise af(f"falta «{clave}», en diámetros de cuerda")
        numeros[clave] = float(v)
    if numeros["radio"] < 0.5:
        raise af(f"el radio {_DEL_ANFITRION[tipo]} es de al menos medio diámetro de cuerda")
    if tipo == "poste" and numeros["desde"] >= numeros["hasta"]:
        raise af("«desde» va antes que «hasta»")
    if tipo == "cruz" and numeros["largo"] <= 2 * numeros["radio"]:
        raise af("«largo» es el largo de cada palo; tiene que ser mayor que su grosor")
    if tipo == "tubo" and numeros["largo"] <= 2 * numeros["radio"]:
        raise af("«largo» es el largo del tubo; tiene que ser mayor que su grosor")
    return Anfitrion(tipo, **numeros)


def _cuerdas(datos, falla) -> tuple[Cuerda, ...]:
    if datos is None:
        return ()
    if not isinstance(datos, list) or len(datos) < 2:
        raise falla("«cuerdas» es la lista de las cuerdas de un nudo de dos o más; un nudo "
                    "de una sola cuerda no lo lleva")
    out: list[Cuerda] = []
    for i, c in enumerate(datos, 1):
        def cf(msg: str) -> SpecError:
            return falla(f"cuerda {i}: {msg}")
        if not isinstance(c, dict):
            raise cf("debe ser un mapa con nombre, grosor y color")
        sobran = set(c) - _CAMPOS_CUERDA
        if sobran:
            raise cf(f"campos desconocidos: {', '.join(sorted(sobran))}")
        nombre = c.get("nombre")
        if not isinstance(nombre, str) or not _NOMBRE.match(nombre):
            raise cf("«nombre» usa minúsculas, números y guiones, como gruesa")
        if any(o.nombre == nombre for o in out):
            raise cf(f"ya hay una cuerda que se llama {nombre}")
        grosor = c.get("grosor")
        if not isinstance(grosor, (int, float)) or isinstance(grosor, bool) or grosor <= 0:
            raise cf("«grosor» es el diámetro de la cuerda: 1 es la de siempre, 1.5 una más gruesa")
        color = c.get("color")
        if color not in COLORES:
            raise cf(f"«color» es uno de: {', '.join(COLORES)}")
        if any(o.color == color for o in out):
            raise cf(f"la cuerda {nombre} tiene el mismo color que otra; cada cuerda lleva el suyo")
        out.append(Cuerda(nombre, float(grosor), color))
    return tuple(out)


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


def _paso(n: int, datos, segmentos: dict[str, Segmento], cuerdas: tuple[Cuerda, ...],
          duenos: dict[str, tuple[int, int]], falla) -> Paso:
    """`duenos` guarda, de un paso al siguiente, en qué cuerda y en qué paso apareció por
    primera vez cada segmento: un segmento es un tramo de una cuerda y no cambia de cuerda."""
    def pf(msg: str) -> SpecError:
        return falla(f"paso {n}: {msg}")

    if not isinstance(datos, dict):
        raise pf("debe ser un mapa")
    sobran = set(datos) - _CAMPOS_PASO
    if sobran:
        raise pf(f"campos desconocidos: {', '.join(sorted(sobran))}")
    nombres = [c.nombre for c in cuerdas]
    trazado = _por_cuerda(datos.get("trazado"), "trazado", nombres, pf)

    # (segmento, índices de sus puntos, índice de la cuerda), en el orden de la cuerda.
    partes: list[tuple[str, list[int], int]] = []
    for k, lista in enumerate(trazado):
        de = f" de la cuerda {nombres[k]}" if cuerdas else ""
        if not isinstance(lista, list) or not lista:
            raise pf(f"falta el trazado{de}")
        antes = len(partes)
        for ref in lista:
            nombre, sel = _ref(ref, pf)
            if nombre not in segmentos:
                raise pf(f"el segmento «{nombre}» no existe")
            if isinstance(sel, int):
                raise pf(f"«{ref}»: en el trazado va un segmento o un tramo [a:b], no un punto")
            if any(nombre == usado for usado, _, _ in partes):
                raise pf(f"el segmento {nombre} aparece dos veces")
            indices = list(range(len(segmentos[nombre].puntos)))[sel]
            if not indices:
                raise pf(f"«{ref}» no tiene puntos")
            if cuerdas:
                k0, n0 = duenos.setdefault(nombre, (k, n))
                if k0 != k:
                    raise pf(f"el segmento {nombre} va en la cuerda {nombres[k0]} en el paso {n0} "
                             f"y aquí en la cuerda {nombres[k]}; un segmento es de una sola cuerda")
            partes.append((nombre, indices, k))
        if sum(len(indices) for _, indices, _ in partes[antes:]) < 2:
            raise pf(f"el trazado{de} necesita al menos dos puntos")

    puntos = np.vstack([segmentos[nombre].puntos[indices] for nombre, indices, _ in partes])
    sobre = np.concatenate([np.full(len(indices), segmentos[nombre].sobre) for nombre, indices, _ in partes])
    cuerda = np.concatenate([np.full(len(indices), k) for _, indices, k in partes])
    # Entre dos puntos sobre el poste, la segunda coordenada son grados: 1° cuenta como
    # 0,02 diámetros, más o menos lo que mide en la superficie de un poste delgado.
    paso_xy = np.diff(puntos, axis=0) * np.where((sobre[1:] & sobre[:-1])[:, None], [1.0, 0.02], 1.0)
    cerca = ((np.linalg.norm(paso_xy, axis=1) < DISTANCIA_MIN) & (sobre[1:] == sobre[:-1])
             & (cuerda[1:] == cuerda[:-1]))
    if cerca.any():
        p = puntos[int(np.argmax(cerca))]
        raise pf(f"hay dos puntos seguidos casi iguales cerca de ({p[0]:g}, {p[1]:g})")

    if "secuencia" not in datos:
        raise pf("falta «secuencia» (escribe \"\" si el paso no tiene cruces)")
    if cuerdas:
        textos = dict(zip(nombres, _por_cuerda(datos["secuencia"], "secuencia", nombres, pf)))
        for nombre, texto in textos.items():
            if not isinstance(texto, str):
                raise pf(f"falta la secuencia de la cuerda {nombre} (escribe \"\" si no pasa por cruces)")
    else:
        textos = {"": str(datos["secuencia"])}
    try:
        leidas = leer_secuencias(textos)
    except SecuenciaError as e:
        raise pf(str(e)) from None

    return Paso(
        n=n,
        titulo=_texto(datos, "titulo", pf),
        texto=_texto(datos, "texto", pf),
        puntos=puntos,
        secuencia=tuple(t for sec in leidas.values() for t in sec),
        resaltar=_resaltar(datos.get("resaltar"), partes, segmentos, cuerda, pf),
        sobre=sobre if sobre.any() else None,
        cuerda=cuerda if cuerdas else None,
        pasadas=tuple(len(sec) for sec in leidas.values()) if cuerdas else None,
    )


def _por_cuerda(valor, campo: str, nombres: list[str], pf) -> list:
    """El trazado o la secuencia de un paso, como lista con un valor por cuerda. Con una
    sola cuerda (`nombres` vacío) es el valor tal cual; con varias, un mapa por cuerda."""
    if not nombres:
        if isinstance(valor, dict):
            raise pf(f"«{campo}» va por cuerda solo cuando el nudo declara «cuerdas»")
        return [valor]
    if not isinstance(valor, dict):
        ejemplo = ", ".join(f"{c}: [...]" if campo == "trazado" else f'{c}: "..."' for c in nombres)
        raise pf(f"con varias cuerdas, «{campo}» es un mapa por cuerda: {{{ejemplo}}}")
    sobran = [c for c in valor if c not in nombres]
    if sobran:
        raise pf(f"en «{campo}», la cuerda «{sobran[0]}» no existe")
    faltan = [c for c in nombres if c not in valor]
    if faltan:
        raise pf(f"falta «{campo}» de la cuerda {faltan[0]}; cada paso lleva todas las cuerdas")
    return [valor[c] for c in nombres]


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


def _resaltar(datos, partes, segmentos, cuerda: np.ndarray, pf) -> tuple[int, int] | None:
    """Con varias cuerdas, el tramo resaltado va en una sola y «fin» es el último punto
    de la cuerda donde empieza."""
    if datos is None:
        return None
    if not isinstance(datos, dict) or set(datos) != {"desde", "hasta"}:
        raise pf("resaltar lleva «desde» y «hasta»")
    varias = len(set(cuerda.tolist())) > 1
    if varias and datos["desde"] == "fin":
        raise pf("en resaltar, «desde» es un punto de una cuerda, como segmento[0]; «fin» va en «hasta»")
    a = _punto(datos["desde"], partes, segmentos, len(cuerda) - 1, pf)
    fin = int(np.nonzero(cuerda == cuerda[a])[0][-1])
    b = _punto(datos["hasta"], partes, segmentos, fin, pf)
    if cuerda[b] != cuerda[a]:
        raise pf("en resaltar, «desde» y «hasta» van en la misma cuerda")
    if b <= a:
        raise pf("en resaltar, «hasta» debe ir después de «desde»")
    return a, b


def _punto(ref, partes, segmentos, fin: int, pf) -> int:
    """Índice, dentro del paso, del punto al que apunta una referencia. `fin` es el
    índice al que apunta «fin»."""
    if ref == "fin":
        return fin
    nombre, sel = _ref(ref, pf)
    if not isinstance(sel, int):
        raise pf(f"«{ref}»: en resaltar va un punto, como segmento[0] o segmento[-1]")
    base = 0
    for usado, indices, _ in partes:
        if usado == nombre:
            largo = len(segmentos[nombre].puntos)
            original = sel + largo if sel < 0 else sel
            if original not in indices:
                raise pf(f"«{ref}» no está en el tramo de {nombre} que usa este paso")
            return base + indices.index(original)
        base += len(indices)
    raise pf(f"«{ref}»: el segmento {nombre} no está en el trazado de este paso")
