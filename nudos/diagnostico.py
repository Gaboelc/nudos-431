"""Diagnóstico de un borrador: dónde se acerca cada paso a los límites y en qué punto del YAML.

`python -m nudos diagnostico <slug>` construye los pasos (o solo los de `--pasos`) y dice, en
pocas líneas por paso, lo que falla o está cerca del límite y cerca de qué punto de control:
el trazado antes de relajar (la skill nudo-nuevo pide radio de 1,2 o más), y en la cuerda
relajada la separación entre tramos, la curvatura, el estiramiento y lo que mida el
anfitrión, además de dónde quedó cada cruce y cuánto se movió desde el paso anterior. Con
`--todo`, también el error común, el nudo por detrás y los dos apretados.

Cada lugar se nombra con el punto de control más cercano a lo largo de la cuerda, como
`gaza[3]`, con los índices del segmento tal como está en el YAML. Así un borrador se corrige
sin escribir scripts propios para medirlo. No escribe nada ni cambia cómo se construye.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from scipy.spatial import cKDTree

from . import SPECS
from .libre import LIMITES, Reparto, Resultado, TrazadoError, construir_paso
from .spec import Spec, _ref

# Radio mínimo del trazado antes de relajar que pide la skill nudo-nuevo, en diámetros.
TRAZADO_MIN = 1.2
# Se muestran, además del peor, otros lugares que pasan de estos valores (la falla empieza en
# LIMITES), para corregirlos de una vez.
CERCA = {"separacion": 1.0, "curvatura": 1.0, "estiramiento": 0.016}
LUGARES = 3          # cuántos lugares por medida, como máximo
APARTE = 2.0         # dos lugares cuentan como distintos si están a más de esto, en diámetros
MEDIDAS_BASE = {"largo", "separacion_min", "curvatura_min", "estiramiento_max", "altura_max"}


def leer_pasos(texto: str, total: int) -> list[int]:
    """«2,4-5» → [2, 4, 5]. Vacío: todos."""
    if not texto:
        return list(range(1, total + 1))
    out: set[int] = set()
    for parte in texto.split(","):
        a, _, b = parte.strip().partition("-")
        try:
            desde, hasta = int(a), int(b or a)
        except ValueError:
            raise ValueError(f"«{texto}»: los pasos van como 2,4-5") from None
        if not 1 <= desde <= hasta <= total:
            raise ValueError(f"«{parte.strip()}»: el nudo tiene los pasos 1 a {total}")
        out.update(range(desde, hasta + 1))
    return sorted(out)


def etiquetas(ruta: Path) -> dict[int, list[str]]:
    """Para cada paso con trazado, el nombre de cada punto de control en el YAML, como
    «gaza[3]», en el orden de `Paso.puntos`: las cuerdas en el orden de `cuerdas` y, en cada
    una, los segmentos del trazado."""
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f)
    segmentos = datos.get("segmentos") or {}
    cuerdas = [c["nombre"] for c in datos.get("cuerdas") or []]

    def largo(nombre: str) -> int:
        s = segmentos[nombre]
        return len(next(iter(s.values())) if isinstance(s, dict) else s)

    out = {}
    for n, paso in enumerate(datos.get("pasos") or [], 1):
        trazado = paso.get("trazado")
        if trazado is None:
            continue
        nombres = []
        for lista in ([trazado[c] for c in cuerdas] if cuerdas else [trazado]):
            for ref in lista:
                nombre, sel = _ref(ref, ValueError)
                nombres += [f"{nombre}[{i}]" for i in list(range(largo(nombre)))[sel]]
        out[n] = nombres
    return out


def trazado(spec: Spec, paso) -> tuple[np.ndarray, float, np.ndarray, Reparto | None]:
    """La línea central antes de relajar, su paso h, la posición a lo largo de ella de cada
    punto de control y, con varias cuerdas, el reparto. Es la misma que construye el paso."""
    if spec.anfitrion is not None and not spec.anfitrion.en_la_mesa:
        from .anfitrion import Poste, _curva
        X, h, ctrl_s, _ = _curva(paso, Poste(spec.anfitrion))
        return X, h, np.asarray(ctrl_s, float), None
    from .libre import _curva
    X, h, ctrl_s, reparto = _curva(paso, spec.cuerdas)
    return X, h, np.asarray(ctrl_s, float), reparto


# --------------------------------------------------------------------------
# Medidas por punto
# --------------------------------------------------------------------------
def radios(X, h, rep: Reparto) -> np.ndarray:
    """Radio de curvatura en cada punto, en diámetros de su cuerda, como en la comprobación
    (libre.curvatura_min con ventana 1). En los extremos de cada cuerda, infinito."""
    out = np.full(len(X), np.inf)
    for a, b in rep.tramos:
        Y = X[a:b + 1]
        if len(Y) < 4:
            continue
        t = np.diff(Y, axis=0)
        t /= np.linalg.norm(t, axis=1)[:, None]
        ang = np.arccos(np.clip((t[:-2] * t[2:]).sum(1), -1, 1))
        out[a + 2:a + 2 + len(ang)] = 2 * h / np.maximum(ang, 1e-9) / rep.grosor[a]
    return out


def cercanias(X, h, rep: Reparto, hasta: float) -> list[tuple[float, int, int]]:
    """Pares de tramos que no son vecinos en la cuerda, a menos de `hasta` veces la suma de
    sus radios: (distancia relativa, i, j), de la menor a la mayor, como libre._separacion."""
    radio = rep.radio
    pares = cKDTree(X).query_pairs(r=2 * float(radio.max()) * hasta, output_type="ndarray")
    if not len(pares):
        return []
    pares = pares[rep.lejos(pares, rep.salto(h))]
    rel = np.linalg.norm(X[pares[:, 1]] - X[pares[:, 0]], axis=1) / (radio[pares[:, 0]] + radio[pares[:, 1]])
    orden = np.argsort(rel)
    return [(float(rel[k]), int(pares[k, 0]), int(pares[k, 1])) for k in orden if rel[k] < hasta]


def estiramientos(X, h, rep: Reparto) -> list[tuple[float, int]]:
    """(estiramiento, índice del primer punto) de cada tramo de una misma cuerda, del mayor
    al menor."""
    i = np.nonzero(rep.seguido)[0]
    est = np.abs(np.linalg.norm(X[i + 1] - X[i], axis=1) / h - 1)
    return [(float(est[k]), int(i[k])) for k in np.argsort(-est)]


def _elegir(candidatos, X, cuantos=LUGARES):
    """Los primeros candidatos (valor, i, …) que caen a más de APARTE de los ya elegidos."""
    elegidos = []
    for c in candidatos:
        p = X[c[1]]
        if all(np.linalg.norm(p - X[e[1]]) > APARTE for e in elegidos):
            elegidos.append(c)
            if len(elegidos) == cuantos:
                break
    return elegidos


# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------
class Nombres:
    """Nombra un punto de la línea central por el punto de control más cercano a lo largo de
    la cuerda. Sin posiciones (el nudo apretado, que acorta la cuerda), solo por su lugar."""

    def __init__(self, X, h, ctrl_s=None, nombres=None):
        self.X, self.h = X, h
        self.ctrl_s = ctrl_s if nombres is not None and ctrl_s is not None and len(ctrl_s) == len(nombres) else None
        self.nombres = nombres

    def __call__(self, i: int) -> str:
        p = self.X[i]
        donde = f"({p[0]:.1f}, {p[1]:.1f})"
        if self.ctrl_s is None:
            return donde
        k = int(np.abs(self.ctrl_s - i * self.h).argmin())
        return f"{self.nombres[k]} {donde}"


def _marca(falla: bool) -> str:
    return "!!" if falla else "  "


def lineas_trazado(X, h, rep: Reparto, nombre: Nombres) -> list[str]:
    """El radio del trazado antes de relajar. No es una falla de construir sino la regla de la
    skill, así que se marca con un solo «!»."""
    r = radios(X, h, rep)
    candidatos = sorted((float(v), int(i)) for i, v in enumerate(r) if np.isfinite(v))
    if not candidatos:
        return []
    peores = [candidatos[0]] + [c for c in candidatos[1:] if c[0] < TRAZADO_MIN]
    elegidos = _elegir(peores, X)
    texto = "; ".join(f"{v:.2f} en {nombre(i)}" for v, i in elegidos)
    marca = "! " if elegidos[0][0] < TRAZADO_MIN else "  "
    return [f"{marca}trazado      radio {texto}  [≥ {TRAZADO_MIN}]"]


def lineas_resultado(r: Resultado, nombre: Nombres) -> list[str]:
    X, h = r.puntos, r.h
    rep = r.reparto or Reparto.una(len(X))
    out = [f"!!{f.split(': ', 1)[-1]}" for f in r.fallas if "la secuencia es" in f]

    sep = cercanias(X, h, rep, max(CERCA["separacion"], LIMITES["separacion_min"]) * 1.0001)
    if sep:
        elegidos = _elegir(sep, X)
        lim = LIMITES["separacion_min"]
        texto = "; ".join(f"{v:.2f} entre {nombre(i)} y {nombre(j)}" for v, i, j in elegidos)
        out.append(f"{_marca(elegidos[0][0] < lim)}separación   {texto}  [≥ {lim}]")
    else:
        out.append(f"  separación   {r.medidas['separacion_min']:.2f}  [≥ {LIMITES['separacion_min']}]")

    rad = radios(X, h, rep)
    cand = sorted((float(v), int(i)) for i, v in enumerate(rad) if np.isfinite(v))
    if cand:
        lim = LIMITES["curvatura_min"]
        elegidos = _elegir([cand[0]] + [c for c in cand[1:] if c[0] < CERCA["curvatura"]], X)
        texto = "; ".join(f"{v:.2f} en {nombre(i)}" for v, i in elegidos)
        out.append(f"{_marca(elegidos[0][0] < lim)}curvatura    {texto}  [≥ {lim}]")

    est = estiramientos(X, h, rep)
    if est:
        lim = LIMITES["estiramiento_max"]
        elegidos = _elegir([est[0]] + [e for e in est[1:] if e[0] > CERCA["estiramiento"]], X)
        texto = "; ".join(f"{v:.1%} en {nombre(i)}" for v, i in elegidos)
        out.append(f"{_marca(elegidos[0][0] > lim)}estiramiento {texto}  [≤ {lim:.0%}]")

    for clave, valor in r.medidas.items():
        if clave not in MEDIDAS_BASE:
            falla = any(clave.split("_")[0] in f for f in r.fallas)
            out.append(f"{_marca(falla)}{clave} {valor:.2f}")
    return out


def lineas_cruces(r: Resultado, antes: dict[str, tuple[float, float]]) -> list[str]:
    if not r.cruces:
        return []
    partes = []
    for et, (x, y) in sorted(r.cruces.items(), key=lambda kv: (len(kv[0]), kv[0])):
        mov = ""
        if et in antes:
            d = float(np.hypot(x - antes[et][0], y - antes[et][1]))
            mov = f" +{d:.1f}" + ("!!" if d > 2.5 else "")
        partes.append(f"{et} ({x:.1f}, {y:.1f}){mov}")
    return ["  cruces       " + " · ".join(partes)]


# --------------------------------------------------------------------------
# Orden
# --------------------------------------------------------------------------
def diagnostico(spec: Spec, pasos: list[int], todo: bool = False, ruta: Path | None = None) -> list[str]:
    """Las líneas del diagnóstico de los pasos `pasos` (números desde 1)."""
    if spec.plantilla is not None:
        raise ValueError(f"{spec.slug} es un nudo de plantilla: su cuerda la calcula la plantilla. "
                         "Usa python -m nudos construir.")
    nombres = etiquetas(ruta or SPECS / f"{spec.slug}.yaml")
    out = [f"{spec.nombre} ({spec.slug}). Límites: separación ≥ {LIMITES['separacion_min']}, "
           f"curvatura ≥ {LIMITES['curvatura_min']}, estiramiento ≤ {LIMITES['estiramiento_max']:.0%}; "
           f"trazado sobre la mesa ≥ {TRAZADO_MIN} (skill). !! falla; ! no cumple la skill."]
    # Sobre el poste, el trazado pasa de la mesa al poste con una esquina que el relajado
    # redondea, así que su radio no dice nada: ahí cuenta solo la curvatura relajada.
    en_la_mesa = spec.anfitrion is None or spec.anfitrion.en_la_mesa
    antes: dict[str, tuple[float, float]] = {}
    for paso in spec.pasos:
        if paso.n not in pasos:
            continue
        X0, h0, ctrl_s, rep0 = trazado(spec, paso)
        cruces = len(paso.secuencia) // 2
        out.append(f"Paso {paso.n}: {len(paso.puntos)} puntos de control, "
                   f"{cruces} cruce{'' if cruces == 1 else 's'}")
        if en_la_mesa:
            out += lineas_trazado(X0, h0, rep0 or Reparto.una(len(X0)),
                                  Nombres(X0, h0, ctrl_s, nombres.get(paso.n)))
        try:
            r = construir_paso(paso, spec.anfitrion, spec.cuerdas)
        except TrazadoError as e:
            out.append(f"!!{str(e).split(': ', 1)[-1]}")
            continue
        out += lineas_resultado(r, Nombres(r.puntos, r.h, ctrl_s, nombres.get(paso.n)))
        out += lineas_cruces(r, antes)
        antes = dict(r.cruces)
    if todo:
        out += _finales(spec, nombres)
    return out


def ampliar(imagen: Path, destino: Path, zona=(0.0, 0.0, 1.0, 1.0), lado: int = 800) -> Path:
    """Copia ampliada de una zona de una imagen de la fuente, para leer un cruce de cerca.
    `zona` es (x0, y0, x1, y1) en fracciones del ancho y el alto, desde arriba a la izquierda.
    La copia mide `lado` píxeles en su lado mayor y lleva una cuadrícula cada décimo de la
    zona, rotulada en fracciones de la imagen entera, para pedir la siguiente zona sin
    adivinar. Se guarda en `destino`, nunca junto a la fuente."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = zona
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError("la zona va como x0,y0,x1,y1, con fracciones de 0 a 1 y x0 < x1, y0 < y1")
    with Image.open(imagen) as im:
        im = im.convert("RGB")
        W, H = im.size
        recorte = im.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)))
    escala = lado / max(recorte.size)
    grande = recorte.resize((max(1, round(recorte.width * escala)), max(1, round(recorte.height * escala))),
                            Image.LANCZOS)
    d = ImageDraw.Draw(grande)
    for k in range(1, 10):
        fx, fy = x0 + (x1 - x0) * k / 10, y0 + (y1 - y0) * k / 10
        px, py = round(grande.width * k / 10), round(grande.height * k / 10)
        d.line([(px, 0), (px, grande.height)], fill=(255, 0, 255), width=1)
        d.line([(0, py), (grande.width, py)], fill=(255, 0, 255), width=1)
        d.text((px + 2, 2), f"{fx:.2f}", fill=(255, 0, 255))
        d.text((2, py + 2), f"{fy:.2f}", fill=(255, 0, 255))
    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / f"{Path(imagen).stem}-{x0:g}-{y0:g}-{x1:g}-{y1:g}.png"
    grande.save(salida)
    return salida


def _finales(spec: Spec, nombres: dict[int, list[str]]) -> list[str]:
    """El error común, el nudo por detrás y los dos apretados, como los construye construir."""
    from .construir import construir
    m = construir(spec)
    ultimo = len(spec.pasos)
    out = []
    piezas = []
    if m.error is not None:
        piezas.append((f"Error común (paso {spec.error.paso})", m.error, spec.error.paso))
    if m.reverso is not None:
        piezas.append(("Nudo por detrás", m.reverso, ultimo))
    if m.apretado is not None:
        piezas.append(("Apretado", m.apretado, None))
    if m.reverso_apretado is not None:
        piezas.append(("Apretado, por detrás", m.reverso_apretado, None))
    for titulo, r, n in piezas:
        ctrl_s = None
        if n is not None:
            paso = spec.pasos[n - 1]
            ctrl_s = trazado(spec, paso)[2]
        out.append(titulo)
        out += lineas_resultado(r, Nombres(r.puntos, r.h, ctrl_s, nombres.get(n) if n else None))
    if m.apretado is not None and m.pasos:
        final = next((r for r in m.pasos if r.n == ultimo), None)
        if final is not None:
            antes, despues = final.medidas["largo"], m.apretado.medidas["largo"]
            out.append(f"  al apretar, la cuerda baja de {antes:.1f} a {despues:.1f} diámetros "
                       f"({1 - despues / antes:.0%})")
    sueltas = [f for f in m.fallas if f.startswith(("Error", "Nudo terminado", "El nudo"))]
    out += [f"!!{f}" for f in sueltas]
    return out
