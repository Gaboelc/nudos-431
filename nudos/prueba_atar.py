"""La prueba de T17: el as de guía y el amarre cuadrado atados con el motor, en movimiento.

`python -m nudos prueba-atar` construye los dos pilotos con el motor, anima cada paso
(`nudos/animar.py`, con el modo «atar» de `nudos/fisica/atar.py`), comprueba todos los cuadros y
deja en build/atar/:

- `<slug>.npz`, los cuadros del nudo entero a 60 por segundo (con las pausas), y
  `<slug>.json`, qué paso y qué movimiento es cada cuadro, las medidas y las fallas.
- `<slug>-prueba.mp4`, los 10 s en movimiento de la puerta del método de elasthic, dibujados en
  Blender con la escena de T16, a 1280 × 720 y 30 cuadros por segundo.
- `<slug>-previa.mp4`, el nudo entero en baja calidad (960 × 540, 16 muestras, 15 cuadros por
  segundo), para ver todos los pasos.

La cámara va por tramos: cada paso tiene su toma, encuadrada con la cuerda de ese paso, y la
cámara solo se mueve en la pausa. En una plantilla, el ángulo alrededor de la mesa se elige en
cada paso para que los palos tapen lo menos posible de la cuerda nueva.

Necesita Google Chrome (o Edge, con NUDOS_CHROME) para sacar de escena.js las mallas del
anfitrión, Blender 5.2 y ffmpeg.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import BUILD
from .fisica.atar import FPS

DESTINO = BUILD / "atar"
PILOTOS = ("as-de-guia", "amarre-cuadrado")
PAUSA = 1.5           # s quieta en la pose de la ficha al final de cada paso
QUIETA = 0.5          # s de la pausa antes de que la cámara se mueva
CAMBIO = 0.8          # s que tarda la cámara en ir de una toma a la siguiente
GIRO = math.radians(8)   # el giro lento de la cámara a lo largo de un paso
POLAR, AZ = 0.68, -0.32  # la vista «3d» de render/escena.js
FOV = 30.0
REMATE = 0.8          # d: el remate de la punta, como en render/escena.js
# Los 10 s de la prueba: desde qué paso y qué movimiento, y cuánto antes.
VENTANAS = {"as-de-guia": (4, "enhebrar", 0.5), "amarre-cuadrado": (4, "enhebrar", 0.5)}
PRUEBA = {"segundos": 10.0, "fps": 30, "tam": (1280, 720), "muestras": 64}
PREVIA = {"fps": 15, "tam": (960, 540), "muestras": 16}


@dataclass
class Cuadro:
    X: np.ndarray
    paso: int          # el paso al que se va (o en el que se está quieto)
    fase: str
    resaltado: tuple | None
    camara: dict | None = None
    visible: float | None = None   # en una plantilla (T21d), hasta dónde se ve la cuerda (σ)


# --------------------------------------------------------------------------
# La línea de tiempo
# --------------------------------------------------------------------------
def linea_de_tiempo(modelo, animados) -> list[Cuadro]:
    """Todos los cuadros del nudo: la pausa en el paso 1 y, por cada paso siguiente, su
    movimiento y su pausa en la pose de la ficha."""
    from .animar import poses_atado
    P = {r.n: r for r in poses_atado(modelo)}   # con largo fijo (T21) o con la cola en la mano (T18)
    pausa = round(PAUSA * FPS)
    primero = P[modelo.pasos[0].n]
    out = [Cuadro(primero.puntos, primero.n, "pausa", primero.resaltado,
                  visible=getattr(primero, "visible", None)) for _ in range(pausa)]
    for a in animados:
        B = P[a.n]
        fase_de = {}
        for nombre, (f0, f1) in a.fases.items():
            for f in range(f0, f1 + 1):
                fase_de[f] = nombre
        vis = getattr(a, "visible", None)
        for i, X in enumerate(a.X[1:], start=1):
            out.append(Cuadro(np.asarray(X), a.n, fase_de.get(i, "recta"), B.resaltado,
                              visible=None if vis is None else vis[i]))
        out += [Cuadro(B.puntos, a.n, "pausa", B.resaltado, visible=getattr(B, "visible", None))
                for _ in range(pausa)]
    return out


# --------------------------------------------------------------------------
# La cámara
# --------------------------------------------------------------------------
def _mirar(pos, target):
    """La matriz de la cámara (como la de three.js, en columnas) que mira de pos a target, con
    +z hacia arriba."""
    z = pos - target
    z = z / np.linalg.norm(z)
    x = np.cross([0.0, 0.0, 1.0], z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, pos
    return M


def toma(puntos, polar, az, aspecto, fov=FOV) -> dict:
    """La cámara que encuadra la caja de los puntos (de la mesa a lo más alto), con el mismo
    ajuste que `pose()` de render/escena.js: corre el centro y la distancia hasta que la caja
    ocupa el 94 % del cuadro."""
    P = np.asarray(puntos, float)
    x0, y0 = P[:, :2].min(axis=0)
    x1, y1 = P[:, :2].max(axis=0)
    z1 = max(float(P[:, 2].max()), 1.0)
    esquinas = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (0.0, z1)])
    t = np.array([(x0 + x1) / 2, (y0 + y1) / 2, 0.5])
    d = 60.0
    th = math.tan(math.radians(fov) / 2)
    direc = np.array([math.sin(polar) * math.sin(az), -math.sin(polar) * math.cos(az), math.cos(polar)])
    for _ in range(8):
        M = _mirar(t + d * direc, t)
        R, pos = M[:3, :3], M[:3, 3]
        q = (esquinas - pos) @ R          # en el marco de la cámara (mira por −z)
        px = q[:, 0] / (-q[:, 2] * th * aspecto)
        py = q[:, 1] / (-q[:, 2] * th)
        hw, hh = d * th * aspecto, d * th
        t = t + R[:, 0] * ((px.min() + px.max()) / 2) * hw + R[:, 1] * ((py.min() + py.max()) / 2) * hh
        d *= max((px.max() - px.min()) / 2, (py.max() - py.min()) / 2) / 0.94
    M = _mirar(t + d * direc, t)
    return {"pos": t + d * direc, "target": t, "fov": fov, "aspecto": aspecto,
            "centro": [float(t[0]), float(t[1])],
            "extension": float(max(x1 - x0, y1 - y0) / 2)}


def _datos_camara(c: dict) -> dict:
    M = _mirar(np.asarray(c["pos"]), np.asarray(c["target"]))
    return {"matriz": M.T.ravel().tolist(), "fov": c["fov"], "aspecto": c["aspecto"],
            "cerca": 0.5, "lejos": 500.0}


def _tapado(c: dict, puntos, solido) -> float:
    """La parte de los puntos que los palos de la cruz tapan desde la cámara."""
    if solido is None or not hasattr(solido, "zb"):
        return 0.0
    pos = np.asarray(c["pos"])
    P = np.asarray(puntos, float)
    tapados = np.zeros(len(P), bool)
    medio = solido.largo / 2
    for eje, zc in ((1, solido.zb), (0, solido.zt)):
        # Un palo a lo largo de `eje`, con el eje a la altura zc y radio solido.radio.
        otro = 1 - eje
        for k, p in enumerate(P):
            if tapados[k]:
                continue
            ts = np.linspace(0.02, 0.98, 60)
            Q = p[None, :] + ts[:, None] * (pos - p)[None, :]
            r = np.hypot(Q[:, otro], Q[:, 2] - zc)
            if np.any((r < solido.radio) & (np.abs(Q[:, eje]) < medio)):
                tapados[k] = True
    return float(tapados.mean())


def tomas(spec, modelo, cuadros: list[Cuadro], aspecto) -> dict[int, tuple[dict, dict]]:
    """La toma de cada paso animado: (al empezar, al terminar), con el giro lento entre las dos."""
    from .animar import cuerda_visible, de_plantilla
    P = {r.n: r for r in modelo.pasos}
    e = spec.encuadre
    out = {}
    movidos: dict[int, list] = {}
    for c in cuadros:
        if c.fase != "pausa":
            movidos.setdefault(c.paso, []).append(cuerda_visible(c.X, modelo.pasos[-1].h, c.visible)[0])
    for n, Xs in movidos.items():
        A, B = P[n - 1].puntos, P[n].puntos
        pts = np.vstack([A, B] + [np.asarray(x) for x in Xs[::10]])
        if e is not None:
            m = 3.0
            dentro = ((pts[:, 0] > e.x[0] - m) & (pts[:, 0] < e.x[1] + m)
                      & (pts[:, 1] > e.y[0] - m) & (pts[:, 1] < e.y[1] + m))
            pts = pts[dentro]
        az = AZ
        if spec.plantilla is not None:
            solido, _ = de_plantilla(spec, n)
            r0 = int(round(P[n].resaltado[0] / P[n].h)) if P[n].resaltado else 0
            r1 = int(round(P[n].resaltado[1] / P[n].h)) if P[n].resaltado else len(B)
            nueva = B[r0:r1:4]
            mejor = None
            for k in range(12):
                cand = AZ + math.radians(30 * k)
                c = toma(pts, POLAR, cand, aspecto)
                tap = _tapado(c, nueva, solido)
                clave = (round(tap, 2), min(k, 12 - k))
                if mejor is None or clave < mejor[0]:
                    mejor = (clave, cand)
            az = mejor[1]
        out[n] = (toma(pts, POLAR, az - GIRO / 2, aspecto), toma(pts, POLAR, az + GIRO / 2, aspecto))
    return out


def _mezclar(c0: dict, c1: dict, u: float) -> dict:
    u = u * u * (3 - 2 * u)
    out = dict(c0)
    for k in ("pos", "target"):
        out[k] = np.asarray(c0[k]) + u * (np.asarray(c1[k]) - np.asarray(c0[k]))
    out["centro"] = list(np.asarray(c0["centro"]) + u * (np.asarray(c1["centro"]) - np.asarray(c0["centro"])))
    out["extension"] = c0["extension"] + u * (c1["extension"] - c0["extension"])
    return out


def poner_camaras(cuadros: list[Cuadro], ts: dict) -> None:
    """La cámara de cada cuadro: dentro de un paso, de su toma de partida a la de llegada; en
    la pausa, quieta QUIETA s y después, en CAMBIO s, hasta la toma del paso siguiente."""
    pasos = sorted(ts)
    # Los cuadros de cada movimiento, para el giro lento.
    rango = {}
    for i, c in enumerate(cuadros):
        if c.fase != "pausa":
            r = rango.setdefault(c.paso, [i, i])
            r[1] = i
    for i, c in enumerate(cuadros):
        if c.fase != "pausa":
            f0, f1 = rango[c.paso]
            c.camara = _mezclar(*ts[c.paso], (i - f0) / max(1, f1 - f0))
    # Las pausas: la del paso 1 mira con la toma del primer paso animado; las demás, desde la
    # última toma de su paso hasta la primera del siguiente.
    for i, c in enumerate(cuadros):
        if c.fase != "pausa":
            continue
        if c.paso not in ts:
            c.camara = ts[pasos[0]][0]
            continue
        j = pasos.index(c.paso)
        f1 = rango[c.paso][1]
        t = (i - f1) / FPS
        if j + 1 < len(pasos):
            u = min(1.0, max(0.0, (t - QUIETA) / CAMBIO))
            c.camara = _mezclar(ts[c.paso][1], ts[pasos[j + 1]][0], u)
        else:
            c.camara = ts[c.paso][1]


# --------------------------------------------------------------------------
# Blender
# --------------------------------------------------------------------------
def mallas_anfitrion(modelo) -> list[dict]:
    """Las mallas del anfitrión, como las exporta render/escena.js (sin las tapas de las
    puntas de la cuerda, que van con cada cuadro)."""
    if modelo.spec.anfitrion is None:
        return []
    from .imprimir import CELDA_MM, _exportar, _servidor, chrome, imagenes, px
    img = imagenes(modelo)[0]
    with _servidor() as base, chrome() as navegador:
        escena, _ = _exportar(navegador, base, img, px(CELDA_MM[0]), px(CELDA_MM[1]))
    # Sin las tapas de las puntas («punta») ni la de la cuerda: van con cada cuadro. Con la
    # tapa de la punta del paso 1, quedaba una marca oscura fija sobre la mesa (T18).
    return [m for m in escena["mallas"] if m["rol"] not in ("cuerda", "punta")]


def _tramos(N: int, h: float, resaltado, dos_remates: bool) -> list:
    """Los tramos de material de la cuerda (base 0, resaltado 1, remate 2), en tramos entre
    nodos, como `exportar()` de escena.js."""
    T = N - 1
    w = max(1, T - int(round(REMATE / h)))
    w0 = min(w, int(round(REMATE / h))) if dos_remates else 0
    if resaltado:
        a = max(w0, min(w, int(round(resaltado[0] / h))))
        b = max(w0, min(w, int(round(resaltado[1] / h))))
    else:
        a = b = w
    return [t for t in ([0, w0, 2], [w0, a, 0], [a, b, 1], [b, w, 0], [w, T, 2]) if t[1] > t[0]]


def renderizar_cuadros(cuadros: list[Cuadro], h: float, mallas: list[dict], dos_remates: bool,
                       salida: Path, tam, muestras: int, fps: int) -> dict:
    """Dibuja los cuadros con Blender y arma el video con ffmpeg. Devuelve los tiempos."""
    from . import blender
    t0 = time.time()
    ancho, alto = tam
    with tempfile.TemporaryDirectory(prefix="nudos-atar-") as tmp:
        tmp = Path(tmp)
        base = tmp / "escena.json"
        base.write_text(json.dumps({"mallas": mallas, "camara": None, "centro": [0, 0],
                                    "extension": 10}), encoding="utf-8")
        solidos = blender._muestras_solidos(mallas) if blender.APLASTAR else None
        trabajos = []
        from .animar import cuerda_visible
        for k, c in enumerate(cuadros):
            X = cuerda_visible(c.X, h, getattr(c, "visible", None))[0]
            esc = {"cuerdas": [{"espina": X.ravel().tolist(), "radio": 0.5, "grosor": 1.0,
                                "color": "azul", "tramos": _tramos(len(X), h, c.resaltado, dos_remates)}],
                   "mallas": mallas}
            m = blender.malla_cuerda(0, esc, solidos=solidos)
            ruta = tmp / f"c{k:05d}.npz"
            np.savez(ruta, vertices=m.vertices.astype(np.float32), caras=m.caras.astype(np.int32),
                     uv=m.uv.astype(np.float32), material=m.material, s=m.s.astype(np.float32))
            trabajos.append({"escena": str(base),
                             "cuerdas": [{"malla": str(ruta), "color": "azul", "grosor": 1.0,
                                          "aplastado": float(m.aplastado.max())}],
                             "camara": _datos_camara(c.camara), "centro": c.camara["centro"],
                             "extension": c.camara["extension"],
                             "salida": str(tmp / f"r{k:05d}.png")})
        t_mallas = time.time() - t0
        blender.renderizar(trabajos, ancho, alto, muestras)
        t_blender = time.time() - t0 - t_mallas
        for k, t in enumerate(trabajos):
            blender.componer(Path(t["salida"]), None, ancho, alto).save(tmp / f"f{k:05d}.png")
        salida.parent.mkdir(parents=True, exist_ok=True)
        orden = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                 str(tmp / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
                 "-movflags", "+faststart", str(salida)]
        subprocess.run(orden, check=True)
    return {"cuadros": len(cuadros), "segundos_mallas": round(t_mallas, 1),
            "segundos_blender": round(t_blender, 1),
            "por_cuadro": round(t_blender / max(1, len(cuadros)), 2)}


# --------------------------------------------------------------------------
# La prueba
# --------------------------------------------------------------------------
def ventana(cuadros: list[Cuadro], slug: str, fps: int, segundos: float) -> list[Cuadro]:
    """Los cuadros de los 10 s de la prueba, uno de cada FPS/fps."""
    paso, fase, antes = VENTANAS[slug]
    i0 = next(i for i, c in enumerate(cuadros) if c.paso == paso and c.fase == fase)
    i0 = max(0, i0 - round(antes * FPS))
    i1 = min(len(cuadros), i0 + round(segundos * FPS))
    return cuadros[i0:i1:FPS // fps]


def guardar(slug: str, cuadros: list[Cuadro], animados, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destino / f"{slug}.npz",
                        **{f"c{k:05d}": np.asarray(c.X, np.float32) for k, c in enumerate(cuadros)})
    info = {"fps": FPS, "cuadros": [{"paso": c.paso, "fase": c.fase, "visible": c.visible} for c in cuadros],
            "tramos": [{"paso": a.n, "modo": a.modo, "fases": a.fases, "medidas": a.medidas,
                        "fallas": a.fallas} for a in animados]}
    (destino / f"{slug}.json").write_text(json.dumps(info, indent=1, ensure_ascii=False),
                                          encoding="utf-8")


def cargar_cuadros(slug: str, modelo, destino: Path = DESTINO) -> list[Cuadro]:
    """Los cuadros que guardó `guardar`, con su paso, su movimiento y el resaltado del paso."""
    info = json.loads((destino / f"{slug}.json").read_text(encoding="utf-8"))
    P = {r.n: r for r in modelo.pasos}
    with np.load(destino / f"{slug}.npz") as z:
        return [Cuadro(z[f"c{k:05d}"].astype(float), c["paso"], c["fase"], P[c["paso"]].resaltado,
                       visible=c.get("visible")) for k, c in enumerate(info["cuadros"])]


def videos(slugs=PILOTOS, destino: Path = DESTINO, previa: bool = True) -> dict:
    """Los videos de la prueba desde los cuadros ya guardados, sin volver a atar."""
    from .prueba_blender import construir_pilotos
    modelos = construir_pilotos(slugs)
    informe = {}
    for slug in slugs:
        m = modelos[slug]
        cuadros = cargar_cuadros(slug, m, destino)
        informe[slug] = _videos(slug, m, cuadros, destino, True, previa)
    return informe


def _videos(slug, m, cuadros, destino, video: bool, previa: bool) -> dict:
    out = {}
    dos = m.spec.plantilla is not None
    h = m.pasos[-1].h
    mallas = mallas_anfitrion(m)
    if video:
        asp = PRUEBA["tam"][0] / PRUEBA["tam"][1]
        poner_camaras(cuadros, tomas(m.spec, m, cuadros, asp))
        sel = ventana(cuadros, slug, PRUEBA["fps"], PRUEBA["segundos"])
        out["prueba"] = renderizar_cuadros(sel, h, mallas, dos, destino / f"{slug}-prueba.mp4",
                                           PRUEBA["tam"], PRUEBA["muestras"], PRUEBA["fps"])
        print(f"  {slug}, prueba: {out['prueba']}", flush=True)
    if previa:
        asp = PREVIA["tam"][0] / PREVIA["tam"][1]
        poner_camaras(cuadros, tomas(m.spec, m, cuadros, asp))
        sel = cuadros[::FPS // PREVIA["fps"]]
        out["previa"] = renderizar_cuadros(sel, h, mallas, dos, destino / f"{slug}-previa.mp4",
                                           PREVIA["tam"], PREVIA["muestras"], PREVIA["fps"])
        print(f"  {slug}, previa: {out['previa']}", flush=True)
    return out


def prueba(slugs=PILOTOS, destino: Path = DESTINO, video: bool = True, previa: bool = True) -> dict:
    from .animar import animar
    from .prueba_blender import construir_pilotos
    t0 = time.time()
    modelos = construir_pilotos(slugs)
    informe = {}
    for slug in slugs:
        m = modelos[slug]
        if m.fallas:
            raise RuntimeError(f"{slug}: el nudo tiene fallas con el motor")
        t = time.time()
        animados = animar(m.spec, m)
        cuadros = linea_de_tiempo(m, animados)
        guardar(slug, cuadros, animados, destino)
        fallas = [f for a in animados for f in a.fallas]
        informe[slug] = {"segundos_motor": round(time.time() - t, 1),
                         "segundos_video": round(len(cuadros) / FPS, 1), "fallas": fallas,
                         "tramos": {a.n: a.medidas for a in animados}}
        print(f"{slug}: {len(cuadros)} cuadros ({len(cuadros) / FPS:.1f} s) en "
              f"{time.time() - t:.0f} s; {len(fallas)} fallas", flush=True)
        for f in fallas:
            print("  -", f, flush=True)
        if video or previa:
            informe[slug].update(_videos(slug, m, cuadros, destino, video, previa))
    informe["segundos"] = round(time.time() - t0, 1)
    (destino / "informe.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False,
                                                     default=str), encoding="utf-8")
    return informe
