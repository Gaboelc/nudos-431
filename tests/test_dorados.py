"""Pruebas doradas de la skill nudo-nuevo: sus borradores tienen las secuencias validadas.

La comparación no depende de cómo se llama cada cruce (nudos/dorados.py)."""
import dataclasses

from nudos.dorados import diferencias, renumerar
from nudos.spec import cargar


def con_secuencias(spec, cambiar):
    """La especificación con otra secuencia en cada paso: cambiar(n, secuencia)."""
    pasos = tuple(dataclasses.replace(p, secuencia=cambiar(p.n, p.secuencia)) for p in spec.pasos)
    return dataclasses.replace(spec, pasos=pasos)


def otras_etiquetas(spec):
    """Las mismas secuencias con otras etiquetas: 1 pasa a ser 11, 2 a 12…"""
    nuevo = lambda t: str(int(t[:-1]) + 10) + t[-1]
    out = con_secuencias(spec, lambda n, s: tuple(map(nuevo, s)))
    error = dataclasses.replace(spec.error, invierte=tuple(str(int(e) + 10) for e in spec.error.invierte))
    return dataclasses.replace(out, error=error)


def test_renumerar_sigue_el_orden_en_que_aparecen():
    numeradas, numeros = renumerar([("7U", "3O"), ("7U", "3O", "7O", "3U")])
    assert numeradas == [("1U", "2O"), ("1U", "2O", "1O", "2U")]
    assert numeros == {"7": "1", "3": "2"}


def test_con_otras_etiquetas_no_hay_diferencias():
    for slug in ("as-de-guia", "vuelta-de-escota"):
        spec = cargar(slug)
        assert diferencias(otras_etiquetas(spec), spec) == []


def test_un_cruce_al_reves_es_una_diferencia():
    spec = cargar("as-de-guia")
    ultimo = spec.pasos[-1].n
    al_reves = {"O": "U", "U": "O"}
    malo = con_secuencias(spec, lambda n, s: tuple(t[:-1] + al_reves[t[-1]] if n == ultimo and t[:-1] == "1"
                                                   else t for t in s))
    (diferencia,) = diferencias(malo, spec)
    assert diferencia.startswith(f"paso {ultimo}:")


def test_otra_division_de_los_pasos_es_una_diferencia():
    spec = cargar("as-de-guia")
    sin_uno = dataclasses.replace(spec, pasos=spec.pasos[:2] + spec.pasos[3:])
    assert diferencias(sin_uno, spec)[0] == (
        f"el borrador tiene {len(spec.pasos) - 1} pasos y la especificación validada {len(spec.pasos)}")


def test_el_error_comun_se_compara():
    spec = cargar("as-de-guia")
    otro_paso = dataclasses.replace(spec, error=dataclasses.replace(spec.error, paso=spec.error.paso + 1))
    assert diferencias(otro_paso, spec) == [
        f"el error común va junto al paso {spec.error.paso + 1} en vez del {spec.error.paso}"]
    sin_error = dataclasses.replace(spec, error=None)
    assert diferencias(sin_error, spec) == ["el error común está en una sola de las dos"]
