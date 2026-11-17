"""Los palos paralelos, el anfitrión del amarre redondo y del trípode (nudos/anfitrion.py, Palos)."""
import copy

import numpy as np
import pytest

from nudos.anfitrion import DEBAJO, HUECO, PENETRACION_MAX, Palos, solido
from nudos.ficha import POR_DETRAS
from nudos.hoja import MADERA, _palos
from nudos.libre import R
from nudos.spec import TIPOS_ANFITRION, Anfitrion, SpecError, desde_datos

DOS = Anfitrion("palos", radio=2.5, largo=30, cantidad=2)
TRES = Anfitrion("palos", radio=2.5, largo=30, cantidad=3)


def datos(**cambios):
    base = {
        "slug": "amarre-redondo", "nombre": "Amarre redondo", "familia": "Amarres",
        "anfitrion": {"tipo": "palos", "cantidad": 2, "radio": 2.5, "largo": 30},
        "plantilla": {"tipo": "amarre-redondo", "vueltas": 6, "ahorcados": 2},
        "pasos": [{"titulo": "Paso", "texto": "Texto.", "hasta": "cierre"}],
    }
    base.update(copy.deepcopy(cambios))
    return base


def test_la_especificacion_se_lee():
    a = desde_datos(datos()).anfitrion
    assert (a.tipo, a.cantidad, a.radio, a.largo) == ("palos", 2, 2.5, 30)
    assert "palos" in TIPOS_ANFITRION


@pytest.mark.parametrize("anfitrion, pista", [
    ({"tipo": "palos", "radio": 2.5, "largo": 30}, "cantidad"),
    ({"tipo": "palos", "cantidad": 1, "radio": 2.5, "largo": 30}, "cantidad"),
    ({"tipo": "palos", "cantidad": 4, "radio": 2.5, "largo": 30}, "cantidad"),
    ({"tipo": "palos", "cantidad": 2.0, "radio": 2.5, "largo": 30}, "cantidad"),
    ({"tipo": "palos", "cantidad": 2, "radio": 2.5}, "largo"),
    ({"tipo": "palos", "cantidad": 2, "radio": 2.5, "largo": 5}, "mayor que su grosor"),
    ({"tipo": "palos", "cantidad": 2, "radio": 0.3, "largo": 30}, "medio diámetro"),
])
def test_unos_palos_mal_escritos_se_detectan(anfitrion, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(anfitrion=anfitrion))


def test_cada_plantilla_pide_su_numero_de_palos():
    tres = {"tipo": "palos", "cantidad": 3, "radio": 2.5, "largo": 30}
    with pytest.raises(SpecError, match="va sobre 2 palos"):
        desde_datos(datos(anfitrion=tres))
    with pytest.raises(SpecError, match="va sobre 3 palos"):
        desde_datos(datos(plantilla={"tipo": "amarre-tripode", "vueltas": 6, "ahorcados": 2}))


def test_los_palos_van_con_una_plantilla():
    d = datos(segmentos={"a": [[0, 0], [1, 0]]}, pasos=[{"titulo": "P", "texto": "T.",
                                                       "trazado": ["a"], "secuencia": ""}])
    del d["plantilla"]
    with pytest.raises(SpecError, match="va con una plantilla"):
        desde_datos(d)


def test_donde_van_los_palos():
    for a, ys in ((DOS, [-3.05, 3.05]), (TRES, [-6.1, 0.0, 6.1])):
        p = Palos(a)
        assert np.allclose(p.ys, ys)
        assert p.zc == pytest.approx(a.radio + DEBAJO)
        # Entre dos palos vecinos queda el hueco, y su centro, a medio camino.
        assert np.allclose(np.diff(p.ys) - 2 * a.radio, HUECO)
        assert np.allclose(p.huecos, (np.array(ys[:-1]) + ys[1:]) / 2)
    # Una cuerda en el medio del hueco, a la altura de los ejes, cabe entre los dos palos.
    p = Palos(DOS)
    assert p.penetracion(np.array([[0.0, 0.0, p.zc]])) == 0.0
    x, th, r = p.cilindricas(0, p.punto(0, np.array([1.0, 2.0]), np.array([90.0, 180.0])))
    assert np.allclose(x, [1, 2]) and np.allclose(np.degrees(th), [90, 180]) and np.allclose(r, p.rb)


def test_empujar_saca_lo_que_entro_a_cualquier_palo():
    p = Palos(TRES)
    X = np.array([[1.0, 6.1, p.zc + 1.0], [0.0, -6.1, p.zc - 2.0], [20.0, 0.0, p.zc],
                  [0.0, 3.05, p.zc]])
    assert p.penetracion(X) == pytest.approx(p.rb - 1.0)
    p.empujar(X, np.ones(4, bool))
    assert p.penetracion(X) == pytest.approx(0, abs=1e-9)
    assert np.allclose(X[2], [20, 0, p.zc])        # fuera del largo de los palos no se toca
    assert np.allclose(X[3], [0, 3.05, p.zc])      # en el hueco no hay nada que empujar


def test_la_escena_y_la_hoja_los_dibujan():
    d = Palos(TRES).datos()
    assert d == {"tipo": "palos", "radio": 2.5, "largo": 30, "y": [-6.1, 0.0, 6.1],
                 "z": pytest.approx(4.6)}
    assert solido(TRES).datos() == d
    puntos, color, _ = _palos(d, -8.0, 8.0, -10.0, 10.0)
    assert color is MADERA
    # Tres palos a lo largo de x, cortados en el encuadre más un margen.
    for y in d["y"]:
        cerca = np.abs(puntos[:, 1] - y) <= d["radio"]
        assert np.ptp(puntos[cerca, 0]) > 16 and puntos[cerca, 0].max() < 8 + 6


def test_la_ficha_dice_como_se_ve_por_detras():
    assert set(POR_DETRAS) == {None, *TIPOS_ANFITRION}
    assert "palos" in POR_DETRAS["palos"] and "página" in POR_DETRAS["palos"]


def test_por_detras_se_voltean_con_la_cuerda():
    """Media vuelta alrededor del eje y, como una página: un giro rígido que deja los palos a
    lo largo de x, el de delante delante, y lo más bajo apoyado en la mesa."""
    from nudos.libre import Resultado
    p = Palos(DOS)
    X = np.array([[-3.0, -3.05, p.zc + p.rb], [3.0, 0.0, 0.5], [4.0, 3.05, p.zc - p.rb]])
    r = Resultado(n=1, puntos=X, h=0.2, secuencia=("1U", "1O"), esperada=("1U", "1O"),
                  medidas={}, fallas=[], cruces={"1": (2.0, 1.0)}, resaltado=(0.0, 1.0))
    v, datos_ = p.voltear(r)
    Y = v.puntos
    assert np.allclose(Y[:, 0], -X[:, 0]) and np.allclose(Y[:, 1], X[:, 1])
    assert np.allclose(Y[:, 2] + X[:, 2], Y[0, 2] + X[0, 2])
    assert datos_["y"] == p.datos()["y"]
    assert min(Y[:, 2].min() - R, datos_["z"] - p.radio) == pytest.approx(0, abs=1e-9)
    assert v.secuencia == r.secuencia and v.resaltado is None and v.cruces == {"1": (-2.0, 1.0)}
    assert np.hypot(Y[:, 1] - p.ys[0], Y[:, 2] - datos_["z"]).min() >= p.rb - PENETRACION_MAX
