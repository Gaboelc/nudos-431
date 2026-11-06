"""El as de guía se construye sin fallas en todos sus pasos."""
import pytest

from nudos.libre import LIMITES


def test_sin_fallas(modelo_as_de_guia):
    assert modelo_as_de_guia.fallas == []


@pytest.mark.parametrize("n", range(1, 8))
def test_paso_cumple_los_limites(modelo_as_de_guia, n):
    r = modelo_as_de_guia.pasos[n - 1]
    assert r.n == n
    assert r.secuencia == r.esperada
    assert r.medidas["separacion_min"] >= LIMITES["separacion_min"]
    assert r.medidas["curvatura_min"] >= LIMITES["curvatura_min"]
    assert r.medidas["estiramiento_max"] <= LIMITES["estiramiento_max"]
