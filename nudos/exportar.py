"""Sitio web: un visor 3D por nudo, en la dirección permanente que lleva su QR."""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from . import RAIZ, SPECS, URL_BASE
from .construir import Modelo, construir
from .libre import Resultado
from .spec import Encuadre, cargar

SITIO = RAIZ / "sitio"
ESCENA = RAIZ / "render" / "escena.js"
PUBLICADOS = RAIZ / "publicados.txt"

# Lo único que puede tener el sitio. Ninguna imagen: así no se cuela ninguna de las fuentes.
EXTENSIONES = {".html", ".js", ".css", ".woff2", ".txt"}
MARCA = ".nojekyll"   # además le dice a GitHub Pages que no procese el sitio


class SitioError(Exception):
    """El sitio no se puede publicar así."""


def leer_publicados(ruta: Path = PUBLICADOS) -> list[str]:
    """Slugs con QR impreso, uno por línea; «#» empieza un comentario."""
    slugs = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea:
            slugs.append(linea)
    return slugs


def datos_visor(modelo: Modelo) -> dict:
    """Lo que necesita el visor: la cuerda de cada paso y el tramo resaltado."""
    return datos_escena(modelo.spec.slug, modelo.spec.encuadre, modelo.pasos)


def datos_escena(slug: str, e: Encuadre | None, resultados: list[Resultado]) -> dict:
    """Lo que necesita render/escena.js para dibujar estos resultados con este encuadre.
    El encuadre se ajusta a la cuerda de todos los resultados juntos."""
    pasos = []
    for r in resultados:
        largo = r.h * (len(r.puntos) - 1)
        hl = None
        if r.resaltado is not None:
            hl = [round(min(max(s / largo, 0.0), 1.0), 4) for s in r.resaltado]
        idx = list(range(0, len(r.puntos), 2))
        if idx[-1] != len(r.puntos) - 1:
            idx.append(len(r.puntos) - 1)
        p = [round(float(v), 3) for i in idx for v in r.puntos[i]]
        pasos.append({"n": r.n, "hl": hl, "p": p})
    return {
        "slug": slug,
        "encuadre": None if e is None else {"x": list(e.x), "y": list(e.y)},
        "pasos": pasos,
    }


def _rellenar(plantilla: str, valores: dict[str, str]) -> str:
    def poner(m: re.Match) -> str:
        clave = m.group(1)
        if clave not in valores:
            raise KeyError(f"la plantilla pide «{clave}» y no tiene valor")
        return valores[clave]
    return re.sub(r"\{\{(\w+)\}\}", poner, plantilla)


def _lista(modelos: list[Modelo], prefijo: str) -> str:
    filas = []
    for m in modelos:
        s = m.spec
        filas.append(f'      <li><a href="{prefijo}{s.slug}/"><span class="n">{html.escape(s.nombre)}</span>'
                     f'<span class="f">{html.escape(s.familia)}</span></a></li>')
    return "\n".join(filas)


def pagina_nudo(modelo: Modelo) -> str:
    s = modelo.spec
    esc = html.escape
    hechos = [("Familia", s.familia)]
    if s.abok is not None:
        hechos.append(("ABOK", f"N.º {s.abok}"))
    hechos.append(("Pasos", str(len(s.pasos))))
    pasos = "\n".join(
        f'        <li><button class="step" type="button" data-n="{p.n}"><span class="num">{p.n}</span>'
        f'<span><span class="t">{esc(p.titulo)}</span><span class="d">{esc(p.texto)}</span></span></button></li>'
        for p in s.pasos)
    datos = json.dumps(datos_visor(modelo), ensure_ascii=False, separators=(",", ":"))
    return _rellenar((SITIO / "plantilla.html").read_text(encoding="utf-8"), {
        "titulo": esc(s.nombre),
        "descripcion": esc(f"{s.nombre}, paso a paso, con un modelo 3D de cada paso."),
        "url": esc(f"{URL_BASE}{s.slug}/"),
        "hechos": "\n".join(f"      <div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in hechos),
        "n_pasos": str(len(s.pasos)),
        "pasos": pasos,
        "datos": datos.replace("</", "<\\/"),
    })


def _limpiar(destino: Path) -> None:
    """Vacía la carpeta de salida, pero solo si es un sitio anterior o está vacía."""
    if destino.exists():
        if any(destino.iterdir()) and not (destino / MARCA).exists():
            raise SitioError(f"{destino} no está vacía y no parece un sitio anterior; no la borro.")
        shutil.rmtree(destino)
    destino.mkdir(parents=True)


def archivos_no_permitidos(destino: Path) -> list[Path]:
    return [p for p in destino.rglob("*")
            if p.is_file() and p.name != MARCA and p.suffix.lower() not in EXTENSIONES]


def construir_sitio(destino: Path, modelos: list[Modelo] | None = None,
                    publicados: list[str] | None = None) -> list[str]:
    """Construye el sitio en «destino» y devuelve los slugs que contiene.

    Sin «modelos», construye todos los nudos de specs/. No publica nada si algún nudo
    tiene fallas o si falta la página de un nudo con QR impreso."""
    if modelos is None:
        modelos = [construir(cargar(p)) for p in sorted(SPECS.glob("*.yaml"))]
    if publicados is None:
        publicados = leer_publicados()

    problemas = [f"{m.spec.slug}: {f}" for m in modelos for f in m.fallas]
    if problemas:
        raise SitioError("Hay nudos con fallas; no se publica nada:\n" + "\n".join(f"  - {p}" for p in problemas))
    slugs = [m.spec.slug for m in modelos]
    faltan = [s for s in publicados if s not in slugs]
    if faltan:
        raise SitioError("Faltan nudos que ya tienen QR impreso: " + ", ".join(faltan)
                         + ". Su dirección no puede dejar de funcionar.")

    _limpiar(destino)
    recursos = destino / "recursos"
    shutil.copytree(SITIO / "vendor", recursos / "vendor")
    shutil.copy2(ESCENA, recursos / "escena.js")
    shutil.copy2(SITIO / "visor.js", recursos / "visor.js")
    shutil.copy2(SITIO / "visor.css", recursos / "visor.css")
    for m in modelos:
        (destino / m.spec.slug).mkdir()
        (destino / m.spec.slug / "index.html").write_text(pagina_nudo(m), encoding="utf-8")
    (destino / "index.html").write_text(_rellenar((SITIO / "indice.html").read_text(encoding="utf-8"), {
        "url": html.escape(URL_BASE), "nudos": _lista(modelos, ""),
    }), encoding="utf-8")
    base = urlparse(URL_BASE).path
    (destino / "404.html").write_text(_rellenar((SITIO / "404.html").read_text(encoding="utf-8"), {
        "base": base, "nudos": _lista(modelos, base),
    }), encoding="utf-8")
    (destino / MARCA).write_text("", encoding="utf-8")

    sobran = archivos_no_permitidos(destino)
    if sobran:
        raise SitioError("El sitio tiene archivos que no deberían estar: "
                         + ", ".join(str(p.relative_to(destino)) for p in sobran))
    return slugs
