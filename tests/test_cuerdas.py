"""Varias cuerdas: cortes entre ellas, radio de cada una y separación por la suma de los
radios, y cómo se dibujan. Con cuerdas sintéticas, sin un nudo real."""
from dataclasses import replace

import numpy as np
import pytest

from PIL import Image

from nudos import hoja
from nudos.construir import _resultado_json, construir
from nudos.cruces import encontrar_cruces
from nudos.exportar import datos_escena
from nudos.ficha import html_ficha
from nudos.imprimir import ImpresionError, chrome, dibujar, imagenes, nombres, terminado
from nudos.libre import (LIMITES, R, Reparto, TrazadoError, _fallas, _separacion, _texto,
                         construir_paso, curvatura_min,
                         separacion_min)
from nudos.spec import desde_datos

GRUESA = 1.6


def dos_cuerdas(trazado, secuencia, segmentos, **paso):
    return desde_datos({
        "slug": "prueba", "nombre": "Prueba", "familia": "De unión",
        "cuerdas": [{"nombre": "gruesa", "grosor": GRUESA, "color": "azul"},
                    {"nombre": "delgada", "grosor": 1, "color": "crema"}],
        "segmentos": segmentos,
        "pasos": [{"titulo": "T", "texto": "X.", "trazado": trazado, "secuencia": secuencia, **paso}],
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
                                 [2, 6], [2, 12]]},
                     resaltar={"desde": "vuelta[3]", "hasta": "fin"})


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


def test_la_separacion_dice_donde_ocurre():
    # Dos tramos de una cuerda: uno recto y otro en V, que se acerca más en x = 5.
    x = np.arange(0, 10.01, 0.2)
    recto = np.column_stack([x, np.zeros_like(x), np.full_like(x, 0.5)])
    v = np.column_stack([x[::-1], 0.9 + 0.2 * np.abs(x[::-1] - 5), np.full_like(x, 0.5)])
    X = np.vstack([recto, [[12.0, 3.0, 0.5]], v])
    separacion, donde = _separacion(X, 0.2, Reparto(np.zeros(len(X), int), np.ones(len(X))))
    assert separacion == pytest.approx(0.9)
    assert donde[:2] == pytest.approx([5.0, 0.45])


def test_las_fallas_dicen_donde_ocurren():
    medidas = {"separacion_min": 0.5, "curvatura_min": 0.5, "estiramiento_max": 0.05}
    fallas = _fallas(2, ("«1O»", "«1O»"), medidas, np.array([1.0, 2.0, 0]),
                     np.array([3.0, 4.0, 0]), np.array([5.0, 6.0, 0]))
    assert fallas == [
        "Paso 2: dos tramos quedan a 0.50 diámetros cerca de (3.0, 4.0); el mínimo es 0.97.",
        "Paso 2: la cuerda se dobla con radio 0.50 cerca de (1.0, 2.0); el mínimo es 0.9.",
        "Paso 2: la cuerda se estira 5.0% cerca de (5.0, 6.0); el máximo es 2%."]


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


# --------------------------------------------------------------------------
# Escena, impresión y hoja de revisión
# --------------------------------------------------------------------------
def test_la_escena_lleva_cada_cuerda(tejida):
    datos = datos_escena(tejida, None, tejida.pasos)
    assert datos["cuerdas"] == [
        {"nombre": "gruesa", "etiqueta": "Gruesa", "grosor": GRUESA, "color": "azul"},
        {"nombre": "delgada", "etiqueta": "Delgada", "grosor": 1.0, "color": "crema"}]
    paso = datos["pasos"][0]
    assert "p" not in paso and len(paso["cuerdas"]) == 2
    r = tejida.pasos[0]
    for c, (i0, i1) in zip(paso["cuerdas"], r.reparto.tramos):
        # Uno de cada dos puntos de esa cuerda, y su último punto.
        assert len(c["p"]) == 3 * len(range(i0, i1 + 1, 2)) + 3 * ((i1 - i0) % 2)
        assert c["p"][-3:] == [round(float(v), 3) for v in r.puntos[i1]]
    # El resaltado es de la delgada, medido a lo largo de ella, y por eso lleva «Chicote».
    gruesa, delgada = paso["cuerdas"]
    assert gruesa["hl"] is None
    assert 0 < delgada["hl"][0] < delgada["hl"][1] == 1.0
    assert paso["chicote"] == 1


def test_sin_resaltado_el_chicote_es_el_de_la_ultima_que_se_movio(tejida):
    datos = datos_escena(tejida, None, [tejida.reverso])
    assert [c["hl"] for c in datos["pasos"][0]["cuerdas"]] == [None, None]
    assert datos["pasos"][0]["chicote"] == 1


def test_una_cuerda_no_cambia_la_escena(modelo_as_de_guia):
    datos = datos_escena(modelo_as_de_guia, None, modelo_as_de_guia.pasos[:1])
    assert "cuerdas" not in datos
    assert set(datos["pasos"][0]) == {"n", "hl", "p"}


def test_las_imagenes_nombran_cada_cuerda(tejida, modelo_as_de_guia):
    assert nombres(tejida) == ("cuerda-gruesa", "cuerda-delgada", "chicote")
    assert nombres(tejida, chicote=False) == ("cuerda-gruesa", "cuerda-delgada")
    assert nombres(modelo_as_de_guia) == ("firme", "chicote")
    assert {i.nombres for i in imagenes(tejida)} == {nombres(tejida)}


def test_la_hoja_dibuja_cada_cuerda_con_su_radio_y_su_color(tejida):
    r = tejida.pasos[0]
    datos = {"encuadre": None, "cuerdas": [{"nombre": c.nombre, "grosor": c.grosor, "color": c.color}
                                          for c in tejida.spec.cuerdas],
             "pasos": [{"n": 1, **_resultado_json(r)}]}
    p = datos["pasos"][0]
    gruesa, delgada = hoja._cuerdas(datos, p)
    assert (gruesa[1], delgada[1]) == (GRUESA * R, R)
    assert gruesa[2] is hoja.AZUL and delgada[2] is hoja.CREMA
    assert len(gruesa[0]) + len(delgada[0]) == len(r.puntos)
    assert gruesa[3] is None
    # El resaltado de la delgada, a lo largo de la delgada.
    i0 = r.reparto.tramos[1][0]
    assert delgada[3] == pytest.approx([s - i0 * p["h"] for s in p["resaltado"]])
    assert hoja.hoja(datos).size[0] == hoja.COLUMNAS * hoja.ANCHO


@pytest.fixture(scope="module")
def con_chrome():
    try:
        with chrome():
            pass
    except ImpresionError as e:
        pytest.skip(str(e))


def test_las_dos_cuerdas_se_dibujan_con_su_color(con_chrome, tejida, tmp_path):
    # El último paso sin resaltado, como el terminado antes de T7c: apretado, la vuelta de la
    # delgada se cierra sobre la gruesa y se ve menos de ella.
    frente = terminado(tejida, tejida.pasos[-1], tejida.reverso)[0]
    [ruta] = dibujar([frente], tmp_path)
    with Image.open(ruta) as im:
        rgb = np.asarray(im.convert("RGB"), int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    azul = (b > r + 60).sum()
    crema = ((r > 180) & (g > 170) & (b > 140) & (r - b > 15)).sum()
    assert azul > 5000 and crema > 5000, (azul, crema)


def test_la_ficha_explica_que_cada_cuerda_lleva_su_nombre(modelo_as_de_guia):
    una = html_ficha(modelo_as_de_guia)
    assert "Ves la cuerda sobre la mesa" in una
    dos = html_ficha(replace(modelo_as_de_guia, spec=replace(modelo_as_de_guia.spec, cuerdas=TEJIDA.cuerdas)))
    assert "Ves las cuerdas sobre la mesa" in dos and "cada una con su nombre junto a su firme" in dos
