"""El aspecto del video (T20): la trenza con geometría, sus texturas, la escena de Blender y el
costo de la prueba del cuadro final."""
import json
import math

import numpy as np
import pytest
from PIL import Image

from nudos import aspecto, blender, trenza
from nudos.recursos import RecursoError, recurso


def _cuerda(n=101, largo=20.0):
    x = np.linspace(-largo / 2, largo / 2, n)
    return np.c_[x, 2 * np.sin(x / 3), np.full(n, 0.5)]


# --- La trenza --------------------------------------------------------------

def test_cada_punto_es_de_un_hilo_y_la_mitad_son_a():
    u, v = np.meshgrid(np.linspace(0, 1, 200, endpoint=False), np.linspace(0, 1, 200, endpoint=False))
    es_a, hilo, ancho, largo, alto, _ = trenza.celdas(u, v)
    assert abs(es_a.mean() - 0.5) < 0.01
    assert hilo.min() == 0 and hilo.max() == trenza.HILOS - 1
    assert 0 <= ancho.min() and ancho.max() <= 1 and 0 <= largo.min() and largo.max() <= 1
    assert 0 <= alto.min() and alto.max() <= 1


def test_cada_hilo_pasa_por_encima_de_dos_y_por_debajo_de_dos():
    # A lo largo de un hilo A (v + u constante), lo que se ve cambia de A a B cada dos celdas.
    t = (np.arange(64) + 0.5) / 64
    es_a, *_ = trenza.celdas(t, 0.03 - t)
    cambios = np.flatnonzero(np.diff(es_a.astype(int)))
    assert len(cambios) >= 4
    assert np.allclose(np.diff(cambios), np.diff(cambios)[0], atol=1)


def test_la_trenza_se_repite_cada_mosaico():
    u, v = np.random.default_rng(1).random((2, 500))
    assert np.allclose(trenza.relieve(u, v), trenza.relieve(u + 1, v))
    assert np.allclose(trenza.relieve(u, v), trenza.relieve(u, v + 1))


def test_las_texturas_y_el_trazador_amarillo_de_la_cuerda_real():
    color, finos, hilos = trenza.texturas(trenza.ESTILOS["real"], 256)
    assert color.shape == (256, 256, 3) and finos.shape == hilos.shape == (256, 256)
    assert color.dtype == np.float32 and 0 <= color.min() and color.max() <= 1
    assert set(np.unique(hilos)) == {0.0, 1.0}
    amarillo = (color[..., 0] > 0.6) & (color[..., 1] > 0.55) & (color[..., 2] < 0.45)
    # Dos de los 16 hilos son amarillos: algo menos de un octavo de la superficie (sin los surcos).
    assert 0.05 < amarillo.mean() < 0.125
    azul, _, _ = trenza.texturas(trenza.ESTILOS["azul"], 256)
    assert azul[..., 2].mean() > azul[..., 0].mean()


def test_la_direccion_de_los_hilos():
    T = np.array([[1.0, 0, 0]])
    al = np.array([[0, 1.0, 0]])
    for mosaico in (1.0, 2.0):
        a, b = trenza.direcciones_hilos(T, al, mosaico)
        ang = math.degrees(math.atan(1 / mosaico))
        assert math.degrees(math.acos(a[0] @ T[0])) == pytest.approx(ang)
        assert math.degrees(math.acos(b[0] @ T[0])) == pytest.approx(ang)
        assert a[0, 1] < 0 < b[0, 1]


# --- La malla con la trenza en la geometría ---------------------------------

def test_la_curva_densa_pasa_por_los_nodos():
    X = _cuerda(21)
    for sub in (1, 3, 5):
        P = blender.curva_densa(X, sub)
        assert len(P) == (len(X) - 1) * sub + 1
        assert np.allclose(P[::sub], X)


def test_la_malla_de_la_trenza():
    X = _cuerda()
    n, sub, lados = len(X), 5, 96
    m = blender.malla_trenza(X, tramos=[[0, 96, 0], [96, 100, 2]], sub=sub, lados=lados)
    nd = (n - 1) * sub + 1
    anillos, _ = blender.TAPA_TRENZA
    assert m.vertices.shape == (nd * lados + 2 * anillos * lados, 3)
    assert m.caras.shape == ((nd - 1) * lados + 2 * anillos * lados, 4)
    assert len(m.uv) == len(m.caras) == len(m.material)
    assert m.fibra_a.shape == m.fibra_b.shape == m.vertices.shape
    assert np.allclose(np.linalg.norm(m.fibra_a, axis=1), 1, atol=1e-6)
    P = blender.curva_densa(X, sub)
    r = np.linalg.norm(m.vertices[:nd * lados].reshape(nd, lados, 3) - P[:, None, :], axis=2)
    trenzado = r[: 90 * sub]
    # El radio medio es el de la cuerda, y el relieve de los hilos va de un surco a lo alto.
    assert trenzado.mean() == pytest.approx(0.5, abs=0.01)
    assert trenzado.max() - trenzado.min() == pytest.approx(blender.TRENZA_RELIEVE, abs=0.01)
    # La cinta del chicote, lisa y un poco más gruesa.
    cinta = r[-3 * sub:]
    assert np.allclose(cinta, 0.5 + blender.CINTA_GROSOR, atol=1e-6)
    assert set(np.unique(m.material[-lados * anillos:])) == {2}


def test_la_misma_cantidad_de_nodos_da_la_misma_malla_vertice_a_vertice():
    X = _cuerda()
    Y = X + np.array([0.3, -0.2, 0.0]) + 0.05 * np.sin(np.arange(len(X)))[:, None]
    a, b = blender.malla_trenza(X), blender.malla_trenza(Y)
    assert a.vertices.shape == b.vertices.shape
    assert np.array_equal(a.caras, b.caras)


def test_la_trenza_sigue_la_coordenada_de_la_cuerda():
    # Con la coordenada de material (T21b), la trenza va con la cuerda. El relieve se repite cada
    # π/8 d a lo largo (lo que avanza la trenza de un cruce de hilos al siguiente).
    X = _cuerda()
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))])
    a = blender.malla_trenza(X, s=s, tapas=False)
    b = blender.malla_trenza(X, s=s + np.pi / 8, tapas=False)
    assert np.allclose(a.vertices, b.vertices, atol=1e-9)
    c = blender.malla_trenza(X, s=s + np.pi / 16, tapas=False)
    assert not np.allclose(a.vertices, c.vertices, atol=1e-3)


def test_la_trenza_se_aplasta_contra_otra_cuerda():
    a = np.c_[np.linspace(-3, 3, 31), np.zeros(31), np.full(31, 0.5)]
    b = np.c_[np.zeros(31), np.linspace(-3, 3, 31), np.full(31, 1.4)]
    sb = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(b, axis=0), axis=1))])
    m = blender.malla_trenza(a, otras=[(b, sb, 0.5, False)], relieve=0.0, tapas=False)
    assert m.aplastado.max() == pytest.approx(0.1, abs=0.02)
    assert m.vertices[np.abs(m.vertices[:, 0]) < 0.05, 2].max() <= 0.95 + 0.01


# --- La prueba del cuadro final -----------------------------------------------

def test_la_vineta_oscurece_las_esquinas_y_el_grano_cambia_con_la_semilla():
    im = Image.new("RGB", (384, 216), (128, 128, 128))
    a = np.asarray(aspecto.vineta_y_grano(im, 1), float)
    b = np.asarray(aspecto.vineta_y_grano(im, 1), float)
    c = np.asarray(aspecto.vineta_y_grano(im, 2), float)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    centro, esquina = a[98:118, 182:202].mean(), a[:10, :10].mean()
    assert esquina < centro * (1 - aspecto.VINETA * 0.7)
    assert abs(centro - 128) < 3


def test_el_fondo_del_campamento_solo_baja_con_la_camara_baja():
    alta = {"pos": [0, -40, 50], "target": [0, 0, 0.5], "fov": 30.0}
    baja = {"pos": [0, -50, 18], "target": [0, 0, 0.5], "fov": 30.0}
    assert aspecto.inclinacion_fondo(alta) == 0.0
    assert 5 < aspecto.inclinacion_fondo(baja) < 30


def test_la_proyeccion_del_costo():
    r = aspecto.Resultado("1", "CYCLES", [
        {"toma": "paso4", "tipo": "seguido", "s": 4.0}, {"toma": "amarre", "tipo": "seguido", "s": 4.0},
        {"toma": "paso4", "tipo": "vertical", "s": 1.0}, {"toma": "trenza", "tipo": "seguido", "s": 9.0}])
    assert r.cuadro_4k == 4.0 and r.cuadro_vertical == 1.0
    assert r.dias == pytest.approx(36 * (7200 * 4 + 3000 * 1) / 86400)


def test_el_centro_de_la_camara_cae_en_el_centro_del_cuadro():
    c = {"pos": [3, -40, 30], "target": [1, 2, 0.5], "fov": 30.0, "aspecto": 16 / 9}
    x, y = aspecto._proyectar(c, c["target"], (3840, 2160))
    assert x == pytest.approx(1920) and y == pytest.approx(1080)


def test_un_recurso_que_falta_o_no_es_el_del_registro(tmp_path, monkeypatch):
    monkeypatch.setenv("NUDOS_RECURSOS", str(tmp_path))
    with pytest.raises(RecursoError, match="bájalo"):
        recurso("hdri/meadow_4k.hdr")
    (tmp_path / "hdri").mkdir()
    (tmp_path / "hdri" / "meadow_4k.hdr").write_bytes(b"no es un hdri")
    with pytest.raises(RecursoError, match="no mide"):
        recurso("hdri/meadow_4k.hdr")
    with pytest.raises(RecursoError, match="no está"):
        recurso("hdri/otro.hdr")


# --- Blender ------------------------------------------------------------------

@pytest.fixture(scope="module")
def con_blender():
    try:
        blender.ejecutable()
    except blender.BlenderError as e:
        pytest.skip(str(e))


@pytest.mark.parametrize("motor", ["CYCLES", "BLENDER_EEVEE"])
def test_blender_dibuja_el_estudio_y_mide_el_tiempo(con_blender, tmp_path, motor):
    X = _cuerda(61, 12.0)
    h = float(np.linalg.norm(X[1] - X[0]))
    camara = {"pos": [0.0, -20.0, 16.0], "target": [0.0, 0.0, 0.5], "fov": 30.0, "aspecto": 16 / 9}
    tramos = [[0, 56, 0], [56, 60, 2]]
    mov = {"X": X, "antes": X - [0.05, 0, 0], "despues": X + [0.05, 0, 0], "tramos": tramos,
           "camara": camara, "foco": list(X[-1])}
    t = aspecto.Toma("prueba", "prueba", "as-de-guia", X, [X + [0.05, 0, 0]], h, tramos, [tramos], camara, None,
                     [], list(X[-1]), sub=2, lados=32, movimiento=mov)
    a = next(x for x in aspecto.ASPECTOS if x.clave == "1")
    parte = aspecto.preparar(t, a, tmp_path / "mallas", movimiento=True, seguidos=1)
    tiempos = aspecto.dibujar(a, motor, [parte], tmp_path, (160, 90), {"muestras": 4}, aviso=lambda *x: None)
    tipos = [d["tipo"] for d in tiempos]
    assert tipos == ["primero", "seguido", "movimiento-sin", "movimiento"]
    with Image.open(tmp_path / f"prueba-1-{motor.lower()}.png") as im:
        assert im.size == (160, 90) and im.mode == "RGB"
        # La mesa de madera se ve: el cuadro no es blanco.
        assert np.asarray(im, float).mean() < 200
    json.dumps(tiempos)


# --- El aspecto de los videos (T20b) ------------------------------------------

class _C:
    """Un cuadro del video, con lo que usan focos y velocidad_nodos."""

    def __init__(self, X, camara, paso=4, fase="enhebrar"):
        self.X, self.camara, self.paso, self.fase = np.asarray(X, float), camara, paso, fase


_CAM = {"pos": np.array([0.0, -30.0, 30.0]), "target": np.array([0.0, 0.0, 0.5]), "fov": 30.0, "aspecto": 16 / 9}


def test_la_velocidad_de_los_nodos_usa_los_vecinos_con_la_misma_cantidad_de_nodos():
    X = _cuerda(11)
    cuadros = [_C(X, _CAM), _C(X + [0.1, 0, 0], _CAM), _C(X + [0.2, 0, 0], _CAM), _C(_cuerda(12), _CAM)]
    assert np.allclose(aspecto.velocidad_nodos(cuadros, 1, 60), [6.0, 0, 0])   # (0,2 d en 2 cuadros) × 60
    assert np.allclose(aspecto.velocidad_nodos(cuadros, 2, 60), [6.0, 0, 0])   # el siguiente no sirve: hacia atrás
    assert np.allclose(aspecto.velocidad_nodos(cuadros, 0, 60), [6.0, 0, 0])
    assert aspecto.velocidad_nodos(cuadros, 3, 60) is None


def test_el_foco_sigue_la_punta_sin_saltar():
    X = _cuerda(11)
    lejos = X.copy()
    lejos[-1] += [0, 20.0, 0]
    cuadros = [_C(X, _CAM)] * 30 + [_C(lejos, _CAM)] * 30
    f = aspecto.focos(cuadros, 60)
    assert len(f) == 60
    assert f[0] == pytest.approx(aspecto._profundidad(_CAM, X[-1]))
    assert np.all(np.diff(f) >= -1e-9) and max(np.diff(f)) < (f[-1] - f[0]) / 10


def test_la_mesa_del_video_cubre_toda_la_cuerda_y_el_anfitrion():
    X = _cuerda(51, 30.0)
    lejos = X + [40.0, 25.0, 0]
    palo = {"pos": [-60.0, 0, 1, 60.0, 0, 1], "rol": "madera"}
    e = aspecto.escenario_video([X] * 30 + [lejos], [palo], 0.3)
    (cx, cy), (a, b) = e["mesa"]["centro"], e["mesa"]["semi"]
    pts = np.vstack([X, lejos, [[-60, 0, 1], [60, 0, 1]]])
    assert np.all(np.abs(pts[:, 0] - cx) < a) and np.all(np.abs(pts[:, 1] - cy) < b)
    assert e["luz"]["az"] == 0.3


def test_el_grano_del_video_cambia_en_cada_cuadro():
    im = Image.new("RGB", (192, 108), (128, 128, 128))
    a, b = np.asarray(aspecto.posproceso_video(im, 1), float), np.asarray(aspecto.posproceso_video(im, 2), float)
    assert not np.array_equal(a, b)
    assert np.array_equal(a, np.asarray(aspecto.posproceso_video(im, 1), float))
    assert a[:6, :6].mean() < a[50:58, 92:100].mean()


def test_la_ventana_de_la_prueba_va_al_medio_del_paso():
    from nudos.video import ventana
    X = _cuerda(11)
    cuadros = ([_C(X, _CAM, 3, "pausa") for _ in range(900)] + [_C(X, _CAM, 4, "enhebrar") for _ in range(1200)]
               + [_C(X, _CAM, 4, "pausa") for _ in range(100)])
    v = ventana(cuadros, segundos=10.0, fps=60)
    assert len(v) == 600
    i0 = next(i for i, c in enumerate(cuadros) if c is v[0])
    assert i0 == 900 + 600 - 300


def test_la_malla_del_video_lleva_la_velocidad(tmp_path):
    from nudos import video
    X = _cuerda(31, 6.0)
    ruta = str(tmp_path / "c.npz")
    video._SOLIDOS = None
    video._preparar_malla(X.astype(np.float32), [[0, 26, 0], [26, 30, 2]], ruta, float(np.linalg.norm(X[1] - X[0])),
                          np.tile([0.0, 3.0, 0.0], (31, 1)), "real")
    z = np.load(ruta)
    assert set(z.files) >= {"vertices", "caras", "uv", "material", "fibra_a", "fibra_b", "velocidad"}
    assert z["velocidad"].shape == z["vertices"].shape
    assert np.allclose(z["velocidad"], [0.0, 3.0, 0.0])


def test_blender_dibuja_los_cuadros_del_video(con_blender, tmp_path):
    import subprocess
    from nudos import RAIZ, video
    from nudos.prueba_atar import _datos_camara
    X = _cuerda(41, 10.0)
    h = float(np.linalg.norm(X[1] - X[0]))
    video._SOLIDOS = None
    trabajos = []
    for k in range(2):
        ruta = str(tmp_path / f"c{k}.npz")
        video._preparar_malla(X + [0.05 * k, 0, 0], [[0, 36, 0], [36, 40, 2]], ruta, h,
                              np.tile([3.0, 0, 0], (41, 1)), "real")
        trabajos.append({"cuerdas": [{"malla": ruta}], "camara": _datos_camara({**_CAM, "aspecto": 16 / 9}),
                         "foco": 40.0, "salida": str(tmp_path / f"r{k}.png")})
    escena = tmp_path / "escena.json"
    lote_v = aspecto.lote_video("estudio", 0.0)
    escena.write_text(json.dumps({"mallas": [], **aspecto.escenario_video([X], [], 0.0)}), encoding="utf-8")
    lote = tmp_path / "lote.json"
    lote.write_text(json.dumps({"ancho": 128, "alto": 72, "fps": 60, "motor": lote_v["motor"],
                                "ajustes": {**lote_v["ajustes"], "muestras": 4}, "aspecto": lote_v["aspecto"],
                                "escena": str(escena), "cuerdas": [{"estilo": "real", "resaltado": "real-ambar"}],
                                "desenfoque": True, "trabajos": trabajos}), encoding="utf-8")
    r = subprocess.run([blender.ejecutable(), "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", str(RAIZ / "render" / "blender" / "video.py"), "--", "--lote", str(lote)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert r.stdout.count("listo:") == 2
    for k in range(2):
        with Image.open(tmp_path / f"r{k}.png") as im:
            assert im.size == (128, 72) and im.mode == "RGB"


def test_armar_pasa_los_cuadros_por_archivos_y_en_orden(tmp_path):
    import shutil
    import subprocess
    from nudos import video
    if shutil.which("ffmpeg") is None:
        pytest.skip("falta ffmpeg")
    rutas = []
    for k in range(5):
        r = tmp_path / f"r{k}.png"
        Image.new("RGB", (960, 540), (40 * k, 90, 160)).save(r)
        rutas.append(r)
    cuadros = [video.Cuadro(_cuerda(5), 1, "pausa", None, titulo=0, alfa=1.0) for _ in rutas]
    salida = tmp_path / "v.mp4"
    video.armar(cuadros, rutas, {}, "previa", salida)
    assert salida.exists() and not list(tmp_path.glob("*.rgb"))
    n = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(salida)], capture_output=True, text=True)
    assert n.stdout.strip() == "5"
