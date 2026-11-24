"""T14b: renderiza los cuadros de un video en Blender, con la escena de poc/blender/escena.py.

Corre dentro de Blender, sin interfaz:
    blender --background --factory-startup --python poc/video/escena_video.py -- \
        --cuadros <npz> --salida <carpeta> [--anfitrion <json>] [--ancho 1280 --alto 720]
        [--muestras 64] [--orbita 0.35] [--desde 0 --hasta N]

`cuadros` es un .npz con un arreglo (N, 3) por cuadro (c0000, c0001…), la cuerda en
diámetros. En cada cuadro se rehace el tubo de la cuerda y se renderiza. La cámara encuadra
todos los cuadros juntos, con la vista «3d» de las fichas, y gira despacio (`orbita`, en
radianes a lo largo del video): un solo movimiento, como pide el método de elasthic.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "blender"))
import escena as E   # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    a = argparse.ArgumentParser()
    a.add_argument("--cuadros", required=True)
    a.add_argument("--salida", required=True)
    a.add_argument("--anfitrion")
    a.add_argument("--ancho", type=int, default=1280)
    a.add_argument("--alto", type=int, default=720)
    a.add_argument("--muestras", type=int, default=64)
    a.add_argument("--orbita", type=float, default=0.35)
    a.add_argument("--desde", type=int, default=0)
    a.add_argument("--hasta", type=int, default=None)
    a.add_argument("--total", type=int, default=None, help="cuadros del video, si el npz trae solo algunos")
    a.add_argument("--caja", help="otro npz para encuadrar (el de todos los cuadros)")
    args = a.parse_args(argv)
    datos = np.load(args.cuadros)
    claves = sorted(k for k in datos.files if k.startswith("c"))
    numeros = [int(k[1:]) for k in claves]       # el número de cada cuadro en el video
    cuadros = [datos[k] for k in claves]
    total = args.total or (max(numeros) + 1)
    para_caja = cuadros
    if args.caja:
        dc = np.load(args.caja)
        para_caja = [dc[k] for k in sorted(k for k in dc.files if k.startswith("c"))]
    anf = json.loads(Path(args.anfitrion).read_text(encoding="utf-8")) if args.anfitrion else None

    E.limpiar()
    escena = bpy.context.scene
    escena.render.resolution_x, escena.render.resolution_y = args.ancho, args.alto
    escena.render.resolution_percentage = 100
    base = E.material_trenza("trenza", E.COLORES["azul"])
    punta, _, _ = E.material("punta")
    bsdf = punta.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*E.lineal((27, 21, 23)), 1)
    bsdf.inputs["Roughness"].default_value = 0.45
    remate = E.material_simple("remate", (110, 22, 24), 0.55)
    E.anfitrion(anf)
    E.mesa()
    # La caja de todos los cuadros, con el formato que espera E.caja.
    modelo = {"encuadre": None, "anfitrion": anf, "pasos": [{"p": c.ravel().tolist()} for c in para_caja[::5] + [para_caja[-1]]]}
    B, alto = E.caja(modelo)
    polar, az = E.VISTAS["3d"]
    cam, centro, dist = E.camara(escena, B, alto, polar, az)
    E.luces(centro.x, centro.y, max(B[1] - B[0], B[3] - B[2]) / 2 + 2)
    escena.render.film_transparent = True
    escena.view_settings.view_transform = "Standard"
    escena.view_settings.look = "None"
    escena.view_settings.exposure = -0.55
    disp = E.gpu(escena)
    escena.cycles.samples = args.muestras
    escena.cycles.use_denoising = True
    escena.cycles.seed = 431
    escena.render.image_settings.file_format = "PNG"
    escena.render.image_settings.color_mode = "RGBA"
    Path(args.salida).mkdir(parents=True, exist_ok=True)
    hasta = len(cuadros) if args.hasta is None else min(args.hasta, len(cuadros))
    objetos = []
    t0 = time.time()
    for j in range(args.desde, hasta):
        f = numeros[j]
        for ob in objetos:
            datos_ob = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if datos_ob is not None and datos_ob.users == 0:
                bpy.data.meshes.remove(datos_ob)
        P = np.asarray(cuadros[j], float)
        L = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
        fin = 1 - E.REMATE / L
        ob, Ps, _ = E.tubo("cuerda", P, E.RADIO, [(0, 1.01, 0), (fin, 1.01, 1)])
        ob.data.materials.append(base)
        ob.data.materials.append(remate)
        t1 = E.tapa("punta-inicio", Ps[0], Ps[0] - Ps[1], E.RADIO, base)
        t2 = E.tapa("punta-fin", Ps[-1], Ps[-1] - Ps[-2], E.RADIO, punta)
        objetos = [ob, t1, t2]
        x = f / max(1, total - 1)
        g = az - args.orbita / 2 + args.orbita * x
        cam.location = centro + Vector((dist * math.sin(polar) * math.sin(g), -dist * math.sin(polar) * math.cos(g), dist * math.cos(polar)))
        cam.rotation_quaternion = (centro - cam.location).to_track_quat("-Z", "Y")
        escena.render.filepath = str(Path(args.salida) / f"cuadro-{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        if j % 25 == 0:
            print(f"cuadro {f}/{hasta}: {time.time() - t0:.0f} s con {disp}", flush=True)
    print(f"listo: {hasta - args.desde} cuadros en {time.time() - t0:.0f} s con {disp}", flush=True)


main()
