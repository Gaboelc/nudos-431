"""La calidad del movimiento de la cuerda en un video (T21a).

Mide en los cuadros que ve quien mira el video lo que lo hace verse tosco:

- **El largo.** La cantidad de nodos y el largo total en cada cuadro. Una cuerda de verdad no se
  acorta ni se alarga mientras se ata. Además, si cambia la cantidad de nodos, de un cuadro al
  siguiente no se sabe qué nodo es cuál.
- **La velocidad, la aceleración y el tirón** de cada nodo: las diferencias primera, segunda y
  tercera entre cuadros seguidos, multiplicadas por los cuadros por segundo. Se miden solo entre
  cuadros con la misma cantidad de nodos.
- **Los brincos:** veces en que algún nodo acelera más que BRINCO. Un movimiento rápido y un
  brinco se distinguen por la aceleración, no por cuánto se mueve el nodo. Con la gravedad de
  T21, la cuerda que cae y se apoya en la mesa también pasa de BRINCO (la gravedad son 1225
  d/s²), así que con ella valen los **picos** y los **temblores**: un nodo que en un cuadro va más
  de PICO más rápido que en el de antes y en el de después, y al menos al doble (salta y se
  queda), o cuya aceleración pasa de TEMBLOR y cambia de sentido dos veces seguidas (salta y
  vuelve, o tiembla). Caer y apoyarse no es ninguna de las dos cosas: al apoyarse, la aceleración
  cambia de sentido una sola vez.
- **Las paradas en seco** de la punta: veces en que su aceleración pasa de SECO. Pasar de 5 a 2,5
  d/s en un cuadro son 150 d/s², mientras que la mano de T17 llega a su velocidad en 0,3 s, a
  unos 17 d/s². Esa aceleración también cuenta las curvas: a 10 d/s, una vuelta de 2 d de radio
  ya son 50 d/s². Por eso están también las **frenadas en seco** (T21): veces en que lo que
  cambia es la rapidez de la punta, más de SECO.
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
PICO = 6.0       # d/s: 0,1 d en un cuadro a 60 por segundo, por encima del de antes y del de después
TEMBLOR = 180.0  # d/s²: 0,05 d de diferencia segunda a 60 por segundo, que cambia de sentido dos
                 # veces seguidas


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


def medir(cuadros, fps: float, fases=None, punta: int = -1, puntas=None, largos=None) -> dict:
    """Las medidas del movimiento de una lista de cuadros, cada uno con los nodos (N, 3) de la
    cuerda. `fases` es el nombre de la fase de cada cuadro, para contar cuánto dura cada una.
    `punta` es el nodo que lleva la mano (el último). Con `puntas` (un punto por cuadro), la punta es
    ese punto, que entra a la medida como un nodo más: en una plantilla (T21d), donde la cuerda sale
    de la mano, entre dos nodos. Con `largos`, el largo de la cuerda en cada cuadro es ese."""
    X = [np.asarray(x, float).reshape(-1, 3) for x in cuadros]
    n = len(X)
    if n == 0:
        raise ValueError("no hay cuadros")
    N = np.array([len(x) for x in X])
    L = np.array([largo(x) for x in X]) if largos is None else np.asarray(largos, float)
    if puntas is not None:
        X = [np.vstack([x, np.asarray(p, float).reshape(1, 3)]) for x, p in zip(X, puntas)]
        punta = -1
    igual = N[1:] == N[:-1]               # pares de cuadros seguidos con los mismos nodos
    vel, v_punta, movido = [], [], []
    for k in range(n - 1):
        if not igual[k]:
            continue
        rapidez = np.linalg.norm(X[k + 1] - X[k], axis=1) * fps
        vel.append(rapidez.max())
        v_punta.append(rapidez[punta])
        movido.append(rapidez.max() >= QUIETO)
    acel, a_punta, frena = [], [], []
    for k in range(1, n - 1):
        if not (igual[k - 1] and igual[k]):
            continue
        a = np.linalg.norm(X[k + 1] - 2 * X[k] + X[k - 1], axis=1) * fps * fps
        acel.append(a.max())
        a_punta.append(a[punta])
        rapidez = [float(np.linalg.norm(X[j + 1][punta] - X[j][punta])) * fps for j in (k - 1, k)]
        frena.append(abs(rapidez[1] - rapidez[0]) * fps > SECO)
    tiron, pico, temblor = [], [], []
    for k in range(1, n - 2):
        if not (igual[k - 1] and igual[k] and igual[k + 1]):
            continue
        j = np.linalg.norm(X[k + 2] - 3 * X[k + 1] + 3 * X[k] - X[k - 1], axis=1) * fps ** 3
        tiron.append(j.max())
        d0, d1, d2 = (X[k] - X[k - 1]) * fps, (X[k + 1] - X[k]) * fps, (X[k + 2] - X[k + 1]) * fps
        v0, v1, v2 = (np.linalg.norm(d, axis=1) for d in (d0, d1, d2))
        # Un pico es un arrebato aislado: más de PICO sobre el cuadro de antes y el de después,
        # y al menos el doble de los dos (la cuerda que cae ya venía rápida al apoyarse).
        vecino = np.maximum(v0, v2)
        pico.append(bool(np.any((v1 - vecino > PICO) & (vecino < 0.5 * v1))))
        if k + 3 < n and igual[k + 2]:
            d3 = (X[k + 3] - X[k + 2]) * fps
            a0, a1, a2 = (d1 - d0) * fps, (d2 - d1) * fps, (d3 - d2) * fps
            m0, m1, m2 = (np.linalg.norm(a, axis=1) for a in (a0, a1, a2))
            vuelve = ((np.einsum("ij,ij->i", a0, a1) < 0) & (np.einsum("ij,ij->i", a1, a2) < 0)
                      & (np.minimum(np.minimum(m0, m1), m2) > TEMBLOR))
            temblor.append(bool(np.any(vuelve)))
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
        "picos": episodios(pico),
        "temblores": episodios(temblor),
        "punta": {"velocidad": _resumen(v_punta), "paradas_en_seco": episodios(a_punta > SECO),
                  "frenadas_en_seco": episodios(frena)},
        "paradas": episodios(~movido),
        "quietos": round(float(np.mean(~movido)), 3) if movido.size else 0.0,
    }
    if fases is not None:
        cuenta: dict[str, int] = {}
        for f in fases:
            cuenta[f] = cuenta.get(f, 0) + 1
        informe["fases"] = {f: round(c / fps, 2) for f, c in sorted(cuenta.items())}
    return informe
