"""El error común y el reverso del nudo terminado."""
import pytest
import yaml

from nudos import SPECS
from nudos.errores import construir_error, cruces_distintos, invertir
from nudos.libre import LIMITES, Resultado
from nudos.spec import SpecError, desde_datos


def leer_as_de_guia():
    with open(SPECS / "as-de-guia.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cumple_limites(r):
    m = r.medidas
    return (r.secuencia == r.esperada
            and m["separacion_min"] >= LIMITES["separacion_min"]
            and m["curvatura_min"] >= LIMITES["curvatura_min"]
            and m["estiramiento_max"] <= LIMITES["estiramiento_max"])


def test_el_error_difiere_exactamente_en_los_cruces_declarados(modelo_as_de_guia):
    e = modelo_as_de_guia.spec.error
    correcto = modelo_as_de_guia.pasos[e.paso - 1]
    # Se comparan las secuencias obtenidas después de relajar, no las declaradas.
    assert cruces_distintos(correcto.secuencia, modelo_as_de_guia.error.secuencia) == {"1"}


def test_el_error_cumple_los_limites(modelo_as_de_guia):
    assert cumple_limites(modelo_as_de_guia.error)


def test_el_reverso_invierte_todos_los_cruces(modelo_as_de_guia):
    final = modelo_as_de_guia.pasos[-1]
    reverso = modelo_as_de_guia.reverso
    assert reverso.secuencia == list(invertir(final.secuencia, {t[:-1] for t in final.secuencia}))
    assert cumple_limites(reverso)


def test_si_el_error_no_difiere_donde_declara_es_una_falla(modelo_as_de_guia):
    spec = modelo_as_de_guia.spec
    error = modelo_as_de_guia.error
    # Un «paso correcto» que en realidad ya tiene el cruce invertido: no difieren en nada.
    igual = Resultado(n=error.n, puntos=error.puntos, h=error.h, resaltado=None, cruces={},
                      secuencia=list(error.secuencia), esperada=[], medidas={})
    _, fallas = construir_error(spec, igual)
    assert any("difiere del paso 2 en los cruces ninguno y debía diferir en 1" in f for f in fallas)


def test_cruces_distintos():
    assert cruces_distintos("1U 2O 1O 2U".split(), "1O 2O 1U 2U".split()) == {"1"}
    with pytest.raises(ValueError):
        cruces_distintos("1U 2O 1O 2U".split(), "1U 1O".split())


def test_invertir_solo_cambia_los_cruces_pedidos():
    assert invertir(("1U", "2O", "1O", "2U"), {"2"}) == ("1U", "2U", "1O", "2O")


@pytest.mark.parametrize("cambio, pista", [
    ({"invierte": [9]}, "el paso 2 no tiene el cruce 9"),
    ({"invierte": []}, "lista de cruces"),
    ({"invierte": [1, 1]}, "aparece dos veces"),
    ({"paso": 8}, "de 1 a 7"),
    ({"paso": 1}, "el paso 1 no tiene el cruce 1"),
    ({"color": "rojo"}, "campos desconocidos: color"),
    ({"titulo": ""}, "falta «titulo»"),
])
def test_un_error_mal_escrito_se_detecta_al_cargar(cambio, pista):
    datos = leer_as_de_guia()
    datos["error"].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos)


def test_terminado_solo_acepta_encuadre():
    datos = leer_as_de_guia()
    datos["terminado"]["vista"] = "3d"
    with pytest.raises(SpecError, match="terminado: campos desconocidos: vista"):
        desde_datos(datos)


def test_el_error_y_el_terminado_son_opcionales():
    datos = leer_as_de_guia()
    del datos["error"], datos["terminado"]
    spec = desde_datos(datos)
    assert spec.error is None and spec.terminado.encuadre is None
