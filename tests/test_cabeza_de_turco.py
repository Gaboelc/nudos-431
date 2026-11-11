"""La cabeza de turco: la segunda plantilla, tejida sobre un tubo (anfitrión «tubo»)."""
import copy

import pytest

from nudos.plantillas.cabeza_turco import (CabezaDeTurco, cruces_del_centro, encima_del_centro,
                                           por_vuelta)
from nudos.spec import SpecError, desde_datos

PASOS = [
    ("Da la primera vuelta", "vuelta-1"),
    ("Cruza por encima", "vuelta-2"),
    ("Empieza a tejer", "vuelta-3-mitad"),
    ("Termina de tejer", "vueltas"),
    ("Sigue el mismo camino", "pasadas"),
    ("Esconde los chicotes", "remate"),
]


def datos(**cambios):
    base = {
        "slug": "cabeza-de-turco",
        "nombre": "Cabeza de turco",
        "familia": "Decorativos",
        "anfitrion": {"tipo": "tubo", "radio": 4, "largo": 24},
        "plantilla": {"tipo": "cabeza-de-turco", "cabos": 3, "senos": 4, "pasadas": 2},
        "pasos": [{"titulo": t, "texto": "Texto.", "hasta": h} for t, h in PASOS],
        "error": {"paso": 3, "variante": "empieza-por-encima", "titulo": "Empieza por encima",
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
    assert spec.anfitrion.tipo == "tubo"
    assert (spec.anfitrion.radio, spec.anfitrion.largo) == (4, 24)
    assert spec.plantilla == CabezaDeTurco(cabos=3, senos=4, pasadas=2)
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]
    assert all(p.puntos.shape == (0, 2) and p.secuencia == () for p in spec.pasos)
    assert spec.error.variante == "empieza-por-encima" and spec.error.invierte == ()


def test_los_hitos_siguen_la_cuerda():
    hitos = CabezaDeTurco(3, 4, 3).hitos()
    orden = ["vuelta-1-mitad", "vuelta-1", "vuelta-2-mitad", "vuelta-2", "vuelta-3-mitad",
             "vuelta-3", "pasada-2-mitad", "pasada-2", "pasada-3-mitad", "pasada-3", "remate"]
    assert [hitos[h] for h in orden] == list(range(len(orden)))
    # «vueltas» es la última vuelta y «pasadas» la última pasada.
    assert hitos["vueltas"] == hitos["vuelta-3"]
    assert hitos["pasadas"] == hitos["pasada-3"]


def test_con_una_pasada_las_pasadas_son_las_vueltas():
    hitos = CabezaDeTurco(2, 3, 1).hitos()
    assert list(hitos) == ["vuelta-1-mitad", "vuelta-1", "vuelta-2-mitad", "vuelta-2",
                           "vueltas", "pasadas", "remate"]
    assert hitos["pasadas"] == hitos["vueltas"] == hitos["vuelta-2"]
    d = con(cabos=2, senos=3, pasadas=1)
    d["pasos"] = [{"titulo": "T", "texto": "T.", "hasta": h} for h in ("vuelta-1", "vueltas", "remate")]
    del d["error"]
    assert [p.hasta for p in desde_datos(d).pasos] == ["vuelta-1", "vueltas", "remate"]


def test_las_medidas_salen_en_letras_en_todo_el_texto():
    d = con(pasadas=3)
    d["pasos"][1]["texto"] = "Cruza la primera vuelta {senos} menos una veces."
    d["pasos"][4]["titulo"] = "Completa las {pasadas} pasadas"
    d["error"]["otros"] = [{"titulo": "Apretado de una vez", "texto": "Son {cabos} vueltas."}]
    d["verificacion"] = ["Cuenta {senos} senos en cada borde."]
    spec = desde_datos(d)
    assert spec.pasos[1].texto == "Cruza la primera vuelta cuatro menos una veces."
    assert spec.pasos[4].titulo == "Completa las tres pasadas"
    assert spec.error.otros[0].texto == "Son tres vueltas."
    assert spec.verificacion == ("Cuenta cuatro senos en cada borde.",)
    assert CabezaDeTurco(5, 7, 1).medidas() == {"cabos": "cinco", "senos": "siete", "pasadas": "una"}


def test_una_medida_que_no_existe_en_el_texto():
    d = datos()
    d["pasos"][0]["texto"] = "Da {vueltas} vueltas."
    with pytest.raises(SpecError, match=r"«\{vueltas\}» no es una medida de la plantilla; puede "
                                        r"ser \{cabos\} o \{senos\} o \{pasadas\}"):
        desde_datos(d)


def test_cambiar_las_medidas_es_cambiar_un_numero():
    spec = desde_datos(con(senos=5, pasadas=3))
    assert spec.plantilla == CabezaDeTurco(3, 5, 3)
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]


@pytest.mark.parametrize("cambio, pista", [
    ({"tipo": "cabeza-de-moro"}, "«tipo» es uno de: amarre-cuadrado, cabeza-de-turco"),
    ({"cabos": 1}, "«cabos» es un número entero de 2 a 5"),
    ({"cabos": 6}, "«cabos» es un número entero de 2 a 5"),
    ({"senos": 8}, "«senos» es un número entero de 2 a 7"),
    ({"senos": 4.0}, "«senos» es un número entero"),
    ({"pasadas": 0}, "«pasadas» es un número entero de 1 a 3"),
    ({"pasadas": True}, "«pasadas» es un número entero"),
    ({"senos": 6}, "con 3 cabos y 6 senos salen 3 cuerdas cerradas"),
    ({"senos": 3}, "no pueden tener un divisor común aparte del 1"),
    ({"cabos": 4, "senos": 2}, "salen 2 cuerdas cerradas"),
    ({"vueltas": 3}, "campos desconocidos: vueltas"),
])
def test_una_plantilla_mal_escrita_se_detecta(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(con(**cambio))


@pytest.mark.parametrize("cambio, pista", [
    ({"radio": 0.3}, "el radio del tubo es de al menos medio diámetro"),
    ({"largo": 8}, "«largo» es el largo del tubo; tiene que ser mayor que su grosor"),
    ({"desde": -10}, "campos desconocidos: desde"),
    ({"largo": None}, "falta «largo»"),
])
def test_un_tubo_mal_escrito_se_detecta(cambio, pista):
    d = datos()
    d["anfitrion"].update(cambio)
    if cambio == {"largo": None}:
        del d["anfitrion"]["largo"]
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_la_plantilla_necesita_el_tubo():
    with pytest.raises(SpecError, match="la plantilla cabeza-de-turco va sobre el anfitrión tubo"):
        desde_datos(datos(anfitrion={"tipo": "cruz", "radio": 2.5, "largo": 40}))
    sin = datos()
    del sin["anfitrion"]
    with pytest.raises(SpecError, match="va sobre el anfitrión tubo"):
        desde_datos(sin)


def test_el_tubo_necesita_una_plantilla():
    d = datos(segmentos={"a": [[0, 0], [1, 0]]},
              pasos=[{"titulo": "T", "texto": "T.", "trazado": ["a"], "secuencia": ""}])
    del d["plantilla"], d["error"]
    with pytest.raises(SpecError, match="el anfitrión tubo va con una plantilla, como cabeza-de-turco"):
        desde_datos(d)


@pytest.mark.parametrize("cambio, pista", [
    ({"hasta": "vuelta-4"}, "«hasta» es uno de: vuelta-1-mitad, vuelta-1, vuelta-2-mitad"),
    ({"hasta": "pasada-1"}, "«hasta» es uno de"),
    ({"trazado": ["a"]}, "no lleva «trazado»"),
    ({"secuencia": ""}, "no lleva «secuencia»"),
])
def test_errores_de_un_paso_de_plantilla(cambio, pista):
    d = datos()
    d["pasos"][1].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_los_pasos_avanzan_por_la_cuerda():
    d = datos()
    d["pasos"][3]["hasta"] = "vuelta-3-mitad"   # lo mismo que el paso 3
    with pytest.raises(SpecError, match="paso 4: «hasta: vuelta-3-mitad» no avanza"):
        desde_datos(d)
    d = con(pasadas=1)
    del d["pasos"][4]   # «pasadas» es «vueltas»: el paso 5 ya no avanzaría
    assert [p.hasta for p in desde_datos(d).pasos][-2:] == ["vueltas", "remate"]
    d = con(pasadas=1)
    with pytest.raises(SpecError, match="paso 5: «hasta: pasadas» no avanza"):
        desde_datos(d)


def test_el_ultimo_paso_llega_al_remate():
    d = datos()
    d["pasos"].pop()
    with pytest.raises(SpecError, match="paso 5: el último paso llega a «remate»"):
        desde_datos(d)


@pytest.mark.parametrize("cambio, pista", [
    ({"variante": "ahorcados-por-fuera"}, "«variante» es una de: empieza-por-encima"),
    ({"invierte": [1]}, "es una «variante» del método"),
    ({"paso": 2}, "se ve desde «vuelta-3-mitad», y el paso 2 llega solo a vuelta-2"),
])
def test_el_error_de_la_cabeza_de_turco(cambio, pista):
    d = datos()
    d["error"].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_empezar_por_encima_es_el_error_de_tres_cabos():
    for senos in (2, 4, 5, 7):
        assert CabezaDeTurco(3, senos, 1).VARIANTES == {"empieza-por-encima": "vuelta-3-mitad"}
    assert CabezaDeTurco(2, 3, 2).VARIANTES == {} and CabezaDeTurco(4, 5, 2).VARIANTES == {}
    d = con(cabos=4, senos=5)
    with pytest.raises(SpecError, match="con estas medidas, la plantilla cabeza-de-turco no sabe "
                                        "construir ningún error común"):
        desde_datos(d)
    del d["error"]
    assert desde_datos(d).plantilla == CabezaDeTurco(4, 5, 2)


# --- El camino del centro -----------------------------------------------------
@pytest.mark.parametrize("cabos, senos", [(2, 3), (2, 7), (3, 2), (3, 4), (3, 5), (3, 7), (4, 5),
                                          (5, 2), (5, 7)])
def test_el_centro_se_cruza_senos_por_cabos_menos_uno_veces(cabos, senos):
    cruces = cruces_del_centro(cabos, senos)
    assert len(cruces) == senos * (cabos - 1)
    # Alterna a lo largo de la cuerda, y cada cruce tiene una pasada por encima y otra por debajo.
    pasadas = encima_del_centro(cabos, senos)
    assert all(a != b for (_, a, _), (_, b, _) in zip(pasadas, pasadas[1:]))
    lados = {}
    for _, o, k in pasadas:
        lados.setdefault(k, []).append(o)
    assert all(sorted(v) == [False, True] for v in lados.values())
    # Ningún cruce cae a menos de P / (2 cabos) de un ápice (P = 1).
    for t in (t for c in cruces for t in c):
        assert min(t % 0.5, 0.5 - t % 0.5) >= 1 / (2 * cabos) - 1e-9


@pytest.mark.parametrize("senos, segunda, tercera", [
    (2, "OO", "UO"), (4, "OOO", "UOUOU"), (5, "OOOO", "UOUOUO"), (7, "OOOOO", "UOUOUOUOU")])
def test_con_tres_cabos_la_segunda_vuelta_va_toda_por_encima(senos, segunda, tercera):
    """El método clásico: la primera vuelta no cruza nada, la segunda cruza la primera siempre
    por encima y la tercera teje empezando por debajo."""
    vueltas = ["".join("O" if o else "U" for o in v) for v in por_vuelta(3, senos)]
    assert vueltas == ["", segunda, tercera]


def test_con_cuatro_cabos_la_segunda_vuelta_ya_alterna():
    assert ["".join("O" if o else "U" for o in v) for v in por_vuelta(4, 5)][1] == "OU"


def test_ningun_paso_tiene_firme():
    assert CabezaDeTurco.CON_FIRME == ()
