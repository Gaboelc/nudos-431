"""El barril: un cilindro parado, con los bordes redondeados, para la eslinga de barril
(formato v1.13).

El nudo de prueba no es del libro: el firme llega por delante y pasa por debajo del barril,
sube por el costado y cruza la tapa por detrás. En el paso 2 baja por la derecha, rodea el
frente y cruza la tapa en diagonal sobre la primera pasada (un cruce en la tapa). En el paso 3
baja por detrás y rodea el costado sobre la subida (un cruce en el costado)."""

import numpy as np
import pytest
from PIL import Image

from nudos.anfitrion import BORDE, COSTADO, MESA, PENETRACION_MAX, TAPA, Barril, _curva, solido, sobre_superficie
from nudos.construir import construir, datos_json
from nudos.exportar import datos_escena
from nudos.ficha import POR_DETRAS
from nudos.hoja import MADERA, hoja, mapa
from nudos.imprimir import imagenes
from nudos.spec import BASE_BARRIL, CANTO_BARRIL, Anfitrion, SpecError, desde_datos

BARRIL = {"tipo": "barril", "radio": 6, "alto": 10}


def datos(**cambios):
    d = {
        "slug": "eslinga-de-barril", "nombre": "Prueba", "familia": "De sujeción",
        "anfitrion": dict(BARRIL),
        "encuadre": {"x": [-11.0, 11.0], "y": [-12.0, 9.0]},
        "segmentos": {
            "firme": [[-9, -18], [-7.5, -12], [-5.5, -6], [-3.0, 1.5]],
            "sube": {"barril": [[240, 3], [240, 7], [240, 10]]},
            "tapa-1": {"tapa": [[-4.33, 2.5], [0.0, 3.0], [4.33, 2.5]]},
            "rodea": {"barril": [[120, 10], [100, 7.5], [30, 7], [-40, 8], [-60, 10]]},
            "tapa-2": {"tapa": [[-4.33, -2.5], [-1.0, 0.8], [2.5, 4.33]]},
            "abajo": {"barril": [[150, 10], [165, 6], [200, 4], [240, 3.6], [280, 4]]},
        },
        "pasos": [
            {"titulo": "Sube y cruza", "texto": "Prueba.",
             "trazado": ["firme", "sube", "tapa-1"], "secuencia": ""},
            {"titulo": "Cruza la tapa", "texto": "Prueba.",
             "trazado": ["firme", "sube", "tapa-1", "rodea", "tapa-2"], "secuencia": "1U 1O"},
            {"titulo": "Rodea el costado", "texto": "Prueba.",
             "trazado": ["firme", "sube", "tapa-1", "rodea", "tapa-2", "abajo"],
             "secuencia": "2U 1U 1O 2O"},
        ],
    }
    d.update(cambios)
    return d


@pytest.fixture(scope="module")
def modelo():
    return construir(desde_datos(datos()))


def barril():
    return Barril(Anfitrion("barril", radio=6.0, alto=10.0))


# --- La especificación ------------------------------------------------------
def test_se_carga_con_su_radio_y_su_alto():
    s = desde_datos(datos())
    assert s.anfitrion == Anfitrion("barril", radio=6.0, alto=10.0)
    assert not s.anfitrion.en_la_mesa
    p = s.pasos[0]
    # firme (4) sobre la mesa, sube (3) por el costado, tapa-1 (3) por la tapa
    assert p.sobre.tolist() == [False] * 4 + [True] * 6
    assert p.tapa.tolist() == [False] * 7 + [True] * 3


@pytest.mark.parametrize("anfitrion, mensaje", [
    ({"tipo": "barril", "radio": 6}, "alto"),
    ({"tipo": "barril", "radio": 2, "alto": 10}, "radio del barril va de 3 a 12"),
    ({"tipo": "barril", "radio": 6, "alto": 3}, "alto.*de al menos 4"),
    ({"tipo": "barril", "radio": 6, "alto": 10, "largo": 3}, "desconocidos"),
])
def test_medidas_que_no_valen(anfitrion, mensaje):
    with pytest.raises(SpecError, match=mensaje):
        desde_datos(datos(anfitrion=anfitrion))


def test_los_segmentos_sobre_el_barril_van_por_el_costado_o_por_la_tapa():
    d = datos()
    d["segmentos"]["sube"] = {"poste": d["segmentos"]["sube"]["barril"]}
    with pytest.raises(SpecError, match=r"\{barril: \[\[ángulo, altura\].*\{tapa: \[\[x, y\]"):
        desde_datos(d)
    d = datos()
    d["segmentos"]["sube"]["barril"][-1] = [240, 10.8]
    with pytest.raises(SpecError, match="fuera del costado.*de 1.6 a 10.4"):
        desde_datos(d)
    d = datos()
    d["segmentos"]["tapa-1"]["tapa"][0] = [-5.8, 0.5]
    with pytest.raises(SpecError, match="fuera de la parte plana de la tapa"):
        desde_datos(d)


def test_de_la_tapa_a_la_mesa_se_baja_por_el_costado():
    d = datos()
    d["segmentos"]["sale"] = [[8, 3], [12, 3]]
    d["pasos"][0]["trazado"] = ["firme", "sube", "tapa-1", "sale"]
    with pytest.raises(SpecError, match="baja por el costado del barril"):
        desde_datos(d)


# --- El sólido --------------------------------------------------------------
def test_se_apoya_en_la_cuerda_y_su_costado_es_como_el_del_destorcedor():
    b = barril()
    assert b.rb == pytest.approx(6.5) and b.ztapa == pytest.approx(BASE_BARRIL + 10 + 0.5)
    assert b.zb == pytest.approx(BASE_BARRIL + CANTO_BARRIL)
    # 0 hacia quien ata, 90 a la derecha
    assert np.allclose(b.costado([0.0, 90.0], [3.0, 5.0]), [[0, -6.5, 3], [6.5, 0, 5]], atol=1e-12)


def test_empujar_saca_por_el_costado_la_tapa_la_base_y_el_borde():
    b = barril()
    X = np.array([[0.0, -5.0, 6.0],     # dentro, cerca del costado de delante
                  [1.0, 1.0, 10.8],     # dentro, cerca de la tapa
                  [0.0, 0.0, 0.5],      # bajo la base, justo tocándola
                  [5.9, 0.0, 10.9],     # en el borde de la tapa
                  [0.0, 0.0, 15.0]])    # lejos, arriba
    assert b.penetracion(X) > 1
    b.empujar(X, np.ones(len(X), bool))
    assert b.penetracion(X) == pytest.approx(0, abs=1e-9)
    assert X[0].tolist() == pytest.approx([0.0, -6.5, 6.0])
    assert X[1].tolist() == pytest.approx([1.0, 1.0, 11.5])
    assert X[2].tolist() == pytest.approx([0.0, 0.0, 0.5])
    assert np.hypot(X[3, 0] - b.rc, X[3, 2] - b.zt) == pytest.approx(b.e0)
    assert X[4].tolist() == [0.0, 0.0, 15.0]


def test_la_distancia_al_eje_mide_desde_la_superficie():
    b = barril()
    _, th, r = b.cilindricas(np.array([[9.5, 0.0, 6.0], [0.0, 0.0, 14.5], [0.0, -6.5, 6.0]]))
    assert r.tolist() == pytest.approx([9.5, 6.5 + 3, 6.5])
    assert np.degrees(th[0]) == pytest.approx(90) and np.degrees(th[2]) == pytest.approx(0, abs=1e-9)


def test_la_curva_rodea_los_bordes_en_el_angulo_del_costado():
    s = desde_datos(datos())
    b = sobre_superficie(s.anfitrion)
    assert type(b) is Barril and type(solido(s.anfitrion)) is Barril
    X, h, ctrl_s, zona = _curva(s.pasos[0], b)
    assert set(zona.tolist()) == {MESA, COSTADO, TAPA, BORDE}
    assert b.penetracion(X) < 0.05
    # Lo que rodea el borde de la base, sale debajo del barril en el ángulo de la subida (240°).
    borde = X[zona == BORDE]
    abajo = borde[borde[:, 2] < 5]
    angulos = np.degrees(np.arctan2(abajo[:, 0], -abajo[:, 1])) % 360
    assert np.allclose(angulos, 240, atol=1.0)
    assert len(ctrl_s) == len(s.pasos[0].puntos)


# --- El nudo de prueba --------------------------------------------------------
def test_construye_sin_fallas_y_la_cuerda_no_entra(modelo):
    assert modelo.fallas == []
    b = Barril(modelo.spec.anfitrion)
    for r in modelo.pasos + [modelo.apretado]:
        assert r.medidas["penetracion_barril"] <= PENETRACION_MAX
        assert b.penetracion(r.puntos) <= PENETRACION_MAX


def test_los_cruces_se_buscan_en_la_tapa_y_en_el_costado(modelo):
    p2, p3 = modelo.pasos[1], modelo.pasos[2]
    assert p2.secuencia == ["1U", "1O"]
    x, y = p2.cruces["1"]
    assert np.hypot(x, y) < 5        # sobre la tapa
    assert len(p3.cruces) == 2
    lejos = sorted(np.hypot(*xy) for xy in p3.cruces.values())
    assert lejos[0] < 5 and lejos[1] == pytest.approx(6.5, abs=1.2)   # uno en la tapa, otro en el costado
    # El tramo de encima en la tapa queda más alto: la pasada de abajo va pegada a ella.
    assert p2.medidas["altura_max"] > Barril(modelo.spec.anfitrion).ztapa + 0.5


def test_como_sobre_el_poste_no_hay_reverso_y_se_mira_desde_el_otro_lado(modelo):
    assert modelo.reverso is None and modelo.apretado is not None
    imgs = {i.nombre: i for i in imagenes(modelo)}
    assert imgs["terminado-reverso"].vista == "detras"
    assert imgs["terminado-frente"].escena["anfitrion"]["tipo"] == "barril"
    e = datos_escena(modelo, None, modelo.pasos)
    assert e["anfitrion"] == {"tipo": "barril", "radio": 6.0, "alto": 10.0, "canto": CANTO_BARRIL,
                              "base": BASE_BARRIL}


def test_la_ficha_dice_como_se_mira_por_detras():
    assert "barril" in POR_DETRAS["barril"]


def test_la_hoja_lo_dibuja_de_madera_y_desenrolla_su_costado(modelo):
    d = datos_json(modelo)
    d1 = {**d, "pasos": d["pasos"][:1]}
    sin = np.asarray(hoja(d1, "arriba"), float) / 255
    con = np.asarray(hoja(d1, "arriba", solido(modelo.spec.anfitrion).datos()), float) / 255

    def madera(im):
        return int((np.abs(im - MADERA).max(axis=2) < 0.12).sum())
    assert madera(con) > madera(sin) + 1000
    im = mapa(d, Barril(modelo.spec.anfitrion))
    assert im.width > 0 and im.height > 0


def test_la_hoja_de_revision_muestra_el_costado(modelo, tmp_path):
    from nudos.revision import revision
    (tmp_path / "entradas" / modelo.spec.slug).mkdir(parents=True)
    pagina = revision(modelo, tmp_path / "revision", tmp_path / "entradas")
    assert "costado.png" in pagina.read_text(encoding="utf-8")
    assert Image.open(pagina.parent / "costado.png").width > 0
