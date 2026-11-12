"""La hoja de revisión privada: la fuente junto a cada paso, sin copiar la fuente."""
from pathlib import Path

import pytest
from PIL import Image

from nudos import RAIZ
from nudos.revision import DESTINO, RevisionError, revision


@pytest.fixture
def entradas(tmp_path):
    """Una fuente de mentira para el as de guía: tres imágenes."""
    carpeta = tmp_path / "entradas" / "as-de-guia"
    carpeta.mkdir(parents=True)
    for nombre in ("fuente-01.png", "fuente-02.png", "fuente-03.jpg"):
        Image.new("RGB", (8, 8), "gray").save(carpeta / nombre)
    return tmp_path / "entradas"


@pytest.fixture
def hoja_con_pasos(tmp_path, entradas, modelo_as_de_guia):
    destino = tmp_path / "revision"
    (destino / "as-de-guia").mkdir(parents=True)
    (destino / "as-de-guia" / "pasos.yaml").write_text(
        "pasos:\n  1: [fuente-01.png]\n  2: [fuente-02.png, no-esta.png]\n"
        "error: [fuente-03.jpg]\n"
        "dudas:\n  2: El cruce 1 se ve tapado por la mano.\n", encoding="utf-8")
    pagina = revision(modelo_as_de_guia, destino, entradas)
    return pagina, pagina.read_text(encoding="utf-8")


def test_cada_paso_lleva_su_fuente_sus_dibujos_y_sus_secuencias(hoja_con_pasos, modelo_as_de_guia):
    pagina, texto = hoja_con_pasos
    for p, r in zip(modelo_as_de_guia.spec.pasos, modelo_as_de_guia.pasos):
        assert f"Paso {p.n}:" in texto
        assert f'src="paso-{p.n}-arriba.png"' in texto and f'src="paso-{p.n}-55.png"' in texto
        assert (pagina.parent / f"paso-{p.n}-arriba.png").is_file()
        assert " ".join(r.esperada) in texto
    assert "../../entradas/as-de-guia/fuente-01.png" in texto
    assert "Duda: El cruce 1 se ve tapado por la mano." in texto
    assert "Error común, junto al paso" in texto and "fuente-03.jpg" in texto


def test_una_imagen_que_no_existe_se_marca(hoja_con_pasos):
    _, texto = hoja_con_pasos
    assert "No existe no-esta.png en la fuente." in texto


def test_no_copia_la_fuente(hoja_con_pasos):
    pagina, _ = hoja_con_pasos
    hechos = {p.name for p in pagina.parent.iterdir()}
    assert not hechos & {"fuente-01.png", "fuente-02.png", "fuente-03.jpg"}
    assert all(n.startswith(("paso-", "error-")) for n in hechos - {"index.html", "pasos.yaml"})


def test_sin_pasos_yaml_muestra_toda_la_fuente(tmp_path, entradas, modelo_as_de_guia):
    texto = revision(modelo_as_de_guia, tmp_path / "revision", entradas).read_text(encoding="utf-8")
    assert "<h2>La fuente</h2>" in texto
    assert all(n in texto for n in ("fuente-01.png", "fuente-02.png", "fuente-03.jpg"))
    assert "no anotó imágenes de la fuente" in texto


def test_un_campo_desconocido_en_pasos_yaml(tmp_path, entradas, modelo_as_de_guia):
    carpeta = tmp_path / "revision" / "as-de-guia"
    carpeta.mkdir(parents=True)
    (carpeta / "pasos.yaml").write_text("imagenes: []\n", encoding="utf-8")
    with pytest.raises(RevisionError, match="campos desconocidos: imagenes"):
        revision(modelo_as_de_guia, tmp_path / "revision", entradas)


def test_la_revision_queda_fuera_de_git():
    assert DESTINO == RAIZ / "revision"
    ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "revision/" in ignorados and "entradas/" in ignorados
