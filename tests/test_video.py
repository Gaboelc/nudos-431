"""Los videos (T18): la velocidad del video, la interpolación por ángulo, la cámara, los títulos y
el video en el sitio. Sin Blender ni ffmpeg: lo que dibuja se prueba con los pilotos."""
import math

import numpy as np
import pytest

from nudos import exportar
from nudos.animar import RADIO_GUIA, _aflojar, radio_minimo
from nudos.fisica.varilla import Varilla
from nudos.exportar import SitioError, construir_sitio
from nudos.video import FORMATOS, Cuadro, _es_serie, alfas, retiempo, toma


def _sim(n, N=5):
    return [Cuadro(np.full((N, 3), float(k)), 2, "enhebrar", None, 2) for k in range(n)]


def test_a_velocidad_normal_el_video_es_la_simulacion():
    sim = _sim(61)
    out = retiempo(sim, np.ones(61), 60)
    assert len(out) == 61
    assert all(np.allclose(a.X, b.X) for a, b in zip(sim, out))


def test_al_triple_dura_un_tercio_e_interpola_dentro_de_la_simulacion():
    sim = _sim(61)
    out = retiempo(sim, np.full(61, 3.0), 60)
    assert len(out) == 21
    assert np.allclose(out[1].X, 3.0)
    lento = retiempo(sim, np.full(61, 0.5), 60)
    # A media velocidad, un cuadro del video cae entre dos de la simulación: la recta entre ellos.
    assert np.allclose(lento[1].X, 0.5)
    assert max(float(c.X.max()) for c in lento) <= 60.0


def test_donde_cambia_la_cantidad_de_nodos_no_interpola():
    sim = [Cuadro(np.zeros((5, 3)), 2, "enhebrar", None), Cuadro(np.ones((6, 3)), 2, "enhebrar", None)]
    out = retiempo(sim, np.array([0.5, 0.5]), 60)
    assert {len(c.X) for c in out} <= {5, 6}


def test_los_titulos_se_funden():
    cs = [Cuadro(np.zeros((2, 3)), 1, "pausa", None, 1) for _ in range(30)]
    cs += [Cuadro(np.zeros((2, 3)), 2, "enhebrar", None, 2) for _ in range(30)]
    alfas(cs, 60)
    assert cs[0].alfa == 1.0 and cs[45].alfa == 1.0
    assert cs[29].alfa < 1.0 and cs[30].alfa < 1.0


def test_la_cuerda_no_sigue_a_la_guia_en_una_cuspide():
    # Una guía con la cuerda doblada sobre sí misma, como la recta de A a B al formar un lazo.
    h = 0.1
    s = np.arange(-8, 8 + h / 2, h)
    G = np.column_stack([s, 0.6 * np.abs(s), np.full_like(s, 0.5)])
    assert radio_minimo(G) < 0.2
    k, curv = _aflojar(G, h, np.full(len(G), 5.0), Varilla.curvatura_de(G))
    medio = len(G) // 2
    assert k[medio] < 0.1 and k[0] == 5.0 and k[-1] == 5.0 and k[10] == 5.0
    assert np.linalg.norm(curv, axis=1).max() <= 2 * math.tan(h / (2 * RADIO_GUIA)) + 1e-12


def test_la_toma_deja_el_nudo_en_el_area_util():
    pts = np.array([[x, y, 0.0] for x in (-5, 5) for y in (-3, 3)] + [[0, 0, 2.0]])
    for nombre, F in FORMATOS.items():
        asp = F["tam"][0] / F["tam"][1]
        c = toma(pts, 0.68, -0.32, asp, F["area"])
        from nudos.video import _mirar
        M = _mirar(np.asarray(c["pos"]), np.asarray(c["target"]))
        R, pos = M[:3, :3], M[:3, 3]
        th = math.tan(math.radians(c["fov"]) / 2)
        q = (pts - pos) @ R
        x = (q[:, 0] / (-q[:, 2] * th * asp) + 1) / 2
        y = (1 - q[:, 1] / (-q[:, 2] * th)) / 2
        x0, y0, x1, y1 = F["area"]
        assert x.min() >= x0 - 0.01 and x.max() <= x1 + 0.01, nombre
        assert y.min() >= y0 - 0.01 and y.max() <= y1 + 0.01, nombre


def test_las_series_van_mas_rapido(modelos):
    spec = modelos["amarre-cuadrado"].spec
    series = [p.n for p in spec.pasos if _es_serie(spec, p.n)]
    assert [spec.pasos[n - 1].hasta for n in series] == ["vueltas", "ahorcados"]
    assert not _es_serie(modelos["as-de-guia"].spec, 3)


def test_el_sitio_lleva_el_video_del_nudo(tmp_path, monkeypatch, modelo_as_de_guia):
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "as-de-guia.mp4").write_bytes(b"\x00" * 1000)
    monkeypatch.setattr(exportar, "VIDEOS", videos)
    destino = tmp_path / "s"
    construir_sitio(destino, modelos=[modelo_as_de_guia], publicados=["as-de-guia"])
    assert (destino / "as-de-guia" / "video.mp4").read_bytes() == b"\x00" * 1000
    pagina = (destino / "as-de-guia" / "index.html").read_text(encoding="utf-8")
    assert 'src="video.mp4"' in pagina and 'preload="none"' in pagina and "autoplay" not in pagina


def test_sin_video_la_pagina_no_cambia(tmp_path, monkeypatch, modelo_as_de_guia):
    monkeypatch.setattr(exportar, "VIDEOS", tmp_path / "no-hay")
    destino = tmp_path / "s"
    construir_sitio(destino, modelos=[modelo_as_de_guia], publicados=["as-de-guia"])
    pagina = (destino / "as-de-guia" / "index.html").read_text(encoding="utf-8")
    assert "verVideo" not in pagina
    assert not (destino / "as-de-guia" / "video.mp4").exists()


def test_un_video_de_mas_no_se_publica(tmp_path, monkeypatch, modelo_as_de_guia):
    videos = tmp_path / "videos"
    videos.mkdir()
    with (videos / "as-de-guia.mp4").open("wb") as f:
        f.seek(int(exportar.TOPE_VIDEO_MB * 1e6) + 10)
        f.write(b"\x00")
    monkeypatch.setattr(exportar, "VIDEOS", videos)
    with pytest.raises(SitioError, match="pesa"):
        construir_sitio(tmp_path / "s", modelos=[modelo_as_de_guia], publicados=["as-de-guia"])


def test_un_salto_se_reparte_en_los_subpasos_del_motor():
    from nudos.fisica.atar import SALTO, repartir_saltos, saltos
    X = [np.zeros((3, 3)), np.zeros((3, 3)), np.full((3, 3), 0.6), np.full((3, 3), 0.7)]
    medio = {2: [np.full((3, 3), 0.2), np.full((3, 3), 0.4)], 3: [np.full((3, 3), 0.65)]}
    Y, p, q, m, nuevo = repartir_saltos(X, {}, {}, medio)
    assert len(Y) == 6 and max(saltos(Y)) <= SALTO
    assert nuevo == {0: 0, 1: 1, 2: 4, 3: 5}
    # El cuadro que no se repartió conserva sus subpasos para `comprobar`.
    assert list(m) == [5]


def test_los_saltos_se_miden_tambien_al_quitar_un_nodo():
    from nudos.fisica.atar import saltos
    a = np.array([[0.0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]])
    # Se quita el penúltimo y la punta queda donde estaba: nada saltó.
    b = np.array([[0.0, 0, 0], [1, 0, 0], [3, 0, 0]])
    assert saltos([a, b], quitado={1: 1}) == [0.0]
    # Sin decir cómo cambió, el cuadro no se mide.
    assert saltos([a, b]) == []
    # La punta que se va lejos sí cuenta.
    c = np.array([[0.0, 0, 0], [1, 0, 0], [5, 0, 0]])
    assert saltos([a, c], quitado={1: 1}) == [2.0]


def test_la_punta_se_dibuja_sin_codo():
    from nudos.video import punta_suave
    h = 0.2
    s = np.arange(40) * h
    recta = np.column_stack([s, np.zeros_like(s), np.full_like(s, 0.5)])
    assert np.array_equal(punta_suave(recta, h), recta)
    codo = recta.copy()
    codo[-1] = codo[-2] + [0.0, h, 0.0]         # el último tramo, a 90°
    suave = punta_suave(codo, h)
    assert np.allclose(suave[-1], codo[-1]) and np.allclose(suave[:-9], codo[:-9])
    d = np.diff(suave[-10:], axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    giro = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", d[:-1], d[1:]), -1, 1)))
    assert giro.max() < 25


def test_la_malla_del_video_cierra_las_puntas():
    from nudos import blender
    s = np.arange(30) * 0.2
    P = np.column_stack([s, np.zeros_like(s), np.full_like(s, 0.5)])
    e = {"cuerdas": [{"espina": P.ravel().tolist(), "radio": 0.5, "grosor": 1.0, "color": "azul",
                      "tramos": [[0, 25, 0], [25, 29, 2]]}], "mallas": []}
    abierta = blender.malla_cuerda(0, e, aplastar=False)
    cerrada = blender.malla_cuerda(0, e, aplastar=False, tapas=True)
    assert abierta.vertices[:, 0].max() == pytest.approx(P[-1, 0])
    assert cerrada.vertices[:, 0].max() > P[-1, 0] + 0.1 and cerrada.vertices[:, 0].min() < -0.1
    assert cerrada.caras.max() < len(cerrada.vertices)
    # La tapa de la punta lleva el remate; la del comienzo, el material de su tramo.
    extra = cerrada.material[len(abierta.material):]
    assert set(extra[:len(extra) // 2]) == {0} and set(extra[len(extra) // 2:]) == {2}


def test_se_reparte_tambien_el_cuadro_en_que_la_mano_da_cuerda():
    from nudos.fisica.atar import SALTO, repartir_saltos, saltos
    a = np.array([[0.0, 0, 3.0], [1, 0, 3.0], [2, 0, 3.0]])
    # La mano dio un nodo (el último tramo partido a la mitad) y la punta avanzó 0,6 d.
    b = np.array([[0.0, 0, 3.0], [1, 0, 3.0], [1.5, 0, 3.0], [2.6, 0, 3.0]])
    medio = {1: [np.array([[0.0, 0, 3.0], [1, 0, 3.0], [1.5, 0, 3.0], [2.3, 0, 3.0]])]}
    assert saltos([a, b], partido={1: [0.5]}) == [pytest.approx(0.6)]
    Y, p, q, m, nuevo = repartir_saltos([a, b], {1: [0.5]}, {}, medio)
    assert max(saltos(Y, p, q)) <= SALTO
    # El cambio de nodos queda en el primer cuadro nuevo, y el cuadro viejo es el último.
    assert list(p) == [1] and nuevo[1] == len(Y) - 1
