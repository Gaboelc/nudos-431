"""Ficha impresa: contenido, vocabulario, QR y que todo quepa en el pliego."""
import io
import re
from dataclasses import replace

import pytest
from PIL import Image

from nudos import URL_BASE
from nudos.ficha import (FichaError, faltantes, ficha, html_ficha, qr_svg,
                         terminos_de_seccion, terminos_encontrados, texto_visible, url_visor)
from nudos.imprimir import CELDA_MM, ImpresionError, chrome, imagenes, px
from nudos.spec import Anfitrion, OtroError


@pytest.fixture(scope="module")
def documento(modelo_as_de_guia):
    return html_ficha(modelo_as_de_guia)


def test_la_ficha_no_usa_terminos_de_seccion(documento):
    assert terminos_encontrados(texto_visible(documento)) == []


@pytest.mark.parametrize("texto, esperado", [
    ("Pídele ayuda a otro Tsuri.", ["Tsurí"]),            # sin tilde también cuenta
    ("Practícalo con tu PATRULLA.", ["patrulla"]),
    ("Lo valora el Consejo de Wak.", ["Wak", "Consejo de Wak"]),
    ("Un kawak no es una sección.", []),                  # solo la palabra completa
])
def test_la_prueba_de_vocabulario_detecta_los_terminos(texto, esperado):
    assert terminos_encontrados(texto) == esperado


def test_la_lista_de_terminos_incluye_los_de_las_reglas():
    terminos = {t.casefold() for t in terminos_de_seccion()}
    assert {"tsurí", "trillo", "consejo de wak", "patrulla"} <= terminos


def test_la_ficha_tiene_todas_sus_secciones(modelo_as_de_guia, documento):
    s = modelo_as_de_guia.spec
    texto = " ".join(texto_visible(documento).split())
    for parte in ["Para qué sirve", "Materiales", "Cómo leer las imágenes", "Míralo en 3D",
                  "Error común · paso 2", s.error.titulo, "El nudo terminado", "Por delante",
                  "Por detrás", "Revisa tu nudo", "Precauciones", "Alternativas", "Seguridad",
                  s.usos, s.materiales, s.seguridad, *s.verificacion, *s.precauciones,
                  *(f"{a.nudo}. {a.cuando}" for a in s.alternativas),
                  *(p.titulo for p in s.pasos), *(p.texto for p in s.pasos)]:
        assert parte in texto, parte
    for img in imagenes(modelo_as_de_guia):
        assert f'src="impresion/{img.nombre}.png"' in documento


def test_el_qr_lleva_a_la_direccion_permanente_del_visor(documento):
    url = url_visor("as-de-guia")
    assert url == f"{URL_BASE}as-de-guia/"
    assert qr_svg(url) in documento
    # Lo lee un decodificador que no es el que lo generó.
    import segno
    import zxingcpp
    png = io.BytesIO()
    segno.make(url, error="m").save(png, kind="png", scale=8, border=4)
    leidos = zxingcpp.read_barcodes(Image.open(io.BytesIO(png.getvalue())))
    assert [b.text for b in leidos] == [url]


def test_los_errores_sin_imagen_van_debajo_del_error(modelo_as_de_guia):
    s = modelo_as_de_guia.spec
    e = replace(s.error, otros=(OtroError("No apretarlo", "Texto del otro error."),))
    texto = " ".join(texto_visible(html_ficha(replace(modelo_as_de_guia, spec=replace(s, error=e)))).split())
    assert "Otro error común No apretarlo Texto del otro error." in texto
    assert texto.index(e.texto) < texto.index("No apretarlo") < texto.index("El nudo terminado")
    assert "Otro error común" not in texto_visible(html_ficha(modelo_as_de_guia))


@pytest.mark.parametrize("anfitrion, detras", [
    (None, "si lo volteas como la página de un libro"),
    (Anfitrion("poste", 1.5, desde=-14, hasta=14), "desde el otro lado del poste"),
    (Anfitrion("cruz", 2.5, largo=40), "si volteas los dos palos juntos como la página de un libro"),
])
def test_como_se_ve_por_detras(modelo_as_de_guia, anfitrion, detras):
    m = replace(modelo_as_de_guia, spec=replace(modelo_as_de_guia.spec, anfitrion=anfitrion))
    assert f"Por detrás es como lo ves {detras}." in " ".join(texto_visible(html_ficha(m)).split())


def test_sin_texto_de_ficha_no_hay_ficha(modelo_as_de_guia, tmp_path):
    incompleto = replace(modelo_as_de_guia, spec=replace(modelo_as_de_guia.spec, usos=None, verificacion=()))
    assert faltantes(incompleto) == ["usos", "verificacion"]
    with pytest.raises(FichaError, match="le falta usos, verificacion"):
        ficha(incompleto, tmp_path)


def test_sin_precauciones_ni_alternativas_no_hay_ficha(modelo_as_de_guia):
    incompleto = replace(modelo_as_de_guia,
                         spec=replace(modelo_as_de_guia.spec, precauciones=(), alternativas=()))
    assert faltantes(incompleto) == ["precauciones", "alternativas"]


# Las que siguen arman el PDF con Chrome. Las imágenes son de relleno, del tamaño real:
# lo que se prueba es la maquetación, no el dibujo.
@pytest.fixture
def carpeta(modelo_as_de_guia, tmp_path):
    try:
        with chrome():
            pass
    except ImpresionError as e:
        pytest.skip(str(e))
    (tmp_path / "impresion").mkdir()
    for img in imagenes(modelo_as_de_guia):
        Image.new("RGB", (px(CELDA_MM[0]), px(CELDA_MM[1])), "white").save(
            tmp_path / "impresion" / f"{img.nombre}.png")
    return tmp_path


def test_la_ficha_es_un_pliego_de_dos_paginas_carta(modelo_as_de_guia, carpeta):
    pdf = ficha(modelo_as_de_guia, carpeta).read_bytes()
    assert len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", pdf)) == 2
    assert re.search(rb"/MediaBox\s*\[\s*0 0 612 792\s*\]", pdf)   # carta: 8,5 × 11 in


def test_si_el_texto_no_cabe_la_ficha_falla(modelo_as_de_guia, carpeta):
    largo = " ".join(["Revisa el nudo con calma antes de usarlo."] * 60)
    s = replace(modelo_as_de_guia.spec, seguridad=largo)
    with pytest.raises(FichaError, match="no cabe en la página 2"):
        ficha(replace(modelo_as_de_guia, spec=s), carpeta)
