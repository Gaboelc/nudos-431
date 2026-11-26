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
    assert V.texto_dicho(ps) == ("Paso cuatro de siete. Usa una cuerda de unos dos metros o un metro y medio "
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
    class SinTiempos(V.Falso):
        def generar(self, pedidos, aviso=print):
            return [(x, sr, None) for x, sr, _ in super().generar(pedidos, aviso)]
    L = V.locuciones(["Sube por la gaza, entra por debajo."], V.Voz("x"), proveedor=SinTiempos(),
                     aviso=lambda *_: None)[0]
    assert L.tiempos == "estimados"
    assert [p.texto for p in L.palabras] == ["Sube", "por", "la", "gaza,", "entra", "por", "debajo."]
    assert L.palabras[0].inicio < 0.4 and L.palabras[-1].fin <= L.segundos


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
    a = V.locuciones(["Haz una gaza.", "Sube por la gaza."], voz, proveedor=V.QwenTTS(), aviso=lambda *_: None)
    assert [len(c) for c in llamadas] == [1, 2]
    assert llamadas[0][0]["tipo"] == "disenar" and llamadas[0][0]["instruccion"] == "A calm voice."
    assert {t["tipo"] for t in llamadas[1]} == {"clonar"}
    assert all(t["referencia"] == llamadas[0][0]["salida"] for t in llamadas[1])
    assert all(t["texto_referencia"] == V.TEXTO_REFERENCIA for t in llamadas[1])
    assert a[0].tiempos == "estimados"
    # Otra vez: ni diseño ni clon.
    V.locuciones(["Haz una gaza.", "Sube por la gaza."], voz, proveedor=V.QwenTTS(), aviso=lambda *_: None)
    assert len(llamadas) == 2


def test_los_textos_de_la_prueba_salen_de_la_especificacion():
    from nudos.ficha import terminos_encontrados
    from nudos.prueba_sonido import textos_prueba
    t = textos_prueba("as-de-guia")
    assert [n for n, _ in t] == ["Apertura", "Paso 2", "Paso 4"]
    assert t[0][1].startswith("As de guía. Forma una gaza fija")
    assert t[1][1].startswith("Paso 2 de 7. Haz una gaza pequeña. ")
    assert not terminos_encontrados(" ".join(x for _, x in t))
    assert len(V.VOCES_PRUEBA) == 4 and len({v.nombre for v in V.VOCES_PRUEBA}) == 4
