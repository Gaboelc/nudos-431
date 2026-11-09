"""Geometría de varias cuerdas: cortes entre ellas, radio de cada una y separación por
la suma de los radios. Con cuerdas sintéticas, sin un nudo real."""
import numpy as np
import pytest

from nudos.construir import construir
from nudos.cruces import encontrar_cruces
from nudos.libre import (LIMITES, R, Reparto, TrazadoError, _texto, construir_paso, curvatura_min,
                         separacion_min)
from nudos.spec import desde_datos

GRUESA = 1.6


def dos_cuerdas(trazado, secuencia, segmentos):
    return desde_datos({
        "slug": "prueba", "nombre": "Prueba", "familia": "De unión",
        "cuerdas": [{"nombre": "gruesa", "grosor": GRUESA, "color": "azul"},
                    {"nombre": "delgada", "grosor": 1, "color": "crema"}],
        "segmentos": segmentos,
        "pasos": [{"titulo": "T", "texto": "X.", "trazado": trazado, "secuencia": secuencia}],
    })


RECTA = [[-12, 0], [-6, 0], [0, 0], [6, 0], [12, 0]]
# La delgada baja desde el fondo de la mesa y pasa sobre la gruesa.
ENCIMA = dos_cuerdas({"gruesa": ["recta"], "delgada": ["baja"]}, {"gruesa": "1U", "delgada": "1O"},
                     {"recta": RECTA, "baja": [[0, 12], [0, 6], [0, 0], [0, -6], [0, -12]]})
# La delgada cruza dos veces: por encima, da la vuelta y vuelve por debajo. Su firme está
# arriba a la derecha, así que el corte entre el final de la gruesa (12, 0) y ese firme
# atravesaría el tramo que sube, si contara como cuerda.
TEJIDA = dos_cuerdas({"gruesa": ["recta"], "delgada": ["vuelta"]},
                     {"gruesa": "1U 2O", "delgada": "1O 2U"},
                     {"recta": RECTA,
                      "vuelta": [[-2, 12], [-2, 6], [-2, 0], [-2, -4], [0, -6], [2, -4], [2, 0],
                                 [2, 6], [2, 12]]})


@pytest.fixture(scope="module")
def encima():
    return construir(ENCIMA)


@pytest.fixture(scope="module")
def tejida():
    return construir(TEJIDA)


def test_la_delgada_se_apoya_sobre_la_gruesa(encima):
    assert encima.fallas == []
    r = encima.pasos[0]
    gruesa, delgada = r.reparto.cuerda == 0, r.reparto.cuerda == 1
    z = r.puntos[:, 2]
    # Cada cuerda se apoya en la mesa según su radio.
    assert z[gruesa] == pytest.approx(GRUESA * R, abs=0.02)
    assert z[delgada].min() == pytest.approx(R, abs=0.02)
    # En el cruce, la delgada queda encima de la gruesa, tocándola.
    assert z[delgada].max() == pytest.approx(2 * GRUESA * R + R, abs=0.05)


def test_cada_firme_queda_fijo(tejida):
    r = tejida.pasos[0]
    for i, (x, y) in zip(r.reparto.inicios, [(-12, 0), (-2, 12)]):
        assert r.puntos[i, :2] == pytest.approx([x, y])


def test_el_corte_entre_cuerdas_no_es_cuerda(tejida):
    """Si el corte contara, habría un tercer cruce y el paso no se construiría."""
    assert tejida.fallas == []
    r = tejida.pasos[0]
    assert r.secuencia == r.esperada == ["1U", "2O", "1O", "2U"]
    assert len(encontrar_cruces(r.puntos, r.h)) == 3   # contando el corte
    assert len(encontrar_cruces(r.puntos, r.h, r.reparto.seguido)) == 2
    # Ninguna medida mira el corte: el estiramiento es el de la cuerda, no el del salto.
    assert r.medidas["estiramiento_max"] <= LIMITES["estiramiento_max"]
    largo = sum(np.linalg.norm(np.diff(r.puntos[r.reparto.cuerda == k], axis=0), axis=1).sum()
                for k in (0, 1))
    assert r.medidas["largo"] == pytest.approx(largo)


def test_la_gruesa_sube_sobre_la_delgada_donde_va_encima(tejida):
    r = tejida.pasos[0]
    gruesa = r.reparto.cuerda == 0
    # En el cruce 2 la gruesa va por encima: sube hasta quedar sobre la delgada.
    assert r.puntos[gruesa, 2].max() == pytest.approx(2 * R + GRUESA * R, abs=0.05)


def test_el_reverso_invierte_los_cruces_entre_cuerdas(tejida):
    assert tejida.reverso is not None
    assert tejida.reverso.secuencia == ["1O", "2U", "1U", "2O"]


def test_la_separacion_usa_la_suma_de_los_radios():
    # Dos tramos paralelos, uno de cada cuerda, a 1,3 diámetros: se tocan justo.
    x = np.arange(0, 10, 0.2)
    X = np.vstack([np.column_stack([x, np.zeros_like(x), np.full_like(x, 0.8)]),
                   np.column_stack([x, np.full_like(x, 1.3), np.full_like(x, 0.8)])])
    cuerda = np.repeat([0, 1], len(x))
    rep = Reparto(cuerda, np.where(cuerda == 0, GRUESA, 1.0))
    assert separacion_min(X, 0.2, rep) == pytest.approx(1.0)
    # Con una sola cuerda de grosor 1, esos tramos no se tocan.
    assert separacion_min(X, 0.2) > 1.0


def test_la_curvatura_se_mide_en_diametros_de_cada_cuerda():
    """Una vuelta que en la cuerda de siempre queda como se dibujó, en una cuerda 1,6
    veces más gruesa se abre hasta el radio mínimo de esa cuerda, en sus diámetros."""
    vuelta = [[-8, -3], [-3, -3], [0, -3], [3, 0], [0, 3], [-3, 3], [-8, 3]]
    radios = []
    for grosor in (1.0, GRUESA):
        spec = desde_datos({
            "slug": "prueba", "nombre": "Prueba", "familia": "De unión",
            "cuerdas": [{"nombre": "vuelta", "grosor": grosor, "color": "azul"},
                        {"nombre": "lejos", "grosor": 1, "color": "crema"}],
            "segmentos": {"vuelta": vuelta, "lejos": [[12, -8], [12, 8]]},
            "pasos": [{"titulo": "T", "texto": "X.",
                       "trazado": {"vuelta": ["vuelta"], "lejos": ["lejos"]},
                       "secuencia": {"vuelta": "", "lejos": ""}}],
        })
        r = construir(spec).pasos[0]
        absoluto, _ = curvatura_min(r.puntos[r.reparto.cuerda == 0], r.h, ventana=1)
        assert r.medidas["curvatura_min"] == pytest.approx(absoluto / grosor)
        radios.append(absoluto)
    delgada, gruesa = radios
    assert delgada < 1.1 * GRUESA                      # la vuelta, como se dibujó
    assert gruesa > 1.1 * GRUESA * 0.95 > delgada      # abierta según el grosor


def test_cada_pasada_va_en_su_cuerda():
    """Los mismos cruces, en el mismo orden, pero en otra cuerda: no es el mismo paso."""
    # La delgada se cruza consigo misma; la secuencia dice que el cruce es de la gruesa.
    rizo = [[-6, 8], [-6, 2], [-4, -2], [0, -3], [3, -1], [3, 2], [0, 3], [-3, 0], [-4, -6], [-4, -12]]
    spec = dos_cuerdas({"gruesa": ["recta"], "delgada": ["rizo"]},
                       {"gruesa": "1O 1U", "delgada": ""},
                       {"recta": [[-12, 14], [12, 14]], "rizo": rizo})
    with pytest.raises(TrazadoError, match="gruesa 0 y delgada 2; la secuencia declara gruesa 2 y delgada 0"):
        construir_paso(spec.pasos[0], None, spec.cuerdas)


def test_la_secuencia_se_escribe_por_cuerda():
    assert _texto(["1O", "2U", "1U", "2O"]) == "«1O 2U 1U 2O»"
    assert (_texto(["1O", "2U", "1U", "2O"], ("gruesa", "delgada"), (2, 2))
            == "gruesa «1O 2U», delgada «1U 2O»")
