"""Uso: python -m nudos <orden> <slug>. «python -m nudos -h» muestra las órdenes."""
from __future__ import annotations

import argparse
import json
import sys

from . import BUILD, RAIZ
from .construir import construir, guardar
from .hoja import hoja
from .libre import LIMITES
from .spec import SpecError, cargar


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m nudos", description="Libro de nudos del Grupo 431")
    ordenes = p.add_subparsers(dest="orden", required=True)
    c = ordenes.add_parser("construir", help="construye los pasos de un nudo y los comprueba")
    c.add_argument("slug")
    h = ordenes.add_parser("hoja", help="hoja de revisión con todos los pasos")
    h.add_argument("slug")
    h.add_argument("--vista", default="arriba",
                   help="«arriba» o la inclinación de la cámara en grados, por ejemplo 55")
    args = p.parse_args(argv)
    try:
        if args.orden == "construir":
            return _construir(args.slug)
        return _hoja(args.slug, args.vista)
    except SpecError as e:
        print(f"Error en la especificación: {e}", file=sys.stderr)
        return 2


def _construir(slug: str) -> int:
    spec = cargar(slug)
    print(f"{spec.nombre} ({spec.slug}): {len(spec.pasos)} pasos\n")
    modelo = construir(spec)
    ruta = guardar(modelo).relative_to(RAIZ)
    print(f"{'Paso':>4}  {'Cruces':>6}  {'Separación':>10}  {'Curvatura':>9}  "
          f"{'Estiramiento':>12}  Secuencia")
    for r in modelo.pasos:
        m = r.medidas
        estado = "ok" if r.secuencia == r.esperada else "distinta"
        print(f"{r.n:>4}  {len(r.esperada) // 2:>6}  {m['separacion_min']:>10.2f}  "
              f"{m['curvatura_min']:>9.2f}  {m['estiramiento_max']:>12.1%}  {estado}")
    print(f"\nLímites: separación ≥ {LIMITES['separacion_min']}, curvatura ≥ "
          f"{LIMITES['curvatura_min']}, estiramiento ≤ {LIMITES['estiramiento_max']:.0%}")
    if modelo.fallas:
        print("\nFallas:")
        for f in modelo.fallas:
            print(f"  - {f}")
        print(f"\nEl modelo se guardó igual en {ruta} para revisarlo.")
        return 1
    print(f"Sin fallas. Modelo en {ruta}")
    return 0


def _hoja(slug: str, vista: str) -> int:
    origen = BUILD / slug / "modelo.json"
    if not origen.exists():
        print(f"No hay modelo de {slug}. Corre primero: python -m nudos construir {slug}",
              file=sys.stderr)
        return 2
    if vista != "arriba":
        try:
            angulo = float(vista)
        except ValueError:
            angulo = -1.0
        if not 0 < angulo < 90:
            print("La vista es «arriba» o un ángulo entre 0 y 90 grados.", file=sys.stderr)
            return 2
    with open(origen, encoding="utf-8") as f:
        datos = json.load(f)
    destino = origen.parent / f"hoja-{vista}.png"
    hoja(datos, vista).save(destino)
    print(f"Hoja en {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
