"""La calidad del movimiento de la cuerda en un video (T21a).

Mide en los cuadros que ve quien mira el video lo que lo hace verse tosco:

- **El largo.** La cantidad de nodos y el largo total en cada cuadro. Una cuerda de verdad no se
  acorta ni se alarga mientras se ata. Además, si cambia la cantidad de nodos, de un cuadro al
  siguiente no se sabe qué nodo es cuál.
- **La velocidad, la aceleración y el tirón** de cada nodo: las diferencias primera, segunda y
  tercera entre cuadros seguidos, multiplicadas por los cuadros por segundo. Se miden solo entre
  cuadros con la misma cantidad de nodos.
- **Los brincos:** veces en que algún nodo acelera más que BRINCO. Un movimiento rápido y un
  brinco se distinguen por la aceleración, no por cuánto se mueve el nodo.
- **Las paradas en seco** de la punta: veces en que su aceleración pasa de SECO. Pasar de 5 a 2,5
  d/s en un cuadro son 150 d/s², mientras que la mano de T17 llega a su velocidad en 0,3 s, a
  unos 17 d/s².
- **Las paradas:** veces en que todo deja de moverse, y la parte de los cuadros en que nada se
  mueve. En la cuerda son las pausas; en la cámara, cuando se congela.

Todo va en d, d/s, d/s² y d/s³ (d es el diámetro de la cuerda), así que no depende de los
cuadros por segundo. También sirve para la cámara: es una cuerda de un nodo.
"""
from __future__ import annotations

import numpy as np

BRINCO = 360.0   # d/s²: 0,1 d de diferencia segunda a 60 cuadros por segundo
SECO = 50.0      # d/s²: un cambio de velocidad de la punta en seco
QUIETO = 0.02    # d/s: más lento que esto, un nodo está quieto


def largo(X) -> float:
    """El largo de la cuerda X (N, 3), en d."""
    X = np.asarray(X, float)
    return float(np.linalg.norm(np.diff(X, axis=0), axis=1).sum()) if len(X) > 1 else 0.0


def _resumen(valores, cuantiles=(50, 95, 99)) -> dict | None:
    v = np.asarray(valores, float)
    if v.size == 0:
        return None
    out = {f"p{q}": round(float(np.percentile(v, q)), 3) for q in cuantiles}
    out["max"] = round(float(v.max()), 3)
    return out


def episodios(marca) -> int:
    """Cuántas veces una condición empieza a cumplirse (los tramos seguidos de True)."""
    m = np.asarray(marca, bool)
    if m.size == 0:
        return 0
    return int(m[0]) + int(np.sum(m[1:] & ~m[:-1]))


def medir(cuadros, fps: float, fases=None, punta: int = -1) -> dict:
    """Las medidas del movimiento de una lista de cuadros, cada uno con los nodos (N, 3) de la
    cuerda. `fases` es el nombre de la fase de cada cuadro, para contar cuánto dura cada una.
    `punta` es el nodo que lleva la mano (el último)."""
    X = [np.asarray(x, float).reshape(-1, 3) for x in cuadros]
    n = len(X)
    if n == 0:
        raise ValueError("no hay cuadros")
    N = np.array([len(x) for x in X])
    L = np.array([largo(x) for x in X])
    igual = N[1:] == N[:-1]               # pares de cuadros seguidos con los mismos nodos
    vel, v_punta, movido = [], [], []
    for k in range(n - 1):
        if not igual[k]:
            continue
        rapidez = np.linalg.norm(X[k + 1] - X[k], axis=1) * fps
        vel.append(rapidez.max())
        v_punta.append(rapidez[punta])
        movido.append(rapidez.max() >= QUIETO)
    acel, a_punta = [], []
    for k in range(1, n - 1):
        if not (igual[k - 1] and igual[k]):
            continue
        a = np.linalg.norm(X[k + 1] - 2 * X[k] + X[k - 1], axis=1) * fps * fps
        acel.append(a.max())
        a_punta.append(a[punta])
    tiron = []
    for k in range(1, n - 2):
        if not (igual[k - 1] and igual[k] and igual[k + 1]):
            continue
        j = np.linalg.norm(X[k + 2] - 3 * X[k + 1] + 3 * X[k] - X[k - 1], axis=1) * fps ** 3
        tiron.append(j.max())
    acel, a_punta, movido = np.array(acel), np.array(a_punta), np.array(movido, bool)
    informe = {
        "cuadros": n,
        "segundos": round(n / fps, 2),
        "nodos": {"min": int(N.min()), "max": int(N.max()), "cambios": int((~igual).sum())},
        "largo": {"min": round(float(L.min()), 2), "max": round(float(L.max()), 2),
                  "variacion": round(float((L.max() - L.min()) / max(float(L.max()), 1e-9)), 4)},
        "velocidad": _resumen(vel),
        "aceleracion": _resumen(acel),
        "tiron": _resumen(tiron),
        "brincos": episodios(acel > BRINCO),
        "punta": {"velocidad": _resumen(v_punta), "paradas_en_seco": episodios(a_punta > SECO)},
        "paradas": episodios(~movido),
        "quietos": round(float(np.mean(~movido)), 3) if movido.size else 0.0,
    }
    if fases is not None:
        cuenta: dict[str, int] = {}
        for f in fases:
            cuenta[f] = cuenta.get(f, 0) + 1
        informe["fases"] = {f: round(c / fps, 2) for f, c in sorted(cuenta.items())}
    return informe
