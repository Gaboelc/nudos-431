"""Construir con procesos da exactamente lo mismo que construir en un solo proceso."""
import json
import sys

import pytest

from nudos import procesos
from nudos.construir import construir, datos_json
from nudos.spec import cargar


def test_nudos_procesos_dice_cuantos(monkeypatch):
    monkeypatch.setenv("NUDOS_PROCESOS", "3")
    assert procesos.cuantos() == 3
    monkeypatch.setenv("NUDOS_PROCESOS", "0")
    assert procesos.cuantos() == 1
    monkeypatch.setenv("NUDOS_PROCESOS", "muchos")
    with pytest.raises(ValueError, match="NUDOS_PROCESOS"):
        procesos.cuantos()


def test_el_video_usa_menos_procesos_si_se_le_pide(monkeypatch):
    # Las mallas y el armado del video usan hasta 8 procesos; con otras sesiones corriendo, el 4K
    # se quedaba sin memoria al armarse, y NUDOS_PROCESOS lo baja.
    import os

    from nudos import video
    monkeypatch.delenv("NUDOS_PROCESOS", raising=False)
    todos = video._procesos()
    assert todos == max(1, min(8, (os.cpu_count() or 4) - 2))
    monkeypatch.setenv("NUDOS_PROCESOS", "2")
    assert video._procesos() == min(2, todos)
    monkeypatch.setenv("NUDOS_PROCESOS", "64")
    assert video._procesos() == todos


def test_con_un_proceso_todo_va_en_linea(monkeypatch):
    monkeypatch.setenv("NUDOS_PROCESOS", "1")
    assert procesos.ejecutor(10) is procesos.EN_LINEA
    monkeypatch.setenv("NUDOS_PROCESOS", "4")
    assert procesos.ejecutor(1) is procesos.EN_LINEA   # una sola tarea: no vale abrir procesos


def test_un_programa_leido_de_stdin_va_en_un_proceso(monkeypatch):
    # Los procesos nuevos vuelven a importar el programa principal, y «<stdin>» no se puede.
    monkeypatch.setenv("NUDOS_PROCESOS", "4")
    monkeypatch.setattr(sys.modules["__main__"], "__file__", "<stdin>", raising=False)
    assert not procesos.en_paralelo()
    assert procesos.ejecutor(10) is procesos.EN_LINEA


def test_en_linea_vuelve_a_lanzar_el_error():
    f = procesos.EN_LINEA.submit(int, "no es un número")
    with pytest.raises(ValueError):
        f.result()


@pytest.mark.parametrize("slug", ["ocho", "ballestrinque"])
def test_con_procesos_da_lo_mismo_que_sin_ellos(slug, monkeypatch):
    # El ocho, con el error común, el reverso y los dos apretados; el ballestrinque, sobre el
    # poste. Se comparan como se guardan en modelo.json, con las fallas en el mismo orden.
    spec = cargar(slug)
    monkeypatch.setenv("NUDOS_PROCESOS", "4")
    con = construir(spec)
    monkeypatch.setenv("NUDOS_PROCESOS", "1")
    sin = construir(spec)
    assert json.dumps(datos_json(con)) == json.dumps(datos_json(sin))
    assert (con.apretado is con.pasos[-1]) == (sin.apretado is sin.pasos[-1])
