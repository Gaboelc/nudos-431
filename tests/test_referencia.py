"""«referencia» y «comparar»: comprobar en una línea que un cambio no mueve los nudos hechos."""
import json
import shutil

from PIL import Image

from nudos.__main__ import main
from nudos.construir import construir, datos_json
from nudos.exportar import leer_publicados
from nudos.referencia import comparar, nudos_hechos, referencia
from nudos.spec import cargar


def _nudo(carpeta, slug, modelo=b'{"a":1}', color=(10, 20, 30), extra=None):
    (carpeta / slug / "impresion" / "prueba").mkdir(parents=True)
    (carpeta / slug / "modelo.json").write_bytes(modelo)
    Image.new("RGBA", (4, 3), color + (255,)).save(carpeta / slug / "impresion" / "paso-1.png")
    Image.new("RGB", (4, 3), color).save(carpeta / slug / "impresion" / "prueba" / "gris.png")
    if extra:
        Image.new("RGB", (4, 3), color).save(carpeta / slug / "impresion" / extra)


def test_dos_carpetas_iguales_dan_cero(tmp_path):
    for lado in ("antes", "despues"):
        _nudo(tmp_path / lado, "ocho")
        _nudo(tmp_path / lado, "simple")
    lineas = []
    assert comparar(tmp_path / "antes", tmp_path / "despues", avisar=lineas.append) == 0
    assert lineas[-1] == "2 de 2 nudos iguales."


def test_dice_que_cambio_y_cuanto(tmp_path):
    _nudo(tmp_path / "antes", "ocho")
    _nudo(tmp_path / "antes", "simple")
    _nudo(tmp_path / "antes", "rizo")
    _nudo(tmp_path / "despues", "ocho", modelo=b'{"a":2}')
    _nudo(tmp_path / "despues", "simple", color=(10, 20, 31), extra="sobra.png")
    _nudo(tmp_path / "despues", "nuevo")
    lineas = []
    assert comparar(tmp_path / "antes", tmp_path / "despues", avisar=lineas.append) == 1
    texto = "\n".join(lineas)
    assert "ocho: modelo.json DISTINTO" in texto
    assert "simple: modelo.json igual" in texto
    assert "paso-1.png: 12 píxeles, hasta 1 niveles" in texto      # en RGB, aunque sea RGBA
    assert "prueba/gris.png: 12 píxeles, hasta 1 niveles" in texto
    assert "sobra.png: sobra" in texto
    assert "rizo: falta en" in texto
    assert "Sin referencia (nuevos): nuevo" in texto
    assert "0 de 3 nudos iguales." in texto


def test_avisa_si_el_navegador_cambio(tmp_path):
    for lado, version in (("antes", "157.0.1"), ("despues", "158.0.4")):
        _nudo(tmp_path / lado, "ocho")
        (tmp_path / lado / "navegador.txt").write_text(version + "\n", encoding="utf-8")
    lineas = []
    assert comparar(tmp_path / "antes", tmp_path / "despues", avisar=lineas.append) == 0
    assert any("navegadores distintos (157.0.1 y 158.0.4)" in linea for linea in lineas)
    (tmp_path / "despues" / "navegador.txt").write_text("157.0.1\n", encoding="utf-8")
    lineas = []
    comparar(tmp_path / "antes", tmp_path / "despues", avisar=lineas.append)
    assert not any("navegadores" in linea for linea in lineas)


def test_una_carpeta_que_no_es_referencia(tmp_path):
    lineas = []
    assert comparar(tmp_path, tmp_path, avisar=lineas.append) == 1
    assert "referencia" in lineas[0]


def test_los_nudos_hechos_incluyen_los_publicados():
    hechos = nudos_hechos()
    assert set(leer_publicados()) <= set(hechos)
    assert all(cargar(s).estado != "borrador" for s in hechos)


def test_referencia_imprime_fuera_de_build_y_reimprimir_arregla(con_chrome, tmp_path):
    antes, despues = tmp_path / "antes", tmp_path / "despues"
    assert referencia(antes, ["simple"], avisar=lambda _: None) == []
    texto = json.dumps(datos_json(construir(cargar("simple"))), ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")
    assert (antes / "simple" / "modelo.json").read_bytes() == texto
    assert (antes / "simple" / "impresion" / "prueba.pdf").is_file()
    assert (antes / "navegador.txt").read_text(encoding="utf-8").strip()
    shutil.copytree(antes, despues)
    assert main(["comparar", str(antes), str(despues)]) == 0
    # Un píxel distinto, como el que a veces dibuja el navegador cargado.
    paso = next((despues / "simple" / "impresion").glob("paso-*.png"))
    with Image.open(paso) as im:
        im = im.convert("RGB")
        r, g, b = im.getpixel((0, 0))
        im.putpixel((0, 0), (r ^ 1, g, b))
        im.save(paso)
    lineas = []
    assert comparar(antes, despues, avisar=lineas.append) == 1
    assert any("1 píxeles, hasta 1 niveles" in linea for linea in lineas)
    assert comparar(antes, despues, reimprimir=True, avisar=lineas.append) == 0
