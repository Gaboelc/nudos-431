"""T21a: las medidas de la calidad del movimiento (nudos/fisica/calidad.py)."""
from __future__ import annotations

import numpy as np

from nudos.fisica.calidad import BRINCO, SECO, episodios, largo, medir

FPS = 60


def cuerda(n=20, h=0.2):
    """Una cuerda recta de n nodos sobre el eje x."""
    return np.column_stack([np.arange(n) * h, np.zeros(n), np.zeros(n)])


def tiron_minimo(u):
    """El recorrido de tirón mínimo de 0 a 1 (velocidad y aceleración cero en las puntas)."""
    return 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5


def desplazada(distancias):
    """La cuerda llevada en y por cada distancia, un cuadro por distancia."""
    base = cuerda()
    return [base + [0.0, float(d), 0.0] for d in distancias]


def test_un_recorrido_de_tiron_minimo_es_suave():
    # 10 d en 2 s: velocidad máxima 9,4 d/s y aceleración máxima 14 d/s², como una mano.
    u = np.linspace(0, 1, 2 * FPS + 1)
    m = medir(desplazada(10 * tiron_minimo(u)), FPS)
    assert m["nodos"]["cambios"] == 0 and m["largo"]["variacion"] == 0
    assert m["brincos"] == 0 and m["punta"]["paradas_en_seco"] == 0
    assert 9.0 < m["velocidad"]["max"] < 9.6
    assert m["aceleracion"]["max"] < 20


def test_un_brinco_de_un_cuadro_se_ve():
    u = np.linspace(0, 1, 2 * FPS + 1)
    cuadros = desplazada(10 * tiron_minimo(u))
    cuadros[60] = cuadros[60].copy()
    cuadros[60][5, 2] += 0.3          # un nodo salta 0,3 d en un solo cuadro
    m = medir(cuadros, FPS)
    assert m["brincos"] == 1
    assert m["aceleracion"]["max"] > BRINCO


def test_un_cambio_de_velocidad_en_seco_se_ve():
    # De 5 a 2,5 d/s de un cuadro al siguiente: una parada en seco de la punta.
    v = np.where(np.arange(120) < 60, 5.0, 2.5)
    m = medir(desplazada(np.concatenate([[0.0], np.cumsum(v) / FPS])), FPS)
    assert m["punta"]["paradas_en_seco"] == 1
    # La misma frenada repartida en 0,3 s (unos 8 d/s²) no lo es.
    w = 5.0 - 2.5 * np.clip((np.arange(120) - 60) / (0.3 * FPS), 0, 1)
    m = medir(desplazada(np.concatenate([[0.0], np.cumsum(w) / FPS])), FPS)
    assert m["punta"]["paradas_en_seco"] == 0 and m["aceleracion"]["max"] < SECO


def test_cuando_cambia_la_cantidad_de_nodos_no_se_mide_entre_esos_cuadros():
    a = cuerda(20)
    cuadros = [a, a, cuerda(21), cuerda(21), cuerda(19)]
    m = medir(cuadros, FPS)
    assert m["nodos"] == {"min": 19, "max": 21, "cambios": 2}
    assert m["largo"]["variacion"] > 0.09
    # Solo dos pares tienen los mismos nodos, y no se mueven: ninguna aceleración se mide.
    assert m["aceleracion"] is None and m["quietos"] == 1.0


def test_las_medidas_no_dependen_de_los_cuadros_por_segundo():
    medidas = []
    for fps in (30, 60, 120):
        u = np.linspace(0, 1, 2 * fps + 1)
        medidas.append(medir(desplazada(10 * tiron_minimo(u)), fps))
    v = [m["velocidad"]["max"] for m in medidas]
    a = [m["aceleracion"]["max"] for m in medidas]
    assert max(v) - min(v) < 0.1
    assert max(a) - min(a) < 0.5


def test_las_paradas_y_las_fases():
    quieta = [cuerda()] * 30
    u = np.linspace(0, 1, 31)
    cuadros = quieta + desplazada(2 * tiron_minimo(u))[1:] + [desplazada([2.0])[0]] * 30
    fases = ["pausa"] * 30 + ["mover"] * 30 + ["pausa"] * 30
    m = medir(cuadros, FPS, fases=fases)
    assert m["paradas"] == 2
    assert m["fases"] == {"mover": 0.5, "pausa": 1.0}


def test_episodios_y_largo():
    assert episodios([False, True, True, False, True]) == 2
    assert episodios([]) == 0
    assert abs(largo(cuerda(11, 0.2)) - 2.0) < 1e-12
