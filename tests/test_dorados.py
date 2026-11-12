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
    diferencia = diferencias(malo, spec)
    assert diferencia[0].startswith(f"paso {ultimo}:") and "no es ningún paso" in diferencia[0]
    assert diferencia[-1].startswith("el nudo terminado es")


def test_otra_division_de_los_pasos_no_es_una_diferencia():
    """Gabriel, 12 nov: la división de los pasos no se exige."""
    spec = cargar("as-de-guia")
    sin_dos = dataclasses.replace(spec, pasos=spec.pasos[:2] + spec.pasos[3:5] + spec.pasos[6:])
    assert diferencias(sin_dos, spec) == []
    # Un paso más sin cruces al comienzo, y el error un paso más allá.
    repetido = dataclasses.replace(spec, pasos=spec.pasos[:1] + spec.pasos,
                                   error=dataclasses.replace(spec.error, paso=spec.error.paso + 1))
    assert diferencias(repetido, spec) == []


def test_sin_el_ultimo_paso_el_nudo_terminado_es_otro():
    spec = cargar("as-de-guia")
    sin_ultimo = dataclasses.replace(spec, pasos=spec.pasos[:-1])
    assert diferencias(sin_ultimo, spec)[0].startswith("el nudo terminado es")


def test_los_pasos_en_otro_orden_son_una_diferencia():
    spec = cargar("as-de-guia")
    p = spec.pasos
    cambiados = dataclasses.replace(spec, pasos=p[:3] + (p[4], p[3]) + p[5:])
    assert diferencias(cambiados, spec) == [
        f"paso {p[3].n}: {' '.join(renumerar([p[3].secuencia])[0][0])} no es ningún paso de la "
        f"especificación validada desde su paso {p[4].n}"]


def test_un_cruce_que_cambia_de_nombre_entre_pasos_es_una_diferencia():
    """En el último paso, 2 y 3 se llaman al revés: la secuencia renumerada es la misma,
    pero el cruce 2 de los pasos anteriores pasa a ser otro."""
    spec = cargar("as-de-guia")
    ultimo = spec.pasos[-1].n
    otro = {"2": "3", "3": "2"}
    malo = con_secuencias(spec, lambda n, s: tuple(otro.get(t[:-1], t[:-1]) + t[-1] for t in s)
                          if n == ultimo else s)
    assert any("en un paso anterior era el" in d for d in diferencias(malo, spec))


def test_el_error_comun_se_compara():
    spec = cargar("as-de-guia")
    otro = dataclasses.replace(spec, error=dataclasses.replace(spec.error, paso=4))
    assert diferencias(otro, spec)[0].startswith("el error común es")
    sin_error = dataclasses.replace(spec, error=None)
    assert diferencias(sin_error, spec) == ["el error común está en una sola de las dos"]
