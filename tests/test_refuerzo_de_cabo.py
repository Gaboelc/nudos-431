"""El refuerzo de cabo: la plantilla sobre la punta de un cabo (anfitrión «cabo»)."""
import copy

import numpy as np
import pytest

from nudos.anfitrion import PENETRACION_MAX, Cabo
from nudos.construir import construir, datos_json
from nudos.cruces import etiqueta
from nudos.exportar import datos_visor
from nudos.ficha import POR_DETRAS
from nudos.hoja import CREMA, hoja, mapa
from nudos.imprimir import imagenes
from nudos.libre import LIMITES, R
from nudos.plantillas.pasos import geometria
from nudos.plantillas.refuerzo import RefuerzoDeCabo, largo_minimo
from nudos.spec import Anfitrion, SpecError, desde_datos

PASOS = [
    ("Da la primera vuelta", "vuelta-1"),
    ("Completa las {vueltas} vueltas", "vueltas"),
    ("Haz un seno", "seno"),
    ("Da {vueltas} vueltas sobre el seno", "seno-vueltas"),
    ("Pasa el chicote por el seno", "por-el-seno"),
    ("Tira del extremo corto", "tirar"),
    ("Corta las puntas", "cortar"),
]
CABO = Anfitrion("cabo", radio=3.0, largo=30.0)


def datos(**cambios):
    base = {
        "slug": "refuerzo-de-cabo",
        "nombre": "Refuerzo de cabo",
        "familia": "Cuidado de la cuerda",
        "anfitrion": {"tipo": "cabo", "radio": 3, "largo": 30},
        "plantilla": {"tipo": "refuerzo-de-cabo", "vueltas": 4},
        "pasos": [{"titulo": t, "texto": "Texto.", "hasta": h} for t, h in PASOS],
        "error": {"paso": 5, "variante": "por-fuera-del-seno", "titulo": "Por fuera",
                  "texto": "Texto."},
    }
    base.update(copy.deepcopy(cambios))
    return base


# --- La especificación ----------------------------------------------------
def test_la_especificacion_se_lee():
    spec = desde_datos(datos())
    assert spec.anfitrion == CABO
    assert spec.plantilla == RefuerzoDeCabo(vueltas=4)
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]
    assert spec.pasos[1].titulo == "Completa las cuatro vueltas"


def test_los_hitos_van_en_el_orden_del_metodo():
    hitos = RefuerzoDeCabo(4).hitos()
    alias = {"vueltas": "vuelta-4", "seno-vueltas": "seno-vuelta-4"}
    assert all(hitos[a] == hitos[h] for a, h in alias.items())
    orden = sorted((h for h in hitos if h not in alias), key=hitos.get)
    assert orden == ["colocar", "vuelta-1", "vuelta-2", "vuelta-3", "vuelta-4", "seno",
                     "seno-vuelta-1", "seno-vuelta-2", "seno-vuelta-3", "seno-vuelta-4",
                     "por-el-seno", "tirar", "cortar"]


@pytest.mark.parametrize("cambio, pista", [
    ({"plantilla": {"tipo": "refuerzo-de-cabo", "vueltas": 3}}, "de 4 a 8"),
    ({"plantilla": {"tipo": "refuerzo-de-cabo", "vueltas": 9}}, "de 4 a 8"),
    ({"plantilla": {"tipo": "refuerzo-de-cabo", "vueltas": 4, "seno": 1}}, "desconocidos"),
    ({"anfitrion": {"tipo": "cabo", "radio": 3, "largo": 20}}, "no cabe en el cabo"),
    ({"anfitrion": {"tipo": "cabo", "radio": 1, "largo": 30}}, "radio del cabo"),
    ({"anfitrion": {"tipo": "cabo", "radio": 9, "largo": 30}}, "radio del cabo"),
    ({"anfitrion": {"tipo": "cabo", "radio": 3}}, "largo"),
    ({"anfitrion": {"tipo": "poste", "radio": 3, "desde": -10, "hasta": 10}}, "anfitrión cabo"),
])
def test_un_refuerzo_mal_escrito_se_detecta(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(**cambio))


def test_el_largo_minimo_crece_con_las_vueltas():
    assert largo_minimo(4) <= 30 < largo_minimo(8)


def test_el_cabo_necesita_una_plantilla():
    d = datos()
    del d["plantilla"], d["error"]
    d["segmentos"] = {"a": [[0, 0], [1, 0]]}
    with pytest.raises(SpecError, match="refuerzo-de-cabo"):
        desde_datos(d)


def test_el_ultimo_paso_corta_las_puntas():
    d = datos()
    d["pasos"] = d["pasos"][:-1]
    with pytest.raises(SpecError, match="cortar"):
        desde_datos(d)


def test_el_error_va_desde_que_se_pasa_el_chicote():
    with pytest.raises(SpecError, match="por-el-seno"):
        desde_datos(datos(error={"paso": 4, "variante": "por-fuera-del-seno",
                                 "titulo": "T", "texto": "Texto."}))


# --- El cabo --------------------------------------------------------------
def test_el_cabo_va_de_la_punta_hacia_atras_y_se_apoya_en_el_cordel():
    cabo = Cabo(CABO)
    assert cabo.zc == pytest.approx(CABO.radio + 2 * R) and cabo.rb == pytest.approx(CABO.radio + R)
    assert cabo.datos() == {"tipo": "cabo", "radio": 3.0, "largo": 30.0, "z": 4.0}
    # Empuja hacia afuera lo que entró, pero no más allá de la punta ni del otro extremo.
    X = np.array([[-5.0, 0.0, cabo.zc + 1.0], [1.0, 0.0, cabo.zc], [-31.0, 0.0, cabo.zc]])
    Y = X.copy()
    cabo.empujar(Y, np.ones(3, bool))
    assert np.hypot(Y[0, 1], Y[0, 2] - cabo.zc) == pytest.approx(cabo.rb)
    assert np.allclose(Y[1:], X[1:])
    assert cabo.penetracion(X) == pytest.approx(cabo.rb - 1.0)
    assert cabo.penetracion(X[1:]) == 0.0


# --- La cuerda del método -------------------------------------------------
@pytest.fixture(scope="module")
def modelo():
    return construir(desde_datos(datos()))


@pytest.fixture(scope="module")
def cuerda(modelo):
    return geometria(modelo.spec).cuerda()


def test_los_cruces_del_metodo(cuerda):
    """Cada vuelta pasa sobre el extremo corto; la rama que vuelve, sobre las primeras vueltas;
    las vueltas de encima, sobre las dos ramas; la última vuelta, otra vez sobre la rama que
    vuelve, y la curva del seno, sobre el chicote."""
    n = 4
    cuantos = {h: len(s) // 2 for h, s in cuerda.secuencias.items()}
    for k in range(1, n + 1):
        assert cuantos[f"vuelta-{k}"] == k
        assert cuantos[f"seno-vuelta-{k}"] == 2 * n + 2 * k
    assert cuantos["seno"] == 2 * n
    assert cuantos["por-el-seno"] == 4 * n + 2


def test_todos_los_pasos_se_construyen_sin_fallas(modelo):
    assert modelo.fallas == []
    for r in modelo.pasos:
        assert r.medidas["separacion_min"] >= LIMITES["separacion_min"]
        assert r.medidas["curvatura_min"] >= LIMITES["curvatura_min"]
        assert r.medidas["penetracion_cabo"] <= PENETRACION_MAX


def test_la_curva_engancha_al_chicote_con_la_misma_etiqueta_al_tirar(cuerda, modelo):
    """El cruce de la curva con el chicote es el mismo al pasarlo y al tirar: la curva se
    acerca a las vueltas y el cruce se corre a lo largo del cabo, sin saltar."""
    def de_la_curva(hito):
        return {c["etiqueta"] for c in cuerda._pasos[hito]["cruces"]
                if set(c["piezas"]) == {"curva", "chicote"}}
    assert de_la_curva("por-el-seno") == de_la_curva("tirar") != set()
    assert de_la_curva("cortar") == set()   # al cortar, el chicote es otro tramo, escondido


def test_el_error_es_el_chicote_por_encima_de_la_curva(modelo, cuerda):
    error = geometria(modelo.spec).cuerda("por-fuera-del-seno")
    bien, mal = cuerda.secuencias["por-el-seno"], error.secuencias["por-el-seno"]
    assert len(bien) == len(mal)
    distintas = [(a, b) for a, b in zip(bien, mal) if a != b]
    assert len(distintas) == 2 and all(etiqueta(a) == etiqueta(b) for a, b in distintas)
    assert modelo.error is not None and modelo.error.n == 5


def test_al_cortar_no_hay_nombres_ni_resaltado(modelo):
    pasos = datos_visor(modelo)["pasos"]
    assert all(p["nombres"] == ["chicote"] for p in pasos[:-1])
    assert pasos[-1]["nombres"] == [] and pasos[-1]["hl"] is None


def test_por_detras_el_cabo_se_gira_en_la_mano(modelo):
    cabo, final = Cabo(CABO), modelo.pasos[-1]
    girado, datos_cabo = cabo.voltear(final)
    X, Y = final.puntos, girado.puntos
    # Media vuelta alrededor del eje del cabo, a lo largo de x: un giro rígido.
    assert np.allclose(Y[:, 0], X[:, 0]) and np.allclose(Y[:, 1], -X[:, 1])
    assert np.allclose(Y[:, 2] + X[:, 2], Y[0, 2] + X[0, 2])
    # Lo más bajo queda sobre la mesa y el cordel sigue sin entrar en el cabo girado.
    assert min(Y[:, 2].min() - R, datos_cabo["z"] - CABO.radio) == pytest.approx(0, abs=1e-9)
    m = (Y[:, 0] > -CABO.largo) & (Y[:, 0] < 0)
    assert np.hypot(Y[m, 1], Y[m, 2] - datos_cabo["z"]).min() >= cabo.rb - PENETRACION_MAX
    assert girado.secuencia == final.secuencia and girado.resaltado is None


def test_las_imagenes_del_refuerzo(modelo):
    imgs = imagenes(modelo)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 8)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]
    assert {i.vista for i in imgs} == {"3d"}
    frente, reverso = imgs[-2:]
    assert frente.escena["anfitrion"] == Cabo(CABO).datos()
    assert reverso.escena["anfitrion"] == Cabo(CABO).voltear(modelo.pasos[-1])[1]
    assert "cabo" in POR_DETRAS["cabo"]


def test_la_hoja_dibuja_el_cabo_y_su_mapa(modelo):
    d = datos_json(modelo)
    d = {**d, "pasos": d["pasos"][-2:]}
    imagen = np.asarray(hoja(d, "arriba", Cabo(CABO).datos()).convert("RGB")).astype(float) / 255
    crema = np.all(np.abs(imagen - CREMA) < 0.08, axis=-1)
    assert crema.mean() > 0.02   # sin el cabo no hay ningún píxel así
    plano = mapa(d, Cabo(CABO))
    assert plano.width > 0 and plano.height > 0
