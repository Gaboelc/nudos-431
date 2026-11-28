"""La página de prueba del amarre tallado, sin el navegador: el HTML y las copias en gris."""
import pytest
from PIL import Image

from nudos.prueba_tallado import IMAGENES, pagina


def _carpeta(base, nombre, color):
    d = base / nombre
    d.mkdir()
    for n, _ in IMAGENES:
        Image.new("RGB", (8, 9), color).save(d / f"{n}.png")
    return d


def test_pagina_sin_navegador(tmp_path):
    hoy, tal = _carpeta(tmp_path, "hoy", (200, 30, 30)), _carpeta(tmp_path, "tal", (30, 30, 200))
    fotos = []
    for i in range(4):
        f = tmp_path / f"f{i}.jpg"
        Image.new("RGB", (6, 8), (10, 200, 10)).save(f)
        fotos.append(f)
    color, gris = pagina(hoy, tal, tmp_path / "out", fotos, pdf=False)
    h = color.read_text(encoding="utf-8")
    assert "Hoy" in h and "Tallado" in h and h.count("<img") == 12
    assert "tal/paso-5.png" in h and "hoy/terminado-reverso.png" in h
    g = gris.read_text(encoding="utf-8")
    assert "gris/tallado-paso-5.png" in g
    with Image.open(tmp_path / "out" / "gris" / "tallado-paso-5.png") as im:
        assert im.mode == "L"


def test_falta_una_imagen(tmp_path):
    hoy = _carpeta(tmp_path, "hoy", (1, 2, 3))
    (hoy / "paso-3.png").unlink()
    with pytest.raises(FileNotFoundError):
        pagina(hoy, None, tmp_path / "out", [], pdf=False)
