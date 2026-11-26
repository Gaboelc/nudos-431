"""Dibuja en Blender los cuadros de un video (T18). Corre dentro de Blender 5.2, sin interfaz, y
la llama nudos/video.py:

    blender --background --factory-startup --python render/blender/video.py -- --lote <lote.json>

Es la escena de las fichas (render/blender/escena.py, T16), armada una sola vez: el anfitrión,
la mesa, el cielo y los materiales de la cuerda. En cada cuadro cambian solo la malla de la
cuerda, la cámara y las luces, y Cycles guarda la escena entre un cuadro y el siguiente
(`use_persistent_data`), así que no vuelve a subir las texturas ni el anfitrión a la tarjeta.

El lote trae todos los cuadros que faltan. Python prepara la malla de cada uno en paralelo,
mientras Blender dibuja (nudos/video.py): Blender espera a que exista el npz de un cuadro antes
de dibujarlo, y escribe «listo: <k>» al terminar cada uno. El PNG va sin comprimir (en 4K pesa
casi lo mismo y se escribe mucho más rápido) y el denoiser va en la tarjeta: un video no
necesita que dos corridas den lo mismo bit a bit.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escena as e  # noqa: E402

ESPERA_MALLA = 900.0   # s: lo más que se espera la malla de un cuadro


def esperar(ruta: str) -> None:
    t0 = time.time()
    while not os.path.exists(ruta):
        if time.time() - t0 > ESPERA_MALLA:
            raise RuntimeError(f"no llegó la malla {ruta}")
        time.sleep(0.02)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", required=True)
    args = ap.parse_args(argv)
    lote = json.loads(open(args.lote, encoding="utf-8").read())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene
    e.gpu(escena)
    e.ajustes(escena, lote["ancho"], lote["alto"], lote["muestras"])
    if hasattr(escena.cycles, "denoising_use_gpu"):
        escena.cycles.denoising_use_gpu = True
    escena.render.image_settings.compression = 0
    escena.render.use_persistent_data = True
    # El cuadro entero de una vez, sin partirlo en pedazos de 2048 px (la escena cabe en la
    # tarjeta), y un muestreo adaptativo más permisivo: casi todo el cuadro es mesa blanca, y
    # Cycles deja de muestrear antes donde ya no hay ruido (Gabriel, 26 nov).
    ajustes = lote.get("cycles", {})
    escena.cycles.use_auto_tile = bool(ajustes.get("teselas", False))
    escena.cycles.use_adaptive_sampling = True
    escena.cycles.adaptive_threshold = float(ajustes.get("umbral_adaptativo", 0.01))

    e.vaciar()
    datos = json.loads(open(lote["escena"], encoding="utf-8").read())
    for i, m in enumerate(datos["mallas"]):
        e.malla_generica(i, m)
    e.mesa()
    color = lote.get("color", "azul")
    materiales = [e.material_trenza(f"trenza-0-{i}", cols)
                  for i, cols in enumerate((e.COLORES[color], e.AMBAR))] + [e.material_remate("remate-0")]
    fija = None          # el objeto de la cuerda: el mismo en todos los cuadros, con otra malla
    luz_previa = None
    for k, t in enumerate(lote["trabajos"]):
        inicio = time.time()
        c = t["cuerdas"][0]
        esperar(c["malla"])
        nueva = e.cuerda(0, c, materiales)
        if fija is None:
            fija = nueva
        else:
            vieja = fija.data
            fija.data = nueva.data
            bpy.data.objects.remove(nueva)
            bpy.data.meshes.remove(vieja)
        luz = (round(t["centro"][0], 4), round(t["centro"][1], 4), round(t["extension"], 4))
        if luz != luz_previa:
            e.luces(t["centro"][0], t["centro"][1], t["extension"] + 2)
            luz_previa = luz
        e.camara(escena, t["camara"])
        escena.render.filepath = t["salida"]
        bpy.ops.render.render(write_still=True)
        print(f"listo: {k} en {time.time() - inicio:.2f} s", flush=True)


if __name__ == "__main__":
    main()
