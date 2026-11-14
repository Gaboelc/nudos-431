"""El destorcedor: un cilindro corto parado sobre la mesa, para el nudo aguja (formato v1.3).

El nudo de prueba no es del libro: una gaza alrededor del destorcedor, cerrada con un cruce
en el que el chicote pasa por encima del firme."""

import math

import numpy as np
import pytest

from nudos.anfitrion import PENETRACION_MAX, Destorcedor
from nudos.construir import construir
from nudos.exportar import datos_escena
from nudos.imprimir import VISTA_TERMINADO, imagenes
from nudos.libre import construir_paso
from nudos.spec import Anfitrion, SpecError, desde_datos

DESTORCEDOR = {"tipo": "destorcedor", "radio": 1.5, "alto": 2}
RB = 1.5 + 0.5 + 0.05   # el eje de la cuerda que lo rodea, un poco afuera


def _arco(desde, hasta, n):
    """Puntos sobre la mesa alrededor del destorcedor, de un ángulo a otro, en grados."""
    return [[round(RB * math.cos(math.radians(a)), 4), round(RB * math.sin(math.radians(a)), 4)]
            for a in np.linspace(desde, hasta, n)]


def datos(**cambios):
    d = {
        "slug": "gaza-de-prueba",
        "nombre": "Gaza de prueba",
        "familia": "Gazas",
        "anfitrion": dict(DESTORCEDOR),
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
    assert s.anfitrion == Anfitrion("destorcedor", radio=1.5, alto=2.0)


@pytest.mark.parametrize("anfitrion, mensaje", [
    ({"tipo": "destorcedor", "radio": 1.5}, "alto"),
    ({"tipo": "destorcedor", "radio": 1.5, "alto": 1}, "mayor que 1"),
    ({"tipo": "destorcedor", "radio": 0.3, "alto": 2}, "medio diámetro"),
    ({"tipo": "destorcedor", "radio": 1.5, "alto": 2, "desde": -3}, "desconocidos"),
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
    d = Destorcedor(Anfitrion("destorcedor", radio=1.5, alto=2.0))
    X = np.array([[1.0, 0.0, 0.5], [0.0, -0.5, 3.0], [0.0, 0.0, 0.5], [5.0, 0.0, 0.5]])
    d.empujar(X, np.ones(4, bool))
    r = _distancia_al_eje(X)
    assert r[:3] == pytest.approx([d.rb] * 3)   # también el que está en el eje y el de arriba
    assert X[1, 2] == 3.0                       # la altura no cambia
    assert X[3].tolist() == [5.0, 0.0, 0.5]     # lo que está afuera no se toca
    assert d.penetracion(X) == pytest.approx(0, abs=1e-9)


def test_un_punto_fijo_no_se_empuja():
    d = Destorcedor(Anfitrion("destorcedor", radio=1.5, alto=2.0))
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
    assert r.medidas["penetracion_destorcedor"] <= PENETRACION_MAX


# --- El nudo de prueba --------------------------------------------------------
def test_construye_sin_fallas_y_la_cuerda_no_entra(modelo):
    assert modelo.fallas == []
    todos = modelo.pasos + [modelo.error, modelo.reverso, modelo.apretado, modelo.reverso_apretado]
    for r in todos:
        assert r is not None
        assert r.medidas["penetracion_destorcedor"] <= PENETRACION_MAX
        assert _distancia_al_eje(r.puntos).min() >= 2.0 - PENETRACION_MAX


def test_la_gaza_abraza_al_destorcedor(modelo):
    # Por delante, la cuerda pasa por los cuatro lados del destorcedor, cerca de él.
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


def test_la_escena_lleva_el_destorcedor(modelo):
    e = datos_escena(modelo, None, modelo.pasos)
    assert e["anfitrion"] == {"tipo": "destorcedor", "radio": 1.5, "alto": 2.0}
    imgs = {i.nombre: i for i in imagenes(modelo)}
    assert all(i.escena["anfitrion"]["tipo"] == "destorcedor" for i in imgs.values())
    # El terminado se mira como sin anfitrión: desde arriba, y por detrás, volteado.
    frente, detras = imgs["terminado-frente"], imgs["terminado-reverso"]
    assert frente.vista == detras.vista == VISTA_TERMINADO
    assert frente.escena is not detras.escena
