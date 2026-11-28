"""La maqueta animada de las tarjetas del video (T22a): `python -m nudos prueba-tarjetas`.

Arma build/tarjetas/maqueta.html, una sola página que se abre con doble clic: las tarjetas de
render/tarjetas/ (tarjetas.css y tarjetas.js, las mismas que dibujará Edge en T22b) con los textos
de un nudo, sobre un cuadro del video, en una secuencia de muestra de cada tipo: el nombre, lo que
necesitas, los pasos, las de capítulo con su fondo de lygia, la ✓ de la revisión, la ✗ del error y
la ✓ del correcto, otro error, la seguridad, el cierre con la pantalla final y el reel vertical con
sus subtítulos palabra por palabra. Las fuentes, lygia y los fondos van dentro de la página.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from . import RAIZ

CARPETA = RAIZ / "render" / "tarjetas"
SALIDA = RAIZ / "build" / "tarjetas"
FUENTES = RAIZ / "sitio" / "vendor" / "fuentes"
LYGIA = RAIZ / "sitio" / "vendor" / "lygia" / "lygia.js"
GRUPO = "Grupo Guía y Scout 431"

# Los colores de cada capítulo (el de arriba a la izquierda y el de abajo a la derecha del fondo).
COLORES = {"materiales": ("#1f6f7b", "#3fa5b3"), "pasos": ("#b8640c", "#eb9a31"),
           "verificacion": ("#1d7a47", "#3cb878"), "errores": ("#a82a27", "#e8574f"),
           "aplicacion": ("#3a6b2c", "#7fb05a"), "seguridad": ("#d99a00", "#ffd34d")}
ICONOS = {"materiales": "cuerda", "pasos": "pasos", "verificacion": "si", "errores": "no", "aplicacion": "tienda",
          "seguridad": "escudo"}

# Dónde va la ✓ de cada revisión sobre el cuadro de muestra (el paso 4 del as de guía en 4K, a
# 1920 × 1080): la gaza grande y el chicote junto a la gaza pequeña. Con otro fondo, no calzan.
PUNTOS_MUESTRA = ((1196, 636), (858, 470))


def _datos(ruta: Path, tipo: str) -> str:
    return f"data:{tipo};base64,{base64.b64encode(ruta.read_bytes()).decode('ascii')}"


def _fuentes() -> str:
    caras = (("Big Shoulders Display", 700, "big-shoulders-display-latin-700-normal.woff2"),
             ("Big Shoulders Display", 800, "big-shoulders-display-latin-800-normal.woff2"),
             ("IBM Plex Mono", 500, "ibm-plex-mono-latin-500-normal.woff2"),
             ("Literata", 400, "literata-latin-400-normal.woff2"),
             ("Literata", 600, "literata-latin-600-normal.woff2"))
    return "\n".join(f'@font-face {{ font-family: "{f}"; font-weight: {p}; '
                     f'src: url({_datos(FUENTES / a, "font/woff2")}) format("woff2"); }}' for f, p, a in caras)


def _lygia() -> str:
    """lygia.js sin cambios, como guion clásico: lo que exporta queda en window.lygia."""
    texto = LYGIA.read_text(encoding="utf-8")
    texto = texto.replace("export function glsl(", "function glsl(")
    if "export " in texto:
        raise ValueError("lygia.js exporta algo más que glsl()")
    return "(function () {\n" + texto + "\nwindow.lygia = { glsl };\n})();"


def palabras(texto: str, desde: float) -> list[dict]:
    """Las palabras de una frase con su tiempo estimado (el de la voz de Gabriel, `guion.estimar`):
    en el video salen del alineador (Qwen3-ForcedAligner)."""
    from .guion import POR_COMA, POR_PUNTO, POR_SILABA
    from .voz import para_decir, silabas
    out, t = [], desde + 0.2
    for p in para_decir(texto):
        d = max(0.12, POR_SILABA * sum(silabas(w) for w in p.dicha.split()))
        out.append({"texto": p.texto, "desde": round(t, 3), "hasta": round(t + d, 3)})
        t += d + (POR_PUNTO + 0.1 if p.texto.endswith((".", ":", ";")) else POR_COMA + 0.05 if p.texto.endswith(",") else 0.04)
    return out


def trozos(palabras_: list[dict], largo: int = 4) -> list[dict]:
    """Los subtítulos del reel van de a `largo` palabras como mucho, y cada frase empieza un trozo:
    a cada palabra le pone el número de su trozo."""
    n, en = 0, 0
    for k, p in enumerate(palabras_):
        if k and (en == largo or palabras_[k - 1]["texto"].endswith((".", ":", "?", "!"))):
            n, en = n + 1, 0
        p["trozo"] = n
        en += 1
    return palabras_


def frases(texto: str, desde: float) -> list[dict]:
    """El texto partido en frases (por punto o punto y coma), con su tiempo estimado."""
    partes = [p.strip() for p in re.findall(r"[^.;]+[.;]?", " ".join(texto.split())) if p.strip()]
    out, t = [], desde
    for p in partes:
        ps = palabras(p, t)
        fin = ps[-1]["hasta"] + 0.25 if ps else t + 1.0
        out.append({"texto": p, "desde": round(t, 3), "hasta": round(fin, 3)})
        t = fin
    return out


def _capitulo(cap: str, desde: float, titulo: str, sub: str = "", dura: float = 1.9) -> dict:
    return {"tipo": "capitulo", "desde": desde, "hasta": desde + dura, "titulo": titulo, "sub": sub,
            "icono": ICONOS[cap], "colores": list(COLORES[cap]), "oscuro": cap == "seguridad"}


def _siguiente(spec) -> str:
    """El nudo que nombra el cierre (para la pantalla final), sacado de sus alternativas."""
    cierre = (spec.video.cierre or "").casefold()
    for a in spec.alternativas:
        if a.nudo.casefold() in cierre:
            return a.nudo
    return spec.alternativas[0].nudo if spec.alternativas else "el nudo que sigue"


def horizontal(spec, otro=None) -> tuple[list[dict], list[tuple[str, float]]]:
    """La secuencia de muestra del video horizontal y dónde empieza cada parte, para saltar."""
    from .guion import NOMBRES, url
    v = spec.video
    total = len(spec.pasos)
    tarjetas, saltos = [], []

    def marca(nombre, t):
        saltos.append((nombre, round(max(0.0, t - 0.3), 2)))
    marca("Nombre", 0.0)
    sub = spec.familia + (f" · ABOK {spec.abok}" if spec.abok else "")
    tarjetas.append({"tipo": "nombre", "desde": 0.5, "hasta": 4.6, "nombre": spec.nombre, "sub": sub})
    t = 5.2
    if spec.materiales:
        marca("Lo que necesitas", t)
        tarjetas.append(_capitulo("materiales", t, NOMBRES["materiales"]))
        tarjetas.append({"tipo": "materiales", "desde": t + 2.0, "hasta": t + 6.0, "texto": spec.materiales})
        t += 6.6
    marca("Pasos", t)
    for p in spec.pasos[:3]:
        tarjetas.append({"tipo": "paso", "desde": round(t, 2), "hasta": round(t + 3.6, 2), "n": p.n, "total": total,
                         "titulo": p.titulo})
        t += 3.9
    marca("Cómo saber que quedó bien", t)
    tarjetas.append(_capitulo("verificacion", t, NOMBRES["verificacion"]))
    t += 2.1
    for r, (x, y) in zip(v.verificacion[:2], PUNTOS_MUESTRA):
        tarjetas.append({"tipo": "revisa", "desde": round(t, 2), "hasta": round(t + 3.0, 2),
                         "etiqueta": r.etiqueta or "", "x": x, "y": y})
        t += 3.3
    if spec.error is not None:
        marca("Error y correcto", t)
        tarjetas.append(_capitulo("errores", t, NOMBRES["errores"]))
        t += 2.1
        tarjetas.append({"tipo": "error", "desde": round(t, 2), "hasta": round(t + 3.4, 2), "titulo": spec.error.titulo})
        t += 3.7
        tarjetas.append({"tipo": "error", "si": True, "desde": round(t, 2), "hasta": round(t + 3.0, 2),
                         "titulo": spec.pasos[spec.error.paso - 1].titulo})
        t += 3.3
    otros = (spec.error.otros if spec.error is not None else ()) or (otro.error.otros if otro is not None else ())
    if otros:
        marca("Otro error" + ("" if spec.error and spec.error.otros else f" (del {otro.nombre.lower()})"), t)
        tarjetas.append({"tipo": "error", "mono": "Otro error", "desde": round(t, 2), "hasta": round(t + 3.2, 2),
                         "titulo": otros[0].titulo})
        t += 3.6
    if v.aplicacion is not None:
        marca("En la práctica", t)
        tarjetas.append(_capitulo("aplicacion", t, NOMBRES["aplicacion"], v.aplicacion.titulo, dura=2.6))
        t += 3.0
    if v.seguridad:
        marca("Seguridad", t)
        fs = frases(v.seguridad, t + 0.5)
        tarjetas.append({"tipo": "seguridad", "desde": round(t, 2), "hasta": round(fs[-1]["hasta"] + 0.3, 2), "frases": fs})
        t = fs[-1]["hasta"] + 0.9
    marca("Cierre", t)
    golpe = t + 0.4
    tarjetas.append({"tipo": "cierre", "desde": round(t, 2), "golpe": round(golpe, 2), "final": round(golpe + 1.6, 2),
                     "hasta": round(golpe + 8.0, 2), "nombre": spec.nombre, "url": url(spec.slug).removeprefix("https://"),
                     "grupo": GRUPO,
                     "finales": [{"x": 1250, "y": 250, "w": 560, "h": 315,
                                  "texto": f"Pantalla final de YouTube: el video que sigue ({_siguiente(spec)})"},
                                 {"x": 1250, "y": 610, "w": 560, "h": 150, "texto": "Pantalla final: suscribirse"}]})
    return tarjetas, saltos


def vertical(spec) -> tuple[list[dict], list[tuple[str, float]]]:
    """La secuencia de muestra del reel: el gancho, los primeros pasos, el error y el cierre, con los
    subtítulos de cada frase palabra por palabra."""
    from .guion import reel, url
    partes = {p.clave: p for p in reel(spec)}
    total = len(spec.pasos)
    tarjetas, saltos, dichas = [], [("Gancho", 0.0)], []
    gancho = partes["gancho"].voz
    tarjetas.append({"tipo": "nombre", "desde": 0.3, "hasta": 4.4, "nombre": spec.nombre, "sub": spec.familia})
    dichas.append(palabras(gancho, 0.4))
    t = 4.8
    saltos.append(("Pasos", round(t - 0.3, 2)))
    for p in spec.pasos[:3]:
        tarjetas.append({"tipo": "paso", "desde": round(t, 2), "hasta": round(t + 3.3, 2), "n": p.n, "total": total,
                         "titulo": p.titulo})
        dichas.append(palabras(partes[f"paso-{p.n}"].voz, t + 0.1))
        t += 3.6
    if spec.error is not None:
        saltos.append(("Error", round(t - 0.3, 2)))
        tarjetas.append({"tipo": "error", "desde": round(t, 2), "hasta": round(t + 3.6, 2), "titulo": spec.error.titulo})
        dichas.append(palabras(partes["error"].voz, t + 0.1))
        t += 3.9
        tarjetas.append({"tipo": "error", "si": True, "desde": round(t, 2), "hasta": round(t + 2.4, 2),
                         "titulo": spec.pasos[spec.error.paso - 1].titulo})
        t += 2.7
    saltos.append(("Cierre", round(t - 0.3, 2)))
    if "cierre" in partes:
        dichas.append(palabras(partes["cierre"].voz, t + 0.5))
    tarjetas.append({"tipo": "cierre", "desde": round(t, 2), "golpe": round(t + 0.4, 2), "final": round(t + 2.0, 2),
                     "hasta": round(t + 5.6, 2), "nombre": spec.nombre, "url": url(spec.slug).removeprefix("https://")})
    tarjetas.append({"tipo": "subtitulos", "desde": 0.0, "hasta": round(t + 5.6, 2),
                     "palabras": trozos([w for ws in dichas for w in ws])})
    return tarjetas, saltos


def maqueta(slug: str = "as-de-guia", fondo=None, fondo_vertical=None) -> Path:
    """Arma build/tarjetas/maqueta.html con los textos de `slug` y, si se dan, los cuadros de fondo."""
    from .ficha import terminos_encontrados
    from .spec import cargar
    spec = cargar(slug)
    otro = cargar("amarre-cuadrado") if not (spec.error and spec.error.otros) else None
    th, sh = horizontal(spec, otro)
    tv, sv = vertical(spec)
    textos = json.dumps([th, tv], ensure_ascii=False)
    malos = terminos_encontrados(textos)
    if malos:
        raise ValueError(f"{slug}: las tarjetas usan términos de sección: {', '.join(malos)}")
    datos = {"nombre": spec.nombre,
             "horizontal": {"formato": "horizontal", "tarjetas": th, "saltos": sh,
                            "fondo": _datos(Path(fondo), "image/jpeg" if str(fondo).lower().endswith((".jpg", ".jpeg"))
                                            else "image/png") if fondo else None},
             "vertical": {"formato": "vertical", "tarjetas": tv, "saltos": sv,
                          "fondo": _datos(Path(fondo_vertical), "image/jpeg" if str(fondo_vertical).lower().endswith(
                              (".jpg", ".jpeg")) else "image/png") if fondo_vertical else None}}
    pagina = (CARPETA / "maqueta.html").read_text(encoding="utf-8")
    for marca, valor in (("/*FUENTES*/", _fuentes()), ("/*TARJETAS_CSS*/", (CARPETA / "tarjetas.css").read_text(encoding="utf-8")),
                         ("/*LYGIA*/", _lygia()), ("/*TARJETAS_JS*/", (CARPETA / "tarjetas.js").read_text(encoding="utf-8")),
                         ("/*DATOS*/", json.dumps(datos, ensure_ascii=False)), ("__NOMBRE__", spec.nombre)):
        if marca not in pagina:
            raise ValueError(f"maqueta.html no tiene {marca}")
        pagina = pagina.replace(marca, valor)
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / "maqueta.html"
    ruta.write_text(pagina, encoding="utf-8")
    return ruta
