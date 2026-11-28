"""La maqueta de las tarjetas del video (T22a): las secuencias de muestra, que la página lleve todo
adentro y que Edge la dibuje sin errores, con cada título de paso de los pilotos en dos líneas o menos."""
import json
import re

import pytest

from nudos import tarjetas as T
from nudos.imprimir import chrome
from nudos.spec import cargar

PILOTOS = ("as-de-guia", "amarre-cuadrado", "eslinga-de-andamio")


def test_la_muestra_horizontal_tiene_cada_tipo_de_tarjeta():
    tarjetas, saltos = T.horizontal(cargar("as-de-guia"), cargar("amarre-cuadrado"))
    tipos = {d["tipo"] for d in tarjetas}
    assert tipos == {"nombre", "materiales", "paso", "capitulo", "revisa", "error", "seguridad", "cierre"}
    assert {d.get("si", False) for d in tarjetas if d["tipo"] == "error"} == {True, False}
    assert any(d.get("mono") == "Otro error" for d in tarjetas)
    assert all(d["desde"] < d["hasta"] for d in tarjetas)
    # Los saltos van en orden y empiezan en 0.
    assert saltos[0] == ("Nombre", 0.0) and [t for _, t in saltos] == sorted(t for _, t in saltos)
    # Los capítulos con su color y su ícono.
    caps = [d for d in tarjetas if d["tipo"] == "capitulo"]
    assert {d["icono"] for d in caps} >= {"si", "no", "tienda"}
    cierre = next(d for d in tarjetas if d["tipo"] == "cierre")
    assert cierre["desde"] < cierre["golpe"] < cierre["final"] < cierre["hasta"]
    assert "As de guía español" in cierre["finales"][0]["texto"]


def test_la_muestra_vertical_tiene_los_subtitulos_en_orden():
    tarjetas, _ = T.vertical(cargar("as-de-guia"))
    sub = next(d for d in tarjetas if d["tipo"] == "subtitulos")
    ps = sub["palabras"]
    assert ps[0]["texto"] == "El" and all(p["desde"] < p["hasta"] for p in ps)
    assert all(a["hasta"] <= b["desde"] for a, b in zip(ps, ps[1:]))
    assert "Ya" in [p["texto"] for p in ps]
    # De a cuatro palabras como mucho, y cada frase empieza un trozo.
    from collections import Counter
    assert max(Counter(p["trozo"] for p in ps).values()) <= 4
    assert all(b["trozo"] == a["trozo"] + 1 for a, b in zip(ps, ps[1:]) if a["texto"].endswith("."))


def test_las_frases_de_la_seguridad():
    fs = T.frases("Uno dos tres. Cuatro cinco; seis: siete.", 1.0)
    assert [f["texto"] for f in fs] == ["Uno dos tres.", "Cuatro cinco;", "seis: siete."]
    assert fs[0]["desde"] == 1.0 and all(a["hasta"] == b["desde"] for a, b in zip(fs, fs[1:]))


def test_cada_paleta_tiene_todos_sus_colores_y_se_lee_bien():
    paletas = T.paletas()
    assert "sitio" in paletas and len(paletas) >= 5
    variables = set(paletas["sitio"]["css"])
    for clave, p in paletas.items():
        assert set(p["css"]) == variables, clave
        assert set(p["capitulos"]) == set(T.CAPITULOS_CON_COLOR), clave
        assert set(p["oscuros"]) <= set(T.CAPITULOS_CON_COLOR) and p["nombre"] and p["descripcion"]
        assert T.problemas_de_paleta(p) == [], clave


def test_una_paleta_que_no_se_lee_tiene_problemas():
    import copy
    p = copy.deepcopy(T.paletas()["sitio"])
    p["css"]["--tinta"] = "#c8c8c8"
    p["capitulos"]["errores"] = ["#ffd0d0", "#ffe0e0"]
    problemas = " ".join(T.problemas_de_paleta(p))
    assert "--tinta sobre el vidrio" in problemas and "capítulo errores" in problemas


def test_el_nombre_y_el_logo_del_grupo_van_en_el_nombre_y_en_el_cierre():
    assert T.GRUPO == "Grupo Guías y Scouts Huetares 431"
    for tarjetas in (T.horizontal(cargar("as-de-guia"), cargar("amarre-cuadrado"))[0], T.vertical(cargar("as-de-guia"))[0]):
        assert next(d for d in tarjetas if d["tipo"] == "nombre")["sub"] == T.GRUPO
        assert next(d for d in tarjetas if d["tipo"] == "cierre")["grupo"] == T.GRUPO
    assert T.LOGO.read_text(encoding="utf-8").lstrip().startswith("<?xml") and "<image" not in T.LOGO.read_text(encoding="utf-8")


def _maqueta(tmp_path, monkeypatch, slug="as-de-guia"):
    monkeypatch.setattr(T, "SALIDA", tmp_path)
    return T.maqueta(slug)


def test_la_maqueta_lleva_todo_adentro(tmp_path, monkeypatch):
    pagina = _maqueta(tmp_path, monkeypatch).read_text(encoding="utf-8")
    for marca in ("/*FUENTES*/", "/*TARJETAS_CSS*/", "/*LYGIA*/", "/*PALETAS*/", "/*TARJETAS_JS*/", "/*DATOS*/",
                  "__NOMBRE__"):
        assert marca not in pagina
    # Nada de afuera: ni guiones, ni hojas de estilo, ni fuentes por la red.
    assert not re.search(r"""(src|href)=["']https?:""", pagina) and "url(http" not in pagina
    assert "data:font/woff2;base64," in pagina and "window.lygia = { glsl }" in pagina
    assert "generative/snoise.glsl" in pagina
    # Las paletas y el logo del grupo, también adentro.
    assert "window.PALETAS = {" in pagina and "data:image/svg+xml;base64," in pagina


@pytest.fixture(scope="module")
def maqueta_en_edge(con_chrome, tmp_path_factory):
    import pytest as _pt
    mp = _pt.MonkeyPatch()
    carpeta = tmp_path_factory.mktemp("maqueta")
    mp.setattr(T, "SALIDA", carpeta)
    ruta = T.maqueta("as-de-guia")
    mp.undo()
    with chrome() as navegador:
        pagina = navegador.new_page(viewport={"width": 1400, "height": 1000})
        errores = []
        pagina.on("pageerror", lambda e: errores.append(str(e)))
        pagina.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pagina.goto(ruta.as_uri(), wait_until="load")
        pagina.wait_for_function("window.maqueta !== undefined", timeout=30000)
        yield pagina, errores


def test_la_maqueta_se_dibuja_sin_errores(maqueta_en_edge):
    pagina, errores = maqueta_en_edge
    datos = pagina.evaluate("DATOS")
    for formato in ("horizontal", "vertical"):
        for _, t in datos[formato]["saltos"]:
            pagina.evaluate(f"window.maqueta.ir({t + 1.2}, '{formato}')")
    # La tarjeta de capítulo dibuja su fondo de lygia en WebGL.
    pagina.evaluate("window.maqueta.ir(%f, 'horizontal')" % (datos["horizontal"]["saltos"][3][1] + 1.0))
    con_webgl = pagina.evaluate("!!document.querySelector('#horizontal .t-capitulo canvas').getContext('webgl')")
    assert errores == []
    assert con_webgl


def test_cada_paleta_se_dibuja_y_pone_sus_colores(maqueta_en_edge):
    pagina, errores = maqueta_en_edge
    paletas = T.paletas()
    datos = pagina.evaluate("DATOS")
    capitulo = datos["horizontal"]["saltos"][3][1] + 1.0
    cierre = datos["horizontal"]["saltos"][-1][1] + 2.0
    for clave, p in paletas.items():
        pagina.evaluate(f"window.maqueta.paleta('{clave}')")
        for t in (capitulo, cierre):
            pagina.evaluate(f"window.maqueta.ir({t}, 'horizontal')")
        tinta = pagina.evaluate("getComputedStyle(document.getElementById('horizontal')).getPropertyValue('--tinta').trim()")
        assert tinta == p["css"]["--tinta"], clave
    # En el cierre se ven el logo grande y el nombre del grupo.
    visto = pagina.evaluate("""() => { const c = document.querySelector('#horizontal .t-cierre');
        return [c.querySelector('.escudo-grupo').getBoundingClientRect().height > 50, c.querySelector('.grupo').textContent]; }""")
    assert visto == [True, T.GRUPO]
    pagina.evaluate(f"window.maqueta.paleta('{T.PALETA}')")
    assert errores == []


def test_la_paleta_de_los_videos_es_huetares(maqueta_en_edge):
    pagina, errores = maqueta_en_edge
    assert T.PALETA == "huetares" and pagina.evaluate("Tarjetas.PALETA") == T.PALETA
    tinta = pagina.evaluate("getComputedStyle(document.getElementById('horizontal')).getPropertyValue('--tinta').trim()")
    assert tinta == T.paletas()[T.PALETA]["css"]["--tinta"]
    # Sin el logo en la esquina (Gabriel, 28 nov): el logo solo va en el nombre y en el cierre.
    assert pagina.evaluate("document.querySelectorAll('#horizontal .capa > img').length") == 0
    assert errores == []


def test_cada_titulo_de_paso_cabe_en_dos_lineas(maqueta_en_edge):
    pagina, errores = maqueta_en_edge
    titulos = [p.titulo for slug in PILOTOS for p in cargar(slug).pasos]
    for formato in ("horizontal", "vertical"):
        pagina.evaluate(f"window.maqueta.ir({json.dumps(pagina.evaluate('DATOS')[formato]['saltos'][1][1] + 1.5)}, '{formato}')")
        lineas = pagina.evaluate("""([formato, titulos]) => {
            const e = document.querySelector(`#${formato} .t-paso .titulo`);
            const viejo = e.textContent;
            const out = titulos.map((t) => { e.textContent = t;
                return Math.round(e.offsetHeight / parseFloat(getComputedStyle(e).lineHeight)); });
            e.textContent = viejo;
            return out; }""", [formato, titulos])
        largos = [t for t, n in zip(titulos, lineas) if n > 2]
        assert largos == [], (formato, largos)
    assert errores == []
