"""El amarre cuadrado: la primera plantilla, sobre dos palos cruzados (anfitrión «cruz»)."""
import copy

import numpy as np
import pytest

from nudos.construir import construir
from nudos.plantillas.amarre import AmarreCuadrado, Extremo
from nudos.spec import SpecError, desde_datos

PASOS = [
    ("Haz un ballestrinque en el palo de abajo", "inicio"),
    ("Da la primera vuelta", "vuelta-1"),
    ("Da las demás vueltas", "vueltas"),
    ("Da el primer ahorcado", "ahorcado-1"),
    ("Da los demás ahorcados", "ahorcados"),
    ("Empieza el ballestrinque de cierre", "cierre-1"),
    ("Termina el ballestrinque", "cierre"),
]


def datos(**cambios):
    base = {
        "slug": "amarre-cuadrado",
        "nombre": "Amarre cuadrado",
        "familia": "Amarres",
        "anfitrion": {"tipo": "cruz", "radio": 2.5, "largo": 40},
        "plantilla": {
            "tipo": "amarre-cuadrado",
            "vueltas": 3,
            "ahorcados": 3,
            "inicio": {"poste": "abajo", "lado": "delante"},
            "cierre": {"poste": "arriba", "lado": "derecha"},
        },
        "pasos": [{"titulo": t, "texto": "Texto.", "hasta": h} for t, h in PASOS],
        "error": {"paso": 5, "variante": "ahorcados-por-fuera", "titulo": "Ahorcados por fuera",
                  "texto": "Texto."},
    }
    base.update(copy.deepcopy(cambios))
    return base


def con(**cambios_plantilla):
    d = datos()
    d["plantilla"].update(cambios_plantilla)
    return d


# --- La especificación ----------------------------------------------------
def test_la_especificacion_se_lee():
    spec = desde_datos(datos())
    assert spec.anfitrion.tipo == "cruz"
    assert (spec.anfitrion.radio, spec.anfitrion.largo) == (2.5, 40)
    assert spec.plantilla == AmarreCuadrado(3, 3, Extremo("abajo", "delante"), Extremo("arriba", "derecha"))
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]
    assert all(p.puntos.shape == (0, 2) and p.secuencia == () for p in spec.pasos)
    assert spec.error.variante == "ahorcados-por-fuera"
    assert spec.error.invierte == ()


def test_los_hitos_siguen_la_cuerda():
    hitos = AmarreCuadrado(3, 2, Extremo("abajo", "delante"), Extremo("arriba", "derecha")).hitos()
    orden = ["inicio-1", "inicio", "vuelta-1", "vuelta-2", "vuelta-3", "ahorcado-1",
             "ahorcado-2", "cierre-1", "cierre"]
    assert [hitos[h] for h in orden] == list(range(len(orden)))
    # «vueltas» es la última vuelta y «ahorcados» el último ahorcado.
    assert hitos["vueltas"] == hitos["vuelta-3"]
    assert hitos["ahorcados"] == hitos["ahorcado-2"]


def test_las_medidas_salen_en_letras_en_todo_el_texto():
    d = con(vueltas=4)
    d["pasos"][2]["texto"] = "Da {vueltas} vueltas en total."
    d["pasos"][4]["titulo"] = "Completa los {ahorcados} ahorcados"
    d["error"]["otros"] = [{"titulo": "Flojo", "texto": "Tira fuerte en las {vueltas} vueltas."}]
    d["verificacion"] = ["Cuenta {vueltas} vueltas y {ahorcados} ahorcados."]
    spec = desde_datos(d)
    assert spec.pasos[2].texto == "Da cuatro vueltas en total."
    assert spec.pasos[4].titulo == "Completa los tres ahorcados"
    assert spec.error.otros[0].texto == "Tira fuerte en las cuatro vueltas."
    assert spec.verificacion == ("Cuenta cuatro vueltas y tres ahorcados.",)


def test_de_3_a_4_vueltas_los_mismos_pasos_siguen_valiendo():
    spec = desde_datos(con(vueltas=4))
    assert spec.plantilla.vueltas == 4
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]


def test_una_medida_que_no_existe_en_el_texto():
    d = datos()
    d["pasos"][0]["texto"] = "Da {vuletas} vueltas."
    with pytest.raises(SpecError, match=r"«\{vuletas\}» no es una medida"):
        desde_datos(d)


@pytest.mark.parametrize("cambio, pista", [
    ({"tipo": "amarre-redondo"}, "«tipo» es uno de: amarre-cuadrado"),
    ({"vueltas": 1}, "«vueltas» es un número entero de 2 a 6"),
    ({"ahorcados": 3.0}, "«ahorcados» es un número entero"),
    ({"vueltas": True}, "«vueltas» es un número entero"),
    ({"inicio": {"poste": "abajo"}}, "«inicio» lleva «poste»"),
    ({"inicio": {"poste": "medio", "lado": "delante"}}, "«poste» es abajo o arriba"),
    ({"cierre": {"poste": "arriba", "lado": "delante"}}, "«lado» es izquierda o derecha"),
    ({"inicio": {"poste": "arriba", "lado": "izquierda"}}, "por ahora el ballestrinque de inicio"),
    ({"angulo": 45}, "campos desconocidos: angulo"),
])
def test_una_plantilla_mal_escrita_se_detecta(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(con(**cambio))


@pytest.mark.parametrize("cambio, pista", [
    ({"radio": 0.3}, "el radio de los palos es de al menos medio diámetro"),
    ({"largo": 4}, "mayor que su grosor"),
    ({"desde": -10}, "campos desconocidos: desde"),
])
def test_una_cruz_mal_escrita_se_detecta(cambio, pista):
    d = datos()
    d["anfitrion"].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_la_plantilla_necesita_la_cruz():
    with pytest.raises(SpecError, match="va sobre el anfitrión cruz"):
        desde_datos(datos(anfitrion={"tipo": "poste", "radio": 1.5, "desde": -14, "hasta": 14}))
    sin = datos()
    del sin["anfitrion"]
    with pytest.raises(SpecError, match="va sobre el anfitrión cruz"):
        desde_datos(sin)


def test_la_cruz_necesita_una_plantilla():
    d = datos(segmentos={"a": [[0, 0], [1, 0]]},
              pasos=[{"titulo": "T", "texto": "T.", "trazado": ["a"], "secuencia": ""}])
    del d["plantilla"], d["error"]
    with pytest.raises(SpecError, match="el anfitrión cruz va con una plantilla"):
        desde_datos(d)


def test_un_nudo_de_plantilla_no_lleva_segmentos():
    with pytest.raises(SpecError, match="no lleva «segmentos»"):
        desde_datos(datos(segmentos={"a": [[0, 0], [1, 0]]}))


@pytest.mark.parametrize("cambio, pista", [
    ({"hasta": "vuelta-4"}, "«hasta» es uno de: inicio-1, inicio, vuelta-1"),
    ({"hasta": None}, "«hasta» es uno de"),
    ({"trazado": ["a"]}, "no lleva «trazado»"),
    ({"secuencia": ""}, "no lleva «secuencia»"),
    ({"resaltar": {"desde": "a[0]", "hasta": "fin"}}, "no lleva «resaltar»"),
    ({"color": "rojo"}, "campos desconocidos: color"),
])
def test_errores_de_un_paso_de_plantilla(cambio, pista):
    d = datos()
    d["pasos"][1].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_los_pasos_avanzan_por_la_cuerda():
    d = datos()
    d["pasos"][2]["hasta"] = "vuelta-1"   # lo mismo que el paso 2
    with pytest.raises(SpecError, match="paso 3: «hasta: vuelta-1» no avanza"):
        desde_datos(d)
    d = con(vueltas=3)
    d["pasos"].insert(3, {"titulo": "T", "texto": "T.", "hasta": "vuelta-3"})   # = «vueltas»
    with pytest.raises(SpecError, match="paso 4: «hasta: vuelta-3» no avanza"):
        desde_datos(d)


def test_el_ultimo_paso_llega_al_cierre():
    d = datos()
    d["pasos"].pop()
    with pytest.raises(SpecError, match="paso 6: el último paso llega a «cierre»"):
        desde_datos(d)


@pytest.mark.parametrize("cambio, pista", [
    ({"variante": "vueltas-sin-alternar"}, "«variante» es una de: ahorcados-por-fuera"),
    ({"variante": None}, "«variante» es una de"),
    ({"invierte": [1]}, "es una «variante» del método"),
    ({"paso": 3}, "se ve desde «ahorcado-1», y el paso 3 llega solo a vueltas"),
])
def test_el_error_de_una_plantilla(cambio, pista):
    d = datos()
    d["error"].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_un_nudo_de_plantilla_es_de_una_sola_cuerda():
    d = datos(cuerdas=[{"nombre": "gruesa", "grosor": 1.5, "color": "azul"},
                       {"nombre": "delgada", "grosor": 1, "color": "crema"}])
    with pytest.raises(SpecError, match="varias cuerdas no lleva anfitrión"):
        desde_datos(d)


def test_todavia_no_se_construye():
    with pytest.raises(NotImplementedError, match="todavía no calcula la cuerda"):
        construir(desde_datos(datos()))


def test_los_hitos_no_tienen_puntos_de_control():
    p = desde_datos(datos()).pasos[0]
    assert isinstance(p.puntos, np.ndarray) and len(p.puntos) == 0
    assert p.resaltar is None and p.sobre is None
