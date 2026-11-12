"""Hoja de revisión privada de un borrador: la fuente junto a cada paso.

La arma la skill nudo-nuevo (.claude/skills/nudo-nuevo/SKILL.md) para que Gabriel revise
el borrador. Es una página HTML en revision/<slug>/, que está fuera de git. Por cada paso
pone, lado a lado, las imágenes de la fuente que le corresponden, el paso dibujado desde
arriba y a 55° (nudos/hoja.py) y la secuencia de cruces declarada junto a la medida.

Las imágenes de la fuente se enlazan desde entradas/, sin copiarlas: la fuente es entrada,
nunca contenido. Qué imágenes van con cada paso lo dice revision/<slug>/pasos.yaml, que
escribe la skill (ver «La hoja de revisión» en la skill). Sin ese archivo, la página
muestra todas las imágenes de la fuente arriba.
"""
from __future__ import annotations

import html
import os
from pathlib import Path

import yaml

from . import RAIZ
from .construir import Modelo, datos_json
from .hoja import ANCHO, hoja
from .libre import Resultado

DESTINO = RAIZ / "revision"   # fuera de git (.gitignore)
# Las entradas viven en la carpeta de A:; en un worktree no están, y NUDOS_ENTRADAS dice dónde.
ENTRADAS = Path(os.environ.get("NUDOS_ENTRADAS", RAIZ / "entradas"))
IMAGENES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VISTAS = ("arriba", "55")


class RevisionError(Exception):
    """La hoja de revisión no se puede armar así."""


def leer_pasos(ruta: Path) -> dict:
    """revision/<slug>/pasos.yaml: {"pasos": {n: [imagen, ...]}, "error": [...], "dudas": {n: texto}}.
    Las imágenes van relativas a entradas/<slug>/. Si el archivo no existe, todo va vacío."""
    if not ruta.is_file():
        return {"pasos": {}, "error": [], "dudas": {}}
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f) or {}
    sobran = set(datos) - {"pasos", "error", "dudas"}
    if sobran:
        raise RevisionError(f"{ruta}: campos desconocidos: {', '.join(sorted(sobran))}")
    pasos = {int(n): [str(i) for i in imgs or []] for n, imgs in (datos.get("pasos") or {}).items()}
    dudas = {str(n): str(t) for n, t in (datos.get("dudas") or {}).items()}
    return {"pasos": pasos, "error": [str(i) for i in datos.get("error") or []], "dudas": dudas}


def revision(modelo: Modelo, destino: Path | None = None, entradas: Path | None = None) -> Path:
    """Arma la hoja de revisión del nudo y devuelve la ruta de su página."""
    slug = modelo.spec.slug
    destino = (DESTINO if destino is None else destino) / slug
    fuente = (ENTRADAS if entradas is None else entradas) / slug
    destino.mkdir(parents=True, exist_ok=True)
    for viejo in destino.glob("*.png"):
        viejo.unlink()
    mapa = leer_pasos(destino / "pasos.yaml")
    datos = datos_json(modelo)

    def dibujos(dibujo: dict, nombre: str) -> str:
        """`dibujo` es el paso como lo trae modelo.json."""
        celdas = []
        for vista in VISTAS:
            im = hoja({**datos, "pasos": [dibujo]}, vista)
            im = im.crop((0, 0, ANCHO, im.height))
            archivo = f"{nombre}-{vista}.png"
            im.save(destino / archivo)
            celdas.append(f'<figure><img src="{archivo}" alt=""><figcaption>'
                          f'{"Desde arriba" if vista == "arriba" else f"A {vista}°"}</figcaption></figure>')
        return "".join(celdas)

    def de_la_fuente(imagenes: list[str]) -> str:
        if not imagenes:
            return '<p class="nota">La skill no anotó imágenes de la fuente para este paso.</p>'
        return "".join(_imagen(fuente / i, destino, i) for i in imagenes)

    def secuencias(r: Resultado, escrita: tuple[str, ...]) -> str:
        declarada, medida = _con_etiquetas(r, escrita)
        clase = "igual" if r.esperada == r.secuencia else "distinta"
        return (f'<table class="{clase}"><tr><th>Declarada</th><td>{html.escape(declarada) or "sin cruces"}</td></tr>'
                f'<tr><th>Medida</th><td>{html.escape(medida) or "sin cruces"}</td></tr></table>')

    def duda(clave: str) -> str:
        texto = mapa["dudas"].get(clave)
        return f'<p class="duda">Duda: {html.escape(texto)}</p>' if texto else ""

    bloques = []
    for p, r, dibujo in zip(modelo.spec.pasos, modelo.pasos, datos["pasos"]):
        bloques.append(
            f'<section><h2>Paso {p.n}: {html.escape(p.titulo)}</h2><p>{html.escape(p.texto)}</p>'
            f'{duda(str(p.n))}<div class="fila"><div class="fuente">{de_la_fuente(mapa["pasos"].get(p.n, []))}</div>'
            f'<div class="render">{dibujos(dibujo, f"paso-{p.n}")}</div></div>{secuencias(r, p.secuencia)}</section>')
    if modelo.error is not None and modelo.spec.error is not None:
        e = modelo.spec.error
        # La del error es la del paso, con los cruces de «invierte» al revés.
        al_reves = {"O": "U", "U": "O"}
        del_error = tuple(t[:-1] + al_reves[t[-1]] if t[:-1] in e.invierte else t
                          for t in modelo.spec.pasos[e.paso - 1].secuencia)
        bloques.append(
            f'<section><h2>Error común, junto al paso {e.paso}: {html.escape(e.titulo)}</h2>'
            f'<p>{html.escape(e.texto)}</p>{duda("error")}<div class="fila"><div class="fuente">'
            f'{de_la_fuente(mapa["error"])}</div><div class="render">{dibujos(datos["error"], "error")}</div></div>'
            f'{secuencias(modelo.error, del_error)}</section>')

    arriba = ""
    if not mapa["pasos"]:
        todas = sorted(str(p.relative_to(fuente)).replace(os.sep, "/") for p in fuente.rglob("*")
                       if p.suffix.lower() in IMAGENES) if fuente.is_dir() else []
        arriba = ('<section><h2>La fuente</h2><div class="fuente">'
                  + ("".join(_imagen(fuente / i, destino, i) for i in todas) if todas
                     else f'<p class="falla">No hay imágenes en {html.escape(str(fuente))}.</p>')
                  + "</div></section>")
    fallas = "".join(f"<li>{html.escape(f)}</li>" for f in modelo.fallas)
    pagina = _PAGINA.format(
        nombre=html.escape(modelo.spec.nombre), slug=slug, estado=html.escape(modelo.spec.estado),
        fallas=f'<ul class="falla">{fallas}</ul>' if fallas else '<p class="bien">Sin fallas.</p>',
        arriba=arriba, bloques="\n".join(bloques))
    (destino / "index.html").write_text(pagina, encoding="utf-8")
    return destino / "index.html"


def _con_etiquetas(r: Resultado, escrita: tuple[str, ...]) -> tuple[str, str]:
    """La secuencia declarada y la medida, con las etiquetas de la especificación.

    Al construir, las dos se numeran en el orden en que aparecen (cruces.numerada). Aquí la
    k-ésima etiqueta que aparece vuelve a llamarse como en la especificación, que es como la
    revisa Gabriel de un paso a otro. En un nudo de plantilla los pasos no traen secuencia
    escrita, y quedan como las numera la construcción."""
    if len(escrita) != len(r.esperada):
        return " ".join(r.esperada), " ".join(r.secuencia)
    nombres = {e[:-1]: s[:-1] for e, s in zip(r.esperada, escrita)}
    medida = " ".join(nombres.get(t[:-1], t[:-1] + "?") + t[-1] for t in r.secuencia)
    return " ".join(escrita), medida


def _imagen(ruta: Path, destino: Path, nombre: str) -> str:
    if not ruta.is_file():
        return f'<p class="falla">No existe {html.escape(nombre)} en la fuente.</p>'
    try:
        src = Path(os.path.relpath(ruta, destino)).as_posix()
    except ValueError:   # en otra unidad
        src = ruta.resolve().as_uri()
    return (f'<figure><img src="{html.escape(src)}" alt=""><figcaption>{html.escape(nombre)}'
            f'</figcaption></figure>')


_PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisión: {nombre}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 24px; color: #222; background: #fff; }}
h1 {{ margin-bottom: 4px; }} h2 {{ margin-top: 32px; }}
.fila {{ display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-start; }}
.fuente, .render {{ display: flex; gap: 8px; flex-wrap: wrap; }}
figure {{ margin: 0; }} figure img {{ max-width: 360px; max-height: 300px; border: 1px solid #ccc; }}
figcaption {{ font-size: 12px; color: #666; }}
table {{ border-collapse: collapse; margin-top: 8px; font-family: ui-monospace, monospace; }}
th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
table.distinta td {{ background: #fde2e2; }}
.falla {{ color: #a00; }} .bien {{ color: #070; }} .nota {{ color: #666; font-style: italic; }}
.duda {{ background: #fff6d6; padding: 6px 10px; border-left: 4px solid #e0a800; }}
</style></head><body>
<h1>{nombre}</h1>
<p>Hoja de revisión privada de <code>specs/{slug}.yaml</code>, en estado <strong>{estado}</strong>. No se publica: enlaza las imágenes de la fuente sin copiarlas.</p>
{fallas}
{arriba}
{bloques}
</body></html>
"""
