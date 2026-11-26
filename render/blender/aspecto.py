"""Dibuja en Blender el cuadro final de T20a y mide su costo. Corre dentro de Blender 5.2, sin
interfaz, y lo llama nudos/aspecto.py:

    blender --background --factory-startup --python render/blender/aspecto.py -- --lote <lote.json>

El lote trae el motor de render (Cycles o EEVEE) con sus ajustes, el aspecto y las tomas. Cada
toma trae su cámara, la malla de cada cuerda (un npz de nudos/blender.py), las mallas del
anfitrión, la mesa, el fondo y las luces, y la ruta de salida. Por cada toma:
1. arma la escena y dibuja el cuadro (el primero, con la escena por subir a la tarjeta);
2. dibuja los cuadros siguientes del video, cambiando solo la malla de la cuerda, como
   render/blender/video.py: su tiempo es el costo de un cuadro del video;
3. si se pide, dibuja el formato vertical y el cuadro con desenfoque de movimiento (el atributo
   `velocity` de la malla, que Cycles toma solo).
Escribe una línea «tiempo: {json}» por cada cuadro.

Los aspectos (nudos/aspecto.py):
- 0, hoy: la escena de render/blender/escena.py (T16 y T18), tal cual.
- 1 y 2, estudio: la cuerda con la trenza en la geometría, brillo de filamento (anisotropía a lo
  largo de cada hilo) y pelusa (*sheen*); una mesa de madera con sus cantos sobre un fondo curvo
  de estudio (una taza: el piso curva hacia arriba en todas direcciones, así que se ve igual
  desde cualquier lado de la mesa); una ventana grande, un contraluz y un relleno; profundidad de
  campo; la vista AgX o Khronos PBR Neutral.
- 3, campamento: la misma mesa, más gastada, al aire libre: el cielo de Blender con el sol suave
  y, si el lote trae uno, un HDRI de árboles al fondo.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.dirname(os.path.dirname(AQUI)))
import escena as e  # noqa: E402
from nudos import trenza as tr  # noqa: E402

SEMILLA = 431
MM_POR_D = 8.0          # la escena está en diámetros de cuerda: 8 mm (T15e)


# --------------------------------------------------------------------------
# Nodos
# --------------------------------------------------------------------------
class Nodos:
    """Atajos para armar un árbol de nodos de material."""

    def __init__(self, arbol):
        self.n, self.l = arbol.nodes, arbol.links

    def nuevo(self, tipo, **props):
        x = self.n.new(tipo)
        for k, v in props.items():
            setattr(x, k, v)
        return x

    def poner(self, socket, valor):
        if hasattr(valor, "is_output"):
            self.l.new(valor, socket)
        elif valor is not None:
            socket.default_value = valor

    def math(self, op, a, b=None, c=None, clamp=False):
        x = self.nuevo("ShaderNodeMath", operation=op, use_clamp=clamp)
        for s, v in zip(x.inputs, (a, b, c)):
            self.poner(s, v)
        return x.outputs[0]

    def entrada(self, nodo, nombre, tipo=None):
        return next(s for s in nodo.inputs if s.name == nombre and (tipo is None or s.type == tipo))

    def salida(self, nodo, nombre, tipo=None):
        return next(s for s in nodo.outputs if s.name == nombre and (tipo is None or s.type == tipo))

    def mezclar(self, factor, a, b, tipo="RGBA", modo="MIX"):
        x = self.nuevo("ShaderNodeMix", data_type=tipo)
        if tipo == "RGBA":
            x.blend_type = modo
        self.poner(x.inputs[0], factor)
        t = {"RGBA": "RGBA", "VECTOR": "VECTOR", "FLOAT": "VALUE"}[tipo]
        self.poner(self.entrada(x, "A", t), a)
        self.poner(self.entrada(x, "B", t), b)
        return self.salida(x, "Result", t)

    def rampa(self, fac, colores):
        """Una rampa de color: colores = [(posición, (r, g, b) lineal)]."""
        x = self.nuevo("ShaderNodeValToRGB")
        cr = x.color_ramp
        while len(cr.elements) < len(colores):
            cr.elements.new(0.5)
        for el, (p, c) in zip(cr.elements, colores):
            el.position = p
            el.color = (*c, 1.0)
        self.poner(x.inputs["Fac"], fac)
        return x.outputs["Color"]


# --------------------------------------------------------------------------
# El motor de render y la vista
# --------------------------------------------------------------------------
def motor(escena, nombre, aj):
    if nombre == "CYCLES":
        dispositivo = e.gpu(escena)
        c = escena.cycles
        c.samples = int(aj.get("muestras", 64))
        c.use_adaptive_sampling = True
        c.adaptive_threshold = float(aj.get("umbral", 0.02))
        c.use_denoising = True
        c.denoiser = "OPENIMAGEDENOISE"
        c.denoising_use_gpu = True
        c.seed = SEMILLA
        c.use_animated_seed = False
        c.max_bounces = 6
        c.diffuse_bounces = 3
        c.glossy_bounces = 3
        c.transmission_bounces = 2
        c.volume_bounces = 0
        c.transparent_max_bounces = 4
        c.caustics_reflective = False
        c.caustics_refractive = False
        c.use_light_tree = True
        c.use_auto_tile = False
        escena.render.use_persistent_data = True
        return dispositivo
    escena.render.engine = "BLENDER_EEVEE"
    ee = escena.eevee
    ee.taa_render_samples = int(aj.get("muestras", 64))
    ee.use_raytracing = True
    ee.ray_tracing_method = aj.get("trazado", "SCREEN")
    o = ee.ray_tracing_options
    o.resolution_scale = "1"
    o.trace_max_roughness = 0.6
    o.use_denoise = True
    ee.use_fast_gi = True
    ee.fast_gi_method = "GLOBAL_ILLUMINATION"
    ee.use_shadows = True
    ee.shadow_ray_count = int(aj.get("rayos_sombra", 2))
    ee.shadow_step_count = 8
    ee.shadow_resolution_scale = 1.0
    ee.use_bokeh_jittered = True
    ee.bokeh_max_size = 100
    return "GPU"


def vista(escena, a):
    escena.view_settings.view_transform = a.get("vista", "AgX")
    escena.view_settings.look = a.get("look", "None")
    escena.view_settings.exposure = float(a.get("exposicion", 0.0))
    escena.view_settings.gamma = 1.0
    escena.render.dither_intensity = 1.0


# --------------------------------------------------------------------------
# Materiales nuevos
# --------------------------------------------------------------------------
_TEXTURAS = {}


def _imagen(nombre, datos, no_color=False, flotante=False):
    h, w = datos.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = datos[..., None] if datos.ndim == 2 else datos
    im = bpy.data.images.new(nombre, w, h, alpha=False, float_buffer=flotante)
    if no_color:
        im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(rgba.ravel())
    im.pack()
    return im


def material_cuerda(nombre, estilo, a):
    """La cuerda con la trenza: el color y los filamentos en textura, el relieve de los hilos en la
    geometría, y el brillo de filamento a lo largo de cada hilo (la tangente sale de los atributos
    fibra_a y fibra_b de la malla, según el hilo que haya en cada punto)."""
    lado = int(a.get("textura", 2048))
    clave = (estilo, lado)
    if clave not in _TEXTURAS:
        _TEXTURAS[clave] = tr.texturas(tr.ESTILOS[estilo], lado)
    color, finos, hilos = _TEXTURAS[clave]
    m, n, l = e.material(nombre)
    n.clear()
    N = Nodos(m.node_tree)
    salida = N.nuevo("ShaderNodeOutputMaterial")
    bsdf = N.nuevo("ShaderNodeBsdfPrincipled")
    uv = N.nuevo("ShaderNodeUVMap", uv_map="UVMap")
    tc = N.nuevo("ShaderNodeTexImage", interpolation="Cubic")
    tc.image = _imagen(nombre + "-color", color)
    tf = N.nuevo("ShaderNodeTexImage", interpolation="Linear")
    tf.image = _imagen(nombre + "-finos", finos, no_color=True, flotante=True)
    th = N.nuevo("ShaderNodeTexImage", interpolation="Closest")
    th.image = _imagen(nombre + "-hilos", hilos, no_color=True)
    for t in (tc, tf, th):
        l.new(uv.outputs["UV"], t.inputs["Vector"])
    bump = N.nuevo("ShaderNodeBump")
    bump.inputs["Strength"].default_value = float(a.get("filamentos", 0.35))
    bump.inputs["Distance"].default_value = 0.01
    l.new(tf.outputs["Color"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    fa = N.nuevo("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="fibra_a")
    fb = N.nuevo("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="fibra_b")
    t = N.mezclar(th.outputs["Color"], N.salida(fb, "Vector"), N.salida(fa, "Vector"), "VECTOR")
    nor = N.nuevo("ShaderNodeVectorMath", operation="NORMALIZE")
    l.new(t, nor.inputs[0])
    l.new(nor.outputs["Vector"], bsdf.inputs["Tangent"])
    bsdf.inputs["Roughness"].default_value = float(a.get("rugosidad", 0.42))
    bsdf.inputs["Anisotropic"].default_value = float(a.get("anisotropia", 0.7))
    bsdf.inputs["Anisotropic Rotation"].default_value = float(a.get("giro_brillo", 0.25))
    bsdf.inputs["Sheen Weight"].default_value = float(a.get("sheen", 0.35))
    bsdf.inputs["Sheen Roughness"].default_value = 0.4
    bsdf.inputs["Specular IOR Level"].default_value = float(a.get("especular", 0.5))
    l.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])
    return m


def material_cinta(nombre, rgb, mosaico=1.0):
    """La cinta del chicote: vinílica, con brillo, enrollada en espiral (el borde de cada vuelta,
    cada 0,55 d, se ve como una línea fina) y con arrugas suaves."""
    m, n, l = e.material(nombre)
    n.clear()
    N = Nodos(m.node_tree)
    salida = N.nuevo("ShaderNodeOutputMaterial")
    bsdf = N.nuevo("ShaderNodeBsdfPrincipled")
    uv = N.nuevo("ShaderNodeUVMap", uv_map="UVMap")
    sep = N.nuevo("ShaderNodeSeparateXYZ")
    l.new(uv.outputs["UV"], sep.inputs[0])
    vuelta = N.math("MULTIPLY_ADD", sep.outputs["X"], math.pi * mosaico / 0.55, sep.outputs["Y"])
    fr = N.math("FRACT", vuelta)
    cerca = N.math("MINIMUM", fr, N.math("SUBTRACT", 1.0, fr))
    borde = N.math("SUBTRACT", 1.0, N.math("DIVIDE", cerca, 0.015), clamp=True)
    c = np.asarray(e.lineal(rgb), float)
    col = N.rampa(borde, [(0.0, c), (1.0, c * 0.8)])
    l.new(col, bsdf.inputs["Base Color"])
    arruga = N.nuevo("ShaderNodeTexNoise")
    arruga.inputs["Scale"].default_value = 9.0
    arruga.inputs["Detail"].default_value = 2.0
    alto = N.math("SUBTRACT", N.math("MULTIPLY", arruga.outputs["Fac"], 0.3), N.math("MULTIPLY", borde, 0.5))
    bump = N.nuevo("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.012
    l.new(alto, bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.3
    bsdf.inputs["Coat Weight"].default_value = 0.35
    bsdf.inputs["Coat Roughness"].default_value = 0.1
    l.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])
    return m


def material_madera(nombre, claro, oscuro, ancho_tabla=18.0, separacion=0.1, barniz=0.12,
                    rugosidad=0.5, veta=0.11):
    """Tablas de madera a lo largo de x local, de `ancho_tabla` d, con la veta, el tono de cada
    tabla y la junta entre tablas. Todo en las coordenadas del objeto, en diámetros."""
    m, n, l = e.material(nombre)
    n.clear()
    N = Nodos(m.node_tree)
    salida = N.nuevo("ShaderNodeOutputMaterial")
    bsdf = N.nuevo("ShaderNodeBsdfPrincipled")
    tc = N.nuevo("ShaderNodeTexCoord")
    sep = N.nuevo("ShaderNodeSeparateXYZ")
    l.new(tc.outputs["Object"], sep.inputs[0])
    x, y, z = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
    t = N.math("DIVIDE", y, ancho_tabla)
    idx = N.math("FLOOR", t)
    fr = N.math("SUBTRACT", t, idx)
    borde = N.math("MULTIPLY", N.math("MINIMUM", fr, N.math("SUBTRACT", 1.0, fr)), ancho_tabla)
    junta = N.math("SUBTRACT", 1.0, N.math("DIVIDE", borde, separacion), clamp=True)
    azar = N.nuevo("ShaderNodeTexWhiteNoise", noise_dimensions="1D")
    N.poner(azar.inputs["W"], idx)
    r1 = azar.outputs["Value"]
    rgb = N.nuevo("ShaderNodeSeparateColor")
    l.new(azar.outputs["Color"], rgb.inputs[0])
    r2 = rgb.outputs[1]
    # La veta: los anillos del árbol, cortados a lo largo (bandas de unos 2 cm, con la madera
    # tardía más oscura y angosta: el perfil de sierra), torcidos por un ruido lento.
    xv = N.math("MULTIPLY_ADD", x, 0.12, N.math("MULTIPLY", r1, 57.0))
    yv = N.math("ADD", y, N.math("MULTIPLY", r1, 13.0))
    v = N.nuevo("ShaderNodeCombineXYZ")
    N.poner(v.inputs[0], xv)
    N.poner(v.inputs[1], yv)
    N.poner(v.inputs[2], z)
    ola = N.nuevo("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y", wave_profile="SAW")
    ola.inputs["Scale"].default_value = veta
    ola.inputs["Distortion"].default_value = 9.0
    ola.inputs["Detail"].default_value = 2.0
    ola.inputs["Detail Scale"].default_value = 0.6
    ola.inputs["Detail Roughness"].default_value = 0.4
    l.new(v.outputs[0], ola.inputs["Vector"])
    # La madera tardía: una línea angosta y oscura al final de cada anillo.
    anillo = N.math("POWER", ola.outputs["Fac"], 7.0)
    # Las fibras: un ruido fino, muy estirado a lo largo de la tabla.
    vf = N.nuevo("ShaderNodeCombineXYZ")
    N.poner(vf.inputs[0], N.math("MULTIPLY", x, 0.05))
    N.poner(vf.inputs[1], N.math("MULTIPLY", yv, 2.5))
    N.poner(vf.inputs[2], z)
    fibra = N.nuevo("ShaderNodeTexNoise")
    fibra.inputs["Scale"].default_value = 2.0
    fibra.inputs["Detail"].default_value = 6.0
    l.new(vf.outputs[0], fibra.inputs["Vector"])
    # Manchas grandes: la madera no es pareja.
    mancha = N.nuevo("ShaderNodeTexNoise")
    mancha.inputs["Scale"].default_value = 0.035
    mancha.inputs["Detail"].default_value = 3.0
    l.new(tc.outputs["Object"], mancha.inputs["Vector"])
    g = N.math("MULTIPLY_ADD", anillo, 0.45, N.math("MULTIPLY", fibra.outputs["Fac"], 0.4))
    g = N.math("MULTIPLY_ADD", mancha.outputs["Fac"], 0.3, g)
    col = N.rampa(g, [(0.3, e.lineal(claro)), (0.85, e.lineal(oscuro))])
    tono = N.nuevo("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    tono.inputs[0].default_value = 1.0
    N.poner(N.entrada(tono, "A", "RGBA"), col)
    gris = N.nuevo("ShaderNodeCombineColor")
    k = N.math("MULTIPLY_ADD", r2, 0.3, 0.82)
    for s in gris.inputs[:3]:
        N.poner(s, k)
    N.poner(N.entrada(tono, "B", "RGBA"), gris.outputs[0])
    base = N.mezclar(N.math("MULTIPLY", junta, 0.85), N.salida(tono, "Result", "RGBA"), (0.05, 0.032, 0.02, 1.0))
    l.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rugosidad
    bsdf.inputs["Coat Weight"].default_value = barniz
    bsdf.inputs["Coat Roughness"].default_value = 0.3
    alto = N.math("SUBTRACT", N.math("MULTIPLY", fibra.outputs["Fac"], 0.25), N.math("MULTIPLY", junta, 1.2))
    bump = N.nuevo("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    bump.inputs["Distance"].default_value = 0.06
    l.new(alto, bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])
    return m


def material_palo(nombre, rgb_lineal, eje):
    """Un palo de madera: la veta a lo largo de su eje (coordenadas del mundo: las mallas del
    anfitrión ya vienen en el mundo)."""
    m, n, l = e.material(nombre)
    n.clear()
    N = Nodos(m.node_tree)
    salida = N.nuevo("ShaderNodeOutputMaterial")
    bsdf = N.nuevo("ShaderNodeBsdfPrincipled")
    tc = N.nuevo("ShaderNodeTexCoord")
    escala = [1.0, 1.0, 1.0]
    escala[eje] = 0.05
    mapa = N.nuevo("ShaderNodeMapping")
    mapa.inputs["Scale"].default_value = escala
    l.new(tc.outputs["Object"], mapa.inputs["Vector"])
    ola = N.nuevo("ShaderNodeTexWave", wave_type="RINGS", rings_direction=("X", "Y", "Z")[eje])
    ola.inputs["Scale"].default_value = 0.35
    ola.inputs["Distortion"].default_value = 5.0
    ola.inputs["Detail"].default_value = 3.0
    l.new(mapa.outputs["Vector"], ola.inputs["Vector"])
    c = np.asarray(rgb_lineal, float)
    col = N.rampa(ola.outputs["Fac"], [(0.15, c * 0.62), (0.85, c * 1.08)])
    l.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    bump = N.nuevo("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.04
    l.new(ola.outputs["Fac"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])
    return m


def material_papel(nombre, rgb):
    """El fondo de estudio: papel mate, un poco más oscuro arriba."""
    m, n, l = e.material(nombre)
    n.clear()
    N = Nodos(m.node_tree)
    salida = N.nuevo("ShaderNodeOutputMaterial")
    bsdf = N.nuevo("ShaderNodeBsdfPrincipled")
    geo = N.nuevo("ShaderNodeNewGeometry")
    sep = N.nuevo("ShaderNodeSeparateXYZ")
    l.new(geo.outputs["Position"], sep.inputs[0])
    c = np.asarray(e.lineal(rgb), float)
    alto = N.nuevo("ShaderNodeMapRange")
    alto.inputs["From Min"].default_value, alto.inputs["From Max"].default_value = 0.0, 160.0
    l.new(sep.outputs["Z"], alto.inputs["Value"])
    col = N.rampa(alto.outputs["Result"], [(0.0, c), (1.0, c * 0.55)])
    l.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.92
    bsdf.inputs["Specular IOR Level"].default_value = 0.2
    l.new(bsdf.outputs["BSDF"], salida.inputs["Surface"])
    return m


# --------------------------------------------------------------------------
# Mallas
# --------------------------------------------------------------------------
def objeto(nombre, malla):
    ob = bpy.data.objects.new(nombre, malla)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def malla_npz(nombre, ruta, con_trenza):
    """La malla de una cuerda desde su npz, con la UV y, en la trenza, las direcciones de los
    hilos y la velocidad (si la trae)."""
    z = np.load(ruta)
    V, F, UV, mat = z["vertices"], z["caras"], z["uv"], z["material"]
    malla = bpy.data.meshes.new(nombre)
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
    if con_trenza:
        for at in ("fibra_a", "fibra_b"):
            a = malla.attributes.new(at, "FLOAT_VECTOR", "POINT")
            a.data.foreach_set("vector", z[at].ravel())
        if "velocidad" in z:
            a = malla.attributes.new("velocidad", "FLOAT_VECTOR", "POINT")
            a.data.foreach_set("vector", z["velocidad"].ravel())
    return malla


def poner_cuerda(nombre, ruta, materiales, con_trenza, previo=None):
    """La cuerda de un cuadro: un objeto nuevo o, si ya hay uno (`previo`), el mismo con la malla
    nueva, como en render/blender/video.py."""
    malla = malla_npz(nombre, ruta, con_trenza)
    for m in materiales:
        malla.materials.append(m)
    if previo is None:
        return objeto(nombre, malla)
    vieja = previo.data
    previo.data = malla
    bpy.data.meshes.remove(vieja)
    return previo


def caja(nombre, cx, cy, a, b, z0, z1, giro=0.0):
    """Una caja de 2a × 2b de z0 a z1, girada `giro` alrededor de z, con el origen en su centro de
    arriba (las coordenadas del objeto son las de la tabla)."""
    V = [(x, y, z) for z in (z0 - z1, 0.0) for y in (-b, b) for x in (-a, a)]
    F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    malla = bpy.data.meshes.new(nombre)
    malla.from_pydata(V, [], F)
    malla.update()
    ob = objeto(nombre, malla)
    ob.location = (cx, cy, z1)
    ob.rotation_euler = (0.0, 0.0, giro)
    return ob


def mesa_madera(m: dict, material):
    """La mesa: una tabla gruesa con los cantos biselados, la cara de arriba en z = 0."""
    ob = caja("mesa", m["centro"][0], m["centro"][1], m["semi"][0], m["semi"][1], -m["grosor"], 0.0,
              m.get("giro", 0.0))
    bis = ob.modifiers.new("bisel", "BEVEL")
    bis.width = m.get("bisel", 0.45)
    bis.segments = 4
    bis.limit_method = "ANGLE"
    ob.data.materials.append(material)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def taza(f: dict, material):
    """El fondo de estudio: un piso redondo a la altura `piso` que curva hacia arriba con radio
    `curva` desde el radio `radio` y sube hasta `alto`. Desde cualquier lado de la mesa se ve
    igual."""
    cx, cy = f["centro"]
    z0, r0, rc, alto = f["piso"], f["radio"], f["curva"], f["alto"]
    perfil = [(0.0, z0)]
    perfil += [(r0 * k / 12, z0) for k in range(1, 13)]
    perfil += [(r0 + rc * math.sin(t), z0 + rc * (1 - math.cos(t)))
               for t in np.linspace(0, math.pi / 2, 16)[1:]]
    perfil += [(r0 + rc, z0 + rc + (alto - rc) * k / 6) for k in range(1, 7)]
    lados = 128
    V, F = [], []
    for j in range(lados):
        a = 2 * math.pi * j / lados
        for r, z in perfil:
            V.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    p = len(perfil)
    for j in range(lados):
        jn = (j + 1) % lados
        for i in range(p - 1):
            F.append((j * p + i, jn * p + i, jn * p + i + 1, j * p + i + 1))
    malla = bpy.data.meshes.new("fondo")
    malla.from_pydata(V, [], F)
    malla.update()
    malla.polygons.foreach_set("use_smooth", np.ones(len(F), dtype=bool))
    malla.materials.append(material)
    return objeto("fondo", malla)


def anfitrion(i, m, aspecto_nuevo):
    """Una malla de escena.js (el anfitrión): la de escena.py o, en un aspecto nuevo, con la
    madera nueva."""
    if not aspecto_nuevo or m["rol"] not in ("madera", "testa"):
        return e.malla_generica(i, m)
    P = np.asarray(m["pos"], float).reshape(-1, 3)
    N_ = np.asarray(m["nor"], float).reshape(-1, 3)
    tri = np.asarray(m["idx"], int).reshape(-1, 3)
    usados = np.unique(tri)
    nuevo = np.full(len(P), -1)
    nuevo[usados] = np.arange(len(usados))
    P, N_, tri = P[usados], N_[usados], nuevo[tri]
    malla = bpy.data.meshes.new(f"{m['rol']}-{i}")
    malla.from_pydata(P.tolist(), [], tri.tolist())
    malla.polygons.foreach_set("use_smooth", np.ones(len(tri), dtype=bool))
    malla.update()
    malla.normals_split_custom_set_from_vertices(N_.tolist())
    c = e.hex_lineal(m["color"])
    eje = int(np.argmax(P.max(axis=0) - P.min(axis=0)))
    if m["rol"] == "testa":
        mat = e.material_liso(f"testa-{i}", c * 0.85, 0.8)
    else:
        mat = material_palo(f"palo-{i}", c, eje)
    malla.materials.append(mat)
    return objeto(malla.name, malla)


CUADRO = 100            # el cuadro de la escena en que se dibuja todo (el desenfoque mira ±¼)
FPS = 60


def mover_por_velocidad():
    """Un modificador de Geometry Nodes que corre cada vértice su velocidad (el atributo
    «velocidad», en d por segundo) por el tiempo que pasa desde CUADRO. La malla es la de un solo
    cuadro, pero el desenfoque de movimiento de Cycles y de EEVEE mira la escena al abrir y al
    cerrar el obturador, y ahí la cuerda ya se movió. (Ninguno de los dos toma el atributo
    `velocity` de una malla común: con él, el cuadro sale igual, medido en T20a.)"""
    ng = bpy.data.node_groups.get("mover-por-velocidad")
    if ng is not None:
        return ng
    ng = bpy.data.node_groups.new("mover-por-velocidad", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n, l = ng.nodes, ng.links
    entrada, salida = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    tiempo = n.new("GeometryNodeInputSceneTime")
    desde = n.new("ShaderNodeMath")
    desde.operation = "SUBTRACT"
    desde.inputs[1].default_value = CUADRO
    segundos = n.new("ShaderNodeMath")
    segundos.operation = "DIVIDE"
    segundos.inputs[1].default_value = FPS
    vel = n.new("GeometryNodeInputNamedAttribute")
    vel.data_type = "FLOAT_VECTOR"
    vel.inputs["Name"].default_value = "velocidad"
    corrida = n.new("ShaderNodeVectorMath")
    corrida.operation = "SCALE"
    poner = n.new("GeometryNodeSetPosition")
    l.new(entrada.outputs[0], poner.inputs["Geometry"])
    l.new(tiempo.outputs["Frame"], desde.inputs[0])
    l.new(desde.outputs[0], segundos.inputs[0])
    l.new(vel.outputs["Attribute"], corrida.inputs[0])
    l.new(segundos.outputs[0], corrida.inputs["Scale"])
    l.new(corrida.outputs["Vector"], poner.inputs["Offset"])
    l.new(poner.outputs[0], salida.inputs[0])
    return ng


# --------------------------------------------------------------------------
# Luz
# --------------------------------------------------------------------------
def direccion(az, phi, elev):
    """La dirección (unitaria) hacia una luz: `phi` es el ángulo alrededor de la mesa desde la
    cámara (0, del lado de la cámara; 90°, a su derecha; 180°, detrás del nudo) y `elev`, la
    altura sobre la mesa."""
    cam = np.array([math.sin(az), -math.cos(az)])
    der = np.array([math.cos(az), math.sin(az)])
    hz = math.cos(phi) * cam + math.sin(phi) * der
    return np.array([hz[0] * math.cos(elev), hz[1] * math.cos(elev), math.sin(elev)])


def luz_area(nombre, centro, d, dist, irradiancia, tam_x, tam_y=None, color=(1.0, 1.0, 1.0)):
    """Una luz de área a `dist` del centro en la dirección d, que mira al centro y da ahí más o
    menos `irradiancia`."""
    datos = bpy.data.lights.new(nombre, "AREA")
    datos.shape = "RECTANGLE"
    datos.size = tam_x
    datos.size_y = tam_y if tam_y is not None else tam_x
    datos.energy = irradiancia * math.pi * dist * dist
    datos.color = color
    datos.use_shadow = True
    if hasattr(datos, "use_shadow_jitter"):
        datos.use_shadow_jitter = True
    ob = objeto(nombre, datos)
    pos = Vector(centro) + Vector(d) * dist
    ob.location = pos
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (Vector(centro) - pos).to_track_quat("-Z", "Y")
    return ob


def mundo_color(rgb_lineal, fuerza):
    mundo = bpy.data.worlds.new("mundo")
    bpy.context.scene.world = mundo
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    fondo = mundo.node_tree.nodes.get("Background") or mundo.node_tree.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (*rgb_lineal, 1)
    fondo.inputs["Strength"].default_value = fuerza
    return mundo


def luces_estudio(l: dict, a: dict):
    c = (l["centro"][0], l["centro"][1], 1.0)
    s, az = l["escala"], l["az"]
    k = a.get("luz", 1.0)
    luz_area("ventana", c, direccion(az, math.radians(-118), math.radians(40)), 4.2 * s, 3.4 * k,
             2.6 * s, 1.6 * s, (1.0, 0.97, 0.93))
    luz_area("contraluz", c, direccion(az, math.radians(165), math.radians(24)), 3.2 * s, 2.2 * k,
             0.6 * s, 0.6 * s, (0.92, 0.95, 1.0))
    luz_area("relleno", c, direccion(az, math.radians(65), math.radians(28)), 3.8 * s, 0.55 * k,
             2.4 * s, 2.4 * s, (0.95, 0.97, 1.0))
    mundo_color((0.6, 0.62, 0.66), 0.04)


def mundo_campamento(l: dict, a: dict, hdri: str | None):
    """Con HDRI, el HDRI da la luz y el fondo, girado (`hdri_giro`, que calcula nudos/aspecto.py)
    para que su sol quede atrás a la izquierda de la cámara; EEVEE saca de él un sol con sombra.
    Sin HDRI, el cielo de Blender (dispersión múltiple, sin el disco del sol) y un sol suave."""
    az = l["az"]
    k = a.get("luz", 1.0)
    mundo = bpy.data.worlds.new("cielo")
    bpy.context.scene.world = mundo
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    n, li = mundo.node_tree.nodes, mundo.node_tree.links
    n.clear()
    salida = n.new("ShaderNodeOutputWorld")
    fondo = n.new("ShaderNodeBackground")
    li.new(fondo.outputs["Background"], salida.inputs["Surface"])
    if hdri:
        imagen = bpy.data.images.load(hdri)
        coord = n.new("ShaderNodeTexCoord")

        def hdri_girado(rotacion):
            mapa = n.new("ShaderNodeMapping")
            mapa.inputs["Rotation"].default_value = rotacion
            li.new(coord.outputs["Generated"], mapa.inputs["Vector"])
            env = n.new("ShaderNodeTexEnvironment")
            env.image = imagen
            li.new(mapa.outputs["Vector"], env.inputs["Vector"])
            return env.outputs["Color"]

        giro = Matrix.Rotation(a.get("hdri_giro", 0.0), 3, "Z")
        li.new(hdri_girado(giro.to_euler("XYZ")), fondo.inputs["Color"])
        fondo.inputs["Strength"].default_value = a.get("hdri_fuerza", 1.0) * k
        incl = a.get("hdri_inclinacion", 0.0)
        if incl:
            # Lo que ve la cámara: el HDRI bajado `incl` grados hacia donde mira, para que los
            # árboles entren al cuadro; la luz sigue siendo la del HDRI sin bajar.
            der = Vector((math.cos(az), math.sin(az), 0.0))
            visto = n.new("ShaderNodeBackground")
            visto.inputs["Strength"].default_value = a.get("hdri_fuerza", 1.0) * k
            li.new(hdri_girado((giro @ Matrix.Rotation(math.radians(incl), 3, der)).to_euler("XYZ")),
                   visto.inputs["Color"])
            camino = n.new("ShaderNodeLightPath")
            mez = n.new("ShaderNodeMixShader")
            li.new(camino.outputs["Is Camera Ray"], mez.inputs[0])
            li.new(fondo.outputs["Background"], mez.inputs[1])
            li.new(visto.outputs["Background"], mez.inputs[2])
            li.new(mez.outputs[0], salida.inputs["Surface"])
        mundo.sun_threshold = a.get("umbral_sol", 10.0)
        mundo.sun_angle = math.radians(a.get("sol_angulo", 4.0))
        mundo.use_sun_shadow = True
        if hasattr(mundo, "use_sun_shadow_jitter"):
            mundo.use_sun_shadow_jitter = True
        return
    d_sol = direccion(az, math.radians(a.get("sol_phi", -125)), math.radians(a.get("sol_elev", 38)))
    cielo = n.new("ShaderNodeTexSky")
    cielo.sky_type = "MULTIPLE_SCATTERING"
    cielo.sun_disc = False
    cielo.sun_elevation = math.asin(d_sol[2])
    # sun_rotation: el ángulo del sol alrededor de z, desde +y en el sentido de las agujas.
    cielo.sun_rotation = math.atan2(d_sol[0], d_sol[1])
    cielo.altitude = 300.0
    fondo.inputs["Strength"].default_value = a.get("cielo", 0.12) * k
    li.new(cielo.outputs["Color"], fondo.inputs["Color"])
    datos = bpy.data.lights.new("sol", "SUN")
    datos.energy = a.get("sol", 3.2) * k
    datos.angle = math.radians(a.get("sol_angulo", 4.0))
    datos.color = (1.0, 0.95, 0.86)
    if hasattr(datos, "use_shadow_jitter"):
        datos.use_shadow_jitter = True
    ob = objeto("sol", datos)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector(-d_sol).to_track_quat("-Z", "Y")


# --------------------------------------------------------------------------
# Cámara
# --------------------------------------------------------------------------
def camara(escena, c, foco=None, fstop=None):
    e.camara(escena, c)
    cam = escena.camera
    dof = cam.data.dof
    dof.use_dof = foco is not None and fstop is not None
    if dof.use_dof:
        dof.focus_distance = float(foco)
        # La escena está en diámetros: el número f de un lente real, pasado a la escala de 8 mm.
        dof.aperture_fstop = float(fstop) * MM_POR_D / 1000.0
        dof.aperture_blades = 0
    return cam


# --------------------------------------------------------------------------
# Una toma
# --------------------------------------------------------------------------
def armar(escena, a: dict, t: dict, motor_nombre: str):
    """La escena de la toma en el aspecto: todo menos la cuerda. Devuelve los materiales de la
    cuerda (base, resaltado y remate)."""
    e.vaciar()
    datos = json.loads(open(t["escena"], encoding="utf-8").read())
    nuevo = a["malla"] == "trenza"
    for i, m in enumerate(datos["mallas"]):
        anfitrion(i, m, nuevo)
    if not nuevo:
        # Hoy: la mesa es un receptor de sombras sobre transparente (Cycles); EEVEE no tiene
        # receptor de sombras, así que ahí la mesa es blanca.
        if motor_nombre == "CYCLES":
            e.mesa()
            escena.render.film_transparent = True
        else:
            bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, 0))
            bpy.context.active_object.data.materials.append(e.material_liso("blanco", (0.8, 0.8, 0.8), 0.9))
            escena.render.film_transparent = False
        cx, cy = t["luz"]["centro"]
        e.luces(cx, cy, t["luz"]["extension"] + 2)
        color = t["cuerdas"][0].get("color", "azul")
        return [e.material_trenza(f"trenza-{i}", cols)
                for i, cols in enumerate((e.COLORES[color], e.AMBAR))] + [e.material_remate("remate")]
    escena.render.film_transparent = False
    if a["escena"] == "estudio":
        mesa_madera(t["mesa"], material_madera("madera", a["madera_claro"], a["madera_oscuro"],
                                               barniz=a.get("barniz", 0.12)))
        taza(t["fondo"], material_papel("papel", a.get("papel", (196, 192, 186))))
        luces_estudio(t["luz"], a)
    else:
        mesa_madera(t["mesa"], material_madera("madera", a["madera_claro"], a["madera_oscuro"],
                                               ancho_tabla=14.0, separacion=0.25, barniz=0.0,
                                               rugosidad=0.72, veta=0.09))
        mundo_campamento(t["luz"], a, a.get("hdri"))
    c = t["cuerdas"][0]
    return [material_cuerda("cuerda", c["estilo"], a), material_cuerda("resaltado", c["resaltado"], a),
            material_cinta("cinta", a.get("cinta", (214, 52, 32)), tr.ESTILOS[c["estilo"]].mosaico)]


def render(escena, salida, comprimir=15):
    escena.render.filepath = salida
    escena.render.image_settings.compression = comprimir
    inicio = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - inicio


def anotar(**datos):
    print("tiempo: " + json.dumps(datos), flush=True)


def toma(escena, a, t, motor_nombre, ancho, alto):
    a = t.get("aspecto", a)
    materiales = armar(escena, a, t, motor_nombre)
    trenza = a["malla"] == "trenza"
    escena.render.resolution_x, escena.render.resolution_y = ancho, alto
    escena.render.image_settings.color_mode = "RGBA" if escena.render.film_transparent else "RGB"
    fstop = a.get("fstop") if trenza else None
    cuerda = poner_cuerda("cuerda", t["cuerdas"][0]["malla"], materiales, trenza)
    camara(escena, t["camara"], t.get("foco"), fstop)
    anotar(toma=t["nombre"], tipo="primero", s=round(render(escena, t["salida"]), 2))
    # Los cuadros siguientes del video: solo cambia la malla de la cuerda (y la cámara se queda).
    for k, ruta in enumerate(t.get("seguidos", [])):
        cuerda = poner_cuerda("cuerda", ruta, materiales, trenza, cuerda)
        anotar(toma=t["nombre"], tipo="seguido", k=k,
               s=round(render(escena, t["salida_seguidos"], comprimir=0), 2))
    v = t.get("vertical")
    if v:
        escena.render.resolution_x, escena.render.resolution_y = v["ancho"], v["alto"]
        camara(escena, v["camara"], v.get("foco"), fstop)
        for k, ruta in enumerate([t["cuerdas"][0]["malla"]] + t.get("seguidos", [])[:2]):
            cuerda = poner_cuerda("cuerda", ruta, materiales, trenza, cuerda)
            dt = render(escena, v["salida"] if k == 0 else t["salida_seguidos"], comprimir=15 if k == 0 else 0)
            anotar(toma=t["nombre"], tipo="vertical" if k else "vertical-primero", k=k, s=round(dt, 2))
        escena.render.resolution_x, escena.render.resolution_y = ancho, alto
        camara(escena, t["camara"], t.get("foco"), fstop)
    mov = t.get("movimiento")
    if mov:
        # El cuadro más rápido del paso, con su cámara: sin y con el desenfoque de movimiento, que
        # sale de la velocidad de cada vértice (el atributo «velocity» de la malla).
        cuerda = poner_cuerda("cuerda", mov["malla"], materiales, trenza, cuerda)
        if mov.get("camara"):
            camara(escena, mov["camara"], mov.get("foco"), fstop)
        anotar(toma=t["nombre"], tipo="movimiento-sin", s=round(render(escena, mov["salida_sin"]), 2))
        mod = cuerda.modifiers.new("velocidad", "NODES")
        mod.node_group = mover_por_velocidad()
        escena.render.use_motion_blur = True
        escena.render.motion_blur_shutter = mov.get("obturador", 0.5)
        if motor_nombre == "BLENDER_EEVEE":
            escena.eevee.motion_blur_steps = 1
        anotar(toma=t["nombre"], tipo="movimiento", s=round(render(escena, mov["salida"]), 2))
        escena.render.use_motion_blur = False
        cuerda.modifiers.remove(mod)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", required=True)
    args = ap.parse_args(argv)
    lote = json.loads(open(args.lote, encoding="utf-8").read())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene
    escena.render.fps = FPS
    escena.frame_set(CUADRO)
    dispositivo = motor(escena, lote["motor"], lote.get("ajustes", {}))
    a = lote["aspecto"]
    vista(escena, a)
    escena.render.image_settings.file_format = "PNG"
    escena.render.image_settings.color_depth = "8"
    print(f"motor: {lote['motor']} en {dispositivo}", flush=True)
    for t in lote["tomas"]:
        toma(escena, a, t, lote["motor"], lote["ancho"], lote["alto"])


if __name__ == "__main__":
    main()
