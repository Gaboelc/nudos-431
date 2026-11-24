"""Prueba de concepto de T15: que la cuerda de un amarre deje de verse tiesa.

Aprieta un paso de un nudo de plantilla sobre la cruz con nudos/apretar.py y los cruces de
la plantilla (nudos/plantillas/pasos.py), cada punto con la zona de donde estaba, por su
coordenada material, como apretar_paso() con el poste. Con --todo, todo el amarre cuenta
como «nudo» y se acorta, no solo lo que está cerca de un cruce sobre la mesa: en un amarre
casi toda la cuerda está lejos de los cruces y apretar() la deja sujeta, inflada.

Uso, desde la raíz del repositorio:
    .venv/Scripts/python poc/cuerda/apretar.py --paso 7 --rondas 60 [--todo] [--tension 0.25]
Escribe el trabajo de la imagen para Blender en build/poc-cuerda/trabajos/.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time

import numpy as np

import nudos.apretar as ap
from nudos import RAIZ
from nudos.construir import construir
from nudos.imprimir import CELDA_MM, imagenes, px, trabajo
from nudos.libre import catmull_rom, remuestrear
from nudos.plantillas.pasos import buscar as en_la_cruz, geometria
from nudos.spec import cargar

SALIDA = RAIZ / "build" / "poc-cuerda"


def zonas_del_paso(spec, n, puntos):
    """Las zonas de cada punto del paso n, como en construir_paso()."""
    g = geometria(spec)
    c = g.cuerda(None)
    hito = spec.pasos[n - 1].hasta
    previo = spec.pasos[n - 2].hasta if n > 1 else None
    t = c.trazo(hito, previo)
    D, ctrl = catmull_rom(t.puntos)
    X, h0, s_ctrl = remuestrear(D, ctrl)
    if len(X) != len(puntos):
        raise SystemExit(f"El paso {n} construido no es el de la plantilla.")
    s = np.arange(len(X)) * h0
    tramo = np.clip(np.searchsorted(s_ctrl, s, side="right") - 1, 0, len(t.puntos) - 1)
    siguiente = np.minimum(tramo + 1, len(t.puntos) - 1)
    return np.where(t.zonas[tramo] == t.zonas[siguiente], t.zonas[tramo], -1), h0, g.solido


FUERTE = 3   # una parte más: el nudo que se acorta con más tensión (los ahorcados)
EXTRA_INICIO = float(__import__("os").environ.get("EXTRA_INICIO", "15"))   # lo quieto después del ballestrinque de inicio


def largos_de_hitos(spec, n):
    """Dónde termina cada hito de la plantilla, en diámetros a lo largo de la cuerda del paso n."""
    g = geometria(spec)
    c = g.cuerda(None)
    t = c.trazo(spec.pasos[n - 1].hasta, spec.pasos[n - 2].hasta if n > 1 else None)
    _, ctrl = catmull_rom(t.puntos)
    _, _, s_ctrl = remuestrear(*catmull_rom(t.puntos))
    return {nombre: float(s_ctrl[i]) for nombre, i in c.c.hitos.items() if i <= t.fin}


def ronda_con_cincha(t_suave, t_fuerte):
    """La ronda de nudos/apretar.py (_ronda), con dos tensiones: los ahorcados (FUERTE) se
    acortan más que las vueltas, así que al cerrarse empujan las vueltas hacia el centro."""
    def _ronda(X, h, rep, parte, anfitrion, gravedad):
        N = len(X)
        nudo, sujeto = (parte == ap.NUDO) | (parte == FUERTE), parte == ap.SUJETO
        libre = np.ones(N, bool)
        for i in rep.inicios:
            libre[i:i + ap.FIJOS] = False
        salto, radio, seguido, interior = rep.salto(h), rep.radio, rep.seguido, rep.interior
        tension = np.where(parte == FUERTE, t_fuerte, t_suave)[1:-1, None]
        tensa = (nudo & interior & libre)[1:-1, None]
        nudo_seg = nudo[:-1] | nudo[1:]
        agarre = sujeto & libre
        ancla = X[agarre].copy()
        for it in range(ap.ITERACIONES_ACORTAR + ap.ITERACIONES_SOLTAR):
            acorta = it < ap.ITERACIONES_ACORTAR
            if acorta:
                X[1:-1] += tension * (X[:-2] + X[2:] - 2 * X[1:-1]) * tensa
            X[agarre] = ancla
            for _ in range(ap.CORRECCIONES):
                ap._limitar_curva(X, h, libre, rmin=1.1, ganancia=0.35, grosor=rep.grosor,
                                  interior=interior)
                ap._colisiones(X, salto, libre, rep, radio * ap.HOLGURA)
                X[:, 2] = np.maximum(X[:, 2], radio)
                if anfitrion is not None:
                    anfitrion.empujar(X, libre)
                X[agarre] = ancla
                ap._largos(X, h, libre, nudo_seg, seguido, ap.PASADAS_LARGO, acorta)
    return _ronda


def apretar_con_cincha(spec, r, rondas, t_suave, t_fuerte, registro):
    """Los ballestrinques de inicio y de cierre quedan quietos; las vueltas, con tensión
    suave, y los ahorcados, con tensión fuerte."""
    zonas, h0, cruz = zonas_del_paso(spec, r.n, r.puntos)
    hitos = largos_de_hitos(spec, r.n)
    print("hitos:", {k: round(v, 1) for k, v in hitos.items()})

    def buscar(Y, hY, u):
        return en_la_cruz(Y, hY, zonas[np.clip(np.round(u / h0).astype(int), 0, len(zonas) - 1)], cruz)

    def partes(X, h, rep, cruces):
        p = partes_originales(X, h, rep, cruces)
        s = np.arange(len(X)) * h
        out = np.where(p == ap.COLA, ap.COLA, ap.NUDO)
        out[s <= hitos["inicio"] + EXTRA_INICIO] = ap.SUJETO
        if "vueltas" in hitos or any(k.startswith("ahorcado") for k in hitos):
            fin_vueltas = max(v for k, v in hitos.items() if k.startswith("vuelta"))
            ahorcados = [v for k, v in hitos.items() if k.startswith("ahorcado")]
            if ahorcados:
                out[(s > fin_vueltas) & (s <= max(ahorcados))] = FUERTE
                out[(s > max(ahorcados)) & (out != ap.COLA)] = ap.SUJETO
        return out

    partes_originales, ronda_original = ap._partes, ap._ronda
    ap._partes, ap._ronda = partes, ronda_con_cincha(t_suave, t_fuerte)
    try:
        p = partes(r.puntos, r.h, None, None) if False else None
        return ap.apretar(r, r.secuencia, rondas=rondas, anfitrion=cruz,
                          gravedad=lambda Y: np.zeros(len(Y), bool), buscar=buscar, registro=registro)
    finally:
        ap._partes, ap._ronda = partes_originales, ronda_original


def apretar_paso(spec, r, rondas, todo, registro):
    zonas, h0, cruz = zonas_del_paso(spec, r.n, r.puntos)

    def buscar(Y, hY, u):
        return en_la_cruz(Y, hY, zonas[np.clip(np.round(u / h0).astype(int), 0, len(zonas) - 1)], cruz)

    partes_originales = ap._partes
    if todo:
        def partes(X, h, rep, cruces):
            p = partes_originales(X, h, rep, cruces)
            return np.where(p == ap.COLA, ap.COLA, ap.NUDO)
        ap._partes = partes
    try:
        p = ap._partes(r.puntos, r.h, ap.Reparto.una(len(r.puntos)), buscar(r.puntos, r.h, np.arange(len(r.puntos)) * r.h)[0])
        print("partes: nudo {}, cola {}, sujeto {} puntos".format(*(int((p == k).sum()) for k in (ap.NUDO, ap.COLA, ap.SUJETO))))
        return ap.apretar(r, r.secuencia, rondas=rondas, anfitrion=cruz,
                          gravedad=lambda Y: np.zeros(len(Y), bool), buscar=buscar, registro=registro)
    finally:
        ap._partes = partes_originales


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--slug", default="amarre-cuadrado")
    a.add_argument("--paso", type=int, default=7)
    a.add_argument("--rondas", type=int, default=60)
    a.add_argument("--todo", action="store_true")
    a.add_argument("--tension", type=float, default=ap.TENSION)
    a.add_argument("--nombre", default=None)
    a.add_argument("--cincha", action="store_true", help="ballestrinques quietos, vueltas suaves y ahorcados fuertes")
    a.add_argument("--suave", type=float, default=0.1)
    a.add_argument("--fuerte", type=float, default=0.6)
    args = a.parse_args()
    ap.TENSION = args.tension
    # Qué falla en cada ronda que no cumple: apretar() solo dice «cumple» o no.
    original = ap._resultado
    vistas: set[str] = set()

    def con_fallas(*a, **k):
        r = original(*a, **k)
        for f in r.fallas[:2]:
            clave = f.split(":")[0][:60] + f[:80]
            if clave not in vistas:
                vistas.add(clave)
                print("  falla:", f[:160])
        return r
    ap._resultado = con_fallas
    spec = cargar(args.slug)
    modelo = construir(spec)
    r = modelo.pasos[args.paso - 1]
    registro: list = []
    inicio = time.time()
    if args.cincha:
        apretado = apretar_con_cincha(spec, r, args.rondas, args.suave, args.fuerte, registro)
    else:
        apretado = apretar_paso(spec, r, args.rondas, args.todo, registro)
    for fila in registro[:: max(1, len(registro) // 15)] + registro[-1:]:
        print("ronda {:4d}  largo {:7.1f}  separación {:.3f}  curvatura {:.3f}  estiramiento {:.4f}  {}".format(*fila))
    print(f"{time.time() - inicio:.0f} s")
    if apretado is r:
        print("Ninguna ronda cumple la secuencia y los límites.")
        return 1
    print(f"Largo: {r.medidas['largo']:.1f} → {apretado.medidas['largo']:.1f} diámetros "
          f"({1 - apretado.medidas['largo'] / r.medidas['largo']:.0%} menos)")
    apretado = dataclasses.replace(apretado, resaltado=r.resaltado) if False else apretado
    pasos = list(modelo.pasos)
    pasos[args.paso - 1] = apretado
    nuevo = dataclasses.replace(modelo, pasos=pasos)
    img = next(i for i in imagenes(nuevo) if i.nombre == f"paso-{args.paso}")
    nombre = args.nombre or f"paso-{args.paso}-{'todo' if args.todo else 'cerca'}-{args.rondas}"
    t = trabajo(img) | {"ancho": px(CELDA_MM[0]), "alto": px(CELDA_MM[1]), "slug": args.slug,
                        "nombre": nombre}
    (SALIDA / "trabajos").mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / "trabajos" / f"{args.slug}--{nombre}.json"
    ruta.write_text(json.dumps(t), encoding="utf-8")
    np.save(SALIDA / "trabajos" / f"{args.slug}--{nombre}.npy", apretado.puntos)
    print(ruta.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
