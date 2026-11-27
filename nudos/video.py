"""Los videos de cada nudo (T18).

`python -m nudos video <slug> [...]` (o `--todos`) construye el nudo con el motor, lo ata con el
modo «atar» de T17 (`nudos/animar.py`), arma la línea de tiempo y dibuja en Blender:

- `<slug>-4k.mp4`, el horizontal para YouTube: 3840 × 2160 a 60 cuadros por segundo y 68 Mbps;
- `<slug>-visor.mp4`, su copia en 1920 × 1080 para el visor, con un tope de TOPE_VISOR MB, que
  se copia también a `videos/<slug>.mp4` del repositorio;
- `<slug>-vertical.mp4`, el vertical para Instagram: 1080 × 1920 a 60 fps y 20 Mbps, con su
  propia cámara.

Los tres llevan el audio de nudos/audio.py (el clic de cada título, el golpe del apretado y el
roce de la cuerda), que se pega aparte: cambiarlo no obliga a volver a dibujar.

El aspecto es el de T20b (nudos/aspecto.py): la cuerda real con la trenza en la geometría, en el
estudio de madera, con Cycles a 16 muestras, profundidad de campo con el foco en la punta,
desenfoque de movimiento, y viñeta y grano al armar.

Con `--previa`, el nudo entero en 960 × 540, 30 fps y 16 muestras, para revisar los tiempos, la
cámara, los títulos y el audio antes del render largo. Con `--prueba`, 10 s del paso 4 en 4K.

Todo se puede retomar: el atado se guarda con la huella del nudo y del código de la animación,
cada cuadro dibujado con la huella de lo que muestra, y cada video terminado con la huella de sus
cuadros. Volver a correr la orden hace solo lo que falta. Los cuadros (decenas de GB en 4K) van
fuera de A:, en NUDOS_CUADROS, y los videos, en NUDOS_VIDEOS.

Necesita Edge o Chrome (NUDOS_CHROME), Blender 5.2 y ffmpeg.
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import RAIZ, SPECS
from .fisica.atar import FPS

VIDEOS_REPO = RAIZ / "videos"
TOPE_VISOR = 20.0          # MB
PAUSA = 1.5                # s quieta en la pose de cada paso
PAUSA_INICIO = 2.0         # s en el paso 1, con el nombre del nudo
PAUSA_FINAL = 2.5          # s en el nudo apretado
ACERCAR = 0.10             # la cámara se acerca esto en la pausa final
QUIETA = 0.5               # s de la pausa antes de que la cámara se mueva
CAMBIO = 0.8               # s que tarda la cámara en ir de una toma a la siguiente
GIRO = math.radians(8)     # el giro lento a lo largo de un paso
POLAR, AZ, FOV = 0.68, -0.32, 30.0   # la vista «3d» de render/escena.js
ANTES_DEL_NUDO = 6.0       # d: la toma empieza tanto antes del primer cruce
SEMIANCHO_MIN = 8.0        # d
LENTO = 6.0                # d: en una plantilla, la primera cuerda nueva de cada paso va a 1×
RAPIDO, MUY_RAPIDO = 3.0, 5.0   # lo demás de cada paso, y lo de un paso que repite (T18)
RAMPA_VEL = 0.5            # s: lo que tarda un cambio de velocidad
FUNDIDO = 0.25             # s: los títulos
AVISO_CADA = 10            # cuadros: cada cuántos imprime el avance

FORMATOS = {
    # tam, cuadros por segundo, muestras (None: las del motor del video, aspecto.MOTOR_VIDEO),
    # área útil del nudo (x0, y0, x1, y1 en fracciones del cuadro, y hacia abajo), el CSS del
    # título y su escala.
    "horizontal": {"tam": (3840, 2160), "fps": 60, "muestras": None, "area": (0.05, 0.05, 0.95, 0.78),
                   "css": (1920, 1080), "escala": 2.0},
    "vertical": {"tam": (1080, 1920), "fps": 60, "muestras": None, "area": (0.05, 0.29, 0.95, 0.76),
                 "css": (1080, 1920), "escala": 1.0},
    "previa": {"tam": (960, 540), "fps": 30, "muestras": 16, "area": (0.05, 0.05, 0.95, 0.78),
               "css": (1920, 1080), "escala": 0.5},
}


class VideoError(Exception):
    """El video no se puede armar así."""


def carpeta_cuadros(slug: str) -> Path:
    base = os.environ.get("NUDOS_CUADROS") or str(Path(os.environ.get("LOCALAPPDATA", Path.home()))
                                                  / "nudos" / "cuadros")
    return Path(base) / slug


def carpeta_videos(slug: str | None = None) -> Path:
    """Donde quedan los videos: build/videos/<slug>/ en la carpeta del libro (Gabriel, 25 nov),
    o NUDOS_VIDEOS."""
    base = Path(os.environ.get("NUDOS_VIDEOS") or RAIZ / "build" / "videos")
    return base if slug is None else base / slug


def _huella(*partes) -> str:
    h = hashlib.sha256()
    for p in partes:
        if isinstance(p, np.ndarray):
            h.update(np.ascontiguousarray(p, np.float64).tobytes())
        elif isinstance(p, (bytes, bytearray)):
            h.update(p)
        else:
            h.update(json.dumps(p, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def _codigo(*rutas) -> bytes:
    return b"".join((RAIZ / r).read_bytes() for r in rutas)


# --------------------------------------------------------------------------
# El atado, guardado
# --------------------------------------------------------------------------
CODIGO_ATAR = ("nudos/animar.py", "nudos/fisica/atar.py", "nudos/fisica/integrador.py",
               "nudos/fisica/contacto.py", "nudos/fisica/asentar.py", "nudos/apretar.py")


@dataclass
class Tramo:
    """Lo que guarda el atado de un tramo (del paso n − 1 al n, o el apretado)."""
    n: int
    modo: str
    X: list
    fases: dict
    fallas: list
    medidas: dict


def atar(modelo, rehacer: bool = False) -> tuple[list[Tramo], str]:
    """Los tramos atados del nudo, desde lo guardado si la huella coincide. Da también la
    huella."""
    from .animar import animar, animar_apretado, poses_atado
    P = poses_atado(modelo)
    if modelo.spec.plantilla is None and modelo.apretado is not None and (P[-1].o > 0 or P[-1].cola > 0):
        raise VideoError(f"{modelo.spec.slug}: el último paso lleva depósito o cola de más, y el "
                         "apretado del video todavía no los sabe llevar")
    ap = modelo.apretado.puntos if modelo.apretado is not None else np.zeros((0, 3))
    huella = _huella(*[p.puntos for p in P], ap, _codigo(*CODIGO_ATAR))
    dest = carpeta_cuadros(modelo.spec.slug)
    ruta_npz, ruta_json = dest / "atado.npz", dest / "atado.json"
    if not rehacer and ruta_json.exists() and ruta_npz.exists():
        info = json.loads(ruta_json.read_text(encoding="utf-8"))
        if info.get("huella") == huella:
            with np.load(ruta_npz) as z:
                tramos = [Tramo(t["n"], t["modo"],
                                [z[f"t{k}c{i}"].astype(float) for i in range(t["cuadros"])],
                                {a: tuple(b) for a, b in t["fases"].items()}, t["fallas"], t["medidas"])
                          for k, t in enumerate(info["tramos"])]
            return tramos, huella
    animados = animar(modelo.spec, modelo)
    final = animar_apretado(modelo.spec, modelo)
    if final is not None:
        animados.append(final)
    tramos = [Tramo(a.n, a.modo, [np.asarray(x, float) for x in a.X], dict(a.fases), list(a.fallas),
                    dict(a.medidas)) for a in animados]
    dest.mkdir(parents=True, exist_ok=True)
    arrays = {f"t{k}c{i}": np.asarray(x, np.float32) for k, t in enumerate(tramos)
              for i, x in enumerate(t.X)}
    np.savez_compressed(ruta_npz, **arrays)
    info = {"huella": huella, "tramos": [{"n": t.n, "modo": t.modo, "cuadros": len(t.X),
                                          "fases": t.fases, "fallas": t.fallas, "medidas": t.medidas}
                                         for t in tramos]}
    ruta_json.write_text(json.dumps(info, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    # Lo guardado vuelve como float32: se relee para que el video no dependa de si se ató ahora.
    return atar(modelo)[0], huella


# --------------------------------------------------------------------------
# La línea de tiempo
# --------------------------------------------------------------------------
@dataclass
class Cuadro:
    X: np.ndarray
    paso: int              # el paso al que va (o en el que está quieto); N + 1 es el apretado
    fase: str
    resaltado: tuple | None   # a lo largo de la cuerda (con largo fijo, en σ)
    titulo: int = 0        # el paso cuyo título se ve (0: el nombre del nudo solo)
    alfa: float = 1.0      # el del título
    camara: dict | None = None
    acercar: float = 0.0
    foco: np.ndarray | None = None   # el punto que sigue el foco (sin él, la punta de la cuerda)


def _es_serie(spec, n: int) -> bool:
    """En una plantilla, un paso que termina una serie (`vueltas`, `ahorcados`): repite el
    movimiento del paso de antes."""
    if spec.plantilla is None or n > len(spec.pasos):
        return False
    hasta = spec.pasos[n - 1].hasta or ""
    return "-" not in hasta and hasta not in ("inicio", "cierre")


FOCO_MANO = (6.0, 12.0)   # d: el foco va pasando a la mano cuando la punta está a menos de esto
                          # de la punta del paso (con largo fijo, la punta de la cuerda puede estar
                          # lejos, al final de la cola de más)


def _foco_de(p) -> np.ndarray | None:
    """Con largo fijo (T21), la punta del tramo de la ficha de la pose; si no, nada (el foco
    sigue la punta de la cuerda)."""
    if not hasattr(p, "tramo_ficha"):
        return None
    return np.asarray(p.X[p.tramo_ficha()[1]], float)


def _foco_mano(X, destino) -> np.ndarray | None:
    """El foco mientras se ata: la punta del paso de llegada, y la mano (la punta de la cuerda)
    a medida que se acerca a ella."""
    if destino is None:
        return None
    p = np.asarray(X[-1], float)
    d = float(np.linalg.norm((p - destino)[:2]))
    w = float(np.clip((FOCO_MANO[1] - d) / (FOCO_MANO[1] - FOCO_MANO[0]), 0.0, 1.0))
    w = w * w * (3 - 2 * w)
    return w * p + (1 - w) * destino


def simulacion(modelo, tramos: list[Tramo]) -> tuple[list[Cuadro], np.ndarray]:
    """Los cuadros de la simulación con sus pausas, y la velocidad del video en cada uno."""
    from .animar import poses_atado
    spec = modelo.spec
    P = {p.n: p for p in poses_atado(modelo)}
    ultimo = modelo.pasos[-1].n
    out: list[Cuadro] = []
    vel: list[float] = []

    def pausa(X, n, seg, res, titulo, foco=None):
        for _ in range(round(seg * FPS)):
            out.append(Cuadro(np.asarray(X, float), n, "pausa", res, titulo, foco=foco))
            vel.append(1.0)

    primero = P[modelo.pasos[0].n]
    pausa(primero.puntos, primero.n, PAUSA_INICIO, primero.resaltado, primero.n, _foco_de(primero))
    for t in tramos:
        apretar = t.modo == "apretar"
        res = None if apretar else P[t.n].resaltado
        destino = None if apretar else _foco_de(P[t.n])
        fase_de = {}
        for nombre, (f0, f1) in t.fases.items():
            for f in range(f0, f1 + 1):
                fase_de[f] = nombre
        N0 = len(t.X[0])
        h = modelo.pasos[-1].h
        for i, X in enumerate(t.X[1:], start=1):
            fase = fase_de.get(i, "recta")
            v = 1.0
            if spec.plantilla is not None and fase in ("enhebrar", "recoger") and not apretar:
                if (len(X) - N0) * h >= LENTO:
                    v = MUY_RAPIDO if _es_serie(spec, t.n) else RAPIDO
            out.append(Cuadro(np.asarray(X, float), t.n, fase, res, 0 if apretar else t.n,
                              foco=_foco_mano(X, destino)))
            vel.append(v)
        if apretar:
            pausa(t.X[-1], t.n, PAUSA_FINAL, None, 0)
        else:
            pausa(P[t.n].puntos, t.n, PAUSA, res, t.n, destino)
    if tramos and tramos[-1].modo != "apretar":
        pausa(P[ultimo].puntos, ultimo, PAUSA_FINAL - PAUSA, P[ultimo].resaltado, ultimo,
              _foco_de(P[ultimo]))
    v = np.array(vel)
    # Los cambios de velocidad, suaves.
    k = max(1, int(RAMPA_VEL * FPS))
    v = np.convolve(np.pad(v, (k // 2, k - 1 - k // 2), mode="edge"), np.ones(k) / k, mode="valid")
    # El promedio de unos da 0,9999999999999999, y `retiempo` corría un cuadro cada tanto.
    v = np.where(np.abs(v - 1.0) < 1e-9, 1.0, v)
    return out, v


def retiempo(sim: list[Cuadro], vel: np.ndarray, fps: int) -> list[Cuadro]:
    """Los cuadros del video a `fps`, recorriendo la simulación a la velocidad `vel`. Un cuadro
    que cae entre dos de la simulación se interpola en línea recta, que es lo que `comprobar`
    verificó como libre; donde cambia la cantidad de nodos, se toma el más cercano."""
    paso_sim = FPS / fps                      # cuadros de la simulación por cuadro del video a 1×
    tau = np.concatenate([[0.0], np.cumsum(1.0 / vel[:-1])])   # el tiempo del video, en cuadros de 60
    out = []
    f = 0.0
    while f <= tau[-1] + 1e-9:
        k = int(np.clip(np.searchsorted(tau, f, side="right") - 1, 0, len(sim) - 1))
        c = sim[k]
        X, foco = c.X, c.foco
        if k + 1 < len(sim):
            u = (f - tau[k]) * vel[k]
            b = sim[k + 1]
            if len(b.X) == len(X) and u > 1e-9:
                X = X + u * (b.X - X)
                if foco is not None and b.foco is not None:
                    foco = foco + u * (b.foco - foco)
            elif u > 0.5:
                c, X, foco = b, b.X, b.foco
        out.append(Cuadro(X, c.paso, c.fase, c.resaltado, c.titulo, foco=foco))
        f += paso_sim
    return out


def alfas(cuadros: list[Cuadro], fps: int) -> None:
    """El fundido de los títulos: cada uno aparece y se va en FUNDIDO s."""
    k = max(1, int(round(FUNDIDO * fps)))
    n = len(cuadros)
    i = 0
    while i < n:
        j = i
        while j < n and cuadros[j].titulo == cuadros[i].titulo:
            j += 1
        for m in range(i, j):
            a = 1.0
            if i > 0:
                a = min(a, (m - i + 1) / k)
            if j < n:
                a = min(a, (j - m) / k)
            cuadros[m].alfa = float(np.clip(a, 0.0, 1.0))
        i = j


# --------------------------------------------------------------------------
# La cámara
# --------------------------------------------------------------------------
def _mirar(pos, target):
    from .prueba_atar import _mirar as m
    return m(pos, target)


def toma(puntos, polar, az, aspecto, area=(0.03, 0.03, 0.97, 0.97), fov=FOV) -> dict:
    """La cámara que encuadra la caja de los puntos (de la mesa a lo más alto) dentro del área
    útil del cuadro (x0, y0, x1, y1, en fracciones, con y hacia abajo)."""
    P = np.asarray(puntos, float)
    x0, y0 = P[:, :2].min(axis=0)
    x1, y1 = P[:, :2].max(axis=0)
    z1 = max(float(P[:, 2].max()), 1.0)
    esquinas = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (0.0, z1)])
    ax0, ay0, ax1, ay1 = area
    cx_t, cy_t = (ax0 + ax1) - 1.0, 1.0 - (ay0 + ay1)        # el centro del área, en [-1, 1]
    wx_t, wy_t = 2 * (ax1 - ax0), 2 * (ay1 - ay0)
    t = np.array([(x0 + x1) / 2, (y0 + y1) / 2, 0.5])
    d = 60.0
    th = math.tan(math.radians(fov) / 2)
    direc = np.array([math.sin(polar) * math.sin(az), -math.sin(polar) * math.cos(az), math.cos(polar)])
    for _ in range(12):
        M = _mirar(t + d * direc, t)
        R, pos = M[:3, :3], M[:3, 3]
        q = (esquinas - pos) @ R
        px = q[:, 0] / (-q[:, 2] * th * aspecto)
        py = q[:, 1] / (-q[:, 2] * th)
        hw, hh = d * th * aspecto, d * th
        t = t + R[:, 0] * ((px.min() + px.max()) / 2 - cx_t) * hw \
              + R[:, 1] * ((py.min() + py.max()) / 2 - cy_t) * hh
        d *= max((px.max() - px.min()) / wx_t, (py.max() - py.min()) / wy_t)
    return {"pos": t + d * direc, "target": t, "fov": fov, "aspecto": aspecto, "d": d,
            "centro": [float((x0 + x1) / 2), float((y0 + y1) / 2)],
            "extension": float(max(x1 - x0, y1 - y0) / 2)}


def _datos_camara(c: dict) -> dict:
    M = _mirar(np.asarray(c["pos"]), np.asarray(c["target"]))
    return {"matriz": M.T.ravel().tolist(), "fov": c["fov"], "aspecto": c["aspecto"],
            "cerca": 0.5, "lejos": 500.0}


def _primer_cruce(X, h) -> float | None:
    from .cruces import encontrar_cruces
    return min((min(c.sa, c.sb) for c in encontrar_cruces(np.asarray(X, float), h)), default=None)


def puntos_del_nudo(X, h, s0=None, corrido: int = 0) -> np.ndarray:
    """La cuerda desde ANTES_DEL_NUDO d antes de su primer cruce (vista desde arriba) hasta la
    punta: el firme lejano sale del cuadro. Sin cruces, desde `s0` (el primer cruce del paso
    siguiente), con los nodos `corrido` que ese paso tiene de más en el firme."""
    X = np.asarray(X, float)
    propio = _primer_cruce(X, h)
    if propio is not None:
        return X[max(0, int((propio - ANTES_DEL_NUDO) / h)):]
    if s0 is not None:
        return X[max(0, int((s0 - ANTES_DEL_NUDO) / h) - corrido):]
    return X


def _sigma_primer_cruce(p) -> float | None:
    """El primer cruce del tramo de la ficha de una pose con largo fijo, en σ."""
    a, b = p.tramo_ficha()
    c = _primer_cruce(p.X[a:b + 1], p.h)
    return None if c is None else a * p.h + c


def _nudo_del_video(p, s_otro=None) -> tuple[int, int]:
    """Los nodos de una pose con largo fijo que encuadra la cámara: desde ANTES_DEL_NUDO antes
    de su primer cruce (sin cruces, del `s_otro` del paso siguiente) hasta la punta de la ficha."""
    a, b = p.tramo_ficha()
    s = _sigma_primer_cruce(p)
    s = s_otro if s is None else s
    return (a if s is None else max(a, int((s - ANTES_DEL_NUDO) / p.h))), b


def _con_minimo(pts: np.ndarray) -> np.ndarray:
    """Los puntos, con una caja de SEMIANCHO_MIN d como mínimo alrededor de su centro."""
    c = (pts[:, :2].min(axis=0) + pts[:, :2].max(axis=0)) / 2
    caja = np.array([[c[0] + sx * SEMIANCHO_MIN, c[1] + sy * SEMIANCHO_MIN, 0.0]
                     for sx in (-1, 1) for sy in (-1, 1)])
    return np.vstack([pts, caja])


def tomas(modelo, sim: list[Cuadro], formato: str) -> tuple[dict, float]:
    """La toma de cada paso animado (al empezar, al terminar) en el formato, y el ángulo
    alrededor de la mesa de un nudo libre."""
    from .animar import de_plantilla, poses_atado
    from .prueba_atar import _tapado
    F = FORMATOS[formato]
    asp = F["tam"][0] / F["tam"][1]
    area = F["area"]
    spec = modelo.spec
    P = {p.n: p for p in poses_atado(modelo)}
    h = modelo.pasos[-1].h
    movidos: dict[int, list] = {}
    for c in sim:
        if c.fase != "pausa":
            movidos.setdefault(c.paso, []).append(c.X)
    pts_de = {}
    for n, Xs in movidos.items():
        A = P[n - 1].puntos if n - 1 in P else P[n].puntos
        B = P[n].puntos if n in P else Xs[-1]
        if spec.plantilla is None:
            # Con largo fijo (T21), los mismos nodos son la misma cuerda en todos los pasos: la
            # toma va de ANTES_DEL_NUDO antes del primer cruce a la punta de la ficha, sin el
            # depósito ni la cola de más.
            pa = P[n - 1] if n - 1 in P else P[n]
            pb = P[n] if n in P else pa
            sB = _sigma_primer_cruce(pb)
            ia = _nudo_del_video(pa, sB)
            ib = _nudo_del_video(pb, sB)
            i0, i1 = min(ia[0], ib[0]), max(ia[1], ib[1])
            partes = [pa.X[ia[0]:ia[1] + 1], pb.X[ib[0]:ib[1] + 1]]
            partes += [np.asarray(x)[i0:i1 + 1] for x in Xs[::10]]
            pts = _con_minimo(np.vstack(partes))
        else:
            pts = np.vstack([A, B] + [np.asarray(x) for x in Xs[::10]])
            e = spec.encuadre
            if e is not None:
                m = 3.0
                dentro = ((pts[:, 0] > e.x[0] - m) & (pts[:, 0] < e.x[1] + m)
                          & (pts[:, 1] > e.y[0] - m) & (pts[:, 1] < e.y[1] + m))
                pts = pts[dentro]
        pts_de[n] = pts
    az_libre = AZ
    if spec.plantilla is None and formato == "vertical":
        # El vertical puede girar el nudo hasta 90° respecto de la ficha (Gabriel, 25 nov), para
        # que salga lo más grande posible: el ángulo que deja la cámara más cerca del nudo
        # terminado.
        fin = pts_de[max(pts_de)]
        cands = [AZ + math.radians(30 * k) for k in range(-3, 4)]
        az_libre = min(cands, key=lambda a: (round(toma(fin, POLAR, a, asp, area)["d"], 1),
                                             abs(a - AZ)))
    out = {}
    for n, pts in pts_de.items():
        az = az_libre
        if spec.plantilla is not None:
            ref = n if n in P else max(P)
            solido, _ = de_plantilla(spec, ref)
            B = P[ref].puntos
            res = P[ref].resaltado
            r0 = int(round(res[0] / h)) if res else 0
            r1 = int(round(res[1] / h)) if res else len(B)
            nueva = B[r0:r1:4] if r1 > r0 else B[::8]
            mejor = None
            for k in range(12):
                cand = AZ + math.radians(30 * k)
                c = toma(pts, POLAR, cand, asp, area)
                clave = (round(_tapado(c, nueva, solido), 2), min(k, 12 - k))
                if mejor is None or clave < mejor[0]:
                    mejor = (clave, cand)
            az = mejor[1]
            if n not in P:      # el apretado mira como el último paso
                az = out[max(out)][2] if out else az
        out[n] = (toma(pts, POLAR, az - GIRO / 2, asp, area), toma(pts, POLAR, az + GIRO / 2, asp, area), az)
    return {n: v[:2] for n, v in out.items()}, az_libre


def _mezclar(c0: dict, c1: dict, u: float) -> dict:
    from .prueba_atar import _mezclar as m
    return m(c0, c1, u)


def _acercada(c: dict, u: float) -> dict:
    out = dict(c)
    pos, t = np.asarray(c["pos"]), np.asarray(c["target"])
    out["pos"] = t + (1 - u * u * (3 - 2 * u) * ACERCAR) * (pos - t)
    return out


def poner_camaras(cuadros: list[Cuadro], ts: dict, fps: int) -> None:
    """La cámara de cada cuadro: dentro de un paso, de su toma de partida a la de llegada (el
    giro lento); en la pausa, quieta QUIETA s y después, en CAMBIO s, hasta la del paso
    siguiente. En la pausa final, se acerca un ACERCAR."""
    pasos = sorted(ts)
    rango = {}
    for i, c in enumerate(cuadros):
        if c.fase != "pausa":
            r = rango.setdefault(c.paso, [i, i])
            r[1] = i
    for i, c in enumerate(cuadros):
        if c.fase != "pausa":
            f0, f1 = rango[c.paso]
            c.camara = _mezclar(*ts[c.paso], (i - f0) / max(1, f1 - f0))
    final = [i for i, c in enumerate(cuadros) if c.fase == "pausa" and c.paso == pasos[-1]
             and i > rango[pasos[-1]][1]]
    for i, c in enumerate(cuadros):
        if c.fase != "pausa":
            continue
        if c.paso not in rango or i < rango[c.paso][0]:
            c.camara = ts[pasos[0]][0]
            continue
        j = pasos.index(c.paso)
        t = (i - rango[c.paso][1]) / fps
        if j + 1 < len(pasos):
            u = min(1.0, max(0.0, (t - QUIETA) / CAMBIO))
            c.camara = _mezclar(ts[c.paso][1], ts[pasos[j + 1]][0], u)
        else:
            u = (i - final[0]) / max(1, len(final) - 1) if final else 0.0
            c.camara = _acercada(ts[c.paso][1], u)


# --------------------------------------------------------------------------
# Los títulos
# --------------------------------------------------------------------------
TITULO_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Big Shoulders Display"; font-weight: 700; src: url("fuentes/big-shoulders-display-latin-700-normal.woff2"); }}
@font-face {{ font-family: "Big Shoulders Display"; font-weight: 800; src: url("fuentes/big-shoulders-display-latin-800-normal.woff2"); }}
@font-face {{ font-family: "IBM Plex Mono"; font-weight: 500; src: url("fuentes/ibm-plex-mono-latin-500-normal.woff2"); }}
@font-face {{ font-family: "Literata"; font-weight: 600; src: url("fuentes/literata-latin-600-normal.woff2"); }}
html, body {{ margin: 0; background: transparent; }}
body {{ width: {w}px; height: {h}px; position: relative; overflow: hidden; }}
.tarjeta {{ position: absolute; {lugar} max-width: {ancho}px; padding: {pad}px {padx}px;
  background: rgba(247, 249, 250, 0.90); border-radius: {radio}px; color: #16202f;
  box-shadow: 0 {sombra}px {sombra2}px rgba(22, 32, 47, 0.10); }}
.nudo {{ font-family: "Big Shoulders Display"; font-weight: 800; text-transform: uppercase;
  font-size: {f_nudo}px; line-height: 0.9; letter-spacing: 0.01em; }}
.fila {{ display: flex; align-items: baseline; gap: {gap}px; }}
.num {{ font-family: "Big Shoulders Display"; font-weight: 700; font-size: {f_num}px; line-height: 0.9;
  color: #d1801a; font-variant-numeric: tabular-nums; }}
.de {{ font-family: "IBM Plex Mono"; font-weight: 500; font-size: {f_de}px; text-transform: uppercase;
  letter-spacing: 0.09em; color: #586273; }}
.t {{ font-family: "Literata"; font-weight: 600; font-size: {f_t}px; line-height: 1.18; margin-top: {mt}px;
  text-wrap: balance; }}
.nudo + .fila {{ margin-top: {mt}px; }}
</style></head><body><div class="tarjeta" id="t">{contenido}</div></body></html>"""


def _html_titulo(formato: str, nudo: str, n: int | None, total: int, titulo: str | None) -> str:
    import html as h
    F = FORMATOS[formato]
    w, hh = F["css"]
    vertical = formato == "vertical"
    if vertical:
        lugar = f"left: {round(w * 0.06)}px; top: {round(hh * 0.11)}px;"
        ancho = round(w * 0.86)
        f = 1.6
    else:
        lugar = f"left: {round(w * 0.05)}px; bottom: {round(hh * 0.06)}px;"
        ancho = round(w * 0.55)
        f = 1.15
    partes = []
    if n is None or n == 1:
        partes.append(f'<div class="nudo">{h.escape(nudo)}</div>')
    if n is not None:
        partes.append(f'<div class="fila"><span class="num">{n}</span>'
                      f'<span class="de">Paso {n} de {total}</span></div>')
        partes.append(f'<div class="t" id="texto">{h.escape(titulo or "")}</div>')
    return TITULO_HTML.format(
        w=w, h=hh, lugar=lugar, ancho=ancho, pad=round(18 * f), padx=round(26 * f), radio=round(14 * f),
        sombra=round(4 * f), sombra2=round(18 * f), f_nudo=round(64 * f), f_num=round(58 * f),
        f_de=round(19 * f), f_t=round(40 * f), gap=round(14 * f), mt=round(6 * f),
        contenido="".join(partes))


def titulos(modelo, formatos: list[str]) -> dict[tuple[str, int], Image.Image]:
    """La imagen del título de cada paso (y la del nombre del nudo solo, con la clave 0) en
    cada formato, dibujada por Edge con las fuentes del sitio sobre fondo transparente."""
    from .exportar import SITIO
    from .ficha import terminos_encontrados
    from .imprimir import chrome
    spec = modelo.spec
    total = len(spec.pasos)
    textos = {p.n: p.titulo for p in spec.pasos}
    malos = terminos_encontrados(" ".join([spec.nombre, *textos.values()]))
    if malos:
        raise VideoError(f"{spec.slug}: el título usa términos de sección: {', '.join(malos)}")
    out = {}
    with tempfile.TemporaryDirectory(prefix="nudos-titulos-") as tmp, chrome() as navegador:
        raiz = Path(tmp)
        shutil.copytree(SITIO / "vendor" / "fuentes", raiz / "fuentes")
        srv, url = _servir(raiz)
        for formato in formatos:
            F = FORMATOS[formato]
            w, hh = F["css"]
            ctx = navegador.new_context(viewport={"width": w, "height": hh},
                                        device_scale_factor=F["tam"][0] / w, color_scheme="light")
            try:
                pagina = ctx.new_page()
                for n in [0, *textos]:
                    ruta = raiz / f"{formato}-{n}.html"
                    ruta.write_text(_html_titulo(formato, spec.nombre, n or None, total,
                                                 textos.get(n)), encoding="utf-8")
                    pagina.goto(url + ruta.name, wait_until="load")
                    pagina.evaluate("async () => { await document.fonts.ready; return true; }")
                    if n:
                        lineas = pagina.evaluate(
                            "() => { const e = document.getElementById('texto');"
                            " return Math.round(e.getBoundingClientRect().height /"
                            " parseFloat(getComputedStyle(e).lineHeight)); }")
                        if lineas > 2:
                            raise VideoError(f"{spec.slug}: el título del paso {n} no cabe en dos "
                                             f"líneas en el formato {formato} ({lineas}).")
                    png = pagina.screenshot(type="png", omit_background=True)
                    im = Image.open(io.BytesIO(png)).convert("RGBA")
                    if im.size != tuple(F["tam"]):
                        im = im.resize(F["tam"], Image.Resampling.LANCZOS)
                    out[(formato, n)] = im
            finally:
                ctx.close()
        srv.shutdown()
        srv.server_close()
    return out


def _servir(raiz: Path):
    """Un servidor local de la carpeta: Chrome no carga fuentes desde file://."""
    import functools
    import http.server
    import threading

    class Callado(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Callado, directory=str(raiz)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/"


# --------------------------------------------------------------------------
# Blender y ffmpeg
# --------------------------------------------------------------------------
# Lo que cambia el dibujo de un cuadro: la escena y los materiales del aspecto de T20b.
CODIGO_RENDER = ("render/blender/escena.py", "render/blender/aspecto.py", "render/blender/video.py",
                 "nudos/blender.py", "nudos/trenza.py")


def _clave(c: Cuadro, h: float, dos: bool, formato: str, base: str, foco: float = 0.0, vel=None) -> str:
    from .prueba_atar import _tramos
    cam = _datos_camara(c.camara)
    return _huella(np.round(np.asarray(c.X, float), 5), _tramos(len(c.X), h, c.resaltado, dos),
                   np.round(cam["matriz"], 6).tolist(), c.camara["centro"], round(c.camara["extension"], 4),
                   formato, base, round(foco, 3), None if vel is None else np.round(vel, 2))


def rutas_de(modelo, cuadros: list[Cuadro], formato: str, mallas) -> list[Path]:
    """La ruta del render de cada cuadro, con la huella de lo que muestra: la cuerda, la cámara,
    el foco y la velocidad (el desenfoque de movimiento). Cuadros iguales (las pausas) comparten
    ruta."""
    from . import blender
    from .aspecto import focos, velocidad_nodos
    F = FORMATOS[formato]
    h = modelo.pasos[-1].h
    dos = modelo.spec.plantilla is not None
    dest = carpeta_cuadros(modelo.spec.slug) / formato
    base = _huella(mallas, F["muestras"], F["tam"], _codigo(*CODIGO_RENDER), blender.APLASTAR, CYCLES,
                   PUNTA, "tapas", "sigma", _aspecto_video(modelo, cuadros, mallas))
    fs = focos(cuadros, F["fps"])
    return [dest / f"r-{_clave(c, h, dos, formato, base, fs[i], velocidad_nodos(cuadros, i, F['fps']))}.png"
            for i, c in enumerate(cuadros)]


def _aspecto_video(modelo, cuadros: list[Cuadro], mallas) -> dict:
    """Lo que el lote de render/blender/video.py lleva del aspecto (T20b): el motor, sus ajustes,
    el aspecto, la mesa, el fondo, la luz y el estilo de la cuerda."""
    from .aspecto import ESCENA_VIDEO, VIDEO, escenario_video, estilo_video, lote_video
    az = _az_de(cuadros)
    color = modelo.spec.cuerdas[0].color if modelo.spec.cuerdas else "azul"
    return {**lote_video(ESCENA_VIDEO, az), **escenario_video([c.X for c in cuadros], mallas, az),
            "estilo": estilo_video(color), "resaltado": VIDEO[ESCENA_VIDEO].resaltado}


def _az_de(cuadros: list[Cuadro]) -> float:
    """El azimut de la cámara del primer cuadro: la luz y el sol se orientan según él."""
    c = cuadros[0].camara
    d = np.asarray(c["pos"], float) - np.asarray(c["target"], float)
    return float(math.atan2(d[0], -d[1]))


RENDER_VIDEO = RAIZ / "render" / "blender" / "video.py"
ADELANTE = 48              # mallas que se preparan por delante de Blender, como mucho
# Lo que cambia cómo dibuja Cycles en el video (render/blender/video.py; Gabriel, 26 nov): el
# cuadro entero de una vez y el muestreo adaptativo más permisivo (Blender trae 0,01). Va en la
# huella de cada cuadro.
CYCLES = {"teselas": False, "umbral_adaptativo": 0.03}


def _procesos() -> int:
    """Los procesos para las mallas y para armar: los núcleos que quedan, hasta 8."""
    return max(1, min(8, (os.cpu_count() or 4) - 2))


# Lo que cada proceso de las mallas carga una vez: las mallas del anfitrión y sus muestras.
_MALLAS = None
_SOLIDOS = None


def _iniciar_mallas(escena: str, aplastar: bool) -> None:
    global _MALLAS, _SOLIDOS
    from . import blender
    _MALLAS = json.loads(Path(escena).read_text(encoding="utf-8"))["mallas"]
    _SOLIDOS = blender._muestras_solidos(_MALLAS) if aplastar else None


PUNTA = (1.5, 25.0)   # d y grados: el largo de la punta que se suaviza, y el codo desde el que se suaviza


def punta_suave(X, h: float, largo: float = PUNTA[0], umbral: float = PUNTA[1]) -> np.ndarray:
    """La cuerda con la punta sin codo, para dibujarla: si en los últimos `largo` d la cuerda
    dobla más de `umbral` grados en un solo nodo, esa parte se dibuja sobre una curva suave
    (Bézier cuadrática) que sale con la dirección de la cuerda y llega a la misma punta. En los
    cuadros del motor, la mano que lleva la punta puede doblar el último tramo en ángulo, y el
    remate se veía como un codo (T18). La punta no se mueve; solo cambia cómo llega a ella."""
    X = np.asarray(X, float)
    k = int(round(largo / h))
    if len(X) < k + 3:
        return X
    P = X[-k - 2:]
    d = np.diff(P, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-12)[:, None]
    giro = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", d[:-1], d[1:]), -1, 1)))
    if giro.max() <= umbral:
        return X
    p0, p2 = X[-k - 1], X[-1]
    t0 = d[0]
    p1 = p0 + t0 * np.linalg.norm(p2 - p0) / 2
    u = np.linspace(0, 1, k + 1)[:, None]
    out = X.copy()
    out[-k - 1:] = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u ** 2 * p2
    return out


def _preparar_malla(X, tramos, ruta: str, h: float, velocidad=None, estilo: str = "real") -> None:
    """La malla de la cuerda de un cuadro, con la trenza en la geometría (T20b) y la velocidad de
    cada vértice, en un npz que Blender espera: se escribe con otro nombre y se renombra, para
    que Blender nunca lea uno a medias."""
    from . import blender
    from .trenza import ESTILOS
    X = punta_suave(np.asarray(X, float), h)
    # La trenza sale de la coordenada de material (T21): el nodo j es siempre el punto σ = j·h
    # de la cuerda, así que la trenza va pegada a ella aunque se mueva.
    s = np.arange(len(X)) * h
    m = blender.malla_trenza(X, tramos=tramos, mosaico=ESTILOS[estilo].mosaico, otras=[(X, s, 0.5, True)],
                             solidos=_SOLIDOS, velocidad=velocidad, s=s)
    tmp = ruta + ".tmp.npz"
    blender.guardar_trenza(m, tmp)
    os.replace(tmp, ruta)


def dibujar(modelo, cuadros: list[Cuadro], formato: str, mallas, aviso=print, solo: range | None = None) -> list[Path]:
    """Dibuja con Blender los cuadros que faltan y da la ruta del render de cada cuadro (PNG
    RGB, con el aspecto de T20b: la escena entera, sin la viñeta ni el grano, que van al
    armar). Cuadros iguales se dibujan una vez.

    Una sola llamada a Blender (render/blender/video.py) dibuja todos los que faltan, con la
    escena armada una vez. Mientras tanto, varios procesos preparan las mallas de la cuerda, a
    lo más ADELANTE cuadros por delante. Cada cuadro se guarda en cuanto Blender lo termina, así
    que si la orden se corta, al volver a correrla sigue desde ahí.

    Con `solo`, dibuja solo esos cuadros (la prueba de 10 s), con la escena, el foco y la huella
    que tienen en el video entero."""
    import threading
    from concurrent.futures import ProcessPoolExecutor

    from . import blender
    from .aspecto import focos, velocidad_nodos
    from .prueba_atar import _tramos
    F = FORMATOS[formato]
    ancho, alto = F["tam"]
    h = modelo.pasos[-1].h
    dos = modelo.spec.plantilla is not None
    rutas = rutas_de(modelo, cuadros, formato, mallas)
    rutas[0].parent.mkdir(parents=True, exist_ok=True)
    fs = focos(cuadros, F["fps"])
    faltan = {}
    for i, (c, r) in enumerate(zip(cuadros, rutas)):
        if solo is not None and i not in solo:
            continue
        if r not in faltan and not (r.exists() and r.stat().st_size > 0):
            faltan[r] = i
    pendientes = [(r, cuadros[i], i) for r, i in faltan.items()]
    aviso(f"  {formato}: {len(cuadros)} cuadros, {len(set(rutas))} distintos, faltan {len(pendientes)}")
    if not pendientes:
        return rutas
    t0 = time.time()
    estado = {"listos": 0}
    errores: list[BaseException] = []
    with tempfile.TemporaryDirectory(prefix="nudos-video-") as tmp:
        tmp = Path(tmp)
        esc = tmp / "escena.json"
        aspecto = _aspecto_video(modelo, cuadros, mallas)
        esc.write_text(json.dumps({"mallas": mallas, "mesa": aspecto["mesa"], "fondo": aspecto["fondo"],
                                   "luz": aspecto["luz"]}), encoding="utf-8")
        trabajos = [{"cuerdas": [{"malla": str(tmp / f"c{k:05d}.npz")}], "camara": _datos_camara(c.camara),
                     "foco": fs[i], "salida": str(ruta.with_suffix(".tmp.png"))}
                    for k, (ruta, c, i) in enumerate(pendientes)]
        ajustes = {**aspecto["ajustes"], "umbral": CYCLES["umbral_adaptativo"]}
        if F["muestras"]:
            ajustes["muestras"] = F["muestras"]
        lote = tmp / "lote.json"
        lote.write_text(json.dumps({"ancho": ancho, "alto": alto, "fps": F["fps"], "motor": aspecto["motor"],
                                    "ajustes": ajustes, "aspecto": aspecto["aspecto"], "escena": str(esc),
                                    "cuerdas": [{"estilo": aspecto["estilo"], "resaltado": aspecto["resaltado"]}],
                                    "desenfoque": True, "obturador": 0.5, "trabajos": trabajos}),
                        encoding="utf-8")
        orden = [blender.ejecutable(), "--background", "--factory-startup", "--python-exit-code", "1",
                 "--python", str(RENDER_VIDEO), "--", "--lote", str(lote)]
        proc = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")
        hay_lugar = threading.Condition()

        def revisar(f):
            if f.exception() is not None:
                errores.append(f.exception())
                proc.kill()

        def dar_mallas(pool):
            for k, (ruta, c, i) in enumerate(pendientes):
                with hay_lugar:
                    hay_lugar.wait_for(lambda: k < estado["listos"] + ADELANTE or bool(errores)
                                       or proc.poll() is not None)
                if errores or proc.poll() is not None:
                    return
                f = pool.submit(_preparar_malla, np.asarray(c.X, np.float32),
                                _tramos(len(c.X), h, c.resaltado, dos), trabajos[k]["cuerdas"][0]["malla"], h,
                                velocidad_nodos(cuadros, i, F["fps"]), aspecto["estilo"])
                f.add_done_callback(revisar)

        cola: list[str] = []
        with ProcessPoolExecutor(_procesos(), initializer=_iniciar_mallas,
                                 initargs=(str(esc), blender.APLASTAR)) as pool:
            hilo = threading.Thread(target=dar_mallas, args=(pool,), daemon=True)
            hilo.start()
            try:
                for linea in proc.stdout:
                    cola = (cola + [linea.rstrip()])[-25:]
                    if not linea.startswith("listo:"):
                        continue
                    k = int(linea.split()[1])
                    ruta = pendientes[k][0]
                    try:
                        _reemplazar(ruta.with_suffix(".tmp.png"), ruta)
                        Path(trabajos[k]["cuerdas"][0]["malla"]).unlink(missing_ok=True)
                    except OSError as e:
                        # Que se sepa enseguida: si no, Blender sigue dibujando hasta quedarse sin
                        # mallas y la orden se ve trabada (T20b, con la máquina muy cargada).
                        aviso(f"  {modelo.spec.slug}, {formato}: no se pudo guardar el cuadro {k}: {e}")
                        raise
                    with hay_lugar:
                        estado["listos"] = k + 1
                        hay_lugar.notify_all()
                    n = estado["listos"]
                    if n % AVISO_CADA == 0 or n == len(pendientes):
                        seg = time.time() - t0
                        falta = seg / n * (len(pendientes) - n)
                        aviso(f"  {modelo.spec.slug}, {formato}: {n}/{len(pendientes)} cuadros "
                              f"({100 * n / len(pendientes):.0f} %), {seg / n:.1f} s cada uno, "
                              f"faltan {int(falta // 3600)} h {int(falta % 3600 // 60)} min")
            finally:
                codigo = proc.wait()
                with hay_lugar:
                    hay_lugar.notify_all()
                hilo.join()
    if errores:
        raise VideoError(f"no se pudo preparar la malla de un cuadro: {errores[0]}")
    if codigo != 0 or estado["listos"] < len(pendientes):
        raise blender.BlenderError(f"Blender no pudo dibujar el video (código {codigo}):\n" + "\n".join(cola))
    return rutas


def _reemplazar(origen: Path, destino: Path, intentos: int = 50) -> None:
    """os.replace con reintentos: en Windows, el antivirus o el indexador pueden tener abierto un
    PNG recién escrito unos instantes."""
    for k in range(intentos):
        try:
            origen.replace(destino)
            return
        except PermissionError:
            if k == intentos - 1:
                raise
            time.sleep(0.2)


COLOR = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def _codificar(formato: str) -> list[str]:
    if formato == "horizontal":
        return ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level", "5.2",
                "-b:v", "68M", "-maxrate", "68M", "-bufsize", "136M", "-g", "30", "-bf", "2"]
    if formato == "vertical":
        return ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level", "4.2",
                "-b:v", "20M", "-maxrate", "25M", "-bufsize", "40M", "-g", "30", "-bf", "2"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]


# Lo que cada proceso de armar carga una vez: las imágenes de los títulos, y el último render
# que abrió (las pausas repiten el mismo).
_TITULOS: dict = {}
_ULTIMO: tuple = (None, None)


def _iniciar_armar(titulos: dict) -> None:
    global _TITULOS
    _TITULOS = {k: Image.open(v).convert("RGBA") for k, v in titulos.items()}


def _componer(args) -> str:
    """El cuadro del video: el render con la viñeta y el grano de T20b (un grano distinto en
    cada cuadro, con la semilla de su número) y el título encima con su fundido. Lo escribe en
    RGB crudo en `crudo` y da esa ruta: un cuadro de 4K son 25 MB, y mandarlos de vuelta por la
    tubería del proceso hacía fallar a Windows («recursos insuficientes», T20b)."""
    global _ULTIMO
    from .aspecto import posproceso_video
    ruta, titulo, alfa, indice, crudo = args
    if _ULTIMO[0] != ruta:
        with Image.open(ruta) as im:
            fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
            fondo.alpha_composite(im.convert("RGBA"))
        _ULTIMO = (ruta, fondo.convert("RGB"))
    im = posproceso_video(_ULTIMO[1], indice).convert("RGBA")
    t = _TITULOS.get(titulo)
    if t is not None and alfa > 0:
        im.alpha_composite(t if alfa >= 1 else _con_alfa(t, alfa))
    Path(crudo).write_bytes(im.convert("RGB").tobytes())
    return crudo


def armar(cuadros: list[Cuadro], rutas: list[Path], tits: dict, formato: str, salida: Path) -> None:
    """Le pone a cada render la viñeta y el grano, y el título encima con su fundido, y se lo
    pasa a ffmpeg. Los cuadros se componen en varios procesos, cada uno a un archivo crudo, con
    a lo más EN_VUELO por delante de ffmpeg (así el disco no se llena si ffmpeg va más lento), y
    pasan a ffmpeg en orden."""
    from collections import deque
    from concurrent.futures import ProcessPoolExecutor
    F = FORMATOS[formato]
    ancho, alto = F["tam"]
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = salida.with_suffix(".tmp.mp4")
    orden = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{ancho}x{alto}", "-r", str(F["fps"]), "-i", "-", "-an",
             "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
             *_codificar(formato), *COLOR, "-r", str(F["fps"]), "-movflags", "+faststart", str(tmp)]
    with tempfile.TemporaryDirectory(prefix="nudos-titulos-") as carpeta:
        rutas_tit = {}
        for (f, n), im in tits.items():
            if f == formato:
                rutas_tit[n] = str(Path(carpeta) / f"t{n}.png")
                im.save(rutas_tit[n])
        args = iter([(str(r), c.titulo, c.alfa, i, str(Path(carpeta) / f"c{i:06d}.rgb"))
                     for i, (c, r) in enumerate(zip(cuadros, rutas))])
        proc = subprocess.Popen(orden, stdin=subprocess.PIPE)
        try:
            n = _procesos()
            with ProcessPoolExecutor(n, initializer=_iniciar_armar, initargs=(rutas_tit,)) as pool:
                en_vuelo = deque()

                def lanzar():
                    a = next(args, None)
                    if a is not None:
                        en_vuelo.append(pool.submit(_componer, a))

                for _ in range(EN_VUELO * n):
                    lanzar()
                while en_vuelo:
                    crudo = Path(en_vuelo.popleft().result())
                    proc.stdin.write(crudo.read_bytes())
                    crudo.unlink()
                    lanzar()
            proc.stdin.close()
        except BrokenPipeError:
            pass
        if proc.wait() != 0:
            raise VideoError(f"ffmpeg no pudo armar {salida.name}")
    tmp.replace(salida)


EN_VUELO = 2     # cuadros compuestos por proceso que pueden esperar a ffmpeg


def _con_alfa(im: Image.Image, a: float) -> Image.Image:
    r, g, b, al = im.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def visor(origen: Path, salida: Path) -> float:
    """La copia del visor: el 4K bajado a 1920 × 1080, con su audio tal cual, y el tope de
    TOPE_VISOR MB. Da los MB."""
    tmp = salida.with_suffix(".tmp.mp4")
    orden = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(origen), "-c:a", "copy",
             "-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "slow",
             "-profile:v", "high", "-level", "4.2", "-crf", "20", "-maxrate", "4M", "-bufsize", "8M",
             "-g", "60", "-pix_fmt", "yuv420p", *COLOR, "-movflags", "+faststart", str(tmp)]
    subprocess.run(orden, check=True)
    mb = tmp.stat().st_size / 1e6
    tmp.replace(salida)
    if mb > TOPE_VISOR:
        raise VideoError(f"{salida.name} pesa {mb:.1f} MB; el tope del visor es {TOPE_VISOR} MB.")
    return mb


# --------------------------------------------------------------------------
# Un nudo y la cola
# --------------------------------------------------------------------------
def construir(slugs: list[str]) -> dict:
    from .prueba_blender import construir_pilotos
    return construir_pilotos(tuple(slugs))


def cuadros_de(modelo, tramos, formato: str) -> list[Cuadro]:
    F = FORMATOS[formato]
    sim, vel = simulacion(modelo, tramos)
    ts, _ = tomas(modelo, sim, formato)
    cuadros = retiempo(sim, vel, F["fps"])
    alfas(cuadros, F["fps"])
    poner_camaras(cuadros, ts, F["fps"])
    return cuadros


def calidad(modelo, formato: str = "horizontal") -> dict:
    """La calidad del movimiento (T21a) en los cuadros del video, sin dibujarlo: la cuerda
    (nudos/fisica/calidad.py), el resaltado del tramo que se mueve y la cámara. Usa el atado
    guardado si su huella coincide."""
    from .fisica.calidad import medir
    from .prueba_atar import _tramos
    tramos, _ = atar(modelo)
    F = FORMATOS[formato]
    cuadros = cuadros_de(modelo, tramos, formato)
    h = modelo.pasos[-1].h
    dos = modelo.spec.plantilla is not None
    informe = medir([c.X for c in cuadros], F["fps"], fases=[c.fase for c in cuadros])
    # El resaltado va por índice de nodo: si la cuerda se acorta por debajo de donde empieza,
    # o la pausa de una plantilla la corta en el hito, se achica o no se ve.
    con = vacio = corto = 0
    for c in cuadros:
        if not c.resaltado:
            continue
        con += 1
        nominal = c.resaltado[1] - c.resaltado[0]
        visto = sum((b - a) * h for a, b, m in _tramos(len(c.X), h, c.resaltado, dos) if m == 1)
        vacio += int(visto <= 0)
        corto += int(0 < visto < nominal / 2)
    informe["resaltado"] = {"cuadros": con, "vacio": vacio, "corto": corto}
    informe["camara"] = medir([np.asarray(c.camara["pos"], float).reshape(1, 3) for c in cuadros],
                              F["fps"])
    return informe


ARMADO = "2"   # súbela si cambia cómo se arma un video desde sus cuadros (componer o codificar)


def firma_imagen(rutas: list[Path], cuadros: list[Cuadro], tits: dict, formato: str) -> str:
    """Lo que decide la imagen de un video: sus cuadros (la ruta de cada render lleva la huella
    de lo que muestra y de cómo se dibujó), sus títulos con su fundido y cómo se arma. No el
    código de este módulo: con los cuadros ya borrados, cambiarlo obligaría a dibujar todo otra
    vez, unas 5 horas por nudo en 4K."""
    return _huella([r.name for r in rutas], [(c.titulo, round(c.alfa, 3)) for c in cuadros],
                   [np.asarray(tits[(formato, k)]).sum() for k in sorted(k for f, k in tits if f == formato)],
                   ARMADO, _codificar(formato), COLOR)


def _leer(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cuadros_del_video(ruta: Path) -> int | None:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_frames", "-of", "csv=p=0", str(ruta)],
                       capture_output=True, text=True, timeout=60)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return None


def ya_armado(salida: Path, sello: dict, firma: str, n_cuadros: int) -> bool:
    """Si el video ya está armado con esta imagen. Uno armado antes de que el sello dependiera
    solo de la imagen (26 nov), que trae «firma» y no «imagen», se reconoce por su cantidad de
    cuadros: sus cuadros ya se borraron, y dibujarlo de nuevo son horas."""
    if not salida.exists():
        return False
    if sello.get("imagen") == firma:
        return True
    return "imagen" not in sello and "firma" in sello and cuadros_del_video(salida) == n_cuadros


def video(modelo, previa: bool = False, solo: str | None = None, aviso=print) -> dict:
    """Los videos de un nudo ya construido con el motor. Da un informe."""
    from .prueba_atar import mallas_anfitrion
    slug = modelo.spec.slug
    os.environ["NUDOS_MOTOR"] = "1"
    if modelo.fallas:
        raise VideoError(f"{slug}: el nudo tiene fallas con el motor:\n  " + "\n  ".join(modelo.fallas))
    t0 = time.time()
    tramos, huella = atar(modelo)
    fallas = [f for t in tramos for f in t.fallas]
    informe = {"slug": slug, "segundos_atar": round(time.time() - t0, 1), "fallas": fallas,
               "tramos": {t.n: t.medidas for t in tramos}}
    if fallas:
        raise VideoError(f"{slug}: el atado tiene fallas:\n  " + "\n  ".join(fallas))
    formatos = ["previa"] if previa else [f for f in ("horizontal", "vertical") if solo in (None, f)]
    dest = carpeta_videos(slug)
    tits = titulos(modelo, formatos)
    mallas = mallas_anfitrion(modelo)
    nombres = {"horizontal": f"{slug}-4k.mp4", "vertical": f"{slug}-vertical.mp4",
               "previa": f"{slug}-previa.mp4"}
    from . import audio
    audios: dict = {}      # el horizontal y el vertical tienen los mismos cuadros: el mismo audio
    for formato in formatos:
        t1 = time.time()
        F = FORMATOS[formato]
        cuadros = cuadros_de(modelo, tramos, formato)
        salida = dest / nombres[formato]
        ruta_sello = salida.with_suffix(".json")
        sello = _leer(ruta_sello)
        rutas = rutas_de(modelo, cuadros, formato, mallas)
        firma = firma_imagen(rutas, cuadros, tits, formato)
        if ya_armado(salida, sello, firma, len(cuadros)):
            aviso(f"  {slug}, {formato}: ya está armado")
            if sello.get("imagen") != firma:
                sello = {"imagen": firma, "cuadros": len(cuadros), "fecha": sello.get("fecha")}
        else:
            dibujar(modelo, cuadros, formato, mallas, aviso)
            armar(cuadros, rutas, tits, formato, salida)
            sello = {"imagen": firma, "cuadros": len(cuadros),
                     "fecha": datetime.datetime.now().isoformat(timespec="seconds")}
        ruta_sello.write_text(json.dumps(sello), encoding="utf-8")
        # El audio va aparte: si cambia, se pega otra vez sin volver a dibujar.
        firma_audio = _huella(firma, _codigo("nudos/audio.py"))
        if sello.get("audio") != firma_audio:
            clave = (F["fps"], len(cuadros))
            if clave not in audios:
                aviso(f"  {slug}, {formato}: el audio")
                audios[clave] = audio.pista(cuadros, F["fps"], modelo.pasos[-1].h, mallas)
            audio.pegar(salida, audios[clave])
            sello["audio"] = firma_audio
            ruta_sello.write_text(json.dumps(sello), encoding="utf-8")
        informe[formato] = {"segundos": round(len(cuadros) / F["fps"], 1),
                            "cuadros": len(cuadros), "mb": round(salida.stat().st_size / 1e6, 1),
                            "minutos": round((time.time() - t1) / 60, 1), "ruta": str(salida)}
        aviso(f"  {salida}: {informe[formato]['segundos']} s, {informe[formato]['mb']} MB")
        if formato == "horizontal":
            v = dest / f"{slug}-visor.mp4"
            ruta_sv = v.with_suffix(".json")
            origen = _huella(firma, sello.get("audio"))
            if v.exists() and _leer(ruta_sv).get("origen") == origen:
                mb = v.stat().st_size / 1e6
            else:
                mb = visor(salida, v)
                ruta_sv.write_text(json.dumps({"origen": origen}), encoding="utf-8")
            informe["visor"] = {"mb": round(mb, 1), "ruta": str(v)}
            al_repositorio(slug, v, mb)
        # Con el video armado, sus cuadros sobran: en 4K pesan unos 33 MB cada uno, unos 78 GB
        # por nudo, y C: no aguanta los de dos nudos.
        borrar_cuadros(slug, formato)
    return informe


PRUEBA_PASO = 4             # la prueba del aspecto (T20b): el medio de este paso
PRUEBA_SEGUNDOS = 10.0


def ventana(cuadros: list[Cuadro], paso: int = PRUEBA_PASO, segundos: float = PRUEBA_SEGUNDOS,
            fps: int = 60) -> list[Cuadro]:
    """Los cuadros de `segundos` alrededor del medio de lo que se mueve en el paso."""
    mov = [i for i, c in enumerate(cuadros) if c.paso == paso and c.fase != "pausa"]
    if not mov:
        raise VideoError(f"el video no tiene movimiento en el paso {paso}")
    n = min(len(cuadros), int(round(segundos * fps)))
    a = max(0, min(len(cuadros) - n, mov[len(mov) // 2] - n // 2))
    return cuadros[a:a + n]


def prueba(modelo, segundos: float = PRUEBA_SEGUNDOS, aviso=print) -> Path:
    """La prueba del aspecto de T20b: `segundos` del medio del paso PRUEBA_PASO en 4K, con su
    título, la viñeta y el grano, sin audio, en <slug>-prueba-4k.mp4. Los cuadros se quedan en
    NUDOS_CUADROS: el video entero, con el mismo código, los vuelve a usar."""
    from .prueba_atar import mallas_anfitrion
    os.environ["NUDOS_MOTOR"] = "1"
    if modelo.fallas:
        raise VideoError(f"{modelo.spec.slug}: el nudo tiene fallas con el motor")
    tramos, _ = atar(modelo)
    F = FORMATOS["horizontal"]
    todos = cuadros_de(modelo, tramos, "horizontal")
    cuadros = ventana(todos, segundos=segundos, fps=F["fps"])
    a = next(i for i, c in enumerate(todos) if c is cuadros[0])
    mallas = mallas_anfitrion(modelo)
    tits = titulos(modelo, ["horizontal"])
    t0 = time.time()
    rutas = dibujar(modelo, todos, "horizontal", mallas, aviso, solo=range(a, a + len(cuadros)))
    salida = carpeta_videos(modelo.spec.slug) / f"{modelo.spec.slug}-prueba-4k.mp4"
    armar(cuadros, rutas[a:a + len(cuadros)], tits, "horizontal", salida)
    aviso(f"  {salida}: {len(cuadros) / F['fps']:.1f} s, en {(time.time() - t0) / 60:.0f} min")
    return salida


def borrar_cuadros(slug: str, formato: str) -> None:
    carpeta = carpeta_cuadros(slug) / formato
    if carpeta.is_dir():
        shutil.rmtree(carpeta, ignore_errors=True)


def al_repositorio(slug: str, origen: Path, mb: float) -> Path:
    """Copia el video del visor a videos/<slug>.mp4 y anota de dónde salió en videos/LEEME.txt."""
    VIDEOS_REPO.mkdir(exist_ok=True)
    destino = VIDEOS_REPO / f"{slug}.mp4"
    if not destino.exists() or destino.read_bytes() != origen.read_bytes():
        shutil.copyfile(origen, destino)
    leeme = VIDEOS_REPO / "LEEME.txt"
    cabecera = ("Los videos del visor (T18), uno por nudo: la copia en 1920 × 1080 del video en 4K\n"
                "que arma `python -m nudos video <slug>`. `python -m nudos sitio` los copia a\n"
                "<slug>/video.mp4 de los nudos publicados. No se editan a mano.\n\n")
    lineas = []
    if leeme.exists():
        lineas = [l for l in leeme.read_text(encoding="utf-8").splitlines()[4:]
                  if l.strip() and not l.startswith(slug + " ")]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                                text=True).stdout.strip()
    except OSError:
        commit = "?"
    lineas.append(f"{slug}  {datetime.date.today().isoformat()}  código {commit}  {mb:.1f} MB")
    leeme.write_text(cabecera + "\n".join(sorted(lineas)) + "\n", encoding="utf-8")
    return destino


def todos() -> list[str]:
    from .referencia import nudos_hechos
    return nudos_hechos()


def cola(slugs: list[str], previa: bool = False, solo: str | None = None) -> int:
    """Los videos de varios nudos, uno tras otro. Un nudo que falla no detiene la cola; cada
    uno se anota en NUDOS_VIDEOS/cola.txt. Da cuántos fallaron."""
    os.environ["NUDOS_MOTOR"] = "1"     # el apretado del video es el del motor, como el de la ficha
    slugs = list(dict.fromkeys(slugs))
    registro = carpeta_videos() / "cola.txt"
    registro.parent.mkdir(parents=True, exist_ok=True)

    def anotar(texto):
        print(texto, flush=True)
        with registro.open("a", encoding="utf-8") as f:
            f.write(texto + "\n")

    anotar(f"\n{datetime.datetime.now():%Y-%m-%d %H:%M}: cola de {len(slugs)} nudos: {' '.join(slugs)}")
    malos = 0
    # Mientras Blender dibuja un nudo (la tarjeta), el siguiente se construye y se ata con el
    # motor (el procesador): en la cola de los 36 nudos son de 5 a 25 minutos menos por nudo.
    from concurrent.futures import ThreadPoolExecutor
    adelante = ThreadPoolExecutor(1)
    futuros = {}

    def pedir(i):
        if i < len(slugs) and slugs[i] not in futuros:
            futuros[slugs[i]] = adelante.submit(preparar, slugs[i])

    pedir(0)
    for i, slug in enumerate(slugs):
        t0 = time.time()
        try:
            modelo = futuros.pop(slug).result()
            pedir(i + 1)
            inf = video(modelo, previa=previa, solo=solo, aviso=lambda t: print(t, flush=True))
            hechos = ", ".join(f"{k} {v['segundos']} s" for k, v in inf.items()
                               if isinstance(v, dict) and "segundos" in v)
            anotar(f"{datetime.datetime.now():%H:%M} {slug}: listo en {(time.time() - t0) / 60:.0f} min ({hechos})")
        except Exception as e:      # la cola sigue con el siguiente nudo
            malos += 1
            anotar(f"{datetime.datetime.now():%H:%M} {slug}: FALLÓ en {(time.time() - t0) / 60:.0f} min: "
                   + str(e).replace("\n", " | "))
        pedir(i + 1)
    adelante.shutdown()
    anotar(f"{datetime.datetime.now():%Y-%m-%d %H:%M}: cola terminada, {malos} con fallas")
    return malos


def preparar(slug: str):
    """El nudo construido con el motor y atado (el atado queda guardado). Si el nudo tiene
    fallas o el atado falla, la falla sale al pedir el resultado, con su nudo."""
    modelo = construir([slug])[slug]
    if not modelo.fallas:
        atar(modelo)
    return modelo
