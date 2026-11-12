"""Uso: python -m nudos <orden> [argumentos]. «python -m nudos -h» muestra las órdenes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from . import BUILD, RAIZ
from .anfitrion import Tubo
from .construir import construir, guardar
from .exportar import SitioError, construir_sitio
from .ficha import FichaError, ficha, url_visor
from .hoja import hoja, mapa
from .imprimir import (CELDA_MM, PPP, ImpresionError, extra_prueba, imprimir, pagina_prueba,
                       px)
from .libre import LIMITES
from .mejoras import DESTINO as DESTINO_MEJORAS, construir_muestras, pagina_apretado, pagina_mejoras
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
    s = ordenes.add_parser("sitio", help="construye el sitio con el visor de cada nudo")
    s.add_argument("--salida", type=Path, default=BUILD / "sitio",
                   help="carpeta donde queda el sitio (por omisión build/sitio)")
    s.add_argument("--con", action="append", default=[], metavar="SLUG",
                   help="agrega al sitio local un nudo que no está en publicados.txt, para "
                        "verlo antes de publicarlo; scripts/publicar.sh no lo usa")
    i = ordenes.add_parser("imprimir", help="imágenes de impresión a 300 ppp y página de prueba")
    i.add_argument("slug")
    f = ordenes.add_parser("ficha", help="ficha impresa en PDF: pliego de dos páginas con QR")
    f.add_argument("slug")
    ordenes.add_parser("mejoras", help="páginas de prueba de las mejoras del render (hoy y con "
                                      "cada mejora) y del nudo terminado apretado, en color y "
                                      "en gris")
    args = p.parse_args(argv)
    try:
        if args.orden == "construir":
            return _construir(args.slug)
        if args.orden == "sitio":
            return _sitio(args.salida, args.con)
        if args.orden == "imprimir":
            return _imprimir(args.slug)
        if args.orden == "ficha":
            return _ficha(args.slug)
        if args.orden == "mejoras":
            return _mejoras()
        return _hoja(args.slug, args.vista)
    except SpecError as e:
        print(f"Error en la especificación: {e}", file=sys.stderr)
        return 2


def _ficha(slug: str) -> int:
    modelo = construir(cargar(slug))
    carpeta = BUILD / slug
    try:
        imprimir(modelo, carpeta / "impresion")
        destino = ficha(modelo, carpeta)
    except (ImpresionError, FichaError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Ficha en {destino.relative_to(RAIZ)} · QR a {url_visor(slug)}")
    return 0


def _mejoras() -> int:
    try:
        modelos = construir_muestras()
        mejoras = pagina_mejoras(modelos, DESTINO_MEJORAS)
        apretado = pagina_apretado(modelos, DESTINO_MEJORAS)
    except ImpresionError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Página de prueba de las mejoras en {mejoras.relative_to(RAIZ)}")
    print(f"Página de prueba del nudo terminado apretado en {apretado.relative_to(RAIZ)}")
    return 0


def _imprimir(slug: str) -> int:
    modelo = construir(cargar(slug))
    carpeta = BUILD / slug / "impresion"
    try:
        rutas = imprimir(modelo, carpeta, extra=extra_prueba(modelo))
        prueba = pagina_prueba(modelo, carpeta)
    except ImpresionError as e:
        print(e, file=sys.stderr)
        return 1
    ancho, alto = px(CELDA_MM[0]), px(CELDA_MM[1])
    print(f"{len(rutas)} imágenes de {ancho} × {alto} px ({CELDA_MM[0]:g} × {CELDA_MM[1]:g} mm "
          f"a {PPP} ppp) en {carpeta.relative_to(RAIZ)}")
    if modelo.error is None:
        print("Esta especificación no declara el error común.")
    print(f"Página de prueba: {prueba.relative_to(RAIZ)}")
    return 0


def _sitio(salida: Path, con: list[str]) -> int:
    try:
        slugs = construir_sitio(salida.resolve(), con=con)
    except SitioError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Sitio con {len(slugs)} nudo(s) en {salida}: {', '.join(slugs)}")
    return 0


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
    imagen = hoja(datos, vista)
    spec = cargar(slug)
    if spec.anfitrion is not None and spec.anfitrion.tipo == "tubo":
        # Sobre el tubo, la hoja lleva además el tubo desenrollado, con cada cruce.
        abajo = mapa(datos, Tubo(spec.anfitrion), spec.plantilla.senos)
        junta = Image.new("RGB", (max(imagen.width, abajo.width), imagen.height + abajo.height), "white")
        junta.paste(imagen, (0, 0))
        junta.paste(abajo, (0, imagen.height))
        imagen = junta
    imagen.save(destino)
    print(f"Hoja en {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
