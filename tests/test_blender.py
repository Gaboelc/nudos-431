"""Las imágenes de impresión con Blender (T16) y la sección aplastada (T15g)."""
import numpy as np
import pytest
from PIL import Image

from nudos import blender
from nudos.imprimir import CELDA_MM, ImpresionError, dibujar, imagenes, px, render_activo
from nudos.referencia import RUIDO_NIVELES, comparar, es_ruido


def _recta(desde, hasta, paso=0.08):
    desde, hasta = np.asarray(desde, float), np.asarray(hasta, float)
    n = int(np.ceil(np.linalg.norm(hasta - desde) / paso))
    return list((desde + np.linspace(0, 1, n + 1)[:, None] * (hasta - desde)).ravel())


def _cuerda(espina, tramos=None):
    T = len(espina) // 3 - 1
    return {"color": "azul", "grosor": 1, "radio": 0.5, "L": 0, "espina": espina,
            "tramos": tramos or [[0, T, 0]]}


def _plano(z, rol="madera"):
    """Una tabla horizontal a la altura z, con la normal hacia arriba."""
    pos = [-5, -5, z, 5, -5, z, 5, 5, z, -5, 5, z]
    return {"rol": rol, "color": "#c8a27a", "rugosidad": 0.6, "metal": 0, "pos": pos,
            "nor": [0, 0, 1] * 4, "idx": [0, 1, 2, 0, 2, 3]}


def _area(m: blender.MallaCuerda, anillo: int) -> float:
    V = m.vertices[anillo * blender.LADOS:(anillo + 1) * blender.LADOS]
    c = V.mean(axis=0)
    a = V - c
    return 0.5 * float(np.linalg.norm(np.cross(a, np.roll(a, -1, axis=0)).sum(axis=0)))


def test_una_cuerda_sola_es_redonda():
    escena = {"cuerdas": [_cuerda(_recta([-3, 0, 0.5], [3, 0, 0.5]))], "mallas": []}
    m = blender.malla_cuerda(0, escena)
    n = len(escena["cuerdas"][0]["espina"]) // 3
    assert m.vertices.shape == (n * blender.LADOS, 3)
    assert m.caras.shape == ((n - 1) * blender.LADOS, 4)
    assert m.aplastado.max() == 0
    r = np.linalg.norm(m.vertices[:blender.LADOS] - [-3, 0, 0.5], axis=1)
    assert np.allclose(r, 0.5)


def test_dos_cuerdas_que_se_aprietan_se_aplastan_sin_atravesarse():
    # Dos cuerdas cruzadas con los ejes a 0,9 diámetros: cada sección se aplana hasta 0,45.
    a = _cuerda(_recta([-3, 0, 0.5], [3, 0, 0.5]))
    b = _cuerda(_recta([0, -3, 1.4], [0, 3, 1.4]))
    escena = {"cuerdas": [a, b], "mallas": []}
    ma, mb = blender.malla_cuerda(0, escena), blender.malla_cuerda(1, escena)
    # Los ejes están muestreados cada 0,08 diámetros: el anillo más cercano al cruce queda a
    # menos de 0,04 de él.
    assert ma.aplastado.max() == pytest.approx(0.1, abs=0.01)
    # Justo en el cruce, las dos caras planas se tocan a 0,95.
    assert ma.vertices[np.abs(ma.vertices[:, 0]) < 0.05, 2].max() <= 0.95 + 0.002
    assert mb.vertices[np.abs(mb.vertices[:, 1]) < 0.05, 2].min() >= 0.95 - 0.002
    # Lejos del cruce sigue redonda, y donde se aplasta conserva el área (hasta ENSANCHE_MAX).
    assert ma.aplastado[0] == 0
    medio = int(np.argmax(ma.aplastado))
    assert _area(ma, medio) == pytest.approx(_area(ma, 0), rel=0.01)
    # Sin aplastar, el tubo redondo de siempre.
    assert blender.malla_cuerda(0, escena, aplastar=False).aplastado.max() == 0


def test_una_cuerda_se_aplasta_contra_la_madera_y_no_contra_la_mesa():
    espina = _recta([-3, 0, 0.45], [3, 0, 0.45])
    escena = {"cuerdas": [_cuerda(espina)], "mallas": [_plano(0.0)]}
    m = blender.malla_cuerda(0, escena)
    assert m.aplastado.max() == pytest.approx(0.1, abs=1e-6)
    assert m.vertices[:, 2].min() >= -1e-6
    # La mesa no es un sólido de la escena (en Blender es un receptor de sombras), y las tapas
    # de las puntas tampoco.
    escena["mallas"] = [_plano(0.0, rol="punta")]
    assert blender.malla_cuerda(0, escena).aplastado.max() == 0


def test_la_cuerda_no_se_aplasta_contra_si_misma_a_lo_largo():
    # Una curva cerrada (radio 0,8): los puntos vecinos a lo largo están a menos de un diámetro,
    # pero no se tocan.
    t = np.linspace(0, np.pi, 40)
    espina = list(np.c_[0.8 * np.cos(t), 0.8 * np.sin(t), np.full_like(t, 0.5)].ravel())
    m = blender.malla_cuerda(0, {"cuerdas": [_cuerda(espina)], "mallas": []})
    assert m.aplastado.max() == 0


def test_los_tramos_dan_el_material_de_cada_cara():
    espina = _recta([0, 0, 0.5], [4, 0, 0.5], paso=0.5)   # 8 tramos
    m = blender.malla_cuerda(0, {"cuerdas": [_cuerda(espina, [[0, 2, 0], [2, 5, 1], [5, 8, 2]])],
                                 "mallas": []})
    por_tramo = m.material.reshape(-1, blender.LADOS)[:, 0]
    assert list(por_tramo) == [0, 0, 1, 1, 1, 2, 2, 2]
    # La trenza avanza un mosaico cada π diámetros.
    assert m.uv[-1, 1, 0] == pytest.approx(4 / np.pi)


def test_render_activo(monkeypatch):
    monkeypatch.setenv("NUDOS_RENDER", "")
    assert render_activo() == "blender"
    monkeypatch.setenv("NUDOS_RENDER", "threejs")
    assert render_activo() == "threejs"
    monkeypatch.setenv("NUDOS_RENDER", "otro")
    with pytest.raises(ImpresionError):
        render_activo()


def test_el_ruido_de_cycles():
    dif = np.zeros((100, 100), dtype=np.int16)
    assert es_ruido(dif)
    dif[0, :40] = 1
    assert es_ruido(dif)
    dif[1, :20] = 1     # 60 píxeles de 10 000: más que RUIDO_PIXELES
    assert not es_ruido(dif)
    dif[:] = 0
    dif[0, 0] = RUIDO_NIVELES + 1
    assert not es_ruido(dif)


def test_comparar_tolera_el_ruido_solo_entre_carpetas_de_blender(tmp_path):
    for lado, valor in (("antes", 200), ("despues", 201)):
        d = tmp_path / lado / "simple"
        (d / "impresion").mkdir(parents=True)
        (d / "modelo.json").write_text("{}", encoding="utf-8")
        im = Image.new("RGB", (100, 100), (200, 200, 200))
        im.putpixel((0, 0), (valor, 200, 200))
        im.save(d / "impresion" / "paso-1.png")
    lineas = []
    assert comparar(tmp_path / "antes", tmp_path / "despues", avisar=lineas.append) == 1
    for lado in ("antes", "despues"):
        (tmp_path / lado / "render.txt").write_text("blender\n", encoding="utf-8")
    assert comparar(tmp_path / "antes", tmp_path / "despues", avisar=lineas.append) == 0
    (tmp_path / "antes" / "render.txt").write_text("threejs\n", encoding="utf-8")
    lineas.clear()
    assert comparar(tmp_path / "antes", tmp_path / "despues", avisar=lineas.append) == 1
    assert any("se dibujó con threejs" in linea for linea in lineas)


@pytest.fixture(scope="module")
def con_blender(con_chrome):
    try:
        blender.ejecutable()
    except blender.BlenderError as e:
        pytest.skip(str(e))


def test_blender_dibuja_y_repite(con_blender, modelos, tmp_path):
    """Dos veces la misma imagen con Blender: del tamaño de la ficha, con la cuerda y los nombres,
    y la segunda igual a la primera o con solo ruido de Cycles."""
    m = modelos["ballestrinque"]
    img = next(i for i in imagenes(m) if i.nombre == "paso-3")
    a = dibujar([img], tmp_path / "a", render="blender")[0]
    b = dibujar([img], tmp_path / "b", render="blender")[0]
    x = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
    y = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
    assert x.shape == (px(CELDA_MM[1]), px(CELDA_MM[0]), 3)
    assert es_ruido(np.abs(x - y).max(axis=2))
    # La cuerda azul se ve, y el fondo es blanco.
    azul = (x[..., 2] > x[..., 0] + 60)
    assert azul.mean() > 0.02
    assert (x[0, -1] >= 245).all()
