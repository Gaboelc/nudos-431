"""Dibuja en Blender las imágenes de impresión de un nudo (T16). Corre dentro de Blender 5.2,
sin interfaz, y la llama nudos/blender.py:

    blender --background --factory-startup --python render/blender/escena.py -- --lote <lote.json>

El lote trae el tamaño, las muestras y, por cada imagen, la escena que exportó render/escena.js
(la cámara y las mallas del anfitrión, de las tapas y de los dedos), la malla de cada cuerda
(un npz que arma nudos/blender.py, con la sección aplastada de T15g) y la ruta de salida. Cada
imagen sale en RGBA: la mesa es un receptor de sombras y el fondo, transparente.

La escena es la de la prueba de concepto (T14b, rama poc/render-motor), que Gabriel aprobó en el
punto de control E: Cycles en la tarjeta, la trenza de render/escena.js con relieve, la luz de
escena.js hecha luces de área y la vista «Standard». Para que imprimir dos veces dé lo mismo, la
semilla es fija y el denoiser corre en la CPU.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

SEMILLA = 431
EXPOSICION = -0.55     # con «Standard»: AgX lavaba el azul de la marca (T14b)
TRENZA_LADO = 1024
# Los colores de render/escena.js: claro, medio y oscuro de la trenza, y el hilo trazador.
COLORES = {
    "azul": [(118, 156, 238), (42, 88, 200), (12, 30, 86), (196, 36, 44)],
    "crema": [(255, 250, 238), (236, 225, 198), (138, 124, 96), (196, 36, 44)],
}
AMBAR = [(255, 214, 140), (222, 140, 34), (92, 46, 6), (150, 30, 30)]


def lineal(c):
    """sRGB 0-255 a lineal 0-1."""
    c = np.asarray(c, dtype=float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def hex_lineal(h):
    h = h.lstrip("#")
    return lineal([int(h[i:i + 2], 16) for i in (0, 2, 4)])


# --------------------------------------------------------------------------
# Cycles y la escena vacía
# --------------------------------------------------------------------------
def gpu(escena):
    """Cycles en la tarjeta, con OptiX si está; si no, en la CPU."""
    escena.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for tipo in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = tipo
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == tipo for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == tipo
            escena.cycles.device = "GPU"
            return tipo
    escena.cycles.device = "CPU"
    return "CPU"


def vaciar():
    for col in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for x in list(col):
            col.remove(x)


def ajustes(escena, ancho, alto, muestras):
    escena.render.resolution_x, escena.render.resolution_y = ancho, alto
    escena.render.resolution_percentage = 100
    escena.cycles.samples = muestras
    escena.cycles.seed = SEMILLA
    escena.cycles.use_animated_seed = False
    escena.cycles.use_denoising = True
    escena.cycles.denoiser = "OPENIMAGEDENOISE"
    if hasattr(escena.cycles, "denoising_use_gpu"):
        escena.cycles.denoising_use_gpu = False
    escena.render.film_transparent = True
    escena.view_settings.view_transform = "Standard"
    escena.view_settings.look = "None"
    escena.view_settings.exposure = EXPOSICION
    escena.render.image_settings.file_format = "PNG"
    escena.render.image_settings.color_mode = "RGBA"
    escena.render.image_settings.color_depth = "8"


# --------------------------------------------------------------------------
# Materiales
# --------------------------------------------------------------------------
def material(nombre):
    m = bpy.data.materials.new(nombre)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    return m, m.node_tree.nodes, m.node_tree.links


def imagen(nombre, rgba, no_color=False):
    h, w, _ = rgba.shape
    im = bpy.data.images.new(nombre, w, h, alpha=True, float_buffer=True)
    im.pixels.foreach_set(rgba.astype(np.float32).ravel())
    if no_color:
        im.colorspace_settings.name = "Non-Color"
    im.pack()
    return im


_TRENZAS = {}


def trenza(top, mid, low, tracer, S=TRENZA_LADO):
    """texturasTrenza de render/escena.js, con numpy: 16 hilos, 2 sobre 2, y el hilo trazador.
    x avanza a lo largo de la cuerda (un mosaico cada π diámetros) e y da la vuelta. Devuelve el
    color (lineal) y el alto, en RGBA."""
    clave = (tuple(top), tuple(mid), tuple(low), tuple(tracer), S)
    if clave in _TRENZAS:
        return _TRENZAS[clave]
    v, u = np.meshgrid((np.arange(S) + 0.5) / S, (np.arange(S) + 0.5) / S, indexing="ij")
    pa, pb = 8 * v + 8 * u, 8 * v - 8 * u
    i, j = np.floor(pa), np.floor(pb)
    fa, fb = pa - i, pb - j
    m = np.mod(i + j, 4)
    es_a = m < 2
    across = np.where(es_a, fa, fb)
    along = np.where(es_a, (m + fb) / 2, (m - 2 + fa) / 2)
    prof = np.sqrt(np.maximum(0, 1 - (2 * across - 1) ** 2))
    ends = np.abs(np.sin(np.pi * along)) ** 0.55
    yarn = 0.9 + 0.1 * np.cos(across * np.pi * 12)
    k = prof * (0.3 + 0.7 * ends) * yarn
    T, M, L, R = (np.asarray(c, float) / 255 for c in (top, mid, low, tracer))
    tr = es_a & (np.mod(i, 8) == 0) & (np.abs(across - 0.5) < 0.2) & (np.mod(np.floor(j / 4), 2) == 0)
    base = np.where(tr[..., None], R, M)
    alto_c = np.where(tr[..., None], np.minimum(1, R * 1.25), T)
    t1 = np.minimum(1, k / 0.55)[..., None]
    t2 = np.maximum(0, (k - 0.55) / 0.45)[..., None]
    a = L + (base - L) * t1
    srgb = a + (alto_c - a) * t2 * 0.6
    color = lineal(np.round(255 * srgb))
    rgba = np.concatenate([color, np.ones((S, S, 1))], axis=2)
    alto = np.repeat(np.minimum(1, k)[..., None], 4, axis=2)
    alto[..., 3] = 1
    _TRENZAS[clave] = (rgba, alto)
    return rgba, alto


def material_trenza(nombre, colores):
    """Principled con la trenza en color y en relieve, por la UV de la malla de la cuerda."""
    rgba, alto = trenza(*colores)
    m, n, l = material(nombre)
    n.clear()
    salida = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    uv = n.new("ShaderNodeUVMap")
    tc = n.new("ShaderNodeTexImage"); tc.image = imagen(nombre + "-color", rgba)
    th = n.new("ShaderNodeTexImage"); th.image = imagen(nombre + "-alto", alto, no_color=True)
    tc.interpolation = th.interpolation = "Cubic"
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.14
    l.new(uv.outputs["UV"], tc.inputs["Vector"])
    l.new(uv.outputs["UV"], th.inputs["Vector"])
    l.new(th.outputs["Color"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.8
    # Sin brillo de tela: deja un halo claro en el borde que borra el recorte de los cruces.
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    # Un poco de oclusión en los surcos: la trenza oscurece donde es baja.
    ao = n.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.25
    mezcla = n.new("ShaderNodeMix"); mezcla.data_type = "RGBA"; mezcla.blend_type = "MULTIPLY"
    color_de = lambda sockets, nombre: next(x for x in sockets if x.name == nombre and x.type == "RGBA")
    mezcla.inputs[0].default_value = 0.6
    l.new(tc.outputs["Color"], color_de(mezcla.inputs, "A"))
    l.new(ao.outputs["AO"], color_de(mezcla.inputs, "B"))
    l.new(color_de(mezcla.outputs, "Result"), bsdf.inputs["Base Color"])
    l.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])
    return m


def material_remate(nombre):
    """El remate del chicote: texturaRemate de escena.js, cuatro rayas cada medio diámetro,
    entre dos rojos oscuros. La UV avanza un mosaico cada π diámetros."""
    m, n, l = material(nombre)
    bsdf = n.get("Principled BSDF")
    uv = n.new("ShaderNodeUVMap")
    sep = n.new("ShaderNodeSeparateXYZ")
    fase = n.new("ShaderNodeMath"); fase.operation = "MULTIPLY"; fase.inputs[1].default_value = 2 * math.pi * 8 * math.pi
    cos = n.new("ShaderNodeMath"); cos.operation = "COSINE"
    rampa = n.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].position, rampa.color_ramp.elements[1].position = 0.0, 1.0
    rampa.color_ramp.elements[0].color = (*lineal((10, 2, 4)), 1)
    rampa.color_ramp.elements[1].color = (*lineal((130, 26, 28)), 1)
    mapa = n.new("ShaderNodeMapRange")
    mapa.inputs["From Min"].default_value, mapa.inputs["From Max"].default_value = -1.0, 1.0
    mapa.inputs["To Min"].default_value, mapa.inputs["To Max"].default_value = 0.46, 1.0
    l.new(uv.outputs["UV"], sep.inputs[0])
    l.new(sep.outputs["X"], fase.inputs[0])
    l.new(fase.outputs[0], cos.inputs[0])
    l.new(cos.outputs[0], mapa.inputs["Value"])
    l.new(mapa.outputs["Result"], rampa.inputs["Fac"])
    l.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    return m


def material_liso(nombre, rgb_lineal, rugosidad, metal=0.0, veta_eje=None):
    """Un color liso. Con `veta_eje` (0, 1 o 2), la veta de la madera a lo largo de ese eje."""
    m, n, l = material(nombre)
    bsdf = n.get("Principled BSDF")
    c = np.asarray(rgb_lineal, float)
    bsdf.inputs["Base Color"].default_value = (*c, 1)
    bsdf.inputs["Roughness"].default_value = rugosidad
    bsdf.inputs["Metallic"].default_value = metal
    if veta_eje is not None:
        escala = [1.6, 1.6, 1.6]
        escala[veta_eje] = 0.08
        coord = n.new("ShaderNodeTexCoord")
        mapa = n.new("ShaderNodeMapping"); mapa.inputs["Scale"].default_value = escala
        ruido = n.new("ShaderNodeTexNoise"); ruido.inputs["Scale"].default_value = 3.0
        ruido.inputs["Detail"].default_value = 6.0
        rampa = n.new("ShaderNodeValToRGB")
        rampa.color_ramp.elements[0].color = (*(c * 0.82), 1)
        rampa.color_ramp.elements[1].color = (*(c * 1.07), 1)
        l.new(coord.outputs["Object"], mapa.inputs["Vector"])
        l.new(mapa.outputs["Vector"], ruido.inputs["Vector"])
        l.new(ruido.outputs["Fac"], rampa.inputs["Fac"])
        l.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    return m


# --------------------------------------------------------------------------
# Mallas
# --------------------------------------------------------------------------
def cuerda(k, datos):
    """La malla de una cuerda, desde el npz de nudos/blender.py, con sus tres materiales."""
    z = np.load(datos["malla"])
    V, F, UV, mat = z["vertices"], z["caras"], z["uv"], z["material"]
    malla = bpy.data.meshes.new(f"cuerda-{k}")
    malla.vertices.add(len(V))
    malla.vertices.foreach_set("co", V.ravel())
    malla.loops.add(F.size)
    malla.loops.foreach_set("vertex_index", F.ravel())
    malla.polygons.add(len(F))
    malla.polygons.foreach_set("loop_start", np.arange(0, F.size, 4, dtype=np.int32))
    malla.polygons.foreach_set("material_index", mat.astype(np.int32))
    malla.update(calc_edges=True)
    capa = malla.uv_layers.new(name="UVMap")
    capa.data.foreach_set("uv", UV.ravel())
    malla.polygons.foreach_set("use_smooth", np.ones(len(F), dtype=bool))
    color = datos["color"]
    for i, cols in enumerate((COLORES[color], AMBAR)):
        malla.materials.append(material_trenza(f"trenza-{k}-{i}", cols))
    malla.materials.append(material_remate(f"remate-{k}"))
    malla.validate()
    ob = bpy.data.objects.new(f"cuerda-{k}", malla)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def malla_generica(i, m):
    """Una malla de escena.js (el anfitrión, una tapa o un dedo), ya en coordenadas del mundo,
    con sus normales y el material de su papel."""
    P = np.asarray(m["pos"], float).reshape(-1, 3)
    N = np.asarray(m["nor"], float).reshape(-1, 3)
    tri = np.asarray(m["idx"], int).reshape(-1, 3)
    usados = np.unique(tri)
    nuevo = np.full(len(P), -1); nuevo[usados] = np.arange(len(usados))
    P, N, tri = P[usados], N[usados], nuevo[tri]
    malla = bpy.data.meshes.new(f"{m['rol']}-{i}")
    malla.from_pydata(P.tolist(), [], tri.tolist())
    malla.polygons.foreach_set("use_smooth", np.ones(len(tri), dtype=bool))
    malla.update()
    malla.normals_split_custom_set_from_vertices(N.tolist())
    rol, c = m["rol"], hex_lineal(m["color"])
    if rol == "madera":
        eje = int(np.argmax(P.max(axis=0) - P.min(axis=0)))
        mat = material_liso(f"madera-{i}", c, m["rugosidad"], veta_eje=eje)
    elif rol == "cuerda":
        # La tapa del comienzo de la cuerda: el tono medio de su trenza.
        mat = material_liso(f"tapa-{i}", lineal(COLORES[m["cuerda"]][1]) * 0.8, 0.8)
    else:
        mat = material_liso(f"{rol}-{i}", c, m["rugosidad"], m["metal"])
    malla.materials.append(mat)
    ob = bpy.data.objects.new(malla.name, malla)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesa():
    bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, 0))
    ob = bpy.context.active_object
    ob.name = "mesa"
    ob.is_shadow_catcher = True


# --------------------------------------------------------------------------
# Luz y cámara
# --------------------------------------------------------------------------
def luz(nombre, pos, mira, energia, tam):
    datos = bpy.data.lights.new(nombre, "AREA")
    datos.energy = energia
    datos.size = tam
    ob = bpy.data.objects.new(nombre, datos)
    ob.location = pos
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (Vector(mira) - Vector(pos)).to_track_quat("-Z", "Y")
    bpy.context.scene.collection.objects.link(ob)


def luces(cx, cy, escala):
    """La luz de escena.js: el sol arriba a la izquierda y el relleno del otro lado, como luces
    de área grandes, que dan sombras blandas, y un cielo claro de ambiente (T14b)."""
    k = escala ** 2
    luz("clave", (cx - 10 * escala / 12, cy + 12 * escala / 12, 26 * escala / 12), (cx, cy, 0),
        6500 * k / 144, 18 * escala / 12)
    luz("relleno", (cx + 14 * escala / 12, cy - 16 * escala / 12, 10 * escala / 12), (cx, cy, 0),
        1500 * k / 144, 24 * escala / 12)
    mundo = bpy.data.worlds.new("cielo")
    bpy.context.scene.world = mundo
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    fondo = mundo.node_tree.nodes.get("Background") or mundo.node_tree.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (*lineal((236, 241, 250)), 1)
    fondo.inputs["Strength"].default_value = 0.8


def camara(escena, c):
    """La cámara de three.js, con su misma matriz: las dos miran por −z con +y hacia arriba."""
    datos = bpy.data.cameras.new("camara")
    datos.sensor_fit = "VERTICAL"
    datos.angle_y = math.radians(c["fov"])
    datos.clip_start, datos.clip_end = c["cerca"], c["lejos"]
    cam = bpy.data.objects.new("camara", datos)
    e = c["matriz"]
    cam.matrix_world = Matrix([[e[col * 4 + fila] for col in range(4)] for fila in range(4)])
    escena.collection.objects.link(cam)
    escena.camera = cam


# --------------------------------------------------------------------------
# El lote
# --------------------------------------------------------------------------
def dibujar(escena, trabajo):
    vaciar()
    datos = json.loads(open(trabajo["escena"], encoding="utf-8").read())
    for k, c in enumerate(trabajo["cuerdas"]):
        cuerda(k, c)
    for i, m in enumerate(datos["mallas"]):
        malla_generica(i, m)
    mesa()
    # En un video (T17), cada cuadro trae su cámara y su luz; la escena es la misma.
    cx, cy = trabajo.get("centro", datos["centro"])
    luces(cx, cy, trabajo.get("extension", datos["extension"]) + 2)
    camara(escena, trabajo.get("camara") or datos["camara"])
    escena.render.filepath = trabajo["salida"]
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", required=True)
    args = ap.parse_args(argv)
    lote = json.loads(open(args.lote, encoding="utf-8").read())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene
    dispositivo = gpu(escena)
    ajustes(escena, lote["ancho"], lote["alto"], lote["muestras"])
    for t in lote["trabajos"]:
        inicio = time.time()
        dibujar(escena, t)
        print(f"listo: {t['salida']} en {time.time() - inicio:.1f} s con {dispositivo}", flush=True)


if __name__ == "__main__":
    main()
