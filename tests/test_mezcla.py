"""El diseño sonoro y la mezcla (T23c), sin red ni tarjeta: la voz con el proveedor falso, la
música con los instrumentos sintéticos y el foley desde cuadros armados aquí."""
import json
import shutil
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest

from nudos import foley as F
from nudos import mezcla as MZ
from nudos import musica as M
from nudos import sonoridad as so
from nudos import voz as V

SR = MZ.SR
FPS = 60
H = 0.2
TARJETAS = (4.0, 7.37, 12.11, 16.0)


def callar(*_):
    pass


@pytest.fixture(autouse=True)
def caches(tmp_path, monkeypatch):
    monkeypatch.setenv("NUDOS_MUSICA", str(tmp_path / "musica"))
    monkeypatch.setenv("NUDOS_VOZ", str(tmp_path / "voz"))


@pytest.fixture(scope="module")
def pista_sintetica(tmp_path_factory):
    """Veinte segundos: la canción del as de guía en tres capítulos, tres locuciones, cuatro
    tarjetas en lugares distintos del cuadro y el golpe."""
    base = tmp_path_factory.mktemp("pista")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("NUDOS_MUSICA", str(base / "musica"))
        mp.setenv("NUDOS_VOZ", str(base / "voz"))
        textos = ["Paso 2 de 7. Haz una gaza pequeña.", "Pasa el chicote por la gaza, por debajo.",
                  "Revisa este cruce: al revés no sale."]
        locs = V.locuciones(textos, V.Voz("prueba", proveedor="falso"), proveedor=V.Falso(), aviso=callar,
                            alineador=False)
        caps = [M.Capitulo("apertura", 0.0, 4.0), M.Capitulo("pasos", 4.0, 16.0), M.Capitulo("cierre", 16.0, 20.0)]
        eventos = [F.Evento("tarjeta", t, x) for t, x in zip(TARJETAS, (-0.35, 0.5, -0.8, 0.0))]
        eventos.append(F.Evento("golpe", 18.2, 0.1))
        p = MZ.pista(20.0, capitulos=caps, golpe=18.2, cancion="fogata", instrumentos=M.Sintetico(),
                     dichos=[MZ.Dicho(1.0, locs[0]), MZ.Dicho(6.0, locs[1]), MZ.Dicho(11.5, locs[2])],
                     eventos=eventos, aviso=callar)
    return p


# --------------------------------------------------------------------------
# La mezcla
# --------------------------------------------------------------------------
def test_la_pista_queda_a_14_lufs_y_1_dbtp(pista_sintetica):
    p = pista_sintetica
    assert p.audio.shape == (20 * SR, 2) and p.audio.dtype == np.float32
    assert np.isfinite(p.audio).all()
    assert abs(p.lufs - MZ.OBJETIVO) <= 0.5
    assert abs(so.lufs(p.audio, SR) - MZ.OBJETIVO) <= 0.5
    assert so.pico_real(p.audio, SR) <= MZ.TECHO + 0.05
    # Nunca hay ceros exactos largos (el AAC de ffmpeg 9.1 se corta).
    assert np.abs(p.audio[:int(0.5 * SR)]).max() > 0


def test_la_musica_queda_15_db_bajo_la_voz(pista_sintetica):
    p = pista_sintetica
    assert len(p.frases) == 3
    for a, b in p.frases:
        i, j = int(a * SR), int(b * SR)
        v = so.lufs(p.buses["voz"][i:j], SR)
        _, m = so.corto(p.buses["musica"][i:j], SR, ventana=0.4, salto=0.05)
        assert v - m.max() >= MZ.SEPARACION, (a, b, v, m.max())
    # Entre frases la música vuelve: lejos de la voz, a su nivel.
    _, m_sola = so.corto(p.buses["musica"][int(16.5 * SR):int(17.5 * SR)], SR, 0.4, 0.1)
    assert m_sola.max() > so.lufs(p.buses["voz"], SR) - MZ.SEPARACION


def _ataque(x, t, ventana=0.1):
    """Dónde empieza el golpe más fuerte entre 2 y 6 kHz cerca de t: el primer instante en que
    la envolvente pasa la mitad de su máximo, en ±ventana s (filtrado sin desfase)."""
    from scipy.ndimage import maximum_filter1d
    from scipy.signal import butter, sosfiltfilt
    i0 = int((t - ventana) * SR)
    seg = np.asarray(x, np.float64).mean(axis=1)[i0:int((t + ventana) * SR)]
    y = sosfiltfilt(butter(4, [2000, 6000], btype="band", fs=SR, output="sos"), seg)
    env = maximum_filter1d(np.abs(y), size=int(0.0005 * SR))
    return (i0 + int(np.argmax(env > 0.5 * env.max()))) / SR


def test_los_clics_caen_donde_aparecen_las_tarjetas(pista_sintetica):
    for t in TARJETAS:
        assert abs(_ataque(pista_sintetica.audio, t) - t) <= 0.020, t


def test_cada_cosa_suena_donde_se_ve(pista_sintetica):
    p = pista_sintetica
    # La tarjeta de la derecha (x = 0,5) suena más a la derecha; la de la izquierda (−0,8), al revés.
    e = p.buses["efectos"]
    for t, lado in ((7.37, 1), (12.11, 0)):
        seg = e[int(t * SR):int((t + 0.05) * SR)]
        izq, der = np.sqrt((seg ** 2).mean(axis=0))
        assert (der > 1.5 * izq) if lado else (izq > 1.5 * der)
    # La voz, en el centro: los dos canales iguales salvo su poquito de sala.
    v = p.buses["voz"]
    assert np.sqrt(((v[:, 0] - v[:, 1]) ** 2).mean()) < 0.05 * np.sqrt((v ** 2).mean())
    assert MZ.panear(np.ones(4), 0.0)[0].tolist() == pytest.approx([1.0, 1.0])
    l, r = MZ.panear(np.ones(4), 1.0)[0]
    assert r > l > 0 and l ** 2 + r ** 2 == pytest.approx(2.0)


def test_la_sala_chica():
    ir = MZ.sala_chica()
    assert ir.ndim == 2 and ir.shape[1] == 2
    e = (ir ** 2).sum(axis=1)
    # Una sala chica: lo que queda después de 0,3 s es menos de una milésima de la energía.
    assert e[int(0.3 * SR):].sum() < 1e-3 * e.sum()
    assert len(ir) < 0.5 * SR


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="sin ffmpeg")
def test_pegar_deja_aac_estereo_de_256_kbps(tmp_path, pista_sintetica):
    v = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=160x90:rate=30:duration=20", "-pix_fmt", "yuv420p", str(v)], check=True)
    MZ.pegar(v, pista_sintetica)
    r = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                                   "stream=codec_name,channels,bit_rate,sample_rate", "-of", "json", str(v)],
                                  capture_output=True, text=True).stdout)["streams"][0]
    assert r["codec_name"] == "aac" and r["channels"] == 2 and r["sample_rate"] == "48000"
    assert 200_000 < int(r["bit_rate"]) <= 270_000
    # Ya en AAC, el pico sigue bajo −1 dBTP y la sonoridad, en −14.
    from scipy.io import wavfile
    wav = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(v), "-vn", "-c:a", "pcm_f32le",
                    str(wav)], check=True)
    sr, x = wavfile.read(wav)
    assert so.pico_real(x, sr) <= -1.0
    assert abs(so.lufs(x, sr) - MZ.OBJETIVO) <= 0.5


# --------------------------------------------------------------------------
# El foley desde el motor
# --------------------------------------------------------------------------
def _recta(n=60, x0=0.0, y=0.0, z=0.5):
    return np.column_stack([x0 + np.arange(n) * H, np.full(n, y), np.full(n, z)])


def _cuadros(Xs, fase="recta", camara=None, titulos=None):
    titulos = titulos or [1] * len(Xs)
    return [SimpleNamespace(X=np.asarray(X, float), fase=fase, camara=camara, titulo=t) for X, t in zip(Xs, titulos)]


def test_el_roce_sigue_la_rapidez_y_la_presion():
    K = 30
    # Sobre la mesa: el doble de rápido, el doble de roce; más apoyada, más presión.
    lento = F.medir(_cuadros([_recta(x0=2.0 * k / FPS) for k in range(K)]), FPS, H)
    rapido = F.medir(_cuadros([_recta(x0=4.0 * k / FPS) for k in range(K)]), FPS, H)
    assert rapido.roce["mesa"][5] == pytest.approx(2 * lento.roce["mesa"][5], rel=1e-6)
    leve = F.medir(_cuadros([_recta(x0=2.0 * k / FPS, z=0.56) for k in range(K)]), FPS, H)
    assert lento.presion["mesa"][5] == pytest.approx(1.0) and leve.presion["mesa"][5] == pytest.approx(0.25)
    assert lento.roce["cuerda"].max() == 0 and lento.roce["anfitrion"].max() == 0

    # Dos partes de la cuerda, una deslizándose sobre la otra (en el aire): pegadas aprietan más.
    def par(brecha):
        return F.medir(_cuadros([np.vstack([_recta(z=2.0), _recta(x0=3.0 * k / FPS, y=brecha, z=2.0)])
                                 for k in range(K)]), FPS, H)
    pegadas, sueltas = par(1.0), par(1.09)
    assert pegadas.roce["cuerda"][5] == pytest.approx(sueltas.roce["cuerda"][5], rel=0.05)
    assert pegadas.presion["cuerda"][5] > 0.9 > 0.4 > sueltas.presion["cuerda"][5]
    assert pegadas.apretado[5] > 5 * sueltas.apretado[5]
    assert np.isfinite(pegadas.donde["cuerda"][5]).all() and pegadas.roce["mesa"].max() == 0


def test_el_roce_suena_solo_cuando_algo_se_desliza():
    quieta = [_recta()] * 30
    moviendo = [_recta(x0=3.0 * k / FPS) for k in range(30)]
    s = [x for x in F.del_motor(_cuadros(quieta + moviendo), FPS, H, tics=False) if x.tipo == "roce"]
    assert len(s) == 1 and s[0].bus == "foley"
    a = s[0].audio
    mitad = int(0.5 * SR)
    assert np.abs(a[:mitad - int(0.03 * SR)]).max() == 0
    assert np.sqrt((a[mitad:] ** 2).mean()) > 0


def test_el_tac_cuando_la_cuerda_cae_en_la_mesa():
    def cayendo(rapidez, desde=3.0):
        return [_recta(z=max(0.5, desde - rapidez * k / FPS)) for k in range(60)]
    tacs = [s for s in F.del_motor(_cuadros(cayendo(6.0)), FPS, H, tics=False) if s.tipo == "tac"]
    llega = next(k for k in range(1, 60) if 3.0 - 6.0 * k / FPS < F.SOBRE_LA_MESA)
    assert len(tacs) == 1 and tacs[0].t == pytest.approx(llega / FPS) and tacs[0].bus == "foley"
    # Bajada lenta: se apoya sin sonar.
    lenta = _cuadros(cayendo(0.5, desde=0.7))
    assert lenta[-1].X[0, 2] < F.SOBRE_LA_MESA
    assert not [s for s in F.del_motor(lenta, FPS, H, tics=False) if s.tipo == "tac"]


def _cruzando(z_quieta, z_movil):
    """Una cuerda: un tramo quieto a lo largo de x (en y = 0), una vuelta lejos y la punta, que
    avanza por x = 0 hacia +y a 6 d/s y pasa sobre (o bajo) el tramo quieto."""
    quieto = np.column_stack([-6.0 + np.arange(60) * H, np.zeros(60), np.full(60, z_quieta)])
    vuelta = np.vstack([np.column_stack([np.full(40, 6.0), -np.arange(1, 41) * H, np.full(40, 0.5)]),
                        np.column_stack([6.0 - np.arange(1, 31) * H, np.full(30, -8.0), np.full(30, 0.5)])])
    out = []
    for k in range(60):
        movil = np.column_stack([np.zeros(25), PUNTA0 - 24 * H + 6.0 * k / FPS + np.arange(25) * H,
                                 np.full(25, z_movil)])
        out.append(np.vstack([quieto, vuelta, movil]))
    return out


PUNTA0 = -1.25      # dónde está la punta al empezar: pasa y = 0 entre los cuadros 12 y 13


def test_un_tic_por_cruce_nuevo_agudo_encima_y_grave_debajo():
    def tics(z_quieta, z_movil):
        return [s for s in F.del_motor(_cuadros(_cruzando(z_quieta, z_movil)), FPS, H, tics=True)
                if s.tipo.startswith("tic")]
    encima = tics(0.5, 1.5)
    assert [s.tipo for s in encima] == ["tic_encima"]
    # El cruce aparece cuando la punta pasa y = 0: en el cuadro 13.
    aparece = next(k for k in range(60) if PUNTA0 + 6.0 * k / FPS > 0)
    assert aparece == 13 and abs(encima[0].t - aparece / FPS) <= 1.5 / FPS
    assert [s.tipo for s in tics(1.5, 0.5)] == ["tic_debajo"]
    # Agudo y grave: la frecuencia más fuerte de cada uno.
    rng = np.random.default_rng(0)
    def tono(x):
        return np.fft.rfftfreq(len(x), 1 / SR)[np.argmax(np.abs(np.fft.rfft(x)))]
    assert tono(F.tic(True, rng)) == pytest.approx(1750, rel=0.05)
    assert tono(F.tic(False, rng)) == pytest.approx(620, rel=0.05)
    # Por omisión, tics (TICS) en los nudos libres y no en los que tienen anfitrión.
    libre = F.del_motor(_cuadros(_cruzando(0.5, 1.5)), FPS, H, tics=None)
    assert any(s.tipo.startswith("tic") for s in libre) == F.TICS
    palo = [{"rol": "madera", "pos": [30, 30, 0, 31, 30, 0, 30, 31, 0], "nor": [0, 0, 1] * 3, "idx": [0, 1, 2]}]
    con_anfitrion = F.del_motor(_cuadros(_cruzando(0.5, 1.5)), FPS, H, mallas=palo, tics=None)
    assert not any(s.tipo.startswith("tic") for s in con_anfitrion)


def _camara(objetivo_x):
    return {"pos": [objetivo_x, -30.0, 30.0], "target": [objetivo_x, 0.0, 0.5], "fov": 30.0, "aspecto": 16 / 9}


def test_un_soplido_cuando_la_camara_se_mueve():
    K = 150
    # Quieta 1 s, se corre 10 d hacia +x en 0,8 s (suave) y queda quieta.
    xs = []
    for k in range(K):
        u = np.clip((k / FPS - 1.0) / 0.8, 0, 1)
        xs.append(10.0 * u * u * (3 - 2 * u))
    cs = [SimpleNamespace(X=_recta(n=40, x0=-4.0), fase="pausa", camara=_camara(x), titulo=1) for x in xs]
    s = F.de_la_camara(cs, FPS)
    assert len(s) == 1 and s[0].tipo == "soplido_camara"
    assert 0.9 <= s[0].t <= 1.2 and s[0].t + len(s[0].audio) / SR <= 2.0
    # La cámara va a +x: la imagen se corre a la izquierda, y el soplido con ella.
    assert s[0].x[0] > 0 > s[0].x[-1]
    # Quieta, nada.
    assert not F.de_la_camara([SimpleNamespace(X=_recta(), fase="pausa", camara=_camara(0.0), titulo=1)] * 60, FPS)


def test_los_eventos_de_los_cuadros_de_hoy():
    cs = _cuadros([_recta()] * 40, titulos=[1] * 10 + [2] * 20 + [0] * 10)
    for c in cs[30:]:
        c.fase = "apretar"
    cs[-1].fase = "pausa"
    ev = F.eventos_de_cuadros(cs, FPS)
    assert [(e.tipo, e.t) for e in ev] == [("tarjeta", 10 / FPS), ("tarjeta", 30 / FPS), ("golpe", 38 / FPS)]
    sonidos = F.de_eventos(ev)
    clics = [s for s in sonidos if s.tipo == "clic"]
    assert [s.t for s in clics] == [10 / FPS, 30 / FPS]
    # El soplido de cada tarjeta llega a su máximo justo cuando aparece.
    sop = [s for s in sonidos if s.tipo == "soplido"]
    assert all(s.ataque == pytest.approx(c.t) for s, c in zip(sop, clics))
