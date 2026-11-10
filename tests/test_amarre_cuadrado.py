"""El amarre cuadrado: la primera plantilla, sobre dos palos cruzados (anfitrión «cruz»)."""
import copy

import numpy as np
import pytest
from PIL import Image

from nudos.anfitrion import PENETRACION_MAX, Cruz
from nudos.construir import DESPLAZAMIENTO_MAX, construir
from nudos.cruces import numerada
from nudos.exportar import datos_visor
from nudos.imprimir import dibujar, imagenes
from nudos.libre import LIMITES, R
from nudos.plantillas.amarre import AmarreCuadrado, Extremo, cuerda
from nudos.plantillas.pasos import buscar
from nudos.plantillas.trazo import ABAJO, CINTURA
from nudos.spec import Anfitrion, SpecError, desde_datos

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


def test_los_hitos_no_tienen_puntos_de_control():
    p = desde_datos(datos()).pasos[0]
    assert isinstance(p.puntos, np.ndarray) and len(p.puntos) == 0
    assert p.resaltar is None and p.sobre is None


# --- La cruz ----------------------------------------------------------------
CRUZ = Anfitrion("cruz", radio=2.5, largo=40)


def test_los_palos_se_apoyan_uno_sobre_otro():
    c = Cruz(CRUZ)
    assert c.zb == pytest.approx(3.5)          # el de abajo, sobre la cuerda que pasa por debajo
    assert c.zt - c.zb == pytest.approx(5.0)   # el de arriba, sobre el de abajo
    y, a, r = c.abajo(np.array([[0.0, 7.0, c.zb + c.rb], [c.rb, -2.0, c.zb]]))
    assert np.allclose(y, [7, -2]) and np.allclose(np.degrees(a), [90, 0]) and np.allclose(r, c.rb)
    x, a, r = c.arriba(np.array([[4.0, 0.0, c.zt + c.rb], [-1.0, -c.rb, c.zt]]))
    assert np.allclose(x, [4, -1]) and np.allclose(np.degrees(a), [90, 180]) and np.allclose(r, c.rb)


def test_empujar_saca_lo_que_entro_a_cualquiera_de_los_dos_palos():
    c = Cruz(CRUZ)
    X = np.array([[1.0, 8.0, c.zb], [6.0, 0.5, c.zt - 1.0], [0.0, 30.0, c.zb], [5.0, 5.0, 6.0]])
    assert c.penetracion(X) == pytest.approx(c.rb - 1.0)   # el primero, a 1 del eje de abajo
    c.empujar(X, np.ones(4, bool))
    assert c.penetracion(X) == pytest.approx(0, abs=1e-9)
    assert np.allclose(X[2], [0, 30, c.zb])   # fuera del largo del palo no se toca
    assert np.allclose(X[3], [5, 5, 6])       # entre los palos no hay nada que empujar


# --- La cuerda entera -------------------------------------------------------
def la_cuerda(variante=None, **cambios):
    spec = desde_datos(con(**cambios))
    return cuerda(spec.plantilla, Cruz(spec.anfitrion), variante)


POR_FUERA = "ahorcados-por-fuera"


@pytest.mark.parametrize("vueltas, ahorcados", [(2, 2), (3, 3), (4, 3), (3, 4), (6, 6)])
def test_la_secuencia_del_metodo(vueltas, ahorcados):
    """Cada ahorcado pasa por encima de cada vuelta en las cuatro esquinas, las vueltas no se
    cruzan entre sí y cada ballestrinque tiene sus dos cruces: 40 con 3 y 3."""
    c = la_cuerda(vueltas=vueltas, ahorcados=ahorcados)
    sec = c.secuencias["cierre"]
    assert len(sec) // 2 == 4 * vueltas * ahorcados + 4
    assert sec[:4] == ("1U", "1O", "2O", "2U")
    esquinas = [t for t in sec[4:-4] if t.endswith("U")]
    assert len(esquinas) == 4 * vueltas * ahorcados   # todas las esquinas, por debajo
    assert all(t.endswith("O") for t in sec[4 + len(esquinas):-4])
    assert len(c.secuencias["inicio"]) == 4 and len(c.secuencias["vueltas"]) == 4
    assert len(c.secuencias["ahorcado-1"]) // 2 == 4 * vueltas + 2


def test_los_hitos_avanzan_por_la_misma_cuerda():
    c = la_cuerda()
    orden = list(AmarreCuadrado(3, 3, Extremo("abajo", "delante"), Extremo("arriba", "derecha")).hitos())
    indices = [c.hitos[h] if h in c.hitos else c.hitos[c.alias[h]] for h in orden]
    assert indices == sorted(indices)
    assert c.hitos["cierre"] == len(c.puntos) - 1
    assert set(c.restos) == set(c.hitos) - {"cierre"}   # el último paso no lleva resto
    for nombre, resto in c.restos.items():
        assert resto[-1][2] == pytest.approx(0.5), nombre   # el resto termina sobre la mesa


def test_los_lados_de_los_ballestrinques_son_reflejos():
    base = la_cuerda()
    izquierda = la_cuerda(cierre={"poste": "arriba", "lado": "izquierda"})
    detras = la_cuerda(inicio={"poste": "abajo", "lado": "detras"})
    assert np.allclose(izquierda.puntos * [-1, 1, 1], base.puntos)
    assert np.allclose(detras.puntos * [1, -1, 1], base.puntos)
    assert izquierda.secuencias == base.secuencias


def test_los_cruces_se_buscan_solo_dentro_de_cada_zona():
    # Dos tramos que se cruzan en el mapa de la cintura: con las dos en la cintura es un
    # cruce; si una va sobre el palo de abajo, no se busca.
    c = Cruz(CRUZ)
    a = np.column_stack([np.full(21, 6.0), np.linspace(-1, 1, 21), np.linspace(5, 7, 21)])
    b = np.column_stack([np.full(21, 6.0), np.linspace(-1, 1, 21), np.linspace(7, 5, 21)]) * [1.2, 1.2, 1]
    X = np.vstack([a, b])
    zonas = np.full(len(X), CINTURA)
    zonas[20] = -1   # el salto entre los dos tramos no es cuerda
    cruces, alturas = buscar(X, 1.0, zonas, c)
    assert len(cruces) == 1 and alturas[0][1] > alturas[0][0]   # encima, el más lejos del eje
    zonas[21:] = ABAJO
    assert buscar(X, 1.0, zonas, c)[0] == []


# --- El error común como variante del método ----------------------------------
@pytest.mark.parametrize("vueltas, ahorcados", [(2, 2), (3, 3), (4, 3), (3, 4), (6, 6)])
def test_el_error_cruza_las_mismas_esquinas(vueltas, ahorcados):
    """Los ahorcados por encima del palo de arriba cruzan las mismas esquinas que los bien
    hechos, y en el mismo orden al recorrerlos: por donde pasan el palo de arriba no cruzan
    nada. Como en el error cada ahorcado va más bajo que el anterior, sobre cada esquina
    pasan en el orden contrario."""
    bien = la_cuerda(vueltas=vueltas, ahorcados=ahorcados).secuencias
    mal = la_cuerda(POR_FUERA, vueltas=vueltas, ahorcados=ahorcados).secuencias
    assert mal.keys() == bien.keys()
    for hito in bien:
        assert sorted(mal[hito]) == sorted(bien[hito]), hito
        assert [t for t in mal[hito] if t.endswith("O")] == [t for t in bien[hito] if t.endswith("O")]
    assert mal["inicio"] == bien["inicio"] and mal["vueltas"] == bien["vueltas"]
    assert mal["ahorcados"] != bien["ahorcados"]


def test_el_error_es_el_mismo_amarre_hasta_las_vueltas():
    bien, mal = la_cuerda(), la_cuerda(POR_FUERA)
    i = bien.hitos["vuelta-3"]
    assert mal.hitos["vuelta-3"] == i
    assert np.array_equal(mal.puntos[:i + 1], bien.puntos[:i + 1])


def test_una_variante_que_la_plantilla_no_sabe_construir():
    spec = desde_datos(datos())
    with pytest.raises(ValueError, match="no tiene la variante vueltas-sin-alternar"):
        cuerda(spec.plantilla, Cruz(spec.anfitrion), "vueltas-sin-alternar")


# --- El nudo ------------------------------------------------------------------
@pytest.fixture(scope="module")
def modelo(modelo_amarre_cuadrado):
    """La especificación de specs/, con las mismas medidas que datos()."""
    return modelo_amarre_cuadrado


def test_todos_los_pasos_se_construyen_sin_fallas(modelo):
    assert modelo.fallas == []
    assert [r.n for r in modelo.pasos] == list(range(1, 8))
    assert modelo.error is not None and modelo.error.n == 5
    assert modelo.reverso is None   # por detrás, el amarre se voltea con los palos (Cruz.voltear)


def test_la_cuerda_no_atraviesa_los_palos_ni_otras_vueltas(modelo):
    for r in modelo.pasos:
        m = r.medidas
        assert m["penetracion_palos"] <= PENETRACION_MAX, r.n
        assert m["separacion_min"] >= LIMITES["separacion_min"], r.n
        assert m["curvatura_min"] >= LIMITES["curvatura_min"], r.n
        assert m["estiramiento_max"] <= LIMITES["estiramiento_max"], r.n


def test_los_cruces_coinciden_con_el_metodo(modelo):
    c = la_cuerda()
    for r, (_, hasta) in zip(modelo.pasos, PASOS):
        assert r.secuencia == r.esperada == numerada(c.secuencias[hasta]), r.n
    assert len(modelo.pasos[-1].secuencia) == 80   # 40 cruces


def test_el_error_se_construye_como_un_paso_mas(modelo):
    """El error se relaja y se comprueba como un paso: cumple los mismos límites y, después
    de relajar, cruza lo que la plantilla escribe para la variante."""
    e = modelo.error
    m = e.medidas
    assert m["penetracion_palos"] <= PENETRACION_MAX
    assert m["separacion_min"] >= LIMITES["separacion_min"]
    assert m["curvatura_min"] >= LIMITES["curvatura_min"]
    assert m["estiramiento_max"] <= LIMITES["estiramiento_max"]
    assert e.secuencia == e.esperada == numerada(la_cuerda(POR_FUERA).secuencias["ahorcados"])
    # Resalta lo mismo que el paso 5: los ahorcados que agrega desde el primero.
    assert 0 < e.resaltado[0] < e.resaltado[1]


def test_en_el_error_los_ahorcados_pasan_por_encima_del_palo_de_arriba(modelo):
    """A los dos lados de las vueltas, la cuerda del error pasa por encima del palo de
    arriba; la del paso 5 bien hecho, no."""
    cruz = Cruz(CRUZ)
    X = modelo.pasos[2].puntos   # hasta las vueltas
    sobre = (np.abs(X[:, 1]) < 1.0) & (X[:, 2] > cruz.zt)
    vueltas = np.abs(X[sobre, 0]).max()   # hasta dónde llegan las vueltas sobre el palo

    def por_encima(r, signo):
        Y = r.puntos
        fuera = (signo * Y[:, 0] > vueltas + 0.5) & (np.abs(Y[:, 0]) < CRUZ.largo / 2)
        return bool((fuera & (np.abs(Y[:, 1]) < 1.0) & (Y[:, 2] > cruz.zt)).any())

    for signo in (1, -1):
        assert por_encima(modelo.error, signo), signo
        assert not por_encima(modelo.pasos[4], signo), signo


def test_cada_paso_resalta_lo_que_agrega(modelo):
    # Cada paso empieza a resaltar donde terminó el anterior. La curva suave alrededor de ese
    # punto depende de lo que sigue de la cuerda, así que la posición cambia en milésimas.
    previo = 0.0
    for r in modelo.pasos:
        desde, hasta = r.resaltado
        assert desde == pytest.approx(previo, abs=0.01) and hasta > desde, r.n
        previo = hasta


def test_un_cruce_conserva_su_etiqueta_y_su_lugar(modelo):
    final = modelo.pasos[-1].cruces
    for r in modelo.pasos[:-1]:
        assert set(r.cruces) <= set(final), r.n
        for et, (x, y) in r.cruces.items():
            assert np.hypot(x - final[et][0], y - final[et][1]) <= DESPLAZAMIENTO_MAX, (r.n, et)


def test_de_3_a_4_vueltas_se_regeneran_los_pasos():
    m = construir(desde_datos(con(vueltas=4)))
    assert m.fallas == []   # también las del error
    assert len(m.pasos) == 7
    assert len(m.error.secuencia) == len(m.pasos[4].secuencia)
    assert len(m.pasos[-1].secuencia) // 2 == 4 * 4 * 3 + 4
    assert len(m.pasos[3].secuencia) // 2 == 4 * 4 + 2   # el primer ahorcado cruza 16 esquinas


# --- Escena e impresión ---------------------------------------------------------
def test_la_escena_dibuja_la_cruz(modelo):
    d = datos_visor(modelo)
    assert d["anfitrion"] == Cruz(CRUZ).datos() == {
        "tipo": "cruz", "radio": 2.5, "largo": 40, "z_abajo": 3.5, "z_arriba": 8.5}
    assert d["dos_remates"] is True   # se ven los dos extremos de la cuerda


def test_firme_en_el_ballestrinque_de_inicio_y_despues_solo_chicote(modelo):
    """En el paso 1, «Firme» va en la parte larga y «Chicote» en el extremo corto, como en el
    ballestrinque: la cuerda va al revés, desde la parte larga. Desde el paso 2, la cuerda va
    desde el extremo corto y solo lleva «Chicote», en la punta de la parte larga."""
    pasos = datos_visor(modelo)["pasos"]
    r = modelo.pasos[0]
    p = np.reshape(pasos[0]["p"], (-1, 3))
    assert np.allclose(p[0], r.puntos[-1], atol=1e-3) and np.allclose(p[-1], r.puntos[0], atol=1e-3)
    assert "nombres" not in pasos[0]
    largo = (len(r.puntos) - 1) * r.h
    desde, hasta = r.resaltado
    assert pasos[0]["hl"] == pytest.approx([1 - hasta / largo, 1 - desde / largo], abs=1e-4)
    for paso, r in zip(pasos[1:], modelo.pasos[1:]):
        p = np.reshape(paso["p"], (-1, 3))
        assert np.allclose(p[0], r.puntos[0], atol=1e-3) and np.allclose(p[-1], r.puntos[-1], atol=1e-3)
        assert paso["nombres"] == ["chicote"], r.n


def test_por_detras_el_amarre_se_voltea_con_los_palos(modelo):
    cruz, final = Cruz(CRUZ), modelo.pasos[-1]
    volteado, datos_cruz = cruz.voltear(final)
    X, Y = final.puntos, volteado.puntos
    # Media vuelta alrededor del eje y, como una página: un giro rígido.
    assert np.allclose(Y[:, 0], -X[:, 0]) and np.allclose(Y[:, 1], X[:, 1])
    assert np.allclose(Y[:, 2] + X[:, 2], Y[0, 2] + X[0, 2])
    # El palo de abajo queda encima, lo más bajo se apoya en la mesa y la cuerda sigue sin
    # entrar en los palos, ahora volteados.
    assert datos_cruz["z_abajo"] - datos_cruz["z_arriba"] == pytest.approx(2 * CRUZ.radio)
    assert min(Y[:, 2].min() - R, datos_cruz["z_arriba"] - CRUZ.radio) == pytest.approx(0, abs=1e-9)
    for de, a_lo_largo, z in ((0, 1, datos_cruz["z_abajo"]), (1, 0, datos_cruz["z_arriba"])):
        m = np.abs(Y[:, a_lo_largo]) < CRUZ.largo / 2
        assert np.hypot(Y[m, de], Y[m, 2] - z).min() >= cruz.rb - PENETRACION_MAX
    # Los cruces se miden respecto a los palos: la secuencia no cambia.
    assert volteado.secuencia == final.secuencia and volteado.resaltado is None
    assert volteado.cruces == {et: (-x, y) for et, (x, y) in final.cruces.items()}


def test_las_imagenes_del_amarre(modelo):
    imgs = imagenes(modelo)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 8)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]
    assert {i.vista for i in imgs} == {"3d"}   # el terminado, como los pasos, por delante y por detrás
    # El error va junto al paso 5 bien hecho, en la misma escena y con el mismo encuadre.
    por_nombre = {i.nombre: i for i in imgs}
    bien, mal = por_nombre["error-correcto"], por_nombre["error"]
    assert bien.escena is mal.escena and (bien.indice, mal.indice) == (1, 2)
    assert bien.escena["encuadre"] == por_nombre["paso-5"].escena["encuadre"]
    assert [p["n"] for p in bien.escena["pasos"]] == [5, 5]
    frente, reverso = imgs[-2:]
    assert frente.escena["anfitrion"] == Cruz(CRUZ).datos()
    assert reverso.escena["anfitrion"] == Cruz(CRUZ).voltear(modelo.pasos[-1])[1]
    assert frente.escena["pasos"][0]["nombres"] == reverso.escena["pasos"][0]["nombres"] == ["chicote"]


def test_las_imagenes_muestran_los_palos(con_chrome, modelo, tmp_path):
    """El navegador dibuja el amarre sin errores, y por delante y por detrás se ve la madera."""
    imgs = {i.nombre: i for i in imagenes(modelo)}
    rutas = dibujar([imgs["paso-1"], imgs["terminado-frente"], imgs["terminado-reverso"]], tmp_path)
    vistas = []
    for ruta in rutas[1:]:
        a = np.asarray(Image.open(ruta).convert("RGB")).astype(int)
        madera = (a[..., 0] > a[..., 1]) & (a[..., 1] > a[..., 2]) & (a[..., 0] - a[..., 2] > 40)
        assert madera.mean() > 0.08, ruta.name   # sin la cruz no hay ningún píxel así
        vistas.append(a)
    assert (vistas[0] != vistas[1]).any()
