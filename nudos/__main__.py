"""Uso: python -m nudos <orden> [argumentos]. «python -m nudos -h» muestra las órdenes."""
from __future__ import annotations

import argparse
import os
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from . import BUILD, RAIZ
from .anfitrion import Tubo, solido
from .construir import construir, guardar
from .diagnostico import ampliar, diagnostico, leer_pasos
from .estado import nudos, probadores, tabla
from .exportar import SitioError, construir_sitio
from .ficha import FichaError, ficha, url_visor
from .hoja import ANCHO, desde_abajo, hoja, mapa, mapa_puno
from .plantillas.puno import PunoDeMono
from .imprimir import (CELDA_MM, PPP, ImpresionError, extra_prueba, imprimir, pagina_prueba,
                       px)
from .fisica import usar_motor
from .libre import LIMITES, LIMITES_MOTOR
from .mejoras import DESTINO as DESTINO_MEJORAS, construir_muestras, pagina_apretado, pagina_mejoras
from .revision import RevisionError, revision
from .spec import SpecError, cargar


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m nudos", description="Libro de nudos del Grupo 431")
    p.add_argument("--motor", action="store_true",
                   help="asienta los pasos y aprieta el terminado con el motor de física (T15d); "
                        "va antes de la orden, como «python -m nudos --motor construir <slug>»")
    ordenes = p.add_subparsers(dest="orden", required=True)
    c = ordenes.add_parser("construir", help="construye los pasos de un nudo y los comprueba")
    c.add_argument("slug")
    h = ordenes.add_parser("hoja", help="hoja de revisión con todos los pasos")
    h.add_argument("slug")
    h.add_argument("--vista", default="arriba",
                   help="«arriba» o la inclinación de la cámara en grados, por ejemplo 55")
    h.add_argument("--pasos", default="", help="solo esos pasos, como 2,4-5 (por omisión, todos)")
    d = ordenes.add_parser("diagnostico", help="construye solo los pasos elegidos y dice qué falla "
                                               "o está cerca del límite, y cerca de qué punto del YAML")
    d.add_argument("slug")
    d.add_argument("--pasos", default="", help="como 2,4-5 (por omisión, todos)")
    d.add_argument("--todo", action="store_true",
                   help="también el error común, el nudo por detrás y los dos apretados")
    a = ordenes.add_parser("ampliar", help="copia ampliada de una zona de una imagen de la fuente, "
                                           "con cuadrícula, en revision/_ampliadas/")
    a.add_argument("imagen", type=Path)
    a.add_argument("--zona", default="0,0,1,1",
                   help="x0,y0,x1,y1 en fracciones de la imagen, desde arriba a la izquierda")
    a.add_argument("--lado", type=int, default=800, help="píxeles del lado mayor de la copia")
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
    r = ordenes.add_parser("revision", help="hoja de revisión privada de un borrador, con la "
                                            "fuente junto a cada paso (en revision/<slug>/)")
    r.add_argument("slug")
    ordenes.add_parser("estado", help="estado de producción de los 36 nudos de la edición 1 "
                                     "y qué le falta a cada uno para el siguiente")
    rf = ordenes.add_parser("referencia", help="construye a la vez los nudos de modelado o más (o "
                                                "los nombrados) e imprime cada uno en <carpeta>/<slug>/, "
                                                "fuera de build/, para comparar después")
    rf.add_argument("carpeta", type=Path)
    rf.add_argument("slugs", nargs="*", help="solo estos nudos (por omisión, los de modelado o más)")
    rf.add_argument("--impresores", type=int, default=None,
                    help="navegadores a la vez (por omisión 8)")
    cm = ordenes.add_parser("comparar", help="compara dos carpetas de «referencia»: modelo.json "
                                             "byte a byte e imágenes en RGB")
    cm.add_argument("antes", type=Path)
    cm.add_argument("despues", type=Path)
    cm.add_argument("--reimprimir", action="store_true",
                    help="vuelve a imprimir solos, en <despues>, los nudos con el modelo igual y "
                         "alguna imagen distinta, y compara otra vez")
    ordenes.add_parser("prueba-motor", help="página de prueba del motor de física (T15d): los "
                                           "pilotos como salen hoy y con el motor, en color y "
                                           "en gris")
    ordenes.add_parser("prueba-blender", help="página de prueba de las fichas en Blender (T16 y "
                                             "T15g): los pilotos con el motor, dibujados con "
                                             "three.js y con Blender, en color y en gris")
    ordenes.add_parser("mejoras", help="páginas de prueba de las mejoras del render (hoy y con "
                                      "cada mejora) y del nudo terminado apretado, en color y "
                                      "en gris")
    args = p.parse_args(argv)
    if args.motor:
        os.environ["NUDOS_MOTOR"] = "1"
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
        if args.orden == "prueba-motor":
            return _prueba_motor()
        if args.orden == "prueba-blender":
            return _prueba_blender()
        if args.orden == "estado":
            return _estado()
        if args.orden == "revision":
            return _revision(args.slug)
        if args.orden == "diagnostico":
            return _diagnostico(args.slug, args.pasos, args.todo)
        if args.orden == "ampliar":
            return _ampliar(args.imagen, args.zona, args.lado)
        if args.orden == "referencia":
            return _referencia(args.carpeta, args.slugs, args.impresores)
        if args.orden == "comparar":
            from .referencia import comparar
            return comparar(args.antes.resolve(), args.despues.resolve(), args.reimprimir)
        return _hoja(args.slug, args.vista, args.pasos)
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


def _prueba_motor() -> int:
    from .prueba_motor import DESTINO, construir_pilotos, pagina
    try:
        modelos = construir_pilotos()
        destino = pagina(modelos, DESTINO)
    except ImpresionError as e:
        print(e, file=sys.stderr)
        return 1
    for slug, (_, motor) in modelos.items():
        print(f"{slug}: {len(motor.fallas)} fallas con el motor")
        for f in motor.fallas:
            print(f"  - {f}")
    print(f"Página de prueba del motor en {destino.relative_to(RAIZ)}")
    return 0


def _prueba_blender() -> int:
    from .prueba_blender import DESTINO, construir_pilotos, pagina
    try:
        modelos = construir_pilotos()
        for slug, m in modelos.items():
            if m.fallas:
                print(f"{slug}: {len(m.fallas)} fallas con el motor; no se dibuja", file=sys.stderr)
                return 1
        destino = pagina(modelos, DESTINO)
    except ImpresionError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Página de prueba de Blender en {destino.relative_to(RAIZ)}")
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


def _referencia(carpeta: Path, slugs: list[str], impresores: int | None) -> int:
    from .referencia import IMPRESORES, referencia
    try:
        fallas = referencia(carpeta.resolve(), slugs or None, impresores or IMPRESORES)
    except ImpresionError as e:
        print(e, file=sys.stderr)
        return 1
    for f in fallas:
        print(f, file=sys.stderr)
    return 1 if fallas else 0


def _sitio(salida: Path, con: list[str]) -> int:
    try:
        slugs = construir_sitio(salida.resolve(), con=con)
    except SitioError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Sitio con {len(slugs)} nudo(s) en {salida}: {', '.join(slugs)}")
    return 0


def _revision(slug: str) -> int:
    modelo = construir(cargar(slug))
    guardar(modelo)
    try:
        pagina = revision(modelo)
    except RevisionError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Hoja de revisión en {pagina}")
    if modelo.fallas:
        print(f"El nudo tiene {len(modelo.fallas)} falla(s); la hoja las muestra arriba.")
    return 0


def _estado() -> int:
    lista = nudos()
    print(tabla(lista))
    codigos = probadores()
    if codigos:
        print("\nProbadores del filtro 2, con los nudos que ya conocen")
        for codigo, (rol, slugs) in codigos.items():
            print(f"  {codigo} ({rol}): {', '.join(slugs)}")
    malos = [n.slug for n in lista if n.problemas]
    if malos:
        print(f"\nEstos nudos dicen un estado que no tienen (!!): {', '.join(malos)}", file=sys.stderr)
        return 1
    return 0


def _diagnostico(slug: str, pasos: str, todo: bool) -> int:
    spec = cargar(slug)
    try:
        lineas = diagnostico(spec, leer_pasos(pasos, len(spec.pasos)), todo)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    print("\n".join(lineas))
    return 1 if any(l.startswith("!!") for l in lineas) else 0


def _ampliar(imagen: Path, zona: str, lado: int) -> int:
    try:
        valores = tuple(float(v) for v in zona.split(","))
        if len(valores) != 4:
            raise ValueError
        salida = ampliar(imagen, RAIZ / "revision" / "_ampliadas", valores, lado)
    except (ValueError, OSError) as e:
        print(f"No se pudo ampliar: {e or 'la zona va como x0,y0,x1,y1'}", file=sys.stderr)
        return 2
    print(f"Copia ampliada en {salida}")
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
    lim = LIMITES_MOTOR if usar_motor() else LIMITES
    print(f"\nLímites: separación ≥ {lim['separacion_min']}, curvatura ≥ "
          f"{lim['curvatura_min']}, estiramiento ≤ {lim['estiramiento_max']:.0%}"
          + (" (con el motor)" if usar_motor() else ""))
    if modelo.fallas:
        print("\nFallas:")
        for f in modelo.fallas:
            print(f"  - {f}")
        print(f"\nEl modelo se guardó igual en {ruta} para revisarlo.")
        return 1
    print(f"Sin fallas. Modelo en {ruta}")
    return 0


def mapa_del_puno_de_mono(datos: dict, spec):
    """El puño de mono desenrollado de los pasos de `datos` (hoja.mapa_puno): el centro y el
    tamaño de cada paso los da la plantilla."""
    from .plantillas.puno import CAPA, Cuerda, FormaDedos
    c = Cuerda(spec.plantilla)
    hitos = {p.n: p.hasta for p in spec.pasos}
    centros, radios = [], []
    for p in datos["pasos"]:
        d = c.paso(hitos[p["n"]])
        forma = c._forma(c.alias.get(hitos[p["n"]], hitos[p["n"]]))
        centros.append(d["centro"])
        # En los dedos, el tercer juego pasa cerca del centro: se dibuja todo lo que no es el
        # firme ni lo que sigue.
        cerca = 1.0 if isinstance(forma, FormaDedos) else float(forma.S.min())
        radios.append((cerca, float(forma.S.max()) + CAPA))
    return mapa_puno(datos, centros, radios)


def _hoja(slug: str, vista: str, pasos: str = "") -> int:
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
    spec = cargar(slug)
    if pasos:
        # Solo esos pasos, en una imagen más chica, para mirar lo que se acaba de cambiar.
        try:
            elegidos = leer_pasos(pasos, len(datos["pasos"]))
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        datos = {**datos, "pasos": [p for p in datos["pasos"] if p["n"] in elegidos]}
        destino = origen.parent / f"hoja-{vista}-pasos-{pasos.replace(',', '_')}.png"
    imagen = hoja(datos, vista, None if spec.anfitrion is None else solido(spec.anfitrion).datos())
    abajo = None
    if spec.anfitrion is not None and spec.anfitrion.tipo in ("tubo", "cabo", "barril"):
        # Sobre el tubo, el cabo y el barril, la hoja lleva además su superficie desenrollada,
        # con cada cruce: en el barril, su costado.
        abajo = (mapa(datos, Tubo(spec.anfitrion), spec.plantilla.senos)
                 if spec.anfitrion.tipo == "tubo" else mapa(datos, solido(spec.anfitrion)))
    elif isinstance(spec.plantilla, PunoDeMono):
        # El puño de mono, desenrollado y mirado desde su centro, con cada cruce de las vueltas.
        abajo = mapa_del_puno_de_mono(datos, spec)
    if abajo is not None:
        junta = Image.new("RGB", (max(imagen.width, abajo.width), imagen.height + abajo.height), "white")
        junta.paste(imagen, (0, 0))
        junta.paste(abajo, (0, imagen.height))
        imagen = junta
    elif spec.anfitrion is None and spec.plantilla is not None:
        # El adujado: además, la aduja vista desde abajo.
        abajo = hoja(desde_abajo(datos), vista)
        ImageDraw.Draw(abajo).text((ANCHO - 150, 10), "Vista desde abajo", fill=(30, 30, 30))
        junta = Image.new("RGB", (imagen.width, imagen.height + abajo.height), "white")
        junta.paste(imagen, (0, 0))
        junta.paste(abajo, (0, imagen.height))
        imagen = junta
    imagen.save(destino)
    print(f"Hoja en {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
