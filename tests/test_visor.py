"""El visor físico (T24): el material físico, el entorno, AgX y el postprocesado, solo en el visor."""
import functools
import http.server
import re
import threading
import time
from pathlib import Path

import pytest

from nudos import RAIZ
from nudos.exportar import archivos_no_permitidos, construir_sitio
from nudos.imprimir import chrome

SITIO = RAIZ / "sitio"


@pytest.fixture(scope="module")
def sitio_chico(tmp_path_factory, modelo_as_de_guia):
    destino = tmp_path_factory.mktemp("visor") / "sitio"
    construir_sitio(destino, [modelo_as_de_guia], publicados=["as-de-guia"])
    return destino


def _importes(archivo: Path) -> list[str]:
    texto = archivo.read_text(encoding="utf-8")
    return re.findall(r"""(?:from|import)\s+['"](\.{1,2}/[^'"]+)['"]""", texto)


def test_cada_modulo_del_visor_encuentra_lo_que_importa(sitio_chico):
    recursos = sitio_chico / "recursos"
    pendientes = [recursos / "visor.js"]
    vistos = set()
    while pendientes:
        m = pendientes.pop()
        if m in vistos:
            continue
        vistos.add(m)
        for ruta in _importes(m):
            destino = (m.parent / ruta).resolve()
            assert destino.is_file(), f"{m.name} importa {ruta}, que no está"
            pendientes.append(destino)
    nombres = {p.name for p in vistos}
    assert {"fisico.js", "escena.js", "GTAOPass.js", "RoomEnvironment.js", "lygia.js"} <= nombres
    assert archivos_no_permitidos(sitio_chico) == []


def test_las_imagenes_de_impresion_no_cargan_el_visor_fisico():
    # escena.js no importa fisico.js ni los complementos: la impresión (que no pasa «fisico»)
    # dibuja igual que antes de T24.
    for archivo in (RAIZ / "render" / "escena.js", RAIZ / "render" / "impresion.js"):
        importes = _importes(archivo)
        assert importes and not any("fisico" in i or "addons/" in i or "lygia" in i for i in importes)


def test_lygia_va_con_su_licencia_y_sin_archivos_glsl():
    lygia = SITIO / "vendor" / "lygia"
    assert (lygia / "LICENCIA.txt").read_text(encoding="utf-8").startswith("# The Prosperity Public License 3.0.0")
    assert not list(lygia.rglob("*.glsl"))
    texto = (lygia / "lygia.js").read_text(encoding="utf-8")
    for archivo in ("generative/snoise.glsl", "math/mod289.glsl", "color/dither/interleavedGradientNoise.glsl"):
        assert f'"{archivo}"' in texto
    assert "lygia" in (SITIO / "vendor" / "LEEME.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def servidor(sitio_chico):
    class Callado(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Callado, directory=str(sitio_chico)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/as-de-guia/"
    srv.shutdown()
    srv.server_close()


@pytest.mark.parametrize("consulta", ["", "?simple"])
def test_el_visor_carga_sin_errores(con_chrome, servidor, consulta):
    with chrome() as navegador:
        pagina = navegador.new_page(viewport={"width": 900, "height": 700})
        errores = []
        pagina.on("pageerror", lambda e: errores.append(str(e)))
        pagina.on("console", lambda m: errores.append(m.text)
                  if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
        pagina.goto(servidor + consulta, wait_until="load")
        pagina.wait_for_function("window.visorListo === true", timeout=60000)
        time.sleep(1.0)
        fisico = pagina.evaluate("() => window.visorFisico ? {post: window.visorFisico.conPostprocesado} : null")
        # lygia arma snoise con todas sus dependencias, en el mismo navegador.
        sin_resolver = pagina.evaluate("""async () => {
            const m = await import('../recursos/vendor/lygia/lygia.js');
            return (m.glsl('generative/snoise.glsl').match(/#include/g) || []).length; }""")
    assert errores == []
    assert sin_resolver == 0
    if consulta:
        assert fisico is None
    else:
        assert fisico is not None
