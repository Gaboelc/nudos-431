"""El adujado: la primera plantilla sin anfitrión, libre sobre la mesa."""
import copy

import numpy as np
import pytest

from nudos.construir import construir, datos_json
from nudos.cruces import encima, etiqueta
from nudos.exportar import datos_visor
from nudos.hoja import desde_abajo, hoja
from nudos.imprimir import imagenes
from nudos.libre import LIMITES, R
from nudos.plantillas.adujado import Adujado
from nudos.plantillas.pasos import geometria
from nudos.spec import SpecError, desde_datos

PASOS = [
    ("Haz los dos primeros senos", "seno-2"),
    ("Haz los demás senos", "senos"),
    ("Junta la aduja y da la primera vuelta", "vuelta-1"),
    ("Da las {vueltas} vueltas", "vueltas"),
    ("Pasa un seno por el ojo", "por-el-ojo"),
    ("Pasa el seno por encima de la punta", "por-encima"),
    ("Tira del chicote", "tirar"),
]


def datos(**cambios):
    base = {
        "slug": "adujado",
        "nombre": "Adujado",
        "familia": "Cuidado de la cuerda",
        "plantilla": {"tipo": "adujado", "senos": 4, "vueltas": 4},
        "pasos": [{"titulo": t, "texto": "Texto.", "hasta": h} for t, h in PASOS],
        "error": {"paso": 1, "variante": "sin-alternar", "titulo": "Sin alternar",
                  "texto": "Texto."},
    }
    base.update(copy.deepcopy(cambios))
    return base


# --- La especificación ----------------------------------------------------
def test_la_especificacion_se_lee():
    spec = desde_datos(datos())
    assert spec.anfitrion is None
    assert spec.plantilla == Adujado(senos=4, vueltas=4)
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]
    assert spec.pasos[3].titulo == "Da las cuatro vueltas"


def test_los_hitos_van_en_el_orden_del_metodo():
    hitos = Adujado(3, 3).hitos()
    alias = {"senos": "seno-3", "vueltas": "vuelta-3"}
    assert all(hitos[a] == hitos[h] for a, h in alias.items())
    orden = sorted((h for h in hitos if h not in alias), key=hitos.get)
    assert orden == ["seno-1", "seno-2", "seno-3", "juntar", "vuelta-1", "vuelta-2", "vuelta-3",
                     "por-el-ojo", "por-encima", "tirar"]


@pytest.mark.parametrize("cambio, pista", [
    ({"plantilla": {"tipo": "adujado", "senos": 2, "vueltas": 4}}, "senos.*de 3 a 6"),
    ({"plantilla": {"tipo": "adujado", "senos": 7, "vueltas": 4}}, "senos.*de 3 a 6"),
    ({"plantilla": {"tipo": "adujado", "senos": 4, "vueltas": 2}}, "vueltas.*de 3 a 8"),
    ({"plantilla": {"tipo": "adujado", "senos": 4, "vueltas": 9}}, "vueltas.*de 3 a 8"),
    ({"plantilla": {"tipo": "adujado", "senos": 4}}, "vueltas"),
    ({"plantilla": {"tipo": "adujado", "senos": 4, "vueltas": 4, "ojos": 2}}, "desconocidos"),
    ({"anfitrion": {"tipo": "cabo", "radio": 3, "largo": 30}}, "libre sobre la mesa"),
])
def test_un_adujado_mal_escrito_se_detecta(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(**cambio))


def test_un_hasta_que_no_existe_o_fuera_de_orden_se_detecta():
    d = datos()
    d["pasos"][0]["hasta"] = "seno-5"
    with pytest.raises(SpecError, match="«hasta» es uno de"):
        desde_datos(d)
    d = datos()
    d["pasos"][2], d["pasos"][3] = d["pasos"][3], d["pasos"][2]
    with pytest.raises(SpecError):
        desde_datos(d)


def test_el_ultimo_paso_tira_del_chicote():
    d = datos()
    d["pasos"] = d["pasos"][:-1]
    with pytest.raises(SpecError, match="tirar"):
        desde_datos(d)


def test_las_demas_plantillas_siguen_pidiendo_su_anfitrion():
    d = {"slug": "x", "nombre": "X", "familia": "F",
         "plantilla": {"tipo": "refuerzo-de-cabo", "vueltas": 4},
         "pasos": [{"titulo": "T", "texto": "Texto.", "hasta": "cortar"}]}
    with pytest.raises(SpecError, match="anfitrión cabo"):
        desde_datos(d)


# --- La cuerda del método -------------------------------------------------
@pytest.fixture(scope="module")
def modelo():
    return construir(desde_datos(datos()))


@pytest.fixture(scope="module")
def cuerda(modelo):
    return geometria(modelo.spec).cuerda()


def test_los_cruces_del_metodo(cuerda):
    """Cada seno se cierra sobre el extremo o bajo él; cada vuelta cruza los 2n tramos de la
    banda por arriba y por abajo; la cuerda pasa sobre los tramos de delante hacia el ojo; el
    seno por el ojo pasa bajo las puntas y el chicote sale sobre los de detrás; el seno que
    rodea la aduja la cruza por arriba y por abajo, y pasa sobre la cuerda que entra al ojo."""
    n = m = 4
    cuantos = {h: len(s) // 2 for h, s in cuerda.secuencias.items()}
    for k in range(1, n + 1):
        assert cuantos[f"seno-{k}"] == k
    assert cuantos["juntar"] == n
    for j in range(1, m + 1):
        assert cuantos[f"vuelta-{j}"] == n + 4 * n * j
    assert cuantos["por-el-ojo"] == 5 * n + 4 * n * m
    assert cuantos["por-encima"] == cuantos["tirar"] == 7 * n + 4 * n * m + 1


def test_los_senos_alternan_sobre_el_extremo(cuerda):
    cruces = [c for c in cuerda._pasos["seno-4"]["cruces"] if "extremo" in c["piezas"]]
    por_seno = {c["piezas"][1]: c["encima"] for c in cruces}
    # La primera pasada es la del extremo: va por encima solo de los senos pares.
    assert por_seno == {"seno-1": False, "seno-2": True, "seno-3": False, "seno-4": True}


def test_todos_los_pasos_se_construyen_sin_fallas(modelo):
    assert modelo.fallas == []
    assert len(modelo.pasos) == 7 and modelo.error is not None and modelo.reverso is not None
    for r in modelo.pasos:
        assert r.medidas["separacion_min"] >= LIMITES["separacion_min"]
        assert r.medidas["curvatura_min"] >= LIMITES["curvatura_min"]
        assert r.medidas["estiramiento_max"] <= LIMITES["estiramiento_max"]
        assert r.puntos[:, 2].min() >= R - 1e-9


@pytest.mark.parametrize("senos, vueltas", [(3, 3), (6, 8)])
def test_otras_medidas_se_construyen_sin_fallas(senos, vueltas):
    d = datos(plantilla={"tipo": "adujado", "senos": senos, "vueltas": vueltas})
    assert construir(desde_datos(d)).fallas == []


def test_los_cruces_conservan_su_etiqueta(cuerda):
    """Al juntar la aduja, los cruces de los senos con el extremo son los mismos; al tirar, los
    del seno que rodea la aduja también."""
    def etiquetas(hito, pieza):
        return {c["etiqueta"] for c in cuerda._pasos[hito]["cruces"] if pieza in c["piezas"]}
    assert etiquetas("seno-4", "extremo") == etiquetas("juntar", "extremo") != set()
    assert etiquetas("por-encima", "lazo-arriba") == etiquetas("tirar", "lazo-arriba") != set()
    # Los del seno con las puntas del ojo desaparecen al pasarlo por encima.
    assert etiquetas("por-el-ojo", "seno-del-ojo").isdisjoint(
        {c["etiqueta"] for c in cuerda._pasos["por-encima"]["cruces"]})


def test_el_error_es_el_segundo_seno_por_encima_del_extremo(modelo, cuerda):
    error = geometria(modelo.spec).cuerda("sin-alternar")
    bien, mal = cuerda.secuencias["seno-2"], error.secuencias["seno-2"]
    assert len(bien) == len(mal) == 4
    distintas = [(a, b) for a, b in zip(bien, mal) if a != b]
    assert len(distintas) == 2 and all(etiqueta(a) == etiqueta(b) for a, b in distintas)
    assert modelo.error.n == 1 and modelo.error.secuencia == modelo.error.esperada


def test_por_detras_se_voltea_como_una_pagina(modelo):
    final, reverso = modelo.pasos[-1], modelo.reverso
    X, Y = final.puntos, reverso.puntos
    assert np.allclose(Y[:, 0], -X[:, 0]) and np.allclose(Y[:, 1], X[:, 1])
    assert np.allclose(Y[:, 2] + X[:, 2], Y[0, 2] + X[0, 2])
    assert Y[:, 2].min() == pytest.approx(R)
    assert [encima(t) for t in reverso.esperada] == [not encima(t) for t in final.esperada]
    assert reverso.fallas == []


def test_la_escena_es_una_cuerda_sin_anfitrion(modelo):
    d = datos_visor(modelo)
    assert d["anfitrion"] is None and d["dos_remates"] is True
    assert all(p["nombres"] == ["chicote"] for p in d["pasos"])
    imgs = imagenes(modelo)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 8)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]


def test_la_hoja_lleva_la_aduja_desde_abajo(modelo):
    d = datos_json(modelo)
    d = {**d, "pasos": d["pasos"][-1:]}
    abajo = desde_abajo(d)
    X = np.asarray(d["pasos"][0]["puntos"])
    Y = np.asarray(abajo["pasos"][0]["puntos"])
    assert np.allclose(Y[:, 1], -X[:, 1]) and Y[:, 2].min() == pytest.approx(R)
    assert abajo["encuadre"]["y"] == [-d["encuadre"]["y"][1], -d["encuadre"]["y"][0]] \
        if d.get("encuadre") else True
    assert hoja(abajo, "arriba").width > 0
