"""Plantilla de la cabeza de turco, tejida sobre un tubo (anfitrión «tubo»).

El método es el del diseño de T8 en tasks/plan.md: la cuerda se teje vuelta por vuelta, y
cada vuelta pasa por encima o por debajo de lo que ya está, como queda en el nudo terminado.
Da tantas vueltas al tubo como cabos y hace tantos senos en cada borde como senos. Cada
pasada más sigue el mismo camino junto a la primera, y al final los dos extremos se esconden
bajo la banda de al lado (el remate).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Las medidas que acepta la plantilla, en letras. Solo las pasadas pueden ser una («una
# pasada»); cabos y senos empiezan en dos.
NUMEROS = {1: "una", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete"}
CABOS = (2, 5)
SENOS = (2, 7)
PASADAS = (1, 3)
_CAMPOS = {"tipo", "cabos", "senos", "pasadas"}


@dataclass(frozen=True)
class CabezaDeTurco:
    cabos: int     # vueltas al tubo
    senos: int     # senos en cada borde
    pasadas: int   # veces que la cuerda recorre el mismo camino

    tipo = "cabeza-de-turco"
    ANFITRION = "tubo"
    # Ningún paso tiene firme: el extremo corto se sujeta contra el tubo y se trabaja con la
    # parte larga, que lleva «Chicote» en su punta en todos los pasos.
    CON_FIRME: tuple[str, ...] = ()

    @classmethod
    def leer(cls, datos: dict, falla) -> CabezaDeTurco:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        numeros = {}
        for clave, (a, b) in (("cabos", CABOS), ("senos", SENOS), ("pasadas", PASADAS)):
            v = datos.get(clave)
            if not isinstance(v, int) or isinstance(v, bool) or not a <= v <= b:
                raise falla(f"«{clave}» es un número entero de {a} a {b}")
            numeros[clave] = v
        comun = math.gcd(numeros["cabos"], numeros["senos"])
        if comun != 1:
            raise falla(f"con {numeros['cabos']} cabos y {numeros['senos']} senos salen {comun} "
                        "cuerdas cerradas y no un nudo de una sola cuerda: cabos y senos no "
                        "pueden tener un divisor común aparte del 1")
        return cls(**numeros)

    @property
    def VARIANTES(self) -> dict[str, str]:
        """El error común que sabe construir, con el primer hito desde el que se ve: en la
        tercera vuelta, la cuerda empieza a tejer por encima en vez de por debajo y sigue
        alternando. Es el error del método de tres cabos, donde la segunda vuelta va toda por
        encima y la tercera empieza por debajo, sean cuantos sean los senos (2, 4, 5 o 7).
        Con otro número de cabos la segunda vuelta ya alterna, y no hay variante."""
        if self.cabos != 3 or por_vuelta(self.cabos, self.senos)[2][0]:
            return {}
        return {"empieza-por-encima": "vuelta-3-mitad"}

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, con su posición en la cuerda: la primera pasada por medias
        vueltas, cada pasada más por mitades y el remate. `vueltas` es lo mismo que la última
        vuelta y `pasadas` que la última pasada (con una sola, la última vuelta)."""
        out, k = {}, -1
        for i in range(1, self.cabos + 1):
            for nombre in (f"vuelta-{i}-mitad", f"vuelta-{i}"):
                k += 1
                out[nombre] = k
        out["vueltas"] = k
        for i in range(2, self.pasadas + 1):
            for nombre in (f"pasada-{i}-mitad", f"pasada-{i}"):
                k += 1
                out[nombre] = k
        out["pasadas"] = k
        out["remate"] = k + 1
        return out

    def medidas(self) -> dict[str, str]:
        return {"cabos": NUMEROS[self.cabos], "senos": NUMEROS[self.senos],
                "pasadas": NUMEROS[self.pasadas]}


# --------------------------------------------------------------------------
# El camino del centro
# --------------------------------------------------------------------------
def cruces_del_centro(cabos: int, senos: int, P: float = 1.0) -> list[tuple[float, float]]:
    """Los cruces del camino del centro de un cabo, cerrado, en la superficie desenrollada del
    tubo: para cada uno, dónde pasa la cuerda por primera y por segunda vez (t1 < t2), a lo
    largo del camino desde el ápice de un seno. P es el periodo de la onda; una vuelta al tubo
    mide P · senos / cabos, y la cuerda da tantas vueltas como cabos.

    Dos pasadas se cruzan donde están a la misma altura del tubo en el mismo lugar alrededor:
    a m vueltas una de otra (t2 = t1 + m vueltas). Como la onda es simétrica respecto de cada
    ápice y cambia de signo cada media onda, eso pasa donde t1 ≡ −d/2 (mód P/2), con d el
    corrimiento de la onda en m vueltas. No depende de la forma de la onda, y ningún cruce
    cae a menos de P / (2 · cabos) de un ápice. Son senos × (cabos − 1)."""
    vuelta = P * senos / cabos
    out = []
    for m in range(1, cabos):
        t = (-((m * vuelta) % P) / 2) % (P / 2)
        while t < (cabos - m) * vuelta - 1e-9:
            out.append((t, t + m * vuelta))
            t += P / 2
    return sorted(out)


def encima_del_centro(cabos: int, senos: int, P: float = 1.0) -> list[tuple[float, bool, int]]:
    """Las pasadas del camino del centro por sus cruces, en orden: (dónde, si va por encima,
    índice del cruce en cruces_del_centro). Alternan encima y debajo a lo largo de la cuerda;
    de las dos formas de alternar, la del método: el primer cruce que forma la segunda vuelta
    (el de su primera pasada por encima de lo que ya está) va por encima. Así, con tres cabos,
    la segunda vuelta va toda por encima de la primera."""
    cruces = cruces_del_centro(cabos, senos, P)
    vuelta = P * senos / cabos
    pasadas = sorted([(t1, k) for k, (t1, _) in enumerate(cruces)]
                     + [(t2, k) for k, (_, t2) in enumerate(cruces)])
    _, primero = min((t2, k) for k, (_, t2) in enumerate(cruces)
                     if numero_de_vuelta(t2, vuelta) == 2)
    fase = next(i for i, (t, k) in enumerate(pasadas) if k == primero and t == cruces[k][1]) % 2
    return [(t, i % 2 == fase, k) for i, (t, k) in enumerate(pasadas)]


def numero_de_vuelta(t: float, vuelta: float) -> int:
    """En qué vuelta, desde 1, está el punto t del camino. La vuelta k termina justo al volver
    al lugar donde empezó (t = k vueltas, incluido): con algunas medidas hay cruces
    exactamente ahí, y son de la vuelta que termina."""
    return max(1, math.ceil(t / vuelta - 1e-9))


def por_vuelta(cabos: int, senos: int) -> list[list[bool]]:
    """Para cada vuelta de la primera pasada, si va por encima en cada cruce que forma, en
    orden: los cruces que esa vuelta hace con lo que ya está."""
    cruces = cruces_del_centro(cabos, senos)
    vuelta = senos / cabos
    out = [[] for _ in range(cabos)]
    for t, arriba, k in encima_del_centro(cabos, senos):
        if t == cruces[k][1]:
            out[numero_de_vuelta(t, vuelta) - 1].append(arriba)
    return out
