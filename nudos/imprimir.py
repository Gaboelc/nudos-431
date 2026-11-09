"""Imágenes de impresión de un nudo, a 300 ppp en su tamaño impreso.

Salen de la misma escena 3D del visor (render/escena.js), dibujada con Chrome sin
interfaz y con WebGL por software (SwiftShader), para que construir dos veces dé
exactamente las mismas imágenes, píxel por píxel, en cualquier computadora con la misma
versión de Chrome. Con otra versión de Pillow cambian los bytes del PNG, no los píxeles.

Para cada nudo se generan, en build/<slug>/impresion/:
- paso-<n>.png: cada paso, con el tramo que se mueve resaltado y los nombres.
- error-correcto.png y error.png: el paso del error común, bien y mal, con el mismo encuadre.
- terminado-frente.png y terminado-reverso.png: el nudo terminado por delante y por detrás.
- prueba.pdf: página de prueba en tamaño carta, en color y en escala de grises, para
  imprimirla en casa y revisar que se distinga qué tramo va encima en cada cruce.
"""
from __future__ import annotations

import functools
import html
import http.server
import io
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

from . import RAIZ
from .construir import Modelo
from .exportar import ESCENA, SITIO, datos_escena
from .spec import Encuadre

PPP = 300
# Tamaño impreso de cada imagen: una celda de la rejilla de tres columnas de la ficha
# (libro/ficha.css). Si cambia, cambia también allí.
CELDA_MM = (58.0, 64.0)
VISTA_PASOS = "3d"         # la vista de quien ata sentado a la mesa
VISTA_TERMINADO = "arriba"
# Sobre un anfitrión el nudo no se voltea: se mira por delante y desde el otro lado.
VISTAS_TERMINADO_ANFITRION = ("3d", "detras")
ESQUINA_PASO = (11.0, 11.0)    # el número del paso (libro/ficha.css, .num)
ESQUINA_SELLO = (26.0, 7.0)    # «Bien», «Así no», «Por delante», «Por detrás» (.sello)
PAGINA = RAIZ / "render" / "impresion.html"
GUION = RAIZ / "render" / "impresion.js"
ARGUMENTOS_CHROME = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                     "--ignore-gpu-blocklist", "--font-render-hinting=none"]


class ImpresionError(Exception):
    """No se pudieron generar las imágenes de impresión."""


@dataclass(frozen=True)
class Imagen:
    nombre: str          # nombre del archivo, sin extensión
    titulo: str          # para la página de prueba
    escena: dict         # datos para escena.js
    indice: int          # qué paso de la escena se dibuja, desde 1
    vista: str
    resaltar: bool
    nombres: tuple[str, ...] = field(default=("firme", "chicote"))
    # Esquina superior izquierda (ancho, alto en mm) que la ficha tapa con el número del
    # paso o con un sello. Ahí no se ponen los nombres.
    reservado_mm: tuple[float, float] = (0.0, 0.0)


def px(mm: float) -> int:
    return round(mm / 25.4 * PPP)


def espejo(e: Encuadre | None) -> Encuadre | None:
    """El encuadre del nudo volteado sobre el eje y."""
    return None if e is None else Encuadre((-e.x[1], -e.x[0]), e.y)


def imagenes(modelo: Modelo) -> list[Imagen]:
    """Las imágenes de la ficha de un nudo."""
    s = modelo.spec
    a = s.anfitrion
    pasos = datos_escena(s.slug, s.encuadre, modelo.pasos, a)
    out = [Imagen(f"paso-{r.n}", f"Paso {r.n}", pasos, i + 1, VISTA_PASOS, True,
                  reservado_mm=ESQUINA_PASO)
           for i, r in enumerate(modelo.pasos)]
    if modelo.error is not None:
        e = s.error
        correcto = next(r for r in modelo.pasos if r.n == e.paso)
        par = datos_escena(s.slug, e.encuadre or s.encuadre, [correcto, modelo.error], a)
        out.append(Imagen("error-correcto", f"Paso {e.paso}, bien", par, 1, VISTA_PASOS, True,
                          ("firme",), ESQUINA_SELLO))
        out.append(Imagen("error", f"Error: {e.titulo}", par, 2, VISTA_PASOS, True,
                          ("firme",), ESQUINA_SELLO))
    enc = s.terminado.encuadre or s.encuadre
    if a is not None:
        final = datos_escena(s.slug, enc, [modelo.pasos[-1]], a)
        delante, detras = VISTAS_TERMINADO_ANFITRION
        out.append(Imagen("terminado-frente", "Terminado, por delante", final, 1, delante, False,
                          reservado_mm=ESQUINA_SELLO))
        out.append(Imagen("terminado-reverso", "Terminado, por detrás", final, 1, detras, False,
                          reservado_mm=ESQUINA_SELLO))
        return out
    out.append(Imagen("terminado-frente", "Terminado, por delante",
                      datos_escena(s.slug, enc, [modelo.pasos[-1]]), 1, VISTA_TERMINADO, False,
                      reservado_mm=ESQUINA_SELLO))
    if modelo.reverso is not None:
        out.append(Imagen("terminado-reverso", "Terminado, por detrás",
                          datos_escena(s.slug, espejo(enc), [modelo.reverso]), 1, VISTA_TERMINADO, False,
                          reservado_mm=ESQUINA_SELLO))
    return out


def imprimir(modelo: Modelo, destino: Path, extra: list[Imagen] | None = None) -> list[Path]:
    """Genera las imágenes en «destino» y devuelve sus rutas. «extra» son imágenes
    adicionales que solo se guardan, como las de la página de prueba."""
    if modelo.fallas:
        raise ImpresionError("El nudo tiene fallas; no se imprime:\n"
                             + "\n".join(f"  - {f}" for f in modelo.fallas))
    return dibujar(imagenes(modelo) + (extra or []), destino)


def dibujar(lista: list[Imagen], destino: Path) -> list[Path]:
    """Dibuja cada imagen en destino/<nombre>.png, al tamaño de CELDA_MM y a PPP."""
    destino.mkdir(parents=True, exist_ok=True)
    ancho, alto = px(CELDA_MM[0]), px(CELDA_MM[1])
    rutas = []
    with _servidor() as base, chrome() as navegador:
        for img in lista:
            png = _dibujar(navegador, base, img, ancho, alto)
            ruta = destino / f"{img.nombre}.png"
            _guardar(Image.open(io.BytesIO(png)), ruta)
            rutas.append(ruta)
    return rutas


def _guardar(im: Image.Image, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(ruta, dpi=(PPP, PPP))


@contextmanager
def _servidor():
    """Sirve la página de impresión con la escena y three.js. Los módulos de JavaScript no
    cargan desde file://, así que hace falta un servidor local."""
    with tempfile.TemporaryDirectory(prefix="nudos-impresion-") as tmp:
        raiz = Path(tmp)
        shutil.copytree(SITIO / "vendor", raiz / "recursos" / "vendor")
        shutil.copy2(ESCENA, raiz / "recursos" / "escena.js")
        shutil.copy2(PAGINA, raiz / "index.html")
        shutil.copy2(GUION, raiz / "impresion.js")

        class Callado(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                              functools.partial(Callado, directory=str(raiz)))
        hilo = threading.Thread(target=srv.serve_forever, daemon=True)
        hilo.start()
        try:
            yield f"http://127.0.0.1:{srv.server_address[1]}/"
        finally:
            srv.shutdown()
            srv.server_close()


@contextmanager
def chrome():
    """Chrome sin interfaz. Usa NUDOS_CHROME si está definida; si no, el Chrome instalado
    en la computadora y, como último recurso, el navegador que trae Playwright."""
    try:
        from playwright.sync_api import Error as PwError, sync_playwright
    except ImportError:
        raise ImpresionError("Falta Playwright. Instálalo con: python -m pip install -e .[dev]") from None
    with sync_playwright() as p:
        intentos = []
        if os.environ.get("NUDOS_CHROME"):
            intentos.append({"executable_path": os.environ["NUDOS_CHROME"]})
        intentos.append({"channel": "chrome"})
        for nombre in ("google-chrome", "chromium", "chromium-browser"):
            if shutil.which(nombre):
                intentos.append({"executable_path": shutil.which(nombre)})
        intentos.append({})
        navegador = None
        for opciones in intentos:
            try:
                navegador = p.chromium.launch(args=ARGUMENTOS_CHROME, **opciones)
                break
            except PwError:
                continue
        if navegador is None:
            raise ImpresionError("No encuentro Chrome. Instala Google Chrome o define NUDOS_CHROME "
                                 "con la ruta del ejecutable.")
        try:
            yield navegador
        finally:
            navegador.close()


def _dibujar(navegador, base: str, img: Imagen, ancho: int, alto: int) -> bytes:
    contexto = navegador.new_context(viewport={"width": ancho, "height": alto},
                                     device_scale_factor=1, color_scheme="light")
    try:
        pagina = contexto.new_page()
        problemas: list[str] = []
        pagina.on("console", lambda m: problemas.append(m.text) if m.type == "error" else None)
        pagina.on("pageerror", lambda e: problemas.append(str(e)))
        # Como el visor, la impresión no depende de nada fuera de sus propios archivos.
        pagina.on("request", lambda r: None if r.url.startswith((base, "data:"))
                  else problemas.append(f"pidió un recurso de fuera: {r.url}"))
        pagina.goto(base + "index.html", wait_until="load")
        pagina.wait_for_function("window.impresionLista === true", timeout=30000)
        pagina.evaluate("t => window.dibujar(t)", {
            "modelo": img.escena, "paso": img.indice, "vista": img.vista,
            "resaltar": img.resaltar, "nombres": list(img.nombres),
            "reservado": [px(img.reservado_mm[0]), px(img.reservado_mm[1])],
        })
        if problemas:
            raise ImpresionError(f"{img.nombre}: el navegador dio errores:\n  " + "\n  ".join(problemas))
        return pagina.screenshot(type="png", animations="disabled", caret="hide")
    finally:
        contexto.close()


# --------------------------------------------------------------------------
# Página de prueba
# --------------------------------------------------------------------------
def extra_prueba(modelo: Modelo) -> list[Imagen]:
    """El último paso también desde arriba, para comparar las dos vistas impresas."""
    s = modelo.spec
    pasos = datos_escena(s.slug, s.encuadre, modelo.pasos, s.anfitrion)
    n = len(modelo.pasos)
    return [Imagen(f"prueba/paso-{n}-arriba", f"Paso {n}, desde arriba", pasos, n, "arriba", True)]


def pagina_prueba(modelo: Modelo, carpeta: Path) -> Path:
    """Escribe carpeta/prueba.pdf: una página en color y otra en escala de grises."""
    imgs = {i.nombre: i for i in imagenes(modelo) + extra_prueba(modelo)}
    n = len(modelo.pasos)
    filas = [(f"paso-{n}", f"prueba/paso-{n}-arriba")]
    if modelo.error is not None:
        filas.append(("error-correcto", "error"))
    filas.append(("terminado-frente", "terminado-reverso"))
    # Versiones en gris: lo que daría una impresora sin color.
    for nombre in {x for fila in filas for x in fila if x in imgs}:
        with Image.open(carpeta / f"{nombre}.png") as im:
            _guardar(ImageOps.grayscale(im), carpeta / "prueba" / "gris" / f"{Path(nombre).name}.png")

    def hoja(modo: str, ruta) -> str:
        celdas = []
        for fila in filas:
            for nombre in fila:
                if nombre in imgs:
                    celdas.append(f'<figure><img src="{ruta(nombre)}"><figcaption>'
                                  f'{html.escape(imgs[nombre].titulo)}</figcaption></figure>')
        return (f'<section class="hoja"><header><h1>{html.escape(modelo.spec.nombre)}: página de prueba '
                f'· {modo}</h1><p>Imprime a tamaño real (100 %, sin «ajustar a la página»). Cada imagen '
                f'mide {CELDA_MM[0]:g} × {CELDA_MM[1]:g} mm y la línea mide 50 mm. Revisa que en cada '
                f'cruce se vea qué tramo va encima.</p><div class="regla"></div></header>'
                f'<div class="rejilla">{"".join(celdas)}</div></section>')

    fuentes = (SITIO / "vendor" / "fuentes").as_uri()
    documento = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Literata"; font-weight: 400; src: url("{fuentes}/literata-latin-400-normal.woff2"); }}
@font-face {{ font-family: "Literata"; font-weight: 600; src: url("{fuentes}/literata-latin-600-normal.woff2"); }}
@page {{ size: letter; margin: 12mm; }}
body {{ margin: 0; font-family: "Literata", serif; color: #16202f; }}
.hoja {{ break-after: page; }}
.hoja:last-child {{ break-after: auto; }}
h1 {{ font-size: 13pt; font-weight: 600; margin: 0 0 1.5mm; }}
p {{ font-size: 8.5pt; line-height: 1.35; margin: 0 0 2mm; max-width: 180mm; }}
.regla {{ width: 50mm; height: 0; border-top: 0.4mm solid #16202f; margin: 0 0 4mm; }}
.rejilla {{ display: grid; grid-template-columns: {CELDA_MM[0]}mm {CELDA_MM[0]}mm; gap: 3mm 8mm; }}
figure {{ margin: 0; }}
img {{ display: block; width: {CELDA_MM[0]}mm; height: {CELDA_MM[1]}mm; outline: 0.2mm solid #ccd4db; }}
figcaption {{ font-size: 8pt; margin-top: 1mm; }}
</style></head><body>
{hoja("color", lambda n: f"{n}.png")}
{hoja("escala de grises", lambda n: f"prueba/gris/{Path(n).name}.png")}
</body></html>"""
    origen = carpeta / "prueba" / "prueba.html"
    origen.parent.mkdir(parents=True, exist_ok=True)
    origen.write_text(documento.replace('src="', 'src="../'), encoding="utf-8")
    destino = carpeta / "prueba.pdf"
    with chrome() as navegador:
        pagina = navegador.new_page()
        pagina.goto(origen.as_uri(), wait_until="load")
        pagina.pdf(path=str(destino), prefer_css_page_size=True, print_background=True)
    return destino
