#!/usr/bin/env python3
"""Verification renders: orthographic sphere-swept tube with z-buffer,
shadow map from a directional light, and contact darkening on the table."""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

R = 0.5
BLUE = np.array([0.10, 0.25, 0.75])
AMBER = np.array([0.95, 0.55, 0.12])
WHIP = np.array([0.35, 0.06, 0.06])
TABLE = np.array([0.80, 0.81, 0.80])


def densify(X, step=0.06):
    seg = np.linalg.norm(np.diff(X, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    sg = np.arange(0, s[-1], step)
    return np.stack([np.interp(sg, s, X[:, k]) for k in range(3)], 1), sg, s[-1]


def basis(view):
    if view == "top":
        zc = np.array([0.0, 0.0, 1.0]); up = np.array([0.0, 1.0, 0.0])
    else:
        t = np.radians(view)
        zc = np.array([0.0, -np.sin(t), np.cos(t)]); up = np.array([0.0, 1.0, 0.0])
    xc = np.cross(up, zc); xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    return np.stack([xc, yc, zc])          # rows: camera axes in world coords


def splat(C, W, H, ppd, want_normals=True):
    zb = np.full((H, W), -np.inf)
    idx = np.full((H, W), -1, int)
    nrm = np.zeros((H, W, 3)) if want_normals else None
    rad = R * ppd
    for m in range(len(C)):
        px, py = W / 2 + C[m, 0] * ppd, H / 2 - C[m, 1] * ppd
        x0, x1 = int(max(0, np.floor(px - rad))), int(min(W, np.ceil(px + rad) + 1))
        y0, y1 = int(max(0, np.floor(py - rad))), int(min(H, np.ceil(py + rad) + 1))
        if x0 >= x1 or y0 >= y1:
            continue
        xs = (np.arange(x0, x1) + 0.5 - px) / ppd
        ys = -(np.arange(y0, y1) + 0.5 - py) / ppd
        dx, dy = np.meshgrid(xs, ys)
        r2 = dx * dx + dy * dy
        msk = r2 < R * R
        if not msk.any():
            continue
        dz = np.sqrt(np.maximum(R * R - r2, 0))
        depth = C[m, 2] + dz
        win = zb[y0:y1, x0:x1]
        upd = msk & (depth > win)
        win[upd] = depth[upd]
        idx[y0:y1, x0:x1][upd] = m
        if want_normals:
            nw = nrm[y0:y1, x0:x1]
            nw[upd] = np.stack([dx[upd], dy[upd], dz[upd]], 1) / R
    return zb, idx, nrm


def render(X, hl, view, W, H, ppd, ctr, light=(-0.5, 0.6, 1.0)):
    Xd, sd, L = densify(X)
    col = np.tile(BLUE, (len(Xd), 1))
    if hl is not None:
        m = (sd >= hl[0]) & (sd <= hl[1])
        col[m] = AMBER
    col[sd > L - 0.8] = WHIP
    B = basis(view)
    C = (Xd - ctr) @ B.T
    zb, idx, nrm = splat(C, W, H, ppd)
    rope = idx >= 0

    # world position of each pixel (rope surface or table)
    ys, xs = np.mgrid[0:H, 0:W]
    cx = (xs + 0.5 - W / 2) / ppd
    cy = -(ys + 0.5 - H / 2) / ppd
    n_c = B @ np.array([0, 0, 1.0])           # table normal in camera coords
    p0 = B @ (np.zeros(3) - ctr)
    tz = (n_c @ p0 - n_c[0] * cx - n_c[1] * cy) / n_c[2]
    cz = np.where(rope, zb, tz)
    Pc = np.stack([cx, cy, cz], -1)
    Pw = Pc @ B + ctr                          # camera -> world

    # shadow map along the light direction
    Ld = np.array(light, float); Ld /= np.linalg.norm(Ld)
    up = np.array([0, 1.0, 0]) if abs(Ld[1]) < 0.9 else np.array([1.0, 0, 0])
    lx = np.cross(up, Ld); lx /= np.linalg.norm(lx); ly = np.cross(Ld, lx)
    BL = np.stack([lx, ly, Ld])
    CL = (Xd - ctr) @ BL.T
    sppd = 14.0
    ext = np.abs(CL[:, :2]).max(0) + 2
    SW, SH = int(2 * ext[0] * sppd), int(2 * ext[1] * sppd)
    szb, _, _ = splat(CL, SW, SH, sppd, want_normals=False)
    PL = (Pw - ctr) @ BL.T
    u = np.clip((SW / 2 + PL[..., 0] * sppd).astype(int), 0, SW - 1)
    v = np.clip((SH / 2 - PL[..., 1] * sppd).astype(int), 0, SH - 1)
    occl = szb[v, u]
    lit = (~np.isfinite(occl)) | (occl < PL[..., 2] + 0.06)
    lit = lit.astype(float)
    lit = gaussian_filter(lit, sigma=max(1.0, 0.08 * ppd))

    # contact darkening on the table from distance to the rope surface
    tree = cKDTree(Xd)
    dist, _ = tree.query(Pw.reshape(-1, 3), k=1)
    dist = (dist - R).reshape(H, W)
    ao = 1 - 0.45 * np.exp(-np.maximum(dist, 0) / 0.3)

    img = np.zeros((H, W, 3))
    tab = ~rope
    img[tab] = TABLE * (0.55 + 0.45 * lit[tab])[:, None] * ao[tab][:, None]

    n_w = nrm @ B                               # camera normals -> world
    lam = np.clip((n_w * Ld).sum(-1), 0, 1)
    Hv = Ld + B[2]; Hv /= np.linalg.norm(Hv)
    spec = np.clip((n_w * Hv).sum(-1), 0, 1) ** 28
    base = col[np.maximum(idx, 0)]
    shade = (0.28 + 0.72 * lam * lit)[..., None]
    rimg = base * shade + 0.22 * (spec * lit)[..., None]
    img[rope] = rimg[rope]
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    return (img * 255).astype(np.uint8)


def main(out_dir, which):
    steps = np.load(f"{out_dir}/steps.npy", allow_pickle=True)
    meta = json.load(open(f"{out_dir}/meta.json"))
    view = "top" if which == "top" else float(which)
    W, H, ppd = 520, 700, 25.0
    ctr = np.array([-1.0, -1.6, 0.0])
    tiles = []
    for X, m in zip(steps, meta):
        im = render(X.astype(float), m["hl"], view, W, H, ppd, ctr)
        pil = Image.fromarray(im)
        ImageDraw.Draw(pil).text((12, 10), f"Paso {m['n']}", fill=(30, 30, 30))
        pil.save(f"{out_dir}/step{m['n']}_{which}.png")
        tiles.append(pil)
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rows * H), (255, 255, 255))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * W, (k // cols) * H))
    sheet.save(f"{out_dir}/sheet_{which}.png")
    print("ok", which)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
