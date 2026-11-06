"""Lectura y validación de especificaciones."""
import pytest

from nudos.spec import SpecError, desde_datos


def datos(**cambios):
    base = {
        "slug": "prueba",
        "nombre": "Prueba",
        "familia": "De tope",
        "segmentos": {"a": [[0, 0], [1, 0], [2, 0]], "b": [[3, 0], [4, 1]]},
        "pasos": [paso()],
    }
    base.update(cambios)
    return base


def paso(**cambios):
    base = {"titulo": "Título", "texto": "Texto.", "trazado": ["a", "b"], "secuencia": ""}
    base.update(cambios)
    return base


def test_tramos_y_puntos_se_resuelven():
    spec = desde_datos(datos(pasos=[paso(trazado=["a[1:]", "b"],
                                         resaltar={"desde": "a[-1]", "hasta": "fin"})]))
    p = spec.pasos[0]
    assert p.puntos.tolist() == [[1, 0], [2, 0], [3, 0], [4, 1]]
    assert p.resaltar == (1, 3)


@pytest.mark.parametrize("secuencia, pista", [
    ("1U 1U", "una por encima"),
    ("1U", "una por encima"),
    ("1X 1O", "no es un paso por un cruce"),
])
def test_secuencia_mal_escrita(secuencia, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(pasos=[paso(secuencia=secuencia)]))


@pytest.mark.parametrize("cambio, pista", [
    ({"trazado": ["a", "c"]}, "«c» no existe"),
    ({"trazado": ["a[0]", "b"]}, "no un punto"),
    ({"trazado": ["a", "a"]}, "aparece dos veces"),
    ({"trazado": ["a[1:]", "b"], "resaltar": {"desde": "a[0]", "hasta": "fin"}},
     "no está en el tramo"),
    ({"resaltar": {"desde": "b[0]", "hasta": "a[0]"}}, "después de"),
    ({"color": "rojo"}, "campos desconocidos"),
])
def test_errores_del_paso(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(pasos=[paso(**cambio)]))


def test_falta_la_secuencia():
    p = paso()
    del p["secuencia"]
    with pytest.raises(SpecError, match="falta «secuencia»"):
        desde_datos(datos(pasos=[p]))


def test_puntos_seguidos_casi_iguales():
    with pytest.raises(SpecError, match="casi iguales"):
        desde_datos(datos(segmentos={"a": [[0, 0], [0.01, 0]], "b": [[3, 0], [4, 1]]}))


def test_campo_desconocido():
    with pytest.raises(SpecError, match="campos desconocidos"):
        desde_datos(datos(autor="yo"))
