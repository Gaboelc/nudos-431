"""Las pruebas de escucha de T23: `prueba-voz`, `prueba-musica` y `prueba-mezcla`, en revision/
(fuera de git).

- `prueba_voz()`: la apertura y dos pasos del as de guía, dichos por cada voz de
  `voz.VOCES_PRUEBA`, todos a la misma sonoridad, en una página para escuchar a ciegas: las voces
  van con una letra, en un orden al azar con semilla fija, y la clave queda escondida al final.
- `prueba_musica()`: el instrumento del motivo de la serie (cada opción en la apertura y el cierre
  de «Fogata»; Gabriel eligió la celesta) y las cinco canciones sobre la misma línea de tiempo,
  sin voz y con la voz elegida.
- `prueba_mezcla()`: la previa de cada piloto (T18) con la pista de T23c pegada: su canción, el
  foley del motor, los soplidos, las tarjetas, el golpe y la voz de dos pasos.
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
<p class="bajada">Primero, las opciones del instrumento del motivo de la serie: la apertura y el cierre de «Fogata»
con cada una (Gabriel eligió la celesta el 26 nov). Después, las cinco canciones sobre la misma línea de tiempo, con
la celesta, sin voz y con la voz elegida. La barra marca en qué capítulo vas; toca un capítulo para ir ahí.</p>
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


# --------------------------------------------------------------------------
# La mezcla (T23c)
# --------------------------------------------------------------------------
PILOTOS_MEZCLA = ("as-de-guia", "amarre-cuadrado")


def capitulos_t18(cuadros, fps: float):
    """Los capítulos de la música sobre la línea de tiempo de hoy (T18): la apertura hasta la
    primera tarjeta, el paso a paso hasta el apretado y el cierre. Los de verdad los pone T22."""
    from .musica import Capitulo
    dur = len(cuadros) / fps
    cambios = [k for k in range(1, len(cuadros)) if cuadros[k].titulo != cuadros[k - 1].titulo]
    if not cambios:
        return [Capitulo("pasos", 0.0, dur)]
    t1 = cambios[0] / fps
    tc = next((k / fps for k in cambios if cuadros[k].titulo == 0), dur)
    caps = [Capitulo("apertura", 0.0, t1), Capitulo("pasos", t1, tc)]
    if tc < dur:
        caps.append(Capitulo("cierre", tc, dur))
    return caps


def _medidas_aac(ruta: Path) -> tuple[float, float]:
    """La sonoridad y el pico real del audio de un video, ya en AAC."""
    import subprocess
    import tempfile

    from scipy.io import wavfile

    from . import sonoridad as so
    with tempfile.TemporaryDirectory(prefix="nudos-aac-") as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(ruta), "-vn", "-c:a",
                        "pcm_f32le", str(wav)], check=True, timeout=300)
        sr, x = wavfile.read(wav)
    return so.lufs(x, sr), so.pico_real(x, sr)


PAGINA_MEZCLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prueba de la mezcla</title>
<style>
  :root {{ color-scheme: light; --tinta: #16202f; --suave: #586273; --fondo: #f6f4ef; }}
  body {{ margin: 0; background: var(--fondo); color: var(--tinta);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 1000px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; margin: 0 0 6px; }}
  .bajada {{ color: var(--suave); margin: 0 0 16px; }}
  .demo {{ background: #fff; border-radius: 14px; padding: 16px 20px; margin: 0 0 16px;
           box-shadow: 0 2px 10px rgba(22, 32, 47, .06); }}
  .demo h2 {{ margin: 0 0 4px; font-size: 20px; }}
  .demo p {{ margin: 0 0 10px; color: var(--suave); font-size: 14px; }}
  video {{ width: 100%; border-radius: 8px; background: #000; }}
</style></head>
<body><main>
<h1>Prueba de la mezcla</h1>
<p class="bajada">La previa de cada piloto con la pista nueva: su canción, el foley que sale del motor (el roce según
la presión y el deslizamiento, el «tac» en la mesa, el crujido al apretar), los soplidos de la cámara y de las
tarjetas, el clic de cada tarjeta y el golpe, cada cosa donde se ve, en una sala chica. La voz dice los pasos 2 y 4
donde aparecen sus tarjetas: el tiempo de cada parte lo pone T22. Mejor con audífonos.</p>
{demos}
</main></body></html>
"""


class Previa:
    """La previa de un nudo (T18, 960 × 540): sus cuadros y su video, para pegarle una pista."""

    def __init__(self, m, aviso=print):
        from . import video as VI
        from .prueba_atar import mallas_anfitrion
        self.m, self.slug = m, m.spec.slug
        self.fps = VI.FORMATOS["previa"]["fps"]
        tramos, _ = VI.atar(m)
        self.cuadros = VI.cuadros_de(m, tramos, "previa")
        self.video = VI.carpeta_videos(self.slug) / f"{self.slug}-previa.mp4"
        if not self.video.exists() or VI.cuadros_del_video(self.video) != len(self.cuadros):
            aviso(f"  {self.slug}: dibujando la previa")
            VI.video(m, previa=True, aviso=aviso)
        self.h = m.pasos[-1].h
        self.mallas = mallas_anfitrion(m)
        self.capitulos = capitulos_t18(self.cuadros, self.fps)

    def en_las_tarjetas(self, locs, pasos=(2, 4)) -> list:
        """Cada locución, 0,25 s después de que aparece la tarjeta de su paso."""
        from . import mezcla as MZ
        c = self.cuadros
        tarjeta = {c[k].titulo: k / self.fps for k in range(1, len(c)) if c[k].titulo != c[k - 1].titulo}
        return [MZ.Dicho(tarjeta[n] + 0.25, loc) for n, loc in zip(pasos, locs)]

    def pista(self, dichos=(), aviso=print):
        from . import mezcla as MZ
        return MZ.pista_de_cuadros(self.cuadros, self.fps, self.h, self.mallas, formato="previa",
                                   capitulos=self.capitulos, slug=self.slug, dichos=dichos, aviso=aviso)


def _voz_sobre_musica(p) -> list[float]:
    """Por cada frase de la voz, cuántos dB queda sobre lo más fuerte de la música."""
    from . import mezcla as MZ
    from . import sonoridad as so
    out = []
    for a, b in p.frases:
        i, j = int(a * MZ.SR), int(b * MZ.SR)
        _, mc = so.corto(p.buses["musica"][i:j], MZ.SR, 0.4, 0.05)
        if len(mc):
            out.append(round(so.lufs(p.buses["voz"][i:j], MZ.SR) - float(mc.max()), 1))
    return out


def prueba_mezcla(slugs=PILOTOS_MEZCLA, voz: bool = True, aviso=print) -> Path:
    """Arma revision/sonido/index.html con la previa de cada piloto (960 × 540) y la pista de
    T23c pegada. Si la previa no está o tiene otros cuadros, la dibuja (Blender). Deja
    informe.json con las medidas: la sonoridad y el pico antes y después del AAC, la voz sobre la
    música en cada frase y cuántos sonidos de cada tipo."""
    import os

    from . import mezcla as MZ
    from . import video as VI
    from . import voz as V
    os.environ["NUDOS_MOTOR"] = "1"
    destino = REVISION / "sonido"
    destino.mkdir(parents=True, exist_ok=True)
    modelos = VI.construir(list(slugs))
    bloques, informe = [], {}
    for slug in slugs:
        m = modelos[slug]
        pv = Previa(m, aviso)
        dichos = []
        if voz and len(m.spec.pasos) >= 4:
            textos = dict(textos_prueba(slug))
            dichos = pv.en_las_tarjetas(V.locuciones([textos["Paso 2"], textos["Paso 4"]], V.VOZ, aviso=aviso))
        p = pv.pista(dichos, aviso)
        nombre = f"{slug}-sonido"
        salida = destino / f"{nombre}.mp4"
        MZ.pegar(pv.video, p, salida)
        lufs_aac, pico_aac = _medidas_aac(salida)
        separacion = _voz_sobre_musica(p)
        cuenta: dict[str, int] = {}
        for s in p.sonidos:
            cuenta[s.tipo] = cuenta.get(s.tipo, 0) + 1
        informe[nombre] = {"segundos": round(p.segundos, 1), "cancion": p.musica.cancion if p.musica else None,
                           "lufs": round(p.lufs, 2), "pico_dbtp": round(p.pico, 2),
                           "lufs_aac": round(lufs_aac, 2), "pico_aac_dbtp": round(pico_aac, 2),
                           "voz_sobre_musica_db": separacion, "sonidos": cuenta}
        aviso(f"  {nombre}: {p.lufs:.1f} LUFS, {p.pico:.1f} dBTP (en AAC, {lufs_aac:.1f} y {pico_aac:.1f}); "
              f"la voz, {min(separacion, default=float('nan')):.1f} dB sobre la música")
        titulo = m.spec.nombre
        cancion = _nombre_cancion(p.musica.cancion) if p.musica else "sin música"
        texto = (f"Canción «{cancion}». {p.lufs:.1f} LUFS y {p.pico:.1f} dBTP "
                 f"({lufs_aac:.1f} y {pico_aac:.1f} ya en AAC).")
        bloques.append(f'<section class="demo"><h2>{html.escape(titulo)}</h2><p>{html.escape(texto)}</p>'
                       f'<video controls preload="metadata" src="{salida.name}"></video></section>')
    (destino / "index.html").write_text(PAGINA_MEZCLA.format(demos="\n".join(bloques)), encoding="utf-8")
    (destino / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino / "index.html"


def _nombre_cancion(clave: str) -> str:
    """El nombre de una canción, desde su clave."""
    from .musica import CANCIONES
    return CANCIONES[clave].nombre if clave in CANCIONES else clave


# --------------------------------------------------------------------------
# La voz de Gabriel
# --------------------------------------------------------------------------
PAGINA_PROPIA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prueba con tu voz</title>
<style>
  :root {{ color-scheme: light; --tinta: #16202f; --suave: #586273; --fondo: #f6f4ef; --marca: #d1801a; }}
  body {{ margin: 0; background: var(--fondo); color: var(--tinta);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 1000px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; margin: 0 0 6px; }}
  h2 {{ font-size: 21px; margin: 28px 0 6px; }}
  .bajada, .nota {{ color: var(--suave); margin: 0 0 14px; }}
  .demo {{ background: #fff; border-radius: 14px; padding: 14px 18px; margin: 0 0 14px;
           box-shadow: 0 2px 10px rgba(22, 32, 47, .06); }}
  .clips {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }}
  .clip b {{ display: block; font-size: 14px; margin-bottom: 2px; }}
  .texto {{ font-size: 14px; color: var(--suave); margin-top: 8px; }}
  audio {{ width: 100%; }}
  video {{ width: 100%; border-radius: 8px; background: #000; }}
  details {{ margin: 0 0 10px; }}
  summary {{ cursor: pointer; font-weight: 600; }}
</style></head>
<body><main>
<h1>Prueba con tu voz</h1>
<p class="bajada">Tu voz grabada y tu voz clonada con Qwen3-TTS, junto a la voz D que elegiste. Las voces
sueltas están todas a {nivel:.0f} LUFS. Mejor con audífonos.</p>
{cuerpo}
</main></body></html>
"""


def _slug_de(nombre: str) -> str | None:
    """El nudo de una grabación por el nombre de su archivo («as de guia» → as-de-guia, «nudo
    simple» → simple), o None si no es ninguno."""
    s = "".join(c for c in unicodedata.normalize("NFD", nombre.casefold()) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    for c in (s, s.removeprefix("nudo-")):
        if c and (RAIZ / "specs" / f"{c}.yaml").exists():
            return c
    return None


def _m4a(ruta: Path, x, sr: int, kbps: int = 192) -> None:
    """Un audio (mono o estéreo) en AAC, para la página y el celular."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix="nudos-m4a-") as tmp:
        wav = Path(tmp) / "a.wav"
        _wav16(wav, x, sr)
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "aac",
                        "-b:a", f"{kbps}k", str(ruta)], check=True, timeout=300)


def _ritmo(palabras) -> float:
    """Sílabas por segundo, con las pausas de más de 0,3 s contadas como de 0,3."""
    from . import voz as V
    if not palabras:
        return 0.0
    habla = sum(p.fin - p.inicio for p in palabras)
    habla += sum(min(b.inicio - a.fin, 0.3) for a, b in zip(palabras, palabras[1:]) if b.inicio > a.fin)
    return sum(V.silabas(p.texto) for p in palabras) / max(habla, 0.1)


def _clip(destino: Path, archivo: str, x, etiqueta: str) -> str:
    """Un audio suelto a NIVEL_VOZ, con su reproductor."""
    from . import sonoridad as so
    from . import voz as V
    _m4a(destino / archivo, so.limitar_pico(so.a_lufs(x, V.SR, NIVEL_VOZ), V.SR, TECHO), V.SR)
    return (f'<div class="clip"><b>{html.escape(etiqueta)}</b>'
            f'<audio controls preload="none" src="{archivo}"></audio></div>')


def _hasta_unos(palabras, segundos: float, pausa: float = 0.3) -> int:
    """Cuántas palabras caben en unos `segundos` desde la primera, cortando en una pausa."""
    cortes = [k + 1 for k in range(len(palabras)) if palabras[k].fin - palabras[0].inicio <= segundos
              and (k + 1 == len(palabras) or palabras[k + 1].inicio - palabras[k].fin >= pausa)]
    return max(cortes or [len(palabras)])


def prueba_voz_propia(carpeta, slug: str = "as-de-guia", aviso=print) -> Path:
    """Arma revision/voz-propia/index.html con la voz de Gabriel junto a la voz D (T23).

    De sus grabaciones (`carpeta`, fuera de git), cada una limpia y transcrita, clona su voz con
    Qwen3-TTS desde el mejor tramo limpio de todas (`voz.tramos_limpios`) de dos maneras: desde la
    grabación limpia, y como de estudio, con la muestra y cada locución pasadas por Sidon
    (`voz.restaurar`). Compara un tramo de otras dos grabaciones dicho por él (también con Sidon),
    por cada voz clonada y por la voz D; los textos de `prueba-voz`; su lectura de `slug` con la
    música, y la previa de `slug` con los pasos 2 y 4 en cada voz. Deja informe.json con lo
    medido."""
    import os

    from . import mezcla as MZ
    from . import musica as M
    from . import sonoridad as so
    from . import video as VI
    from . import voz as V
    destino = REVISION / "voz-propia"
    destino.mkdir(parents=True, exist_ok=True)
    rutas = sorted(p for p in Path(carpeta).iterdir() if p.suffix.lower() in V.EXTENSIONES)
    if not rutas:
        raise ValueError(f"no hay grabaciones en {carpeta}")
    aviso(f"  {len(rutas)} grabaciones en {carpeta}")
    limpias = [V.limpiar(V.leer_grabacion(r)) for r in rutas]
    trans = V.transcribir(limpias, aviso=aviso)
    slugs = [_slug_de(r.stem) for r in rutas]
    informe: dict = {"grabaciones": {}}
    for r, x, t in zip(rutas, limpias, trans):
        informe["grabaciones"][r.name] = {"segundos": round(len(x) / V.SR, 1), "lufs": round(so.lufs(x, V.SR), 1),
                                          "tiempos": t.tiempos, "silabas_por_s": round(_ritmo(t.palabras), 2),
                                          "texto": t.texto}

    def a_nivel(x):
        # A NIVEL_VOZ y bajo el techo: el AAC del celular decodifica con picos sobre 0 dBFS, y el
        # WAV de 16 bits los cortaría.
        return so.limitar_pico(so.a_lufs(x, V.SR, NIVEL_VOZ), V.SR, TECHO)

    # La muestra para clonar: el mejor tramo limpio de todas las grabaciones, que diga palabra por
    # palabra lo que está en la especificación de su nudo o en su guion hablado (si no hay ninguno,
    # sin esa condición).
    def fuente(slug):
        if not slug:
            return None
        textos = [RAIZ / "specs" / f"{slug}.yaml", GUIONES / f"{slug}.yaml"]
        return "\n".join(r.read_text(encoding="utf-8") for r in textos if r.exists())
    fuentes = [fuente(s) for s in slugs]

    def limpios(**kw):
        con = [(p, i, a, b) for i, t in enumerate(trans) for p, a, b in V.tramos_limpios(t, fuente=fuentes[i], **kw)]
        return con or [(p, i, a, b) for i, t in enumerate(trans) for p, a, b in V.tramos_limpios(t, **kw)]
    tramos = limpios()
    if not tramos:
        raise ValueError("ninguna grabación tiene un tramo limpio de 8 a 14 s para clonar la voz")
    _, i0, a0, b0 = max(tramos)
    w0 = trans[i0].palabras
    texto_muestra = " ".join(p.texto for p in w0[a0:b0])
    muestra = a_nivel(V.recorte(limpias[i0], w0[a0].inicio, w0[b0 - 1].fin))
    ruta_muestra = destino / "muestra.wav"
    _wav16(ruta_muestra, muestra, V.SR)
    # La misma muestra como de estudio: Sidon le quita el eco del cuarto y el sonido del celular.
    muestra_estudio = a_nivel(V.restaurar([muestra], aviso=aviso)[0])
    ruta_estudio = destino / "muestra-estudio.wav"
    _wav16(ruta_estudio, muestra_estudio, V.SR)
    voces = (("voz-d", "Voz D", V.VOZ_D),
             ("clonada", "Clonada de tu grabación",
              V.Voz("gabriel", referencia=str(ruta_muestra.resolve()), texto_referencia=texto_muestra,
                    etiqueta="Gabriel, clonada de su grabación", limpiar=True)),
             ("estudio", "Clonada de estudio",
              V.Voz("gabriel-estudio", referencia=str(ruta_estudio.resolve()), texto_referencia=texto_muestra,
                    etiqueta="Gabriel, clonada de su muestra restaurada, como de estudio", restaurar=True)))
    informe["muestra"] = {"grabacion": rutas[i0].name, "desde": w0[a0].inicio, "hasta": w0[b0 - 1].fin,
                          "texto": texto_muestra}

    # La misma frase: un tramo limpio de otras dos grabaciones.
    frases, usadas = [], {i0}
    for _, i, a, b in sorted(limpios(largo=(5.0, 10.0), ideal=8.0), reverse=True):
        if i not in usadas and len(frases) < 2:
            usadas.add(i)
            frases.append((i, a, b))
    textos = textos_prueba(slug)
    dichas = [" ".join(p.texto for p in trans[i].palabras[a:b]) for i, a, b in frases]
    todos = [t for _, t in textos] + dichas
    locs = V.decir([(t, v) for _, _, v in voces for t in todos], aviso=aviso)
    de = {clave: locs[j * len(todos):(j + 1) * len(todos)] for j, (clave, _, _) in enumerate(voces)}
    informe["silabas_por_s"] = {etiqueta: round(float(np.mean([_ritmo(L.palabras) for L in de[clave]])), 2)
                                for clave, etiqueta, _ in voces}
    reales = [V.recorte(limpias[i], trans[i].palabras[a].inicio, trans[i].palabras[b - 1].fin) for i, a, b in frases]
    reales_estudio = V.restaurar(reales, aviso=aviso)

    cuerpo = [f'<h2>La muestra que se clonó</h2><section class="demo"><div class="clips">'
              f'{_clip(destino, "muestra.m4a", muestra, "De tu grabación: " + rutas[i0].stem)}'
              f'{_clip(destino, "muestra-estudio.m4a", muestra_estudio, "La misma, con Sidon")}'
              f'</div><div class="texto">{html.escape(texto_muestra)}</div></section>',
              '<h2>La misma frase</h2><p class="nota">Un tramo de otra grabación: como lo dijiste, con Sidon, '
              'dicho por cada voz clonada y por la voz D.</p>']
    for k, (i, a, b) in enumerate(frases):
        clips = (_clip(destino, f"frase-{k + 1}-tu-voz.m4a", reales[k], "Tu grabación")
                 + _clip(destino, f"frase-{k + 1}-tu-voz-estudio.m4a", reales_estudio[k], "Tu grabación con Sidon")
                 + "".join(_clip(destino, f"frase-{k + 1}-{clave}.m4a", de[clave][len(textos) + k].audio, etiqueta)
                           for clave, etiqueta, _ in voces[1:] + voces[:1]))
        cuerpo.append(f'<section class="demo"><div class="clips">{clips}</div>'
                      f'<div class="texto">{html.escape(rutas[i].stem)}: {html.escape(dichas[k])}</div></section>')
    cuerpo.append('<h2>Los textos de la prueba de voz</h2><p class="nota">Los mismos de la prueba a ciegas: '
                  'la apertura y los pasos 2 y 4.</p>')
    for k, (nombre, texto) in enumerate(textos):
        clips = "".join(_clip(destino, f"prueba-{k + 1}-{clave}.m4a", de[clave][k].audio, etiqueta)
                        for clave, etiqueta, _ in voces)
        cuerpo.append(f'<section class="demo"><b>{html.escape(nombre)}</b><div class="clips">{clips}</div>'
                      f'<div class="texto">{html.escape(texto)}</div></section>')

    # Su lectura con la música: lo que leyó de `slug` (o la grabación de la muestra), hasta unos
    # 30 s, cortada en una pausa; limpia y con Sidon.
    i = slugs.index(slug) if slug in slugs else i0
    w = trans[i].palabras
    if w and trans[i].tiempos == "alineados":
        b = _hasta_unos(w, 30.0)
        x = V.recorte(limpias[i], w[0].inicio, w[b - 1].fin)
        corrida = max(0.0, w[0].inicio - 0.12)
        palabras = [V.Palabra(p.texto, p.dicha, p.inicio - corrida, p.fin - corrida) for p in w[:b]]
        clips = []
        for archivo, etiqueta, audio in (("lectura-con-musica.m4a", "Tu grabación", x),
                                         ("lectura-con-musica-estudio.m4a", "Con Sidon",
                                          V.restaurar([x], aviso=aviso)[0])):
            loc = V.locucion_grabada(audio, palabras, voz="gabriel")
            dur = loc.segundos + 4.0
            p = MZ.pista(dur, capitulos=[M.Capitulo("apertura", 0.0, 2.5), M.Capitulo("pasos", 2.5, dur)],
                         slug=slug, dichos=[MZ.Dicho(2.0, loc)], aviso=aviso)
            _m4a(destino / archivo, p.audio, MZ.SR, kbps=256)
            informe[archivo] = {"segundos": round(dur, 1), "lufs": round(p.lufs, 2), "pico_dbtp": round(p.pico, 2),
                                "voz_sobre_musica_db": _voz_sobre_musica(p)}
            clips.append(f'<div class="clip"><b>{etiqueta}</b><audio controls preload="none" src="{archivo}"></audio></div>')
        cuerpo.append('<h2>Tu lectura con la música</h2><p class="nota">Tu grabación con la canción del nudo '
                      'debajo, como en el video: la música baja sola mientras hablas.</p>'
                      f'<section class="demo"><div class="clips">{"".join(clips)}</div>'
                      f'<div class="texto">{html.escape(" ".join(q.texto for q in w[:b]))}</div></section>')

    # La previa del nudo, con los pasos 2 y 4 en cada voz.
    os.environ["NUDOS_MOTOR"] = "1"
    pv = Previa(VI.construir([slug])[slug], aviso)
    videos = []
    for clave, etiqueta, _ in voces:
        p = pv.pista(pv.en_las_tarjetas([de[clave][1], de[clave][2]]), aviso)
        salida = destino / f"{slug}-{clave}.mp4"
        MZ.pegar(pv.video, p, salida)
        informe[salida.name] = {"lufs": round(p.lufs, 2), "pico_dbtp": round(p.pico, 2),
                                "voz_sobre_musica_db": _voz_sobre_musica(p)}
        videos.append(f'<div class="clip"><b>{etiqueta}</b><video controls preload="metadata" '
                      f'src="{salida.name}"></video></div>')
    cuerpo.append('<h2>En el video</h2><p class="nota">La previa con la mezcla nueva: los pasos 2 y 4 donde '
                  'aparecen sus tarjetas.</p><section class="demo"><div class="clips">' + "".join(videos)
                  + '</div></section>')

    # Las grabaciones enteras, limpias, con lo que entendió el reconocimiento de voz.
    filas = []
    for k, (r, x, t) in enumerate(zip(rutas, limpias, trans)):
        archivo = f"grabacion-{k + 1}.m4a"
        _m4a(destino / archivo, a_nivel(x), V.SR, kbps=128)
        filas.append(f'<details><summary>{html.escape(r.stem)} ({len(x) / V.SR:.0f} s)</summary>'
                     f'<audio controls preload="none" src="{archivo}"></audio>'
                     f'<div class="texto">{html.escape(t.texto)}</div></details>')
    cuerpo.append('<h2>Tus grabaciones, limpias y transcritas</h2><p class="nota">Lo que escribió Qwen3-ASR: '
                  'es lo que usarían los subtítulos.</p><section class="demo">' + "".join(filas) + '</section>')
    (destino / "index.html").write_text(PAGINA_PROPIA.format(nivel=NIVEL_VOZ, cuerpo="\n".join(cuerpo)),
                                        encoding="utf-8")
    (destino / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino / "index.html"


# --------------------------------------------------------------------------
# El guion hablado (borrador para T22a)
# --------------------------------------------------------------------------
GUIONES = RAIZ / "config" / "guion"
HUECO_PASO = 1.8           # s entre el fin de un paso dicho y el siguiente: lo que tardaría el movimiento
HUECO = 1.0                # s entre la apertura y el primer paso, y antes del cierre

# Lo que Gabriel no diría (27 nov): diminutivos y «así», que no van con su manera de hablar. Los
# puntos suspensivos tampoco: la voz clonada los dice estirando la palabra de antes («deeel»).
PALABRAS_EVITAR = ("así", "chiquito", "chiquitito", "pequeñito", "pequeñita", "cortito", "cortita", "poquito",
                   "poquita", "ratito", "ahorita", "despacito", "rapidito", "facilito", "tantito", "bonito")


def guion_hablado(slug: str) -> dict:
    """El guion hablado de un nudo (config/guion/<slug>.yaml): `apertura`, un texto por paso
    (`pasos`), `cierre` y, si hace falta, `seguridad`. Falla si no tiene un texto por cada paso de
    la especificación, si usa términos de sección o si no sigue el estilo (`estilo_del_guion`)."""
    import yaml

    from .ficha import terminos_encontrados
    from .spec import cargar
    ruta = GUIONES / f"{slug}.yaml"
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    sobran = set(datos) - {"apertura", "pasos", "cierre", "seguridad"}
    if sobran:
        raise ValueError(f"{ruta.name}: campos desconocidos: {', '.join(sorted(sobran))}")
    pasos = [" ".join(str(t).split()) for t in datos.get("pasos") or []]
    total = len(cargar(slug).pasos)
    if len(pasos) != total:
        raise ValueError(f"{ruta.name}: tiene {len(pasos)} pasos y la especificación {total}")
    guion = {"apertura": " ".join(str(datos.get("apertura") or "").split()), "pasos": pasos,
             "cierre": " ".join(str(datos.get("cierre") or "").split()),
             "seguridad": " ".join(str(datos.get("seguridad") or "").split())}
    malos = terminos_encontrados(" ".join([guion["apertura"], *pasos, guion["cierre"], guion["seguridad"]]))
    if malos:
        raise ValueError(f"{ruta.name}: usa términos de sección: {', '.join(malos)}")
    estilo = estilo_del_guion(" ".join([guion["apertura"], *pasos, guion["cierre"], guion["seguridad"]]))
    if estilo:
        raise ValueError(f"{ruta.name}: {'; '.join(estilo)}")
    return guion


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


def lineas_de_la_ficha(slug: str) -> list[tuple[str, str]]:
    """Lo que diría la voz con el texto de la ficha, como hasta ahora: el nombre y los usos, «Paso N
    de M», el título y el texto de cada paso, y la seguridad o la primera precaución."""
    from .spec import cargar
    spec = cargar(slug)
    total = len(spec.pasos)
    out = [("apertura", f"{_punto(spec.nombre)} {_oracion(spec.usos or '')}")]
    out += [("pasos", f"Paso {n} de {total}. {_punto(p.titulo)} {' '.join(p.texto.split())}")
            for n, p in enumerate(spec.pasos, 1)]
    aviso = " ".join((getattr(spec, "seguridad", "") or "").split()) or next(iter(spec.precauciones or ()), "")
    if aviso:
        out.append(("seguridad", aviso))
    return out


def lineas_del_guion(slug: str) -> list[tuple[str, str]]:
    """El guion hablado en el orden de los capítulos de T22: la apertura, los pasos, la seguridad y
    el cierre, que termina con el nudo que sigue (para la pantalla final de YouTube)."""
    g = guion_hablado(slug)
    out = [("apertura", g["apertura"])] + [("pasos", t) for t in g["pasos"]]
    out += [(cap, g[cap]) for cap in ("seguridad", "cierre") if g[cap]]
    return out


def narracion(lineas: list[tuple[str, str]], slug: str, voz=None, aviso=print, instrumentos=None,
              alineador=None, revisar=None):
    """La pista de un video entero hecha solo de voz, como la armaría T22 («la voz manda el
    tiempo»): cada locución después de la anterior, con HUECO_PASO entre pasos para el movimiento;
    la tarjeta de cada paso 0,25 s antes de su voz, el golpe al terminar los pasos (el nudo
    apretado), y la canción del nudo con sus capítulos. Una locución que titubea se vuelve a decir
    (`voz.locuciones_sin_titubeos`). Da (pista, locuciones)."""
    from . import foley as F
    from . import mezcla as MZ
    from . import musica as M
    from . import voz as V
    locs = V.locuciones_sin_titubeos([t for _, t in lineas], voz or V.VOZ, aviso=aviso, alineador=alineador,
                                     revisar=revisar)
    t, dichos, eventos, inicios = 1.2, [], [], {}
    previo = None
    for (cap, _), loc in zip(lineas, locs):
        if previo is not None:
            t += HUECO_PASO if (cap == previo == "pasos") else HUECO
        if cap not in inicios:
            inicios[cap] = max(0.0, t - (0.6 if cap != "apertura" else t))
        if cap == "pasos":
            eventos.append(F.Evento("tarjeta", t - 0.25, -0.35))
        dichos.append(MZ.Dicho(t, loc))
        t += loc.segundos
        previo = cap
    dur = t + 2.5
    despues = [c for c in inicios if c not in ("apertura", "pasos")]
    golpe = inicios[despues[0]] if despues else None
    if golpe is not None:
        eventos.append(F.Evento("golpe", golpe, 0.0))
    nombres = list(inicios)
    capitulos = [M.Capitulo(c, inicios[c], inicios[nombres[k + 1]] if k + 1 < len(nombres) else dur)
                 for k, c in enumerate(nombres)]
    capitulos[0] = M.Capitulo(capitulos[0].nombre, 0.0, capitulos[0].fin)
    p = MZ.pista(dur, capitulos=capitulos, golpe=golpe, slug=slug, dichos=dichos, eventos=eventos,
                 instrumentos=instrumentos, aviso=aviso)
    return p, locs


def _parecido(dicho: str, oido: str) -> list[str]:
    """Las diferencias entre lo que se pidió decir y lo que entendió el reconocimiento, sin contar
    las letras que suenan igual (s, z y c; b y v; ll e y; la h), la puntuación, los espacios ni
    una vocal que se pierde al juntar dos palabras («rodea el» y «rodeal», «el as» y «las»)."""
    import difflib

    def normal(s: str) -> list[str]:
        s = "".join(c for c in unicodedata.normalize("NFD", s.casefold()) if unicodedata.category(c) != "Mn")
        s = re.sub(r"c(?=[ei])", "s", s).replace("z", "s").replace("v", "b").replace("ll", "y").replace("h", "")
        return re.findall(r"[a-zñ0-9]+", s)
    a, b = normal(dicho), normal(oido)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        # Lo que solo cambia en los espacios («revísalo» y «revisa lo») o en una vocal que se
        # pierde al juntar dos palabras en una no cuenta; dentro de una palabra («haz» y «hace») sí.
        x, y = "".join(a[i1:i2]), "".join(b[j1:j2])
        junta = (i2 - i1) != (j2 - j1) and _sinalefa(x, y)
        if op != "equal" and x != y and not junta:
            out.append(f"«{' '.join(a[i1:i2])}» → «{' '.join(b[j1:j2])}»")
    return out


def _sinalefa(x: str, y: str) -> bool:
    """Si una de las dos es la otra con una vocal menos («rodeael» y «rodeal»)."""
    largo, corto = (x, y) if len(x) > len(y) else (y, x)
    return len(largo) == len(corto) + 1 and any(
        largo[i] in "aeiou" and largo[:i] + largo[i + 1:] == corto for i in range(len(largo)))


def _se_entiende(textos: list[str], locs, aviso=print) -> list[bool]:
    """Si el reconocimiento de voz entiende en cada locución lo que se pidió decir (`_parecido`)."""
    from . import ia
    from . import voz as V
    tmp = REVISION / "guion" / "_oir"
    tmp.mkdir(parents=True, exist_ok=True)
    rutas = []
    for k, L in enumerate(locs):
        ruta = tmp / f"oir-{k}.wav"
        V._escribir_wav(ruta, L.audio, V.SR)
        rutas.append(ruta)
    try:
        res = ia.correr("qwen-asr", "transcribir.py", {"tareas": [
            {"audio": str(r.resolve()), "idioma": "Spanish", "contexto": V.CONTEXTO} for r in rutas]}, aviso=aviso)
    finally:
        for r in rutas:
            r.unlink(missing_ok=True)
    return [not _parecido(V.texto_dicho(L.palabras) if L.palabras else t, V.texto_dicho(V.para_decir(h["texto"])))
            for t, L, h in zip(textos, locs, res["hechas"])]


PAGINA_GUION = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>El guion hablado</title>
<style>
  :root {{ color-scheme: light; --tinta: #16202f; --suave: #586273; --fondo: #f6f4ef; }}
  body {{ margin: 0; background: var(--fondo); color: var(--tinta);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 900px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; margin: 0 0 6px; }}
  h2 {{ font-size: 21px; margin: 28px 0 6px; }}
  .bajada {{ color: var(--suave); margin: 0 0 14px; }}
  .demo {{ background: #fff; border-radius: 14px; padding: 14px 18px; margin: 0 0 14px;
           box-shadow: 0 2px 10px rgba(22, 32, 47, .06); }}
  .clips {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }}
  .clip b {{ display: block; font-size: 14px; margin-bottom: 2px; }}
  audio {{ width: 100%; }}
  ol {{ margin: 10px 0 0; padding-left: 22px; color: var(--suave); font-size: 15px; }}
  li {{ margin: 4px 0; }}
</style></head>
<body><main>
<h1>El guion hablado</h1>
<p class="bajada">La narración entera de cada piloto con tu voz, la música, el clic de cada tarjeta y el golpe
del final, como sonaría el video si la voz manda el tiempo. «Antes» es el texto de la ficha con «Paso número N de
M» en cada paso; «después», el guion nuevo.</p>
{cuerpo}
</main></body></html>
"""


def prueba_guion(slugs=PILOTOS_MEZCLA, aviso=print) -> Path:
    """Arma revision/guion/index.html: la narración entera de cada nudo con el texto de la ficha
    y con su guion hablado (config/guion/), con la música, las tarjetas y el golpe, y revisa con el
    reconocimiento de voz que cada locución del guion diga lo que tiene que decir. Deja
    informe.json con la duración y lo que no calzó."""
    from . import ia
    from . import mezcla as MZ
    from . import voz as V
    from .spec import cargar
    destino = REVISION / "guion"
    destino.mkdir(parents=True, exist_ok=True)
    informe, cuerpo = {}, []
    for slug in slugs:
        nombre = cargar(slug).nombre
        guion = lineas_del_guion(slug)
        partes = {}
        for clave, lineas in (("antes", lineas_de_la_ficha(slug)), ("despues", guion)):
            # El guion nuevo, con las tomas que el reconocimiento no entiende dichas otra vez.
            revisar = (lambda ts, ls: _se_entiende(ts, ls, aviso)) if clave == "despues" else None
            p, locs = narracion(lineas, slug, aviso=aviso, revisar=revisar)
            archivo = f"{slug}-{clave}.m4a"
            _m4a(destino / archivo, p.audio, MZ.SR, kbps=256)
            partes[clave] = (p, locs)
            informe[archivo] = {"segundos": round(p.segundos, 1), "lufs": round(p.lufs, 2),
                                "pico_dbtp": round(p.pico, 2),
                                "silabas_por_s": round(float(np.mean([_ritmo(L.palabras) for L in locs])), 2)}
            aviso(f"  {archivo}: {p.segundos:.0f} s, {p.lufs:.1f} LUFS")
        # Lo que entiende el reconocimiento de cada locución del guion.
        locs = partes["despues"][1]
        tmp = destino / "_oir"
        tmp.mkdir(exist_ok=True)
        rutas = []
        for k, L in enumerate(locs):
            ruta = tmp / f"{slug}-{k}.wav"
            V._escribir_wav(ruta, L.audio, V.SR)
            rutas.append(ruta)
        res = ia.correr("qwen-asr", "transcribir.py", {"tareas": [
            {"audio": str(r.resolve()), "idioma": "Spanish", "contexto": V.CONTEXTO} for r in rutas]}, aviso=aviso)
        diferencias = {}
        for (cap, texto), L, h in zip(guion, locs, res["hechas"]):
            # Los números que escriba el reconocimiento, en letras, como se pidieron.
            d = _parecido(V.texto_dicho(L.palabras) if L.palabras else texto, V.texto_dicho(V.para_decir(h["texto"])))
            if d:
                diferencias[texto[:60]] = d
        for r in rutas:
            r.unlink(missing_ok=True)
        informe[f"{slug}-diferencias"] = diferencias
        if diferencias:
            aviso(f"  {slug}: el reconocimiento oyó otra cosa en {len(diferencias)} locuciones")
        textos = "".join(f"<li>{html.escape(t)}</li>" for _, t in guion)
        cuerpo.append(f'<h2>{html.escape(nombre)}</h2><section class="demo"><div class="clips">'
                      f'<div class="clip"><b>Antes ({partes["antes"][0].segundos:.0f} s)</b>'
                      f'<audio controls preload="none" src="{slug}-antes.m4a"></audio></div>'
                      f'<div class="clip"><b>Después ({partes["despues"][0].segundos:.0f} s)</b>'
                      f'<audio controls preload="none" src="{slug}-despues.m4a"></audio></div></div>'
                      f'<ol>{textos}</ol></section>')
    (destino / "index.html").write_text(PAGINA_GUION.format(cuerpo="\n".join(cuerpo)), encoding="utf-8")
    (destino / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino / "index.html"
