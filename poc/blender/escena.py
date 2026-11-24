"""Prueba de concepto de la fase 6 (T14 y T18): la escena de un nudo en Blender.

Corre dentro de Blender, sin interfaz:
    blender --background --factory-startup --python poc/blender/escena.py -- \
        --trabajo build/poc-blender/trabajos/<slug>--<nombre>.json --salida <png>
        [--muestras 256] [--video <carpeta de cuadros> --segundos 10]

El trabajo es el mismo que recibe render/impresion.js (ver poc/blender/exportar.py): la
cuerda de cada paso, el tramo resaltado, el anfitrión, la vista y el tamaño. La escena
copia la de render/escena.js en lo que dice (unidades en diámetros, la mesa en z = 0, los
colores de la trenza, la cámara de 30° y su encuadre) y cambia cómo se dibuja: Cycles, la
trenza con relieve, luz de área y sombras reales sobre la mesa.

Con --video, la cuerda se va mostrando a lo largo de su camino, de su comienzo a su final, y
la cámara gira despacio: es la animación más simple de un nudo de plantilla, donde cada paso
es un comienzo más largo de la misma cuerda (T17).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

RADIO = 0.5
REMATE = 0.8
ALTO = 1.6
MARGEN = 1.0
FOV = 30.0
VISTAS = {"arriba": (0.001, 0.0), "3d": (0.68, -0.32), "detras": (0.68, math.pi - 0.32)}
# Los colores de render/escena.js: claro, medio y oscuro de la trenza, y el hilo trazador.
COLORES = {
    "azul": [(118, 156, 238), (42, 88, 200), (12, 30, 86), (196, 36, 44)],
    "crema": [(255, 250, 238), (236, 225, 198), (138, 124, 96), (196, 36, 44)],
}
AMBAR = [(255, 214, 140), (222, 140, 34), (92, 46, 6), (150, 30, 30)]
MADERA = (200, 162, 122)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def lineal(c):
    """sRGB 0-255 a lineal 0-1."""
    c = np.asarray(c, dtype=float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def gpu(escena):
    """Cycles en la tarjeta, con OptiX si está."""
    escena.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for tipo in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = tipo
        except TypeError:
            continue
        prefs.get_devices()
        usables = [d for d in prefs.devices if d.type == tipo]
        if usables:
            for d in prefs.devices:
                d.use = d.type == tipo
            escena.cycles.device = "GPU"
            return tipo
    escena.cycles.device = "CPU"
    return "CPU"


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


# --------------------------------------------------------------------------
# La trenza: 16 hilos, 2 sobre 2, como texturasTrenza de render/escena.js
# --------------------------------------------------------------------------
def trenza(top, mid, low, trazador, S=1024):
    """Color (lineal) y alto de un mosaico. u da la vuelta a la cuerda; v avanza π
    diámetros, lo que tarda un hilo en dar una vuelta completa."""
    u, v = np.meshgrid((np.arange(S) + 0.5) / S, (np.arange(S) + 0.5) / S)
    a, b = 8 * (u + v), 8 * (u - v)
    ia, ib = np.floor(a), np.floor(b)
    fa, fb = a - ia, b - ib
    encima_a = np.mod(ia + ib, 4) < 2
    ha, hb = np.sin(np.pi * fa), np.sin(np.pi * fb)
    # Cada hilo es un haz de fibras: se nota un poco a lo largo del hilo.
    fibras_a = 0.92 + 0.08 * np.sin(np.pi * 6 * fa) ** 2
    fibras_b = 0.92 + 0.08 * np.sin(np.pi * 6 * fb) ** 2
    alto = np.where(encima_a, ha ** 0.6 * (0.55 + 0.45 * hb ** 0.5) * fibras_a,
                    hb ** 0.6 * (0.55 + 0.45 * ha ** 0.5) * fibras_b)
    top_, mid_, low_, tr_ = (lineal(c) for c in (top, mid, low, trazador))
    # Casi todo el hilo es del tono medio: el claro solo en la cresta y el oscuro en el surco.
    t = np.clip(alto, 0, 1)[..., None]
    color = np.where(t < 0.5, low_ + (mid_ - low_) * (t / 0.5) ** 1.3,
                     mid_ + (top_ - mid_) * ((t - 0.5) / 0.5) ** 3 * 0.3)
    # El hilo trazador: uno de los ocho hilos de un sentido, angosto y mezclado con la trenza.
    es_trazador = (encima_a & (np.mod(ia, 8) == 0) & (np.abs(fa - 0.5) < 0.28))[..., None]
    color = np.where(es_trazador, 0.55 * tr_ * (0.4 + 0.6 * t) + 0.45 * color, color)
    rng = np.random.default_rng(431)
    color = color * (0.96 + 0.04 * rng.random((S, S, 1)))
    rgba = np.concatenate([color, np.ones((S, S, 1))], axis=2)
    alto_rgba = np.repeat(np.clip(alto, 0, 1)[..., None], 4, axis=2)
    alto_rgba[..., 3] = 1
    return rgba, alto_rgba


def material_trenza(nombre, colores, revelar=None):
    """Principled con la trenza en color y en relieve. Con `revelar`, la cuerda solo se ve
    hasta ese largo (en diámetros), que se anima: lo de más allá es transparente."""
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
    l.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
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
    superficie = bsdf.outputs["BSDF"]
    if revelar is not None:
        # El largo de cada punto viene en el atributo «s»; más allá de «revelar», transparente.
        attr = n.new("ShaderNodeAttribute"); attr.attribute_name = "s"
        valor = n.new("ShaderNodeValue"); valor.name = "revelar"
        mayor = n.new("ShaderNodeMath"); mayor.operation = "GREATER_THAN"
        l.new(attr.outputs["Fac"], mayor.inputs[0])
        l.new(valor.outputs["Value"], mayor.inputs[1])
        transp = n.new("ShaderNodeBsdfTransparent")
        mix = n.new("ShaderNodeMixShader")
        l.new(mayor.outputs["Value"], mix.inputs["Fac"])
        l.new(superficie, mix.inputs[1])
        l.new(transp.outputs["BSDF"], mix.inputs[2])
        superficie = mix.outputs["Shader"]
        revelar.append(valor)
    l.new(superficie, salida.inputs["Surface"])
    return m


def material_simple(nombre, rgb, rugosidad, ruido=0.0):
    m, n, l = material(nombre)
    bsdf = n.get("Principled BSDF") or n.new("ShaderNodeBsdfPrincipled")
    c = lineal(rgb)
    bsdf.inputs["Base Color"].default_value = (*c, 1)
    bsdf.inputs["Roughness"].default_value = rugosidad
    if ruido:
        # Veta de la madera: ruido estirado a lo largo del palo.
        coord = n.new("ShaderNodeTexCoord")
        mapa = n.new("ShaderNodeMapping"); mapa.inputs["Scale"].default_value = (0.08, 1.6, 1.6)
        ruido_n = n.new("ShaderNodeTexNoise"); ruido_n.inputs["Scale"].default_value = 3.0
        ruido_n.inputs["Detail"].default_value = 6.0
        rampa = n.new("ShaderNodeValToRGB")
        rampa.color_ramp.elements[0].color = (*(c * (1 - ruido)), 1)
        rampa.color_ramp.elements[1].color = (*(c * (1 + ruido * 0.4)), 1)
        l.new(coord.outputs["Object"], mapa.inputs["Vector"])
        l.new(mapa.outputs["Vector"], ruido_n.inputs["Vector"])
        l.new(ruido_n.outputs["Fac"], rampa.inputs["Fac"])
        l.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    return m


# --------------------------------------------------------------------------
# La cuerda: un tubo por la línea central
# --------------------------------------------------------------------------
def suavizar(P, veces=2):
    """Catmull-Rom uniforme: cada vez agrega un punto entre cada par, por la curva."""
    for _ in range(veces):
        Q = np.vstack([P[:1] * 2 - P[1:2], P, P[-1:] * 2 - P[-2:-1]])
        medio = (-Q[:-3] + 9 * Q[1:-2] + 9 * Q[2:-1] - Q[3:]) / 16
        out = np.empty((len(P) * 2 - 1, 3))
        out[0::2] = P
        out[1::2] = medio
        P = out
    return P


def tubo(nombre, P, radio, tramos, lados=32):
    """Malla de un tubo por los puntos P, con transporte paralelo para que no se tuerza.
    `tramos`: [(s0, s1, índice de material)] en fracciones del largo. Guarda el largo de
    cada anillo en el atributo «s» y la UV de la trenza: u alrededor, v = s / π."""
    P = suavizar(np.asarray(P, float))
    d = np.diff(P, axis=0)
    seg = np.linalg.norm(d, axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.zeros_like(P)
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N[0] = np.cross(T[0], ref); N[0] /= np.linalg.norm(N[0])
    for k in range(1, len(P)):
        n = N[k - 1] - np.dot(N[k - 1], T[k]) * T[k]
        N[k] = n / np.linalg.norm(n)
    B = np.cross(T, N)
    ang = np.linspace(0, 2 * np.pi, lados, endpoint=False)
    V = (P[:, None, :] + radio * (np.cos(ang)[None, :, None] * N[:, None, :]
                                  + np.sin(ang)[None, :, None] * B[:, None, :])).reshape(-1, 3)
    m = len(P)
    caras = []
    for k in range(m - 1):
        for j in range(lados):
            a, b = k * lados + j, k * lados + (j + 1) % lados
            caras.append((a, b, b + lados, a + lados))
    malla = bpy.data.meshes.new(nombre)
    malla.from_pydata(V.tolist(), [], caras)
    malla.update()
    # UV: u alrededor (0 a 1, con la costura), v a lo largo.
    uvl = malla.uv_layers.new(name="UVMap")
    uvs = np.zeros((len(caras), 4, 2))
    kk = np.repeat(np.arange(m - 1), lados)
    jj = np.tile(np.arange(lados), m - 1)
    du = 1.0 / lados
    uvs[:, 0] = np.c_[jj * du, s[kk] / (math.pi * 2 * radio)]
    uvs[:, 1] = np.c_[(jj + 1) * du, s[kk] / (math.pi * 2 * radio)]
    uvs[:, 2] = np.c_[(jj + 1) * du, s[kk + 1] / (math.pi * 2 * radio)]
    uvs[:, 3] = np.c_[jj * du, s[kk + 1] / (math.pi * 2 * radio)]
    uvl.data.foreach_set("uv", uvs.ravel())
    attr = malla.attributes.new("s", "FLOAT", "POINT")
    attr.data.foreach_set("value", np.repeat(s, lados))
    # Materiales por tramo: cada cara toma el de la fracción de su anillo.
    frac = (s[kk] + s[kk + 1]) / 2 / L
    idx = np.zeros(len(caras), dtype=int)
    for s0, s1, mi in tramos:
        idx[(frac >= s0) & (frac < s1)] = mi
    malla.polygons.foreach_set("material_index", idx)
    malla.polygons.foreach_set("use_smooth", np.ones(len(caras), dtype=bool))
    ob = bpy.data.objects.new(nombre, malla)
    bpy.context.scene.collection.objects.link(ob)
    return ob, P, s


def tapa(nombre, P, adelante, radio, mat):
    """La punta de la cuerda: media esfera aplastada, como en escena.js."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=radio)
    ob = bpy.context.active_object
    ob.name = nombre
    ob.scale = (1, 1, 0.3)
    ob.location = Vector(P)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector(adelante).to_track_quat("Z", "Y")
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mat)
    return ob


# --------------------------------------------------------------------------
# El anfitrión y la mesa
# --------------------------------------------------------------------------
def palo(nombre, largo, centro, eje, radio, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=radio, depth=largo, location=centro)
    ob = bpy.context.active_object
    ob.name = nombre
    if eje == "x":
        ob.rotation_euler = (0, math.pi / 2, 0)
    elif eje == "y":
        ob.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.shade_smooth()
    # Los cantos un poco redondeados, como un palo cortado.
    bis = ob.modifiers.new("canto", "BEVEL"); bis.width = 0.12; bis.segments = 4
    bis.limit_method = "ANGLE"
    ob.data.materials.append(mat)


def anfitrion(a):
    if not a:
        return
    mat = material_simple("madera", MADERA, 0.62, ruido=0.18)
    if a["tipo"] == "poste":
        palo("poste", a["hasta"] - a["desde"], ((a["desde"] + a["hasta"]) / 2, a["y"], a["z"]), "x", a["radio"], mat)
    elif a["tipo"] == "tubo":
        palo("tubo", a["largo"], (0, 0, a["z"]), "x", a["radio"], mat)
    elif a["tipo"] == "cruz":
        palo("palo-abajo", a["largo"], (0, 0, a["z_abajo"]), "y", a["radio"], mat)
        palo("palo-arriba", a["largo"], (0, 0, a["z_arriba"]), "x", a["radio"], mat)
    elif a["tipo"] == "palos":
        for k, y in enumerate(a["y"]):
            palo(f"palo-{k}", a["largo"], (0, y, a["z"]), "x", a["radio"], mat)
    else:
        print(f"aviso: el anfitrión «{a['tipo']}» no está en la prueba de concepto", file=sys.stderr)


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
    return ob


def luces(cx, cy, escala):
    """La luz de escena.js: el sol arriba a la izquierda y un relleno del otro lado, ahora
    como luces de área grandes, que dan sombras blandas; y un cielo claro de ambiente."""
    k = escala ** 2
    luz("clave", (cx - 10 * escala / 12, cy + 12 * escala / 12, 26 * escala / 12), (cx, cy, 0), 6500 * k / 144, 18 * escala / 12)
    luz("relleno", (cx + 14 * escala / 12, cy - 16 * escala / 12, 10 * escala / 12), (cx, cy, 0), 1500 * k / 144, 24 * escala / 12)
    mundo = bpy.data.worlds.new("cielo")
    bpy.context.scene.world = mundo
    try:
        mundo.use_nodes = True
    except AttributeError:
        pass
    fondo = mundo.node_tree.nodes.get("Background") or mundo.node_tree.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (*lineal((236, 241, 250)), 1)
    fondo.inputs["Strength"].default_value = 0.8


def caja(modelo):
    """cajaDeEncuadre y altoDeEncuadre de escena.js."""
    e = modelo.get("encuadre")
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    for s in modelo["pasos"]:
        p = np.asarray(s["p"]).reshape(-1, 3)
        if e:
            p = p[(p[:, 0] >= e["x"][0]) & (p[:, 0] <= e["x"][1]) & (p[:, 1] >= e["y"][0]) & (p[:, 1] <= e["y"][1])]
        x0, x1 = min(x0, p[:, 0].min()), max(x1, p[:, 0].max())
        y0, y1 = min(y0, p[:, 1].min()), max(y1, p[:, 1].max())
    B = (x0 - MARGEN, x1 + MARGEN, y0 - MARGEN, y1 + MARGEN)
    a = modelo.get("anfitrion")
    alto = ALTO
    if a or modelo.get("dos_remates"):
        for s in modelo["pasos"]:
            p = np.asarray(s["p"]).reshape(-1, 3)
            dentro = (p[:, 0] >= B[0]) & (p[:, 0] <= B[1]) & (p[:, 1] >= B[2]) & (p[:, 1] <= B[3])
            if dentro.any():
                alto = max(alto, p[dentro, 2].max() + RADIO)
    if a and a["tipo"] in ("poste", "tubo", "palos", "cabo", "cornamusa"):
        alto = max(alto, a["z"] + a["radio"])
    if a and a["tipo"] == "cruz":
        alto = max(alto, max(a["z_abajo"], a["z_arriba"]) + a["radio"])
    return B, alto


def camara(escena, B, alto, polar, az):
    """pose() de escena.js: centra y acerca la cámara hasta que la caja ocupe el 94 %."""
    datos = bpy.data.cameras.new("camara")
    datos.sensor_fit = "VERTICAL"
    datos.angle_y = math.radians(FOV)
    datos.clip_start, datos.clip_end = 0.5, 800
    cam = bpy.data.objects.new("camara", datos)
    escena.collection.objects.link(cam)
    escena.camera = cam
    esquinas = [Vector((x, y, z)) for x in B[:2] for y in B[2:] for z in (0, alto)]
    t = Vector(((B[0] + B[1]) / 2, (B[2] + B[3]) / 2, 0.5))
    dist = 60.0
    aspecto = escena.render.resolution_x / escena.render.resolution_y

    def colocar():
        cam.location = t + Vector((dist * math.sin(polar) * math.sin(az), -dist * math.sin(polar) * math.cos(az), dist * math.cos(polar)))
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = (t - cam.location).to_track_quat("-Z", "Y")
        bpy.context.view_layer.update()

    for _ in range(8):
        colocar()
        pr = [world_to_camera_view(escena, cam, c) for c in esquinas]
        xs = [2 * p.x - 1 for p in pr]
        ys = [2 * p.y - 1 for p in pr]
        hh = dist * math.tan(math.radians(FOV) / 2)
        hw = hh * aspecto
        mw = cam.matrix_world
        derecha, arriba = mw.col[0].xyz.normalized(), mw.col[1].xyz.normalized()
        t = t + derecha * ((min(xs) + max(xs)) / 2 * hw) + arriba * ((min(ys) + max(ys)) / 2 * hh)
        dist *= max((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2) / 0.94
    colocar()
    return cam, t, dist


# --------------------------------------------------------------------------
# La escena de un trabajo
# --------------------------------------------------------------------------
def construir(trabajo, revelar=None):
    escena = bpy.context.scene
    escena.render.resolution_x = trabajo["ancho"]
    escena.render.resolution_y = trabajo["alto"]
    escena.render.resolution_percentage = 100
    modelo = trabajo["modelo"]
    paso = modelo["pasos"][trabajo["paso"] - 1]
    P = np.asarray(paso["p"]).reshape(-1, 3)
    base = material_trenza("trenza", COLORES["azul"], revelar)
    ambar = material_trenza("ambar", AMBAR, revelar)
    punta, _, _ = material("punta")
    bsdf = punta.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*lineal((27, 21, 23)), 1)
    bsdf.inputs["Roughness"].default_value = 0.45
    remate = material_simple("remate", (110, 22, 24), 0.55)
    L = float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
    fin = 1 - REMATE / L
    ini = REMATE / L if modelo.get("dos_remates") else 0.0
    hl = paso.get("hl") if trabajo.get("resaltar", True) else None
    tramos = [(0, 1.01, 0), (fin, 1.01, 2)]
    if revelar is not None:
        # En el video la cuerda avanza: el remate no puede esperar al final desde el primer
        # cuadro. Va sin remate, y la punta oscura la acompaña.
        tramos, ini = [(0, 1.01, 0)], 0.0
    if ini:
        tramos.append((0, ini, 2))
    if hl:
        tramos.insert(1, (max(hl[0], ini), min(hl[1], fin), 1))
    ob, Ps, s = tubo("cuerda", P, RADIO, tramos)
    for m in (base, ambar, remate):
        ob.data.materials.append(m)
    t0 = Ps[0] - Ps[1]
    tapa("punta-inicio", Ps[0], t0, RADIO, punta if modelo.get("dos_remates") else base)
    tapa_fin = tapa("punta-fin", Ps[-1], Ps[-1] - Ps[-2], RADIO, punta)
    anfitrion(modelo.get("anfitrion"))
    mesa()
    B, alto = caja(modelo)
    polar, az = VISTAS[trabajo["vista"]]
    cam, centro, dist = camara(escena, B, alto, polar, az)
    luces(centro.x, centro.y, max(B[1] - B[0], B[3] - B[2]) / 2 + 2)
    escena.render.film_transparent = True
    # «Standard» deja los colores de la marca como son en sRGB; AgX los lava.
    escena.view_settings.view_transform = "Standard"
    escena.view_settings.look = "None"
    escena.view_settings.exposure = -0.55
    return escena, cam, Ps, s, tapa_fin, centro, dist, polar, az


def anclas(escena, cam, Ps, salida):
    """Dónde caen en la imagen el firme (el primer punto de la cuerda dentro del cuadro) y el
    chicote (el último), en px desde arriba a la izquierda, con hacia dónde va la cuerda ahí.
    Las usa poc/video/nombres.py para poner los nombres, como hoy los pone render/impresion.js."""
    W = escena.render.resolution_x * escena.render.resolution_percentage / 100
    H = escena.render.resolution_y * escena.render.resolution_percentage / 100
    pts = [world_to_camera_view(escena, cam, Vector(p)) for p in Ps]
    dentro = [i for i, q in enumerate(pts) if 0.03 < q.x < 0.97 and 0.03 < q.y < 0.97 and q.z > 0]
    out = {}
    if dentro:
        def px(i):
            return [pts[i].x * W, (1 - pts[i].y) * H]
        i0, i1 = dentro[0], dentro[-1]
        out["firme"] = {"punto": px(i0), "hacia": px(min(i0 + 15, len(Ps) - 1))}
        # La punta, o el último punto que se ve si la punta queda fuera del cuadro.
        out["chicote"] = {"punto": px(i1), "hacia": px(max(i1 - 15, 0))}
    with open(salida.rsplit(".", 1)[0] + ".anclas.json", "w", encoding="utf-8") as f:
        json.dump(out, f)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--trabajo", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--muestras", type=int, default=256)
    ap.add_argument("--video", help="carpeta para los cuadros del video")
    ap.add_argument("--segundos", type=float, default=10)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--escala", type=int, default=100, help="porcentaje del tamaño (vista previa)")
    args = ap.parse_args(argv)
    trabajo = json.loads(open(args.trabajo, encoding="utf-8").read())
    limpiar()
    revelar = [] if args.video else None
    escena, cam, Ps, s, tapa_fin, centro, dist, polar, az = construir(trabajo, revelar)
    dispositivo = gpu(escena)
    escena.cycles.samples = args.muestras
    escena.cycles.use_denoising = True
    escena.cycles.seed = 431
    escena.cycles.transparent_max_bounces = 128
    escena.render.resolution_percentage = args.escala
    escena.render.image_settings.file_format = "PNG"
    escena.render.image_settings.color_mode = "RGBA"
    inicio = time.time()
    if not args.video:
        escena.render.filepath = args.salida
        bpy.ops.render.render(write_still=True)
        anclas(escena, cam, Ps, args.salida)
        print(f"listo: {args.salida} en {time.time() - inicio:.1f} s con {dispositivo}")
        return
    # El video: la cuerda avanza por su camino y la cámara gira despacio, un solo movimiento.
    cuadros = round(args.segundos * args.fps)
    escena.frame_start, escena.frame_end = 1, cuadros
    escena.render.fps = args.fps
    L = s[-1]
    for f in range(1, cuadros + 1):
        x = (f - 1) / (cuadros - 1)
        avance = min(1.0, x / 0.85)                       # al final, un momento quieto
        avance = avance * avance * (3 - 2 * avance)       # empieza y termina suave
        largo = max(0.6, avance * L)
        k = int(np.searchsorted(s, largo).clip(1, len(s) - 1))
        for v in revelar:
            v.outputs["Value"].default_value = largo
            v.outputs["Value"].keyframe_insert("default_value", frame=f)
        tapa_fin.location = Vector(Ps[k])
        tapa_fin.rotation_quaternion = Vector(Ps[k] - Ps[k - 1]).to_track_quat("Z", "Y")
        tapa_fin.keyframe_insert("location", frame=f)
        tapa_fin.keyframe_insert("rotation_quaternion", frame=f)
        g = az - 0.25 + 0.5 * x
        cam.location = centro + Vector((dist * math.sin(polar) * math.sin(g), -dist * math.sin(polar) * math.cos(g), dist * math.cos(polar)))
        cam.rotation_quaternion = (centro - cam.location).to_track_quat("-Z", "Y")
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
    escena.render.filepath = args.video.rstrip("/\\") + "/cuadro-"
    bpy.ops.render.render(animation=True)
    print(f"listo: {cuadros} cuadros en {time.time() - inicio:.1f} s con {dispositivo}")


if __name__ == "__main__":
    main()
