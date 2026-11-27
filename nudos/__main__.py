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
    pa = ordenes.add_parser("prueba-atar", help="prueba de la animación entre pasos (T17): el "
                                                "as de guía y el amarre atados con el motor, "
                                                "en video")
    pa.add_argument("slugs", nargs="*", help="los nudos (por omisión, los dos pilotos)")
    pa.add_argument("--sin-video", action="store_true", help="solo los cuadros, sin Blender")
    pa.add_argument("--solo-video", action="store_true",
                    help="dibuja los videos desde los cuadros ya guardados en build/atar")
    vd = ordenes.add_parser("video", help="los videos de cada nudo (T18): el horizontal en 4K, "
                                          "su copia del visor y el vertical, con el motor")
    vd.add_argument("slugs", nargs="*", help="los nudos, en cola, uno tras otro")
    vd.add_argument("--todos", action="store_true", help="todos los nudos de modelado o más")
    vd.add_argument("--previa", action="store_true",
                    help="el nudo entero en 960 × 540, 30 fps y 16 muestras, para revisar")
    vd.add_argument("--solo", choices=("horizontal", "vertical"), help="solo ese formato")
    vd.add_argument("--prueba", action="store_true",
                    help="la prueba del aspecto (T20b): 10 s del paso 4 en 4K, sin audio, en "
                         "<slug>-prueba-4k.mp4")
    asp = ordenes.add_parser("prueba-aspecto", help="el cuadro final de T20a: tres tomas en 4K en cada "
                                                    "aspecto, con Cycles y con EEVEE, con su costo, en "
                                                    "build/aspecto/prueba.pdf")
    asp.add_argument("--aspectos", default="", help="las claves de los aspectos, como 0,1,3a (por "
                                                     "omisión, todos)")
    asp.add_argument("--motores", default="cycles,eevee",
                     help="cycles, eevee o los dos; cycles:16 es Cycles con 16 muestras")
    asp.add_argument("--tomas-de-nuevo", action="store_true",
                     help="vuelve a sacar las tomas del atado de los pilotos (con el motor)")
    asp.add_argument("--tomas", default="", help="solo esas tomas, como paso4,amarre (por omisión, las tres)")
    asp.add_argument("--solo-pdf", action="store_true",
                     help="arma el PDF con las imágenes y los tiempos ya dibujados")
    ca = ordenes.add_parser("calidad", help="mide la calidad del movimiento en los cuadros del "
                                            "video (T21a), con el motor y sin dibujar")
    ca.add_argument("slugs", nargs="*", help="los nudos (por omisión, los dos pilotos de T17)")
    pv = ordenes.add_parser("prueba-voz", help="la prueba de voz a ciegas de T23: la apertura y "
                                               "dos pasos del as de guía con cada voz, en revision/voz/")
    pv.add_argument("--proveedor", choices=("qwen", "elevenlabs", "falso"),
                    help="otro proveedor para las voces de prueba (por omisión, Qwen3-TTS)")
    pm = ordenes.add_parser("prueba-musica", help="las demos de la música de T23: el instrumento del "
                                                  "motivo y las cinco canciones, en revision/musica/")
    pm.add_argument("--cancion", help="solo esa canción (fogata, sendero, rocio, lumbre o amanecer)")
    pz = ordenes.add_parser("prueba-mezcla", help="la prueba de la mezcla de T23c: la previa de cada "
                                                  "piloto con la pista nueva, en revision/sonido/")
    pz.add_argument("slugs", nargs="*", help="los nudos (por omisión, los dos pilotos de T17)")
    pz.add_argument("--sin-voz", action="store_true", help="sin la voz de los pasos 2 y 4")
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
        if args.orden == "prueba-atar":
            return _prueba_atar(args.slugs, not args.sin_video, args.solo_video)
        if args.orden == "video":
            if args.prueba:
                return _video_prueba(args.slugs)
            return _video(args.slugs, args.todos, args.previa, args.solo)
        if args.orden == "calidad":
            return _calidad(args.slugs)
        if args.orden == "prueba-voz":
            from .prueba_sonido import prueba_voz
            sys.stdout.reconfigure(line_buffering=True)      # el avance de los modelos, al momento
            print(f"Prueba de voz en {prueba_voz(args.proveedor)}")
            return 0
        if args.orden == "prueba-musica":
            from .prueba_sonido import prueba_musica
            sys.stdout.reconfigure(line_buffering=True)
            print(f"Prueba de música en {prueba_musica(args.cancion)}")
            return 0
        if args.orden == "prueba-mezcla":
            from .prueba_sonido import PILOTOS_MEZCLA, prueba_mezcla
            sys.stdout.reconfigure(line_buffering=True)
            print(f"Prueba de la mezcla en {prueba_mezcla(args.slugs or PILOTOS_MEZCLA, not args.sin_voz)}")
            return 0
        if args.orden == "prueba-aspecto":
            return _prueba_aspecto(args.aspectos, args.motores, args.tomas_de_nuevo, args.solo_pdf, args.tomas)
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


def _video_prueba(slugs) -> int:
    """La prueba del aspecto de T20b: 10 s del paso 4 de cada nudo en 4K."""
    from .blender import BlenderError
    from .video import VideoError, construir, prueba
    if not slugs:
        print("Di qué nudos.", file=sys.stderr)
        return 2
    try:
        modelos = construir(list(slugs))
        for slug in slugs:
            salida = prueba(modelos[slug], aviso=lambda t: print(t, flush=True))
            print(f"Prueba del aspecto en {salida}")
    except (VideoError, BlenderError, ImpresionError) as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def _video(slugs, todos: bool, previa: bool, solo) -> int:
    from .video import carpeta_videos, cola
    from .video import todos as todos_los
    if todos:
        slugs = todos_los()
    if not slugs:
        print("Di qué nudos o usa --todos.", file=sys.stderr)
        return 2
    malos = cola(list(slugs), previa=previa, solo=solo)
    print(f"Videos en {carpeta_videos()}; {malos} nudos con fallas (ver cola.txt)")
    return 1 if malos else 0


def _prueba_aspecto(aspectos: str, motores: str, de_nuevo: bool, solo_pdf: bool, solo_tomas: str = "") -> int:
    """El cuadro final de T20a, en build/aspecto/prueba.pdf."""
    from .aspecto import ASPECTOS, DESTINO, Resultado, pagina, prueba, tomas
    from .blender import BlenderError
    from .recursos import RecursoError
    nombres = {"cycles": "CYCLES", "eevee": "BLENDER_EEVEE"}
    lista = []
    for m in (x.strip().lower() for x in motores.split(",") if x.strip()):
        motor, _, muestras = m.partition(":")
        if motor not in nombres or (muestras and not muestras.isdigit()):
            print(f"No conozco el motor {m}: usa cycles, eevee o, con otras muestras, cycles:16 o eevee:32.",
                  file=sys.stderr)
            return 2
        lista.append(nombres[motor] + (f":{muestras}" if muestras else ""))
    claves = [c.strip() for c in aspectos.split(",") if c.strip()]
    elegidos = [a for a in ASPECTOS if not claves or a.clave in claves]
    if not elegidos:
        print(f"No hay aspectos {aspectos}: son {', '.join(a.clave for a in ASPECTOS)}.", file=sys.stderr)
        return 2
    try:
        if de_nuevo:
            tomas(rehacer=True)
        if solo_pdf:
            datos = json.loads((DESTINO / "tiempos.json").read_text(encoding="utf-8"))
            destino = pagina(tomas(), [Resultado(**d) for d in datos], DESTINO)
        else:
            destino = prueba(elegidos, lista, DESTINO,
                             solo=[t.strip() for t in solo_tomas.split(",") if t.strip()] or None)
    except (BlenderError, ImpresionError, RecursoError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Página de prueba del aspecto en {destino.relative_to(RAIZ)}")
    return 0


def _calidad(slugs) -> int:
    """La calidad del movimiento de los videos (T21a), en build/calidad/<slug>.json."""
    from .prueba_atar import PILOTOS
    from .video import calidad, construir
    os.environ["NUDOS_MOTOR"] = "1"
    slugs = tuple(slugs) or PILOTOS
    modelos = construir(list(slugs))
    destino = BUILD / "calidad"
    destino.mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        if modelos[slug].fallas:
            print(f"{slug}: el nudo tiene fallas con el motor; no se mide", file=sys.stderr)
            return 1
        m = calidad(modelos[slug])
        (destino / f"{slug}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False),
                                             encoding="utf-8")
        r, c = m["resaltado"], m["camara"]
        print(f"{slug}: {m['segundos']} s, {m['cuadros']} cuadros\n"
              f"  nodos {m['nodos']['min']}–{m['nodos']['max']}, {m['nodos']['cambios']} cambios; "
              f"largo {m['largo']['min']}–{m['largo']['max']} d ({m['largo']['variacion']:.0%})\n"
              f"  aceleración p99 {m['aceleracion']['p99']} y máx {m['aceleracion']['max']} d/s²; "
              f"{m['brincos']} brincos; {m['punta']['paradas_en_seco']} paradas en seco de la punta\n"
              f"  resaltado vacío en {r['vacio']} y corto en {r['corto']} de {r['cuadros']} cuadros\n"
              f"  cámara: {c['paradas']} paradas, quieta el {c['quietos']:.0%} del tiempo, "
              f"aceleración máx {c['aceleracion']['max']} d/s²")
    print(f"Medidas en {destino.relative_to(RAIZ)}")
    return 0


def _prueba_atar(slugs, video: bool, solo_video: bool = False) -> int:
    from .prueba_atar import DESTINO, PILOTOS, prueba, videos
    if solo_video:
        try:
            videos(tuple(slugs) or PILOTOS)
        except ImpresionError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"Videos de la prueba de atar en {DESTINO.relative_to(RAIZ)}")
        return 0
    try:
        informe = prueba(tuple(slugs) or PILOTOS, video=video, previa=video)
    except ImpresionError as e:
        print(e, file=sys.stderr)
        return 1
    fallas = sum(len(v["fallas"]) for k, v in informe.items() if isinstance(v, dict))
    print(f"Prueba de atar en {DESTINO.relative_to(RAIZ)}, con {fallas} fallas")
    return 1 if fallas else 0


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
