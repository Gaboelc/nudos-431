"""Dibuja en Blender los cuadros de un video (T18), con el aspecto de T20b. Corre dentro de
Blender 5.2, sin interfaz, y la llama nudos/video.py:

    blender --background --factory-startup --python render/blender/video.py -- --lote <lote.json>

La escena es la del aspecto elegido en T20a (render/blender/aspecto.py): el anfitrión, la mesa de
madera, el fondo, la luz y los materiales de cada cuerda (la trenza con geometría y la cinta del
chicote), armada una sola vez. En cada cuadro cambian solo la malla de cada cuerda, la cámara y el
foco, y Cycles guarda la escena entre un cuadro y el siguiente (`use_persistent_data`), así que no
vuelve a subir las texturas ni el anfitrión a la tarjeta.

El desenfoque de movimiento sale de la velocidad de cada vértice, que trae la malla (el atributo
«velocidad»), con el modificador de Geometry Nodes de `aspecto.mover_por_velocidad`.

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
import aspecto as asp  # noqa: E402
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
    escena.render.fps = int(lote.get("fps", asp.FPS))
    escena.frame_set(asp.CUADRO)
    motor = lote["motor"]
    asp.motor(escena, motor, lote.get("ajustes", {}))
    if motor == "CYCLES":
        # El cuadro entero de una vez, sin partirlo en pedazos (la escena cabe en la tarjeta).
        escena.cycles.use_auto_tile = False
    a = lote["aspecto"]
    asp.vista(escena, a)
    escena.render.resolution_x, escena.render.resolution_y = lote["ancho"], lote["alto"]
    escena.render.resolution_percentage = 100
    escena.render.image_settings.file_format = "PNG"
    escena.render.image_settings.color_mode = "RGB"
    escena.render.image_settings.color_depth = "8"
    escena.render.image_settings.compression = 0

    e.vaciar()
    datos = json.loads(open(lote["escena"], encoding="utf-8").read())
    asp.entorno(escena, a, datos, motor)
    materiales = [asp.materiales(a, c["estilo"], c["resaltado"], f"-{k}") for k, c in enumerate(lote["cuerdas"])]
    desenfoque = bool(lote.get("desenfoque", True))
    escena.render.use_motion_blur = desenfoque
    escena.render.motion_blur_shutter = float(lote.get("obturador", 0.5))
    if motor == "BLENDER_EEVEE":
        escena.eevee.motion_blur_steps = 1
    cuerdas = [None] * len(materiales)    # los objetos: los mismos en todos los cuadros, con otra malla
    for k, t in enumerate(lote["trabajos"]):
        inicio = time.time()
        for j, c in enumerate(t["cuerdas"]):
            esperar(c["malla"])
            cuerdas[j] = asp.poner_cuerda(f"cuerda-{j}", c["malla"], materiales[j], True, cuerdas[j])
            if desenfoque:
                asp.con_desenfoque(cuerdas[j])
        asp.camara(escena, t["camara"], t.get("foco"), a.get("fstop"))
        escena.render.filepath = t["salida"]
        bpy.ops.render.render(write_still=True)
        print(f"listo: {k} en {time.time() - inicio:.2f} s", flush=True)


if __name__ == "__main__":
    main()
