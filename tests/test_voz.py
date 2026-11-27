"""La voz de los videos (T23a): la pronunciación, el caché, los tiempos de cada palabra y los
proveedores, con proveedores falsos (sin red ni tarjeta)."""
import base64
import io
import json

import numpy as np
import pytest

from nudos import voz as V


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("NUDOS_VOZ", str(tmp_path / "voz"))
    return tmp_path / "voz"


def test_los_numeros_van_en_letras():
    assert V.numero(0) == "cero"
    assert V.numero(7) == "siete"
    assert V.numero(21) == "veintiuno"
    assert V.numero(21, apocope=True) == "veintiún"
    assert V.numero(31, apocope=True) == "treinta y un"
    assert V.numero(100) == "cien"
    assert V.numero(115) == "ciento quince"
    assert V.numero(2026) == "dos mil veintiséis"
    assert V.numero(1000) == "mil"


def test_la_pronunciacion_dice_las_medidas_y_recuerda_como_se_ve():
    ps = V.para_decir("Paso 4 de 7. Usa «una cuerda» de unos 2 m (o 1,5 m) y de 6 a 10 mm.")
    assert V.texto_dicho(ps) == ("Paso número cuatro de siete. Usa una cuerda de unos dos metros o un metro y medio "
                                 "y de seis a diez milímetros.")
    vistas = [p.texto for p in ps]
    assert "4" in vistas and "7." in vistas and "2 m" in vistas and "1,5 m" in vistas and "10 mm." in vistas
    assert all("«" not in p.dicha and "(" not in p.dicha for p in ps)
    # La puntuación de apertura va con la palabra de después.
    assert V.para_decir("¿Ves el cruce 1?")[0].texto == "¿Ves"
    assert V.texto_dicho(V.para_decir("¿Ves el cruce 1?")) == "¿Ves el cruce uno?"
    assert V.texto_dicho(V.para_decir("Un 1 m, no 21 m.")) == "Un un metro, no veintiún metros."


def test_las_silabas():
    for palabra, n in {"gaza": 2, "chicote": 3, "ballestrinque": 4, "pequeña": 3, "guía": 2, "que": 1,
                       "oído": 3, "aire": 2, "país": 2, "muy": 1, "y": 1, "construcción": 3, "caer": 2}.items():
        assert V.silabas(palabra) == n, palabra


def test_nada_se_genera_dos_veces(cache):
    falso = V.Falso()
    voz = V.Voz("prueba", proveedor="falso")
    textos = ["Paso 2 de 7. Haz una gaza pequeña.", "Sube por la gaza.", "Sube por la gaza."]
    a = V.locuciones(textos, voz, proveedor=falso, aviso=lambda *_: None)
    assert falso.llamadas == 1 and len(a) == 3
    assert a[1].huella == a[2].huella                      # el repetido, una sola vez
    b = V.locuciones(textos, voz, proveedor=falso, aviso=lambda *_: None)
    assert falso.llamadas == 1
    assert [x.huella for x in a] == [x.huella for x in b]
    assert np.array_equal(a[0].audio, b[0].audio)
    assert a[0].tiempos == "proveedor" and a[0].audio.dtype == np.float32
    # Otra voz u otro texto sí se generan.
    V.locuciones(["Sube por la gaza."], V.Voz("otra", proveedor="falso"), proveedor=falso, aviso=lambda *_: None)
    assert falso.llamadas == 2


def test_los_tiempos_estimados_quedan_cerca_de_los_reales():
    falso = V.Falso()
    texto = ("As de guía. Forma una gaza fija en el extremo de la cuerda: no se cierra ni se corre cuando "
             "tiras del firme. Revisa este cruce, que al revés no sale.")
    x, sr, verdad = falso.generar([(V.para_decir(texto), V.Voz("x"))])[0]
    est = V.estimar_tiempos(x, sr, verdad)
    assert [p.texto for p in est] == [p.texto for p in verdad]
    err = np.array([abs(a.inicio - b.inicio) for a, b in zip(est, verdad)])
    assert err.mean() < 0.06 and err.max() < 0.15
    assert all(p.fin > p.inicio for p in est)
    assert all(a.fin <= b.inicio + 1e-6 for a, b in zip(est, est[1:]))


def test_sin_tiempos_del_proveedor_se_estiman(monkeypatch):
    L = V.locuciones(["Sube por la gaza, entra por debajo."], V.Voz("x"), proveedor=SinTiempos(),
                     aviso=lambda *_: None, alineador=False)[0]
    assert L.tiempos == "estimados"
    assert [p.texto for p in L.palabras] == ["Sube", "por", "la", "gaza,", "entra", "por", "debajo."]
    assert L.palabras[0].inicio < 0.4 and L.palabras[-1].fin <= L.segundos


class SinTiempos(V.Falso):
    """El falso, pero sin decir los tiempos, como el modelo local."""
    def generar(self, pedidos, aviso=print):
        return [(x, sr, None) for x, sr, _ in super().generar(pedidos, aviso)]


class AlineadorFalso(V.Alineador):
    """Da los tiempos exactos del falso; o nada («nada»), o falla como un entorno roto («falla»)."""
    nombre = "falso"

    def __init__(self, modo="exacto"):
        self.modo, self.llamadas = modo, 0

    def alinear(self, pedidos, aviso=print):
        from nudos import ia
        self.llamadas += 1
        if self.modo == "falla":
            raise ia.IAError("sin modelo")
        if self.modo == "nada":
            return [None for _ in pedidos]
        return [V.Falso().generar([(p, V.Voz("x"))])[0][2] for _, _, p in pedidos]


def test_las_palabras_alineadas_calzan_con_los_trozos():
    ps = V.para_decir("Paso 35. Sube por la gaza.")
    assert V.texto_dicho(ps) == "Paso treinta y cinco. Sube por la gaza."
    # Un trozo por cada pedazo entre espacios, en pasos de 80 ms; la última sin duración, pegada al
    # final, como la deja el modelo.
    t = [(0.40, 0.72), (0.72, 0.96), (0.96, 1.04), (1.04, 1.36), (1.92, 2.16), (2.16, 2.32), (2.32, 2.80),
         (2.80, 2.80)]
    trozos = [{"texto": "", "inicio": a, "fin": b} for a, b in t]
    al = V.palabras_alineadas(ps, trozos, 2.9)
    assert [p.texto for p in al] == ["Paso", "35.", "Sube", "por", "la", "gaza."]
    assert (al[1].inicio, al[1].fin) == (0.72, 1.36)        # «treinta y cinco»: del primer trozo al último
    assert al[4].inicio == 2.32 and al[5].fin == 2.8 and al[4].fin == al[5].inicio
    assert al[5].fin - al[5].inicio > al[4].fin - al[4].inicio > V.MIN_PALABRA   # por sílabas
    # Si no calzan, None: otro número de trozos, o tiempos fuera del audio o hacia atrás.
    assert V.palabras_alineadas(ps, trozos[:-1], 2.9) is None
    assert V.palabras_alineadas(ps, trozos, 2.5) is None
    assert V.palabras_alineadas(ps, trozos[:4] + [{"inicio": 0.1, "fin": 0.2}] + trozos[5:], 2.9) is None


def test_el_alineador_pone_los_tiempos_sin_volver_a_generar():
    texto = "Sube por la gaza, entra por debajo y sale por encima."
    voz, prov = V.Voz("x"), SinTiempos()
    callar = dict(aviso=lambda *_: None)
    assert V.locuciones([texto], voz, proveedor=prov, alineador=False, **callar)[0].tiempos == "estimados"
    al = AlineadorFalso()
    L = V.locuciones([texto], voz, proveedor=prov, alineador=al, **callar)[0]
    assert prov.llamadas == 1 and al.llamadas == 1             # la del caché se alinea, no se genera
    assert L.tiempos == "alineados"
    verdad = V.Falso().generar([(V.para_decir(texto), voz)])[0][2]
    assert [(p.inicio, p.fin) for p in L.palabras] == [(p.inicio, p.fin) for p in verdad]
    V.locuciones([texto], voz, proveedor=prov, alineador=al, **callar)
    assert al.llamadas == 1                                    # ya alineada con este alineador
    # Si no calza, quedan los estimados y no se vuelve a intentar con el mismo alineador.
    nada = AlineadorFalso("nada")
    assert V.locuciones(["Haz una gaza."], voz, proveedor=prov, alineador=nada, **callar)[0].tiempos == "estimados"
    V.locuciones(["Haz una gaza."], voz, proveedor=prov, alineador=nada, **callar)
    assert nada.llamadas == 1
    # Si el alineador falla, también, pero se vuelve a intentar la próxima vez.
    roto = AlineadorFalso("falla")
    assert V.locuciones(["Tira del firme."], voz, proveedor=prov, alineador=roto, **callar)[0].tiempos == "estimados"
    V.locuciones(["Tira del firme."], voz, proveedor=prov, alineador=roto, **callar)
    assert roto.llamadas == 2


def test_qwen_alinea_en_su_entorno(monkeypatch, tmp_path):
    from pathlib import Path
    from nudos import ia
    vistos = []

    def correr(entorno, script, trabajo, aviso=print, **kw):
        vistos.append((entorno, script, trabajo["tareas"]))
        assert all(Path(t["audio"]).exists() for t in trabajo["tareas"])
        return {"alineadas": [[{"texto": w, "inicio": 0.2 + 0.3 * i, "fin": 0.5 + 0.3 * i}
                               for i, w in enumerate(t["texto"].split())] for t in trabajo["tareas"]]}
    monkeypatch.setattr(ia, "correr", correr)
    res = V.QwenAlineador().alinear([(np.zeros(3 * 48000), 48000, V.para_decir("Paso 21. Sube."))],
                                    aviso=lambda *_: None)
    assert vistos[0][:2] == ("qwen-asr", "alinear.py")
    assert vistos[0][2][0]["texto"] == "Paso veintiuno. Sube." and vistos[0][2][0]["idioma"] == "Spanish"
    assert [(p.texto, p.inicio, p.fin) for p in res[0]] == [("Paso", 0.2, 0.5), ("21.", 0.5, 0.8),
                                                            ("Sube.", 0.8, 1.1)]
    assert not list((V.carpeta_cache() / "tmp").glob("alinear-*"))     # sin restos
    # Sin su entorno, por omisión no hay alineador y los tiempos se estiman.
    monkeypatch.setenv("NUDOS_IA", str(tmp_path / "sin-ia"))
    assert V._el_alineador(None) is None and V._el_alineador(False) is None


def test_elevenlabs_con_una_api_falsa(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "clave-de-prueba")
    pedidos = []
    texto_dicho = V.texto_dicho(V.para_decir("Paso 1. Sube."))

    class Respuesta(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def abrir(req, timeout=None):
        pedidos.append(req)
        pcm = (np.sin(np.arange(24000) / 10) * 8000).astype("<i2").tobytes()
        letras = list(texto_dicho)
        ini = [0.1 * i for i in range(len(letras))]
        return Respuesta(json.dumps({"audio_base64": base64.b64encode(pcm).decode(),
                                     "alignment": {"characters": letras, "character_start_times_seconds": ini,
                                                   "character_end_times_seconds": [t + 0.1 for t in ini]}}).encode())
    voz = V.Voz("eleven", proveedor="elevenlabs", id="voz123")
    L = V.locuciones(["Paso 1. Sube."], voz, proveedor=V.ElevenLabs(abrir=abrir), aviso=lambda *_: None)[0]
    assert len(pedidos) == 1
    assert "voz123" in pedidos[0].full_url and pedidos[0].get_header("Xi-api-key") == "clave-de-prueba"
    assert json.loads(pedidos[0].data)["text"] == "Paso uno. Sube."
    assert L.tiempos == "proveedor"
    assert [(p.texto, p.inicio) for p in L.palabras] == [("Paso", 0.0), ("1.", 0.5), ("Sube.", 1.0)]
    # La clave nunca queda en el caché.
    assert "clave-de-prueba" not in "".join(p.read_text(encoding="utf-8") for p in V.carpeta_cache().glob("*.json"))


def test_elevenlabs_sin_clave_falla(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(V.VozError):
        V.locuciones(["Hola."], V.Voz("e", proveedor="elevenlabs", id="x"), aviso=lambda *_: None)


def test_qwen_disena_una_vez_y_clona_cada_texto(monkeypatch):
    from nudos import ia
    llamadas = []

    def correr(entorno, script, trabajo, aviso=print, **kw):
        llamadas.append(trabajo["tareas"])
        for t in trabajo["tareas"]:
            V._escribir_wav(__import__("pathlib").Path(t["salida"]), np.sin(np.arange(24000) / 7) * 0.2, 24000)
        return {"hechas": []}
    monkeypatch.setattr(ia, "correr", correr)
    voz = V.Voz("diseñada", descripcion="A calm voice.", semilla=7)
    a = V.locuciones(["Haz una gaza.", "Sube por la gaza."], voz, proveedor=V.QwenTTS(), aviso=lambda *_: None,
                     alineador=False)
    assert [len(c) for c in llamadas] == [1, 2]
    assert llamadas[0][0]["tipo"] == "disenar" and llamadas[0][0]["instruccion"] == "A calm voice."
    assert {t["tipo"] for t in llamadas[1]} == {"clonar"}
    assert all(t["referencia"] == llamadas[0][0]["salida"] for t in llamadas[1])
    assert all(t["texto_referencia"] == V.TEXTO_REFERENCIA for t in llamadas[1])
    assert a[0].tiempos == "estimados"
    # Otra vez: ni diseño ni clon.
    V.locuciones(["Haz una gaza.", "Sube por la gaza."], voz, proveedor=V.QwenTTS(), aviso=lambda *_: None,
                 alineador=False)
    assert len(llamadas) == 2


def test_la_voz_d_esta_en_el_repositorio():
    assert V.VOZ_D.nombre == "joven"
    ruta = V.VOZ_D.ruta_referencia()
    assert ruta.exists() and ruta.stat().st_size > 100_000
    assert V.VOZ_D.huella()["referencia"] == V._huella_archivo(ruta)
    assert V.QwenTTS().muestra(V.VOZ_D) == (ruta, V.TEXTO_REFERENCIA)


def test_la_voz_de_los_videos_es_la_de_gabriel_fuera_de_git(monkeypatch, tmp_path):
    # Su muestra va en entradas/ (fuera de git), y cada locución pasa por Sidon.
    assert V.VOZ.restaurar and V.VOZ.referencia.startswith("entradas/") and V.VOZ.texto_referencia
    monkeypatch.setenv("NUDOS_ENTRADAS", str(tmp_path))
    assert V.VOZ.ruta_referencia() == tmp_path / "_voz" / "gabriel-estudio.wav"
    with pytest.raises(V.VozError):
        V.VOZ.huella()                                      # sin la muestra, un error que dice cuál falta
    (tmp_path / "_voz").mkdir()
    (tmp_path / "_voz" / "gabriel-estudio.wav").write_bytes(b"muestra")
    assert V.VOZ.huella()["referencia"] == V._huella_archivo(tmp_path / "_voz" / "gabriel-estudio.wav")


def test_los_textos_de_la_prueba_salen_de_la_especificacion():
    from nudos.ficha import terminos_encontrados
    from nudos.prueba_sonido import textos_prueba
    t = textos_prueba("as-de-guia")
    assert [n for n, _ in t] == ["Apertura", "Paso 2", "Paso 4"]
    assert t[0][1].startswith("As de guía. Forma una gaza fija")
    assert t[1][1].startswith("Paso 2 de 7. Haz una gaza pequeña. ")
    assert not terminos_encontrados(" ".join(x for _, x in t))
    assert len(V.VOCES_PRUEBA) == 4 and len({v.nombre for v in V.VOCES_PRUEBA}) == 4


# --------------------------------------------------------------------------
# Las grabaciones: la voz de Gabriel
# --------------------------------------------------------------------------
def _rms_db(x):
    return 10 * np.log10(np.mean(np.asarray(x, np.float64) ** 2) + 1e-20)


def test_limpiar_baja_el_ruido_y_deja_la_voz():
    sr = V.SR
    rng = np.random.default_rng(3)
    t = np.arange(4 * sr) / sr
    voz = sum(np.sin(2 * np.pi * f * t) / k for k, f in enumerate((180, 360, 540, 900, 1800), 1))
    activa = (t % 1.0) < 0.5                                     # medio segundo sí, medio no
    limpio = 0.2 * voz * activa
    ruido = 10 ** (-45 / 20) * rng.standard_normal(len(t))
    y = V.limpiar(limpio + ruido)
    hueco = ~activa & ((t % 1.0) > 0.6) & ((t % 1.0) < 0.9)      # lejos de los bordes
    lleno = activa & ((t % 1.0) > 0.1) & ((t % 1.0) < 0.4)
    baja = _rms_db(ruido[hueco]) - _rms_db(y[hueco])
    assert 8.0 < baja <= V.REDUCCION + 0.5
    assert abs(_rms_db(y[lleno]) - _rms_db((limpio + ruido)[lleno])) < 1.0
    assert len(y) == len(t) and y.dtype == np.float32


def test_leer_grabacion_en_mono_a_48_khz(tmp_path):
    from scipy.io import wavfile
    sr = 44100
    t = np.arange(int(1.5 * sr)) / sr
    x = np.column_stack([0.5 * np.sin(2 * np.pi * 440 * t), 0.25 * np.sin(2 * np.pi * 440 * t)])
    wavfile.write(tmp_path / "toma.wav", sr, (x * 32767).astype(np.int16))
    y = V.leer_grabacion(tmp_path / "toma.wav")
    assert y.ndim == 1 and abs(len(y) - 1.5 * V.SR) < 0.01 * V.SR
    with pytest.raises(V.VozError):
        V.leer_grabacion(tmp_path / "no-esta.m4a")


def _transcripcion(frases, pausa=0.5, ritmo=0.3):
    """Una transcripción alineada: cada frase, una palabra cada `ritmo` s, y `pausa` s entre frases."""
    palabras, t = [], 0.2
    for frase in frases:
        for w in frase.split():
            palabras.append(V.Palabra(w, w, round(t, 3), round(t + ritmo - 0.05, 3)))
            t += ritmo
        t += pausa
    return V.Transcripcion(" ".join(frases), palabras, t, "alineados")


def test_los_tramos_limpios_esquivan_los_tropiezos():
    limpia = ("Forma una gaza fija en el extremo de la cuerda que no se cierra cuando tiras "
              "del firme y sirve para rodear un poste.")
    tropiezo = ("No se cierra ni se, ni se corre cuando tiras del firme y sirve para pasar la "
                "cuerda por una argolla o colgar algo.")
    t = _transcripcion([tropiezo, limpia])
    tramos = V.tramos_limpios(t, largo=(6.0, 14.0))
    assert tramos
    _, a, b = tramos[0]
    assert " ".join(p.texto for p in t.palabras[a:b]) == limpia
    assert all(a >= len(tropiezo.split()) for _, a, _ in tramos)
    assert V._tropieza([V.Palabra(w, w) for w in "pasa por por una argolla".split()])
    assert V._tropieza([V.Palabra(w, w) for w in "eh pasa la cuerda".split()])
    assert not V._tropieza([V.Palabra(w, w) for w in "pasa una vez por encima y una por debajo".split()])
    # Sin tiempos no hay tramos.
    assert V.tramos_limpios(V.Transcripcion("a", t.palabras, 1.0, "sin")) == []
    # Con el texto que se leyó, solo lo que lo dice palabra por palabra (los números, en letras).
    leida = _transcripcion(["Usa una de seis a diez milímetros de grosor que no sea rígida y que no tenga nudos.",
                            "Usa una de seis a diez milímetros de grosor que no sea muy rígida y sin nudos."])
    fuente = "materiales: >-\n  Usa una de 6 a 10 mm de grosor que no sea rígida y que no tenga nudos."
    tramos = V.tramos_limpios(leida, largo=(4.0, 14.0), fuente=fuente)
    assert tramos and all(b <= 18 for _, _, b in tramos)      # la primera frase tiene 18 palabras
    assert len(V.tramos_limpios(leida, largo=(4.0, 14.0))) > len(tramos)


def test_recorte_con_aire_y_fundidos():
    x = np.ones(3 * V.SR, np.float32)
    y = V.recorte(x, 1.0, 2.0, margen=0.1, fundido=0.02)
    assert abs(len(y) - 1.2 * V.SR) <= 1
    assert y[0] == 0 and y[-1] == 0 and y[len(y) // 2] == 1


def test_transcribir_con_el_reconocimiento_falso(monkeypatch):
    from pathlib import Path
    from nudos import ia
    vistos = []

    def correr(entorno, script, trabajo, aviso=print, **kw):
        vistos.append(script)
        assert entorno == "qwen-asr" and all(Path(t["audio"]).exists() for t in trabajo["tareas"])
        if script == "transcribir.py":
            assert "gaza" in trabajo["tareas"][0]["contexto"]
            return {"hechas": [{"texto": "Haz una gaza, chica.", "idioma": "Spanish"}] * len(trabajo["tareas"])}
        return {"alineadas": [[{"texto": w, "inicio": 0.2 + 0.4 * i, "fin": 0.5 + 0.4 * i}
                               for i, w in enumerate(["Haz", "una", "gaza", "chica"])] for _ in trabajo["tareas"]]}
    monkeypatch.setattr(ia, "correr", correr)
    audio = np.zeros(2 * V.SR, np.float32)
    t = V.transcribir([audio], aviso=lambda *_: None)[0]
    assert vistos == ["transcribir.py", "alinear.py"]
    assert t.texto == "Haz una gaza, chica." and t.tiempos == "alineados" and t.segundos == 2.0
    assert [(p.texto, p.inicio, p.fin) for p in t.palabras] == [
        ("Haz", 0.2, 0.5), ("una", 0.6, 0.9), ("gaza,", 1.0, 1.3), ("chica.", 1.4, 1.7)]
    # Del caché, sin volver a llamar a los modelos; y sin restos en la carpeta temporal.
    assert V.transcribir([audio], aviso=lambda *_: None)[0].palabras == t.palabras
    assert vistos == ["transcribir.py", "alinear.py"]
    assert not list((V.carpeta_cache() / "tmp").glob("*.wav"))


def test_una_grabacion_entra_a_la_mezcla_como_locucion():
    x = np.zeros(V.SR, np.float32)
    loc = V.locucion_grabada(x, [V.Palabra("Hola.", "Hola.", 0.1, 0.4)])
    assert loc.texto == "Hola." and loc.tiempos == "alineados" and loc.segundos == 1.0


def test_el_nudo_de_cada_grabacion_por_su_nombre():
    from nudos.prueba_sonido import _slug_de
    assert _slug_de("nudo simple") == "simple"
    assert _slug_de("As de Guía") == "as-de-guia"
    assert _slug_de("amarre cuadrado ") == "amarre-cuadrado"
    assert _slug_de("receta de pan") is None


def test_una_voz_que_se_limpia_cambia_su_huella_y_su_audio(cache):
    callar = {"aviso": lambda *_: None, "alineador": False}
    normal = V.Voz("prueba", proveedor="falso")
    assert "limpiar" not in normal.huella()                     # las voces de antes no cambian
    limpia = V.Voz("prueba", proveedor="falso", limpiar=True)
    assert limpia.huella()["limpiar"] is True
    a = V.locuciones(["Tira del firme y aprieta."], normal, **callar)[0]
    b = V.locuciones(["Tira del firme y aprieta."], limpia, **callar)[0]
    assert a.huella != b.huella and not np.allclose(a.audio[:len(b.audio)], b.audio[:len(a.audio)])


def _sidon_falso(llamadas):
    """Un Sidon de mentira: «restaura» dejando el audio a la mitad, a 48 kHz."""
    from scipy.io import wavfile

    def correr(entorno, script, trabajo, aviso=print, **kw):
        llamadas.append((entorno, script, len(trabajo["tareas"])))
        for t in trabajo["tareas"]:
            _, x = wavfile.read(t["audio"])
            wavfile.write(t["salida"], 48000, np.asarray(x, np.float32) * 0.5)
        return {"hechas": len(trabajo["tareas"])}
    return correr


def test_restaurar_con_sidon_falso(monkeypatch):
    from nudos import ia
    llamadas = []
    monkeypatch.setattr(ia, "correr", _sidon_falso(llamadas))
    a = np.full(V.SR // 2, 0.4, np.float32)
    y = V.restaurar([a], aviso=lambda *_: None)[0]
    assert llamadas == [("qwen-asr", "restaurar.py", 1)]
    assert len(y) == len(a) and np.allclose(y, 0.2, atol=1e-6)
    # Del caché, sin volver a llamar a Sidon, y sin restos en la carpeta temporal.
    assert np.allclose(V.restaurar([a], aviso=lambda *_: None)[0], y)
    assert len(llamadas) == 1
    assert not list((V.carpeta_cache() / "tmp").glob("*.wav"))


def test_una_voz_de_estudio_pasa_por_sidon(monkeypatch):
    from nudos import ia
    llamadas = []
    monkeypatch.setattr(ia, "correr", _sidon_falso(llamadas))
    callar = {"aviso": lambda *_: None, "alineador": False}
    textos = ["Tira del firme.", "Aprieta el nudo."]
    normal = V.locuciones(textos, V.Voz("prueba", proveedor="falso"), **callar)
    estudio = V.locuciones(textos, V.Voz("prueba", proveedor="falso", restaurar=True), **callar)
    assert llamadas == [("qwen-asr", "restaurar.py", 2)]          # las dos en una sola llamada
    for a, b in zip(normal, estudio):
        assert a.huella != b.huella and len(a.audio) == len(b.audio)
        assert np.allclose(b.audio, a.audio * 0.5, atol=1e-4)
    assert not (V.carpeta_cache() / "restauradas").exists()        # decir guarda solo la locución
    assert "restaurar" not in V.Voz("prueba").huella()


def test_la_misma_voz_con_otra_semilla_es_otra_locucion():
    callar = {"aviso": lambda *_: None, "alineador": False}
    a = V.Voz("prueba", proveedor="falso")
    b = V.Voz("prueba", proveedor="falso", semilla=432)
    la, lb = V.decir([("Tira del firme.", a), ("Tira del firme.", b)], **callar)
    assert la.huella != lb.huella
    # Pedidas por separado dan las mismas: el caché distingue las dos.
    assert V.locuciones(["Tira del firme."], b, **callar)[0].huella == lb.huella


def test_paso_numero_n_de_m():
    # Gabriel eligió «Paso número dos de siete» (27 nov); se ve «Paso 2 de 7».
    ps = V.para_decir("Paso 2 de 7. Haz una gaza.")
    assert V.texto_dicho(ps) == "Paso número dos de siete. Haz una gaza."
    assert [p.texto for p in ps[:4]] == ["Paso", "2", "de", "7."]
    # Solo en el encabezado de un paso: lo demás se dice como antes.
    assert V.texto_dicho(V.para_decir("En el paso 3 hiciste un seno.")) == "En el paso tres hiciste un seno."
    assert V.texto_dicho(V.para_decir("Paso 21. Sube.")) == "Paso veintiuno. Sube."
    assert V.texto_dicho(V.para_decir("De 2 de 7 cuerdas.")) == "De dos de siete cuerdas."
    # «número dos» son dos trozos para el alineador, y caen en la misma palabra vista.
    assert V._trozos(ps[1].dicha) == 2


# --------------------------------------------------------------------------
# Los titubeos
# --------------------------------------------------------------------------
def _locucion(palabras, tiempos="alineados"):
    """Una locución con estas palabras: (texto, inicio, fin)."""
    ps = [V.Palabra(t, V.texto_dicho(V.para_decir(t)), a, b) for t, a, b in palabras]
    return V.Locucion(" ".join(t for t, _, _ in palabras), np.zeros(V.SR * 3, np.float32), ps, tiempos, "h")


def test_un_del_estirado_es_un_titubeo():
    # «el trabajo deeel as de guía»: el «del» de 0,40 s que oyó Gabriel.
    L = _locucion([("Ese", 0.0, 0.2), ("es", 0.2, 0.3), ("el", 0.3, 0.38), ("trabajo", 0.38, 0.78),
                   ("del", 0.78, 1.18), ("as", 1.18, 1.3), ("de", 1.3, 1.38), ("guía.", 1.38, 1.8)])
    assert [p.texto for p in V.titubeos(L)] == ["del"]
    # Dicho bien, nada; y sin tiempos alineados, tampoco se mide.
    bien = _locucion([("Ese", 0.0, 0.2), ("es", 0.2, 0.3), ("el", 0.3, 0.38), ("trabajo", 0.38, 0.78),
                      ("del", 0.78, 0.94), ("as", 0.94, 1.06), ("de", 1.06, 1.14), ("guía.", 1.14, 1.5)])
    assert V.titubeos(bien) == []
    assert V.titubeos(_locucion([("Ese", 0, 0.2), ("del", 0.2, 1.5), ("as.", 1.5, 2)], "estimados")) == []


def test_una_pausa_donde_el_texto_no_la_pide_es_un_titubeo():
    L = _locucion([("Tira", 0.0, 0.3), ("del", 0.3, 0.45), ("chicote,", 1.2, 1.6), ("y", 2.4, 2.5),
                   ("listo.", 2.5, 2.9)])
    # Tras «del» calla 0,75 s sin una coma: duda. Tras «chicote,» la coma pide la pausa.
    assert [p.texto for p in V.titubeos(L)] == ["del"]


def test_la_toma_que_titubea_se_repite_con_otra_semilla(monkeypatch):
    llamadas = []
    estirada = _locucion([("Tira", 0, 0.3), ("del", 0.3, 0.9), ("chicote", 0.9, 1.3), ("ya.", 1.3, 1.6)])
    bien = _locucion([("Tira", 0, 0.3), ("del", 0.3, 0.42), ("chicote", 0.42, 0.9), ("ya.", 0.9, 1.2)])

    def locuciones(textos, voz, proveedor=None, aviso=print, alineador=None):
        llamadas.append((tuple(textos), voz.semilla))
        return [estirada if (t == "Tira del chicote ya." and voz.semilla == 431) else bien for t in textos]
    monkeypatch.setattr(V, "locuciones", locuciones)
    voz = V.Voz("prueba", proveedor="falso")
    locs = V.locuciones_sin_titubeos(["Primero.", "Tira del chicote ya."], voz, aviso=lambda *_: None)
    assert locs[1] is bien and locs[0] is bien
    assert llamadas == [(("Primero.", "Tira del chicote ya."), 431), (("Tira del chicote ya.",), 432)]



def test_la_toma_que_no_se_entiende_tambien_se_repite(monkeypatch):
    primera = _locucion([("Forma", 0, 0.3), ("una", 0.3, 0.42), ("gaza", 0.42, 0.7), ("pequeña.", 0.7, 1.1)])
    segunda = _locucion([("Forma", 0, 0.3), ("una", 0.3, 0.42), ("gaza", 0.42, 0.7), ("pequeña.", 0.7, 1.1)])

    def locuciones(textos, voz, proveedor=None, aviso=print, alineador=None):
        return [primera if voz.semilla == 431 else segunda for _ in textos]
    monkeypatch.setattr(V, "locuciones", locuciones)
    vistos = []

    def revisar(textos, locs):
        # El reconocimiento oye «formo» en la primera toma y entiende la segunda.
        vistos.append([L is segunda for L in locs])
        return [L is segunda for L in locs]
    locs = V.locuciones_sin_titubeos(["Forma una gaza pequeña."], V.Voz("prueba", proveedor="falso"),
                                     revisar=revisar, aviso=lambda *_: None)
    assert locs[0] is segunda and vistos == [[False], [True]]
