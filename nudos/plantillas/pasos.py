"""Los pasos de un nudo de plantilla: cada uno es el comienzo de la cuerda entera.

La plantilla calcula una sola vez la cuerda entera (por ejemplo, nudos/plantillas/amarre.py).
Cada paso toma su comienzo, hasta el hito que dice `hasta`, y le agrega el resto: lo que sigue
de la cuerda, que sale del amarre y cae a la mesa. Así un cruce es el mismo en todos los
pasos y conserva su etiqueta. Después se construye como cerca del poste (nudos/anfitrion.py):

1. Una curva suave pasa por esos puntos y se muestrea cada H. Cada punto conserva la zona
   del tramo de donde viene: el palo de abajo, el de arriba, la cintura entre los dos o la
   mesa.
2. Los cruces se buscan zona por zona, cada una en su mapa: la superficie desenrollada de su
   cilindro (el palo de abajo, el de arriba y uno vertical alrededor del cruce, la cintura),
   donde encima es lo más lejos del eje, y en la mesa la proyección de siempre. Entre zonas
   no se buscan; ahí la comprobación es solo de separación.
3. La cuerda entera ya pasa por encima donde debe: la diagonal de cada ballestrinque va un
   diámetro más lejos del palo donde cruza, y los ahorcados van por fuera de las esquinas.
   Aquí solo se comprueba que los cruces de la cuerda son los del método.
4. Se relaja sin gravedad, como si la cuerda estuviera tensa, con choques entre tramos y sin
   entrar en los palos. El resto ya va trazado hasta la mesa.
"""
from __future__ import annotations

import math

import numpy as np

from ..anfitrion import PASADAS_LARGO, PENETRACION_MAX, Cruz
from ..cruces import Cruce, cruces_2d, emparejar
from ..libre import Resultado, TrazadoError, _resultado, catmull_rom, relajar, remuestrear
from ..spec import Spec
from .amarre import cuerda
from .trazo import ABAJO, ARRIBA, CINTURA, MESA

RADIO_CINTURA = 6.0   # radio con que se desenrolla la cintura; solo cambia la escala del mapa


def construir_pasos(spec: Spec) -> tuple[list[Resultado], list[str], list[tuple[int, tuple[str, ...]]]]:
    """Construye los pasos de un nudo de plantilla. Devuelve los resultados, las fallas de
    cada paso en orden y la secuencia del método en cada paso."""
    cruz = Cruz(spec.anfitrion)
    c = cuerda(spec.plantilla, cruz)
    resultados, fallas, secuencias, previo = [], [], [], None
    for paso in spec.pasos:
        hito = paso.hasta
        secuencias.append((paso.n, c.secuencias[hito]))
        try:
            r = construir_paso(paso.n, c, hito, previo, cruz)
        except TrazadoError as e:
            fallas.append(str(e))
        else:
            resultados.append(r)
            fallas.extend(r.fallas)
        previo = hito
    return resultados, fallas, secuencias


def construir_paso(n: int, c, hito: str, previo: str | None, cruz: Cruz) -> Resultado:
    """El paso n: la cuerda hasta `hito`, más el resto. Se resalta lo que agrega desde `previo`.
    `hito` puede ser también «vueltas» o «ahorcados», que son la última vuelta y el último ahorcado."""
    hito, previo = c.alias.get(hito, hito), c.alias.get(previo, previo)
    i = c.hitos[hito]
    resto = c.restos.get(hito)
    P = c.puntos[:i + 1] if resto is None else np.vstack([c.puntos[:i + 1], resto])
    Z = c.zonas[:i + 1] if resto is None else np.concatenate([c.zonas[:i + 1], np.full(len(resto), MESA)])
    D, ctrl = catmull_rom(P)
    X, h, s_ctrl = remuestrear(D, ctrl)
    s = np.arange(len(X)) * h
    tramo = np.clip(np.searchsorted(s_ctrl, s, side="right") - 1, 0, len(P) - 1)
    siguiente = np.minimum(tramo + 1, len(P) - 1)
    # La zona de cada punto: la del tramo de control donde cae, si sus dos extremos la
    # comparten; si no, ninguna (-1), y ese pedacito no entra en ningún mapa.
    zonas = np.where(Z[tramo] == Z[siguiente], Z[tramo], -1)
    secuencia = c.secuencias[hito]
    cruces, _ = buscar(X, h, zonas, cruz)
    declarados = len(secuencia) // 2
    if len(cruces) != declarados:
        raise TrazadoError(f"Paso {n}: la cuerda tiene {len(cruces)} cruces y el método "
                           f"declara {declarados}.")
    if cruces and emparejar(cruces, secuencia) is None:
        raise TrazadoError(f"Paso {n}: los cruces de la cuerda aparecen en otro orden que en "
                           "la secuencia del método.")
    s_fin = float(s_ctrl[i])
    s_ini = 0.0 if previo is None else float(s_ctrl[c.hitos[previo]])
    # La cuerda va tensa, como cuando se ata, y el resto ya está trazado sobre la mesa: no
    # cae nada. Si el resto cayera, tiraría del amarre y lo estiraría.
    Xr = relajar(X, h, anfitrion=cruz, gravedad=np.zeros(len(X), bool), pasadas_largo=PASADAS_LARGO)

    def medir(Y):
        pen = cruz.penetracion(Y)
        f = [] if pen <= PENETRACION_MAX else [
            f"Paso {n}: la cuerda entra {pen:.2f} diámetros en un palo; el máximo es "
            f"{PENETRACION_MAX}."]
        return {"penetracion_palos": pen}, f

    return _resultado(n, Xr, h, secuencia, (s_ini, s_fin),
                      buscar=lambda Y: buscar(Y, h, zonas, cruz), medir=medir)


def mapas(X, cruz: Cruz) -> dict[int, tuple[np.ndarray, np.ndarray, float | None]]:
    """Para cada zona, las coordenadas de cada punto en su mapa, su «altura» (lo que va
    encima es lo más alto) y el periodo de la segunda coordenada, si es periódica."""
    y_ab, a_ab, r_ab = cruz.abajo(X)
    x_ar, a_ar, r_ar = cruz.arriba(X)
    giro = np.unwrap(np.arctan2(X[:, 1], X[:, 0]))
    return {
        ABAJO: (np.column_stack([y_ab, np.unwrap(a_ab) * cruz.rb]), r_ab, 2 * math.pi * cruz.rb),
        ARRIBA: (np.column_stack([x_ar, np.unwrap(a_ar) * cruz.rb]), r_ar, 2 * math.pi * cruz.rb),
        CINTURA: (np.column_stack([X[:, 2], giro * RADIO_CINTURA]), np.hypot(X[:, 0], X[:, 1]),
                  2 * math.pi * RADIO_CINTURA),
        MESA: (X[:, :2], X[:, 2], None),
    }


def buscar(X, h, zonas, cruz: Cruz) -> tuple[list[Cruce], list[tuple[float, float]]]:
    """Los cruces de la cuerda, zona por zona, ordenados por su primera pasada, con la altura
    de sus dos pasadas."""
    s = np.arange(len(X)) * h
    cruces, alturas = [], []
    for zona, (M, alto, periodo) in mapas(X, cruz).items():
        validos = (zonas[:-1] == zona) & (zonas[1:] == zona)
        for sa, sb, seno, _ in cruces_2d(M, validos, h, periodo=periodo):
            p = (float(np.interp(sa, s, X[:, 0])), float(np.interp(sa, s, X[:, 1])))
            cruces.append(Cruce(sa, sb, p, seno))
            alturas.append((float(np.interp(sa, s, alto)), float(np.interp(sb, s, alto))))
    orden = sorted(range(len(cruces)), key=lambda k: cruces[k].sa)
    return [cruces[k] for k in orden], [alturas[k] for k in orden]
