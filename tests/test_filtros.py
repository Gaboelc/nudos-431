"""Registro de los dos filtros humanos en la especificación."""
import datetime as dt

import pytest
import yaml

from nudos import SPECS
from nudos.spec import SpecError, cargar, desde_datos


def con_filtros(filtros):
    with open(SPECS / "as-de-guia.yaml", encoding="utf-8") as f:
        datos = yaml.safe_load(f)
    datos["filtros"] = filtros
    return desde_datos(datos)


FILTRO_2 = {"filtro": 2, "fecha": dt.date(2026, 11, 7), "rol": "dirigente", "codigo": "P02",
            "resultado": "aprobado"}


def test_el_as_de_guia_paso_los_dos_filtros():
    filtros = {f.filtro: f for f in cargar("as-de-guia").filtros}
    assert set(filtros) == {1, 2}
    assert all(f.resultado == "aprobado" for f in filtros.values())
    assert filtros[2].rol and filtros[2].codigo == "P01"


@pytest.mark.parametrize("cambio, pista", [
    ({"codigo": "Juan"}, "código anónimo como P01, nunca un nombre"),
    ({"codigo": "JUAN"}, "código anónimo como P01, nunca un nombre"),
    ({"nombre": "Ana"}, "campos desconocidos: nombre"),
    ({"codigo": None}, "van el rol y el código"),
    ({"rol": None}, "van el rol y el código"),
    ({"fecha": "7 de noviembre"}, "AAAA-MM-DD"),
    ({"resultado": "bien"}, "aprobado o no aprobado"),
    ({"filtro": 3}, "es 1 o 2"),
    ({"ficha": "la de ayer"}, "commit de la ficha"),
])
def test_el_registro_rechaza_lo_que_no_va(cambio, pista):
    filtro = {k: v for k, v in {**FILTRO_2, **cambio}.items() if v is not None}
    with pytest.raises(SpecError, match=pista):
        con_filtros([filtro])


def test_el_filtro_1_solo_necesita_fecha_y_resultado():
    (f,) = con_filtros([{"filtro": 1, "fecha": dt.date(2026, 11, 7), "resultado": "aprobado"}]).filtros
    assert (f.rol, f.codigo) == (None, None)


def test_un_filtro_que_no_pasa_tambien_se_registra():
    (f,) = con_filtros([{**FILTRO_2, "resultado": "no aprobado"}]).filtros
    assert f.resultado == "no aprobado"
