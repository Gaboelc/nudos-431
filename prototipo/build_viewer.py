#!/usr/bin/env python3
"""Inject the relaxed step models into the viewer template."""
import json
import sys

import numpy as np

out_dir, template, dest = sys.argv[1], sys.argv[2], sys.argv[3]
steps = np.load(f"{out_dir}/steps.npy", allow_pickle=True)
meta = json.load(open(f"{out_dir}/meta.json"))

data = []
for X, m in zip(steps, meta):
    X = X.astype(float)
    L_full = float(np.linalg.norm(np.diff(X, axis=0), axis=1).sum())
    idx = list(range(0, len(X), 2))
    if idx[-1] != len(X) - 1:
        idx.append(len(X) - 1)
    P = X[idx]
    L = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    hl = None
    if m["hl"] is not None:
        hl = [round(m["hl"][0] / L_full, 4), round(min(m["hl"][1] / L_full, 1.0), 4)]
    data.append(dict(n=m["n"], L=round(L, 3), hl=hl, cr=m["rep"]["crossings"],
                     p=[round(v, 3) for v in P.ravel().tolist()]))

payload = json.dumps(dict(steps=data), separators=(",", ":"))
html = open(template, encoding="utf-8").read()
assert "/*__DATA__*/null" in html
html = html.replace("/*__DATA__*/null", payload)
open(dest, "w", encoding="utf-8").write(html)
print(dest, len(html) // 1024, "KB")
