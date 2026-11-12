"""Imágenes de impresión de un nudo, a 300 ppp en su tamaño impreso.

Salen de la misma escena 3D del visor (render/escena.js), dibujada con Chrome sin
interfaz y con WebGL por software (SwiftShader), para que construir dos veces dé
exactamente las mismas imágenes, píxel por píxel, en cualquier computadora con la misma
versión de Chrome. Con otra versión de Pillow cambian los bytes del PNG, no los píxeles.

Para cada nudo se generan, en build/<slug>/impresion/:
- paso-<n>.png: cada paso, con el tramo que se mueve resaltado y los nombres.
- error-correcto.png y error.png: el paso del error común, bien y mal, con el mismo encuadre.
- terminado-frente.png y terminado-reverso.png: el nudo terminado por delante y por detrás,
  apretado (ver TERMINADO_APRETADO).
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
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from . import RAIZ
from .anfitrion import Cruz, Tubo
from .construir import Modelo
from .exportar import ESCENA, SITIO, datos_escena
from .spec import Encuadre

PPP = 300
# Tamaño impreso de cada imagen: una celda de la rejilla de tres columnas de la ficha
# (libro/ficha.css). Si cambia, cambia también allí.
CELDA_MM = (58.0, 64.0)
VISTA_PASOS = "3d"         # la vista de quien ata sentado a la mesa
VISTA_TERMINADO = "arriba"
# Sobre un poste el nudo no se voltea: se mira por delante y desde el otro lado. Sobre la
# cruz de un amarre se voltea con los palos y se mira, las dos veces, como los pasos.
VISTAS_TERMINADO_ANFITRION = ("3d", "detras")
ESQUINA_PASO = (11.0, 11.0)    # el número del paso (libro/ficha.css, .num)
ESQUINA_SELLO = (26.0, 7.0)    # «Bien», «Así no», «Por delante», «Por detrás» (.sello)
PAGINA = RAIZ / "render" / "impresion.html"
GUION = RAIZ / "render" / "impresion.js"
ARGUMENTOS_CHROME = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                     "--ignore-gpu-blocklist", "--font-render-hinting=none"]
# Mejoras del render (T7b): la sombra de contacto, dibujar al doble y reducir, y sombras más
# claras y de borde blando. Gabriel las eligió con la página de prueba impresa («python -m
# nudos mejoras»); el contorno de tinta no entró.
MEJORAS = ("contacto", "supermuestreo", "sombras-suaves")
# Las que llevan las imágenes de la ficha: todas. Sin ninguna, las imágenes salen como antes
# de T7b.
MEJORAS_ACTIVAS: tuple[str, ...] = MEJORAS
SUPERMUESTREO = 2   # con «supermuestreo», cada imagen se dibuja a esta escala y se reduce
# El nudo terminado apretado (T7c, nudos/apretar.py): si es verdadero, las dos vistas del
# terminado salen del nudo apretado. Gabriel lo eligió el 11 de noviembre de 2026, después de
# comparar en papel el terminado sin apretar, a medias y apretado («python -m nudos mejoras»,
# build/mejoras/apretado.pdf). En falso, el terminado es el último paso, como antes de T7c.
TERMINADO_APRETADO = True


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
    nombres: tuple[str, ...]   # claves de los nombres que lleva (ver nombres())
    # Esquina superior izquierda (ancho, alto en mm) que la ficha tapa con el número del
    # paso o con un sello. Ahí no se ponen los nombres.
    reservado_mm: tuple[float, float] = (0.0, 0.0)
    mejoras: tuple[str, ...] = MEJORAS_ACTIVAS   # de MEJORAS

    def __post_init__(self):
        if set(self.mejoras) - set(MEJORAS):
            raise ValueError(f"{self.nombre}: mejoras desconocidas: "
                             f"{', '.join(sorted(set(self.mejoras) - set(MEJORAS)))}")


def px(mm: float) -> int:
    return round(mm / 25.4 * PPP)


def espejo(e: Encuadre | None) -> Encuadre | None:
    """El encuadre del nudo volteado sobre el eje y."""
    return None if e is None else Encuadre((-e.x[1], -e.x[0]), e.y)


def girado_y(e: Encuadre | None) -> Encuadre | None:
    """El encuadre del nudo girado media vuelta alrededor del eje del tubo, a lo largo de x."""
    return None if e is None else Encuadre(e.x, (-e.y[1], -e.y[0]))


def nombres(modelo: Modelo, chicote: bool = True) -> tuple[str, ...]:
    """Los nombres que llevan las imágenes, como claves de render/escena.js: «Firme» y
    «Chicote» con una cuerda; con varias, el de cada cuerda junto a su firme y «Chicote»."""
    firmes = tuple(f"cuerda-{c.nombre}" for c in modelo.spec.cuerdas) or ("firme",)
    return firmes + (("chicote",) if chicote else ())


def imagenes(modelo: Modelo) -> list[Imagen]:
    """Las imágenes de la ficha de un nudo."""
    s = modelo.spec
    todos = nombres(modelo)
    pasos = datos_escena(modelo, s.encuadre, modelo.pasos)
    out = [Imagen(f"paso-{r.n}", f"Paso {r.n}", pasos, i + 1, VISTA_PASOS, True, todos,
                  reservado_mm=ESQUINA_PASO)
           for i, r in enumerate(modelo.pasos)]
    if modelo.error is not None:
        e = s.error
        correcto = next(r for r in modelo.pasos if r.n == e.paso)
        par = datos_escena(modelo, e.encuadre or s.encuadre, [correcto, modelo.error])
        firmes = nombres(modelo, chicote=False)
        out.append(Imagen("error-correcto", f"Paso {e.paso}, bien", par, 1, VISTA_PASOS, True,
                          firmes, ESQUINA_SELLO))
        out.append(Imagen("error", f"Error: {e.titulo}", par, 2, VISTA_PASOS, True,
                          firmes, ESQUINA_SELLO))
    if TERMINADO_APRETADO and modelo.apretado is not None:
        return out + terminado(modelo, modelo.apretado, modelo.reverso_apretado)
    return out + terminado(modelo, modelo.pasos[-1], modelo.reverso)


def terminado(modelo: Modelo, final, reverso, prefijo: str = "terminado") -> list[Imagen]:
    """Las dos vistas del nudo terminado: `final` por delante y `reverso` por detrás. Sobre un
    poste no hay reverso (se mira `final` desde el otro lado), sobre la cruz se voltea
    `final` con los palos y sobre el tubo se gira `final` media vuelta con el tubo. Se llaman
    <prefijo>-frente y <prefijo>-reverso."""
    s = modelo.spec
    todos = nombres(modelo)
    enc = s.terminado.encuadre or s.encuadre
    frente, atras = f"{prefijo}-frente", f"{prefijo}-reverso"
    if s.anfitrion is not None and s.anfitrion.tipo == "tubo":
        # La cabeza de turco se mira como los pasos: por delante, el remate; por detrás, el tubo
        # y el nudo girados media vuelta alrededor del eje, como se gira el tubo en la mano.
        girado = Tubo(s.anfitrion).voltear(final)
        return [Imagen(frente, "Terminado, por delante", datos_escena(modelo, enc, [final]), 1,
                       VISTA_PASOS, False, todos, reservado_mm=ESQUINA_SELLO),
                Imagen(atras, "Terminado, por detrás", datos_escena(modelo, girado_y(enc), [girado]),
                       1, VISTA_PASOS, False, todos, reservado_mm=ESQUINA_SELLO)]
    if s.anfitrion is not None and s.anfitrion.tipo == "cruz":
        # El amarre se voltea entero, palos y cuerda, como un marco sobre la mesa, y por
        # delante y por detrás se mira desde donde se ata.
        volteado, cruz = Cruz(s.anfitrion).voltear(final)
        return [Imagen(frente, "Terminado, por delante", datos_escena(modelo, enc, [final]), 1,
                       VISTA_PASOS, False, todos, reservado_mm=ESQUINA_SELLO),
                Imagen(atras, "Terminado, por detrás",
                       datos_escena(modelo, espejo(enc), [volteado], anfitrion=cruz), 1,
                       VISTA_PASOS, False, todos, reservado_mm=ESQUINA_SELLO)]
    if s.anfitrion is not None:
        escena = datos_escena(modelo, enc, [final])
        delante, detras = VISTAS_TERMINADO_ANFITRION
        return [Imagen(frente, "Terminado, por delante", escena, 1, delante, False, todos,
                       reservado_mm=ESQUINA_SELLO),
                Imagen(atras, "Terminado, por detrás", escena, 1, detras, False, todos,
                       reservado_mm=ESQUINA_SELLO)]
    out = [Imagen(frente, "Terminado, por delante", datos_escena(modelo, enc, [final]), 1,
                  VISTA_TERMINADO, False, todos, reservado_mm=ESQUINA_SELLO)]
    if reverso is not None:
        out.append(Imagen(atras, "Terminado, por detrás",
                          datos_escena(modelo, espejo(enc), [reverso]), 1, VISTA_TERMINADO,
                          False, todos, reservado_mm=ESQUINA_SELLO))
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
            im = Image.open(io.BytesIO(png))
            if im.size != (ancho, alto):   # supermuestreo: de vuelta a PPP
                im = im.convert("RGB").resize((ancho, alto), Image.Resampling.LANCZOS)
            _guardar(im, ruta)
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
    """La captura de la imagen. Con supermuestreo mide SUPERMUESTREO veces más por lado: la
    página es la misma, pero el navegador la dibuja con más px por px de CSS."""
    escala = SUPERMUESTREO if "supermuestreo" in img.mejoras else 1
    contexto = navegador.new_context(viewport={"width": ancho, "height": alto},
                                     device_scale_factor=escala, color_scheme="light")
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
            "mejoras": list(img.mejoras),
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
    pasos = datos_escena(modelo, modelo.spec.encuadre, modelo.pasos)
    n = len(modelo.pasos)
    return [Imagen(f"prueba/paso-{n}-arriba", f"Paso {n}, desde arriba", pasos, n, "arriba", True,
                   nombres(modelo))]


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
