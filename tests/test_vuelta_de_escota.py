"""La vuelta de escota: el primer nudo de dos cuerdas, una gruesa y una delgada."""
import pytest

from nudos.cruces import etiqueta
from nudos.errores import cruces_distintos
from nudos.imprimir import imagenes, nombres
from nudos.libre import LIMITES


def test_dos_cuerdas_de_distinto_grosor_y_color(modelo_vuelta_de_escota):
    cuerdas = modelo_vuelta_de_escota.spec.cuerdas
    assert [(c.nombre, c.color) for c in cuerdas] == [("gruesa", "azul"), ("delgada", "crema")]
    assert cuerdas[0].grosor > cuerdas[1].grosor


def test_todos_los_pasos_se_construyen_sin_fallas(modelo_vuelta_de_escota):
    assert modelo_vuelta_de_escota.fallas == []
    assert len(modelo_vuelta_de_escota.pasos) == 4


@pytest.mark.parametrize("cual", ["paso-1", "paso-2", "paso-3", "paso-4", "error", "reverso"])
def test_cada_modelo_cumple_los_limites(modelo_vuelta_de_escota, cual):
    m = modelo_vuelta_de_escota
    r = {"error": m.error, "reverso": m.reverso}.get(cual) or m.pasos[int(cual[-1]) - 1]
    assert r.secuencia == r.esperada
    assert r.medidas["separacion_min"] >= LIMITES["separacion_min"]
    assert r.medidas["curvatura_min"] >= LIMITES["curvatura_min"]
    assert r.medidas["estiramiento_max"] <= LIMITES["estiramiento_max"]


def test_los_cruces_entre_cuerdas_y_el_de_la_delgada_consigo_misma(modelo_vuelta_de_escota):
    """La delgada cruza a la gruesa seis veces y una vez a sí misma: el chicote pasa por
    debajo del tramo que salió del seno."""
    final = modelo_vuelta_de_escota.spec.pasos[-1]
    n_gruesa, n_delgada = final.pasadas
    gruesa = [etiqueta(t) for t in final.secuencia[:n_gruesa]]
    delgada = final.secuencia[n_gruesa:]
    assert (n_gruesa, n_delgada) == (6, 8)
    assert set(gruesa) == {"1", "2", "3", "4", "5", "7"}
    assert [t for t in delgada if etiqueta(t) == "6"] == ["6O", "6U"]


def test_los_dos_chicotes_salen_del_mismo_lado(modelo_vuelta_de_escota):
    """Lo que revisa la ficha: los chicotes quedan del mismo lado del seno, más allá de la
    rama del chicote de la gruesa."""
    r = modelo_vuelta_de_escota.pasos[-1]
    rama = 4.8   # la rama del chicote de la gruesa, en y
    for _, fin in r.reparto.tramos:
        assert r.puntos[fin, 1] > rama


def test_el_error_es_el_chicote_por_encima_de_si_misma(modelo_vuelta_de_escota):
    m = modelo_vuelta_de_escota
    # Las secuencias obtenidas van numeradas en orden de aparición: el cruce 6 es el 7.º.
    assert cruces_distintos(m.pasos[-1].secuencia, m.error.secuencia) == {"7"}


def test_por_detras_todos_los_cruces_quedan_al_reves(modelo_vuelta_de_escota):
    m = modelo_vuelta_de_escota
    al_reves = [t[:-1] + ("U" if t[-1] == "O" else "O") for t in m.pasos[-1].secuencia]
    assert m.reverso.secuencia == al_reves


def test_la_ficha_tiene_todas_sus_imagenes_con_el_nombre_de_cada_cuerda(modelo_vuelta_de_escota):
    imgs = imagenes(modelo_vuelta_de_escota)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 5)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]
    assert nombres(modelo_vuelta_de_escota) == ("cuerda-gruesa", "cuerda-delgada", "chicote")
    # En el paso 1 se mueve la gruesa; desde el 2, la delgada.
    pasos = imgs[0].escena["pasos"]
    assert [p["chicote"] for p in pasos] == [0, 1, 1, 1]
