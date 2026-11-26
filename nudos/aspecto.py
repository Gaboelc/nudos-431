"""El aspecto del video (T20a): el cuadro final en cuatro aspectos, con Cycles y con EEVEE, y su
costo.

`python -m nudos prueba-aspecto` dibuja en 4K tres tomas:
- **paso 4:** el as de guía a mitad del paso 4, con la cámara del video;
- **amarre:** el amarre cuadrado terminado, con la cámara del final del video;
- **trenza:** un primer plano de la trenza, en el chicote del as de guía terminado.

Cada toma va en cuatro aspectos (ASPECTOS), con Cycles y con EEVEE:
- **0, hoy:** el render de T18 (el tubo con la trenza en textura, sobre blanco, vista Standard).
- **1, estudio:** la trenza con geometría, brillo de filamento y pelusa (*sheen*), una mesa de
  madera, un fondo curvo de estudio, una ventana, un contraluz y un relleno, profundidad de campo
  con el foco en la punta, viñeta y grano.
- **2, estudio con la cuerda real:** como el 1, con la cuerda de los filtros (negra, con el
  trazador amarillo de las fotos de T15e).
- **3, campamento:** la mesa al aire libre, con el cielo de Blender, sol suave y, si está, un HDRI
  de árboles de Poly Haven al fondo.

Mide también el tiempo por cuadro en la tarjeta (el primer cuadro de cada toma, con la escena por
armar, y los siguientes, que son los del video: solo cambia la malla de la cuerda), el formato
vertical y el desenfoque de movimiento, y arma build/aspecto/prueba.pdf con la proyección para
los 36 nudos contra la meta de dos semanas.

Las tomas (la cuerda de cada cuadro, sus vecinos y la cámara) salen del atado guardado de los
pilotos (`nudos/video.py`) y quedan en build/aspecto/tomas.npz: la segunda vez no hace falta el
motor.

Necesita Edge o Chrome (NUDOS_CHROME, para las mallas del anfitrión y el PDF) y Blender 5.2.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from . import BUILD, RAIZ

DESTINO = BUILD / "aspecto"
RENDER_ASPECTO = RAIZ / "render" / "blender" / "aspecto.py"
TAM = (3840, 2160)
TAM_VERTICAL = (1080, 1920)
MM_POR_D = 8.0                 # la cuerda de los filtros mide 8 mm (T15e)
MOTORES = ("CYCLES", "BLENDER_EEVEE")
NOMBRE_MOTOR = {"CYCLES": "Cycles", "BLENDER_EEVEE": "EEVEE"}


def motor_y_muestras(m: str) -> tuple[str, int | None]:
    """«CYCLES:16» es Cycles con 16 muestras en vez de las de AJUSTES_MOTOR."""
    motor, _, n = m.partition(":")
    return motor, (int(n) if n else None)


def nombre_motor(m: str) -> str:
    motor, n = motor_y_muestras(m)
    return f"{NOMBRE_MOTOR[motor]} ({n} muestras)" if n else NOMBRE_MOTOR[motor]


def sufijo_motor(m: str) -> str:
    return m.lower().replace(":", "-")
VECINOS = 3                    # cuadros del video después del de la toma, para medir el tiempo


@dataclass
class Aspecto:
    clave: str                 # "0", "1", "2", "3a"…: el nombre de sus archivos
    n: int                     # el aspecto del plan (0 a 3)
    nombre: str
    malla: str                 # "tubo" (el de hoy) o "trenza" (con geometría)
    escena: str                # "blanco", "estudio" o "campamento"
    estilo: str = "azul"       # el de la cuerda (nudos/trenza.py)
    resaltado: str = "ambar"
    descripcion: str = ""
    hdri: str | None = None    # el del campamento, en config/recursos.yaml


ASPECTOS = (
    Aspecto("0", 0, "hoy", "tubo", "blanco",
            descripcion="El render de T18: el tubo con la trenza en textura y relieve, sobre blanco, "
                        "con dos luces de área y la vista Standard."),
    Aspecto("1", 1, "estudio", "trenza", "estudio",
            descripcion="La trenza con geometría, brillo de filamento y pelusa, la mesa de madera, el "
                        "fondo curvo, la ventana, el contraluz y el relleno, la profundidad de campo con "
                        "el foco en la punta, viñeta y grano."),
    Aspecto("2", 2, "estudio con la cuerda real", "trenza", "estudio", estilo="real", resaltado="real-ambar",
            descripcion="Como el 1, con la cuerda de los filtros: negra con el trazador amarillo de las "
                        "fotos de T15e, y la trenza más estirada."),
    Aspecto("3a", 3, "campamento (Meadow)", "trenza", "campamento", hdri="hdri/meadow_4k.hdr",
            descripcion="La mesa al aire libre, con la luz y el fondo de árboles del HDRI «Meadow» de "
                        "Poly Haven (CC0): sol suave entre nubes."),
    Aspecto("3b", 3, "campamento (J&E Gray 02)", "trenza", "campamento", hdri="hdri/je_gray_02_4k.hdr",
            descripcion="La mesa al aire libre, con la luz y el fondo de árboles del HDRI «J&E Gray 02» de "
                        "Poly Haven (CC0): sol bajo y nítido entre los árboles."),
)


# --------------------------------------------------------------------------
# Las tomas
# --------------------------------------------------------------------------
@dataclass
class Toma:
    nombre: str
    titulo: str
    slug: str
    X: np.ndarray                      # la cuerda del cuadro
    vecinos: list                      # las de los cuadros siguientes (para medir el tiempo)
    h: float
    tramos: list                       # [n0, n1, material] por tramo entre nodos
    tramos_vecinos: list
    camara: dict                       # pos, target, fov, aspecto
    camara_vertical: dict | None
    mallas: list = field(default_factory=list)   # las del anfitrión
    foco: list | None = None           # el punto enfocado
    sub: int = 5                       # anillos por tramo entre nodos
    lados: int = 96
    region: list | None = None         # los puntos de toda la cuerda del video (la mesa los cubre)
    # El cuadro más rápido del paso, para el desenfoque de movimiento: «X», «antes» y «despues»
    # (los cuadros vecinos, con la misma cantidad de nodos), «tramos», «camara» y «foco».
    movimiento: dict | None = None


def _guardar_tomas(tomas: list[Toma], ruta: Path) -> None:
    arr, info = {}, []
    for k, t in enumerate(tomas):
        arr[f"t{k}X"] = t.X
        for i, x in enumerate(t.vecinos):
            arr[f"t{k}v{i}"] = x
        if t.movimiento is not None:
            for c in ("X", "antes", "despues"):
                arr[f"t{k}m{c}"] = t.movimiento[c]
        if t.region is not None:
            arr[f"t{k}r"] = np.asarray(t.region, float)
        info.append({"nombre": t.nombre, "titulo": t.titulo, "slug": t.slug, "h": t.h, "vecinos": len(t.vecinos),
                     "tramos": t.tramos, "tramos_vecinos": t.tramos_vecinos,
                     "movimiento": None if t.movimiento is None else
                     {c: _json(v) for c, v in t.movimiento.items() if c not in ("X", "antes", "despues")},
                     "camara": _json(t.camara), "camara_vertical": _json(t.camara_vertical),
                     "mallas": t.mallas, "foco": _json(t.foco), "sub": t.sub, "lados": t.lados,
                     "region": t.region is not None})
    ruta.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ruta, **arr)
    ruta.with_suffix(".json").write_text(json.dumps(info), encoding="utf-8")


def _json(x):
    if x is None:
        return None
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    return x


def _leer_tomas(ruta: Path) -> list[Toma]:
    info = json.loads(ruta.with_suffix(".json").read_text(encoding="utf-8"))
    with np.load(ruta) as z:
        return [Toma(t["nombre"], t["titulo"], t["slug"], z[f"t{k}X"],
                     [z[f"t{k}v{i}"] for i in range(t["vecinos"])],
                     t["h"], t["tramos"], t["tramos_vecinos"],
                     t["camara"], t["camara_vertical"], t["mallas"], t["foco"], t["sub"], t["lados"],
                     z[f"t{k}r"] if t["region"] else None,
                     None if not t.get("movimiento") else
                     {**t["movimiento"], **{c: z[f"t{k}m{c}"] for c in ("X", "antes", "despues")}})
                for k, t in enumerate(info)]


def _camara(c: dict) -> dict:
    return {"pos": [float(x) for x in c["pos"]], "target": [float(x) for x in c["target"]],
            "fov": float(c["fov"]), "aspecto": float(c["aspecto"])}


def tomas(rehacer: bool = False) -> list[Toma]:
    """Las tres tomas, desde build/aspecto/tomas.npz o desde el atado de los pilotos."""
    ruta = DESTINO / "tomas.npz"
    if ruta.exists() and not rehacer:
        return _leer_tomas(ruta)
    from .prueba_atar import _tramos, mallas_anfitrion
    from .video import atar, construir, cuadros_de, toma
    antes = os.environ.get("NUDOS_MOTOR")
    os.environ["NUDOS_MOTOR"] = "1"       # el apretado del video es el del motor
    try:
        out = _tomas(construir(["as-de-guia", "amarre-cuadrado"]), _tramos, mallas_anfitrion, atar,
                     cuadros_de, toma)
    finally:
        if antes is None:
            os.environ.pop("NUDOS_MOTOR", None)
        else:
            os.environ["NUDOS_MOTOR"] = antes
    _guardar_tomas(out, ruta)
    return out


APERTURA = 1.2      # rad desde la vertical: la cámara baja del amarre, que deja ver el fondo


def primer_plano(X, h: float, camara: dict, alto: float = 7.5) -> tuple[dict, np.ndarray]:
    """La cámara del primer plano de la trenza: mira como `camara`, de cerca (el cuadro mide
    `alto` d de alto), al centro de los cruces del nudo. Da también ese centro, donde va el
    foco."""
    from .cruces import encontrar_cruces
    X = np.asarray(X, float)
    cruces = encontrar_cruces(X, h)
    if cruces:
        pts = [(X[min(len(X) - 1, int(round(c.sa / h)))] + X[min(len(X) - 1, int(round(c.sb / h)))]) / 2
               for c in cruces]
        centro = np.mean(pts, axis=0)
    else:
        centro = X[-1]
    lejos = alto / 2 / math.tan(math.radians(15))
    d = np.asarray(camara["pos"], float) - np.asarray(camara["target"], float)
    d /= np.linalg.norm(d)
    return {"pos": centro + lejos * d, "target": centro, "fov": 30.0, "aspecto": TAM[0] / TAM[1]}, centro


def _tomas(modelos, _tramos, mallas_anfitrion, atar, cuadros_de, toma) -> list[Toma]:
    out = []
    # 1. El as de guía a mitad del paso 4.
    m = modelos["as-de-guia"]
    h = m.pasos[-1].h
    tramos, _ = atar(m)
    cuadros = cuadros_de(m, tramos, "horizontal")
    verticales = cuadros_de(m, tramos, "vertical")
    mov = [i for i, c in enumerate(cuadros) if c.paso == 4 and c.fase != "pausa"]
    medio = mov[len(mov) // 2]

    def resaltado_visto(c):
        return sum((b - a) * h for a, b, mm in _tramos(len(c.X), h, c.resaltado, False) if mm == 1)

    # El cuadro más cercano a la mitad del paso con el resaltado entero a la vista (hoy va por
    # índice de nodo y en la mitad del paso queda vacío, hasta T21b) y con la misma cantidad de
    # nodos que el anterior y el siguiente (el desenfoque de movimiento compara vértice a vértice).
    candidatos = [i for i in mov if mov[0] < i < mov[-1] - VECINOS
                  and resaltado_visto(cuadros[i]) >= 0.6 * (cuadros[i].resaltado[1] - cuadros[i].resaltado[0])
                  and len(cuadros[i - 1].X) == len(cuadros[i].X) == len(cuadros[i + 1].X)]
    i = min(candidatos or [medio], key=lambda j: abs(j - medio))
    c = cuadros[i]
    paso4 = [np.asarray(x.X, float) for x in cuadros if x.paso == 4]
    # El desenfoque de movimiento se prueba en el cuadro del paso que se mueve más rápido, con un
    # movimiento parejo (la misma velocidad en los cuadros vecinos, no un brinco).
    rapido = None
    for j in mov[2:-2]:
        Xs = [np.asarray(cuadros[q].X, float) for q in range(j - 2, j + 3)]
        if len({len(x) for x in Xs}) != 1:
            continue
        v = [np.linalg.norm(Xs[q + 1] - Xs[q], axis=1) for q in range(4)]
        n = int(np.argmax(v[1] + v[2]))
        vs = [x[n] for x in v]
        if min(vs) > 0 and max(vs) / min(vs) < 1.3 and (rapido is None or vs[1] + vs[2] > rapido[0]):
            rapido = (vs[1] + vs[2], j)
    movimiento = None
    if rapido is not None:
        j = rapido[1]
        cj = cuadros[j]
        movimiento = {"X": np.asarray(cj.X, float), "antes": np.asarray(cuadros[j - 1].X, float),
                      "despues": np.asarray(cuadros[j + 1].X, float),
                      "tramos": _tramos(len(cj.X), h, cj.resaltado, False), "camara": _camara(cj.camara),
                      "foco": [float(x) for x in cj.X[-1]], "cuadro": j}
    out.append(Toma("paso4", "El as de guía a mitad del paso 4", "as-de-guia", np.asarray(c.X, float),
                    [np.asarray(cuadros[i + k].X, float) for k in range(1, VECINOS + 1)],
                    h, _tramos(len(c.X), h, c.resaltado, False),
                    [_tramos(len(cuadros[i + k].X), h, cuadros[i + k].resaltado, False)
                     for k in range(1, VECINOS + 1)],
                    _camara(c.camara), _camara(verticales[i].camara), [],
                    [float(x) for x in c.X[-1]], region=np.vstack(paso4)[::7], movimiento=movimiento))
    # 3. El primer plano de la trenza: el nudo del as de guía terminado (sus cruces), de cerca.
    fin = np.asarray(cuadros[-1].X, float)
    trenza_toma, punta = primer_plano(fin, h, cuadros[-1].camara)
    trenza = Toma("trenza", "Primer plano de la trenza, en el chicote del as de guía terminado", "as-de-guia",
                  fin, [fin] * VECINOS, h, _tramos(len(fin), h, None, False),
                  [_tramos(len(fin), h, None, False)] * VECINOS, _camara(trenza_toma), None, [],
                  [float(x) for x in punta], sub=10, lados=160, region=np.vstack(paso4)[::7])
    # 2. El amarre cuadrado terminado: el último cuadro del video, con una cámara más baja que la
    # del video, como la de una apertura, que deja ver el fondo.
    m = modelos["amarre-cuadrado"]
    h = m.pasos[-1].h
    tramos, _ = atar(m)
    cuadros = cuadros_de(m, tramos, "horizontal")
    verticales = cuadros_de(m, tramos, "vertical")
    c = cuadros[-1]
    X = np.asarray(c.X, float)
    mallas = mallas_anfitrion(m)
    palos = np.vstack([np.asarray(x["pos"], float).reshape(-1, 3) for x in mallas]) if mallas else X
    d = np.asarray(c.camara["pos"], float) - np.asarray(c.camara["target"], float)
    az = math.atan2(d[0], -d[1])
    baja = toma(np.vstack([X, palos]), APERTURA, az, TAM[0] / TAM[1], (0.1, 0.12, 0.9, 0.88))
    centro = X.mean(axis=0)
    out.append(Toma("amarre", "El amarre cuadrado terminado, con una cámara de apertura", "amarre-cuadrado",
                    X, [X] * VECINOS, h, _tramos(len(X), h, None, True),
                    [_tramos(len(X), h, None, True)] * VECINOS, _camara(baja),
                    _camara(verticales[-1].camara), mallas, [float(x) for x in centro],
                    region=np.vstack([X, palos] + [np.asarray(x.X, float) for x in cuadros[::40]])[::5]))
    out.append(trenza)
    return out


# --------------------------------------------------------------------------
# Los ajustes de cada aspecto para Blender
# --------------------------------------------------------------------------
VISTA = {"vista": "AgX", "look": "AgX - Base Contrast"}   # la que no lava el azul (ver la prueba)
FSTOP = 11.0           # el número f de un lente real a la escala de la cuerda (8 mm)
VINETA = 0.22          # cuánto oscurece la viñeta en las esquinas
GRANO = 0.016          # el grano, antes de suavizarlo (en 0-1)

AJUSTES_ASPECTO = {
    0: {"vista": "Standard", "look": "None", "exposicion": -0.55},
    1: {**VISTA, "exposicion": 0.0, "fstop": FSTOP, "luz": 1.0,
        "madera_claro": (204, 160, 112), "madera_oscuro": (116, 74, 42), "barniz": 0.12,
        "papel": (200, 196, 190), "rugosidad": 0.42, "anisotropia": 0.7, "giro_brillo": 0.25,
        "sheen": 0.35, "filamentos": 0.35, "textura": 2048, "cinta": (214, 52, 32)},
    2: {**VISTA, "exposicion": 0.0, "fstop": FSTOP, "luz": 1.0,
        "madera_claro": (204, 160, 112), "madera_oscuro": (116, 74, 42), "barniz": 0.12,
        "papel": (200, 196, 190), "rugosidad": 0.34, "anisotropia": 0.75, "giro_brillo": 0.25,
        "sheen": 0.3, "filamentos": 0.4, "textura": 2048, "cinta": (226, 92, 22)},
    3: {**VISTA, "exposicion": 0.0, "fstop": FSTOP, "luz": 1.0,
        "madera_claro": (176, 152, 122), "madera_oscuro": (98, 80, 60),
        "rugosidad": 0.42, "anisotropia": 0.7, "giro_brillo": 0.25, "sheen": 0.35, "filamentos": 0.35,
        "textura": 2048, "cinta": (214, 52, 32), "sol": 3.2, "sol_angulo": 4.0, "sol_phi": -125,
        "sol_elev": 38, "cielo": 0.12, "hdri_fuerza": 1.0, "hdri_giro": 0.0},
}
AJUSTES_MOTOR = {
    # Cycles: como el video de T18 (umbral adaptativo 0,03, el denoiser en la tarjeta), con más
    # muestras por la profundidad de campo.
    "CYCLES": {"muestras": 64, "umbral": 0.03},
    "BLENDER_EEVEE": {"muestras": 64, "rayos_sombra": 2},
}


SOL_CAMPAMENTO = -125.0   # grados alrededor de la mesa desde la cámara: el sol, atrás a la izquierda


def ajustes_aspecto(a: Aspecto, az: float = 0.0) -> dict:
    """Los ajustes del aspecto para render/blender/aspecto.py. En el campamento con HDRI, el giro
    del HDRI que pone su sol atrás a la izquierda de la cámara (az: la de la toma)."""
    out = {"n": a.n, "clave": a.clave, "nombre": a.nombre, "malla": a.malla, "escena": a.escena,
           **AJUSTES_ASPECTO[a.n]}
    if a.hdri:
        from .recursos import recurso, registro
        sol = registro()[a.hdri]["sol"]
        out["hdri"] = str(recurso(a.hdri))
        # En Blender, la dirección (x, y) cae en u = 0,5 − atan2(y, x)/2π del HDRI.
        alfa_hdri = (0.5 - sol["u"]) * 2 * math.pi
        phi = math.radians(SOL_CAMPAMENTO)
        cam = np.array([math.sin(az), -math.cos(az)])
        der = np.array([math.cos(az), math.sin(az)])
        d = math.cos(phi) * cam + math.sin(phi) * der
        out["hdri_giro"] = alfa_hdri - math.atan2(d[1], d[0])
        out["sol_elev"] = sol["altura"]
    return out


def _az(c: dict) -> float:
    d = np.asarray(c["pos"], float) - np.asarray(c["target"], float)
    return math.atan2(d[0], -d[1])


def inclinacion_fondo(c: dict, horizonte: float = 0.38) -> float:
    """En el campamento, cuánto se baja el HDRI que ve la cámara (en grados) para que el
    horizonte, con los árboles, quede a `horizonte` del alto del cuadro desde arriba. Solo si
    la cámara ve el fondo (lo alto del cuadro a menos de 12° bajo el horizonte): las tomas desde
    arriba solo ven la mesa. La luz sigue siendo la del HDRI sin bajar."""
    d = np.asarray(c["pos"], float) - np.asarray(c["target"], float)
    polar = math.degrees(math.acos(d[2] / np.linalg.norm(d)))
    arriba = -(90.0 - polar) + c["fov"] / 2
    if arriba < -12.0:
        return 0.0
    return max(0.0, -arriba + horizonte * c["fov"])


def _profundidad(c: dict, p) -> float:
    """La distancia de la cámara al plano de foco que pasa por p (a lo largo de la mirada)."""
    pos, t = np.asarray(c["pos"], float), np.asarray(c["target"], float)
    f = (t - pos) / np.linalg.norm(t - pos)
    return float(np.dot(np.asarray(p, float) - pos, f))


def escenario(t: Toma) -> dict:
    """La mesa, el fondo y la luz de una toma: la mesa cubre toda la cuerda del video (la del
    paso, en estas tomas) con un margen, para que la cuerda nunca quede en el aire."""
    reg = np.vstack([t.region, t.X]) if t.region is not None else t.X
    (x0, y0), (x1, y1) = reg[:, :2].min(axis=0), reg[:, :2].max(axis=0)
    margen = 10.0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    semi = [max((x1 - x0) / 2 + margen, 30.0), max((y1 - y0) / 2 + margen, 30.0)]
    (kx0, ky0), (kx1, ky1) = t.X[:, :2].min(axis=0), t.X[:, :2].max(axis=0)
    ext = float(max(kx1 - kx0, ky1 - ky0) / 2)
    return {"mesa": {"centro": [float(cx), float(cy)], "semi": [float(s) for s in semi], "grosor": 4.0,
                     "bisel": 0.45, "giro": 0.0},
            "fondo": {"centro": [float(cx), float(cy)], "piso": -4.0, "radio": float(math.hypot(*semi) + 25),
                      "curva": 45.0, "alto": 260.0},
            "luz": {"centro": [float((kx0 + kx1) / 2), float((ky0 + ky1) / 2)],
                    "escala": float(np.clip(ext + 8, 16, 30)), "az": _az(t.camara), "extension": ext}}


def _malla(t: Toma, a: Aspecto, X, tramos, ruta: Path, solidos, velocidad=None) -> np.ndarray:
    """Escribe la malla de la cuerda X para el aspecto y da sus vértices."""
    from . import blender
    from .trenza import ESTILOS
    from .video import punta_suave
    X = punta_suave(np.asarray(X, float), t.h)
    if a.malla == "tubo":
        e = {"cuerdas": [{"espina": X.ravel().tolist(), "radio": 0.5, "grosor": 1.0, "color": "azul",
                          "tramos": tramos}], "mallas": t.mallas}
        m = blender.malla_cuerda(0, e, solidos=solidos, tapas=True)
        np.savez(ruta, vertices=m.vertices.astype(np.float32), caras=m.caras.astype(np.int32),
                 uv=m.uv.astype(np.float32), material=m.material, s=m.s.astype(np.float32))
        return m.vertices
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(X, axis=0), axis=1))])
    m = blender.malla_trenza(X, tramos=tramos, mosaico=ESTILOS[a.estilo].mosaico, sub=t.sub, lados=t.lados,
                             otras=[(X, s, 0.5, True)], solidos=solidos)
    blender.guardar_trenza(m, ruta, velocidad)
    return m.vertices


def preparar(t: Toma, a: Aspecto, carpeta: Path, vertical: bool = False, movimiento: bool = False,
             seguidos: int | None = None) -> dict:
    """Escribe en `carpeta` las mallas de la toma en el aspecto y da su parte del lote."""
    from . import blender
    from .prueba_atar import _datos_camara
    carpeta.mkdir(parents=True, exist_ok=True)
    solidos = blender._muestras_solidos(t.mallas) if t.mallas else None
    esc = carpeta / f"{t.nombre}-escena.json"
    esc.write_text(json.dumps({"mallas": t.mallas}), encoding="utf-8")
    base = f"{t.nombre}-{a.clave}"
    principal = carpeta / f"{base}.npz"
    V0 = _malla(t, a, t.X, t.tramos, principal, solidos)
    n_seg = VECINOS if seguidos is None else seguidos
    rutas = []
    for k, (x, tr) in enumerate(zip(t.vecinos[:n_seg], t.tramos_vecinos[:n_seg])):
        r = carpeta / f"{base}-s{k}.npz"
        _malla(t, a, x, tr, r, solidos)
        rutas.append(str(r))
    lote = {"nombre": t.nombre, "escena": str(esc),
            "cuerdas": [{"malla": str(principal), "estilo": a.estilo, "resaltado": a.resaltado, "color": "azul"}],
            "camara": _datos_camara(t.camara), "seguidos": rutas,
            "salida_seguidos": str(carpeta / f"{base}-seguido.png"), **escenario(t)}
    if t.foco is not None:
        lote["foco"] = _profundidad(t.camara, t.foco)
    lote["hdri_inclinacion"] = inclinacion_fondo(t.camara)
    if vertical and t.camara_vertical is not None:
        cv = t.camara_vertical
        lote["vertical"] = {"ancho": TAM_VERTICAL[0], "alto": TAM_VERTICAL[1], "camara": _datos_camara(cv),
                            "foco": _profundidad(cv, t.foco) if t.foco is not None else None}
    m = t.movimiento
    if movimiento and a.malla == "trenza" and m is not None:
        # La velocidad de cada vértice, de la malla del cuadro anterior a la del siguiente.
        Va = _malla(t, a, m["antes"], m["tramos"], carpeta / f"{base}-antes.npz", solidos)
        Vd = _malla(t, a, m["despues"], m["tramos"], carpeta / f"{base}-despues.npz", solidos)
        r = carpeta / f"{base}-mov.npz"
        V = _malla(t, a, m["X"], m["tramos"], r, solidos)
        if len(Va) == len(V) == len(Vd):
            vel = (Vd - Va) * (60.0 / 2.0)              # d por segundo, a 60 cuadros por segundo
            _malla(t, a, m["X"], m["tramos"], r, solidos, velocidad=vel)
            lote["movimiento"] = {"malla": str(r), "obturador": 0.5, "camara": _datos_camara(m["camara"]),
                                  "foco": _profundidad(m["camara"], m["foco"])}
    return lote


def dibujar(a: Aspecto, motor: str, partes: list[dict], carpeta: Path, tam=TAM, ajustes=None,
            aviso=print) -> list[dict]:
    """Una corrida de Blender: las tomas en el aspecto y el motor. Da los tiempos anotados."""
    from .blender import BlenderError, ejecutable
    nombre = f"{a.clave}-{sufijo_motor(motor)}"
    motor_blender, muestras = motor_y_muestras(motor)
    if muestras:
        # Con otras muestras solo interesa el costo y el ruido: sin la prueba del movimiento.
        for p in partes:
            p.pop("movimiento", None)
    if ajustes is None:
        ajustes = dict(AJUSTES_MOTOR[motor_blender])
        if muestras:
            ajustes["muestras"] = muestras
    for p in partes:
        p["salida"] = str(carpeta / f"{p['nombre']}-{nombre}.png")
        if "vertical" in p:
            p["vertical"]["salida"] = str(carpeta / f"{p['nombre']}-{nombre}-vertical.png")
        if "movimiento" in p:
            p["movimiento"]["salida"] = str(carpeta / f"{p['nombre']}-{nombre}-movimiento.png")
            p["movimiento"]["salida_sin"] = str(carpeta / f"{p['nombre']}-{nombre}-movimiento-sin.png")
    for p in partes:
        p["aspecto"] = {**ajustes_aspecto(a, p["luz"]["az"]), "hdri_inclinacion": p.get("hdri_inclinacion", 0.0)}
    lote = {"motor": motor_blender, "ajustes": ajustes, "aspecto": ajustes_aspecto(a),
            "ancho": tam[0], "alto": tam[1], "tomas": partes}
    ruta = carpeta / f"lote-{nombre}.json"
    ruta.write_text(json.dumps(lote), encoding="utf-8")
    orden = [ejecutable(), "--background", "--factory-startup", "--python-exit-code", "1",
             "--python", str(RENDER_ASPECTO), "--", "--lote", str(ruta)]
    tiempos, cola = [], []
    t0 = time.time()
    proc = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    for linea in proc.stdout:
        cola = (cola + [linea.rstrip()])[-30:]
        if linea.startswith("tiempo: "):
            d = json.loads(linea[len("tiempo: "):])
            tiempos.append(d)
            aviso(f"  aspecto {a.clave}, {nombre_motor(motor)}: {d['toma']} {d['tipo']} {d['s']:.1f} s")
    if proc.wait() != 0:
        raise BlenderError(f"Blender no pudo dibujar el aspecto {a.clave} con {motor}:\n" + "\n".join(cola))
    aviso(f"  aspecto {a.clave}, {nombre_motor(motor)}: listo en {time.time() - t0:.0f} s")
    return tiempos


def posprocesar(ruta: Path, a: Aspecto, semilla: int = 0) -> None:
    """Lo que va después de Blender: el aspecto 0, sobre blanco (como en el video de hoy); los
    demás, con la viñeta y el grano."""
    with Image.open(ruta) as im:
        im = im.convert("RGBA")
    if a.n == 0:
        fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
        fondo.alpha_composite(im)
        fondo.convert("RGB").save(ruta)
        return
    vineta_y_grano(im.convert("RGB"), semilla).save(ruta)


def vineta_y_grano(im: Image.Image, semilla: int = 0) -> Image.Image:
    """La viñeta (las esquinas un VINETA más oscuras) y un grano fino, más fuerte en los tonos
    medios, distinto en cada cuadro (`semilla`)."""
    from scipy.ndimage import gaussian_filter
    x = np.asarray(im, np.float32) / 255.0
    h, w = x.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / math.sqrt(2)
    t = np.clip((r - 0.35) / 0.65, 0, 1)
    x *= (1 - VINETA * t * t * (3 - 2 * t))[..., None]
    g = gaussian_filter(np.random.default_rng(semilla).normal(0, GRANO, (h, w)).astype(np.float32),
                        0.6 * w / 3840)
    L = x.mean(axis=2)
    x += (g * (0.5 + 2.0 * L * (1 - L)))[..., None]
    return Image.fromarray(np.clip(x * 255 + 0.5, 0, 255).astype(np.uint8))


# --------------------------------------------------------------------------
# La prueba entera, el costo y la página
# --------------------------------------------------------------------------
CUADROS_VIDEO = 7200        # cuadros en 4K del video largo de un nudo (unos 2 min a 60 fps)
CUADROS_REEL = 3000         # cuadros en 1080 × 1920 del reel (de 45 a 60 s)
NUDOS = 36
META_DIAS = 14.0            # la meta de Gabriel: unas 2 semanas para los 36 nudos
TOMAS_VIDEO = ("paso4", "amarre")    # las que se parecen a un cuadro del video: su promedio
SEGUIDOS = {"paso4": VECINOS, "amarre": 2, "trenza": 2}


@dataclass
class Resultado:
    clave: str
    motor: str
    tiempos: list

    def de(self, toma: str, tipo: str) -> list[float]:
        return [d["s"] for d in self.tiempos if d["toma"] == toma and d["tipo"] == tipo]

    def promedio(self, tomas, tipo) -> float:
        xs = [s for t in tomas for s in self.de(t, tipo)]
        return float(np.mean(xs)) if xs else float("nan")

    @property
    def cuadro_4k(self) -> float:
        """Los segundos de un cuadro de 4K del video: el promedio de los cuadros seguidos (solo
        cambia la malla de la cuerda) del paso 4 y del amarre."""
        return self.promedio(TOMAS_VIDEO, "seguido")

    @property
    def cuadro_vertical(self) -> float:
        return self.promedio(("paso4",), "vertical")

    @property
    def dias(self) -> float:
        """Los días de render de los 36 nudos: el video largo en 4K y el reel."""
        v = self.cuadro_vertical
        if not np.isfinite(v):
            v = self.cuadro_4k * TAM_VERTICAL[0] * TAM_VERTICAL[1] / (TAM[0] * TAM[1])
        return NUDOS * (CUADROS_VIDEO * self.cuadro_4k + CUADROS_REEL * v) / 86400


def prueba(aspectos=ASPECTOS, motores=MOTORES, carpeta: Path = DESTINO, aviso=print, solo=None) -> Path:
    """Dibuja las tres tomas (o las de `solo`) en cada aspecto y con cada motor, mide el tiempo y
    arma carpeta/prueba.pdf con todo lo dibujado hasta ahora. Devuelve la ruta."""
    import copy
    import shutil
    todas = tomas()
    ts = [t for t in todas if solo is None or t.nombre in solo]
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_tiempos = carpeta / "tiempos.json"
    # Los tiempos de corridas anteriores se quedan, salvo los de las tomas que esta vuelve a dibujar.
    anteriores = {}
    if ruta_tiempos.exists():
        anteriores = {(d["clave"], d["motor"]): d["tiempos"]
                      for d in json.loads(ruta_tiempos.read_text(encoding="utf-8"))}
    nombres = {t.nombre for t in ts}
    resultados = [Resultado(c, m, x) for (c, m), x in anteriores.items()
                  if not any(a.clave == c for a in aspectos) or m not in motores]
    for a in aspectos:
        aviso(f"Aspecto {a.clave} ({a.nombre}): las mallas")
        partes = [preparar(t, a, carpeta / "mallas", vertical=t.nombre == "paso4",
                           movimiento=t.nombre == "paso4", seguidos=SEGUIDOS.get(t.nombre, 2)) for t in ts]
        for m in motores:
            tiempos = dibujar(a, m, copy.deepcopy(partes), carpeta, TAM, aviso=aviso)
            for t in ts:
                for sufijo in ("", "-vertical", "-movimiento", "-movimiento-sin"):
                    r = carpeta / f"{t.nombre}-{a.clave}-{sufijo_motor(m)}{sufijo}.png"
                    if r.exists():
                        posprocesar(r, a)
            viejos = [d for d in anteriores.get((a.clave, m), []) if d["toma"] not in nombres]
            resultados.append(Resultado(a.clave, m, viejos + tiempos))
            ruta_tiempos.write_text(json.dumps([r.__dict__ for r in resultados], indent=1), encoding="utf-8")
        for r in carpeta.glob(f"*-{a.clave}-seguido.png"):
            r.unlink()
        shutil.rmtree(carpeta / "mallas", ignore_errors=True)
    return pagina(todas, resultados, carpeta)


def _proyectar(c: dict, p, tam) -> tuple[float, float]:
    """El píxel (x, y desde arriba a la izquierda) donde la cámara c ve el punto p."""
    from .prueba_atar import _mirar
    M = _mirar(np.asarray(c["pos"], float), np.asarray(c["target"], float))
    q = (np.asarray(p, float) - M[:3, 3]) @ M[:3, :3]
    th = math.tan(math.radians(c["fov"]) / 2)
    x = q[0] / (-q[2] * th * c["aspecto"])
    y = q[1] / (-q[2] * th)
    return (x + 1) / 2 * tam[0], (1 - y) / 2 * tam[1]


def _recorte(ruta: Path, centro, tam=(1280, 720)) -> Image.Image:
    with Image.open(ruta) as im:
        W, H = im.size
        x0 = int(np.clip(centro[0] - tam[0] / 2, 0, W - tam[0]))
        y0 = int(np.clip(centro[1] - tam[1] / 2, 0, H - tam[1]))
        return im.crop((x0, y0, x0 + tam[0], y0 + tam[1])).convert("RGB")


def _jpg(im: Image.Image, ruta: Path, ancho: int | None = None) -> str:
    if ancho and im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.Resampling.LANCZOS)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(ruta, quality=90)
    return ruta.as_uri()


def pagina(ts: list[Toma], resultados: list[Resultado], carpeta: Path = DESTINO) -> Path:
    """build/aspecto/prueba.pdf: el costo y la proyección, cada toma en cada aspecto con los dos
    motores, los detalles a tamaño real y el desenfoque de movimiento."""
    import html
    por = {(r.clave, r.motor): r for r in resultados}
    claves = [a.clave for a in ASPECTOS if any(r.clave == a.clave for r in resultados)]
    # Cycles primero (de más a menos muestras) y después EEVEE.
    motores = sorted(dict.fromkeys(r.motor for r in resultados),
                     key=lambda m: (motor_y_muestras(m)[0] != "CYCLES", -(motor_y_muestras(m)[1] or 999)))
    aspectos = {a.clave: a for a in ASPECTOS}
    pdf = carpeta / "pdf"
    esc = html.escape

    def nombre(t, clave, m, sufijo=""):
        return carpeta / f"{t}-{clave}-{sufijo_motor(m)}{sufijo}.png"

    def seg(x):
        return "—" if not np.isfinite(x) else f"{x:.1f} s".replace(".", ",")

    def dias(x):
        return "—" if not np.isfinite(x) else f"{x:.0f} días"

    # Una fila por motor (con sus muestras) y una columna por aspecto: en cada celda, los segundos
    # de un cuadro de 4K, los del vertical y los días para los 36 nudos.
    filas = []
    for m in motores:
        motor, n = motor_y_muestras(m)
        n = n or AJUSTES_MOTOR[motor]["muestras"]
        celdas = [f"<td class='izq'><b>{NOMBRE_MOTOR[motor]}</b>, {n} muestras</td>"]
        for c in claves:
            r = por.get((c, m))
            if r is None:
                celdas.append("<td>—</td>")
                continue
            cabe = r.dias <= META_DIAS
            celdas.append(f"<td class='{'si' if cabe else 'no'}'><b>{seg(r.cuadro_4k)}</b><br>"
                          f"<span>vertical {seg(r.cuadro_vertical)}</span><br>{dias(r.dias)}</td>")
        filas.append("<tr>" + "".join(celdas) + "</tr>")
    cab = "".join(f"<th>{esc(c)}<br><span>{esc(aspectos[c].nombre)}</span></th>" for c in claves)
    tabla = (f"<table class='costo'><thead><tr><th class='izq'>Motor</th>{cab}</tr></thead>"
             f"<tbody>{''.join(filas)}</tbody></table>")
    plano = []
    for c in claves:
        xs = [f"{nombre_motor(m)} {seg(por[(c, m)].promedio(('trenza',), 'seguido'))}"
              for m in motores if (c, m) in por and por[(c, m)].de("trenza", "seguido")]
        if xs:
            plano.append(f"{esc(c)}, {', '.join(xs)}")
    movs = []
    for c in claves:
        for m in motores:
            r = por.get((c, m))
            if r and r.de("paso4", "movimiento"):
                sin = r.de("paso4", "movimiento-sin")
                movs.append(f"{esc(c)} con {nombre_motor(m)}, {seg(r.de('paso4', 'movimiento')[0])}"
                            + (f" (sin él, {seg(sin[0])})" if sin else ""))
    resumen = (
        f"<section class='hoja'><h1>T20a · El cuadro final: el aspecto y su costo</h1>"
        f"<p>Tres tomas en 4K ({TAM[0]} × {TAM[1]}), cada una en cinco aspectos, con Cycles y con EEVEE, "
        f"dibujadas en la RTX 4070: el as de guía en el paso 4 (con la cámara del video), el amarre "
        f"cuadrado terminado (con una cámara baja, como la de una apertura, que deja ver el fondo) y un "
        f"primer plano de la trenza en el chicote del as de guía terminado. Las imágenes enteras, en PNG, "
        f"están en build/aspecto/.</p>"
        f"<h2>El tiempo por cuadro y la proyección</h2>"
        f"<p>Cada tiempo es el de los cuadros seguidos del video: la escena ya está en la tarjeta y solo "
        f"cambia la malla de la cuerda, como en <code>render/blender/video.py</code>. «4K» es el promedio "
        f"del paso 4 y del amarre; «vertical», el del paso 4 en {TAM_VERTICAL[0]} × {TAM_VERTICAL[1]}. "
        f"La proyección: {NUDOS} nudos × ({CUADROS_VIDEO} cuadros de 4K del video largo + {CUADROS_REEL} "
        f"del reel), contra la meta de {META_DIAS:.0f} días (unos 4 s por cuadro de 4K). En verde, lo que "
        f"cabe.</p>{tabla}"
        f"<p>El primer plano de la trenza, por cuadro: {'; '.join(plano)}.</p>"
        f"<h2>Los aspectos</h2><ul>"
        + "".join(f"<li><b>{esc(c)}, {esc(aspectos[c].nombre)}.</b> {esc(aspectos[c].descripcion)}</li>"
                  for c in claves)
        + "</ul>"
        f"<p>Los aspectos 1 a 3 llevan la trenza con geometría (un anillo cada 0,04 d sobre la Catmull-Rom, "
        f"96 lados; 160 en el primer plano), la cinta en el chicote, profundidad de campo (f/{FSTOP:g} a la "
        f"escala de la cuerda de 8 mm, con el foco en la punta), la vista {esc(VISTA['vista'])} "
        f"({esc(VISTA['look'])}), y viñeta y grano después de Blender. EEVEE no tiene brillo de filamento "
        f"(anisotropía): ahí la cuerda brilla parejo.</p>"
        + (f"<h2>El desenfoque de movimiento</h2><p>Ni Cycles ni EEVEE toman el atributo <code>velocity</code> "
           f"de una malla común: con él, el cuadro salía igual. Funciona con un modificador de Geometry Nodes "
           f"que corre cada vértice su velocidad por el tiempo de la escena, así los dos motores ven la cuerda "
           f"moverse dentro del obturador (180°, a 60 cuadros por segundo). En el cuadro más rápido del paso 4, "
           f"la punta va a 7,6 d/s y deja una estela de 3 o 4 px en 4K: se nota poco a esa velocidad, y cuesta "
           f"entre 1 y 2 % más por cuadro. Con el desenfoque: {'; '.join(movs)}. Ver la última hoja.</p>"
           if movs else "")
        + "<h2>Para decidir</h2><ol><li>¿Qué aspecto?</li><li>¿Cycles o EEVEE para el video, y con cuántas "
          "muestras? (Las fichas siguen en Cycles.)</li><li>Si es el campamento, ¿con qué HDRI?</li></ol></section>")
    hojas = [resumen]
    # Las hojas de las tomas, con los dos motores; las variantes con menos muestras van aparte.
    todos_los_motores = motores
    principales = [m for m in motores if ":" not in m]
    variantes = [m for m in motores if ":" in m]
    motores = principales
    for t in ts:
        grupos = [claves[i:i + 2] for i in range(0, len(claves), 2)]
        for k, grupo in enumerate(grupos):
            filas = []
            for c in grupo:
                figs = []
                for m in motores:
                    r = nombre(t.nombre, c, m)
                    if not r.exists():
                        continue
                    with Image.open(r) as im:
                        uri = _jpg(im, pdf / f"{t.nombre}-{c}-{sufijo_motor(m)}.jpg", 1600)
                    res = por.get((c, m))
                    nota = f"{seg(res.de(t.nombre, 'seguido')[0]) if res and res.de(t.nombre, 'seguido') else ''}"
                    figs.append(f"<figure><img src='{uri}'><figcaption><b>{esc(c)}</b> {esc(aspectos[c].nombre)} · "
                                f"{nombre_motor(m)} <span>{nota} por cuadro</span></figcaption></figure>")
                filas.append(f"<div class='fila'>{''.join(figs)}</div>")
            parte = f" ({k + 1} de {len(grupos)})" if len(grupos) > 1 else ""
            hojas.append(f"<section class='hoja'><h1>{esc(t.titulo)}{parte}</h1>{''.join(filas)}</section>")
    # Los detalles a tamaño real: el centro de la acción de las dos tomas del video.
    for t in ts:
        if t.nombre == "trenza" or t.foco is None:
            continue
        centro = _proyectar(t.camara, t.foco, TAM)
        figs = []
        for c in claves:
            for m in motores:
                r = nombre(t.nombre, c, m)
                if r.exists():
                    uri = _jpg(_recorte(r, centro), pdf / f"{t.nombre}-{c}-{sufijo_motor(m)}-detalle.jpg")
                    figs.append(f"<figure class='chica'><img src='{uri}'><figcaption><b>{esc(c)}</b> · "
                                f"{nombre_motor(m)}</figcaption></figure>")
        for k in range(0, len(figs), 6):
            hojas.append(f"<section class='hoja'><h1>{esc(t.titulo)}: el detalle a tamaño real</h1>"
                         f"<p>Un recorte de 1280 × 720 del cuadro de 4K, sin reducir, alrededor del foco.</p>"
                         f"<div class='rejilla'>{''.join(figs[k:k + 6])}</div></section>")
    # El desenfoque de movimiento: el recorte donde la cuerda se mueve más rápido.
    t = next((x for x in ts if x.nombre == "paso4"), None)
    if t is not None and t.movimiento is not None:
        mv = t.movimiento
        v = np.linalg.norm(mv["despues"] - mv["antes"], axis=1)
        centro = _proyectar(mv["camara"], mv["X"][int(np.argmax(v))], TAM)
        rapidez = float(v.max()) * 30
        figs = []
        for c in claves:
            for m in motores:
                r, rm = nombre("paso4", c, m, "-movimiento-sin"), nombre("paso4", c, m, "-movimiento")
                if r.exists() and rm.exists():
                    for ruta, txt in ((r, "sin desenfoque"), (rm, "con desenfoque")):
                        uri = _jpg(_recorte(ruta, centro, (960, 540)), pdf / f"{ruta.stem}-mov.jpg")
                        figs.append(f"<figure class='chica'><img src='{uri}'><figcaption><b>{esc(c)}</b> · "
                                    f"{nombre_motor(m)} · {txt}</figcaption></figure>")
        for k in range(0, len(figs), 6):
            hojas.append(f"<section class='hoja'><h1>El desenfoque de movimiento (paso 4)</h1>"
                         f"<p>Un recorte de 960 × 540 del cuadro de 4K del paso 4 donde la cuerda se mueve "
                         f"más rápido con un movimiento parejo (la punta, a {rapidez:.1f} d/s), sin y con el "
                         f"desenfoque (obturador de 180°, a 60 cuadros por segundo: la estela mide "
                         f"{rapidez / 120:.2f} d).</p>"
                         f"<div class='rejilla'>{''.join(figs[k:k + 6])}</div></section>")
    # Con menos muestras: el detalle a tamaño real junto al de las muestras de siempre.
    t = next((x for x in ts if x.nombre == "paso4"), None)
    if variantes and t is not None and t.foco is not None:
        centro = _proyectar(t.camara, t.foco, TAM)
        figs = []
        for c in claves:
            if not any(por.get((c, m)) for m in variantes):
                continue
            for m in todos_los_motores:
                r = nombre("paso4", c, m)
                if r.exists():
                    uri = _jpg(_recorte(r, centro), pdf / f"paso4-{c}-{sufijo_motor(m)}-muestras.jpg")
                    res = por.get((c, m))
                    figs.append(f"<figure class='chica'><img src='{uri}'><figcaption><b>{esc(c)}</b> · "
                                f"{nombre_motor(m)} <span>{seg(res.cuadro_4k) if res else ''} por cuadro"
                                f"</span></figcaption></figure>")
        for k in range(0, len(figs), 6):
            hojas.append(f"<section class='hoja'><h1>Con menos muestras (paso 4)</h1>"
                         f"<p>El mismo recorte de 1280 × 720, sin reducir: cuánto ruido queda (después "
                         f"del denoiser) con menos muestras, y lo que cuesta.</p>"
                         f"<div class='rejilla'>{''.join(figs[k:k + 6])}</div></section>")
    return _pdf_horizontal("\n".join(hojas), carpeta, "prueba")


def _pdf_horizontal(hojas: str, carpeta: Path, nombre: str) -> Path:
    """Escribe carpeta/<nombre>.pdf en carta horizontal (las imágenes son de 16:9)."""
    from .imprimir import chrome
    from .exportar import SITIO
    fuentes = (SITIO / "vendor" / "fuentes").as_uri()
    documento = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Literata"; font-weight: 400; src: url("{fuentes}/literata-latin-400-normal.woff2"); }}
@font-face {{ font-family: "Literata"; font-weight: 600; src: url("{fuentes}/literata-latin-600-normal.woff2"); }}
@page {{ size: letter landscape; margin: 9mm; }}
body {{ margin: 0; font-family: "Literata", serif; color: #16202f; }}
.hoja {{ break-after: page; }}
.hoja:last-child {{ break-after: auto; }}
h1 {{ font-size: 13pt; font-weight: 600; margin: 0 0 2mm; }}
h2 {{ font-size: 10pt; font-weight: 600; margin: 3mm 0 1mm; }}
p, li {{ font-size: 8.5pt; line-height: 1.35; margin: 0 0 1.5mm; }}
ul, ol {{ margin: 0 0 2mm; padding-left: 5mm; }}
code {{ font-size: 8pt; }}
table {{ border-collapse: collapse; font-size: 7.5pt; margin: 1mm 0 2mm; }}
table.costo td, table.costo th {{ text-align: center; line-height: 1.25; }}
table.costo td.izq, table.costo th.izq {{ text-align: left; }}
table.costo span {{ color: #5a6878; font-weight: 400; }}
th, td {{ border: 0.2mm solid #ccd4db; padding: 0.8mm 2mm; text-align: right; }}
th {{ font-weight: 600; background: #f1f4f7; }}
.izq {{ text-align: left; }}
td.si {{ background: #dcefdc; }}
td.no {{ background: #f6dede; }}
.fila {{ display: flex; gap: 4mm; margin-bottom: 3mm; }}
figure {{ margin: 0; }}
.fila img {{ display: block; width: 127mm; height: 71.4mm; }}
.rejilla {{ display: grid; grid-template-columns: repeat(3, 84mm); gap: 2.5mm 3mm; }}
.chica img {{ display: block; width: 84mm; height: 47.25mm; }}
figcaption {{ font-size: 8pt; margin-top: 0.8mm; }}
figcaption span {{ color: #5a6878; margin-left: 1mm; }}
</style></head><body>
{hojas}
</body></html>"""
    origen = carpeta / f"{nombre}.html"
    origen.write_text(documento, encoding="utf-8")
    destino = carpeta / f"{nombre}.pdf"
    with chrome() as navegador:
        pagina = navegador.new_page()
        pagina.goto(origen.as_uri(), wait_until="load")
        pagina.pdf(path=str(destino), prefer_css_page_size=True, print_background=True)
    return destino
