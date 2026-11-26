"""El audio de los videos (T18): el clic, el golpe y el roce, sintetizados desde los cuadros."""
import json
import shutil
import subprocess

import numpy as np
import pytest

from nudos import audio
from nudos.video import Cuadro, ya_armado

FPS = 30
H = 0.2


def _cuerda_en_la_mesa(dx: float = 0.0, z: float = 0.5) -> np.ndarray:
    s = np.arange(31) * H
    return np.column_stack([s - 3 + dx, np.zeros_like(s), np.full_like(s, z)])


def _dos_tramos(dy: float) -> np.ndarray:
    """Una cuerda con un tramo en la mesa a lo largo de x y otro, más adelante en la cuerda, que
    cruza encima a lo largo de y, tocándolo, corrido dy."""
    a = _cuerda_en_la_mesa()
    subida = np.linspace([3.0, 0.0, 0.5], [0.0, -3.0, 1.5], 25)[1:-1]
    yb = np.arange(31) * H - 3 + dy
    b = np.column_stack([np.zeros_like(yb), yb, np.full_like(yb, 1.5)])
    return np.vstack([a, subida, b])


def _cuadros(posiciones, titulos=None, fases=None):
    return [Cuadro(np.asarray(X, float), 1, (fases or {}).get(k, "enhebrar"), None,
                   (titulos or {}).get(k, 1)) for k, X in enumerate(posiciones)]


def test_el_roce_suena_donde_la_cuerda_roza():
    # Arrastrada por la mesa: roza la mesa.
    roce, _ = audio.contactos(_cuadros([_cuerda_en_la_mesa(0.1 * k) for k in range(6)]), FPS, H)
    assert roce["mesa"][1:].min() > 0 and roce["cuerda"].max() == 0
    # Moviéndose en el aire: no roza nada.
    roce, _ = audio.contactos(_cuadros([_cuerda_en_la_mesa(0.1 * k, z=5.0) for k in range(6)]), FPS, H)
    assert all(r.max() == 0 for r in roce.values())
    # Un tramo que se desliza sobre otro: roza la cuerda; el de abajo no se mueve sobre la mesa.
    roce, _ = audio.contactos(_cuadros([_dos_tramos(0.1 * k) for k in range(6)]), FPS, H)
    assert roce["cuerda"][1:].min() > 0 and roce["mesa"].max() == 0
    # Quieta: nada.
    roce, _ = audio.contactos(_cuadros([_dos_tramos(0.0)] * 4), FPS, H)
    assert all(r.max() == 0 for r in roce.values())


def _linea_de_tiempo():
    """2 s: se arrastra 1 s, cambia el título en el cuadro 30 y se aprieta del 40 al 50."""
    pos = [_cuerda_en_la_mesa(0.1 * min(k, 30)) for k in range(60)]
    return _cuadros(pos, titulos={k: 2 for k in range(30, 60)},
                    fases={k: "apretar" for k in range(40, 51)})


def test_la_pista_es_del_largo_del_video_y_sale_igual():
    cs = _linea_de_tiempo()
    x = audio.pista(cs, FPS, H)
    assert x.dtype == np.float32 and len(x) == int(np.ceil(len(cs) / FPS * audio.SR))
    assert np.array_equal(x, audio.pista(cs, FPS, H))


def test_el_clic_y_el_golpe_suenan_donde_y_como_deben():
    x = audio.pista(_linea_de_tiempo(), FPS, H)

    def pico(t0, t1):
        return 20 * np.log10(np.abs(x[int(t0 * audio.SR):int(t1 * audio.SR)]).max())

    assert pico(30 / FPS, 30 / FPS + 0.02) == pytest.approx(audio.CLIC_DB, abs=1.5)
    assert pico(50 / FPS, 50 / FPS + 0.2) == pytest.approx(audio.GOLPE_DB, abs=1.0)
    # Antes del clic solo está el roce, por debajo del clic.
    assert pico(0.1, 30 / FPS - 0.01) < audio.CLIC_DB


def test_no_quedan_ceros_seguidos():
    # Con segundos de ceros exactos, el AAC de ffmpeg 9.1 deja de entregar audio.
    cs = _cuadros([_cuerda_en_la_mesa()] * 90)
    x = (np.clip(audio.pista(cs, FPS, H), -1, 1) * 32767).astype(np.int16)
    ceros = np.flatnonzero(np.diff(np.concatenate([[1], (x == 0).astype(int), [1]])))
    largos = ceros[1::2] - ceros[::2]
    assert largos.max(initial=0) < 50


ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="sin ffmpeg")


def _video(ruta, segundos=1.0):
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"testsrc=size=160x90:rate={FPS}:duration={segundos}", "-pix_fmt", "yuv420p",
                    str(ruta)], check=True)


@ffmpeg
def test_pegar_pone_el_audio_sin_tocar_la_imagen(tmp_path):
    v = tmp_path / "v.mp4"
    _video(v)
    def flujos():
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,nb_frames",
                            "-of", "json", str(v)], capture_output=True, text=True).stdout
        return {f["codec_type"]: (f["codec_name"], f.get("nb_frames")) for f in json.loads(r)["streams"]}

    antes = flujos()
    assert "audio" not in antes
    audio.pegar(v, audio.pista(_linea_de_tiempo()[:30], FPS, H))
    despues = flujos()
    assert despues["video"] == antes["video"] and despues["audio"][0] == "aac"
    # Pegar otra vez reemplaza el audio, no agrega otro.
    audio.pegar(v, audio.pista(_linea_de_tiempo()[:30], FPS, H))
    assert flujos() == despues
    assert not list(tmp_path.glob("*.tmp.*"))


@ffmpeg
def test_un_video_con_el_sello_viejo_se_reconoce_por_sus_cuadros(tmp_path):
    v = tmp_path / "v.mp4"
    _video(v)
    viejo = json.loads('{"firma": "abc", "cuadros": 30}')
    assert ya_armado(v, viejo, "otra", 30)
    assert not ya_armado(v, viejo, "otra", 31)
    assert ya_armado(v, {"imagen": "x"}, "x", 99)
    assert not ya_armado(v, {"imagen": "x"}, "y", 30)
    assert not ya_armado(tmp_path / "no.mp4", viejo, "otra", 30)
