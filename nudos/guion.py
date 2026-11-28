"""El guion del video de un nudo (T22a): lo que dice la voz en cada capítulo, con su tarjeta y su
duración estimada, sacado de la especificación (`voz` en cada paso y error, y el bloque `video`,
formato v1.14).

- `partes(spec)`: el video entero, parte por parte, en el orden de los capítulos.
- `reel(spec)`: el guion corto del reel vertical.
- `problemas(spec)`: lo que falta o no sigue el estilo; el video no se arma con problemas.
- `linea(partes)`, `capitulos(partes)` y `youtube(spec, partes)`: la línea de tiempo estimada y los
  capítulos para YouTube, que duran 10 s o más.
- `hoja(slug)`: la hoja de revisión en HTML (`python -m nudos guion <slug>`), con la duración
  estimada de cada parte y, con `oir`, cada parte dicha por la voz de los videos.

La duración de la voz se estima con lo que midió T23 en la voz de Gabriel (`estimar`). Lo que la
imagen agrega alrededor de cada frase (`MARGEN`) es una estimación: T22b mide la real con el
movimiento del motor.
"""
from __future__ import annotations

import base64
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import RAIZ, URL_BASE

BUILD = RAIZ / "build"

# Los capítulos del video, en orden; son los de la música (musica.CAPITULOS).
CAPITULOS = ("apertura", "materiales", "pasos", "verificacion", "errores", "aplicacion", "seguridad", "cierre")
NOMBRES = {"apertura": "Apertura", "materiales": "Lo que necesitas", "pasos": "Paso a paso",
           "verificacion": "Cómo saber que quedó bien", "errores": "Errores comunes",
           "aplicacion": "En la práctica", "seguridad": "Seguridad", "cierre": "Cierre"}
# La escena de cada capítulo (T20a: el estudio para enseñar, el campamento para mostrar).
ESCENA = {"apertura": "campamento", "materiales": "estudio", "pasos": "estudio", "verificacion": "estudio",
          "errores": "estudio", "aplicacion": "campamento", "seguridad": "campamento", "cierre": "campamento"}

# Las escenas de la aplicación (`video.aplicacion.escena`), que arma T22b en Blender con utilería
# propia sobre el campamento; Gabriel eligió las de los pilotos el 27 nov. En todas, el nudo
# trabaja: la cuerda empieza floja, se tensa cuando entra la carga y el nudo aguanta, y después la
# cámara se aleja. El nudo apretado se coloca con un giro rígido, y la carga es el motor llevando
# sus puntas hasta sus anclas y asentándolas (T21e).
ESCENAS = {
    "toldo": "De 0 a 3 s, el nudo de cerca: la gaza rodea un poste de madera clavado en la tierra, cerca "
             "del suelo, y el cabo está flojo. De 3 a 6 s, el toldo jala el cabo: se tensa y la gaza no "
             "se cierra. De 6 a 11 s, la cámara se aleja y sube hasta mostrar el toldo armado, movido "
             "por el viento.",
    "mesa-de-campamento": "De 0 a 3 s, el amarre de una esquina de cerca, en una mesa de palos redondos de "
                          "unos 4 cm (cada cruce lleva una copia del mismo nudo). De 3 a 6 s, una olla se "
                          "apoya en la mesa y nada se mueve. De 6 a 12 s, la cámara se aleja hasta mostrar "
                          "la mesa entera, con un amarre en cada cruce y ollas encima.",
    "repisa-colgante": "De 0 a 3 s, una eslinga de cerca, en la punta de la tabla, que cuelga de un palo "
                       "atravesado entre dos postes, a la altura del pecho, con una eslinga en cada punta "
                       "(el nudo y su espejo). De 3 a 6 s, se ponen las ollas encima: las eslingas se "
                       "tensan y la tabla sigue horizontal. De 6 a 11 s, la cámara se aleja hasta mostrar "
                       "la repisa entre los dos postes, con ollas y tazas.",
}

# La voz de Gabriel (T23), medida en 73 locuciones del caché el 27 nov: lo que dura una locución,
# con su silencio al empezar y al terminar, es BASE más tanto por sílaba dicha, por coma y por
# cada punto (o dos puntos) que no es el último. El error medio es de 0,46 s.
BASE, POR_SILABA, POR_COMA, POR_PUNTO = 1.44, 0.134, 0.086, 0.246

# Lo que la imagen agrega alrededor de cada frase, en s: el movimiento que sigue a la voz de un
# paso, la cámara que va de una cosa a otra en la revisión, el error que se ata, se marca y vuelve
# atrás antes del correcto, la cámara que se aleja en la aplicación.
MARGEN = {"apertura": 2.0, "materiales": 1.0, "pasos": 1.8, "verificacion": 1.2, "error": 3.5,
          "errores": 1.0, "aplicacion": 2.5, "seguridad": 1.0, "cierre": 1.5}
MINIMO = {"apertura": 6.0, "materiales": 3.0}   # s: lo menos que dura el capítulo
CAMBIO_CAPITULO = 0.6      # s: la tarjeta de capítulo, entre uno y otro
PANTALLA_FINAL = 10.0      # s al final para la pantalla final de YouTube (de 5 a 20 s)
MIN_YOUTUBE = 10.0         # s: YouTube no acepta capítulos más cortos
# El video no tiene una duración meta: dura lo que haga falta para explicar bien (Gabriel, 27 nov).
CUADRO_4K = 3.3            # s por cuadro de 4K con EEVEE a 32 muestras (aspecto.MOTOR_VIDEO; Gabriel, 27 nov)
FPS = 60

# El reel vertical: el gancho, el título de cada paso dicho con su movimiento a unas dos veces la
# velocidad, el error, la aplicación y el cierre.
REEL = (45.0, 60.0)
MARGEN_REEL = {"apertura": 1.0, "pasos": 2.2, "errores": 2.5, "aplicacion": 1.5, "cierre": 1.5}

LARGO_ETIQUETA = 32        # letras: lo que cabe junto a la ✓ en el vertical

# Lo que Gabriel no diría (27 nov): diminutivos y «así», que no van con su manera de hablar. Los
# puntos suspensivos tampoco: la voz clonada los dice estirando la palabra de antes («deeel»).
PALABRAS_EVITAR = ("así", "chiquito", "chiquitito", "pequeñito", "pequeñita", "cortito", "cortita", "poquito",
                   "poquita", "ratito", "ahorita", "despacito", "rapidito", "facilito", "tantito", "bonito")


class GuionError(ValueError):
    """El guion de un nudo tiene problemas."""


@dataclass
class Parte:
    """Una frase del video: en qué capítulo va, lo que dice la voz y lo que muestra su tarjeta."""
    capitulo: str
    clave: str                   # «apertura», «paso-3», «revisa-2», «error», «otro-1»…
    voz: str
    tarjeta: dict
    margen: float                # s de imagen que la acompañan además de la voz
    falta: bool = False          # sin `voz` en la especificación: se estima con el texto de la ficha
    segundos: float = 0.0        # la voz, estimada o medida
    medida: bool = False         # si `segundos` es de la locución ya generada
    inicio: float = 0.0          # en el video, estimado
    fin: float = 0.0
    audio: str | None = None     # con `oir`, el archivo de la locución en la hoja

    @property
    def dura(self) -> float:
        return self.segundos + self.margen


# --------------------------------------------------------------------------
# El estilo
# --------------------------------------------------------------------------
def estilo_del_guion(texto: str) -> list[str]:
    """Lo que el guion hablado no debe tener: puntos suspensivos, las PALABRAS_EVITAR y
    comparaciones («como un ojo», «es como un conejo que sale de su pozo», «como si fuera un
    tejido»), que a Gabriel no le gustan (27 nov). «Como en su ficha» sí va: no compara."""
    out = []
    if "…" in texto or "..." in texto:
        out.append("tiene puntos suspensivos, que la voz dice estirando la palabra de antes")
    palabras = set(re.findall(r"[^\W\d_]+", texto.casefold()))
    malas = [w for w in PALABRAS_EVITAR if w in palabras]
    if malas:
        out.append(f"usa palabras que Gabriel no diría: {', '.join(malas)}")
    comparaciones = re.findall(r"\bcomo (?:un|una|si)\b[^.,;:]*", texto.casefold())
    if comparaciones:
        out.append("tiene comparaciones, que a Gabriel no le gustan: " + "; ".join(f"«{c.strip()}»" for c in comparaciones))
    return out


# --------------------------------------------------------------------------
# Las partes
# --------------------------------------------------------------------------
def url(slug: str) -> str:
    return f"{URL_BASE}{slug}/"


def _frase(texto: str, dos_puntos: bool = False) -> str:
    """La primera frase de un texto; con `dos_puntos`, hasta los dos puntos si van antes."""
    texto = " ".join(texto.split())
    m = re.match(r"(.+?)(?:[.!?]|:(?=\s))(?:\s|$)" if dos_puntos else r"(.+?[.!?])(?:\s|$)", texto)
    frase = m.group(1) if m else texto
    return frase if frase[-1:] in ".!?" else frase + "."


def _de_la_ficha(p, total: int) -> str:
    return f"Paso {p.n} de {total}. {p.titulo.rstrip('.')}. {' '.join(p.texto.split())}"


def partes(spec) -> list[Parte]:
    """El video entero, frase por frase, en el orden de los capítulos. Un paso sin `voz` va con el
    texto de su ficha (y `falta`), para que la duración estimada no quede corta."""
    v = spec.video
    total = len(spec.pasos)
    out = []
    if v.apertura:
        out.append(Parte("apertura", "apertura", v.apertura,
                         {"tipo": "nombre", "nombre": spec.nombre, "familia": spec.familia, "abok": spec.abok},
                         MARGEN["apertura"]))
    if v.materiales:
        out.append(Parte("materiales", "materiales", v.materiales,
                         {"tipo": "materiales", "texto": spec.materiales or ""}, MARGEN["materiales"]))
    for p in spec.pasos:
        out.append(Parte("pasos", f"paso-{p.n}", p.voz or _de_la_ficha(p, total),
                         {"tipo": "paso", "n": p.n, "total": total, "titulo": p.titulo}, MARGEN["pasos"],
                         falta=not p.voz))
    for i, r in enumerate(v.verificacion, 1):
        out.append(Parte("verificacion", f"revisa-{i}", r.voz,
                         {"tipo": "revisa", "etiqueta": r.etiqueta or "", "mira": r.mira, "lado": r.lado},
                         MARGEN["verificacion"]))
    if spec.error is not None:
        e = spec.error
        out.append(Parte("errores", "error", e.voz or e.texto,
                         {"tipo": "error", "titulo": e.titulo, "paso": e.paso}, MARGEN["error"], falta=not e.voz))
        for i, o in enumerate(e.otros, 1):
            out.append(Parte("errores", f"otro-{i}", o.voz or o.texto, {"tipo": "otro", "titulo": o.titulo},
                             MARGEN["errores"], falta=not o.voz))
    if v.aplicacion is not None:
        out.append(Parte("aplicacion", "aplicacion", v.aplicacion.voz,
                         {"tipo": "aplicacion", "titulo": v.aplicacion.titulo, "escena": v.aplicacion.escena},
                         MARGEN["aplicacion"]))
    if v.seguridad:
        out.append(Parte("seguridad", "seguridad", v.seguridad, {"tipo": "seguridad"}, MARGEN["seguridad"]))
    if v.cierre:
        out.append(Parte("cierre", "cierre", v.cierre,
                         {"tipo": "cierre", "nombre": spec.nombre, "url": url(spec.slug)}, MARGEN["cierre"]))
    return out


def reel(spec) -> list[Parte]:
    """El guion corto del reel vertical: el gancho (la primera frase de la apertura, hasta los dos
    puntos), el título de cada paso, el error, la primera frase de la aplicación y la del cierre.
    `video.reel` cambia el gancho o el cierre."""
    v = spec.video
    total = len(spec.pasos)
    out = []
    gancho = v.reel.gancho or (_frase(v.apertura, dos_puntos=True) if v.apertura else spec.nombre + ".")
    out.append(Parte("apertura", "gancho", gancho, {"tipo": "nombre", "nombre": spec.nombre},
                     MARGEN_REEL["apertura"]))
    for p in spec.pasos:
        out.append(Parte("pasos", f"paso-{p.n}", p.titulo.rstrip(".") + ".",
                         {"tipo": "paso", "n": p.n, "total": total, "titulo": p.titulo}, MARGEN_REEL["pasos"]))
    if spec.error is not None:
        t = spec.error.titulo.rstrip(".")
        out.append(Parte("errores", "error", f"El error más común: {t[:1].lower()}{t[1:]}.",
                         {"tipo": "error", "titulo": spec.error.titulo}, MARGEN_REEL["errores"]))
    if v.aplicacion is not None:
        out.append(Parte("aplicacion", "aplicacion", _frase(v.aplicacion.voz),
                         {"tipo": "aplicacion", "titulo": v.aplicacion.titulo}, MARGEN_REEL["aplicacion"]))
    cierre = v.reel.cierre or (_frase(v.cierre) if v.cierre else None)
    if cierre:
        out.append(Parte("cierre", "cierre", cierre, {"tipo": "cierre", "nombre": spec.nombre, "url": url(spec.slug)},
                         MARGEN_REEL["cierre"]))
    return out


# --------------------------------------------------------------------------
# Lo que falta
# --------------------------------------------------------------------------
def problemas(spec) -> list[str]:
    """Lo que le falta al guion para armar el video, o lo que no sigue el estilo. Vacío si está
    listo."""
    from .ficha import terminos_encontrados
    v = spec.video
    out = []
    for campo, valor in (("apertura", v.apertura), ("cierre", v.cierre)):
        if not valor:
            out.append(f"falta «video.{campo}»")
    sin_voz = [p.n for p in spec.pasos if not p.voz]
    if sin_voz:
        out.append(f"falta la «voz» de los pasos {', '.join(map(str, sin_voz))}")
    if not v.verificacion:
        out.append("falta «video.verificacion»: lo que se revisa al final, con la voz")
    if spec.error is not None and not spec.error.voz:
        out.append("falta la «voz» del error")
    if v.aplicacion is None:
        out.append("falta «video.aplicacion»")
    elif v.aplicacion.escena not in ESCENAS:
        out.append(f"la escena «{v.aplicacion.escena}» no existe; puede ser {', '.join(ESCENAS)}")
    if spec.seguridad and not v.seguridad:
        out.append("la ficha tiene «seguridad» y falta «video.seguridad», que dice todo lo que dice ella")
    largas = [r.etiqueta for r in v.verificacion if r.etiqueta and len(r.etiqueta) > LARGO_ETIQUETA]
    if largas:
        out.append(f"etiquetas de más de {LARGO_ETIQUETA} letras: " + "; ".join(f"«{e}»" for e in largas))
    textos = [p.voz for p in partes(spec) if not p.falta] + [p.voz for p in reel(spec)]
    textos += [r.etiqueta for r in v.verificacion if r.etiqueta]
    textos += [v.aplicacion.titulo] if v.aplicacion else []
    malos = terminos_encontrados(" ".join(textos))
    if malos:
        out.append(f"usa términos de sección: {', '.join(malos)}")
    for problema in estilo_del_guion(" ".join(textos)):
        out.append(problema)
    largo = sum(p.dura for p in reel_con_tiempos(spec))
    if largo > REEL[1]:
        out.append(f"el reel dura unos {largo:.0f} s, y no debe pasar de {REEL[1]:.0f}")
    return out


def revisado(spec) -> list[Parte]:
    """Las partes del video, o GuionError si el guion tiene problemas."""
    malos = problemas(spec)
    if malos:
        raise GuionError(f"{spec.slug}: " + "; ".join(malos))
    return partes(spec)


# --------------------------------------------------------------------------
# Los tiempos
# --------------------------------------------------------------------------
def estimar(texto: str) -> float:
    """Lo que dura una locución de la voz de Gabriel, con su silencio al empezar y al terminar."""
    from .voz import para_decir, silabas
    palabras = para_decir(texto)
    sil = sum(silabas(w) for p in palabras for w in p.dicha.split())
    t = " ".join(texto.split())
    puntos = len(re.findall(r"[.:;?!]", t.rstrip(".:;?!")))
    return BASE + POR_SILABA * sil + POR_COMA * t.count(",") + POR_PUNTO * puntos


def medir(lista: list[Parte], medidas: list[float | None] | None = None) -> list[Parte]:
    """La duración de cada voz: la medida, si ya se generó, o la estimada."""
    medidas = medidas or [None] * len(lista)
    for p, m in zip(lista, medidas):
        p.segundos, p.medida = (m, True) if m is not None else (estimar(p.voz), False)
    return lista


def linea(lista: list[Parte], final: float = PANTALLA_FINAL) -> float:
    """La línea de tiempo estimada: cada parte dura su voz más su margen, con la tarjeta de capítulo
    entre capítulos y lo mínimo de cada uno. Al final, `final` s para la pantalla final. Da la
    duración total."""
    t, previo, desde = 0.0, None, {}
    for p in lista:
        if previo is not None and p.capitulo != previo:
            t = max(t, desde[previo] + MINIMO.get(previo, 0.0)) + CAMBIO_CAPITULO
        desde.setdefault(p.capitulo, t)
        p.inicio = t
        t += p.dura
        p.fin = t
        previo = p.capitulo
    if previo is not None:
        t = max(t, desde[previo] + MINIMO.get(previo, 0.0))
        lista[-1].fin = t
    return t + final


def con_tiempos(spec, medidas=None) -> tuple[list[Parte], float]:
    lista = medir(partes(spec), medidas)
    return lista, linea(lista)


def reel_con_tiempos(spec, medidas=None) -> list[Parte]:
    lista = medir(reel(spec), medidas)
    linea(lista, final=0.0)
    return lista


def capitulos(lista: list[Parte], total: float) -> list[tuple[str, float, float]]:
    """(capítulo, inicio, fin) de cada capítulo, uno detrás del otro hasta `total`."""
    out: list[list] = []
    for p in lista:
        if not out or out[-1][0] != p.capitulo:
            out.append([p.capitulo, p.inicio, p.fin])
        out[-1][2] = p.fin
    for a, b in zip(out, out[1:]):
        a[2] = b[1]
    if out:
        out[0][1] = 0.0
        out[-1][2] = total
    return [tuple(c) for c in out]


def _titulo_youtube(spec, capitulo: str) -> str:
    if capitulo in ("apertura", "materiales"):
        return spec.nombre
    if capitulo == "aplicacion" and spec.video.aplicacion is not None:
        return f"En la práctica: {spec.video.aplicacion.titulo[:1].lower()}{spec.video.aplicacion.titulo[1:]}"
    if capitulo == "cierre":
        return "Lo que sigue"
    return NOMBRES[capitulo]


def youtube(spec, caps: list[tuple[str, float, float]]) -> list[tuple[float, str]]:
    """Los capítulos para la descripción de YouTube: el primero en 0:00 y cada uno de 10 s o más
    (los más cortos se juntan con el de antes; la apertura, con lo que necesitas)."""
    juntos: list[list] = []
    for cap, a, b in caps:
        titulo = _titulo_youtube(spec, cap)
        if juntos and (b - a < MIN_YOUTUBE or juntos[-1][1] == titulo):
            juntos[-1][2] = b
        else:
            juntos.append([a, titulo, b])
    # El primero, si quedó corto, se junta con el siguiente.
    while len(juntos) > 1 and juntos[0][2] - juntos[0][0] < MIN_YOUTUBE:
        juntos[1][0] = juntos[0][0]
        juntos[1][1] = juntos[0][1]
        juntos.pop(0)
    if juntos:
        juntos[0][0] = 0.0
    return [(a, t) for a, t, _ in juntos]


def reloj(t: float) -> str:
    s = int(round(t))
    return f"{s // 60}:{s % 60:02d}"


# --------------------------------------------------------------------------
# La hoja de revisión
# --------------------------------------------------------------------------
COLOR = {"apertura": "#6b7f99", "materiales": "#3f8f9c", "pasos": "#d1801a", "verificacion": "#2f9e62",
         "errores": "#d64541", "aplicacion": "#5c8f3a", "seguridad": "#e0a800", "cierre": "#16202f"}


def _fuentes() -> str:
    """Las fuentes del sitio dentro de la página, para que se vea igual sin servidor."""
    carpeta = RAIZ / "sitio" / "vendor" / "fuentes"
    caras = (("Big Shoulders Display", 800, "big-shoulders-display-latin-800-normal.woff2"),
             ("IBM Plex Mono", 500, "ibm-plex-mono-latin-500-normal.woff2"),
             ("Literata", 400, "literata-latin-400-normal.woff2"),
             ("Literata", 600, "literata-latin-600-normal.woff2"))
    out = []
    for familia, peso, archivo in caras:
        datos = base64.b64encode((carpeta / archivo).read_bytes()).decode("ascii")
        out.append(f'@font-face {{ font-family: "{familia}"; font-weight: {peso}; '
                   f'src: url(data:font/woff2;base64,{datos}) format("woff2"); }}')
    return "\n".join(out)


def _tarjeta(t: dict) -> str:
    """Lo que muestra la tarjeta de una parte, en una línea."""
    e = html.escape
    tipo = t["tipo"]
    if tipo == "nombre":
        return f'<b>{e(t["nombre"])}</b>'
    if tipo == "materiales":
        return f'Lo que necesitas · {e(t.get("texto", ""))}'
    if tipo == "paso":
        return f'<span class="num">{t["n"]}</span> Paso {t["n"]} de {t["total"]} · <b>{e(t["titulo"])}</b>'
    if tipo == "revisa":
        lado = " · por detrás" if t.get("lado") == "detras" else ""
        mira = f' <span class="mira">mira {e(t["mira"])}{lado}</span>' if t.get("mira") else (
            f' <span class="mira">el nudo entero{lado}</span>')
        return f'<span class="si">✓</span> {e(t.get("etiqueta") or "")}{mira}'
    if tipo == "error":
        return f'<span class="no">✗</span> <b>{e(t["titulo"])}</b> · después, el correcto con ✓'
    if tipo == "otro":
        return f'<span class="no">✗</span> {e(t["titulo"])}'
    if tipo == "aplicacion":
        escena = f' <span class="mira">escena {e(t["escena"])}</span>' if t.get("escena") else ""
        return f'<b>{e(t["titulo"])}</b>{escena}'
    if tipo == "seguridad":
        return "Seguridad"
    if tipo == "cierre":
        return f'<b>{e(t["nombre"])}</b> · {e(t["url"])}'
    return ""


def _duracion(p: Parte) -> str:
    voz = f'{p.segundos:.1f}'.replace(".", ",")
    como = "medida" if p.medida else "estimada"
    return f'<span class="voz">voz {voz} s</span><span class="como">{como}</span>'


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guion: {nombre}</title>
<style>
{fuentes}
:root {{ color-scheme: light; --tinta: #16202f; --suave: #586273; --fondo: #eceff1; --hoja: #f7f9fa;
        --linea: #ccd4db; --ambar: #d1801a; --verde: #2f9e62; --rojo: #d64541; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--fondo); color: var(--tinta); font: 17px/1.55 Literata, Georgia, serif; }}
main {{ max-width: 980px; margin: 0 auto; padding: 32px 16px 80px; }}
h1 {{ font: 800 46px/1 "Big Shoulders Display", sans-serif; text-transform: uppercase; margin: 0 0 6px; }}
h2 {{ font: 800 26px/1.1 "Big Shoulders Display", sans-serif; text-transform: uppercase; letter-spacing: .01em;
      margin: 34px 0 10px; }}
.bajada {{ color: var(--suave); margin: 0 0 18px; max-width: 70ch; }}
.mono, .voz, .como, .t, .mira, .num {{ font-family: "IBM Plex Mono", monospace; }}
.cifras {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 8px; }}
.cifra {{ background: var(--hoja); border: 1px solid var(--linea); border-radius: 12px; padding: 10px 14px; }}
.cifra b {{ display: block; font: 800 30px/1 "Big Shoulders Display", sans-serif; }}
.cifra span {{ font: 500 12px/1.3 "IBM Plex Mono", monospace; color: var(--suave); text-transform: uppercase;
               letter-spacing: .06em; }}
.barra {{ display: flex; height: 34px; border-radius: 9px; overflow: hidden; margin: 10px 0 4px; }}
.barra div {{ color: #fff; font: 500 11px/34px "IBM Plex Mono", monospace; white-space: nowrap; overflow: hidden;
              text-overflow: ellipsis; padding: 0 6px; min-width: 2px; }}
.problemas {{ background: #fdecea; border: 1px solid #f3b8b3; border-radius: 12px; padding: 12px 18px; }}
.problemas li {{ margin: 3px 0; }}
.listo {{ background: #e8f5ee; border: 1px solid #b5dec6; border-radius: 12px; padding: 10px 16px; }}
.cap {{ margin: 26px 0 0; }}
.cap h3 {{ display: flex; align-items: baseline; gap: 10px; font: 800 21px/1.1 "Big Shoulders Display", sans-serif;
          text-transform: uppercase; margin: 0 0 8px; padding-left: 12px; border-left: 6px solid var(--c); }}
.cap h3 .t {{ font-size: 13px; font-weight: 500; color: var(--suave); text-transform: none; }}
.parte {{ display: grid; grid-template-columns: 1fr 150px; gap: 6px 16px; background: var(--hoja);
          border: 1px solid var(--linea); border-radius: 12px; padding: 12px 16px; margin: 0 0 8px; }}
.parte .tarjeta {{ grid-column: 1 / -1; font-size: 14px; color: var(--suave); }}
.parte .dice {{ font-size: 18px; }}
.parte .dice.falta {{ color: #9a3b33; }}
.parte .tiempo {{ text-align: right; font-size: 13px; }}
.parte .tiempo .voz {{ display: block; font-weight: 500; }}
.parte .tiempo .como {{ display: block; color: var(--suave); font-size: 11px; text-transform: uppercase;
                         letter-spacing: .06em; }}
.parte .tiempo .en {{ display: block; color: var(--suave); font: 500 11px/1.4 "IBM Plex Mono", monospace; }}
.parte audio {{ grid-column: 1 / -1; width: 100%; height: 36px; }}
.num {{ display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px;
        background: var(--ambar); color: #fff; font-size: 12px; font-weight: 500; }}
.si {{ color: var(--verde); font-weight: 700; }} .no {{ color: var(--rojo); font-weight: 700; }}
.mira {{ font-size: 12px; color: var(--suave); background: #e3e8eb; border-radius: 6px; padding: 1px 6px; }}
pre {{ background: var(--hoja); border: 1px solid var(--linea); border-radius: 12px; padding: 14px 16px;
       font: 500 14px/1.6 "IBM Plex Mono", monospace; white-space: pre-wrap; }}
.notas {{ color: var(--suave); font-size: 15px; }}
.notas li {{ margin: 4px 0; }}
audio.todo {{ width: 100%; margin: 6px 0 0; }}
@media (max-width: 640px) {{ .parte {{ grid-template-columns: 1fr; }} .parte .tiempo {{ text-align: left; }} }}
</style></head>
<body><main>
<h1>{nombre}</h1>
<p class="bajada">El guion del video completo, como lo diría la voz, con lo que muestra cada tarjeta y la duración
de cada parte. Sale de la especificación: la «voz» de cada paso y de cada error, y el bloque «video».</p>
{cuerpo}
</main></body></html>
"""


def _html(spec, lista: list[Parte], total: float, rl: list[Parte], malos: list[str], todo: str | None) -> str:
    e = html.escape
    caps = capitulos(lista, total)
    yt = youtube(spec, caps)
    largo_reel = sum(p.dura for p in rl)
    voz = sum(p.segundos for p in lista)
    medidas = sum(p.medida for p in lista)
    horas = f"{total * FPS * CUADRO_4K / 3600:.1f}".replace(".", ",")
    por_cuadro = f"{CUADRO_4K:.1f}".replace(".", ",")
    cuerpo = ['<div class="cifras">',
              f'<div class="cifra"><b>{reloj(total)}</b><span>el video, estimado</span></div>',
              f'<div class="cifra"><b>{reloj(voz)}</b><span>de voz ({medidas} de {len(lista)} medidas)</span></div>',
              f'<div class="cifra"><b>{reloj(largo_reel)}</b><span>el reel (de {REEL[0]:.0f} a {REEL[1]:.0f} s)</span></div>',
              f'<div class="cifra"><b>{horas} h</b><span>de render en 4K, a {por_cuadro} s por cuadro '
              f'(EEVEE)</span></div>', '</div>']
    barra = "".join(f'<div style="flex: {b - a:.2f}; background: {COLOR[c]}" title="{e(NOMBRES[c])}: '
                    f'{b - a:.0f} s">{e(NOMBRES[c])}</div>' for c, a, b in caps)
    cuerpo.append(f'<div class="barra">{barra}</div>')
    if malos:
        cuerpo.append('<div class="problemas"><b>Le falta para el video:</b><ul>'
                      + "".join(f"<li>{e(m)}</li>" for m in malos) + "</ul></div>")
    else:
        cuerpo.append('<p class="listo">El guion está completo y sigue el estilo: sin términos de sección, '
                      'sin comparaciones, sin diminutivos ni «así» y sin puntos suspensivos.</p>')
    if todo:
        cuerpo.append('<h2>La narración entera</h2><p class="bajada">Toda la voz, una frase tras otra, con la '
                      'música del nudo, el clic de cada tarjeta y el golpe del cierre. Los silencios entre '
                      'frases son los estimados; en el video, el movimiento los llena.</p>'
                      f'<audio class="todo" controls preload="none" src="{e(todo)}"></audio>')
    cuerpo.append("<h2>El video completo</h2>")
    for cap, a, b in caps:
        cuerpo.append(f'<section class="cap" style="--c: {COLOR[cap]}"><h3>{e(NOMBRES[cap])}'
                      f'<span class="t">{reloj(a)} a {reloj(b)} · {b - a:.0f} s · {ESCENA[cap]}</span></h3>')
        for p in (q for q in lista if q.capitulo == cap):
            falta = ' falta' if p.falta else ''
            aviso = '<br><small>(falta su «voz»: es el texto de la ficha)</small>' if p.falta else ''
            audio = f'<audio controls preload="none" src="{e(p.audio)}"></audio>' if p.audio else ''
            cuerpo.append(f'<div class="parte"><div class="tarjeta">{_tarjeta(p.tarjeta)}</div>'
                          f'<div class="dice{falta}">{e(p.voz)}{aviso}</div>'
                          f'<div class="tiempo">{_duracion(p)}<span class="en">+{p.margen:.1f} s de imagen'
                          f'</span><span class="en">desde {reloj(p.inicio)}</span></div>{audio}</div>')
        cuerpo.append('</section>')
    cuerpo.append('<h2>Capítulos para YouTube</h2><p class="bajada">Para la descripción del video. YouTube pide '
                  'el primero en 0:00 y cada uno de 10 s o más: los más cortos van juntos con el de antes.</p>')
    cuerpo.append("<pre>" + e("\n".join(f"{reloj(a)} {t}" for a, t in yt)) + "</pre>")
    cuerpo.append(f'<h2>El reel vertical</h2><p class="bajada">Unos {largo_reel:.0f} s: el gancho, el título de '
                  'cada paso dicho mientras se ata a unas dos veces la velocidad, el error, la aplicación y el '
                  'cierre, con los subtítulos quemados palabra por palabra.</p>')
    for p in rl:
        cuerpo.append(f'<div class="parte"><div class="tarjeta">{_tarjeta(p.tarjeta)}</div>'
                      f'<div class="dice">{e(p.voz)}</div><div class="tiempo">{_duracion(p)}'
                      f'<span class="en">+{p.margen:.1f} s de imagen</span></div></div>')
    cuerpo.append('<h2>Cómo se estima</h2><ul class="notas">'
                  f'<li>La voz: lo que midió T23 en tu voz clonada, {BASE:.2f} s más {POR_SILABA:.3f} s por sílaba, '
                  f'{POR_COMA:.3f} s por coma y {POR_PUNTO:.3f} s por punto, con un error medio de medio segundo. '
                  'Las partes ya generadas dicen «medida».</li>'
                  '<li>La imagen: cada parte suma lo que el video muestra después de la voz (el movimiento del '
                  'paso, la cámara que va a lo siguiente, el error que se ata y vuelve atrás). Son estimados: la '
                  'implementación (T22b) los mide con el motor, y la voz manda el tiempo.</li>'
                  f'<li>Entre capítulos, {CAMBIO_CAPITULO:.1f} s de la tarjeta de capítulo; al final, '
                  f'{PANTALLA_FINAL:.0f} s para la pantalla final de YouTube.</li></ul>')
    fuentes = _fuentes()
    return PAGINA.format(nombre=e(spec.nombre), fuentes=fuentes, cuerpo="\n".join(cuerpo))


def _medidas_en_cache(textos: list[str]) -> list[float | None]:
    """La duración de las locuciones que ya se generaron con la voz de los videos (sin generar)."""
    from . import voz as V
    try:
        return [L.segundos if L is not None else None for L in V.en_cache(textos, V.VOZ)]
    except Exception:            # sin la muestra de la voz (un clon sin entradas): todo estimado
        return [None] * len(textos)


def hoja(slug: str, oir: bool = False, aviso=print, **narrar) -> Path:
    """Arma build/<slug>/guion/index.html, la hoja de revisión del guion, con la duración estimada
    de cada parte (la medida, si la locución ya está en el caché de la voz). Con `oir`, genera lo
    que falte con la voz de los videos, como lo haría el video (sin titubeos y con el
    reconocimiento de voz revisando cada locución), y pone cada parte y la narración entera.
    `narrar` pasa a `prueba_sonido.narracion` (otra voz, otros instrumentos, sin alineador…)."""
    from .spec import cargar
    spec = cargar(slug)
    destino = BUILD / slug / "guion"
    destino.mkdir(parents=True, exist_ok=True)
    lista, rl = partes(spec), reel(spec)
    todo = None
    if oir:
        from . import mezcla as MZ
        from . import prueba_sonido as P
        from . import sonoridad as so
        from . import voz as V
        narrar.setdefault("revisar", lambda ts, ls: P._se_entiende(ts, ls, aviso))
        pista, locs = P.narracion([(p.capitulo, p.voz) for p in lista], slug, aviso=aviso, **narrar)
        for p, L in zip(lista, locs):
            p.audio = f"{p.clave}.m4a"
            nivelado = so.limitar_pico(so.a_lufs(L.audio, V.SR, P.NIVEL_VOZ), V.SR, P.TECHO)
            P._m4a(destino / p.audio, nivelado, V.SR, kbps=128)
        medir(lista, [L.segundos for L in locs])
        P._m4a(destino / "narracion.m4a", pista.audio, MZ.SR, kbps=192)
        todo = "narracion.m4a"
        medir(rl, _medidas_en_cache([p.voz for p in rl]))
    else:
        medir(lista, _medidas_en_cache([p.voz for p in lista]))
        medir(rl, _medidas_en_cache([p.voz for p in rl]))
    total = linea(lista)
    linea(rl, final=0.0)
    malos = problemas(spec)
    (destino / "index.html").write_text(_html(spec, lista, total, rl, malos, todo), encoding="utf-8")
    caps = capitulos(lista, total)
    (destino / "guion.json").write_text(json.dumps({
        "segundos": round(total, 1), "reel": round(sum(p.dura for p in rl), 1),
        "capitulos": [{"capitulo": c, "inicio": round(a, 1), "fin": round(b, 1)} for c, a, b in caps],
        "youtube": [f"{reloj(a)} {t}" for a, t in youtube(spec, caps)],
        "partes": [{"clave": p.clave, "capitulo": p.capitulo, "voz": p.voz, "segundos": round(p.segundos, 2),
                    "medida": p.medida, "inicio": round(p.inicio, 1)} for p in lista],
        "problemas": malos}, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino / "index.html"
