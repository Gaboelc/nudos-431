"""El ballestrinque sobre un poste: el primer nudo sobre un anfitrión."""

import numpy as np
import pytest
import yaml

from nudos import SPECS
from nudos.anfitrion import PENETRACION_MAX, Poste, _cruces_2d
from nudos.errores import cruces_distintos
from nudos.imprimir import imagenes
from nudos.libre import LIMITES
from nudos.spec import Anfitrion, SpecError, desde_datos

POSTE = Anfitrion("poste", radio=1.5, desde=-14, hasta=14)


def leer():
    with open(SPECS / "ballestrinque.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# --- El poste -------------------------------------------------------------
def test_coordenadas_del_poste_ida_y_vuelta():
    p = Poste(POSTE)
    X = p.punto(np.array([0.0, 1.0, -2.0, 3.0]), np.array([0.0, 90.0, 180.0, -90.0]))
    # 0° arriba, 90° hacia quien ata (y negativo), 180° abajo, -90° atrás.
    assert np.allclose(X[0], [0, 0, p.zc + p.rb])
    assert np.allclose(X[1], [1, -p.rb, p.zc])
    assert np.allclose(X[2], [-2, 0, p.zc - p.rb])
    assert np.allclose(X[3], [3, p.rb, p.zc])
    x, th, r = p.cilindricas(X)
    assert np.allclose(r, p.rb)
    assert np.allclose(np.degrees(th), [0, 90, 180, -90])


def test_el_poste_se_apoya_en_la_cuerda_que_pasa_por_debajo():
    p = Poste(POSTE)
    abajo = p.punto(0.0, 180.0)
    assert abajo[2] == pytest.approx(0.5)   # el eje de la cuerda, a medio diámetro de la mesa


def test_empujar_saca_lo_que_entro_al_poste():
    p = Poste(POSTE)
    X = np.array([[0.0, 0.3, p.zc + 0.4], [0.0, -1.0, p.zc], [20.0, 0.0, p.zc]])
    p.empujar(X, np.ones(3, bool))
    _, _, r = p.cilindricas(X)
    assert r[0] == pytest.approx(p.rb) and r[1] == pytest.approx(p.rb)
    assert X[2, 0] == 20.0 and r[2] == 0.0   # fuera del largo del poste no se toca


def test_los_cruces_sobre_el_poste_se_buscan_en_la_superficie_desenrollada():
    # Dos tramos sobre la superficie que se cruzan justo donde el ángulo da la vuelta.
    periodo = 10.0
    a = np.column_stack([np.linspace(-2, 2, 21), np.full(21, 9.9)])     # casi al final de la vuelta
    b = np.column_stack([np.zeros(21), np.linspace(-1, 1, 21) + 20.0])   # dos vueltas después
    P = np.vstack([a, b])
    validos = np.ones(len(P) - 1, bool)
    validos[20] = False   # el salto entre los dos tramos no es cuerda
    assert len(_cruces_2d(P, validos, 1.0)) == 0
    assert len(_cruces_2d(P, validos, 1.0, periodo=periodo)) == 1


# --- La especificación ----------------------------------------------------
@pytest.mark.parametrize("cambio, pista", [
    ({"tipo": "argolla"}, "«tipo» es uno de: poste"),
    ({"radio": 0.2}, "al menos medio diámetro"),
    ({"desde": 14}, "«desde» va antes que «hasta»"),
    ({"alto": 3}, "campos desconocidos: alto"),
])
def test_un_poste_mal_escrito_se_detecta(cambio, pista):
    datos = leer()
    datos["anfitrion"].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos)


def test_un_segmento_sobre_el_poste_necesita_el_poste():
    datos = leer()
    del datos["anfitrion"]
    with pytest.raises(SpecError, match="no declara «anfitrion»"):
        desde_datos(datos)


def test_un_segmento_sobre_el_poste_lleva_pares_x_angulo():
    datos = leer()
    datos["segmentos"]["vuelta-1"] = {"poste": [[0.6, 100, 0]]}
    with pytest.raises(SpecError, match=r"pares \[x, ángulo\]"):
        desde_datos(datos)


# --- El nudo --------------------------------------------------------------
def test_todos_los_pasos_se_construyen_sin_fallas(modelo_ballestrinque):
    assert modelo_ballestrinque.fallas == []
    assert len(modelo_ballestrinque.pasos) == 5


def test_la_cuerda_no_atraviesa_el_poste(modelo_ballestrinque):
    for r in modelo_ballestrinque.pasos + [modelo_ballestrinque.error]:
        assert r.medidas["penetracion_poste"] <= PENETRACION_MAX, r.n


def test_los_cruces_coinciden_con_la_especificacion(modelo_ballestrinque):
    for r in modelo_ballestrinque.pasos:
        assert r.secuencia == r.esperada, r.n
        m = r.medidas
        assert m["separacion_min"] >= LIMITES["separacion_min"]
        assert m["curvatura_min"] >= LIMITES["curvatura_min"]
        assert m["estiramiento_max"] <= LIMITES["estiramiento_max"]
    assert " ".join(modelo_ballestrinque.pasos[-1].secuencia) == "1U 1O 2O 2U"


def test_los_dos_cruces_estan_sobre_el_frente_del_poste(modelo_ballestrinque):
    final = modelo_ballestrinque.pasos[-1]
    assert set(final.cruces) == {"1", "2"}
    for x, y in final.cruces.values():
        assert -3 < x < 2 and -2.6 < y < 0   # por delante del eje, del lado de quien ata


def test_el_error_es_el_chicote_por_encima_de_la_diagonal(modelo_ballestrinque):
    correcto = modelo_ballestrinque.pasos[4]
    assert cruces_distintos(correcto.secuencia, modelo_ballestrinque.error.secuencia) == {"2"}


def test_el_nudo_terminado_se_mira_por_delante_y_desde_atras(modelo_ballestrinque):
    assert modelo_ballestrinque.reverso is None   # sobre un poste no se voltea
    imgs = {i.nombre: i for i in imagenes(modelo_ballestrinque)}
    frente, detras = imgs["terminado-frente"], imgs["terminado-reverso"]
    assert (frente.vista, detras.vista) == ("3d", "detras")
    assert frente.escena is detras.escena
    assert frente.escena["anfitrion"]["tipo"] == "poste"
    assert all(i.escena["anfitrion"] for i in imgs.values())
