"""Prueba de concepto del motor (T14a): atar el amarre cuadrado, hito por hito.

Un amarre no se aprieta tirando solo del final: el roce del ballestrinque de cierre no deja
pasar la tensión a las vueltas. Se aprieta mientras se ata, vuelta por vuelta. Así lo hace
el motor:
1. La cuerda hasta el primer hito de la plantilla (el ballestrinque de inicio) se asienta con
   el chicote corto fijo y la mano tirando de la punta con T newtons, hacia donde sigue la
   cuerda.
2. Se agrega el tramo de la plantilla hasta el hito siguiente, empalmado a la punta ya
   asentada (el corrimiento se reparte en los primeros diámetros del tramo nuevo), y se vuelve
   a asentar tirando de la nueva punta.
3. Y así hasta el cierre. Cada paso de la ficha es la cuerda asentada hasta su hito, más lo
   que sigue de la cuerda en la mesa (el resto del paso de hoy, empalmado igual).

Cada hito se comprueba como hoy (nudos/libre.py, _resultado): la secuencia que declara la
plantilla, con los cruces medidos en los mapas de los palos (nudos/plantillas/pasos.py), la
separación, la curvatura y el estiramiento. Los nodos no se remuestrean, así que cada uno
conserva la zona de la plantilla donde estaba.

Uso (en el entorno de la prueba, desde la raíz del repositorio):
    python poc/motor/atar_amarre.py [--tension 60] [--pasos 60]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from motor import Escena, Material, Motor, cilindro   # noqa: E402

from nudos import RAIZ   # noqa: E402
from nudos.construir import construir   # noqa: E402
from nudos.libre import _resultado, catmull_rom, remuestrear   # noqa: E402
from nudos.plantillas.pasos import buscar as en_la_cruz, geometria   # noqa: E402
from nudos.spec import cargar   # noqa: E402

SALIDA = RAIZ / "build" / "poc-motor"
HITOS = ["inicio", "vuelta-1", "vuelta-2", "vuelta-3", "ahorcado-1", "ahorcado-2", "ahorcado-3", "cierre-1", "cierre"]
EMPALME = 25   # nodos (5 diámetros) en que se reparte el corrimiento al empalmar


def zonas_y_hitos(spec, n_paso, puntos):
    """Las zonas de cada nodo del paso y dónde termina cada hito (índice de nodo)."""
    g = geometria(spec)
    c = g.cuerda(None)
    t = c.trazo(spec.pasos[n_paso - 1].hasta, spec.pasos[n_paso - 2].hasta if n_paso > 1 else None)
    D, ctrl = catmull_rom(t.puntos)
    X, h, s_ctrl = remuestrear(D, ctrl)
    assert len(X) == len(puntos), "el paso construido no es el de la plantilla"
    s = np.arange(len(X)) * h
    tramo = np.clip(np.searchsorted(s_ctrl, s, side="right") - 1, 0, len(t.puntos) - 1)
    sig = np.minimum(tramo + 1, len(t.puntos) - 1)
    zonas = np.where(t.zonas[tramo] == t.zonas[sig], t.zonas[tramo], -1)
    hitos = {k: int(round(s_ctrl[i] / h)) for k, i in c.c.hitos.items() if i <= t.fin}
    return zonas, hitos, g, c


def empalmar(Y, X, desde, hasta):
    """Los nodos X[desde+1 .. hasta] de la plantilla, corridos para salir de Y[-1] (que es la
    punta asentada de X[desde]): el corrimiento se reparte en los primeros EMPALME nodos."""
    tramo = X[desde + 1:hasta + 1].copy()
    delta = Y[-1] - X[desde]
    w = np.clip(1 - np.arange(1, len(tramo) + 1) / EMPALME, 0, 1)[:, None]
    return tramo + w * delta


def distancia_minima(Y, k=8):
    d = np.linalg.norm(Y[:, None] - Y[None], axis=2)
    i, j = np.triu_indices(len(Y), k + 1)
    return float(d[i, j].min())


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--tension", type=float, default=60.0)
    a.add_argument("--pasos", type=int, default=60)
    a.add_argument("--quieto", type=float, default=1e-3)
    a.add_argument("--kappa", type=float, default=0.3)
    a.add_argument("--simultaneo", action="store_true", help="cada paso de una vez, con una mano en cada hito hecho")
    a.add_argument("--hitos", nargs="+", default=["vuelta-3", "ahorcado-3", "cierre"])
    a.add_argument("--sin-roce", action="store_true")
    a.add_argument("--solo-punta", action="store_true", help="una sola mano, en la punta")
    a.add_argument("--sufijo", default="")
    args = a.parse_args()
    if args.simultaneo:
        return simultaneo(args)
    SALIDA.mkdir(parents=True, exist_ok=True)
    spec = cargar("amarre-cuadrado")
    modelo = construir(spec)
    final = modelo.pasos[-1]
    X, h = final.puntos, final.h
    zonas, hitos, g, c = zonas_y_hitos(spec, len(spec.pasos), X)
    cruz = g.solido
    a_ = spec.anfitrion
    rb, zb, zt = cruz.rb, cruz.zb, cruz.zt
    # Los palos para el motor: el eje de la cuerda no se acerca a menos de dmin (0,95) de la
    # malla, así que la malla va a radio − 0,5: la cuerda se apoya con su eje a radio + 0,45
    # (rb − 0,05, ya que rb = radio + 0,5), apretándose 0,05 contra la madera.
    # La plantilla apoya el eje de la cuerda a radio + 0,468 del eje del palo. La malla va a
    # radio − 0,56: esa cuerda queda a 1,03 de ella, arriba en la franja de la barrera (0,95 a
    # 1,05), y no la aprieta de entrada. Bajo carga puede hundirse hasta 0,08 en la madera.
    solidos = [cilindro((0, 0, zb), "y", cruz.radio - 0.56, 40.0), cilindro((0, 0, zt), "x", cruz.radio - 0.56, 40.0)]
    mat = Material()
    print(f"amarre cuadrado: {len(X)} nodos, h = {h:.3f}; hitos: {hitos}")

    Y = X[:hitos["inicio"] + 1].copy()
    z_nodos = list(zonas[:len(Y)])     # la zona de la plantilla donde se puso cada nodo
    punta = hitos["inicio"]            # el nodo de la plantilla donde está la punta asentada
    previo = None
    resultado = {}
    t_total = time.time()
    for hito in HITOS:
        K = hitos[hito]
        if previo is not None:
            # Al apretar, la cuerda desliza hacia la mano: la punta asentada ya no está donde
            # la plantilla puso ese nodo. El tramo nuevo sigue la plantilla desde donde quedó
            # la punta.
            nuevo = empalmar(Y, X, punta, K)
            z_nodos += list(zonas[punta + 1:K + 1])
            Y = np.vstack([Y, nuevo])
        dmin0 = distancia_minima(Y)
        direccion = Y[-1] - Y[-6]
        direccion /= np.linalg.norm(direccion)
        e = Escena(Y, mat, solidos, mesa=0.0, fijos=np.arange(3), fuerzas={len(Y) - 1: args.tension * direccion},
                   proximal=0.5)
        m = Motor(e)
        t0 = time.time()
        if dmin0 < e.dmin + 1e-3:
            print(f"  {hito}: el empalme deja dos tramos a {dmin0:.3f}; no se puede empezar", flush=True)
            return 1
        Y = m.resolver(pasos=args.pasos, kappa=args.kappa, quieto=args.quieto, mostrar=False)
        # Dónde quedó la punta en la plantilla: el nodo de la plantilla más cercano, cerca de K.
        cerca = np.arange(max(0, K - 40), min(len(X), K + 120))
        punta = int(cerca[np.argmin(np.linalg.norm(X[cerca] - Y[-1], axis=1))])
        # Comprobación como hoy, con los mapas de los palos.
        sec = c.secuencias[c.alias.get(hito, hito)]
        z = np.array(z_nodos)
        r = _resultado(0, Y, h, sec, None, buscar=lambda Z: en_la_cruz(Z, h, z, cruz))
        largo0 = float(np.sum(np.linalg.norm(np.diff(X[:K + 1], axis=0), axis=1)))
        print(f"  {hito}: {len(Y)} nodos, {len(m.registro)} pasos, {time.time() - t0:.0f} s; "
              f"la punta quedó en el nodo {punta} de la plantilla (era el {K}); "
              f"cuerda hasta aquí {largo0:.1f} → {r.medidas['largo']:.1f}; separación {r.medidas['separacion_min']:.3f}; "
              f"curvatura {r.medidas['curvatura_min']:.3f}; fallas: {r.fallas[:2] or 'ninguna'}", flush=True)
        np.save(SALIDA / f"amarre-{hito}.npy", Y)
        resultado[hito] = {"punta": punta, "nodos": len(Y), "pasos": len(m.registro), "segundos": time.time() - t0,
                           "fallas": r.fallas, "medidas": r.medidas}
        previo = hito
    (SALIDA / "amarre.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(f"listo en {time.time() - t_total:.0f} s")
    return 0


def simultaneo(args) -> int:
    """Cada paso de la ficha de una vez: la cuerda de la plantilla hasta su hito, con una mano
    en el final de cada hito ya hecho (el ballestrinque, cada vuelta y cada ahorcado) tirando
    T newtons hacia donde sigue la cuerda, como si se hubiera tirado de cada vuelta al darla.
    Empalmar la plantilla sobre una cuerda ya asentada no sirve: la vuelta nueva atraviesa a la
    anterior, que se corrió al apretarse (eso pide atar con la mano guiada, T14b)."""
    SALIDA.mkdir(parents=True, exist_ok=True)
    spec = cargar("amarre-cuadrado")
    modelo = construir(spec)
    X, h = modelo.pasos[-1].puntos, modelo.pasos[-1].h
    zonas, hitos, g, c = zonas_y_hitos(spec, len(spec.pasos), X)
    cruz = g.solido
    solidos = [cilindro((0, 0, cruz.zb), "y", cruz.radio - 0.56, 40.0), cilindro((0, 0, cruz.zt), "x", cruz.radio - 0.56, 40.0)]
    resultado = {}
    for hito in args.hitos:
        K = hitos[hito]
        Y = X[:K + 1].copy()
        hechos = [k for k in HITOS if hitos[k] <= K]
        if args.solo_punta:
            hechos = [hito]
        fuerzas = {}
        for k in hechos:
            i = hitos[k]
            d = X[min(i + 3, K)] - X[max(i - 3, 0)]
            fuerzas[i] = args.tension * d / np.linalg.norm(d)
        mat = Material(mu_cuerda=0.0, mu_madera=0.0) if args.sin_roce else Material()
        e = Escena(Y, mat, solidos, mesa=0.0, fijos=np.arange(3), fuerzas=fuerzas, proximal=0.5, roce=not args.sin_roce)
        m = Motor(e)
        t0 = time.time()
        Y = m.resolver(pasos=args.pasos, kappa=args.kappa, quieto=args.quieto, mostrar=False)
        sec = c.secuencias[c.alias.get(hito, hito)]
        z = zonas[:len(Y)]
        r = _resultado(0, Y, h, sec, None, buscar=lambda Z: en_la_cruz(Z, h, z, cruz))
        largo0 = float(np.sum(np.linalg.norm(np.diff(X[:K + 1], axis=0), axis=1)))
        print(f"  {hito}: {len(Y)} nodos, {len(hechos)} manos, {len(m.registro)} pasos, {time.time() - t0:.0f} s; "
              f"cuerda {largo0:.1f} → {r.medidas['largo']:.1f}; separación {r.medidas['separacion_min']:.3f}; "
              f"curvatura {r.medidas['curvatura_min']:.3f}; fallas: {r.fallas[:2] or 'ninguna'}", flush=True)
        np.save(SALIDA / f"amarre-{hito}{args.sufijo}.npy", Y)
        resultado[hito] = {"nodos": len(Y), "pasos": len(m.registro), "segundos": time.time() - t0,
                           "fallas": r.fallas, "medidas": r.medidas}
    (SALIDA / "amarre.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
