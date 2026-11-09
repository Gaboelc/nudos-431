"""El sitio: cada nudo con QR tiene su página y no se cuela nada de las fuentes."""
import dataclasses
import json
import re

import pytest

from nudos import URL_BASE
from nudos.exportar import (EXTENSIONES, SitioError, archivos_no_permitidos, construir_sitio,
                            datos_visor, leer_publicados)


@pytest.fixture(scope="module")
def sitio(tmp_path_factory, modelo_as_de_guia, modelo_ballestrinque, modelo_vuelta_de_escota):
    destino = tmp_path_factory.mktemp("sitio") / "sitio"
    slugs = construir_sitio(destino, modelos=[modelo_as_de_guia, modelo_ballestrinque,
                                              modelo_vuelta_de_escota])
    return destino, slugs


def test_cada_nudo_publicado_tiene_su_pagina(sitio):
    destino, slugs = sitio
    for slug in leer_publicados():
        assert slug in slugs
        assert (destino / slug / "index.html").is_file()


def test_falta_un_nudo_publicado(tmp_path, modelo_as_de_guia):
    with pytest.raises(SitioError, match="ballestrinque"):
        construir_sitio(tmp_path / "s", modelos=[modelo_as_de_guia],
                        publicados=["as-de-guia", "ballestrinque"])


def test_un_nudo_con_fallas_no_se_publica(tmp_path, modelo_as_de_guia):
    roto = dataclasses.replace(modelo_as_de_guia, fallas=["Paso 2: secuencia distinta"])
    with pytest.raises(SitioError, match="secuencia distinta"):
        construir_sitio(tmp_path / "s", modelos=[roto], publicados=[])
    assert not (tmp_path / "s").exists()


def test_el_sitio_no_tiene_imagenes_ni_archivos_extranos(sitio):
    destino, _ = sitio
    assert archivos_no_permitidos(destino) == []
    assert not any(p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
                   for p in destino.rglob("*"))
    assert ".png" not in EXTENSIONES


def test_no_borra_una_carpeta_que_no_es_un_sitio(tmp_path, modelo_as_de_guia):
    (tmp_path / "importante.txt").write_text("no me borres")
    with pytest.raises(SitioError, match="no la borro"):
        construir_sitio(tmp_path, modelos=[modelo_as_de_guia], publicados=[])
    assert (tmp_path / "importante.txt").exists()


def test_la_pagina_trae_los_pasos_de_la_especificacion(sitio, modelo_as_de_guia):
    destino, _ = sitio
    pagina = (destino / "as-de-guia" / "index.html").read_text(encoding="utf-8")
    titulos = re.findall(r'<span class="t">([^<]+)</span>', pagina)
    assert titulos == [p.titulo for p in modelo_as_de_guia.spec.pasos]
    datos = json.loads(re.search(r'<script type="application/json" id="modelo">(.*?)</script>',
                                 pagina, re.S).group(1))
    assert [p["n"] for p in datos["pasos"]] == list(range(1, 8))
    assert f'href="{URL_BASE}as-de-guia/"' in pagina


def test_las_rutas_de_la_pagina_existen(sitio):
    destino, _ = sitio
    pagina_dir = destino / "as-de-guia"
    pagina = (pagina_dir / "index.html").read_text(encoding="utf-8")
    for ruta in re.findall(r'(?:href|src)="(\.\./[^"]+)"', pagina):
        assert (pagina_dir / ruta).resolve().exists(), ruta
    escena = (destino / "recursos" / "escena.js").read_text(encoding="utf-8")
    for ruta in re.findall(r'from "(\./[^"]+)"', escena):
        assert (destino / "recursos" / ruta).exists(), ruta


def test_el_resaltado_cae_dentro_de_la_cuerda(modelo_as_de_guia):
    for paso in datos_visor(modelo_as_de_guia)["pasos"]:
        if paso["hl"] is not None:
            a, b = paso["hl"]
            assert 0 <= a < b <= 1
