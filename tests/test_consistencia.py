"""Consistencia de los cruces entre pasos."""
import numpy as np
import yaml

from nudos import SPECS
from nudos.construir import cruces_que_saltan
from nudos.cruces import consistencia
from nudos.libre import Resultado
from nudos.spec import desde_datos


def leer_as_de_guia():
    with open(SPECS / "as-de-guia.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def secuencias(datos):
    return [(p.n, p.secuencia) for p in desde_datos(datos).pasos]


def invertir(secuencia, etiqueta):
    cambio = {"O": "U", "U": "O"}
    return " ".join(t[:-1] + cambio[t[-1]] if t[:-1] == etiqueta else t
                    for t in secuencia.split())


def test_as_de_guia_es_consistente():
    assert consistencia(secuencias(leer_as_de_guia())) == []


def test_un_cruce_invertido_en_un_solo_paso_se_detecta():
    datos = leer_as_de_guia()
    datos["pasos"][4]["secuencia"] = invertir(datos["pasos"][4]["secuencia"], "2")
    errores = consistencia(secuencias(datos))
    assert len(errores) == 1
    assert errores[0].startswith("Cruce 2:")
    assert "por debajo en el paso 5" in errores[0]


def resultado(n, cruces):
    return Resultado(n=n, puntos=np.zeros((2, 3)), h=0.2, resaltado=None, cruces=cruces,
                     secuencia=[], esperada=[], medidas={})


def test_una_etiqueta_reutilizada_para_otro_cruce_se_detecta():
    fallas = cruces_que_saltan([resultado(1, {"1": (0.0, 0.0)}),
                                resultado(2, {"1": (6.0, 0.0)})])
    assert len(fallas) == 1
    assert "cruce 1" in fallas[0]


def test_un_cruce_que_se_mueve_poco_es_el_mismo():
    assert cruces_que_saltan([resultado(1, {"1": (0.0, 0.0)}),
                              resultado(2, {"1": (0.6, 0.3)})]) == []
