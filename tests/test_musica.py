"""La música (T23b), la sonoridad y el bajar la música bajo la voz (T23): sin bancos de sonido ni
programas aparte (los instrumentos sintéticos)."""
import numpy as np
import pytest

from nudos import mezcla
from nudos import musica as M
from nudos import sonoridad as so

SR = 48000


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("NUDOS_MUSICA", str(tmp_path / "musica"))


def _seno(f=1000.0, seg=3.0, amp=1.0, sr=SR, fase=0.0):
    t = np.arange(int(seg * sr)) / sr
    return amp * np.sin(2 * np.pi * f * t + fase)


# --------------------------------------------------------------------------
# La sonoridad, contra la norma
# --------------------------------------------------------------------------
def test_la_sonoridad_da_los_valores_de_la_norma():
    s = _seno()
    assert so.lufs(s, SR) == pytest.approx(-3.01, abs=0.05)               # un canal a 0 dBFS
    assert so.lufs(np.column_stack([s, s]), SR) == pytest.approx(0.0, abs=0.05)
    assert so.lufs(0.1 * s, SR) == pytest.approx(-23.01, abs=0.05)
    assert so.lufs(_seno(sr=44100), 44100) == pytest.approx(-3.01, abs=0.1)
    # El silencio no cuenta (compuerta absoluta) ni lo muy bajo (compuerta relativa); solo los
    # bloques que montan el borde bajan un poco el resultado.
    con_silencio = np.concatenate([np.zeros(3 * SR), 0.1 * _seno(seg=30.0), 1e-4 * s])
    assert so.lufs(con_silencio, SR) == pytest.approx(-23.01, abs=0.1)
    assert so.lufs(np.zeros(SR), SR) == float("-inf")
    assert so.a_lufs(0.1 * s, SR, -14.0).max() == pytest.approx(10 ** ((-14 + 3.01) / 20), rel=0.01)


def test_el_pico_real_ve_lo_que_pasa_entre_muestras():
    # Un seno a fs/4 con fase de 45°: las muestras llegan a 0,707 y la onda, a 1.
    s = _seno(f=SR / 4, seg=0.5, fase=np.pi / 4)
    assert 20 * np.log10(np.abs(s).max()) == pytest.approx(-3.01, abs=0.05)
    assert so.pico_real(s) == pytest.approx(0.0, abs=0.3)


def test_el_limitador_deja_el_pico_bajo_el_techo_y_no_toca_lo_demas():
    s = _seno(seg=1.0)
    x = np.concatenate([0.3 * s, 1.8 * s, 0.3 * s])
    y = so.limitar_pico(x, SR, -1.0)
    assert so.pico_real(y) <= -1.0 + 1e-6
    assert np.allclose(y[:int(0.9 * SR)], x[:int(0.9 * SR)], atol=1e-9)
    assert np.allclose(y[-int(0.9 * SR):], x[-int(0.9 * SR):], atol=1e-9)
    est = np.column_stack([x, 0.5 * x])
    assert so.limitar_pico(est, SR, -1.0).shape == est.shape


# --------------------------------------------------------------------------
# La composición
# --------------------------------------------------------------------------
FOGATA = M.CANCIONES["fogata"]
P = FOGATA.pulso


def _caps():
    return [M.Capitulo("apertura", 0.0, 4.9), M.Capitulo("pasos", 4.9, 15.2), M.Capitulo("verificacion", 15.2, 19.1),
            M.Capitulo("errores", 19.1, 24.0), M.Capitulo("aplicacion", 24.0, 28.7), M.Capitulo("cierre", 28.7, 33.5)]


def _demo(can):
    """La línea de tiempo de la demo en compases enteros de la canción, y su golpe."""
    compas = can.compas * can.pulso
    caps, t = [], 0.0
    for nombre, n in (("apertura", 2), ("pasos", 4), ("verificacion", 2), ("errores", 2), ("aplicacion", 2),
                      ("cierre", 2)):
        caps.append(M.Capitulo(nombre, t, t + n * compas))
        t += n * compas
    return M.en_pulso(caps, can.pulso), caps[-1].inicio + compas


def test_los_capitulos_caen_en_el_pulso():
    caps = M.en_pulso(_caps(), P)
    for c in caps:
        assert abs(c.inicio / P - round(c.inicio / P)) < 1e-6
        assert c.fin - c.inicio >= 2 * P - 1e-9
    assert all(a.fin == b.inicio for a, b in zip(caps, caps[1:]))
    assert [c.nombre for c in caps] == [c.nombre for c in _caps()]
    pulsos, compases = M.rejilla(caps, P, 4)
    assert np.allclose(np.diff(pulsos), P)
    assert all(np.isclose(compases, c.inicio).any() for c in caps)       # cada capítulo empieza un compás
    with pytest.raises(M.MusicaError):
        M.en_pulso([M.Capitulo("intermedio", 0, 3)])


def test_los_grados_y_las_voces_de_la_guitarra():
    assert M.acorde("I", 7) == (7, False, 7)
    assert M.acorde("vi", 7) == (4, True, 4)
    assert M.acorde("V/3", 7) == (2, False, 6)          # re con fa# en el bajo
    assert M.acorde("bVII", 2) == (0, False, 0)         # do en re mayor
    with pytest.raises(M.MusicaError):
        M.acorde("VIII", 0)
    sol = M.voces(*M.acorde("I", 7))
    assert sol == (43, 50, (59, 62, 67))                # sol en posición abierta
    do = M.voces(*M.acorde("IV", 7), previas=sol[2])
    assert do[0] == 48 and do[2] == (60, 64, 67)        # la voz más cercana a la anterior
    for t in range(12):
        for cifra in ("I", "ii", "iii", "IV", "V", "vi", "V/3", "bVII"):
            bajo, alterno, agudos = M.voces(*M.acorde(cifra, t))
            assert 40 <= bajo <= 51 and alterno > bajo and all(55 <= n <= 71 for n in agudos)


def test_los_compases_caen_en_los_capitulos_y_la_semilla_repite():
    caps = M.en_pulso(_caps(), P)
    golpe = caps[-1].inicio + 2.4
    a = M.componer(caps, golpe, semilla=7)
    b = M.componer(caps, golpe, semilla=7)
    c = M.componer(caps, golpe, semilla=8)
    assert a == b and a != c
    _, compases = M.rejilla(caps, P, 4)
    # El bajo toca en el primer pulso de cada compás (hasta el golpe), con lo poco que se corre.
    bajos = np.array([n.t for n in a["bajo"]])
    for t in compases[compases < golpe - 1e-6]:
        assert np.abs(bajos - t).min() <= 2.5 * M.TEMBLOR["bajo"] + 1e-9
    # Nada suena después del golpe, salvo el acorde final.
    for voz, notas in a.items():
        assert not [n for n in notas if n.t > golpe + 0.2], voz
    final = [n for n in a["guitarra"] if abs(n.t - golpe) < 0.12]
    assert len(final) >= 5 and max(n.dur for n in final) >= 4


def test_el_arreglo_cambia_en_cada_capitulo():
    caps = M.en_pulso(_caps(), P)
    notas = M.componer(caps, None)

    def en(voz, nombre):
        c = next(c for c in caps if c.nombre == nombre)
        return [n for n in notas[voz] if c.inicio - 0.02 <= n.t < c.fin - 0.02]
    assert en("motivo", "apertura") and en("motivo", "cierre")              # el motivo abre y cierra
    assert not en("motivo", "pasos")
    for voz in ("shaker", "bombo", "palmas", "contracanto", "pregunta"):
        assert not en(voz, "errores"), voz                                   # los errores, ralos
    assert en("palmas", "aplicacion") and en("contracanto", "aplicacion")    # la práctica, llena
    assert en("pregunta", "verificacion") and not en("pregunta", "pasos")
    assert not en("palmas", "pasos") and not en("contracanto", "pasos")
    assert len(en("guitarra", "errores")) < len(en("guitarra", "pasos"))
    # El motivo de la apertura queda abierto (en re) y el del cierre se resuelve en sol.
    assert en("motivo", "apertura")[-1].nota % 12 == 2
    assert en("motivo", "cierre")[-1].nota % 12 == 7


def test_las_cinco_canciones_son_distintas_y_comparten_el_motivo():
    huellas, motivos = set(), set()
    for clave, can in M.CANCIONES.items():
        caps, golpe = _demo(can)
        notas = M.componer(caps, golpe, cancion=can)
        assert notas["guitarra"] and notas["bajo"] and notas["motivo"], clave
        # La guitarra va en el tono de la canción, salvo los acordes prestados.
        escala = {(can.tonica + g) % 12 for g in M.ESCALA}
        fuera = [n for n in notas["guitarra"] if n.nota % 12 not in escala]
        assert len(fuera) <= len(notas["guitarra"]) * 0.15, clave
        huellas.add(tuple((n.nota - can.tonica) % 12 for n in notas["guitarra"][:40]))
        # El motivo: los mismos grados en todas, desde su tónica.
        apertura = [n for n in notas["motivo"] if n.t < caps[0].fin]
        motivos.add(tuple((n.nota - can.tonica) % 12 for n in apertura))
        # Todo en el rango de cada instrumento.
        de = M.instrumentos_de(can)
        for voz in ("motivo", "pregunta", "contracanto"):
            lo, hi = M.RANGO.get(de[voz], (0, 127))
            assert all(lo - 5 <= n.nota <= hi + 5 for n in notas[voz]), (clave, voz)
    assert len(huellas) == len(M.CANCIONES)
    assert len(motivos) == 1


def test_el_vals_va_en_tres():
    can = M.CANCIONES["rocio"]
    assert can.compas == 3
    caps, golpe = _demo(can)
    _, compases = M.rejilla(caps, can.pulso, can.compas)
    assert np.allclose(np.diff(compases[:5]), 3 * can.pulso)
    notas = M.componer(caps, golpe, cancion=can)
    bajos = np.array([n.t for n in notas["bajo"]])
    for t in compases[compases < golpe - 1e-6]:
        assert np.abs(bajos - t).min() <= 2.5 * M.TEMBLOR["bajo"] + 1e-9


def test_cada_nudo_tiene_su_cancion():
    import yaml
    edicion = yaml.safe_load((M.RAIZ / "config" / "edicion-1.yaml").read_text(encoding="utf-8"))
    slugs = [s for grupo in edicion.values() for s in grupo]
    reparto = M.reparto()
    assert sorted(reparto) == sorted(slugs)
    assert set(reparto.values()) == set(M.CANCIONES)
    cuenta = [list(reparto.values()).count(c) for c in M.CANCIONES]
    assert max(cuenta) - min(cuenta) <= 1
    assert M.cancion_de("as-de-guia").clave == "fogata"
    assert M.cancion_de("un-nudo-nuevo") == M.cancion_de("un-nudo-nuevo")
    assert M.cancion_de("un-nudo-nuevo").clave in M.CANCIONES


def test_el_midi_no_corta_una_nota_que_se_repite():
    notas = [M.Nota(0.0, 1.0, 60, 80), M.Nota(0.6, 1.0, 60, 80), M.Nota(0.0, 2.0, 64, 70)]
    datos = M.midi(notas, 25)
    assert datos[:4] == b"MThd" and b"MTrk" in datos
    i = datos.index(b"MTrk") + 8
    t, eventos = 0, []
    while i < len(datos):
        d = 0
        while True:
            b = datos[i]
            i += 1
            d = (d << 7) | (b & 0x7F)
            if not b & 0x80:
                break
        t += d
        st = datos[i]
        if st == 0xFF:
            n = datos[i + 2]
            i += 3 + n
            continue
        if st & 0xF0 in (0x80, 0x90):
            eventos.append((t, st & 0xF0, datos[i + 1]))
            i += 3
        else:
            i += 2 if st & 0xF0 in (0xC0, 0xD0) else 3
    do = [(t, s) for t, s, n in eventos if n == 60]
    assert [s for _, s in do] == [0x90, 0x80, 0x90, 0x80]
    assert do[1][0] < do[2][0]


def test_la_altura_de_una_muestra():
    x = np.column_stack([_seno(f=440.0 * 2 ** (0.3 / 12), seg=1.0)] * 2) * np.exp(-np.arange(SR) / SR)[:, None]
    assert M.altura(x, 69) == pytest.approx(69.3, abs=0.02)
    y = M._transponer(x, 2.0)
    assert M.altura(y, 71) == pytest.approx(71.3, abs=0.03)


def test_la_musica_de_un_video_con_instrumentos_sinteticos():
    inst = M.Sintetico()
    caps = _caps()
    m = M.musica(caps, golpe=31.3, instrumentos=inst)
    assert m.mezcla.shape == (int(np.ceil(m.capitulos[-1].fin * SR)), 2)
    assert m.mezcla.dtype == np.float32
    assert so.lufs(m.mezcla, SR) == pytest.approx(M.NIVEL, abs=0.6)
    assert so.pico_real(m.mezcla) <= -1.0 + 1e-6
    m2 = M.musica(caps, golpe=31.3, instrumentos=inst)                      # del caché, igual
    assert m.huella == m2.huella and np.array_equal(m.mezcla, m2.mezcla)
    assert M.musica(caps, golpe=31.3, semilla=1, instrumentos=inst).huella != m.huella
    # La canción del nudo, con su pulso y su compás.
    r = M.musica(caps, golpe=31.3, slug="amarre-cuadrado", instrumentos=inst)
    can = M.cancion_de("amarre-cuadrado")
    assert r.cancion == can.clave
    assert np.allclose(np.diff(r.compases[:3]), can.compas * can.pulso)


# --------------------------------------------------------------------------
# La música bajo la voz
# --------------------------------------------------------------------------
def test_la_musica_baja_15_db_mientras_hay_voz():
    rng = np.random.default_rng(1)
    dur = 12.0
    n = int(dur * SR)
    musica = rng.standard_normal((n, 2)) * 0.05
    voz = np.zeros(n)
    tramos = [(2.0, 5.0), (7.0, 9.5)]
    for a, b in tramos:
        i, j = int(a * SR), int(b * SR)
        t = np.arange(j - i) / SR
        voz[i:j] = 0.3 * np.sin(2 * np.pi * 180 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t))
    g = mezcla.ganancia_bajo_voz(voz, musica, SR)
    for a, b in tramos:
        i, j = int((a + 0.05) * SR), int((b - 0.05) * SR)
        v = so.lufs(voz[i:j], SR)
        m = so.lufs(musica[i:j] * g[i:j, None], SR)
        assert v - m >= mezcla.SEPARACION
    # Cuando entra la voz, la música ya bajó del todo y, lejos de ella, no la toca.
    assert g[int(2.0 * SR)] <= g[int(3.5 * SR)] * 1.01 < 1.0
    assert np.allclose(g[:int(1.0 * SR)], 1.0) and np.allclose(g[-int(1.0 * SR):], 1.0)
    x = mezcla.bajo_la_voz(musica, voz, SR)
    assert x.shape == (n, 2)
