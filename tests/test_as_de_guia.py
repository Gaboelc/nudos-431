"""El as de guía se construye sin fallas en todos sus pasos."""
import pytest

from nudos.construir import construir
from nudos.libre import LIMITES
from nudos.spec import cargar


@pytest.fixture(scope="module")
def modelo():
    return construir(cargar("as-de-guia"))


def test_sin_fallas(modelo):
    assert modelo.fallas == []


@pytest.mark.parametrize("n", range(1, 8))
def test_paso_cumple_los_limites(modelo, n):
    r = modelo.pasos[n - 1]
    assert r.n == n
    assert r.secuencia == r.esperada
    assert r.medidas["separacion_min"] >= LIMITES["separacion_min"]
    assert r.medidas["curvatura_min"] >= LIMITES["curvatura_min"]
    assert r.medidas["estiramiento_max"] <= LIMITES["estiramiento_max"]
