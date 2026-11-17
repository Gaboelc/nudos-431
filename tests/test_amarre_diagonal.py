"""El amarre diagonal: una plantilla sobre la cruz del amarre cuadrado (tanda 4)."""
import copy
import math

import numpy as np
import pytest

from nudos.anfitrion import PENETRACION_MAX, Cruz
from nudos.construir import DESPLAZAMIENTO_MAX
from nudos.cruces import numerada
from nudos.exportar import datos_visor
from nudos.imprimir import imagenes
from nudos.libre import LIMITES, relajar
from nudos.plantillas.amarre_diagonal import AmarreDiagonal, cuerda
from nudos.spec import Anfitrion, SpecError, desde_datos

PASOS = [
    ("Haz una vuelta de braza alrededor de los dos palos", "inicio"),
    ("Da las vueltas en diagonal", "vueltas"),
    ("Cambia a la otra diagonal", "segunda-1"),
    ("Completa las vueltas de la otra diagonal", "segundas"),
    ("Da el primer ahorcado", "ahorcado-1"),
    ("Completa los ahorcados", "ahorcados"),
    ("Cierra con un ballestrinque", "cierre"),
]
POR_FUERA = "ahorcados-por-fuera"
# La vuelta de braza: el chicote se enrolla en su tramo (1 a 5) y rodea el firme (6 y 7), como
# en la ficha publicada de la vuelta de braza, leída desde el chicote.
BRAZA = ("1U", "2O", "3U", "4O", "5U", "6O", "7U", "5O", "4U", "3O", "2U", "1O", "7O", "6U")


def datos(**cambios):
    base = {
        "slug": "amarre-diagonal",
        "nombre": "Amarre diagonal",
        "familia": "Amarres",
        "anfitrion": {"tipo": "cruz", "radio": 3.0, "largo": 44},
        "plantilla": {
            "tipo": "amarre-diagonal",
            "vueltas": 3,
            "ahorcados": 3,
            "cierre": {"poste": "arriba", "lado": "derecha"},
        },
        "pasos": [{"titulo": t, "texto": "Texto.", "hasta": h} for t, h in PASOS],
        "error": {"paso": 6, "variante": POR_FUERA, "titulo": "Ahorcados por fuera",
                  "texto": "Texto."},
    }
    base.update(copy.deepcopy(cambios))
    return base


def con(**cambios_plantilla):
    d = datos()
    d["plantilla"].update(cambios_plantilla)
    return d


def la_cuerda(variante=None, radio=3.0, **cambios):
    d = con(**cambios)
    d["anfitrion"]["radio"] = radio
    spec = desde_datos(d)
    return cuerda(spec.plantilla, Cruz(spec.anfitrion), variante)


def cruces(n, m):
    """Los cruces del método: los 7 de la vuelta de braza, los de las dos diagonales (cada
    vuelta de la segunda pasa por encima de cada vuelta de la primera y de la vuelta de braza,
    sobre un palo y bajo el otro), los de los ahorcados (cada uno cruza las dos esquinas de
    cada una de las 2n + 1 vueltas) y los 2 del ballestrinque de cierre."""
    return 7 + 2 * n * (n + 1) + 2 * m * (2 * n + 1) + 2


# --- La especificación ----------------------------------------------------
def test_la_especificacion_se_lee():
    spec = desde_datos(datos())
    p = spec.plantilla
    assert isinstance(p, AmarreDiagonal)
    assert (p.vueltas, p.ahorcados, p.cierre.poste, p.cierre.lado) == (3, 3, "arriba", "derecha")
    assert [x.hasta for x in spec.pasos] == [h for _, h in PASOS]
    assert spec.error.variante == POR_FUERA


def test_los_hitos_siguen_la_cuerda():
    hitos = desde_datos(datos()).plantilla.hitos()
    assert list(hitos) == ["inicio", "vuelta-1", "vuelta-2", "vuelta-3", "vueltas", "segunda-1",
                           "segunda-2", "segunda-3", "segundas", "ahorcado-1", "ahorcado-2",
                           "ahorcado-3", "ahorcados", "cierre-1", "cierre"]
    assert hitos["vueltas"] == hitos["vuelta-3"] and hitos["segundas"] == hitos["segunda-3"]
    assert "inicio-1" not in hitos   # la vuelta de braza sin el chicote no es un comienzo de la cuerda


def test_las_medidas_salen_en_letras():
    d = datos()
    d["pasos"][1]["titulo"] = "Da {vueltas} vueltas en diagonal"
    d["pasos"][5]["titulo"] = "Completa los {ahorcados} ahorcados"
    spec = desde_datos(d)
    assert spec.pasos[1].titulo == "Da tres vueltas en diagonal"
    assert spec.pasos[5].titulo == "Completa los tres ahorcados"


@pytest.mark.parametrize("cambio, pista", [
    ({"vueltas": 5}, "de 2 a 4"),
    ({"vueltas": 1}, "de 2 a 4"),
    ({"ahorcados": 7}, "ahorcados"),
    ({"inicio": {"poste": "abajo", "lado": "delante"}}, "campos desconocidos: inicio"),
    ({"cierre": {"poste": "abajo", "lado": "delante"}}, "palo de arriba"),
    ({"cierre": {"poste": "arriba", "lado": "delante"}}, "izquierda o derecha"),
])
def test_una_plantilla_mal_escrita_se_detecta(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(con(**cambio))


def test_un_hito_que_no_existe_con_esas_medidas():
    d = con(vueltas=2)
    desde_datos(d)   # «vueltas» y «segundas» siguen valiendo con 2 vueltas
    d["pasos"][1]["hasta"] = "vuelta-3"
    with pytest.raises(SpecError, match="«hasta» es uno de"):
        desde_datos(d)


# --- La cruz -----------------------------------------------------------------
def test_bajo_el_palo_de_abajo_van_dos_capas():
    """En el diagonal, las dos diagonales se cruzan bajo el palo de abajo: su eje queda a
    radio + 2,1. El cuadrado sigue a radio + 1."""
    diagonal = desde_datos(datos()).anfitrion
    assert diagonal.capas == 2
    assert Cruz(diagonal).zb == pytest.approx(3.0 + 2.1)
    assert Cruz(diagonal).zt == pytest.approx(3.0 + 2.1 + 6.0)
    cuadrado = Anfitrion("cruz", 2.5, largo=40)
    assert cuadrado.capas == 1 and Cruz(cuadrado).zb == 3.5


# --- La cuerda entera ----------------------------------------------------------
@pytest.mark.parametrize("vueltas, ahorcados, radio", [(2, 2, 3.0), (3, 3, 3.0), (3, 6, 3.0),
                                                      (4, 3, 4.0)])
def test_la_secuencia_del_metodo(vueltas, ahorcados, radio):
    c = la_cuerda(vueltas=vueltas, ahorcados=ahorcados, radio=radio)
    sec = c.secuencias
    n, m = vueltas, ahorcados
    assert sec["inicio"] == BRAZA
    assert sec["vueltas"] == BRAZA   # las vueltas de una diagonal no se cruzan
    assert len(sec["segundas"]) // 2 == 7 + 2 * n * (n + 1)
    assert len(sec["ahorcado-1"]) // 2 == 7 + 2 * n * (n + 1) + 2 * (2 * n + 1)
    assert len(sec["cierre"]) // 2 == cruces(n, m)
    # La segunda diagonal pasa siempre por encima de la primera.
    nuevos = [t for t in sec["segundas"] if t[:-1] not in {x[:-1] for x in sec["vueltas"]}]
    pasadas = {}
    for t in nuevos:
        pasadas.setdefault(t[:-1], []).append(t[-1])
    assert all(v == ["U", "O"] for v in pasadas.values())


def test_las_vueltas_tienen_que_caber_entre_los_palos():
    """Cada vuelta baja entre los palos: con palos de radio 3, 4 vueltas en cada diagonal no
    caben, y la plantilla lo dice en vez de construir otro nudo."""
    with pytest.raises(ValueError, match="no caben entre palos de radio 3"):
        la_cuerda(vueltas=4)


def test_los_hitos_avanzan_por_la_misma_cuerda():
    c = la_cuerda()
    orden = list(desde_datos(datos()).plantilla.hitos())
    indices = [c.hitos[h] if h in c.hitos else c.hitos[c.alias[h]] for h in orden]
    assert indices == sorted(indices)
    assert c.hitos["cierre"] == len(c.puntos) - 1
    assert set(c.restos) == set(c.hitos) - {"cierre"}
    for nombre, resto in c.restos.items():
        assert resto[-1][2] == pytest.approx(0.5), nombre   # el resto termina sobre la mesa


def test_el_cierre_a_la_izquierda_es_el_reflejo():
    base = la_cuerda()
    izquierda = la_cuerda(cierre={"poste": "arriba", "lado": "izquierda"})
    assert np.allclose(izquierda.puntos * [-1, 1, 1], base.puntos)
    assert izquierda.secuencias == base.secuencias


def test_la_vuelta_de_braza_no_se_relaja():
    """La vuelta de braza va trazada tensa y la relajación la deshace: sus puntos quedan
    quietos, y también el firme donde el chicote lo rodea. El resto de la cuerda, no."""
    c = la_cuerda()
    q = c.quietos
    assert q is not None and len(q) == len(c.puntos)
    assert q[:20].all()   # el chicote, desde su punta
    assert not q[c.hitos["vuelta-1"]:].any()


def test_relajar_deja_quietos_los_puntos_quietos():
    X = np.column_stack([np.linspace(0, 10, 51), np.zeros(51), np.full(51, 0.5)])
    X[20:30, 2] = 3.0   # un tramo en el aire
    quietos = np.zeros(51, bool)
    quietos[20:30] = True
    Y = relajar(X, 0.2, iteraciones=50, quietos=quietos)
    assert np.array_equal(Y[20:30], X[20:30])
    Z = relajar(X, 0.2, iteraciones=50)
    assert not np.array_equal(Z[20:30], X[20:30])


# --- El error común -------------------------------------------------------------
@pytest.mark.parametrize("vueltas, ahorcados", [(2, 2), (3, 3), (3, 4)])
def test_el_error_cruza_las_mismas_esquinas(vueltas, ahorcados):
    """Como en el cuadrado: los ahorcados por encima del palo de arriba cruzan lo mismo que los
    bien hechos, y sobre cada esquina pasan en el orden contrario."""
    bien = la_cuerda(vueltas=vueltas, ahorcados=ahorcados).secuencias
    mal = la_cuerda(POR_FUERA, vueltas=vueltas, ahorcados=ahorcados).secuencias
    assert mal.keys() == bien.keys()
    for hito in bien:
        assert sorted(mal[hito]) == sorted(bien[hito]), hito
        assert [t for t in mal[hito] if t.endswith("O")] == [t for t in bien[hito] if t.endswith("O")]
    assert mal["segundas"] == bien["segundas"] and mal["ahorcados"] != bien["ahorcados"]


def test_el_error_es_el_mismo_amarre_hasta_las_segundas_vueltas():
    bien, mal = la_cuerda(), la_cuerda(POR_FUERA)
    i = bien.hitos["segunda-3"]
    assert mal.hitos["segunda-3"] == i
    assert np.array_equal(mal.puntos[:i + 1], bien.puntos[:i + 1])


def test_una_variante_que_la_plantilla_no_sabe_construir():
    with pytest.raises(ValueError, match="no tiene la variante una-sola-diagonal"):
        la_cuerda("una-sola-diagonal")


# --- El nudo ------------------------------------------------------------------
@pytest.fixture(scope="module")
def modelo(modelo_amarre_diagonal):
    """La especificación de specs/, con las mismas medidas que datos()."""
    return modelo_amarre_diagonal


def test_todos_los_pasos_se_construyen_sin_fallas(modelo):
    assert modelo.fallas == []
    assert [r.n for r in modelo.pasos] == list(range(1, 8))
    assert modelo.error is not None and modelo.error.n == 6


def test_la_cuerda_no_atraviesa_los_palos_ni_otras_vueltas(modelo):
    for r in [*modelo.pasos, modelo.error]:
        m = r.medidas
        assert m["penetracion_palos"] <= PENETRACION_MAX, r.n
        assert m["separacion_min"] >= LIMITES["separacion_min"], r.n
        assert m["curvatura_min"] >= LIMITES["curvatura_min"], r.n
        assert m["estiramiento_max"] <= LIMITES["estiramiento_max"], r.n


def test_los_cruces_coinciden_con_el_metodo(modelo):
    c = la_cuerda()
    for r, (_, hasta) in zip(modelo.pasos, PASOS):
        assert r.secuencia == r.esperada == numerada(c.secuencias[hasta]), r.n
    assert len(modelo.pasos[-1].secuencia) // 2 == cruces(3, 3) == 75
    e = modelo.error
    assert e.secuencia == e.esperada == numerada(la_cuerda(POR_FUERA).secuencias["ahorcados"])


def test_cada_paso_resalta_lo_que_agrega(modelo):
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
            assert math.hypot(x - final[et][0], y - final[et][1]) <= DESPLAZAMIENTO_MAX, (r.n, et)


# --- Escena e impresión ---------------------------------------------------------
def test_la_escena_dibuja_la_cruz_mas_alta(modelo):
    d = datos_visor(modelo)
    assert d["anfitrion"] == {"tipo": "cruz", "radio": 3.0, "largo": 44,
                              "z_abajo": pytest.approx(5.1), "z_arriba": pytest.approx(11.1)}
    assert d["dos_remates"] is True


def test_firme_solo_en_la_vuelta_de_braza(modelo):
    pasos = datos_visor(modelo)["pasos"]
    assert "nombres" not in pasos[0]   # «Firme» y «Chicote», como la vuelta de braza
    assert all(p["nombres"] == ["chicote"] for p in pasos[1:])


def test_las_imagenes_del_amarre(modelo):
    imgs = imagenes(modelo)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 8)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]
    por_nombre = {i.nombre: i for i in imgs}
    assert [p["n"] for p in por_nombre["error"].escena["pasos"]] == [6, 6]
    assert por_nombre["terminado-reverso"].escena["anfitrion"] == Cruz(
        desde_datos(datos()).anfitrion).voltear(modelo.pasos[-1])[1]
