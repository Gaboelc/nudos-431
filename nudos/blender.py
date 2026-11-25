"""Las imágenes de impresión dibujadas con Blender (T16, con T15g).

La escena sigue saliendo de render/escena.js, como en el visor: Edge la arma con la cámara, el
encuadre y los nombres de siempre (`nombresDe` y `colocarNombres`), y `window.exportar()` la
devuelve como datos: la matriz de la cámara, el eje de cada cuerda con sus tramos (base,
resaltado y remate) y las demás mallas (el anfitrión, las tapas de las puntas y los dedos), con
el papel de su material. Edge toma además una captura con solo los nombres, sobre fondo
transparente.

Aquí se arma la malla de cada cuerda desde su eje, con lo que el motor le da al render (T15g):
- **La torsión:** la trenza y el hilo trazador siguen el marco sin torsión del motor
  (`marco_paralelo`, que empieza lo más cerca de +z en el firme), así que el dibujo de la trenza
  no salta entre un paso y el siguiente.
- **La sección aplastada:** donde una cuerda aprieta a otra o a un anfitrión, su sección se
  aplana contra el plano de contacto y se ensancha de lado, con la misma área. La IPC del motor
  deja los ejes a 0,95 diámetros como mínimo (`LIMITES_MOTOR`): con tubos redondos, se
  atravesarían un poco; aplastados, se tocan en una cara plana. La presión de contacto de la IPC
  crece sola cuando la distancia baja (la barrera), así que la distancia es la medida de la
  presión.

Después, `render/blender/escena.py` dibuja todas las imágenes de un nudo en una sola corrida de
Blender (Cycles, semilla fija, el denoiser en la CPU) y aquí se ponen sobre blanco, con los
nombres encima.

La ruta de Blender sale de NUDOS_BLENDER, como la de Edge de NUDOS_CHROME; si no está, se busca
Blender 5.2 donde lo instala Windows y en el PATH.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from . import RAIZ
from .imprimir import ImpresionError

ESCENA_BLENDER = RAIZ / "render" / "blender" / "escena.py"
VERSION = "5.2"         # la versión fija, como three.js en sitio/vendor
MUESTRAS = 256
LADOS = 32              # vértices de cada anillo de la cuerda
# T15g: la sección se aplana donde los ejes quedan a menos de un diámetro. Con APLASTAR en falso,
# la cuerda es un tubo redondo, como en three.js.
APLASTAR = True
ENSANCHE_MAX = 1.12     # lo más que se ensancha la sección para conservar su área
VECINOS_ARCO = 1.6      # en diámetros: más cerca que esto a lo largo de la cuerda no se toca
PASO_ANFITRION = 0.1    # en diámetros: cada cuánto se muestrea la superficie del anfitrión
# Los papeles de material que son sólidos contra los que la cuerda se aplasta.
SOLIDOS = {"madera", "testa", "metal", "plastico", "cabo", "corte", "dedo"}


class BlenderError(ImpresionError):
    """Blender no está o no pudo dibujar."""


def ejecutable() -> str:
    """La ruta de blender.exe: NUDOS_BLENDER, la instalación de Windows o el PATH."""
    if os.environ.get("NUDOS_BLENDER"):
        return os.environ["NUDOS_BLENDER"]
    for patron in (f"C:/Program Files/Blender Foundation/Blender {VERSION}/blender.exe",
                   f"C:/Program Files/Blender Foundation/Blender {VERSION}*/blender.exe"):
        hallado = sorted(glob.glob(patron))
        if hallado:
            return hallado[0]
    if shutil.which("blender"):
        return shutil.which("blender")
    raise BlenderError(f"No encuentro Blender {VERSION}. Instálalo o define NUDOS_BLENDER con la "
                       "ruta de blender.exe.")


# --------------------------------------------------------------------------
# La malla de una cuerda (T15g)
# --------------------------------------------------------------------------
@dataclass
class MallaCuerda:
    vertices: np.ndarray    # (n·LADOS, 3)
    caras: np.ndarray       # (m, 4) índices de los cuadriláteros
    uv: np.ndarray          # (m, 4, 2) por esquina: u a lo largo (un mosaico cada π·grosor), v alrededor
    material: np.ndarray    # (m,) 0 base, 1 resaltado, 2 remate
    s: np.ndarray           # (n·LADOS,) largo desde el comienzo, en diámetros
    aplastado: np.ndarray   # (n,) cuánto se acortó el radio más corto de cada anillo, de 0 a 1


def _marcos(P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """d1 y d2 en cada punto del eje: el marco sin torsión del motor (`marco_paralelo`, que
    empieza lo más cerca de +z), llevado de los tramos a los puntos."""
    from .fisica.varilla import marco_paralelo
    t_seg, d1_seg, _ = marco_paralelo(P)
    T = np.empty_like(P)
    T[0], T[-1] = t_seg[0], t_seg[-1]
    T[1:-1] = t_seg[:-1] + t_seg[1:]
    T /= np.linalg.norm(T, axis=1)[:, None]
    D1 = np.empty_like(P)
    D1[0], D1[-1] = d1_seg[0], d1_seg[-1]
    D1[1:-1] = d1_seg[:-1] + d1_seg[1:]
    D1 -= T * np.einsum("ij,ij->i", D1, T)[:, None]
    D1 /= np.linalg.norm(D1, axis=1)[:, None]
    return D1, np.cross(T, D1)


def _muestras_solidos(mallas: list[dict], paso: float = PASO_ANFITRION) -> list[tuple[np.ndarray, np.ndarray]]:
    """Puntos de la superficie de cada sólido, cada `paso`, con su normal hacia afuera: unos
    por malla (un palo, el pie de la cornamusa), para que la cuerda apoyada entre dos palos se
    aplaste contra los dos."""
    out = []
    for m in mallas:
        if m["rol"] not in SOLIDOS:
            continue
        puntos, normales = [], []
        P = np.asarray(m["pos"], float).reshape(-1, 3)
        N = np.asarray(m["nor"], float).reshape(-1, 3)
        tri = np.asarray(m["idx"], int).reshape(-1, 3)
        for a, b, c in tri:
            e1, e2 = P[b] - P[a], P[c] - P[a]
            n1 = max(1, int(np.ceil(np.linalg.norm(e1) / paso)))
            n2 = max(1, int(np.ceil(np.linalg.norm(e2) / paso)))
            i, j = np.meshgrid(np.arange(n1 + 1) / n1, np.arange(n2 + 1) / n2, indexing="ij")
            dentro = i + j <= 1 + 1e-9
            u, v = i[dentro], j[dentro]
            puntos.append(P[a] + u[:, None] * e1 + v[:, None] * e2)
            nn = (1 - u - v)[:, None] * N[a] + u[:, None] * N[b] + v[:, None] * N[c]
            normales.append(nn / np.maximum(np.linalg.norm(nn, axis=1), 1e-12)[:, None])
        out.append((np.vstack(puntos), np.vstack(normales)))
    return out


def _contactos(k: int, cuerdas: list[dict], solidos) -> list[list[tuple[np.ndarray, float]]]:
    """Para cada punto del eje de la cuerda k, los planos de contacto: (n, h), la dirección hacia
    lo que aprieta y la distancia del eje al plano donde la sección se aplana."""
    from scipy.spatial import cKDTree
    c = cuerdas[k]
    P = np.asarray(c["espina"], float).reshape(-1, 3)
    R = c["radio"]
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    out: list[list[tuple[np.ndarray, float]]] = [[] for _ in range(len(P))]
    # Las cuerdas, con la misma de k: a lo largo de la cuerda, solo lo que está lejos.
    for j, otra in enumerate(cuerdas):
        Q = np.asarray(otra["espina"], float).reshape(-1, 3)
        Ro = otra["radio"]
        sq = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))])
        arbol = cKDTree(Q)
        for i, vecinos in enumerate(arbol.query_ball_point(P, R + Ro)):
            for q in vecinos:
                if j == k and abs(sq[q] - s[i]) < VECINOS_ARCO * (R + Ro):
                    continue
                d = Q[q] - P[i]
                dist = float(np.linalg.norm(d))
                if 1e-9 < dist < R + Ro:
                    out[i].append((d / dist, dist * R / (R + Ro)))
    # Cada sólido, por el punto de su superficie más cercano al eje: el plano de contacto es el
    # tangente ahí, con la normal de la superficie. (Los planos tangentes de puntos más lejanos no
    # sirven: el sólido es convexo y la cuerda los cruza sin tocarlo.)
    for Ps, Ns in solidos:
        _, q = cKDTree(Ps).query(P)
        h = np.einsum("ij,ij->i", P - Ps[q], Ns[q])   # del eje al plano tangente
        for i in np.nonzero((h > 0) & (h < R))[0]:
            out[i].append((-Ns[q[i]], float(h[i])))
    return out


def _seccion(direcciones: np.ndarray, R: float, planos) -> np.ndarray:
    """Los radios de un anillo: R, recortados por los planos de contacto y ensanchados donde no
    tocan, para que la sección conserve el área de la redonda."""
    if not planos:
        return np.full(len(direcciones), R)
    limite = np.full(len(direcciones), np.inf)
    for n, h in planos:
        cos = direcciones @ n
        with np.errstate(divide="ignore"):
            limite = np.minimum(limite, np.where(cos > 1e-6, h / np.maximum(cos, 1e-12), np.inf))
    # El área de un polígono de radios r es ½·sen(2π/n)·Σ r_j·r_(j+1): la del redondo es n·R².
    f = 1.0
    for _ in range(8):
        r = np.minimum(R * f, limite)
        f = min(ENSANCHE_MAX, f * np.sqrt(len(r) * R * R / max(np.sum(r * np.roll(r, -1)), 1e-12)))
    return np.minimum(R * f, limite)


def malla_cuerda(k: int, escena: dict, aplastar: bool = APLASTAR, lados: int = LADOS, solidos=None) -> MallaCuerda:
    """La malla de la cuerda k de una escena exportada por render/escena.js."""
    c = escena["cuerdas"][k]
    P = np.asarray(c["espina"], float).reshape(-1, 3)
    R, grosor = c["radio"], c["grosor"]
    n = len(P)
    D1, D2 = _marcos(P)
    ang = 2 * np.pi * np.arange(lados) / lados
    dirs = np.cos(ang)[None, :, None] * D1[:, None, :] + np.sin(ang)[None, :, None] * D2[:, None, :]
    radios = np.full((n, lados), R)
    if aplastar:
        if solidos is None:
            solidos = _muestras_solidos(escena["mallas"])
        planos = _contactos(k, escena["cuerdas"], solidos)
        for i in range(n):
            if planos[i]:
                radios[i] = _seccion(dirs[i], R, planos[i])
    aplastado = 1 - radios.min(axis=1) / R
    V = (P[:, None, :] + radios[:, :, None] * dirs).reshape(-1, 3)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    kk = np.repeat(np.arange(n - 1), lados)
    jj = np.tile(np.arange(lados), n - 1)
    a, b = kk * lados + jj, kk * lados + (jj + 1) % lados
    caras = np.stack([a, a + lados, b + lados, b], axis=1)
    u0, u1 = s[kk] / (np.pi * grosor), s[kk + 1] / (np.pi * grosor)
    v0, v1 = jj / lados, (jj + 1) / lados
    uv = np.stack([np.c_[u0, v0], np.c_[u1, v0], np.c_[u1, v1], np.c_[u0, v1]], axis=1)
    material = np.zeros(n - 1, dtype=np.int32)
    for s0, s1, m in c["tramos"]:
        material[s0:s1] = m
    return MallaCuerda(V, caras, uv, np.repeat(material, lados), np.repeat(s, lados), aplastado)


# --------------------------------------------------------------------------
# Dibujar con Blender
# --------------------------------------------------------------------------
def preparar(escena: dict, carpeta: Path, nombre: str, aplastar: bool = APLASTAR) -> dict:
    """Escribe en `carpeta` lo que Blender necesita para una imagen: la escena sin las cuerdas
    (JSON) y la malla de cada cuerda (npz). Devuelve el trabajo de esa imagen para el lote."""
    carpeta.mkdir(parents=True, exist_ok=True)
    solidos = _muestras_solidos(escena["mallas"]) if aplastar else None
    archivos = []
    for k, c in enumerate(escena["cuerdas"]):
        m = malla_cuerda(k, escena, aplastar, solidos=solidos)
        ruta = carpeta / f"{nombre}-cuerda-{k}.npz"
        np.savez(ruta, vertices=m.vertices.astype(np.float32), caras=m.caras.astype(np.int32),
                 uv=m.uv.astype(np.float32), material=m.material, s=m.s.astype(np.float32))
        archivos.append({"malla": str(ruta), "color": c["color"], "grosor": c["grosor"],
                         "aplastado": float(m.aplastado.max())})
    datos = {k: v for k, v in escena.items() if k != "cuerdas"}
    ruta = carpeta / f"{nombre}.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return {"escena": str(ruta), "cuerdas": archivos}


def renderizar(trabajos: list[dict], ancho: int, alto: int, muestras: int = MUESTRAS) -> None:
    """Dibuja los trabajos en una sola corrida de Blender. Cada trabajo trae su «salida» (PNG
    RGBA sobre fondo transparente, con la sombra de la mesa)."""
    if not trabajos:
        return
    with tempfile.TemporaryDirectory(prefix="nudos-blender-") as tmp:
        lote = Path(tmp) / "lote.json"
        lote.write_text(json.dumps({"ancho": ancho, "alto": alto, "muestras": muestras,
                                    "trabajos": trabajos}), encoding="utf-8")
        orden = [ejecutable(), "--background", "--factory-startup", "--python-exit-code", "1",
                 "--python", str(ESCENA_BLENDER), "--", "--lote", str(lote)]
        r = subprocess.run(orden, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or any(not Path(t["salida"]).exists() for t in trabajos):
        cola = "\n".join((r.stdout + r.stderr).splitlines()[-25:])
        raise BlenderError(f"Blender no pudo dibujar (código {r.returncode}):\n{cola}")


def componer(render: Path, nombres: Image.Image | None, ancho: int, alto: int) -> Image.Image:
    """La imagen de la ficha: blanco, encima el render de Blender y encima los nombres."""
    fondo = Image.new("RGBA", (ancho, alto), (255, 255, 255, 255))
    with Image.open(render) as im:
        fondo.alpha_composite(im.convert("RGBA").resize((ancho, alto), Image.Resampling.LANCZOS)
                              if im.size != (ancho, alto) else im.convert("RGBA"))
    if nombres is not None:
        if nombres.size != (ancho, alto):
            # Reducir con el alfa premultiplicado, para que el borde de las letras no se oscurezca.
            nombres = nombres.convert("RGBa").resize((ancho, alto), Image.Resampling.LANCZOS).convert("RGBA")
        fondo.alpha_composite(nombres)
    return fondo.convert("RGB")
