"""Las pruebas de escucha de T23: `prueba-voz` y `prueba-musica`, en revision/ (fuera de git).

- `prueba_voz()`: la apertura y dos pasos del as de guía, dichos por cada voz de
  `voz.VOCES_PRUEBA`, todos a la misma sonoridad, en una página para escuchar a ciegas: las voces
  van con una letra, en un orden al azar con semilla fija, y la clave queda escondida al final.
- `prueba_musica()`: el instrumento del motivo de la serie (cada opción en la apertura y el cierre
  de «Fogata») y las cinco canciones sobre la misma línea de tiempo, sin voz y con la voz elegida.
"""
from __future__ import annotations

import html
import json
import random
import re
import unicodedata
from pathlib import Path

import numpy as np

from . import RAIZ

REVISION = RAIZ / "revision"
NIVEL_VOZ = -20.0          # LUFS de cada locución en la prueba: todas igual de fuertes
TECHO = -1.0               # dBTP


def _oracion(texto: str) -> str:
    """La primera oración de un texto."""
    m = re.match(r"(.+?[.!?])(\s|$)", " ".join(texto.split()))
    return m.group(1) if m else texto.strip()


def _punto(texto: str) -> str:
    texto = texto.strip()
    return texto if texto[-1:] in ".!?:" else texto + "."


def textos_prueba(slug: str = "as-de-guia", pasos=(2, 4)) -> list[tuple[str, str]]:
    """(nombre, texto) de la apertura y de los pasos elegidos, sacados de la especificación."""
    from .ficha import terminos_encontrados
    from .spec import cargar
    spec = cargar(slug)
    total = len(spec.pasos)
    out = [("Apertura", f"{_punto(spec.nombre)} {_oracion(spec.usos or '')}")]
    for n in pasos:
        p = spec.pasos[n - 1]
        out.append((f"Paso {n}", f"Paso {n} de {total}. {_punto(p.titulo)} {' '.join(p.texto.split())}"))
    malos = terminos_encontrados(" ".join(t for _, t in out))
    if malos:
        raise ValueError(f"{slug}: el texto de la prueba usa términos de sección: {', '.join(malos)}")
    return out


def _wav16(ruta: Path, x, sr: int) -> None:
    from scipy.io import wavfile
    ruta.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(ruta, sr, (np.clip(np.asarray(x), -1, 1) * 32767).round().astype(np.int16))


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
  :root {{ color-scheme: light; --tinta: #16202f; --suave: #586273; --marca: #d1801a; --fondo: #f6f4ef; }}
  body {{ margin: 0; background: var(--fondo); color: var(--tinta);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; margin: 0 0 6px; }}
  .bajada {{ color: var(--suave); margin: 0 0 24px; }}
  .voz {{ background: #fff; border-radius: 14px; padding: 18px 20px; margin: 0 0 16px;
          box-shadow: 0 2px 10px rgba(22, 32, 47, .06); }}
  .voz h2 {{ margin: 0 0 10px; font-size: 22px; }}
  .voz h2 span {{ color: var(--marca); }}
  .clip {{ display: grid; grid-template-columns: 110px 1fr; gap: 10px; align-items: center; margin: 6px 0; }}
  .clip b {{ font-weight: 600; font-size: 14px; color: var(--suave); }}
  audio {{ width: 100%; height: 36px; }}
  .texto {{ grid-column: 2; font-size: 13px; color: var(--suave); margin: -4px 0 6px; }}
  details {{ margin-top: 28px; background: #fff; border-radius: 14px; padding: 14px 20px; }}
  summary {{ cursor: pointer; font-weight: 600; }}
  table {{ border-collapse: collapse; margin-top: 10px; width: 100%; font-size: 14px; }}
  td, th {{ text-align: left; padding: 6px 8px; border-top: 1px solid #eee; vertical-align: top; }}
  .nota {{ font-size: 13px; color: var(--suave); }}
</style></head>
<body><main>
<h1>{titulo}</h1>
<p class="bajada">{bajada}</p>
{voces}
<details><summary>Ver qué es cada letra (después de elegir)</summary>
<table><tr><th>Letra</th><th>Voz</th><th>Cómo se hizo</th></tr>{clave}</table>
<p class="nota">{nota}</p>
</details>
</main></body></html>
"""


def prueba_voz(proveedor: str | None = None, slug: str = "as-de-guia", aviso=print) -> Path:
    """Arma revision/voz/index.html. `proveedor` cambia el de las voces de prueba («falso» sirve
    para ver la página sin la tarjeta)."""
    from dataclasses import replace

    from . import sonoridad as so
    from . import voz as V
    destino = REVISION / "voz"
    textos = textos_prueba(slug)
    voces = [replace(v, proveedor=proveedor) if proveedor else v for v in V.VOCES_PRUEBA]
    pedidos = [(t, v) for v in voces for _, t in textos]
    locs = V.decir(pedidos, aviso=aviso)
    orden = list(range(len(voces)))
    random.Random(431).shuffle(orden)
    letras = "ABCDEFGH"
    bloques, filas, resumen = [], [], []
    for i, k in enumerate(orden):
        v = voces[k]
        letra = letras[i]
        clips = []
        for j, (nombre, texto) in enumerate(textos):
            L = locs[k * len(textos) + j]
            antes = so.lufs(L.audio, V.SR)
            x = so.limitar_pico(so.a_lufs(L.audio, V.SR, NIVEL_VOZ), V.SR, TECHO)
            archivo = f"voz-{letra}-{j + 1}.wav"
            _wav16(destino / archivo, x, V.SR)
            silabas = sum(V.silabas(p.dicha) for p in L.palabras)
            habla = (L.palabras[-1].fin - L.palabras[0].inicio) if L.palabras else 1.0
            resumen.append(f"  {letra} {nombre:9s} {L.segundos:5.1f} s, {silabas / max(habla, 0.1):4.1f} sílabas/s, "
                           f"{antes:6.1f} LUFS antes, pico {so.pico_real(x):5.1f} dBTP")
            clips.append(f'<div class="clip"><b>{html.escape(nombre)}</b>'
                         f'<audio controls preload="none" src="{archivo}"></audio>'
                         f'<div class="texto">{html.escape(texto)}</div></div>')
        bloques.append(f'<section class="voz"><h2>Voz <span>{letra}</span></h2>{"".join(clips)}</section>')
        como = (f"{html.escape(v.proveedor)}: "
                + (f"VoiceDesign con la descripción «{html.escape(v.descripcion)}», semilla {v.semilla}, "
                   "y Base la clona en cada texto" if v.descripcion else "clonada de una muestra"))
        filas.append(f"<tr><td><b>{letra}</b></td><td>{html.escape(v.etiqueta or v.nombre)}</td><td>{como}</td></tr>")
    nota = (f"Todas las locuciones están a {NIVEL_VOZ:.0f} LUFS y con el pico real bajo {TECHO:.0f} dBTP. "
            "Los textos salen de specs/" + slug + ".yaml. Proveedor: " + html.escape(proveedor or "qwen")
            + " (Qwen3-TTS 1.7B, Apache-2.0, en la tarjeta).")
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.html").write_text(PAGINA.format(
        titulo="Prueba de voz a ciegas: as de guía",
        bajada=("Escucha cada voz en los tres textos y elige la que se entiende mejor y suena más natural "
                "para enseñar un nudo. Las letras van en un orden al azar."),
        voces="\n".join(bloques), clave="".join(filas), nota=nota), encoding="utf-8")
    (destino / "clave.json").write_text(json.dumps(
        {letras[i]: {"voz": voces[k].nombre, "etiqueta": voces[k].etiqueta, "proveedor": voces[k].proveedor}
         for i, k in enumerate(orden)}, ensure_ascii=False, indent=1), encoding="utf-8")
    aviso("\n".join(resumen))
    return destino / "index.html"


# --------------------------------------------------------------------------
# La música
# --------------------------------------------------------------------------
# La línea de tiempo de la demo, en compases de cada canción; el golpe del nudo, en el segundo
# compás del cierre.
DEMO = (("apertura", 2), ("pasos", 4), ("verificacion", 2), ("errores", 2), ("aplicacion", 2), ("cierre", 2))
NOMBRES = {"apertura": "Apertura", "materiales": "Materiales", "pasos": "Paso a paso",
           "verificacion": "Cómo revisar", "errores": "Errores", "aplicacion": "En la práctica",
           "seguridad": "Seguridad", "cierre": "Cierre"}
COLORES = {"apertura": "#d1801a", "pasos": "#3d7dca", "verificacion": "#3a9b6e", "errores": "#c4473a",
           "aplicacion": "#8a5cc2", "seguridad": "#7a8696", "cierre": "#d1801a", "materiales": "#6b9bd1"}


def linea_demo(cancion, partes=DEMO):
    """Los capítulos de la demo en s, en compases enteros de la canción, y el golpe."""
    from .musica import Capitulo
    compas = cancion.compas * cancion.pulso
    caps, t = [], 0.0
    for nombre, n in partes:
        caps.append(Capitulo(nombre, round(t, 6), round(t + n * compas, 6)))
        t += n * compas
    golpe = caps[-1].inicio + compas if caps[-1].nombre == "cierre" else None
    return caps, golpe


def demo_con_voz(cancion, motivo: str, aviso=print):
    """La apertura y dos pasos dichos por la voz elegida, sobre la música, con los capítulos del
    largo de lo que dice la voz (en el pulso) y la música abajo mientras habla."""
    from . import musica as M
    from . import sonoridad as so
    from . import voz as V
    from .mezcla import bajo_la_voz
    textos = textos_prueba()
    locs = V.locuciones([t for _, t in textos], V.VOZ, aviso=aviso)
    P = cancion.pulso
    caps, t, entradas = [], 0.0, []
    for i, L in enumerate(locs):
        entrada = t + (P if i == 0 else 2 * P)
        entradas.append(entrada)
        fin = M.al_pulso(entrada + L.segundos + P, 0.0, P)
        if i == 0:
            caps.append(M.Capitulo("apertura", t, fin))
        elif caps[-1].nombre == "pasos":
            caps[-1] = M.Capitulo("pasos", caps[-1].inicio, fin)
        else:
            caps.append(M.Capitulo("pasos", t, fin))
        t = fin
    compas = cancion.compas * P
    caps.append(M.Capitulo("cierre", t, t + 2 * compas))
    mus = M.musica(caps, t + compas, cancion=cancion, motivo=motivo, aviso=aviso)
    n = len(mus.mezcla)
    voz = np.zeros(n)
    for e, L in zip(entradas, locs):
        k = int(round(e * M.SR))
        voz[k:k + len(L.audio)] += L.audio[:max(0, n - k)]
    voz = so.a_lufs(voz, M.SR, -16.0)
    mezcla = bajo_la_voz(mus.mezcla, voz, M.SR)
    return so.limitar_pico(so.a_lufs(mezcla, M.SR, -16.0), M.SR, -1.0), mus.capitulos


def _linea_html(caps, total: float) -> str:
    partes = []
    for c in caps:
        ancho = 100 * (c.fin - c.inicio) / total
        partes.append(f'<div class="cap" style="width:{ancho:.3f}%;background:{COLORES.get(c.nombre, "#888")}" '
                      f'title="{NOMBRES[c.nombre]}: {c.inicio:.1f} a {c.fin:.1f} s">{NOMBRES[c.nombre]}</div>')
    return "".join(partes)


PAGINA_MUSICA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prueba de música: las canciones</title>
<style>
  :root {{ color-scheme: light; --tinta: #16202f; --suave: #586273; --marca: #d1801a; --fondo: #f6f4ef; }}
  body {{ margin: 0; background: var(--fondo); color: var(--tinta);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 900px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; margin: 0 0 6px; }}
  h2 {{ font-size: 22px; margin: 28px 0 8px; }}
  .bajada {{ color: var(--suave); margin: 0 0 16px; }}
  .demo {{ background: #fff; border-radius: 14px; padding: 16px 20px; margin: 0 0 14px;
           box-shadow: 0 2px 10px rgba(22, 32, 47, .06); }}
  .demo h3 {{ margin: 0 0 4px; font-size: 19px; }}
  .demo p {{ margin: 0 0 10px; color: var(--suave); font-size: 14px; }}
  audio {{ width: 100%; }}
  .linea {{ position: relative; display: flex; height: 28px; border-radius: 8px; overflow: hidden; margin-top: 8px; }}
  .cap {{ color: #fff; font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: center;
          white-space: nowrap; overflow: hidden; opacity: .55; cursor: pointer; }}
  .cap.ahora {{ opacity: 1; }}
  .cabeza {{ position: absolute; top: 0; bottom: 0; width: 2px; background: #16202f; left: 0; }}
</style></head>
<body><main>
<h1>Prueba de música: las canciones</h1>
<p class="bajada">Primero, el instrumento del motivo de la serie (la kalimba sonaba «tuc tuc tuc»): la apertura y el
cierre de «Fogata» con cada uno. Después, las cinco canciones sobre la misma línea de tiempo, sin voz y con la voz
elegida. La barra marca en qué capítulo vas; toca un capítulo para ir ahí.</p>
{demos}
</main>
<script>
document.querySelectorAll('.demo').forEach(d => {{
  const a = d.querySelector('audio'), caps = [...d.querySelectorAll('.cap')], cab = d.querySelector('.cabeza');
  if (!cab) return;
  const tiempos = JSON.parse(d.dataset.caps), total = parseFloat(d.dataset.total);
  const pinta = () => {{
    cab.style.left = (100 * a.currentTime / total) + '%';
    caps.forEach((c, i) => c.classList.toggle('ahora', a.currentTime >= tiempos[i][0] && a.currentTime < tiempos[i][1]));
  }};
  a.addEventListener('timeupdate', pinta); a.addEventListener('seeked', pinta);
  caps.forEach((c, i) => c.addEventListener('click', () => {{ a.currentTime = tiempos[i][0]; a.play(); }}));
}});
</script>
</body></html>
"""


def _demo_html(titulo: str, nota: str, archivo: str, caps) -> str:
    total = caps[-1].fin
    tiempos = json.dumps([[c.inicio, c.fin] for c in caps])
    return (f'<section class="demo" data-caps=\'{tiempos}\' data-total="{total}"><h3>{html.escape(titulo)}</h3>'
            f'<p>{html.escape(nota)}</p><audio controls preload="none" src="{archivo}"></audio>'
            f'<div class="linea">{_linea_html(caps, total)}<div class="cabeza"></div></div></section>')


def prueba_musica(cancion: str | None = None, aviso=print) -> Path:
    """Arma revision/musica/index.html: la apertura y el cierre de «Fogata» con cada instrumento
    posible del motivo, y cada canción sobre la línea de tiempo de la demo, sin voz y con la voz
    elegida (si su entorno de voz está). Deja también un JSON por demo con sus capítulos."""
    from . import musica as M
    destino = REVISION / "musica"
    destino.mkdir(parents=True, exist_ok=True)
    for viejo in destino.glob("*"):
        viejo.unlink()
    bloques, indice = ["<h2>El instrumento del motivo</h2>"], {"motivo": {}, "canciones": {}}

    def guardar(nombre: str, x, caps):
        _wav16(destino / f"{nombre}.wav", x, M.SR)
        (destino / f"{nombre}.json").write_text(json.dumps([[c.nombre, c.inicio, c.fin] for c in caps]),
                                                encoding="utf-8")
        return f"{nombre}.wav"

    fogata = M.CANCIONES["fogata"]
    caps_m, golpe_m = linea_demo(fogata, (("apertura", 2), ("cierre", 2)))
    for nombre, instrumento in M.MOTIVOS_PRUEBA.items():
        aviso(f"  motivo: {nombre}")
        mus = M.musica(caps_m, golpe_m, cancion=fogata, motivo=instrumento, aviso=aviso)
        sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
        clave = "motivo-" + re.sub(r"[^a-z]+", "-", sin_tildes.lower()).strip("-")
        archivo = guardar(clave, mus.mezcla, mus.capitulos)
        bloques.append(_demo_html(nombre.capitalize(), "La apertura y el cierre de «Fogata», con el golpe.",
                                  archivo, mus.capitulos))
        indice["motivo"][nombre] = clave
    bloques.append("<h2>Las cinco canciones</h2>")
    for clave, can in M.CANCIONES.items():
        if cancion not in (None, clave):
            continue
        aviso(f"  canción: {can.nombre}")
        caps, golpe = linea_demo(can)
        mus = M.musica(caps, golpe, cancion=can, aviso=aviso)
        archivo = guardar(f"cancion-{clave}", mus.mezcla, mus.capitulos)
        bloques.append(_demo_html(can.nombre, can.descripcion, archivo, mus.capitulos))
        indice["canciones"][clave] = {"nombre": can.nombre, "descripcion": can.descripcion,
                                      "archivos": [f"cancion-{clave}"]}
        try:
            mezcla, caps_v = demo_con_voz(can, M.MOTIVO, aviso=aviso)
        except Exception as e:      # sin el entorno de la voz, la página va sin estas demos
            aviso(f"  sin la demo con voz: {e}")
            continue
        archivo = guardar(f"cancion-{clave}-con-voz", mezcla, caps_v)
        bloques.append(_demo_html(f"{can.nombre}, con voz", "La apertura y dos pasos con la voz elegida; "
                                  "la música baja sola mientras habla.", archivo, caps_v))
        indice["canciones"][clave]["archivos"].append(f"cancion-{clave}-con-voz")
    (destino / "index.html").write_text(PAGINA_MUSICA.format(demos="\n".join(bloques)), encoding="utf-8")
    (destino / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino / "index.html"
