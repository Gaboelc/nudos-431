"""Las órdenes diagnostico y ampliar, que reemplazan los scripts sueltos de los borradores."""
import numpy as np
import pytest
import yaml
from PIL import Image

from nudos import SPECS
from nudos.__main__ import main
from nudos.diagnostico import ampliar, etiquetas, leer_pasos, radios
from nudos.libre import Reparto
from nudos.spec import cargar


def test_los_pasos_se_eligen_con_comas_y_guiones():
    assert leer_pasos("", 4) == [1, 2, 3, 4]
    assert leer_pasos("2,4-5", 6) == [2, 4, 5]
    with pytest.raises(ValueError, match="1 a 3"):
        leer_pasos("4", 3)


@pytest.mark.parametrize("slug", ["as-de-guia", "ballestrinque", "vuelta-de-escota", "nudo-aguja"])
def test_cada_punto_de_control_se_nombra_como_en_el_yaml(slug):
    """Libre, sobre el poste, con dos cuerdas y con el destorcedor: «seg[i]» es el punto i
    del segmento seg tal como está escrito."""
    spec = cargar(slug)
    with open(SPECS / f"{slug}.yaml", encoding="utf-8") as f:
        segmentos = yaml.safe_load(f)["segmentos"]
    nombres = etiquetas(SPECS / f"{slug}.yaml")
    for paso in spec.pasos:
        assert len(nombres[paso.n]) == len(paso.puntos)
        for nombre, punto in zip(nombres[paso.n], paso.puntos):
            seg, i = nombre[:-1].split("[")
            puntos = segmentos[seg]
            puntos = next(iter(puntos.values())) if isinstance(puntos, dict) else puntos
            assert list(punto) == pytest.approx(puntos[int(i)])


def test_el_radio_de_un_arco_es_su_radio():
    t = np.linspace(0, np.pi, 400)
    X = np.column_stack([1.5 * np.cos(t), 1.5 * np.sin(t)])
    h = float(np.linalg.norm(X[1] - X[0]))
    r = radios(X, h, Reparto.una(len(X)))
    assert r[np.isfinite(r)].min() == pytest.approx(1.5, rel=0.01)


def test_un_nudo_publicado_no_marca_fallas(capsys):
    assert main(["diagnostico", "simple", "--pasos", "2-3"]) == 0
    salida = capsys.readouterr().out
    assert "Paso 2:" in salida and "Paso 3:" in salida and "Paso 1:" not in salida
    assert "vuelta[" in salida          # los lugares van con el punto del YAML
    assert "\n!!" not in salida


def test_con_todo_mide_tambien_el_error_el_reverso_y_el_apretado(capsys):
    assert main(["diagnostico", "simple", "--pasos", "1", "--todo"]) == 0
    salida = capsys.readouterr().out
    for parte in ("Error común", "Nudo por detrás", "Apretado", "al apretar, la cuerda baja"):
        assert parte in salida


def test_un_nudo_de_plantilla_no_se_diagnostica(capsys):
    assert main(["diagnostico", "amarre-cuadrado"]) == 2
    assert "plantilla" in capsys.readouterr().err


def test_ampliar_copia_la_zona_fuera_de_la_fuente(tmp_path):
    fuente = tmp_path / "entrada" / "foto.png"
    fuente.parent.mkdir()
    Image.new("RGB", (400, 200), "white").save(fuente)
    salida = ampliar(fuente, tmp_path / "ampliadas", (0.5, 0.0, 1.0, 0.5), lado=600)
    assert salida.parent == tmp_path / "ampliadas"
    with Image.open(salida) as im:
        assert im.size == (600, 300)
    with pytest.raises(ValueError, match="fracciones"):
        ampliar(fuente, tmp_path / "ampliadas", (0.5, 0.0, 0.4, 1.0))
