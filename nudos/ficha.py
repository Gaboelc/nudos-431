"""Ficha impresa de un nudo: un pliego de dos páginas tamaño carta, con QR al visor.

Se llena desde la especificación con la plantilla libro/ficha.html y libro/ficha.css,
y Chrome la exporta a PDF. Antes de exportar se comprueba que:
- la especificación tiene todo lo que la ficha necesita;
- ningún término propio de una sección aparece en el texto (config/terminos_seccion.txt);
- nada se sale de las dos páginas.
"""
from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path

import segno

from . import RAIZ, URL_BASE
from .construir import Modelo
from .exportar import SITIO, rellenar
from .imprimir import chrome

LIBRO = RAIZ / "libro"
TERMINOS = RAIZ / "config" / "terminos_seccion.txt"
PASOS_IZQUIERDA = 6   # dos filas de tres en la página izquierda; el resto va en la derecha


class FichaError(Exception):
    """La ficha no se puede generar así."""


def url_visor(slug: str) -> str:
    return f"{URL_BASE}{slug}/"


def faltantes(modelo: Modelo) -> list[str]:
    """Lo que la especificación todavía no tiene y la ficha necesita."""
    s = modelo.spec
    faltan = [campo for campo, valor in (("usos", s.usos), ("materiales", s.materiales),
                                         ("verificacion", s.verificacion), ("error", s.error))
              if not valor]
    if modelo.reverso is None:
        faltan.append("el nudo terminado por detrás (no se pudo construir el último paso)")
    return faltan


def qr_svg(url: str) -> str:
    """QR vectorial con su margen blanco de cuatro módulos, para que se imprima nítido."""
    return segno.make(url, error="m").svg_inline(dark="#000", light="#fff", border=4, omitsize=True)


# --------------------------------------------------------------------------
# Vocabulario
# --------------------------------------------------------------------------
def _normal(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto)
                         if not unicodedata.combining(c))
    return sin_tildes.casefold()


def terminos_de_seccion(ruta: Path = TERMINOS) -> list[str]:
    out = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea:
            out.append(linea)
    return out


def terminos_encontrados(texto: str, terminos: list[str] | None = None) -> list[str]:
    """Los términos de sección que aparecen en el texto, como palabra completa."""
    normal = _normal(texto)
    return [t for t in (terminos if terminos is not None else terminos_de_seccion())
            if re.search(rf"(?<!\w){re.escape(_normal(t))}(?!\w)", normal)]


def texto_visible(documento: str) -> str:
    """El texto que se lee en la ficha: sin etiquetas, estilos ni el dibujo del QR."""
    documento = re.sub(r"<(style|svg)\b.*?</\1>", " ", documento, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", documento))


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------
def html_ficha(modelo: Modelo, imagenes: str = "impresion") -> str:
    """La ficha en HTML. «imagenes» es la carpeta de las imágenes, relativa al HTML."""
    s = modelo.spec
    esc = html.escape
    img = lambda nombre: f'{imagenes}/{nombre}.png'

    def paso(p) -> str:
        return (f'    <figure class="paso"><div class="img"><img src="{img(f"paso-{p.n}")}" alt="">'
                f'<span class="num">{p.n}</span></div><figcaption><span class="t">{esc(p.titulo)}</span>'
                f'{esc(p.texto)}</figcaption></figure>')

    hechos = [("Familia", s.familia), ("Pasos", str(len(s.pasos)))]
    if s.abok is not None:
        hechos.append(("ABOK", f"n.º {s.abok}"))
    e = s.error
    error = (f'    <figure class="panel error"><div class="imgs">'
             f'<div class="img"><img src="{img("error-correcto")}" alt=""><span class="sello bien">Bien</span></div>'
             f'<div class="img"><img src="{img("error")}" alt=""><span class="sello mal">Así no</span></div>'
             f'</div><figcaption><span class="aviso">Error común · paso {e.paso}</span>'
             f'<span class="t">{esc(e.titulo)}</span>{esc(e.texto)}</figcaption></figure>')
    terminado = (f'    <figure class="panel terminado"><div class="imgs">'
                 f'<div class="img"><img src="{img("terminado-frente")}" alt=""><span class="sello">Por delante</span></div>'
                 f'<div class="img"><img src="{img("terminado-reverso")}" alt=""><span class="sello">Por detrás</span></div>'
                 f'</div><figcaption><span class="t">El nudo terminado</span>Por detrás es como lo ves si '
                 f'lo volteas como la página de un libro.</figcaption></figure>')
    verificacion = ('    <section class="verif"><h2>Revisa tu nudo</h2><ul>'
                    + "".join(f"<li>{esc(v)}</li>" for v in s.verificacion) + "</ul></section>")
    seguridad = ("" if not s.seguridad else
                 f'  <section class="seguridad"><h2>Seguridad</h2><p>{esc(s.seguridad)}</p></section>')
    otros = ("" if not s.otros_nombres else
             f'      <p class="otros">También se llama {esc(_y(s.otros_nombres))}.</p>')
    url = url_visor(s.slug)
    css = (LIBRO / "ficha.css").read_text(encoding="utf-8")
    plantilla = (LIBRO / "ficha.html").read_text(encoding="utf-8").replace("{{css}}", css)
    return rellenar(plantilla, {
        "fuentes": (SITIO / "vendor" / "fuentes").as_uri(),
        "nombre": esc(s.nombre),
        "otros_nombres": otros,
        "hechos": "\n".join(f"        <div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in hechos),
        "usos": esc(s.usos),
        "materiales": esc(s.materiales),
        "qr": "      " + qr_svg(url),
        "url_corta": esc(url.removeprefix("https://").rstrip("/")),
        "pasos_izq": "\n".join(paso(p) for p in s.pasos[:PASOS_IZQUIERDA]),
        "pasos_der": "\n".join(paso(p) for p in s.pasos[PASOS_IZQUIERDA:]),
        "error": error,
        "terminado": terminado,
        "verificacion": verificacion,
        "seguridad": seguridad,
    })


def _y(nombres) -> str:
    nombres = list(nombres)
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " o " + nombres[-1]


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------
def ficha(modelo: Modelo, carpeta: Path) -> Path:
    """Escribe carpeta/ficha.pdf (y ficha.html, para revisarla). Las imágenes tienen que
    estar ya en carpeta/impresion: las genera nudos.imprimir."""
    faltan = faltantes(modelo)
    if faltan:
        raise FichaError(f"{modelo.spec.slug}: a la especificación le falta {', '.join(faltan)}.")
    if modelo.fallas:
        raise FichaError("El nudo tiene fallas; no se genera la ficha:\n"
                         + "\n".join(f"  - {f}" for f in modelo.fallas))
    documento = html_ficha(modelo)
    encontrados = terminos_encontrados(texto_visible(documento))
    if encontrados:
        raise FichaError("La ficha usa términos propios de una sección, que solo van en los anexos: "
                         + ", ".join(encontrados))
    origen = carpeta / "ficha.html"
    origen.write_text(documento, encoding="utf-8")
    destino = carpeta / "ficha.pdf"
    with chrome() as navegador:
        pagina = navegador.new_page()
        pagina.goto(origen.as_uri(), wait_until="load")
        pagina.evaluate("document.fonts.ready.then(() => true)")
        estado = pagina.evaluate("""() => ({
            sinCargar: [...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.getAttribute('src')),
            desbordes: [...document.querySelectorAll('.pagina')].map((p, k) =>
                p.scrollHeight > p.clientHeight + 1 || p.scrollWidth > p.clientWidth + 1 ? k + 1 : 0).filter(Boolean),
        })""")
        if estado["sinCargar"]:
            raise FichaError("Faltan imágenes: " + ", ".join(estado["sinCargar"])
                             + ". Corre primero: python -m nudos imprimir " + modelo.spec.slug)
        if estado["desbordes"]:
            raise FichaError("El contenido no cabe en la página "
                             + " y ".join(map(str, estado["desbordes"])) + " del pliego.")
        pagina.pdf(path=str(destino), prefer_css_page_size=True, print_background=True)
    return destino
