#!/usr/bin/env python3
"""As de guía (bowline): step models.

Pipeline per step:
  2D design (control points, own layout)  ->  smooth curve resampled by arc length
  -> crossings + Gauss word checked against the reference sequence
  -> lift to 3D (over-strand rides on the under-strand)
  -> position-based relaxation (inextensible, gravity, table, self-collision)
  -> validation (same crossing word after relaxing, no interpenetration)
  -> export JSON for the 3D viewer + verification renders.

Units: rope diameter d = 1. x right, y up (away from the reader), z up from the table.
"""
import json
import math
import sys
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

H = 0.2          # resample spacing
R = 0.5          # rope radius
CLEAR = 1.0      # centre-line clearance = diameter

# --------------------------------------------------------------------------
# Design. Own layout; the photos were used only to read the topology.
# --------------------------------------------------------------------------
S_TOP = [(0.0, 30.0), (0.0, 22.0), (0.03, 15.0), (0.08, 11.5), (0.12, 9.6),
         (0.18, 7.6), (0.22, 5.8), (0.27, 4.1), (0.35, 2.6)]
S_TOP_NOLOOP = S_TOP[:-3] + [(0.35, 5.4), (1.0, 3.3), (2.1, 1.2)]

# Nipping loop: from the first pass at C1 round clockwise back to C1.
NL = [(0.15, 1.2), (-0.5, 0.05), (-1.6, -0.5), (-2.8, -0.6), (-3.9, -0.2),
      (-4.6, 0.8), (-4.8, 2.1), (-4.3, 3.5), (-3.3, 4.35), (-2.1, 4.55),
      (-0.9, 4.0), (0.35, 2.6)]

# Eye, large (steps 1-3) and normal (steps 4-7). Both start right after C1.
EYE_BIG = [(1.4, 1.5), (3.2, -0.6), (4.9, -3.3), (6.0, -6.5), (6.0, -9.6),
           (4.6, -12.2), (1.8, -13.6), (-1.8, -13.7), (-5.0, -12.6),
           (-7.2, -10.2), (-8.0, -7.2)]
EYE_N = [(1.4, 1.5), (3.0, -0.6), (4.3, -3.3), (5.0, -6.2), (4.8, -8.9),
         (3.5, -11.0), (1.0, -12.1), (-2.0, -12.1), (-4.5, -11.0),
         (-5.9, -8.8), (-6.1, -6.3), (-5.4, -4.0)]

W_FREE = [(-8.1, -4.2), (-7.9, -1.2), (-7.5, 1.4), (-7.0, 3.2)]
W_TOWARD = [(-7.7, -4.6), (-6.6, -3.2), (-5.1, -2.5), (-3.9, -1.9)]
W_UP = [(-4.3, -2.4), (-3.35, -1.2), (-3.0, 0.3), (-2.95, 2.4)]
W_THROUGH_END = [(-3.0, 5.6), (-3.3, 7.0)]
W_COLLAR_A = [(-3.0, 5.8), (-2.8, 7.4), (-2.1, 8.75), (-1.0, 9.55), (1.3, 9.62)]
W_BEHIND_END = [(2.6, 9.4), (3.7, 9.15)]
W_COLLAR_B = [(2.5, 8.95), (3.0, 7.85), (2.7, 6.75), (1.8, 6.1), (0.8, 5.8),
              (-0.5, 5.45), (-1.3, 4.95), (-1.7, 3.95)]
W_BACK_END = [(-1.75, 3.1)]
W_DOWN = [(-1.75, 2.0), (-1.72, 0.6), (-1.66, -1.6), (-1.6, -3.0), (-1.55, -4.0)]


def _step(parts, hl_from):
    """parts: list of point lists; hl_from: index into the concatenated list
    where the highlighted ('what moves in this step') stretch begins."""
    pts = [p for part in parts for p in part]
    return pts, hl_from


def build_steps():
    steps = []
    a = S_TOP_NOLOOP + EYE_BIG[1:] + W_FREE
    steps.append(dict(n=1, pts=a, hl=None, code=[]))
    a = S_TOP + NL + EYE_BIG + W_FREE
    steps.append(dict(n=2, pts=a, hl=(len(S_TOP) - 1, len(S_TOP) + len(NL)),
                      code="1U 1O"))
    a = S_TOP + NL + EYE_BIG + W_TOWARD
    steps.append(dict(n=3, pts=a, hl=(len(a) - len(W_TOWARD) - 2, len(a) - 1),
                      code="1U 1O"))
    base = S_TOP + NL + EYE_N + W_UP
    a = base + W_THROUGH_END
    steps.append(dict(n=4, pts=a, hl=(len(base) - len(W_UP), len(a) - 1),
                      code="1U 2O 3U 1O 2U 3O"))
    a = base + W_COLLAR_A + W_BEHIND_END
    steps.append(dict(n=5, pts=a, hl=(len(base), len(a) - 1),
                      code="4O 1U 2O 3U 1O 2U 3O 4U"))
    a = base + W_COLLAR_A + W_COLLAR_B + W_BACK_END
    steps.append(dict(n=6, pts=a, hl=(len(base) + len(W_COLLAR_A) - 1, len(a) - 1),
                      code="4O 5U 1U 2O 3U 6U 1O 2U 3O 4U 5O 6O"))
    a = base + W_COLLAR_A + W_COLLAR_B + W_DOWN
    steps.append(dict(n=7, pts=a, hl=(len(a) - len(W_DOWN) - 3, len(a) - 1),
                      code="4O 5U 1U 7O 2O 3U 6U 1O 2U 3O 4U 5O 6O 7U"))
    for st in steps:
        c = st["code"]
        st["code"] = c.split() if isinstance(c, str) else c
    return steps


# --------------------------------------------------------------------------
# Curve construction
# --------------------------------------------------------------------------
def catmull_rom(P, alpha=0.5):
    """Centripetal Catmull-Rom through all points. Returns dense polyline and
    the dense index at which each control point lies."""
    P = np.asarray(P, float)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    dense, ctrl = [], []
    count = 0
    for i in range(len(Q) - 3):
        p0, p1, p2, p3 = Q[i:i + 4]
        ctrl.append(count)
        d01 = max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        d12 = max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        d23 = max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        t0, t1 = 0.0, d01
        t2, t3 = t1 + d12, t1 + d12 + d23
        n = max(8, int(np.linalg.norm(p2 - p1) * 24))
        t = np.linspace(t1, t2, n, endpoint=False)[:, None]
        A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
        B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
        C = (t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2
        dense.append(C)
        count += n
    ctrl.append(count)
    dense.append(Q[-2][None])
    return np.vstack(dense), ctrl


def resample(D, ctrl, h=H):
    seg = np.linalg.norm(np.diff(D, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    L = s[-1]
    n = int(round(L / h))
    hh = L / n
    sg = np.linspace(0.0, L, n + 1)
    X = np.stack([np.interp(sg, s, D[:, k]) for k in range(D.shape[1])], axis=1)
    return X, hh, s[ctrl]


# --------------------------------------------------------------------------
# Crossings and Gauss word
# --------------------------------------------------------------------------
@dataclass
class Crossing:
    sa: float      # arc position of first pass
    sb: float      # arc position of second pass
    p: np.ndarray  # xy location
    sin: float     # |sin| of crossing angle


def find_crossings(X, h):
    P = X[:, :2]
    A, B = P[:-1], P[1:]
    n = len(A)
    i, j = np.triu_indices(n, k=2)
    lo, hi = np.minimum(A, B), np.maximum(A, B)
    ok = ((lo[i, 0] <= hi[j, 0]) & (lo[j, 0] <= hi[i, 0]) &
          (lo[i, 1] <= hi[j, 1]) & (lo[j, 1] <= hi[i, 1]))
    i, j = i[ok], j[ok]
    r, s = B[i] - A[i], B[j] - A[j]
    qp = A[j] - A[i]
    rxs = r[:, 0] * s[:, 1] - r[:, 1] * s[:, 0]
    nz = np.abs(rxs) > 1e-12
    i, j, r, s, qp, rxs = i[nz], j[nz], r[nz], s[nz], qp[nz], rxs[nz]
    t = (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / rxs
    u = (qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]) / rxs
    hit = (t >= 0) & (t < 1) & (u >= 0) & (u < 1)
    out = []
    for k in np.nonzero(hit)[0]:
        sa, sb = (i[k] + t[k]) * h, (j[k] + u[k]) * h
        if any(abs(c.sa - sa) < 0.3 and abs(c.sb - sb) < 0.3 for c in out):
            continue
        sn = abs(rxs[k]) / (np.linalg.norm(r[k]) * np.linalg.norm(s[k]))
        out.append(Crossing(sa, sb, A[i[k]] + t[k] * r[k], sn))
    return out


def occurrences(cr):
    occ = [(c.sa, k, 0) for k, c in enumerate(cr)] + [(c.sb, k, 1) for k, c in enumerate(cr)]
    occ.sort()
    return occ


def canonical(labels):
    m, out = {}, []
    for lb in labels:
        if lb not in m:
            m[lb] = len(m)
        out.append(m[lb])
    return out


def assign_overs(cr, code):
    """Map the reference code onto the geometric crossings.
    Returns overs[k] = True if the first pass of crossing k is the over pass."""
    occ = occurrences(cr)
    geo = canonical([k for _, k, _ in occ])
    ref = canonical([c[:-1] for c in code])
    if geo != ref:
        raise ValueError(f"crossing pattern differs: geometry {geo} vs reference {ref}")
    overs = [None] * len(cr)
    for (_, k, which), c in zip(occ, code):
        is_over = c[-1] == "O"
        if which == 0:
            overs[k] = is_over
    return overs


def word_from_z(X, h, cr):
    s = np.arange(len(X)) * h
    occ = occurrences(cr)
    labels = {}
    out = []
    for _, k, which in occ:
        c = cr[k]
        za = np.interp(c.sa, s, X[:, 2])
        zb = np.interp(c.sb, s, X[:, 2])
        first_over = za > zb
        over = first_over if which == 0 else not first_over
        labels.setdefault(k, len(labels) + 1)
        out.append(f"{labels[k]}{'O' if over else 'U'}")
    return out


# --------------------------------------------------------------------------
# 3D lift and relaxation
# --------------------------------------------------------------------------
def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def lift(X2, h, cr, overs):
    N = len(X2)
    s = np.arange(N) * h
    z = np.full(N, R)
    for _ in range(6):
        for k, c in enumerate(cr):
            so, su = (c.sa, c.sb) if overs[k] else (c.sb, c.sa)
            zu = np.interp(su, s, z)
            hgt = zu + CLEAR - R
            w = float(np.clip(2.6 / max(c.sin, 0.25), 2.6, 5.0))
            b = smoothstep((1.0 - np.abs(s - so) / w) / 0.65)
            z = np.maximum(z, R + hgt * b)
    return np.column_stack([X2, z])


def _collide(X, skip, free, gain=1.0):
    tree = cKDTree(X)
    pr = tree.query_pairs(r=CLEAR, output_type="ndarray")
    if len(pr):
        pr = pr[np.abs(pr[:, 0] - pr[:, 1]) > skip]
    if not len(pr):
        return 0.0
    d = X[pr[:, 1]] - X[pr[:, 0]]
    dist = np.linalg.norm(d, axis=1)
    corr = ((CLEAR - dist) / 2.0 / np.maximum(dist, 1e-9))[:, None] * d
    acc = np.zeros_like(X)
    cnt = np.zeros(len(X))
    np.add.at(acc, pr[:, 0], -corr)
    np.add.at(acc, pr[:, 1], corr)
    np.add.at(cnt, pr[:, 0], 1)
    np.add.at(cnt, pr[:, 1], 1)
    m = (cnt > 0) & free
    X[m] += gain * acc[m] / cnt[m][:, None]
    return float((CLEAR - dist).max())


def _lengths(X, h, free, passes=8):
    """Red-black Gauss-Seidel on segment lengths (vectorised)."""
    N = len(X)
    for _ in range(passes):
        for parity in (0, 1):
            i = np.arange(parity, N - 1, 2)
            seg = X[i + 1] - X[i]
            L = np.linalg.norm(seg, axis=1)
            c = ((L - h) / np.maximum(L, 1e-9))[:, None] * seg
            fa, fb = free[i], free[i + 1]
            wa = np.where(fa & fb, 0.5, np.where(fa, 1.0, 0.0))
            wb = np.where(fa & fb, 0.5, np.where(fb, 1.0, 0.0))
            X[i] += wa[:, None] * c
            X[i + 1] -= wb[:, None] * c


def _limit_bend(X, h, free, rmin=1.0, gain=0.5):
    """Smooth only where the local bend radius is below rmin (removes kinks
    without letting the whole layout drift)."""
    t = X[1:] - X[:-1]
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]
    ang = np.arccos(np.clip((t[1:] * t[:-1]).sum(1), -1, 1))
    bad = np.nonzero(ang > h / rmin)[0] + 1
    bad = bad[free[bad]]
    if len(bad):
        X[bad] += gain * (X[bad - 1] + X[bad + 1] - 2 * X[bad])
    return len(bad)


def relax(X, h, iters=1000, pin=3):
    """Position-based relaxation. The xy anchors model table friction; they are
    weak, so rope can slide to supply the length that climbing over a strand
    costs. Gravity lets every over-strand settle onto what is under it."""
    X = X.copy()
    anchor = X[:, :2].copy()
    N = len(X)
    skip = int(math.ceil(1.6 / h))
    free = np.ones(N, bool)
    free[:pin] = False
    for it in range(iters):
        late = it > iters * 0.75
        g = 0.0 if late else 0.003
        ka = 0.004 if late else 0.012
        X[free, 2] -= g
        lap = X[:-2] + X[2:] - 2 * X[1:-1]
        X[1:-1, 2] += 0.45 * lap[:, 2]
        X[1:-1, :2] += 0.02 * lap[:, :2]
        X[free, :2] += ka * (anchor[free] - X[free, :2])
        for _ in range(2):
            _limit_bend(X, h, free, rmin=1.1, gain=0.35)
            _collide(X, skip, free)
            X[:, 2] = np.maximum(X[:, 2], R)
            _lengths(X, h, free, passes=4)
    for _ in range(80):
        _limit_bend(X, h, free, rmin=1.1, gain=0.25)
        _collide(X, skip, free)
        X[:, 2] = np.maximum(X[:, 2], R)
        _lengths(X, h, free, passes=4)
    return X


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def min_clearance(X, h):
    skip = int(math.ceil(1.6 / h))
    tree = cKDTree(X)
    pr = tree.query_pairs(r=CLEAR * 1.05, output_type="ndarray")
    if len(pr):
        pr = pr[np.abs(pr[:, 0] - pr[:, 1]) > skip]
    if not len(pr):
        return CLEAR * 1.05
    return float(np.linalg.norm(X[pr[:, 1]] - X[pr[:, 0]], axis=1).min())


def min_bend_radius(X, h, win=3):
    """Bend radius over a window of `win` segments each side (less noisy
    than single-segment angles)."""
    t = np.diff(X, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    a, b = t[:-2 * win], t[2 * win:]
    ang = np.arccos(np.clip((a * b).sum(1), -1, 1))
    k = ang / (2 * win * h)
    i = int(k.argmax())
    return float(1.0 / max(k[i], 1e-9)), X[i + win + 1]


def process(st):
    D, ctrl = catmull_rom(st["pts"])
    X2, h, ctrl_s = resample(D, ctrl)
    cr = find_crossings(X2, h)
    overs = assign_overs(cr, st["code"]) if cr else []
    if len(cr) != len(st["code"]) // 2:
        raise ValueError(f"step {st['n']}: {len(cr)} crossings, expected {len(st['code']) // 2}")
    X = lift(X2, h, cr, overs)
    Xr = relax(X, h)
    cr2 = find_crossings(Xr, h)
    got = word_from_z(Xr, h, cr2)
    ref = [f"{lab}{c[-1]}" for lab, c in zip(canonical([c[:-1] for c in st["code"]]), st["code"])]
    ref = [f"{int(x[:-1]) + 1}{x[-1]}" for x in ref]
    seg = np.linalg.norm(np.diff(Xr, axis=0), axis=1)
    br, br_at = min_bend_radius(Xr, h)
    br1, _ = min_bend_radius(Xr, h, win=1)
    drift = np.linalg.norm(Xr[:, :2] - X2, axis=1)
    rep = dict(
        n=st["n"], length=round(float(seg.sum()), 2), crossings=len(cr2),
        word=" ".join(got), ref=" ".join(ref), word_ok=got == ref,
        clearance=round(min_clearance(Xr, h), 3),
        bend_radius=round(br, 3), bend_local=round(br1, 3),
        bend_at=[round(float(v), 2) for v in br_at],
        stretch=round(float(np.abs(seg / h - 1).max()), 4),
        drift_max=round(float(drift.max()), 2),
        zmax=round(float(Xr[:, 2].max()), 3),
    )
    hl = None
    if st["hl"] is not None:
        hl = [float(ctrl_s[st["hl"][0]]), float(ctrl_s[st["hl"][1]])]
    return Xr, h, cr2, rep, hl


def main(out_dir):
    steps = build_steps()
    results = []
    for st in steps:
        Xr, h, cr, rep, hl = process(st)
        print(json.dumps(rep, ensure_ascii=False))
        results.append(dict(n=st["n"], X=Xr, h=h, hl=hl,
                            crossings=[[float(c.p[0]), float(c.p[1])] for c in cr],
                            rep=rep))
    np.save(f"{out_dir}/steps.npy", np.array([r["X"] for r in results], dtype=object),
            allow_pickle=True)
    meta = [dict(n=r["n"], h=r["h"], hl=r["hl"], crossings=r["crossings"], rep=r["rep"])
            for r in results]
    with open(f"{out_dir}/meta.json", "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
