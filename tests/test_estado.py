"""Estado de producción: el estado declarado no dice más que los hechos, y la tabla de los
35 nudos de la edición 1."""
import datetime as dt

import pytest
import yaml

from nudos import SPECS
from nudos.__main__ import main
from nudos.construir import construir
from nudos.estado import (SIN_ESPECIFICACION, faltan_para, leer_edicion, nudo, nudos,
                          probadores, ultimo_filtro)
from nudos.exportar import leer_publicados
from nudos.spec import ESTADOS, SpecError, cargar, desde_datos

DIA = dt.date(2026, 11, 7)


def as_de_guia(**cambios):
    """El as de guía con otros campos, sin escribir ningún archivo."""
    with open(SPECS / "as-de-guia.yaml", encoding="utf-8") as f:
        datos = yaml.safe_load(f)
    datos.update(cambios)
    return desde_datos({k: v for k, v in datos.items() if v is not None})


def filtro(n, resultado="aprobado", fecha=DIA, codigo="P02"):
    f = {"filtro": n, "fecha": fecha, "resultado": resultado}
    return f | ({"rol": "dirigente", "codigo": codigo} if n == 2 else {})


# --- La edición ------------------------------------------------------------

def test_la_edicion_tiene_35_nudos_sin_repetir():
    slugs = [s for tanda in leer_edicion().values() for s in tanda]
    assert len(slugs) == 35
    assert len(set(slugs)) == 35


def test_cada_especificacion_y_cada_nudo_publicado_estan_en_la_edicion():
    slugs = {s for tanda in leer_edicion().values() for s in tanda}
    assert {p.stem for p in SPECS.glob("*.yaml")} <= slugs
    assert set(leer_publicados()) <= slugs


# --- El campo ----------------------------------------------------------------

def test_sin_estado_es_borrador():
    assert as_de_guia(estado=None).estado == "borrador"


def test_el_estado_es_uno_de_los_cinco():
    with pytest.raises(SpecError, match="borrador, modelado, cuerda-ok, novato-ok o publicado"):
        as_de_guia(estado="listo")


# --- Lo que dicen los hechos ------------------------------------------------

def test_los_estados_declarados_coinciden_con_los_hechos():
    problemas = [f"{n.slug}: {p}" for n in nudos() for p in n.problemas]
    assert problemas == []


def test_los_nudos_del_piloto_estan_donde_se_espera():
    estados = {n.slug: n.declarado for n in nudos()}
    assert estados["as-de-guia"] == "publicado"
    for slug in ("ballestrinque", "vuelta-de-escota", "amarre-cuadrado"):
        assert estados[slug] == "cuerda-ok"   # el filtro 2 está en pausa desde el 9 nov
    assert estados["cabeza-de-turco"] == "borrador"   # su texto es provisional
    assert estados["ocho"] == SIN_ESPECIFICACION


def test_publicado_sin_los_dos_filtros_es_un_problema():
    spec = as_de_guia(filtros=[filtro(1)])
    assert faltan_para(spec, "cuerda-ok", ["as-de-guia"]) == []
    assert faltan_para(spec, "publicado", ["as-de-guia"]) == ["falta el filtro 2"]
    sin_ninguno = as_de_guia(filtros=None)
    assert faltan_para(sin_ninguno, "publicado", ["as-de-guia"]) == [
        "falta el filtro 1", "falta el filtro 2"]


def test_publicado_fuera_de_publicados_txt_es_un_problema():
    assert faltan_para(as_de_guia(), "publicado", []) == ["no está en publicados.txt"]
    assert faltan_para(as_de_guia(), "novato-ok", []) == []


def test_modelado_necesita_el_texto_de_la_ficha():
    spec = as_de_guia(usos=None, precauciones=None, error=None)
    assert faltan_para(spec, "modelado", []) == [
        "le falta a la ficha: usos, precauciones, error"]
    assert faltan_para(spec, "borrador", []) == []


def test_vale_el_ultimo_filtro():
    tarde = DIA + dt.timedelta(days=1)
    no_paso = as_de_guia(filtros=[filtro(1), filtro(1, "no aprobado", tarde)])
    assert ultimo_filtro(no_paso, 1).resultado == "no aprobado"
    assert "no pasó" in faltan_para(no_paso, "cuerda-ok", [])[0]
    paso = as_de_guia(filtros=[filtro(1, "no aprobado"), filtro(1, fecha=tarde)])
    assert faltan_para(paso, "cuerda-ok", []) == []


def test_el_estado_declarado_de_mas_sale_como_problema(monkeypatch):
    monkeypatch.setattr("nudos.estado.cargar", lambda slug: as_de_guia(filtros=[filtro(1)]))
    n = nudo("as-de-guia", "Piloto", ["as-de-guia"])
    assert n.alcanzado == "cuerda-ok"
    assert n.problemas == ("dice «publicado», pero falta el filtro 2",)


def test_un_probador_no_repite_el_filtro_2_de_un_nudo(monkeypatch):
    repetido = as_de_guia(estado="cuerda-ok", filtros=[
        filtro(1), filtro(2, "no aprobado"), filtro(2, fecha=DIA + dt.timedelta(days=1))])
    monkeypatch.setattr("nudos.estado.cargar", lambda slug: repetido)
    (problema,) = nudo("as-de-guia", "Piloto", ["as-de-guia"]).problemas
    assert problema.startswith("P02 hizo más de una vez el filtro 2")


def test_lo_que_bloquea_es_lo_que_falta_para_el_estado_siguiente():
    por_slug = {n.slug: n for n in nudos()}
    assert por_slug["ballestrinque"].bloquea == ("falta el filtro 2",)
    assert por_slug["as-de-guia"].bloquea == ()
    assert por_slug["cabeza-de-turco"].bloquea[0].startswith("le falta a la ficha:")
    assert por_slug["ocho"].bloquea == ()   # la tabla ya dice «sin especificación»


def test_los_probadores_y_los_nudos_que_conocen():
    assert probadores()["P01"] == ("joven de la Wak", ["as-de-guia"])


# --- Construye sin fallas ------------------------------------------------------

@pytest.mark.parametrize("slug", sorted(p.stem for p in SPECS.glob("*.yaml")))
def test_los_nudos_modelados_construyen_sin_fallas(slug, request):
    spec = cargar(slug)
    if ESTADOS.index(spec.estado) < ESTADOS.index("modelado"):
        pytest.skip(f"{slug} es un borrador")
    # Los nudos que ya tienen su modelo en conftest.py no se construyen otra vez.
    try:
        modelo = request.getfixturevalue(f"modelo_{slug.replace('-', '_')}")
    except pytest.FixtureLookupError:
        modelo = construir(spec)
    assert modelo.fallas == []


# --- La orden -----------------------------------------------------------------

def test_la_orden_muestra_los_35_nudos(capsys):
    assert main(["estado"]) == 0
    salida = capsys.readouterr().out
    assert salida.startswith("Edición 1: 35 nudos. 1 publicado, 3 cuerda-ok, 1 borrador, "
                             "30 sin especificación.")
    assert "Tanda 5: anfitriones especiales" in salida
    assert "P01 (joven de la Wak): as-de-guia" in salida
