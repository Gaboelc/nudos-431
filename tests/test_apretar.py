"""El nudo terminado apretado (T7c): la misma secuencia de cruces que el último paso, los
mismos límites, y los pasos de los nudos publicados sin cambios."""
import hashlib
import json

import numpy as np
import pytest

from nudos import apretar as ap, imprimir
from nudos.anfitrion import PENETRACION_MAX
from nudos.construir import _resultado_json
from nudos.cruces import encontrar_cruces, numerada
from nudos.exportar import _puntos
from nudos.imprimir import imagenes
from nudos.libre import LIMITES, construir_paso
from nudos.spec import desde_datos

MODELOS = ("modelo_as_de_guia", "modelo_ballestrinque", "modelo_vuelta_de_escota")


def cumple(r):
    assert r.secuencia == r.esperada
    assert r.medidas["separacion_min"] >= LIMITES["separacion_min"]
    assert r.medidas["curvatura_min"] >= LIMITES["curvatura_min"]
    assert r.medidas["estiramiento_max"] <= LIMITES["estiramiento_max"]
    assert r.medidas.get("penetracion_poste", 0.0) <= PENETRACION_MAX
    assert r.fallas == []


@pytest.mark.parametrize("nombre", MODELOS)
def test_el_apretado_tiene_la_secuencia_del_ultimo_paso_y_cumple_los_limites(nombre, request):
    m = request.getfixturevalue(nombre)
    assert m.fallas == []
    cumple(m.apretado)
    assert m.apretado.secuencia == m.pasos[-1].secuencia
    assert m.apretado.resaltado is None


@pytest.mark.parametrize("nombre", ["modelo_as_de_guia", "modelo_vuelta_de_escota"])
def test_por_detras_el_apretado_tiene_la_secuencia_invertida(nombre, request):
    m = request.getfixturevalue(nombre)
    cumple(m.reverso_apretado)
    al_reves = numerada(ap.invertida(m.pasos[-1].secuencia))
    assert m.reverso_apretado.secuencia == al_reves == m.reverso.secuencia


def test_sobre_el_poste_no_hay_reverso_apretado(modelo_ballestrinque):
    # Se mira el mismo nudo desde el otro lado, como hoy.
    assert modelo_ballestrinque.reverso is None
    assert modelo_ballestrinque.reverso_apretado is None
    assert modelo_ballestrinque.apretado.medidas["penetracion_poste"] <= PENETRACION_MAX


def test_el_as_de_guia_se_aprieta_de_verdad(modelo_as_de_guia):
    m = modelo_as_de_guia
    hoy = m.pasos[-1].medidas["largo"]
    assert m.apretado.medidas["largo"] <= hoy - 5
    assert m.reverso_apretado.medidas["largo"] <= m.reverso.medidas["largo"] - 5


def test_la_gruesa_conserva_su_forma(modelo_vuelta_de_escota):
    """Con cuerdas de distinto grosor solo se acorta la más delgada: lo que la gruesa tiene
    en el nudo queda sujeto."""
    r = modelo_vuelta_de_escota.pasos[-1]
    partes = ap._partes(r.puntos, r.h, r.reparto, encontrar_cruces(r.puntos, r.h, r.reparto.seguido))
    (a0, b0), (a1, b1) = r.reparto.tramos
    assert not (partes[a0:b0 + 1] == ap.NUDO).any()
    assert (partes[a1:b1 + 1] == ap.NUDO).sum() > 100
    # La gruesa conserva su largo, salvo lo que cuesta volver a muestrearla; la delgada se acorta.
    m = modelo_vuelta_de_escota

    def largo(r, k):
        a, b = r.reparto.tramos[k]
        return float(np.linalg.norm(np.diff(r.puntos[a:b + 1], axis=0), axis=1).sum())
    assert largo(m.apretado, 0) == pytest.approx(largo(r, 0), abs=0.3)
    assert largo(m.apretado, 1) < largo(r, 1) - 4


@pytest.mark.parametrize("nombre", ["modelo_as_de_guia", "modelo_ballestrinque"])
def test_construir_dos_veces_da_el_mismo_apretado(nombre, request):
    m = request.getfixturevalue(nombre)
    delante, detras = ap.apretado(m.spec, m.pasos[-1], m.reverso)
    assert delante is not m.pasos[-1]
    assert np.array_equal(delante.puntos, m.apretado.puntos) and delante.h == m.apretado.h
    if detras is not None:
        assert np.array_equal(detras.puntos, m.reverso_apretado.puntos)


def test_el_amarre_no_se_aprieta(modelo_amarre_cuadrado, monkeypatch):
    """Su plantilla ya traza la cuerda tensa: el terminado sigue siendo el último paso y su
    volteo rígido, como hoy, aunque las fichas lleven el apretado."""
    m = modelo_amarre_cuadrado
    assert m.apretado is None and m.reverso_apretado is None
    hoy = [i for i in imagenes(m) if i.nombre.startswith("terminado")]
    monkeypatch.setattr(imprimir, "TERMINADO_APRETADO", True)
    assert [i for i in imagenes(m) if i.nombre.startswith("terminado")] == hoy


def test_las_fichas_aun_no_llevan_el_apretado(modelo_as_de_guia, monkeypatch):
    """Mientras Gabriel decide en papel, el terminado de las fichas es el de hoy."""
    m = modelo_as_de_guia
    assert imprimir.TERMINADO_APRETADO is False

    def terminado():
        frente, atras = imagenes(m)[-2:]
        assert [frente.nombre, atras.nombre] == ["terminado-frente", "terminado-reverso"]
        return frente.escena["pasos"][0]["p"], atras.escena["pasos"][0]["p"]

    assert terminado() == (_puntos(m.pasos[-1].puntos), _puntos(m.reverso.puntos))
    monkeypatch.setattr(imprimir, "TERMINADO_APRETADO", True)
    assert terminado() == (_puntos(m.apretado.puntos), _puntos(m.reverso_apretado.puntos))


# --- La guarda, con un nudo pequeño ---------------------------------------
# Un nudo simple: un trébol abierto, con sus tres cruces alternados.
SIMPLE = desde_datos({
    "slug": "simple", "nombre": "Simple", "familia": "De tope",
    "segmentos": {"s": [[1.1, -12.8], [2.3, -5.9], [3.0, -1.4], [0.3, 3.3], [-4.0, 4.9],
                        [-6.5, 2.8], [-4.9, -0.7], [0.0, -2.4], [4.9, -0.7], [6.5, 2.8],
                        [4.0, 4.9], [-0.3, 3.3], [-3.0, -1.4], [-2.3, -5.9], [-1.1, -12.8]]},
    "pasos": [{"titulo": "T", "texto": "X.", "trazado": ["s"], "secuencia": "1O 2U 3O 1U 2O 3U"}],
})


@pytest.fixture(scope="module")
def simple():
    r = construir_paso(SIMPLE.pasos[0])
    assert r.fallas == []
    return r


def cruces_que_cambian_en(ronda):
    """Busca los cruces como siempre, pero en esa ronda el primero queda al revés."""
    llamadas = []

    def buscar(X, h, u):
        llamadas.append(1)
        cruces = encontrar_cruces(X, h)
        s = np.arange(len(X)) * h
        alturas = [(np.interp(c.sa, s, X[:, 2]), np.interp(c.sb, s, X[:, 2])) for c in cruces]
        # La primera llamada es la del último paso, antes de las rondas.
        if len(llamadas) == ronda + 1:
            alturas[0] = alturas[0][::-1]
        return cruces, alturas
    return buscar


def test_no_se_usa_una_ronda_que_cambia_un_cruce(simple):
    sec = SIMPLE.pasos[0].secuencia
    dos = ap.apretar(simple, sec, rondas=2)
    tres = ap.apretar(simple, sec, rondas=3)
    assert tres.medidas["largo"] < dos.medidas["largo"] < simple.medidas["largo"]
    # Si la tercera cambia un cruce, el apretado es la segunda.
    registro = []
    con_falla = ap.apretar(simple, sec, rondas=3, buscar=cruces_que_cambian_en(3), registro=registro)
    assert [cumple for *_, cumple in registro] == [True, True, False]
    assert np.array_equal(con_falla.puntos, dos.puntos)


def test_si_ninguna_ronda_cumple_queda_el_ultimo_paso(simple):
    nunca = lambda X: ({}, ["falla a propósito"])
    assert ap.apretar(simple, SIMPLE.pasos[0].secuencia, rondas=2, medir=nunca) is simple


def test_se_queda_con_la_ronda_mas_apretada_aunque_otra_falle_despues(simple):
    """No se para en la primera ronda que falla: la curvatura sube y baja entre rondas."""
    sec = SIMPLE.pasos[0].secuencia
    registro = []
    a = ap.apretar(simple, sec, rondas=3, buscar=cruces_que_cambian_en(2), registro=registro)
    assert [cumple for *_, cumple in registro] == [True, False, True]
    assert np.array_equal(a.puntos, ap.apretar(simple, sec, rondas=3).puntos)


# --- Los nudos publicados -------------------------------------------------
# La huella de los pasos y el error de cada nudo publicado, como en modelo.json, sin el título
# ni el texto. Sacada de b3ff5ee, el commit de la referencia de T7b: sus filtros 1 valen
# mientras la geometría y los cruces de los pasos no cambien. Si una de estas cambia a
# propósito, hay que repetir el filtro 1 de ese nudo.
HUELLAS = {
    "modelo_as_de_guia": "9b81be60982f4a5dee00f701a02b21ef4e024c54479c957ef58ba84fb1db4f36",
    "modelo_ballestrinque": "d062f96093e0247a4ef140bb9eb9438330700a8756dc6fc75c1f310e72664fc3",
    "modelo_vuelta_de_escota": "218211b0debab83824a633bb9e5fec051685247b493126bd7c96d854ea1731c3",
    "modelo_amarre_cuadrado": "502240236d423bdbe557429b259d5d224e1c23d277fdf8307117e4d55b7247d0",
}


@pytest.mark.parametrize("nombre", HUELLAS)
def test_los_pasos_y_el_error_de_los_nudos_publicados_no_cambian(nombre, request):
    m = request.getfixturevalue(nombre)
    datos = {"pasos": [_resultado_json(r) for r in m.pasos], "error": _resultado_json(m.error)}
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(texto.encode("utf-8")).hexdigest() == HUELLAS[nombre]
