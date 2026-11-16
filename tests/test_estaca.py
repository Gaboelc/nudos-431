"""La estaca: el mismo cilindro parado que el destorcedor, de madera y más alto, para el
tensor ajustable (formato v1.4).

El nudo de prueba no es del libro: una gaza alrededor de la estaca, cerrada con un cruce en el
que el chicote pasa por encima del firme. Es el mismo que el de tests/test_destorcedor.py."""

import math

import numpy as np
import pytest

from nudos.anfitrion import PENETRACION_MAX, Estaca, solido
from nudos.ficha import POR_DETRAS
from nudos.hoja import MADERA, hoja
from nudos.construir import construir, datos_json
from nudos.exportar import datos_escena
from nudos.imprimir import VISTA_TERMINADO, imagenes
from nudos.libre import construir_paso
from nudos.spec import TIPOS_ANFITRION, Anfitrion, SpecError, desde_datos

ESTACA = {"tipo": "estaca", "radio": 1.5, "alto": 5}
RB = 1.5 + 0.5 + 0.05   # el eje de la cuerda que lo rodea, un poco afuera


def _arco(desde, hasta, n):
    """Puntos sobre la mesa alrededor de la estaca, de un ángulo a otro, en grados."""
    return [[round(RB * math.cos(math.radians(a)), 4), round(RB * math.sin(math.radians(a)), 4)]
            for a in np.linspace(desde, hasta, n)]


def datos(**cambios):
    d = {
        "slug": "gaza-de-prueba",
        "nombre": "Gaza de prueba",
        "familia": "Gazas",
        "anfitrion": dict(ESTACA),
        "segmentos": {
            "firme": [[-18, -RB], [-12, -RB], [-6, -RB], [-2, -RB], [0, -RB]],
            "vuelta": _arco(-75, 75, 11),
            "vuelve": [[0, RB], [-2, RB], [-4.5, RB]],
            "chicote": [[-6.0, 1.85], [-7.0, 1.2], [-7.7, 0.0], [-8.3, -RB], [-8.9, -3.6],
                        [-9.4, -5.2]],
        },
        "pasos": [
            {"titulo": "Pasa la cuerda por el ojo", "texto": "Prueba.",
             "trazado": ["firme", "vuelta", "vuelve"], "secuencia": "",
             "resaltar": {"desde": "vuelta[0]", "hasta": "fin"}},
            {"titulo": "Cruza por encima del firme", "texto": "Prueba.",
             "trazado": ["firme", "vuelta", "vuelve", "chicote"], "secuencia": "1U 1O",
             "resaltar": {"desde": "vuelve[-1]", "hasta": "fin"}},
        ],
        "error": {"paso": 2, "invierte": [1], "titulo": "Por debajo", "texto": "Prueba."},
    }
    d.update(cambios)
    return d


@pytest.fixture(scope="module")
def modelo():
    return construir(desde_datos(datos()))


def _distancia_al_eje(X):
    return np.hypot(X[:, 0], X[:, 1])


# --- La especificación ------------------------------------------------------
def test_se_carga_con_su_radio_y_su_alto():
    s = desde_datos(datos())
    assert s.anfitrion == Anfitrion("estaca", radio=1.5, alto=5.0)


@pytest.mark.parametrize("anfitrion, mensaje", [
    ({"tipo": "estaca", "radio": 1.5}, "alto"),
    ({"tipo": "estaca", "radio": 1.5, "alto": 1}, "alto de la estaca.*mayor que 1"),
    ({"tipo": "estaca", "radio": 0.3, "alto": 5}, "radio de la estaca.*medio diámetro"),
    ({"tipo": "estaca", "radio": 1.5, "alto": 5, "largo": 8}, "desconocidos"),
])
def test_medidas_que_no_valen(anfitrion, mensaje):
    with pytest.raises(SpecError, match=mensaje):
        desde_datos(datos(anfitrion=anfitrion))


def test_un_segmento_sobre_el_poste_es_un_error():
    d = datos()
    d["segmentos"]["vuelta"] = {"poste": [[0, 90], [0, 0]]}
    with pytest.raises(SpecError, match="poste"):
        desde_datos(d)


# --- El sólido --------------------------------------------------------------
def test_empujar_saca_lo_que_entro_en_el_plano_de_la_mesa():
    d = Estaca(Anfitrion("estaca", radio=1.5, alto=5.0))
    X = np.array([[1.0, 0.0, 0.5], [0.0, -0.5, 3.0], [0.0, 0.0, 0.5], [5.0, 0.0, 0.5]])
    d.empujar(X, np.ones(4, bool))
    r = _distancia_al_eje(X)
    assert r[:3] == pytest.approx([d.rb] * 3)   # también el que está en el eje y el de arriba
    assert X[1, 2] == 3.0                       # la altura no cambia
    assert X[3].tolist() == [5.0, 0.0, 0.5]     # lo que está afuera no se toca
    assert d.penetracion(X) == pytest.approx(0, abs=1e-9)


def test_un_punto_fijo_no_se_empuja():
    d = Estaca(Anfitrion("estaca", radio=1.5, alto=5.0))
    X = np.array([[1.0, 0.0, 0.5]])
    d.empujar(X, np.zeros(1, bool))
    assert X[0].tolist() == [1.0, 0.0, 0.5]
    assert d.penetracion(X) == pytest.approx(d.rb - 1.0)


def test_un_trazado_que_pasa_por_dentro_sale_empujado_hasta_el_borde():
    s = desde_datos(datos(
        segmentos={"recta": [[-12, -1.0], [-4, -1.0], [0, -1.0], [4, -1.0], [12, -1.0]]},
        pasos=[{"titulo": "Recta", "texto": "Prueba.", "trazado": ["recta"], "secuencia": ""}],
        error=None))
    r = construir_paso(s.pasos[0], s.anfitrion)
    assert _distancia_al_eje(r.puntos).min() >= 2.0 - PENETRACION_MAX
    assert r.medidas["penetracion_estaca"] <= PENETRACION_MAX


# --- El nudo de prueba --------------------------------------------------------
def test_construye_sin_fallas_y_la_cuerda_no_entra(modelo):
    assert modelo.fallas == []
    todos = modelo.pasos + [modelo.error, modelo.reverso, modelo.apretado, modelo.reverso_apretado]
    for r in todos:
        assert r is not None
        assert r.medidas["penetracion_estaca"] <= PENETRACION_MAX
        assert _distancia_al_eje(r.puntos).min() >= 2.0 - PENETRACION_MAX


def test_la_gaza_abraza_a_la_estaca(modelo):
    # Por delante, la cuerda pasa por los cuatro lados de la estaca, cerca de él.
    X = modelo.pasos[-1].puntos
    cerca = X[_distancia_al_eje(X) < 2.6]
    angulos = np.degrees(np.arctan2(cerca[:, 1], cerca[:, 0]))
    assert angulos.min() < -80 and angulos.max() > 80 and (np.abs(angulos) < 10).any()


def test_por_detras_se_voltea_con_la_secuencia_invertida(modelo):
    assert modelo.pasos[-1].secuencia == ["1U", "1O"]
    assert modelo.reverso.secuencia == ["1O", "1U"]
    # Volteado como una página: el chicote, que salía a la izquierda, sale a la derecha.
    assert modelo.reverso.puntos[-1, 0] > 0 > modelo.pasos[-1].puntos[-1, 0]
    assert modelo.reverso_apretado.secuencia == ["1O", "1U"]


def test_el_apretado_acorta_la_cuerda_cerca_del_cruce(modelo):
    # Si ninguna ronda cumpliera los límites, el apretado sería el último paso tal cual.
    assert modelo.apretado is not modelo.pasos[-1]
    assert modelo.apretado.medidas["largo"] < modelo.pasos[-1].medidas["largo"] - 0.2


def test_la_escena_lleva_la_estaca(modelo):
    e = datos_escena(modelo, None, modelo.pasos)
    assert e["anfitrion"] == {"tipo": "estaca", "radio": 1.5, "alto": 5.0}
    imgs = {i.nombre: i for i in imagenes(modelo)}
    assert all(i.escena["anfitrion"]["tipo"] == "estaca" for i in imgs.values())
    # El terminado se mira como sin anfitrión: desde arriba, y por detrás, volteado con la
    # estaca, que queda en el mismo lugar.
    frente, detras = imgs["terminado-frente"], imgs["terminado-reverso"]
    assert frente.vista == detras.vista == VISTA_TERMINADO
    assert frente.escena is not detras.escena
    assert detras.escena["anfitrion"] == e["anfitrion"]


def test_la_hoja_dibuja_la_estaca_de_madera(modelo):
    datos = datos_json(modelo)
    datos["pasos"] = datos["pasos"][:1]
    sin = np.asarray(hoja(datos, "arriba"), float) / 255
    con = np.asarray(hoja(datos, "arriba", solido(modelo.spec.anfitrion).datos()), float) / 255

    def madera(im):
        return int((np.abs(im - MADERA).max(axis=2) < 0.12).sum())
    assert madera(con) > 200 > madera(sin)


def test_cada_anfitrion_dice_como_se_mira_por_detras():
    assert set(POR_DETRAS) == {None, *TIPOS_ANFITRION}
    assert "estaca" in POR_DETRAS["estaca"]
