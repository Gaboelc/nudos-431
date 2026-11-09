"""Hoja de revisión: todos los pasos de un nudo en una sola imagen.

Render rápido con numpy: la cuerda como un tubo de esferas, con sombra y
oscurecimiento de contacto sobre la mesa. Sirve para revisar el modelo, no para
imprimir.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

from .libre import R

AZUL = np.array([0.10, 0.25, 0.75])
CREMA = np.array([0.93, 0.89, 0.78])
COLORES = {"azul": AZUL, "crema": CREMA}   # los de nudos/spec.py COLORES
AMBAR = np.array([0.95, 0.55, 0.12])
REMATE = np.array([0.35, 0.06, 0.06])
MESA = np.array([0.80, 0.81, 0.80])
ANCHO = 520          # píxeles de cada cuadro
COLUMNAS = 4
MARGEN_AUTO = 1.5    # diámetros alrededor del nudo cuando no hay encuadre


def hoja(datos: dict, vista: str = "arriba") -> Image.Image:
    """Un cuadro por paso. `datos` es el contenido de modelo.json y `vista` es
    «arriba» o la inclinación de la cámara en grados."""
    x0, x1, y0, y1 = _encuadre(datos)
    ppd = ANCHO / (x1 - x0)
    alto = int(round((y1 - y0) * ppd))
    centro = np.array([(x0 + x1) / 2, (y0 + y1) / 2, 0.0])
    angulo = "arriba" if vista == "arriba" else float(vista)
    cuadros = []
    for p in datos["pasos"]:
        im = Image.fromarray(_cuadro(_cuerdas(datos, p), angulo, ANCHO, alto, ppd, centro))
        ImageDraw.Draw(im).text((12, 10), f"Paso {p['n']}", fill=(30, 30, 30))
        cuadros.append(im)
    filas = (len(cuadros) + COLUMNAS - 1) // COLUMNAS
    out = Image.new("RGB", (COLUMNAS * ANCHO, filas * alto), (255, 255, 255))
    for k, c in enumerate(cuadros):
        out.paste(c, ((k % COLUMNAS) * ANCHO, (k // COLUMNAS) * alto))
    return out


def _encuadre(datos: dict) -> tuple[float, float, float, float]:
    if datos.get("encuadre"):
        (x0, x1), (y0, y1) = datos["encuadre"]["x"], datos["encuadre"]["y"]
        return x0, x1, y0, y1
    todos = np.vstack([np.asarray(p["puntos"], float)[:, :2] for p in datos["pasos"]])
    (x0, y0), (x1, y1) = todos.min(0) - MARGEN_AUTO, todos.max(0) + MARGEN_AUTO
    return float(x0), float(x1), float(y0), float(y1)


def _cuerdas(datos: dict, p: dict) -> list[tuple[np.ndarray, float, np.ndarray, list | None]]:
    """Las cuerdas de un paso de modelo.json: sus puntos, su radio, su color y el tramo
    resaltado a lo largo de esa cuerda (None si no está en ella)."""
    X = np.asarray(p["puntos"], float)
    if "cuerdas" not in datos:
        return [(X, R, AZUL, p["resaltado"])]
    out = []
    for c, (i0, i1) in zip(datos["cuerdas"], p["tramos"]):
        hl = p["resaltado"]
        s0, s1 = i0 * p["h"], i1 * p["h"]
        if hl is not None:
            hl = [v - s0 for v in hl] if s0 <= (hl[0] + hl[1]) / 2 <= s1 else None
        out.append((X[i0:i1 + 1], c["grosor"] * R, COLORES[c["color"]], hl))
    return out


def _densificar(X, paso=0.06):
    seg = np.linalg.norm(np.diff(X, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    sg = np.arange(0, s[-1], paso)
    return np.stack([np.interp(sg, s, X[:, k]) for k in range(3)], 1), sg, s[-1]


def _base(vista):
    """Ejes de la cámara (filas) en coordenadas del mundo."""
    if vista == "arriba":
        zc = np.array([0.0, 0.0, 1.0])
    else:
        t = np.radians(vista)
        zc = np.array([0.0, -np.sin(t), np.cos(t)])
    arriba = np.array([0.0, 1.0, 0.0])
    xc = np.cross(arriba, zc)
    xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    return np.stack([xc, yc, zc])


def _esferas(C, W, H, ppd, radios, normales=True):
    """Dibuja una esfera en cada punto, del radio de su cuerda, con z-buffer."""
    zb = np.full((H, W), -np.inf)
    idx = np.full((H, W), -1, int)
    nrm = np.zeros((H, W, 3)) if normales else None
    for m in range(len(C)):
        radio = float(radios[m])
        rad = radio * ppd
        px, py = W / 2 + C[m, 0] * ppd, H / 2 - C[m, 1] * ppd
        x0, x1 = int(max(0, np.floor(px - rad))), int(min(W, np.ceil(px + rad) + 1))
        y0, y1 = int(max(0, np.floor(py - rad))), int(min(H, np.ceil(py + rad) + 1))
        if x0 >= x1 or y0 >= y1:
            continue
        xs = (np.arange(x0, x1) + 0.5 - px) / ppd
        ys = -(np.arange(y0, y1) + 0.5 - py) / ppd
        dx, dy = np.meshgrid(xs, ys)
        r2 = dx * dx + dy * dy
        msk = r2 < radio * radio
        if not msk.any():
            continue
        dz = np.sqrt(np.maximum(radio * radio - r2, 0))
        prof = C[m, 2] + dz
        win = zb[y0:y1, x0:x1]
        upd = msk & (prof > win)
        win[upd] = prof[upd]
        idx[y0:y1, x0:x1][upd] = m
        if normales:
            nw = nrm[y0:y1, x0:x1]
            nw[upd] = np.stack([dx[upd], dy[upd], dz[upd]], 1) / radio
    return zb, idx, nrm


def _cuadro(cuerdas, vista, W, H, ppd, centro, luz=(-0.5, 0.6, 1.0)):
    """`cuerdas` es la lista de _cuerdas. Cada una se densifica por separado: entre el final
    de una y el comienzo de la siguiente no hay cuerda."""
    partes = []
    for X, radio, color, resaltado in cuerdas:
        Xd, sd, L = _densificar(X)
        col = np.tile(color, (len(Xd), 1))
        if resaltado is not None:
            col[(sd >= resaltado[0]) & (sd <= resaltado[1])] = AMBAR
        col[sd > L - 0.8 * (radio / R)] = REMATE
        partes.append((Xd, col, np.full(len(Xd), radio)))
    Xd = np.vstack([x for x, _, _ in partes])
    col = np.vstack([c for _, c, _ in partes])
    radios = np.concatenate([r for _, _, r in partes])
    B = _base(vista)
    C = (Xd - centro) @ B.T
    zb, idx, nrm = _esferas(C, W, H, ppd, radios)
    cuerda = idx >= 0

    # posición en el mundo de cada píxel (cuerda o mesa)
    ys, xs = np.mgrid[0:H, 0:W]
    cx = (xs + 0.5 - W / 2) / ppd
    cy = -(ys + 0.5 - H / 2) / ppd
    n_c = B @ np.array([0, 0, 1.0])
    p0 = B @ (np.zeros(3) - centro)
    tz = (n_c @ p0 - n_c[0] * cx - n_c[1] * cy) / n_c[2]
    cz = np.where(cuerda, zb, tz)
    Pw = np.stack([cx, cy, cz], -1) @ B + centro

    # mapa de sombra en la dirección de la luz
    Ld = np.array(luz, float)
    Ld /= np.linalg.norm(Ld)
    up = np.array([0, 1.0, 0]) if abs(Ld[1]) < 0.9 else np.array([1.0, 0, 0])
    lx = np.cross(up, Ld)
    lx /= np.linalg.norm(lx)
    ly = np.cross(Ld, lx)
    BL = np.stack([lx, ly, Ld])
    CL = (Xd - centro) @ BL.T
    sppd = 14.0
    ext = np.abs(CL[:, :2]).max(0) + 2
    SW, SH = int(2 * ext[0] * sppd), int(2 * ext[1] * sppd)
    szb, _, _ = _esferas(CL, SW, SH, sppd, radios, normales=False)
    PL = (Pw - centro) @ BL.T
    u = np.clip((SW / 2 + PL[..., 0] * sppd).astype(int), 0, SW - 1)
    v = np.clip((SH / 2 - PL[..., 1] * sppd).astype(int), 0, SH - 1)
    ocl = szb[v, u]
    lit = ((~np.isfinite(ocl)) | (ocl < PL[..., 2] + 0.06)).astype(float)
    lit = gaussian_filter(lit, sigma=max(1.0, 0.08 * ppd))

    # oscurecimiento de contacto sobre la mesa
    dist, cual = cKDTree(Xd).query(Pw.reshape(-1, 3), k=1)
    dist = (dist - radios[cual]).reshape(H, W)
    ao = 1 - 0.45 * np.exp(-np.maximum(dist, 0) / 0.3)

    img = np.zeros((H, W, 3))
    mesa = ~cuerda
    img[mesa] = MESA * (0.55 + 0.45 * lit[mesa])[:, None] * ao[mesa][:, None]
    n_w = nrm @ B
    lam = np.clip((n_w * Ld).sum(-1), 0, 1)
    Hv = Ld + B[2]
    Hv /= np.linalg.norm(Hv)
    brillo = np.clip((n_w * Hv).sum(-1), 0, 1) ** 28
    base = col[np.maximum(idx, 0)]
    luz_total = (0.28 + 0.72 * lam * lit)[..., None]
    rimg = base * luz_total + 0.22 * (brillo * lit)[..., None]
    img[cuerda] = rimg[cuerda]
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    return (img * 255).astype(np.uint8)
