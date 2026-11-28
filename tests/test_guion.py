"""El guion del video (T22a): el formato v1.14 (`voz` y `video` en la especificación), lo que
falta y el estilo, los tiempos estimados, los capítulos para YouTube, el reel y la hoja de revisión."""
import copy
import html
from dataclasses import replace

import pytest
import yaml

from nudos import SPECS
from nudos import guion as G
from nudos.spec import SpecError, cargar, desde_datos

PILOTOS = ("as-de-guia", "amarre-cuadrado", "eslinga-de-andamio")


def _datos(slug: str) -> dict:
    return yaml.safe_load((SPECS / f"{slug}.yaml").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# El formato
# --------------------------------------------------------------------------
def test_la_especificacion_lleva_la_voz_de_cada_paso_y_el_video():
    spec = cargar("as-de-guia")
    assert all(p.voz and p.voz != " ".join(p.texto.split()) for p in spec.pasos)
    assert spec.error.voz and spec.video.apertura and spec.video.cierre and spec.video.seguridad
    revisa = spec.video.verificacion
    assert [r.lado for r in revisa].count("detras") == 1 and all(r.etiqueta for r in revisa)
    assert spec.video.aplicacion.escena in G.ESCENAS


def test_la_voz_va_en_una_sola_linea():
    for slug in PILOTOS:
        spec = cargar(slug)
        assert all("\n" not in p.voz and "  " not in p.voz for p in spec.pasos)


def test_un_campo_desconocido_en_el_video_falla():
    datos = _datos("as-de-guia")
    datos["video"]["musica"] = "fogata"
    with pytest.raises(SpecError, match="video: campos desconocidos: musica"):
        desde_datos(datos)
    datos = _datos("as-de-guia")
    datos["video"]["verificacion"][0]["camara"] = "cerca"
    with pytest.raises(SpecError, match="verificacion 1: campos desconocidos: camara"):
        desde_datos(datos)


def test_mira_nombra_algo_del_nudo():
    datos = _datos("as-de-guia")
    datos["video"]["verificacion"][0]["mira"] = "no-existe"
    with pytest.raises(SpecError, match="el segmento «no-existe» no existe"):
        desde_datos(datos)
    datos["video"]["verificacion"][0]["mira"] = "gaza[40]"
    with pytest.raises(SpecError, match="no tiene el punto 40"):
        desde_datos(datos)
    # En un nudo de plantilla, un hito.
    datos = _datos("amarre-cuadrado")
    datos["video"]["verificacion"][0]["mira"] = "gaza"
    with pytest.raises(SpecError, match="es un hito de la plantilla"):
        desde_datos(datos)


def test_el_lado_es_delante_o_detras():
    datos = _datos("as-de-guia")
    datos["video"]["verificacion"][0]["lado"] = "arriba"
    with pytest.raises(SpecError, match="«lado» es uno de: delante, detras"):
        desde_datos(datos)


def test_las_medidas_de_la_plantilla_van_tambien_en_la_voz():
    datos = _datos("amarre-cuadrado")
    datos["pasos"][2]["voz"] = "Da más vueltas hasta tener {vueltas}."
    datos["video"]["cierre"] = "Con {ahorcados} ahorcados queda firme."
    spec = desde_datos(datos)
    assert spec.pasos[2].voz == "Da más vueltas hasta tener tres."
    assert spec.video.cierre == "Con tres ahorcados queda firme."


def test_sin_video_todo_sigue_igual():
    datos = _datos("ballestrinque")
    assert "video" not in datos
    spec = desde_datos(datos)
    from nudos.spec import Video
    assert spec.video == Video() and all(p.voz is None for p in spec.pasos)


def test_la_voz_no_cambia_el_modelo(modelo_as_de_guia):
    # `voz` y `video` no entran al modelo.json: con ellos o sin ellos, el mismo.
    from nudos.construir import datos_json
    from nudos.spec import Video
    spec = modelo_as_de_guia.spec
    sin = replace(spec, video=Video(), pasos=tuple(replace(p, voz=None) for p in spec.pasos),
                  error=replace(spec.error, voz=None))
    assert datos_json(replace(modelo_as_de_guia, spec=sin)) == datos_json(modelo_as_de_guia)


# --------------------------------------------------------------------------
# Lo que falta y el estilo
# --------------------------------------------------------------------------
def test_los_tres_pilotos_tienen_el_guion_completo():
    for slug in PILOTOS:
        assert G.problemas(cargar(slug)) == [], slug


def test_un_paso_sin_voz_es_un_problema_y_se_estima_con_la_ficha():
    datos = _datos("as-de-guia")
    del datos["pasos"][2]["voz"]
    spec = desde_datos(datos)
    assert "falta la «voz» de los pasos 3" in G.problemas(spec)
    parte = next(p for p in G.partes(spec) if p.clave == "paso-3")
    assert parte.falta and parte.voz.startswith("Paso 3 de 7. Acerca el chicote.")
    with pytest.raises(G.GuionError, match="pasos 3"):
        G.revisado(spec)


def test_el_estilo_se_revisa_en_todo_lo_que_dice():
    datos = _datos("as-de-guia")
    datos["pasos"][3]["voz"] = "Mete el chicote así, como un conejo… y listo."
    datos["video"]["verificacion"][1]["etiqueta"] = "Una etiqueta que no cabe junto a la marca"
    problemas = G.problemas(desde_datos(datos))
    texto = " ".join(problemas)
    assert "suspensivos" in texto and "así" in texto and "«como un conejo" in texto
    assert "etiquetas de más de 32 letras" in texto


def test_la_seguridad_de_la_ficha_tiene_que_ir_en_el_video():
    datos = _datos("as-de-guia")
    del datos["video"]["seguridad"]
    assert any("«video.seguridad»" in p for p in G.problemas(desde_datos(datos)))


def test_los_terminos_de_seccion_no_van_en_la_voz():
    from nudos.ficha import terminos_encontrados
    termino = next(t for t in ("patrulla", "Consejo de Wak") if terminos_encontrados(t))
    datos = _datos("as-de-guia")
    datos["video"]["apertura"] = f"Con tu {termino}, el as de guía sirve para todo."
    assert any("términos de sección" in p for p in G.problemas(desde_datos(datos)))


def test_la_escena_tiene_que_existir():
    datos = _datos("as-de-guia")
    datos["video"]["aplicacion"]["escena"] = "castillo"
    assert any("la escena «castillo» no existe" in p for p in G.problemas(desde_datos(datos)))


# --------------------------------------------------------------------------
# Los tiempos
# --------------------------------------------------------------------------
def test_los_capitulos_son_los_de_la_musica():
    from nudos import musica as M
    assert G.CAPITULOS == M.CAPITULOS and set(G.NOMBRES) == set(G.CAPITULOS) == set(G.ESCENA)


def test_la_voz_estimada_crece_con_lo_que_dice():
    corto = G.estimar("Tira fuerte.")
    largo = G.estimar("Paso 4. Mete el chicote por la gaza pequeña: entra por debajo y sale por encima.")
    assert 1.5 < corto < largo < 8.0
    # Medida en la voz de Gabriel: esta locución dura 6,24 s; el error medio del modelo es de 0,46 s.
    assert abs(largo - 6.24) < 1.2


def test_la_linea_de_tiempo_va_en_orden_y_respeta_los_minimos():
    spec = cargar("as-de-guia")
    lista, total = G.con_tiempos(spec)
    assert [p.capitulo for p in lista] == sorted((p.capitulo for p in lista), key=G.CAPITULOS.index)
    assert all(a.fin <= b.inicio for a, b in zip(lista, lista[1:]))
    caps = dict((c, (a, b)) for c, a, b in G.capitulos(lista, total))
    assert caps["materiales"][1] - caps["materiales"][0] >= G.MINIMO["materiales"]
    assert caps["cierre"][1] == total and total - lista[-1].fin == pytest.approx(G.PANTALLA_FINAL)
    # El video completo dura más que la voz sola, y no más de unos 4 min.
    assert sum(p.segundos for p in lista) < total < 240


def test_los_capitulos_de_youtube_duran_10_s_o_mas():
    for slug in PILOTOS:
        spec = cargar(slug)
        lista, total = G.con_tiempos(spec)
        yt = G.youtube(spec, G.capitulos(lista, total))
        assert yt[0] == (0.0, spec.nombre) and len(yt) >= 3
        inicios = [a for a, _ in yt] + [total]
        assert all(b - a >= G.MIN_YOUTUBE for a, b in zip(inicios, inicios[1:])), slug
        assert len({t for _, t in yt}) == len(yt)


def test_un_capitulo_corto_se_junta_con_el_de_antes():
    spec = cargar("as-de-guia")
    caps = [("apertura", 0.0, 8.0), ("materiales", 8.0, 12.0), ("pasos", 12.0, 70.0), ("seguridad", 70.0, 75.0),
            ("cierre", 75.0, 90.0)]
    assert G.youtube(spec, caps) == [(0.0, "As de guía"), (12.0, "Paso a paso"), (75.0, "Lo que sigue")]


def test_el_reel_dura_de_45_a_60_s_y_dice_cada_paso():
    for slug in PILOTOS:
        spec = cargar(slug)
        rl = G.reel_con_tiempos(spec)
        assert G.REEL[0] <= sum(p.dura for p in rl) <= G.REEL[1], slug
        assert [p.clave for p in rl][:1] == ["gancho"] and rl[-1].capitulo == "cierre"
        assert sum(p.capitulo == "pasos" for p in rl) == len(spec.pasos)
    rl = G.reel(cargar("as-de-guia"))
    assert rl[0].voz == "El as de guía hace una gaza fija en la punta de la cuerda."
    assert rl[-1].voz == "Ya sabes hacer el as de guía."
    assert any(p.voz == "El error más común: la gaza pequeña al revés." for p in rl)


def test_el_reel_cambia_el_gancho_y_el_cierre():
    datos = _datos("as-de-guia")
    datos["video"]["reel"] = {"gancho": "Una gaza que no se cierra.", "cierre": "Guárdalo para el campamento."}
    rl = G.reel(desde_datos(datos))
    assert rl[0].voz == "Una gaza que no se cierra." and rl[-1].voz == "Guárdalo para el campamento."


def test_las_medidas_reemplazan_lo_estimado():
    spec = cargar("as-de-guia")
    lista = G.partes(spec)
    G.medir(lista, [3.0] + [None] * (len(lista) - 1))
    assert lista[0].segundos == 3.0 and lista[0].medida and not lista[1].medida
    assert lista[1].segundos == pytest.approx(G.estimar(lista[1].voz))


# --------------------------------------------------------------------------
# La hoja
# --------------------------------------------------------------------------
def test_la_hoja_tiene_cada_parte_y_los_capitulos(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "BUILD", tmp_path)
    monkeypatch.setattr(G, "_medidas_en_cache", lambda textos: [None] * len(textos))
    ruta = G.hoja("as-de-guia")
    pagina = ruta.read_text(encoding="utf-8")
    spec = cargar("as-de-guia")
    for p in G.partes(spec):
        assert html.escape(p.voz) in pagina
    for nombre in G.NOMBRES.values():
        assert html.escape(nombre) in pagina
    assert "Capítulos para YouTube" in pagina and "0:00 As de guía" in pagina
    assert "El guion está completo" in pagina
    # Sin servidor: las fuentes van dentro.
    assert "data:font/woff2;base64," in pagina and "http://" not in pagina
    import json
    datos = json.loads((ruta.parent / "guion.json").read_text(encoding="utf-8"))
    assert datos["problemas"] == [] and len(datos["partes"]) == len(G.partes(spec))


def test_con_oir_cada_parte_suena_y_su_duracion_es_la_medida(tmp_path, monkeypatch):
    # Con la voz falsa y los instrumentos sintéticos: sin la tarjeta ni los modelos.
    from nudos import musica as M
    from nudos import voz as V
    # El guion del as de guía con frases cortas, para que la narración dure poco.
    datos = _datos("as-de-guia")
    for p in datos["pasos"]:
        p["voz"] = "Tira."
    datos["error"]["voz"] = "Al revés no sale."
    v = datos["video"]
    v.update(apertura="Hola.", materiales="Una cuerda.", seguridad="Revísalo.", cierre="Listo.")
    v["verificacion"] = v["verificacion"][:1]
    v["aplicacion"]["voz"] = "Un toldo."
    spec = desde_datos(datos)
    monkeypatch.setattr("nudos.spec.cargar", lambda slug: spec)
    monkeypatch.setattr(G, "BUILD", tmp_path)
    monkeypatch.setattr(G, "_medidas_en_cache", lambda textos: [None] * len(textos))
    monkeypatch.setenv("NUDOS_VOZ", str(tmp_path / "voz"))
    ruta = G.hoja("as-de-guia", oir=True, aviso=lambda *a: None, voz=V.Voz("prueba", proveedor="falso"),
                  instrumentos=M.Sintetico(), alineador=False, revisar=None)
    pagina = ruta.read_text(encoding="utf-8")
    partes = G.partes(spec)
    assert all((ruta.parent / f"{p.clave}.m4a").stat().st_size > 1000 for p in partes)
    assert (ruta.parent / "narracion.m4a").exists() and 'src="narracion.m4a"' in pagina
    import json
    datos = json.loads((ruta.parent / "guion.json").read_text(encoding="utf-8"))
    assert all(p["medida"] for p in datos["partes"])


def test_la_hoja_dice_lo_que_falta(tmp_path, monkeypatch):
    datos = _datos("eslinga-de-andamio")
    datos = copy.deepcopy(datos)
    del datos["video"]["cierre"]
    spec = desde_datos(datos)
    monkeypatch.setattr(G, "BUILD", tmp_path)
    monkeypatch.setattr(G, "_medidas_en_cache", lambda textos: [None] * len(textos))
    monkeypatch.setattr("nudos.spec.cargar", lambda slug: spec)
    pagina = G.hoja("eslinga-de-andamio").read_text(encoding="utf-8")
    assert "Le falta para el video" in pagina and "falta «video.cierre»" in pagina
