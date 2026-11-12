"""Los pasos de un nudo de plantilla: cada uno es el comienzo de la cuerda entera.

La plantilla calcula una sola vez la cuerda entera (nudos/plantillas/amarre.py y
nudos/plantillas/cabeza_turco.py). Cada paso toma su comienzo, hasta el hito que dice `hasta`,
y le agrega lo que sale del nudo y cae a la mesa. Así un cruce es el mismo en todos los pasos
y conserva su etiqueta. Aquí se construye cada paso igual en las dos plantillas; lo propio de
cada una lo da su geometría (geometria()): el sólido del anfitrión, la cuerda y cómo buscar
sus cruces.

1. Una curva suave pasa por los puntos de control del paso y se muestrea cada H. Cada punto
   conserva la zona del tramo de donde viene: en el amarre, el palo de abajo, el de arriba, la
   cintura entre los dos o la mesa; en la cabeza de turco, el tubo o la mesa.
2. Los cruces se buscan zona por zona, cada una en su mapa: la superficie desenrollada de su
   cilindro, donde encima es lo más lejos del eje, y en la mesa la proyección de siempre. Entre
   zonas no se buscan; ahí la comprobación es solo de separación.
3. La cuerda entera ya pasa por encima donde debe. Aquí solo se comprueba que los cruces de la
   cuerda son los del método.
4. Se relaja sin gravedad, como si la cuerda estuviera tensa, con choques entre tramos y sin
   entrar en el anfitrión. Lo que cae a la mesa ya va trazado hasta ella.
"""
from __future__ import annotations

import math

import numpy as np

from ..anfitrion import PASADAS_LARGO, PENETRACION_MAX, Cruz, Tubo
from ..cruces import Cruce, cruces_2d, emparejar
from ..libre import Resultado, TrazadoError, _resultado, catmull_rom, relajar, remuestrear
from ..spec import Spec
from .amarre import AmarreCuadrado, cuerda
from .trazo import ABAJO, ARRIBA, CINTURA, MESA, TrazoDePaso

RADIO_CINTURA = 6.0   # radio con que se desenrolla la cintura; solo cambia la escala del mapa


def geometria(spec: Spec):
    """Lo propio de la plantilla del nudo: su sólido, su cuerda y cómo buscar sus cruces."""
    if isinstance(spec.plantilla, AmarreCuadrado):
        return _Amarre(spec)
    return _CabezaDeTurco(spec)


class _Amarre:
    """El amarre cuadrado sobre la cruz. `penetracion` es la clave de la medida y dónde entra."""
    penetracion = ("penetracion_palos", "en un palo")

    def __init__(self, spec: Spec):
        self.plantilla, self.solido = spec.plantilla, Cruz(spec.anfitrion)

    def cuerda(self, variante: str | None = None):
        return _CuerdaDeAmarre(cuerda(self.plantilla, self.solido, variante))

    def buscar(self, X, h, zonas, trazo: TrazoDePaso):
        return buscar(X, h, zonas, self.solido)


class _CuerdaDeAmarre:
    """La cuerda del amarre (amarre.Cuerda) con lo que pide construir_paso: el paso hasta un
    hito es su comienzo, más el resto que cae a la mesa."""

    def __init__(self, c):
        self.c, self.secuencias, self.alias = c, c.secuencias, c.alias

    def trazo(self, hito: str, previo: str | None) -> TrazoDePaso:
        c = self.c
        hito, previo = c.alias.get(hito, hito), c.alias.get(previo, previo)
        i = c.hitos[hito]
        resto = c.restos.get(hito)
        P = c.puntos[:i + 1] if resto is None else np.vstack([c.puntos[:i + 1], resto])
        Z = c.zonas[:i + 1] if resto is None else np.concatenate([c.zonas[:i + 1], np.full(len(resto), MESA)])
        return TrazoDePaso(P, Z, i, None if previo is None else c.hitos[previo])


class _CabezaDeTurco:
    """La cabeza de turco sobre el tubo. El ángulo de la onda se elige una vez para el nudo."""
    penetracion = ("penetracion_tubo", "en el tubo")

    def __init__(self, spec: Spec):
        from .cabeza_turco import elegir_angulo
        self.plantilla, self.solido = spec.plantilla, Tubo(spec.anfitrion)
        self.angulo = elegir_angulo(spec.plantilla, spec.anfitrion.radio)

    def cuerda(self, variante: str | None = None):
        from .cabeza_turco import Cuerda
        return Cuerda(self.plantilla, self.solido, self.angulo, variante)

    def buscar(self, X, h, zonas, trazo: TrazoDePaso):
        from .cabeza_turco import buscar_en_el_tubo
        return buscar_en_el_tubo(X, h, zonas, self.solido, trazo.giro, self.plantilla.senos)


def construir_pasos(spec: Spec) -> tuple[list[Resultado], list[str], list[tuple[int, tuple[str, ...]]]]:
    """Construye los pasos de un nudo de plantilla. Devuelve los resultados, las fallas de
    cada paso en orden y la secuencia del método en cada paso."""
    try:
        g = geometria(spec)
    except TrazadoError as e:
        return [], [str(e)], []
    c = g.cuerda()
    resultados, fallas, secuencias, previo = [], [], [], None
    for paso in spec.pasos:
        hito = paso.hasta
        secuencias.append((paso.n, c.secuencias[hito]))
        try:
            r = construir_paso(paso.n, g, c, hito, previo)
        except TrazadoError as e:
            fallas.append(str(e))
        else:
            resultados.append(r)
            fallas.extend(r.fallas)
        previo = hito
    return resultados, fallas, secuencias


def construir_error(spec: Spec) -> tuple[Resultado | None, list[str]]:
    """El error común de un nudo de plantilla: la cuerda de su variante del método
    (Error.variante) hasta el mismo hito que el paso del error. Se construye y se comprueba
    como un paso más, con la secuencia de cruces que la plantilla escribe para la variante,
    y resalta lo mismo que el paso bien hecho. Devuelve el resultado y sus fallas."""
    e = spec.error
    if e is None:
        return None, []
    try:
        g = geometria(spec)
    except TrazadoError as err:
        return None, [f"Error común: {err}"]
    c = g.cuerda(e.variante)
    previo = spec.pasos[e.paso - 2].hasta if e.paso > 1 else None
    try:
        r = construir_paso(e.paso, g, c, spec.pasos[e.paso - 1].hasta, previo)
    except TrazadoError as err:
        return None, [f"Error común: {err}"]
    return r, [f"Error común: {f}" for f in r.fallas]


def construir_paso(n: int, g, c, hito: str, previo: str | None) -> Resultado:
    """El paso n: la cuerda hasta `hito`, con lo que cae a la mesa. Se resalta lo que agrega
    desde `previo`. `hito` puede ser también un alias, como «vueltas»."""
    t = c.trazo(hito, previo)
    P, Z = t.puntos, t.zonas
    D, ctrl = catmull_rom(P)
    X, h, s_ctrl = remuestrear(D, ctrl)
    s = np.arange(len(X)) * h
    tramo = np.clip(np.searchsorted(s_ctrl, s, side="right") - 1, 0, len(P) - 1)
    siguiente = np.minimum(tramo + 1, len(P) - 1)
    # La zona de cada punto: la del tramo de control donde cae, si sus dos extremos la
    # comparten; si no, ninguna (-1), y ese pedacito no entra en ningún mapa.
    zonas = np.where(Z[tramo] == Z[siguiente], Z[tramo], -1)
    secuencia = c.secuencias[c.alias.get(hito, hito)]
    cruces, _ = g.buscar(X, h, zonas, t)
    declarados = len(secuencia) // 2
    if len(cruces) != declarados:
        raise TrazadoError(f"Paso {n}: la cuerda tiene {len(cruces)} cruces y el método "
                           f"declara {declarados}.")
    if cruces and emparejar(cruces, secuencia) is None:
        raise TrazadoError(f"Paso {n}: los cruces de la cuerda aparecen en otro orden que en "
                           "la secuencia del método.")
    s_fin = float(s_ctrl[t.fin])
    s_ini = 0.0 if t.inicio is None else float(s_ctrl[t.inicio])
    # La cuerda va tensa, como cuando se ata, y lo que cae ya está trazado sobre la mesa: no
    # cae nada. Si cayera, tiraría del nudo y lo estiraría.
    Xr = relajar(X, h, anfitrion=g.solido, gravedad=np.zeros(len(X), bool), pasadas_largo=PASADAS_LARGO)
    clave, donde = g.penetracion

    def medir(Y):
        pen = g.solido.penetracion(Y)
        f = [] if pen <= PENETRACION_MAX else [
            f"Paso {n}: la cuerda entra {pen:.2f} diámetros {donde}; el máximo es "
            f"{PENETRACION_MAX}."]
        return {clave: pen}, f

    r = _resultado(n, Xr, h, secuencia, (s_ini, s_fin),
                   buscar=lambda Y: g.buscar(Y, h, zonas, t), medir=medir)
    r.giro = t.giro
    return r


def mapas(X, cruz: Cruz) -> dict[int, tuple[np.ndarray, np.ndarray, float | None]]:
    """Para cada zona del amarre, las coordenadas de cada punto en su mapa, su «altura» (lo
    que va encima es lo más alto) y el periodo de la segunda coordenada, si es periódica."""
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
    """Los cruces de la cuerda del amarre, zona por zona, ordenados por su primera pasada, con
    la altura de sus dos pasadas."""
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
