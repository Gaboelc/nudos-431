"""Referencia y comparación: comprobar que un cambio de código no mueve los nudos ya hechos.

`python -m nudos referencia <carpeta> [slug ...]` construye a la vez los nudos de `modelado` o
más (o los que se nombren) y deja en <carpeta>/<slug>/ su `modelo.json` y su `impresion/`, como
`construir` e `imprimir`. No escribe en build/: Google Drive a veces no deja borrar las imágenes
de build/<slug>/impresion, y así la referencia no se mezcla con lo que se está probando. Conviene
que la carpeta esté fuera de A:.

`python -m nudos comparar <antes> <después>` compara dos carpetas armadas así: cada `modelo.json`
byte a byte (no los objetos de Python: pickle memoriza los objetos compartidos y da bytes
distintos con valores iguales) y cada imagen en RGB (en RGBA, getbbox() de Pillow solo mira el
alfa). Con `--reimprimir`, los nudos cuyo modelo es igual pero alguna imagen no, se vuelven a
imprimir solos, de a uno, en <después>, y se comparan otra vez: con la computadora cargada, el
navegador a veces dibuja unos píxeles con 1 o 2 niveles de diferencia. Si aun así difiere, la
variación puede ser de la referencia: se imprime ese nudo desde el commit de la referencia, en un
worktree aparte, y se compara con las dos.

Edge se actualiza solo, y con otra versión todas las imágenes cambian un poco aunque el código
no cambie: las dos carpetas se imprimen con el mismo navegador, el mismo día. `referencia` anota
la versión en <carpeta>/navegador.txt, y `comparar` avisa si no coinciden.

Con el motor de física (`python -m nudos --motor referencia …`, T15f), los nudos se construyen
con él, y `referencia` lo anota en <carpeta>/motor.txt. `comparar` avisa si una carpeta se armó
con el motor y la otra no, y `--reimprimir` construye cada nudo como se armó <después>. Así se
compara el motor contra sí mismo (antes y después de un cambio del motor) o contra los nudos de
hoy (lo que hace T19).

El procedimiento entero, en el worktree de una rama:
    python -m nudos referencia <fuera>/antes        (desde un worktree de main, antes del código)
    python -m nudos referencia <fuera>/despues      (con el código nuevo)
    python -m nudos comparar <fuera>/antes <fuera>/despues --reimprimir
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import RAIZ
from .construir import construir, datos_json, guardar
from .imprimir import chrome, extra_prueba, imprimir, pagina_prueba
from .procesos import _Contexto, construir_varios, cuantos, en_paralelo
from .spec import ESTADOS, cargar

IMPRESORES = 8   # navegadores a la vez; con más, la memoria y la variación del navegador crecen
# La versión del navegador con que se imprimió. Edge se actualiza solo, y una versión nueva
# dibuja cientos de píxeles con 2 a 4 niveles de diferencia (el 18 nov de 2026, en todas las
# imágenes): las dos carpetas que se comparan se imprimen con el mismo navegador.
NAVEGADOR = "navegador.txt"
# Si la carpeta se armó con el motor de física (T15f): el archivo existe solo entonces.
MOTOR = "motor.txt"


def nudos_hechos(raiz: Path = RAIZ) -> list[str]:
    """Los nudos de `modelado` o más: los que un cambio de código no debe mover."""
    minimo = ESTADOS.index("modelado")
    return [p.stem for p in sorted((raiz / "specs").glob("*.yaml"))
            if ESTADOS.index(cargar(p.stem).estado) >= minimo]


def borrar(carpeta: Path, intentos: int = 20) -> None:
    """Borra la carpeta aunque tenga archivos de solo lectura, y reintenta si Google Drive tiene
    algo abierto."""
    def quitar_solo_lectura(fn, ruta, _exc):
        os.chmod(ruta, stat.S_IWRITE)
        fn(ruta)

    for i in range(intentos):
        if not carpeta.exists():
            return
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(carpeta, onexc=quitar_solo_lectura)
            else:
                shutil.rmtree(carpeta, onerror=quitar_solo_lectura)
            return
        except PermissionError:
            if i == intentos - 1:
                raise
            time.sleep(1)


def _imprimir_en(modelo, carpeta: Path) -> str:
    """Las imágenes de `imprimir` y su página de prueba, en una carpeta nueva."""
    borrar(carpeta)
    imprimir(modelo, carpeta, extra=extra_prueba(modelo))
    pagina_prueba(modelo, carpeta)
    return modelo.spec.slug


def referencia(destino: Path, slugs: list[str] | None = None, impresores: int = IMPRESORES,
               avisar=print) -> list[str]:
    """Construye los nudos a la vez y deja en destino/<slug>/ su modelo.json y su impresion/.
    Devuelve las fallas: un nudo con fallas guarda su modelo, pero no se imprime."""
    from .fisica import usar_motor
    slugs = nudos_hechos() if slugs is None else list(slugs)
    destino.mkdir(parents=True, exist_ok=True)
    if usar_motor():
        (destino / MOTOR).write_text("con el motor de física (--motor)\n", encoding="utf-8")
    elif (destino / MOTOR).exists():
        (destino / MOTOR).unlink()
    t = time.perf_counter()
    modelos = construir_varios([cargar(s) for s in slugs])
    avisar(f"Construidos {len(modelos)} nudos en {time.perf_counter() - t:.0f} s.")
    fallas, para_imprimir = [], []
    for m in modelos:
        guardar(m, destino / m.spec.slug / "modelo.json")
        if m.fallas:
            fallas.append(f"{m.spec.slug}: {len(m.fallas)} fallas; no se imprime ({m.fallas[0]})")
        else:
            para_imprimir.append(m)
    t = time.perf_counter()
    n = min(impresores, cuantos(), len(para_imprimir))
    if n > 1 and en_paralelo():
        with ProcessPoolExecutor(n, mp_context=_Contexto()) as ex:
            futuros = [ex.submit(_imprimir_en, m, destino / m.spec.slug / "impresion")
                       for m in para_imprimir]
            for f in futuros:
                f.result()
    else:
        for m in para_imprimir:
            _imprimir_en(m, destino / m.spec.slug / "impresion")
    avisar(f"Impresos {len(para_imprimir)} nudos en {time.perf_counter() - t:.0f} s, en {destino}.")
    if para_imprimir:
        with chrome() as navegador:
            (destino / NAVEGADOR).write_text(navegador.version + "\n", encoding="utf-8")
    return fallas


@dataclass
class Diferencia:
    slug: str
    modelo_igual: bool = True
    imagenes: list[str] = field(default_factory=list)   # una línea por imagen distinta
    falta: bool = False


def _rgb(ruta: Path) -> np.ndarray:
    with Image.open(ruta) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16)


def comparar_nudo(antes: Path, despues: Path, slug: str) -> Diferencia | None:
    """Lo que cambió de un nudo entre dos carpetas de referencia, o None si nada."""
    a, b = antes / slug, despues / slug
    if not (b / "modelo.json").exists():
        return Diferencia(slug, modelo_igual=False, falta=True)
    d = Diferencia(slug, modelo_igual=(a / "modelo.json").read_bytes() == (b / "modelo.json").read_bytes())
    ia, ib = a / "impresion", b / "impresion"
    nombres_a = {p.relative_to(ia).as_posix() for p in ia.rglob("*.png")} if ia.exists() else set()
    nombres_b = {p.relative_to(ib).as_posix() for p in ib.rglob("*.png")} if ib.exists() else set()
    for nombre in sorted(nombres_a | nombres_b):
        if nombre not in nombres_b:
            d.imagenes.append(f"{nombre}: falta")
        elif nombre not in nombres_a:
            d.imagenes.append(f"{nombre}: sobra (no está en la referencia)")
        else:
            x, y = _rgb(ia / nombre), _rgb(ib / nombre)
            if x.shape != y.shape:
                d.imagenes.append(f"{nombre}: otro tamaño, {x.shape[1]}×{x.shape[0]} y {y.shape[1]}×{y.shape[0]}")
            else:
                dif = np.abs(x - y).max(axis=2)
                pixeles = int((dif > 0).sum())
                if pixeles:
                    d.imagenes.append(f"{nombre}: {pixeles} píxeles, hasta {int(dif.max())} niveles")
    return None if d.modelo_igual and not d.imagenes else d


def comparar(antes: Path, despues: Path, reimprimir: bool = False, avisar=print) -> int:
    """Compara dos carpetas de `referencia`. Devuelve 0 si todo es igual y 1 si no."""
    slugs = sorted(p.parent.name for p in antes.glob("*/modelo.json"))
    if not slugs:
        avisar(f"{antes} no tiene ningún <slug>/modelo.json: ¿es una carpeta de «referencia»?")
        return 1
    nuevos = sorted(p.parent.name for p in despues.glob("*/modelo.json") if p.parent.name not in slugs)
    difs = [d for d in (comparar_nudo(antes, despues, s) for s in slugs) if d is not None]
    if reimprimir:
        difs = [_reimprimir(antes, despues, d, avisar) if d.modelo_igual and d.imagenes else d
                for d in difs]
        difs = [d for d in difs if d is not None]
    for d in difs:
        if d.falta:
            avisar(f"{d.slug}: falta en {despues}")
            continue
        avisar(f"{d.slug}: modelo.json {'igual' if d.modelo_igual else 'DISTINTO'}"
               + "".join(f"\n  {linea}" for linea in d.imagenes))
    if nuevos:
        avisar(f"Sin referencia (nuevos): {', '.join(nuevos)}")
    va, vd = (_version(c) for c in (antes, despues))
    if va != vd:
        avisar(f"Ojo: las imágenes se imprimieron con navegadores distintos ({va or 'sin anotar'} y "
               f"{vd or 'sin anotar'}). Si los modelos son iguales y todas las imágenes difieren "
               "un poco, es el navegador: arma de nuevo la referencia de antes, hoy.")
    ma, md = (_con_motor(c) for c in (antes, despues))
    if ma != md:
        avisar(f"Ojo: {antes if ma else despues} se armó con el motor de física y "
               f"{despues if ma else antes} no: los modelos no pueden ser iguales.")
    iguales = len(slugs) - len(difs)
    avisar(f"{iguales} de {len(slugs)} nudos iguales." + ("" if not difs else
           " Si una imagen difiere en 1 o 2 niveles en pocos píxeles y el modelo es igual, prueba "
           "--reimprimir; si sigue, imprime ese nudo desde el commit de la referencia."))
    return 0 if not difs else 1


def _version(carpeta: Path) -> str | None:
    ruta = carpeta / NAVEGADOR
    return ruta.read_text(encoding="utf-8").strip() if ruta.exists() else None


def _con_motor(carpeta: Path) -> bool:
    return (carpeta / MOTOR).exists()


def _reimprimir(antes: Path, despues: Path, d: Diferencia, avisar) -> Diferencia | None:
    """Vuelve a imprimir solo un nudo, con el código de ahora, y lo compara otra vez. Solo si el
    modelo que da el código de ahora es el mismo que el de <después>. Se construye con el motor
    si <después> se armó con él."""
    previo = os.environ.get("NUDOS_MOTOR")
    os.environ["NUDOS_MOTOR"] = "1" if _con_motor(despues) else ""
    try:
        m = construir(cargar(d.slug))
    finally:
        if previo is None:
            os.environ.pop("NUDOS_MOTOR", None)
        else:
            os.environ["NUDOS_MOTOR"] = previo
    destino = despues / d.slug / "modelo.json"
    texto = json.dumps(datos_json(m), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if texto != destino.read_bytes():
        avisar(f"{d.slug}: el código de ahora da otro modelo que {despues}; no se reimprime.")
        return d
    avisar(f"{d.slug}: {len(d.imagenes)} imágenes distintas; se imprime solo otra vez.")
    _imprimir_en(m, despues / d.slug / "impresion")
    return comparar_nudo(antes, despues, d.slug)
