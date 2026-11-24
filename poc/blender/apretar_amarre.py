"""Prueba de concepto de la fase 6 (T15): ¿se puede apretar un amarre con lo que ya existe?

Hoy un nudo de plantilla no se aprieta (nudos/apretar.py, apretado()). Aquí se aprieta el
último paso del amarre cuadrado con apretar() tal cual: los palos de la cruz sacan la cuerda
de ellos (Cruz.empujar) y nada cae, porque el amarre cuelga de los palos. Si cumple la
secuencia y los límites, deja el trabajo de su imagen para Blender, junto al de hoy.

Uso, desde la raíz del repositorio:
    .venv/Scripts/python poc/blender/apretar_amarre.py [rondas]
"""
from __future__ import annotations

import dataclasses
import json
import sys

import numpy as np

from nudos import RAIZ
from nudos.apretar import apretar
from nudos.plantillas.pasos import buscar as en_la_cruz, geometria
from nudos.libre import catmull_rom, remuestrear
from nudos.construir import construir
from nudos.imprimir import CELDA_MM, imagenes, px, trabajo
from nudos.spec import cargar


def main() -> int:
    rondas = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    spec = cargar("amarre-cuadrado")
    modelo = construir(spec)
    final = modelo.pasos[-1]
    # Las zonas de cada punto del último paso (en qué mapa de qué palo se buscan sus cruces),
    # como las calcula construir_paso() en nudos/plantillas/pasos.py.
    g = geometria(spec)
    c = g.cuerda(None)
    hito = spec.pasos[-1].hasta
    t = c.trazo(hito, spec.pasos[-2].hasta)
    D, ctrl = catmull_rom(t.puntos)
    X, h0, s_ctrl = remuestrear(D, ctrl)
    if len(X) != len(final.puntos):
        print("El último paso construido no es el de la plantilla.")
        return 1
    s = np.arange(len(X)) * h0
    tramo = np.clip(np.searchsorted(s_ctrl, s, side="right") - 1, 0, len(t.puntos) - 1)
    siguiente = np.minimum(tramo + 1, len(t.puntos) - 1)
    zonas = np.where(t.zonas[tramo] == t.zonas[siguiente], t.zonas[tramo], -1)
    cruz = g.solido

    def buscar(Y, hY, u):
        # Cada punto apretado conserva la zona de donde estaba, por su coordenada material.
        return en_la_cruz(Y, hY, zonas[np.clip(np.round(u / h0).astype(int), 0, len(zonas) - 1)], cruz)

    registro: list = []
    apretado = apretar(final, final.secuencia, rondas=rondas, anfitrion=cruz,
                       gravedad=lambda Y: np.zeros(len(Y), bool), buscar=buscar,
                       registro=registro)
    print("ronda  largo   separación  curvatura  estiramiento  cumple")
    for fila in registro:
        print("{:5d} {:7.1f} {:9.3f} {:10.3f} {:12.4f}  {}".format(*fila))
    if apretado is final:
        print("Ninguna ronda cumple la secuencia y los límites: el amarre queda como está.")
        return 1
    print(f"Largo: {final.medidas['largo']:.1f} → {apretado.medidas['largo']:.1f} diámetros; "
          f"penetración en los palos: {cruz.penetracion(apretado.puntos):.3f}")
    # El terminado por delante, con la cuerda apretada: la misma imagen de la ficha, con el
    # último paso cambiado por el apretado.
    ultimo = dataclasses.replace(modelo, pasos=modelo.pasos[:-1] + [apretado])
    img = next(i for i in imagenes(ultimo) if i.nombre == "terminado-frente")
    t = trabajo(img) | {"ancho": px(CELDA_MM[0]), "alto": px(CELDA_MM[1]),
                        "slug": "amarre-cuadrado", "nombre": "terminado-apretado"}
    ruta = RAIZ / "build" / "poc-blender" / "trabajos" / "amarre-cuadrado--terminado-apretado.json"
    ruta.write_text(json.dumps(t), encoding="utf-8")
    print(ruta.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
