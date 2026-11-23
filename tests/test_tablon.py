"""El tablón: una tabla con los cantos redondeados, para la eslinga de andamio (formato v1.11).

Es el poste con otro perfil, así que el nudo de prueba es el ballestrinque de specs/, puesto
sobre un listón: los mismos segmentos, con {tablon: …} en vez de {poste: …} y corridos hacia
x negativo, porque la punta del tablón está en x = 0."""

import copy
import math

import numpy as np
import pytest
import yaml
from PIL import Image

from nudos import SPECS
from nudos.anfitrion import CANTO, PENETRACION_MAX, Poste, Tablon, solido, sobre_superficie
from nudos.construir import construir, datos_json
from nudos.exportar import datos_escena
from nudos.ficha import POR_DETRAS
from nudos.hoja import MADERA, hoja
from nudos.imprimir import VISTA_PASOS, imagenes
from nudos.spec import Anfitrion, SpecError, desde_datos

TABLON = Anfitrion("tablon", ancho=12.0, grueso=3.0, largo=30.0)
LISTON = {"tipo": "tablon", "ancho": 4, "grueso": 2.4, "largo": 30}
CORRER = -8.0   # el ballestrinque, que va alrededor de x = 0, queda a 8 de la punta


def datos(anfitrion=LISTON):
    """El ballestrinque de specs/ sobre un listón."""
    with open(SPECS / "ballestrinque.yaml", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    d = copy.deepcopy(d)
    d["slug"], d["nombre"], d["estado"] = "ballestrinque-en-un-liston", "Prueba", "borrador"
    d.pop("filtros", None)
    d["anfitrion"] = dict(anfitrion)
    for nombre, puntos in d["segmentos"].items():
        if isinstance(puntos, dict):
            d["segmentos"][nombre] = {"tablon": [[x + CORRER, a] for x, a in puntos["poste"]]}
        else:
            d["segmentos"][nombre] = [[x + CORRER, y] for x, y in puntos]
    for parte in (d, d.get("error") or {}, d.get("terminado") or {}):
        if "encuadre" in parte:
            parte["encuadre"]["x"] = [v + CORRER for v in parte["encuadre"]["x"]]
    return d


def datos_vueltas():
    """Dos vueltas y media sobre un tablón de 12 × 3, como el primer paso de la eslinga de
    andamio: el firme sube por la cara de delante, la cuerda pasa tres veces por arriba y el
    chicote cae por detrás."""
    x0, sep = -10.0, 2.5   # la primera pasada por arriba y la distancia entre pasadas
    vuelta = [[round(x0 + sep * (-a / 360), 4), float(a)] for a in range(100, -821, -20)]
    return {
        "slug": "vueltas-en-un-tablon", "nombre": "Prueba", "familia": "Amarres",
        "anfitrion": {"tipo": "tablon", "ancho": 12, "grueso": 3, "largo": 30},
        "encuadre": {"x": [-17.0, 3.0], "y": [-13.0, 13.0]},
        "segmentos": {
            "firme": [[vuelta[0][0] - 0.4, -16.0], [vuelta[0][0] - 0.1, -10.0]],
            "vuelta": {"tablon": vuelta},
            "chicote": [[vuelta[-1][0] + 0.1, 10.0], [vuelta[-1][0] + 0.4, 16.0]],
        },
        "pasos": [{"titulo": "Da dos vueltas y media", "texto": "Prueba.",
                   "trazado": ["firme", "vuelta", "chicote"], "secuencia": ""}],
    }


@pytest.fixture(scope="module")
def modelo():
    return construir(desde_datos(datos()))


# --- La especificación ------------------------------------------------------
def test_se_carga_con_su_ancho_su_grueso_y_su_largo():
    s = desde_datos(datos())
    assert s.anfitrion == Anfitrion("tablon", ancho=4.0, grueso=2.4, largo=30.0)
    assert s.anfitrion.radio is None and not s.anfitrion.en_la_mesa


@pytest.mark.parametrize("anfitrion, mensaje", [
    ({"tipo": "tablon", "ancho": 12, "grueso": 3}, "largo"),
    ({"tipo": "tablon", "ancho": 1.5, "grueso": 3, "largo": 30}, "ancho.*del tablón.*al menos 2"),
    ({"tipo": "tablon", "ancho": 12, "grueso": 1, "largo": 30}, "grueso.*al menos 2"),
    ({"tipo": "tablon", "ancho": 12, "grueso": 3, "largo": 3}, "largo.*mayor que su grueso"),
    ({"tipo": "tablon", "ancho": 12, "grueso": 3, "largo": 30, "radio": 2}, "desconocidos"),
])
def test_medidas_que_no_valen(anfitrion, mensaje):
    with pytest.raises(SpecError, match=mensaje):
        desde_datos(datos(anfitrion))


def test_sobre_el_tablon_los_segmentos_se_escriben_tablon_y_sobre_el_poste_poste():
    d = datos()
    d["segmentos"]["vuelta-1"] = {"poste": d["segmentos"]["vuelta-1"]["tablon"]}
    with pytest.raises(SpecError, match=r"\{tablon: \[\[x, ángulo\]"):
        desde_datos(d)
    with open(SPECS / "ballestrinque.yaml", encoding="utf-8") as f:
        b = yaml.safe_load(f)
    b["segmentos"]["vuelta-1"] = {"tablon": b["segmentos"]["vuelta-1"]["poste"]}
    with pytest.raises(SpecError, match=r"\{poste: \[\[x, ángulo\]"):
        desde_datos(b)


# --- El sólido --------------------------------------------------------------
def test_los_angulos_caen_en_el_medio_de_cada_cara():
    t = Tablon(TABLON)
    X = t.punto(np.full(4, -5.0), np.array([0.0, 90.0, 180.0, -90.0]))
    # 0° arriba, 90° hacia quien ata (y negativo), 180° abajo y -90° atrás, a medio diámetro.
    assert np.allclose(X, [[-5, 0, t.zc + 2.0], [-5, -6.5, t.zc], [-5, 0, 0.5], [-5, 6.5, t.zc]])
    assert t.zc == pytest.approx(2.5)   # la cara de abajo, a un diámetro de la mesa


def test_coordenadas_ida_y_vuelta():
    t = Tablon(TABLON)
    g = np.random.default_rng(1).uniform(-720, 720, 500)
    for r in (None, t.rb + 0.8):
        X = t.punto(np.full(len(g), -3.0), g, r)
        _, th, d = t.cilindricas(X)
        assert np.allclose((np.degrees(th) - g + 180) % 360 - 180, 0, atol=1e-9)
        assert np.allclose(d, t.rb if r is None else r)
    # El contorno mide 2π rb: el arco de una vuelta es el del poste del mismo rb.
    assert t.perimetro == pytest.approx(4 * (6 - CANTO) + 4 * (1.5 - CANTO) + 2 * math.pi * (CANTO + 0.5))


def test_empujar_saca_lo_que_entro_tambien_por_la_punta():
    t = Tablon(TABLON)
    X = np.array([[-5.0, 1.0, t.zc + 1.0], [-5.0, -6.2, t.zc], [0.3, 0.0, t.zc],
                  [-5.0, 0.0, t.zc - 1.4], [5.0, 0.0, t.zc]])
    assert t.penetracion(X) > 0.5
    t.empujar(X, np.ones(len(X), bool))
    assert t.penetracion(X) == pytest.approx(0, abs=1e-9)
    assert X[0].tolist() == pytest.approx([-5.0, 1.0, t.zc + 2.0])   # a la cara de arriba
    assert X[2].tolist() == pytest.approx([0.5, 0.0, t.zc])          # a la punta
    assert X[4].tolist() == [5.0, 0.0, t.zc]                         # lo de afuera no se toca


def test_el_poste_sigue_siendo_el_poste():
    a = Anfitrion("poste", radio=1.5, desde=-14, hasta=14)
    assert type(sobre_superficie(a)) is Poste and type(solido(a)) is Poste
    assert type(sobre_superficie(TABLON)) is Tablon and type(solido(TABLON)) is Tablon


# --- El nudo de prueba --------------------------------------------------------
def test_construye_sin_fallas_y_la_cuerda_no_entra(modelo):
    assert modelo.fallas == []
    t = Tablon(modelo.spec.anfitrion)
    for r in modelo.pasos + [modelo.error, modelo.apretado]:
        assert r.medidas["penetracion_tablon"] <= PENETRACION_MAX
        assert t.penetracion(r.puntos) <= PENETRACION_MAX


def test_las_vueltas_sobre_un_tablon_ancho_rodean_sus_cantos():
    m = construir(desde_datos(datos_vueltas()))
    assert m.fallas == []
    r = m.pasos[0]
    # La cuerda pasa por los cantos casi vivos y se dobla apenas más que el mínimo.
    assert 0.9 <= r.medidas["curvatura_min"] < 1.0
    t = Tablon(m.spec.anfitrion)
    _, th, _ = t.cilindricas(r.puntos)
    arriba = np.abs(np.degrees(th)) < 5
    assert len(np.unique(np.round(r.puntos[arriba, 0] / 2.5))) == 3   # tres pasadas por arriba


def test_como_sobre_el_poste_no_hay_reverso_y_si_apretado(modelo):
    assert modelo.reverso is None and modelo.reverso_apretado is None
    assert modelo.apretado is not modelo.pasos[-1]
    assert modelo.apretado.secuencia == modelo.pasos[-1].secuencia


def test_por_detras_se_voltea_con_el_tablon(modelo):
    t = Tablon(modelo.spec.anfitrion)
    volteado, datos_t = t.voltear(modelo.apretado)
    assert volteado.secuencia == modelo.apretado.secuencia   # giro rígido
    assert datos_t["desde"] == 0.0 and datos_t["hasta"] == 30.0
    # Se apoya en lo más bajo, y lo que estaba abajo del tablón queda arriba.
    assert volteado.puntos[:, 2].min() == pytest.approx(0.5, abs=1e-6)
    assert volteado.puntos[:, 0].mean() == pytest.approx(-modelo.apretado.puntos[:, 0].mean())


def test_las_imagenes_llevan_el_tablon_y_por_detras_volteado(modelo):
    imgs = {i.nombre: i for i in imagenes(modelo)}
    e = datos_escena(modelo, None, modelo.pasos)
    assert e["anfitrion"]["tipo"] == "tablon" and e["anfitrion"]["desde"] == -30.0
    frente, detras = imgs["terminado-frente"], imgs["terminado-reverso"]
    assert frente.vista == detras.vista == VISTA_PASOS
    assert frente.escena["anfitrion"]["hasta"] == 0.0
    assert detras.escena["anfitrion"]["desde"] == 0.0 and detras.escena["anfitrion"]["hasta"] == 30.0


def test_la_ficha_dice_como_se_mira_por_detras():
    assert "tablón" in POR_DETRAS["tablon"] and "página" in POR_DETRAS["tablon"]


def test_la_hoja_dibuja_el_tablon_de_madera(modelo):
    d = datos_json(modelo)
    d["pasos"] = d["pasos"][:1]
    sin = np.asarray(hoja(d, "arriba"), float) / 255
    con = np.asarray(hoja(d, "arriba", solido(modelo.spec.anfitrion).datos()), float) / 255

    def madera(im):
        return int((np.abs(im - MADERA).max(axis=2) < 0.12).sum())
    assert madera(con) > 2000 > madera(sin)


def test_la_hoja_de_revision_muestra_la_cara_de_abajo(modelo, tmp_path):
    from nudos.revision import revision
    (tmp_path / "entradas" / modelo.spec.slug).mkdir(parents=True)
    pagina = revision(modelo, tmp_path / "revision", tmp_path / "entradas")
    assert "apretado-volteado-arriba.png" in pagina.read_text(encoding="utf-8")
    im = Image.open(pagina.parent / "apretado-volteado-arriba.png")
    assert im.width > 0
