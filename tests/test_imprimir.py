"""Imágenes de impresión. Las pruebas que dibujan necesitan Chrome; sin él se saltan."""
import hashlib

import pytest
from PIL import Image

from nudos.exportar import datos_visor
from nudos.imprimir import CELDA_MM, PPP, dibujar, espejo, imagenes, px
from nudos.spec import Encuadre


def test_tamano_impreso_a_300_ppp():
    assert PPP == 300
    assert (px(58), px(64)) == (685, 756)


def test_espejo_del_encuadre():
    assert espejo(Encuadre((-6.5, 5.5), (-5.0, 11.5))) == Encuadre((-5.5, 6.5), (-5.0, 11.5))
    assert espejo(None) is None


def test_la_ficha_tiene_todas_sus_imagenes(modelo_as_de_guia):
    nombres = [i.nombre for i in imagenes(modelo_as_de_guia)]
    assert nombres == [f"paso-{n}" for n in range(1, 8)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]


def test_el_error_y_el_paso_correcto_comparten_encuadre(modelo_as_de_guia):
    imgs = {i.nombre: i for i in imagenes(modelo_as_de_guia)}
    correcto, error = imgs["error-correcto"], imgs["error"]
    assert correcto.escena is error.escena
    assert (correcto.indice, error.indice) == (1, 2)
    assert correcto.vista == error.vista


def test_los_nudos_sin_plantilla_no_llevan_lo_de_las_plantillas(modelo_as_de_guia,
                                                                modelo_ballestrinque):
    for m in (modelo_as_de_guia, modelo_ballestrinque):
        d = datos_visor(m)
        assert "dos_remates" not in d and all("nombres" not in p for p in d["pasos"])
    assert datos_visor(modelo_ballestrinque)["anfitrion"]["tipo"] == "poste"


def test_dibujar_dos_veces_da_las_mismas_imagenes(con_chrome, modelo_as_de_guia, tmp_path):
    imgs = {i.nombre: i for i in imagenes(modelo_as_de_guia)}
    lista = [imgs["paso-2"], imgs["error"]]
    primera = dibujar(lista, tmp_path / "a")
    segunda = dibujar(lista, tmp_path / "b")
    resumen = lambda rutas: [hashlib.sha256(r.read_bytes()).hexdigest() for r in rutas]
    assert resumen(primera) == resumen(segunda)
    with Image.open(primera[0]) as im:
        assert im.size == (px(CELDA_MM[0]), px(CELDA_MM[1]))
        assert im.mode == "RGB"
        assert all(abs(v - PPP) < 0.01 for v in im.info["dpi"])
