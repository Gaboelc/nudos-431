"""La hoja de revisión dibuja el poste y la cruz, y centra la vista inclinada en el nudo."""
import numpy as np
import pytest

from nudos.anfitrion import solido
from nudos.construir import construir, datos_json
from nudos.hoja import AZUL, MADERA, _altura, _encuadre, _palos, hoja
from nudos.spec import cargar


def _madera(im):
    im = np.asarray(im, float) / 255
    return int((np.abs(im - MADERA).max(axis=2) < 0.12).sum())


@pytest.fixture(scope="module")
def ballestrinque():
    modelo = construir(cargar("ballestrinque"))
    datos = datos_json(modelo)
    return datos, solido(modelo.spec.anfitrion).datos()


def test_la_hoja_dibuja_el_poste_de_madera(ballestrinque):
    datos, anfitrion = ballestrinque
    datos = {**datos, "pasos": datos["pasos"][:1]}
    assert _madera(hoja(datos, "arriba", anfitrion)) > 2000 > _madera(hoja(datos, "arriba"))


def test_el_poste_se_corta_en_el_encuadre(ballestrinque):
    datos, anfitrion = ballestrinque
    x0, x1, y0, y1 = _encuadre(datos)
    puntos, color, _ = _palos({**anfitrion, "desde": -500.0, "hasta": 500.0}, x0, x1, y0, y1)
    assert color is MADERA
    assert x0 - 3 < puntos[:, 0].min() and puntos[:, 0].max() < x1 + 3


def test_la_hoja_dibuja_los_dos_palos_de_la_cruz():
    a = {"tipo": "cruz", "radio": 2.0, "largo": 20.0, "z_abajo": 3.0, "z_arriba": 7.0}
    puntos, _, _ = _palos(a, -6.0, 6.0, -6.0, 6.0)
    de_abajo = np.abs(puntos[:, 2] - 3.0) <= 2.0
    assert np.ptp(puntos[de_abajo, 1]) > 10 and np.ptp(puntos[~de_abajo, 0]) > 10


def test_la_vista_inclinada_se_centra_a_la_altura_del_nudo(ballestrinque):
    datos, anfitrion = ballestrinque
    z = _altura(datos, *_encuadre(datos))
    assert z > 1.0      # el nudo va sobre el poste, por encima de la mesa
    datos = {**datos, "pasos": datos["pasos"][-1:]}
    im = np.asarray(hoja(datos, "55", anfitrion), float) / 255
    cuerda = np.abs(im - AZUL).max(axis=2) < 0.25
    filas = np.nonzero(cuerda.any(axis=1))[0]
    assert len(filas) and filas.min() < im.shape[0] / 2 < filas.max()
