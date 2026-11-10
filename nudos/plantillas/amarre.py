"""Plantilla del amarre cuadrado, sobre dos palos cruzados en ángulo recto (anfitrión «cruz»).

El método es el del diseño de T7 en tasks/plan.md: un ballestrinque en el palo de abajo,
las vueltas alrededor de los dos palos, los ahorcados entre los palos y un ballestrinque
de cierre en el palo de arriba.
"""
from __future__ import annotations

from dataclasses import dataclass

# Cuántas vueltas y ahorcados acepta la plantilla. El manual de la Tropa pide «tres o
# cuatro» de cada uno; el margen deja probar, y un número se escribe en letras.
NUMEROS = {2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis"}
_CAMPOS = {"tipo", "vueltas", "ahorcados", "inicio", "cierre"}
_CAMPOS_EXTREMO = {"poste", "lado"}
# De qué lado del otro palo puede ir un ballestrinque. El palo de abajo va hacia el fondo
# de la mesa, así que el de arriba lo parte en delante (hacia quien ata) y detrás; el de
# arriba va de izquierda a derecha, y el de abajo lo parte en izquierda y derecha.
LADOS = {"abajo": ("delante", "detras"), "arriba": ("izquierda", "derecha")}


@dataclass(frozen=True)
class Extremo:
    """Dónde va un ballestrinque: en qué palo y de qué lado del otro palo."""
    poste: str   # «abajo» o «arriba»
    lado: str    # uno de LADOS[poste]


@dataclass(frozen=True)
class AmarreCuadrado:
    vueltas: int     # alrededor de los dos palos
    ahorcados: int   # entre los palos, alrededor de las vueltas
    inicio: Extremo  # ballestrinque de inicio
    cierre: Extremo  # ballestrinque de cierre

    tipo = "amarre-cuadrado"
    ANFITRION = "cruz"
    # El error común que sabe construir, con el primer hito desde el que se ve.
    # Los ahorcados por encima del palo de arriba, en lugar de entre los palos.
    VARIANTES = {"ahorcados-por-fuera": "ahorcado-1"}

    @classmethod
    def leer(cls, datos: dict, falla) -> AmarreCuadrado:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        numeros = {}
        for clave in ("vueltas", "ahorcados"):
            v = datos.get(clave)
            if not isinstance(v, int) or isinstance(v, bool) or v not in NUMEROS:
                raise falla(f"«{clave}» es un número entero de {min(NUMEROS)} a {max(NUMEROS)}")
            numeros[clave] = v
        inicio = _extremo(datos.get("inicio"), "inicio", falla)
        cierre = _extremo(datos.get("cierre"), "cierre", falla)
        # Es el método del manual de la Tropa. Empezar en el palo de arriba se agrega
        # cuando un nudo lo necesite.
        if inicio.poste != "abajo" or cierre.poste != "arriba":
            raise falla("por ahora el ballestrinque de inicio va en el palo de abajo y el "
                        "de cierre en el de arriba")
        return cls(inicio=inicio, cierre=cierre, **numeros)

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, con su posición en la cuerda. `vueltas` es lo mismo que
        la última vuelta y `ahorcados` que el último ahorcado: así un paso que dice
        «hasta: vueltas» sigue valiendo si cambia el número de vueltas."""
        out = {"inicio-1": 0, "inicio": 1}
        k = 1
        for nombre, total in (("vuelta", self.vueltas), ("ahorcado", self.ahorcados)):
            for i in range(1, total + 1):
                k += 1
                out[f"{nombre}-{i}"] = k
            out[f"{nombre}s"] = k
        out["cierre-1"] = k + 1
        out["cierre"] = k + 2
        return out

    def medidas(self) -> dict[str, str]:
        return {"vueltas": NUMEROS[self.vueltas], "ahorcados": NUMEROS[self.ahorcados]}


def _extremo(datos, clave: str, falla) -> Extremo:
    if not isinstance(datos, dict) or set(datos) != _CAMPOS_EXTREMO:
        raise falla(f"«{clave}» lleva «poste» (abajo o arriba) y «lado»")
    poste, lado = datos["poste"], datos["lado"]
    if poste not in LADOS:
        raise falla(f"en «{clave}», «poste» es abajo o arriba")
    if lado not in LADOS[poste]:
        raise falla(f"en «{clave}», sobre el palo de {poste} «lado» es {' o '.join(LADOS[poste])}")
    return Extremo(poste, lado)
