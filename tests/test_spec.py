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


def test_precauciones_y_alternativas():
    spec = desde_datos(datos(precauciones=["Revísalo antes de usarlo."],
                             alternativas=[{"nudo": "Ocho doble", "cuando": "Si va a aguantar\n mucho."}]))
    assert spec.precauciones == ("Revísalo antes de usarlo.",)
    assert [(a.nudo, a.cuando) for a in spec.alternativas] == [("Ocho doble", "Si va a aguantar mucho.")]


@pytest.mark.parametrize("alternativas, pista", [
    ([], "lista de otros nudos"),
    (["Ocho doble"], "un mapa con «nudo» y «cuando»"),
    ([{"nudo": "Ocho doble"}], "alternativa 1: falta «cuando»"),
    ([{"nudo": "Ocho doble", "cuando": "Siempre.", "slug": "ocho-doble"}], "campos desconocidos: slug"),
])
def test_alternativas_mal_escritas(alternativas, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(alternativas=alternativas))


def test_campo_desconocido():
    with pytest.raises(SpecError, match="campos desconocidos"):
        desde_datos(datos(autor="yo"))


def error(**cambios):
    base = {"paso": 1, "invierte": [1], "titulo": "Al revés", "texto": "Texto."}
    base.update(cambios)
    return base


def test_otros_errores_sin_imagen():
    spec = desde_datos(datos(pasos=[paso(secuencia="1O 1U")], error=error(otros=[
        {"titulo": "Flojo", "texto": "Tira fuerte."}, {"titulo": "Corto", "texto": "Deja más."}])))
    assert [(o.titulo, o.texto) for o in spec.error.otros] == [("Flojo", "Tira fuerte."),
                                                              ("Corto", "Deja más.")]
    assert spec.error.variante is None
    sin = desde_datos(datos(pasos=[paso(secuencia="1O 1U")], error=error()))
    assert sin.error.otros == ()


@pytest.mark.parametrize("otros, pista", [
    ([], "«otros» es una lista de errores sin imagen"),
    (["Flojo"], "otro error 1: debe ser un mapa"),
    ([{"titulo": "Flojo"}], "otro error 1: falta «texto»"),
    ([{"titulo": "Flojo", "texto": "T.", "paso": 2}], "otro error 1: campos desconocidos: paso"),
])
def test_otros_errores_mal_escritos(otros, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(pasos=[paso(secuencia="1O 1U")], error=error(otros=otros)))


def test_la_variante_es_solo_de_las_plantillas():
    with pytest.raises(SpecError, match="«variante» es el error de un nudo de plantilla"):
        desde_datos(datos(pasos=[paso(secuencia="1O 1U")], error=error(variante="flojo")))


def test_sin_plantilla_las_llaves_quedan_como_estan():
    spec = desde_datos(datos(pasos=[paso(texto="Da {vueltas} vueltas.")]))
    assert spec.pasos[0].texto == "Da {vueltas} vueltas."
    assert spec.plantilla is None and spec.pasos[0].hasta is None


def test_hasta_es_solo_de_las_plantillas():
    with pytest.raises(SpecError, match="campos desconocidos: hasta"):
        desde_datos(datos(pasos=[paso(hasta="cierre")]))


# --------------------------------------------------------------------------
# Varias cuerdas
# --------------------------------------------------------------------------
CUERDAS = [{"nombre": "gruesa", "grosor": 1.5, "color": "azul"},
           {"nombre": "delgada", "grosor": 1, "color": "crema"}]
SEGMENTOS_DOS = {"a": [[0, 0], [1, 0], [2, 0]], "b": [[3, 0], [4, 1]],
                 "c": [[1, -2], [1, -1], [1, 1]], "d": [[1, 2], [0, 3]]}


def datos_dos(pasos=None, **cambios):
    base = datos(cuerdas=CUERDAS, segmentos=SEGMENTOS_DOS, pasos=pasos or [paso_dos()])
    base.update(cambios)
    return base


def paso_dos(**cambios):
    base = paso(trazado={"gruesa": ["a", "b"], "delgada": ["c", "d"]},
                secuencia={"gruesa": "1O", "delgada": "1U"})
    base.update(cambios)
    return base


def test_un_nudo_de_una_cuerda_no_cambia():
    spec = desde_datos(datos())
    assert spec.cuerdas == ()
    assert spec.pasos[0].cuerda is None and spec.pasos[0].pasadas is None


def test_cuerdas_se_leen_en_orden():
    spec = desde_datos(datos_dos())
    assert [(c.nombre, c.grosor, c.color) for c in spec.cuerdas] == [
        ("gruesa", 1.5, "azul"), ("delgada", 1.0, "crema")]
    p = spec.pasos[0]
    assert p.puntos.tolist() == [[0, 0], [1, 0], [2, 0], [3, 0], [4, 1],
                                 [1, -2], [1, -1], [1, 1], [1, 2], [0, 3]]
    assert p.cuerda.tolist() == [0] * 5 + [1] * 5


def test_secuencias_van_una_tras_otra():
    """Un cruce puede tener sus dos pasadas en la misma cuerda o en las dos."""
    spec = desde_datos(datos_dos([paso_dos(secuencia={"gruesa": "1O 2U 2O", "delgada": "1U"})]))
    p = spec.pasos[0]
    assert p.secuencia == ("1O", "2U", "2O", "1U")
    assert p.pasadas == (3, 1)


def test_una_cuerda_sin_cruces_lleva_secuencia_vacia():
    spec = desde_datos(datos_dos([paso_dos(secuencia={"gruesa": "", "delgada": ""})]))
    assert spec.pasos[0].secuencia == () and spec.pasos[0].pasadas == (0, 0)


def test_resaltar_en_una_cuerda():
    """«fin» es el último punto de la cuerda donde empieza el resaltado."""
    spec = desde_datos(datos_dos([paso_dos(resaltar={"desde": "c[1]", "hasta": "fin"})]))
    assert spec.pasos[0].resaltar == (6, 9)
    spec = desde_datos(datos_dos([paso_dos(resaltar={"desde": "a[1]", "hasta": "fin"})]))
    assert spec.pasos[0].resaltar == (1, 4)


def test_el_error_invierte_un_cruce_entre_cuerdas():
    spec = desde_datos(datos_dos(error={"paso": 1, "invierte": [1], "titulo": "T", "texto": "X."}))
    assert spec.error.invierte == ("1",)


@pytest.mark.parametrize("cuerdas, pista", [
    (CUERDAS[:1], "dos o más"),
    ([CUERDAS[0], {**CUERDAS[1], "nombre": "gruesa"}], "ya hay una cuerda"),
    ([CUERDAS[0], {**CUERDAS[1], "nombre": "Delgada"}], "minúsculas"),
    ([CUERDAS[0], {**CUERDAS[1], "color": "azul"}], "mismo color"),
    ([CUERDAS[0], {**CUERDAS[1], "color": "ambar"}], "azul, crema"),
    ([CUERDAS[0], {**CUERDAS[1], "grosor": 0}], "grosor"),
    ([CUERDAS[0], {**CUERDAS[1], "grosor": "1"}], "grosor"),
    ([CUERDAS[0], {**CUERDAS[1], "rol": "chicote"}], "campos desconocidos"),
    ([CUERDAS[0], "delgada"], "debe ser un mapa"),
])
def test_cuerdas_mal_declaradas(cuerdas, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos_dos(cuerdas=cuerdas))


def test_varias_cuerdas_sin_anfitrion_por_ahora():
    with pytest.raises(SpecError, match="no lleva anfitrión"):
        desde_datos(datos_dos(anfitrion={"tipo": "poste", "radio": 1.5, "desde": -5, "hasta": 5}))


@pytest.mark.parametrize("cambio, pista", [
    ({"trazado": ["a", "b"]}, "mapa por cuerda"),
    ({"trazado": {"gruesa": ["a", "b"]}}, "falta «trazado» de la cuerda delgada"),
    ({"trazado": {"gruesa": ["a"], "delgada": ["c"], "roja": ["d"]}}, "«roja» no existe"),
    ({"trazado": {"gruesa": ["a", "b"], "delgada": []}}, "falta el trazado de la cuerda delgada"),
    ({"trazado": {"gruesa": ["a", "b"], "delgada": ["d[1:]"]}}, "delgada necesita al menos dos"),
    ({"trazado": {"gruesa": ["a", "c"], "delgada": ["c", "d"]}}, "aparece dos veces"),
    ({"secuencia": "1O 1U"}, "mapa por cuerda"),
    ({"secuencia": {"gruesa": "1O"}}, "falta «secuencia» de la cuerda delgada"),
    ({"secuencia": {"gruesa": "1O 1U", "delgada": None}}, "escribe \"\""),
    ({"secuencia": {"gruesa": "1O", "delgada": "1O"}},
     "1O en la cuerda gruesa y 1O en la cuerda delgada"),
    ({"secuencia": {"gruesa": "1O", "delgada": "1X"}}, "«1X» en la cuerda delgada"),
    ({"resaltar": {"desde": "a[0]", "hasta": "c[0]"}}, "en la misma cuerda"),
    ({"resaltar": {"desde": "fin", "hasta": "fin"}}, "«fin» va en «hasta»"),
])
def test_errores_del_paso_con_dos_cuerdas(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos_dos([paso_dos(**cambio)]))


def test_trazado_por_cuerda_sin_cuerdas():
    with pytest.raises(SpecError, match="solo cuando el nudo declara «cuerdas»"):
        desde_datos(datos(segmentos=SEGMENTOS_DOS,
                          pasos=[paso(trazado={"gruesa": ["a", "b"], "delgada": ["c", "d"]})]))


def test_un_segmento_no_cambia_de_cuerda():
    otro = paso_dos(trazado={"gruesa": ["a", "c"], "delgada": ["b", "d"]})
    with pytest.raises(SpecError, match="paso 2: el segmento c va en la cuerda delgada en el paso 1"):
        desde_datos(datos_dos([paso_dos(), otro]))


def test_puntos_casi_iguales_solo_dentro_de_una_cuerda():
    """El último punto de una cuerda puede quedar junto al primero de la siguiente."""
    segmentos = {**SEGMENTOS_DOS, "c": [[4, 1.01], [1, -1], [1, 1]]}
    desde_datos(datos_dos(segmentos=segmentos))
