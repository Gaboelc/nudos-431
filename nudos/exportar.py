"""Sitio web: un visor 3D por nudo, en la dirección permanente que lleva su QR."""
from __future__ import annotations

import html
import json
import re
import shutil
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

from . import RAIZ, SPECS, URL_BASE
from .construir import Modelo, construir
from .anfitrion import solido
from .libre import Resultado
from .spec import Cuerda, Encuadre, cargar

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
    return datos_escena(modelo, modelo.spec.encuadre, modelo.pasos)


def datos_escena(modelo: Modelo, e: Encuadre | None, resultados: list[Resultado],
                 anfitrion: dict | None = None) -> dict:
    """Lo que necesita render/escena.js para dibujar estos resultados del nudo con este
    encuadre. El encuadre se ajusta a la cuerda de todos los resultados juntos. «anfitrion»
    reemplaza al de la especificación: es la cruz volteada del amarre visto por detrás.

    Con una cuerda, cada paso lleva sus puntos («p») y su tramo resaltado («hl»). Con
    varias, la lista de cuerdas va aparte y cada paso lleva los puntos y el resaltado de
    cada una, y cuál lleva el nombre «Chicote»: la que se mueve en ese paso o, en uno sin
    resaltado (el nudo terminado), la última que se movió.

    En un nudo de plantilla se ven los dos extremos de la cuerda, y los dos llevan remate
    («dos_remates»). Ver _paso_de_plantilla."""
    s = modelo.spec
    mueve = cuerda_que_se_mueve(modelo.pasos)
    pasos = []
    for r in resultados:
        if s.plantilla is not None:
            pasos.append(_paso_de_plantilla(s, r))
            continue
        if r.reparto is None:
            pasos.append({"n": r.n, "hl": _resaltado(r, 0, len(r.puntos) - 1), "p": _puntos(r.puntos)})
            continue
        cuerdas = [{"p": _puntos(r.puntos[i0:i1 + 1]), "hl": _resaltado(r, i0, i1)}
                   for i0, i1 in r.reparto.tramos]
        chicote = mueve if r.resaltado is None else _cuerda_resaltada(r)
        pasos.append({"n": r.n, "cuerdas": cuerdas, "chicote": chicote})
    if anfitrion is None and s.anfitrion is not None:
        anfitrion = solido(s.anfitrion).datos()
    datos = {
        "slug": s.slug,
        "encuadre": None if e is None else {"x": list(e.x), "y": list(e.y)},
        "anfitrion": anfitrion,
        "pasos": pasos,
    }
    if s.plantilla is not None:
        datos["dos_remates"] = True
    if s.cuerdas:
        datos["cuerdas"] = [{"nombre": c.nombre, "etiqueta": etiqueta(c), "grosor": c.grosor,
                             "color": c.color} for c in s.cuerdas]
    return datos


def _paso_de_plantilla(s, r: Resultado) -> dict:
    """Un paso de un nudo de plantilla. La escena pone «Firme» donde empieza la cuerda y
    «Chicote» donde termina. En los pasos que tienen firme (CON_FIRME de la plantilla, como
    el ballestrinque de inicio del amarre), la cuerda va al revés: desde la parte larga, que
    es su firme, hasta el chicote corto. En los demás va desde el chicote corto hasta la
    punta de la parte larga, que es la que se mueve, y solo lleva «Chicote» («nombres»)."""
    hl = _resaltado(r, 0, len(r.puntos) - 1)
    if s.pasos[r.n - 1].hasta in s.plantilla.CON_FIRME:
        return {"n": r.n, "hl": None if hl is None else [round(1 - hl[1], 4), round(1 - hl[0], 4)],
                "p": _puntos(r.puntos[::-1])}
    return {"n": r.n, "hl": hl, "p": _puntos(r.puntos), "nombres": ["chicote"]}


def etiqueta(cuerda: Cuerda) -> str:
    """El nombre de una cuerda en las imágenes, junto a su firme: «gruesa» → «Gruesa»."""
    texto = cuerda.nombre.replace("-", " ")
    return texto[:1].upper() + texto[1:]


def cuerda_que_se_mueve(resultados: list[Resultado]) -> int | None:
    """La cuerda resaltada en el último paso que tiene un resaltado; si ninguno lo tiene,
    la última cuerda. None con una sola cuerda."""
    if not resultados or resultados[0].reparto is None:
        return None
    for r in reversed(resultados):
        if r.resaltado is not None:
            return _cuerda_resaltada(r)
    return len(resultados[0].reparto.tramos) - 1


def _cuerda_resaltada(r: Resultado) -> int:
    # El punto medio del tramo resaltado: sus dos extremos son de la misma cuerda, pero
    # el comienzo puede caer justo en el primer punto de ella.
    return r.reparto.de((r.resaltado[0] + r.resaltado[1]) / 2, r.h)


def _resaltado(r: Resultado, i0: int, i1: int) -> list[float] | None:
    """El tramo resaltado como fracción del largo de la cuerda que va de i0 a i1, o None
    si el resaltado no es de esa cuerda."""
    if r.resaltado is None:
        return None
    s0, largo = i0 * r.h, (i1 - i0) * r.h
    if r.reparto is not None and r.reparto.tramos[_cuerda_resaltada(r)][0] != i0:
        return None
    return [round(min(max((s - s0) / largo, 0.0), 1.0), 4) for s in r.resaltado]


def _puntos(X) -> list[float]:
    """Uno de cada dos puntos, y siempre el último, con tres decimales."""
    idx = list(range(0, len(X), 2))
    if idx[-1] != len(X) - 1:
        idx.append(len(X) - 1)
    return [round(float(v), 3) for i in idx for v in X[i]]


def rellenar(plantilla: str, valores: dict[str, str]) -> str:
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
    otros = ("" if not s.otros_nombres else
             f'    <p class="lede">También se llama {esc(lista_o(s.otros_nombres))}.</p>\n')
    return rellenar((SITIO / "plantilla.html").read_text(encoding="utf-8"), {
        "titulo": esc(s.nombre),
        "otros": otros,
        "sobre": _sobre(s),
        "descripcion": esc(f"{s.nombre}, paso a paso, con un modelo 3D de cada paso."),
        "url": esc(f"{URL_BASE}{s.slug}/"),
        "hechos": "\n".join(f"      <div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in hechos),
        "n_pasos": str(len(s.pasos)),
        "pasos": pasos,
        "datos": datos.replace("</", "<\\/"),
    })


def lista_o(nombres) -> str:
    """«a», «a o b», «a, b o c»."""
    nombres = list(nombres)
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " o " + nombres[-1]


def _sobre(s) -> str:
    """Lo que la página dice del nudo debajo de los pasos: el mismo texto de la ficha. Cada
    parte va solo si la especificación la tiene."""
    esc = html.escape
    partes = []
    if s.usos:
        partes.append(f"      <h3>Para qué sirve</h3><p>{esc(s.usos)}</p>")
    if s.materiales:
        partes.append(f"      <h3>Materiales</h3><p>{esc(s.materiales)}</p>")
    if s.precauciones:
        partes.append("      <h3>Precauciones</h3><ul>"
                      + "".join(f"<li>{esc(t)}</li>" for t in s.precauciones) + "</ul>")
    if s.alternativas:
        partes.append("      <h3>Alternativas</h3><ul>"
                      + "".join(f"<li><strong>{esc(a.nudo)}.</strong> {esc(a.cuando)}</li>"
                                for a in s.alternativas) + "</ul>")
    if s.seguridad:
        partes.append(f'      <div class="seguridad"><h3>Seguridad</h3><p>{esc(s.seguridad)}</p></div>')
    if not partes:
        return ""
    return ('    <section class="sobre" aria-label="Sobre el nudo">\n      <h2>Sobre el nudo</h2>\n'
            + "\n".join(partes) + "\n    </section>")


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


def nudos_del_sitio(publicados: list[str] | None = None, con: Iterable[str] = ()) -> list[str]:
    """Los slugs que lleva el sitio: los de publicados.txt y, para verlos en el sitio local
    antes de publicarlos, los de «con». Las demás especificaciones de specs/ no salen en
    línea, así que ninguna dirección queda en el sitio sin estar en la lista."""
    if publicados is None:
        publicados = leer_publicados()
    faltan = [s for s in publicados if not (SPECS / f"{s}.yaml").is_file()]
    if faltan:
        raise SitioError("Faltan las especificaciones de nudos que ya tienen QR impreso: "
                         + ", ".join(faltan) + ". Su dirección no puede dejar de funcionar.")
    return sorted({*publicados, *con})


def construir_sitio(destino: Path, modelos: list[Modelo] | None = None,
                    publicados: list[str] | None = None, con: Iterable[str] = ()) -> list[str]:
    """Construye el sitio en «destino» y devuelve los slugs que contiene.

    Sin «modelos», construye los nudos de nudos_del_sitio. No publica nada si algún nudo
    tiene fallas o si falta la página de un nudo con QR impreso."""
    if publicados is None:
        publicados = leer_publicados()
    if modelos is None:
        modelos = [construir(cargar(s)) for s in nudos_del_sitio(publicados, con)]

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
    (destino / "index.html").write_text(rellenar((SITIO / "indice.html").read_text(encoding="utf-8"), {
        "url": html.escape(URL_BASE), "nudos": _lista(modelos, ""),
    }), encoding="utf-8")
    base = urlparse(URL_BASE).path
    (destino / "404.html").write_text(rellenar((SITIO / "404.html").read_text(encoding="utf-8"), {
        "base": base, "nudos": _lista(modelos, base),
    }), encoding="utf-8")
    (destino / MARCA).write_text("", encoding="utf-8")

    sobran = archivos_no_permitidos(destino)
    if sobran:
        raise SitioError("El sitio tiene archivos que no deberían estar: "
                         + ", ".join(str(p.relative_to(destino)) for p in sobran))
    return slugs
