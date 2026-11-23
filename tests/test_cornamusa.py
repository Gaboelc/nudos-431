"""La cornamusa: una barra con dos cuernos sobre un pie, fija a la mesa, para la vuelta de
cornamusa (formato v1.12).

El nudo de prueba no es del libro: el firme sube a la barra y la cruza en diagonal, rodea el
cuerno derecho por debajo y, en el paso 2, vuelve por delante y pasa bajo el cuerno izquierdo,
por debajo de la diagonal. Ese cruce es entre un tramo sobre la barra y uno sobre la mesa."""

import numpy as np
import pytest

from nudos.anfitrion import PENETRACION_MAX, Cornamusa, Poste, solido, sobre_superficie
from nudos.construir import construir, datos_json
from nudos.exportar import datos_escena
from nudos.ficha import POR_DETRAS
from nudos.hoja import GRIS, hoja
from nudos.imprimir import imagenes
from nudos.spec import HUECO_CORNAMUSA, PIE_CORNAMUSA, TIPOS_ANFITRION, Anfitrion, SpecError, desde_datos

CORNAMUSA = {"tipo": "cornamusa", "radio": 1, "largo": 16}


def datos(**cambios):
    d = {
        "slug": "vuelta-en-una-cornamusa", "nombre": "Prueba", "familia": "De sujeción",
        "anfitrion": dict(CORNAMUSA),
        "encuadre": {"x": [-12.0, 10.0], "y": [-8.0, 7.0]},
        "segmentos": {
            # El firme llega por delante, a la izquierda, y sube a la barra.
            "firme": [[-16, -6.5], [-11, -5.2], [-8.6, -3.8], [-7.2, -2.6]],
            # La cruza en diagonal, baja por detrás y rodea el cuerno derecho por debajo.
            "diagonal": {"cornamusa": [[-5.8, 120], [-5.0, 85], [-3.2, 45], [0.0, 0], [3.2, -45],
                                       [4.8, -85], [5.4, -130], [5.9, -180]]},
            "sale-1": [[6.3, -1.6], [6.3, -3.4], [6.0, -5.2]],
            # Vuelve por delante y pasa bajo el cuerno izquierdo, por debajo de la diagonal.
            "delante": [[6.3, -1.6], [6.0, -3.4], [5.0, -4.6], [3.6, -4.7], [1.5, -3.9],
                        [-1.5, -3.0], [-3.6, -2.4], [-4.5, -1.1], [-4.7, 0.4], [-4.5, 1.9],
                        [-5.2, 3.4], [-6.2, 5.0]],
        },
        "pasos": [
            {"titulo": "Cruza por encima", "texto": "Prueba.",
             "trazado": ["firme", "diagonal", "sale-1"], "secuencia": ""},
            {"titulo": "Pasa bajo el otro cuerno", "texto": "Prueba.",
             "trazado": ["firme", "diagonal", "delante"], "secuencia": "1O 1U"},
        ],
    }
    d.update(cambios)
    return d


@pytest.fixture(scope="module")
def modelo():
    return construir(desde_datos(datos()))


# --- La especificación ------------------------------------------------------
def test_se_carga_con_su_radio_y_su_largo():
    s = desde_datos(datos())
    assert s.anfitrion == Anfitrion("cornamusa", radio=1.0, largo=16.0)
    assert not s.anfitrion.en_la_mesa


@pytest.mark.parametrize("anfitrion, mensaje", [
    ({"tipo": "cornamusa", "radio": 1}, "largo"),
    ({"tipo": "cornamusa", "radio": 1, "largo": 8}, "largo.*de al menos 10"),
    ({"tipo": "cornamusa", "radio": 0.3, "largo": 16}, "radio de la cornamusa.*medio diámetro"),
    ({"tipo": "cornamusa", "radio": 1, "largo": 16, "alto": 3}, "desconocidos"),
])
def test_medidas_que_no_valen(anfitrion, mensaje):
    with pytest.raises(SpecError, match=mensaje):
        desde_datos(datos(anfitrion=anfitrion))


def test_la_cuerda_no_pasa_por_el_pie():
    d = datos()
    d["segmentos"]["sale-1"] = [[6.3, -1.6], [1.0, 0.3], [6.0, -5.2]]
    with pytest.raises(SpecError, match="dentro del pie"):
        desde_datos(d)
    d = datos()
    d["segmentos"]["diagonal"]["cornamusa"][-1] = [1.0, -180]
    with pytest.raises(SpecError, match="donde está el pie"):
        desde_datos(d)


def test_sobre_la_cornamusa_los_segmentos_se_escriben_cornamusa():
    d = datos()
    d["segmentos"]["diagonal"] = {"poste": d["segmentos"]["diagonal"]["cornamusa"]}
    with pytest.raises(SpecError, match=r"\{cornamusa: \[\[x, ángulo\]"):
        desde_datos(d)


# --- El sólido --------------------------------------------------------------
def test_la_barra_se_apoya_en_la_cuerda_como_el_poste():
    c = Cornamusa(Anfitrion("cornamusa", radio=1.0, largo=16.0))
    assert c.zc == pytest.approx(HUECO_CORNAMUSA + 1.0) == pytest.approx(2.0)
    assert c.punto(4.0, 180.0)[2] == pytest.approx(0.5)   # bajo un cuerno, sobre la mesa
    p = Poste(Anfitrion("poste", radio=1.0, desde=-8, hasta=8))
    assert np.allclose(c.punto(np.array([0.0, 2.0]), np.array([30.0, -120.0])),
                       p.punto(np.array([0.0, 2.0]), np.array([30.0, -120.0])))


def test_empujar_saca_lo_que_entro_en_la_barra_y_en_el_pie():
    c = Cornamusa(Anfitrion("cornamusa", radio=1.0, largo=16.0))
    X = np.array([[4.0, 0.3, 2.4], [0.0, -0.8, 0.5], [7.6, 0.0, 2.0], [0.0, 0.0, 0.5],
                  [12.0, 0.0, 2.0], [4.0, 0.0, 0.5]])
    assert c.penetracion(X) > 1
    c.empujar(X, np.ones(len(X), bool))
    assert c.penetracion(X) == pytest.approx(0, abs=1e-9)
    assert X[1, 2] == pytest.approx(0.5) and X[1, 1] < -1.4   # el pie empuja de lado
    assert X[2, 0] == pytest.approx(8.5)                        # la punta redonda del cuerno
    assert X[4].tolist() == [12.0, 0.0, 2.0]                    # lo de afuera no se toca
    assert X[5].tolist() == [4.0, 0.0, 0.5]                     # bajo el cuerno cabe la cuerda


def test_mas_alla_de_los_cuernos_hay_gravedad():
    c = Cornamusa(Anfitrion("cornamusa", radio=1.0, largo=16.0))
    _, _, r = c.cilindricas(np.array([[0.0, 0.0, 4.0], [14.0, 0.0, 2.0]]))
    assert r[0] == pytest.approx(2.0) and r[1] == pytest.approx(7.0)


def test_el_poste_sigue_siendo_el_poste():
    assert type(sobre_superficie(Anfitrion("poste", radio=1.5, desde=-4, hasta=4))) is Poste
    a = Anfitrion("cornamusa", radio=1.0, largo=16.0)
    assert type(sobre_superficie(a)) is Cornamusa and type(solido(a)) is Cornamusa


# --- El nudo de prueba --------------------------------------------------------
def test_construye_sin_fallas_y_la_cuerda_no_entra(modelo):
    assert modelo.fallas == []
    c = Cornamusa(modelo.spec.anfitrion)
    for r in modelo.pasos + [modelo.apretado]:
        assert r.medidas["penetracion_cornamusa"] <= PENETRACION_MAX
        assert c.penetracion(r.puntos) <= PENETRACION_MAX


def test_el_cruce_bajo_el_cuerno_se_busca_desde_arriba(modelo):
    # La diagonal pasa sobre el cuerno izquierdo y la vuelta por debajo de él: la barra los
    # separa, así que la diagonal va encima y no se eleva sobre la otra.
    r = modelo.pasos[1]
    assert r.secuencia == ["1O", "1U"]
    x, y = r.cruces["1"]
    assert -6 < x < -3.5 and abs(y) < 1.5
    assert r.puntos[:, 2].max() < Cornamusa(modelo.spec.anfitrion).zc + 1.5 + 0.1


def test_como_sobre_el_poste_no_hay_reverso_y_se_mira_desde_el_otro_lado(modelo):
    assert modelo.reverso is None and modelo.apretado is not None
    imgs = {i.nombre: i for i in imagenes(modelo)}
    assert imgs["terminado-reverso"].vista == "detras"
    assert imgs["terminado-frente"].escena["anfitrion"]["tipo"] == "cornamusa"
    e = datos_escena(modelo, None, modelo.pasos)
    assert e["anfitrion"] == {"tipo": "cornamusa", "radio": 1.0, "largo": 16.0, "z": 2.0,
                              "pie": PIE_CORNAMUSA}


def test_cada_anfitrion_dice_como_se_mira_por_detras():
    assert set(POR_DETRAS) == {None, *TIPOS_ANFITRION}
    assert "cornamusa" in POR_DETRAS["cornamusa"]


def test_la_hoja_dibuja_la_cornamusa_gris(modelo):
    d = datos_json(modelo)
    d["pasos"] = d["pasos"][:1]
    sin = np.asarray(hoja(d, "arriba"), float) / 255
    con = np.asarray(hoja(d, "arriba", solido(modelo.spec.anfitrion).datos()), float) / 255

    def gris(im):
        return int((np.abs(im - GRIS).max(axis=2) < 0.1).sum())
    assert gris(con) > gris(sin) + 1000   # la mesa también es gris: se cuenta lo que agrega
