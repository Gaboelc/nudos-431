"""Hoja de revisión: todos los pasos de un nudo en una sola imagen.

Render rápido con numpy: la cuerda como un tubo de esferas, con sombra y
oscurecimiento de contacto sobre la mesa. Sirve para revisar el modelo, no para
imprimir.

Sobre el tubo de la cabeza de turco, la vista desde arriba no sirve para revisar decenas de
cruces: la hoja dibuja además el tubo desenrollado (mapa()), con cada cruce y su etiqueta.

De los anfitriones, la hoja dibuja el destorcedor, en gris; la estaca, el poste, la cruz y los
palos paralelos, color madera, y el cabo, color crema. Sobre el cabo, además, el cabo
desenrollado (mapa()). Son parte de la cuerda que se revisa: sin ellos no se ve qué rodea la
cuerda. El poste, los palos y el cabo se dibujan solo dentro del encuadre, más un margen. El tubo de
la cabeza de turco no se dibuja: para eso está el tubo desenrollado.

El adujado, sin anfitrión, lleva además la aduja vista desde abajo (desde_abajo()): desde arriba
no se ve la cara de abajo de las vueltas ni del seno que la rodea.

En el puño de mono, que no tiene anfitrión, la vista desde arriba no muestra la mitad de las
vueltas: la hoja lleva además el puño desenrollado (mapa_puno()), mirado desde su centro.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

from .libre import R

AZUL = np.array([0.10, 0.25, 0.75])
CREMA = np.array([0.93, 0.89, 0.78])
COLORES = {"azul": AZUL, "crema": CREMA}   # los de nudos/spec.py COLORES
AMBAR = np.array([0.95, 0.55, 0.12])
REMATE = np.array([0.35, 0.06, 0.06])
GRIS = np.array([0.62, 0.64, 0.67])   # el destorcedor
MADERA = np.array([0.78, 0.64, 0.48])  # la estaca, como los palos de render/escena.js
COLOR_PARADO = {"destorcedor": GRIS, "estaca": MADERA}
RADIO_SUPERFICIE = 0.25   # las esferas con que se dibuja la superficie del anfitrión parado
RADIO_PALO, PASO_PALO = 0.7, 0.2   # las del poste y la cruz, más grandes: son más largos
MARGEN_PALO = 2.0         # diámetros de palo que se dibujan fuera del encuadre
MESA = np.array([0.80, 0.81, 0.80])
ANCHO = 520          # píxeles de cada cuadro
COLUMNAS = 4
MARGEN_AUTO = 1.5    # diámetros alrededor del nudo cuando no hay encuadre


def hoja(datos: dict, vista: str = "arriba", anfitrion: dict | None = None,
         altura: float | None = None) -> Image.Image:
    """Un cuadro por paso. `datos` es el contenido de modelo.json y `vista` es
    «arriba» o la inclinación de la cámara en grados. `anfitrion` es el del nudo, como lo
    recibe render/escena.js (nudos/anfitrion.py, datos()): modelo.json no lo lleva.
    `altura` es la z en la que se centra la vista inclinada; sin ella, la de la cuerda de
    estos pasos (_altura). Quien dibuja los pasos uno por uno la pasa, para que el cuadro
    no salte de un paso a otro."""
    x0, x1, y0, y1 = _encuadre(datos)
    solido = _parado(anfitrion) or _palos(anfitrion, x0, x1, y0, y1)
    ppd = ANCHO / (x1 - x0)
    alto = int(round((y1 - y0) * ppd))
    angulo = "arriba" if vista == "arriba" else float(vista)
    centro = np.array([(x0 + x1) / 2, (y0 + y1) / 2,
                       0.0 if angulo == "arriba"
                       else altura if altura is not None else _altura(datos, x0, x1, y0, y1)])
    cuadros = []
    for p in datos["pasos"]:
        im = Image.fromarray(_cuadro(_cuerdas(datos, p), angulo, ANCHO, alto, ppd, centro,
                                     solido=solido))
        ImageDraw.Draw(im).text((12, 10), f"Paso {p['n']}", fill=(30, 30, 30))
        cuadros.append(im)
    filas = (len(cuadros) + COLUMNAS - 1) // COLUMNAS
    out = Image.new("RGB", (COLUMNAS * ANCHO, filas * alto), (255, 255, 255))
    for k, c in enumerate(cuadros):
        out.paste(c, ((k % COLUMNAS) * ANCHO, (k // COLUMNAS) * alto))
    return out


def _altura(datos: dict, x0: float, x1: float, y0: float, y1: float) -> float:
    """Altura de la cuerda dentro del encuadre, en la mediana de todos los pasos. La vista
    inclinada se centra ahí: un nudo sobre el poste queda muy por encima de la mesa y, con la
    cámara centrada en z = 0, saldría del cuadro."""
    X = np.vstack([np.asarray(p["puntos"], float) for p in datos["pasos"]])
    dentro = (X[:, 0] >= x0) & (X[:, 0] <= x1) & (X[:, 1] >= y0) & (X[:, 1] <= y1)
    return float(np.median(X[dentro, 2])) if dentro.any() else 0.0


def desde_abajo(datos: dict) -> dict:
    """Los mismos pasos girados media vuelta sobre el eje x, como se da vuelta la aduja hacia
    quien la mira: lo de abajo queda arriba y lo de delante, atrás. Se dibujan con hoja() como
    cualquier otro paso. El giro es rígido y la cuerda queda apoyada en la mesa."""
    def girar(p: dict) -> dict:
        X = np.asarray(p["puntos"], float).copy()
        X[:, 1] *= -1
        X[:, 2] = X[:, 2].max() + R - X[:, 2]
        return {**p, "puntos": X.tolist()}

    out = {**datos, "pasos": [girar(p) for p in datos["pasos"]]}
    if datos.get("encuadre"):
        y0, y1 = datos["encuadre"]["y"]
        out["encuadre"] = {"x": datos["encuadre"]["x"], "y": [-y1, -y0]}
    return out


def _encuadre(datos: dict) -> tuple[float, float, float, float]:
    if datos.get("encuadre"):
        (x0, x1), (y0, y1) = datos["encuadre"]["x"], datos["encuadre"]["y"]
        return x0, x1, y0, y1
    todos = np.vstack([np.asarray(p["puntos"], float)[:, :2] for p in datos["pasos"]])
    (x0, y0), (x1, y1) = todos.min(0) - MARGEN_AUTO, todos.max(0) + MARGEN_AUTO
    return float(x0), float(x1), float(y0), float(y1)


def _cuerdas(datos: dict, p: dict) -> list[tuple[np.ndarray, float, np.ndarray, list | None]]:
    """Las cuerdas de un paso de modelo.json: sus puntos, su radio, su color y el tramo
    resaltado a lo largo de esa cuerda (None si no está en ella)."""
    X = np.asarray(p["puntos"], float)
    if "cuerdas" not in datos:
        return [(X, R, AZUL, p["resaltado"])]
    out = []
    for c, (i0, i1) in zip(datos["cuerdas"], p["tramos"]):
        hl = p["resaltado"]
        s0, s1 = i0 * p["h"], i1 * p["h"]
        if hl is not None:
            hl = [v - s0 for v in hl] if s0 <= (hl[0] + hl[1]) / 2 <= s1 else None
        out.append((X[i0:i1 + 1], c["grosor"] * R, COLORES[c["color"]], hl))
    return out


def _parado(anfitrion: dict | None) -> tuple[np.ndarray, np.ndarray, float] | None:
    """Puntos sobre la superficie del destorcedor o la estaca, para dibujarla con esferas de
    RADIO_SUPERFICIE: el costado, en anillos, y la tapa, en anillos concéntricos, con su
    color y el radio de esas esferas. None si el nudo no tiene ninguno de los dos."""
    if not anfitrion or anfitrion.get("tipo") not in COLOR_PARADO:
        return None
    rs, paso = RADIO_SUPERFICIE, 0.12
    r, alto = anfitrion["radio"] - rs, anfitrion["alto"] - rs
    puntos = []
    for z in np.arange(rs, alto + 1e-9, paso):
        a = np.linspace(0, 2 * math.pi, max(12, int(2 * math.pi * r / paso)), endpoint=False)
        puntos.append(np.column_stack([r * np.cos(a), r * np.sin(a), np.full(len(a), z)]))
    for ri in np.arange(r, 0, -paso):
        a = np.linspace(0, 2 * math.pi, max(6, int(2 * math.pi * ri / paso)), endpoint=False)
        puntos.append(np.column_stack([ri * np.cos(a), ri * np.sin(a), np.full(len(a), alto)]))
    puntos.append(np.array([[0.0, 0.0, alto]]))
    return np.vstack(puntos), COLOR_PARADO[anfitrion["tipo"]], RADIO_SUPERFICIE


def _palos(anfitrion: dict | None, x0: float, x1: float, y0: float,
           y1: float) -> tuple[np.ndarray, np.ndarray, float] | None:
    """Puntos sobre la superficie del poste, de los dos palos de la cruz o de los palos
    paralelos, color madera, o del cabo, color crema, para dibujarlos con esferas de RADIO_PALO.
    Cada palo se corta en el encuadre, más MARGEN_PALO, y lleva tapa donde termina dentro de ese
    tramo. None si el nudo no tiene ninguno."""
    if not anfitrion or anfitrion.get("tipo") not in ("poste", "cruz", "palos", "cabo"):
        return None
    r = anfitrion["radio"]
    m = MARGEN_PALO
    if anfitrion["tipo"] == "cabo":
        # El cabo, color crema como la cuerda que es, de -largo hasta la punta en x = 0.
        punto = _palo("x", max(-anfitrion["largo"], x0 - m), 0.0, 0.0, anfitrion["z"], r,
                      tapas=(-anfitrion["largo"] >= x0 - m, True))
        return punto, CREMA, RADIO_PALO
    if anfitrion["tipo"] == "poste":
        palos = [("x", anfitrion["desde"], anfitrion["hasta"], x0 - m, x1 + m,
                  anfitrion["y"], anfitrion["z"])]
    elif anfitrion["tipo"] == "palos":
        # uno junto al otro, a lo largo de x, cada uno en su y
        mitad = anfitrion["largo"] / 2
        palos = [("x", -mitad, mitad, x0 - m, x1 + m, y, anfitrion["z"]) for y in anfitrion["y"]]
    else:
        mitad = anfitrion["largo"] / 2
        # el de abajo va a lo largo de y, en x = 0; el de arriba, a lo largo de x, en y = 0
        palos = [("y", -mitad, mitad, y0 - m - 2 * r, y1 + m + 2 * r, 0.0, anfitrion["z_abajo"]),
                 ("x", -mitad, mitad, x0 - m, x1 + m, 0.0, anfitrion["z_arriba"])]
    puntos = [_palo(eje, max(a, c0), min(b, c1), lado, z, r, tapas=(a >= c0, b <= c1))
              for eje, a, b, c0, c1, lado, z in palos if min(b, c1) > max(a, c0)]
    if not puntos:
        return None
    return np.vstack(puntos), MADERA, RADIO_PALO


def _palo(eje: str, a: float, b: float, lado: float, z: float, radio: float,
          tapas: tuple[bool, bool]) -> np.ndarray:
    """Un cilindro acostado a lo largo de x o de y, de a a b, con el eje en `lado` (la otra
    coordenada) y a la altura z: anillos en el costado y, si se pide, anillos en las tapas."""
    rs, paso = RADIO_PALO, PASO_PALO
    r = radio - rs
    n = max(12, int(2 * math.pi * r / paso))
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False)
    largo = np.arange(a + rs, b - rs + 1e-9, paso)
    u = np.repeat(largo, n)                                  # a lo largo del palo
    v = lado + np.tile(r * np.cos(ang), len(largo))          # de lado
    w = z + np.tile(r * np.sin(ang), len(largo))             # hacia arriba
    partes = [(u, v, w)]
    for extremo, hay in zip((a + rs, b - rs), tapas):
        if not hay:
            continue
        for ri in np.arange(r, 0, -paso):
            k = max(6, int(2 * math.pi * ri / paso))
            t = np.linspace(0, 2 * math.pi, k, endpoint=False)
            partes.append((np.full(k, extremo), lado + ri * np.cos(t), z + ri * np.sin(t)))
        partes.append((np.array([extremo]), np.array([lado]), np.array([z])))
    u, v, w = (np.concatenate(c) for c in zip(*partes))
    return np.column_stack([u, v, w] if eje == "x" else [v, u, w])


def _densificar(X, paso=0.06):
    seg = np.linalg.norm(np.diff(X, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    sg = np.arange(0, s[-1], paso)
    return np.stack([np.interp(sg, s, X[:, k]) for k in range(3)], 1), sg, s[-1]


def _base(vista):
    """Ejes de la cámara (filas) en coordenadas del mundo."""
    if vista == "arriba":
        zc = np.array([0.0, 0.0, 1.0])
    else:
        t = np.radians(vista)
        zc = np.array([0.0, -np.sin(t), np.cos(t)])
    arriba = np.array([0.0, 1.0, 0.0])
    xc = np.cross(arriba, zc)
    xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    return np.stack([xc, yc, zc])


def _esferas(C, W, H, ppd, radios, normales=True):
    """Dibuja una esfera en cada punto, del radio de su cuerda, con z-buffer."""
    zb = np.full((H, W), -np.inf)
    idx = np.full((H, W), -1, int)
    nrm = np.zeros((H, W, 3)) if normales else None
    for m in range(len(C)):
        radio = float(radios[m])
        rad = radio * ppd
        px, py = W / 2 + C[m, 0] * ppd, H / 2 - C[m, 1] * ppd
        x0, x1 = int(max(0, np.floor(px - rad))), int(min(W, np.ceil(px + rad) + 1))
        y0, y1 = int(max(0, np.floor(py - rad))), int(min(H, np.ceil(py + rad) + 1))
        if x0 >= x1 or y0 >= y1:
            continue
        xs = (np.arange(x0, x1) + 0.5 - px) / ppd
        ys = -(np.arange(y0, y1) + 0.5 - py) / ppd
        dx, dy = np.meshgrid(xs, ys)
        r2 = dx * dx + dy * dy
        msk = r2 < radio * radio
        if not msk.any():
            continue
        dz = np.sqrt(np.maximum(radio * radio - r2, 0))
        prof = C[m, 2] + dz
        win = zb[y0:y1, x0:x1]
        upd = msk & (prof > win)
        win[upd] = prof[upd]
        idx[y0:y1, x0:x1][upd] = m
        if normales:
            nw = nrm[y0:y1, x0:x1]
            nw[upd] = np.stack([dx[upd], dy[upd], dz[upd]], 1) / radio
    return zb, idx, nrm


def _cuadro(cuerdas, vista, W, H, ppd, centro, luz=(-0.5, 0.6, 1.0), solido=None):
    """`cuerdas` es la lista de _cuerdas. Cada una se densifica por separado: entre el final
    de una y el comienzo de la siguiente no hay cuerda. `solido` son los puntos de la
    superficie del anfitrión, con su color y el radio de sus esferas (_parado, _palos)."""
    partes = []
    for X, radio, color, resaltado in cuerdas:
        Xd, sd, L = _densificar(X)
        col = np.tile(color, (len(Xd), 1))
        if resaltado is not None:
            col[(sd >= resaltado[0]) & (sd <= resaltado[1])] = AMBAR
        col[sd > L - 0.8 * (radio / R)] = REMATE
        partes.append((Xd, col, np.full(len(Xd), radio)))
    if solido is not None:
        puntos, color, radio = solido
        partes.append((puntos, np.tile(color, (len(puntos), 1)), np.full(len(puntos), radio)))
    Xd = np.vstack([x for x, _, _ in partes])
    col = np.vstack([c for _, c, _ in partes])
    radios = np.concatenate([r for _, _, r in partes])
    B = _base(vista)
    C = (Xd - centro) @ B.T
    zb, idx, nrm = _esferas(C, W, H, ppd, radios)
    cuerda = idx >= 0

    # posición en el mundo de cada píxel (cuerda o mesa)
    ys, xs = np.mgrid[0:H, 0:W]
    cx = (xs + 0.5 - W / 2) / ppd
    cy = -(ys + 0.5 - H / 2) / ppd
    n_c = B @ np.array([0, 0, 1.0])
    p0 = B @ (np.zeros(3) - centro)
    tz = (n_c @ p0 - n_c[0] * cx - n_c[1] * cy) / n_c[2]
    cz = np.where(cuerda, zb, tz)
    Pw = np.stack([cx, cy, cz], -1) @ B + centro

    # mapa de sombra en la dirección de la luz
    Ld = np.array(luz, float)
    Ld /= np.linalg.norm(Ld)
    up = np.array([0, 1.0, 0]) if abs(Ld[1]) < 0.9 else np.array([1.0, 0, 0])
    lx = np.cross(up, Ld)
    lx /= np.linalg.norm(lx)
    ly = np.cross(Ld, lx)
    BL = np.stack([lx, ly, Ld])
    CL = (Xd - centro) @ BL.T
    sppd = 14.0
    ext = np.abs(CL[:, :2]).max(0) + 2
    SW, SH = int(2 * ext[0] * sppd), int(2 * ext[1] * sppd)
    szb, _, _ = _esferas(CL, SW, SH, sppd, radios, normales=False)
    PL = (Pw - centro) @ BL.T
    u = np.clip((SW / 2 + PL[..., 0] * sppd).astype(int), 0, SW - 1)
    v = np.clip((SH / 2 - PL[..., 1] * sppd).astype(int), 0, SH - 1)
    ocl = szb[v, u]
    lit = ((~np.isfinite(ocl)) | (ocl < PL[..., 2] + 0.06)).astype(float)
    lit = gaussian_filter(lit, sigma=max(1.0, 0.08 * ppd))

    # oscurecimiento de contacto sobre la mesa
    dist, cual = cKDTree(Xd).query(Pw.reshape(-1, 3), k=1)
    dist = (dist - radios[cual]).reshape(H, W)
    ao = 1 - 0.45 * np.exp(-np.maximum(dist, 0) / 0.3)

    img = np.zeros((H, W, 3))
    mesa = ~cuerda
    img[mesa] = MESA * (0.55 + 0.45 * lit[mesa])[:, None] * ao[mesa][:, None]
    n_w = nrm @ B
    lam = np.clip((n_w * Ld).sum(-1), 0, 1)
    Hv = Ld + B[2]
    Hv /= np.linalg.norm(Hv)
    brillo = np.clip((n_w * Hv).sum(-1), 0, 1) ** 28
    base = col[np.maximum(idx, 0)]
    luz_total = (0.28 + 0.72 * lam * lit)[..., None]
    rimg = base * luz_total + 0.22 * (brillo * lit)[..., None]
    img[cuerda] = rimg[cuerda]
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    return (img * 255).astype(np.uint8)


# --------------------------------------------------------------------------
# El tubo desenrollado
# --------------------------------------------------------------------------
PPD_MAPA = 22          # píxeles por diámetro en el mapa del tubo
COLUMNAS_MAPA = 2
CORTE_CABO = 230.0     # dónde da la vuelta el mapa del cabo, en grados: atrás y abajo


def mapa(datos: dict, tubo, senos: int | None = None) -> Image.Image:
    """Un cuadro por paso con el tubo desenrollado: alrededor del tubo hacia la derecha, desde
    el seno A, y a lo largo del eje hacia arriba. Se ve el nudo entero aunque en el paso esté
    girado. Lo que va más lejos del eje se dibuja encima, más oscuro; lo que agrega el paso,
    en ámbar; cada cruce lleva su etiqueta. `tubo` es el sólido (nudos/anfitrion.py, Tubo) y
    `senos`, los del nudo: el mapa da la vuelta donde la da el lugar de los cruces.

    Sin `senos`, `tubo` es el cabo del refuerzo (Cabo): alrededor del cabo hacia la derecha,
    con el ángulo creciendo hacia quien ata, y el mapa da la vuelta atrás y abajo (CORTE_CABO),
    donde no hay cruces. Sus cruces se guardan en la mesa, así que cada etiqueta va en el punto
    de la cuerda más cercano a ese lugar."""
    C = 2 * math.pi * tubo.rb
    cabo = senos is None
    corte = math.radians(CORTE_CABO) * tubo.rb if cabo else C / (4 * senos)

    def sobre(x, r):
        dentro = (x > -tubo.largo) & (x < 0.0) if cabo else np.abs(x) < tubo.largo / 2
        return (r < tubo.rb + 1.8) & dentro

    todos = []
    for p in datos["pasos"]:
        X = np.asarray(p["puntos"], float)
        x, th, r = tubo.cilindricas(X)
        todos.append(x[sobre(x, r)])
    xs = np.concatenate(todos)
    x0, x1 = float(xs.min()) - 1.5, float(xs.max()) + 1.5
    W, H = int((C + 2) * PPD_MAPA), int((x1 - x0) * PPD_MAPA)
    cuadros = []
    for p in datos["pasos"]:
        im = Image.new("RGB", (W, H), (246, 246, 243))
        d = ImageDraw.Draw(im)
        X = np.asarray(p["puntos"], float)
        x, th, r = tubo.cilindricas(X)
        if cabo:
            u = (th * tubo.rb - corte) % C + corte
        else:
            u = ((math.radians(p.get("giro") or 0.0) - np.unwrap(th)) * tubo.rb - corte) % C + corte
        s = np.arange(len(X)) * p["h"]
        hl = p["resaltado"] or [-1, -1]
        en_tubo = sobre(x, r)

        def px(ui, xi):
            return ((ui - corte + 1) * PPD_MAPA, (x1 - xi) * PPD_MAPA)
        for borde in (corte, corte + C):
            d.line([px(borde, x0), px(borde, x1)], fill=(205, 205, 200), width=1)
        tramos = []
        for i in range(len(X) - 1):
            if en_tubo[i] and en_tubo[i + 1] and abs(u[i + 1] - u[i]) < C / 2:
                tramos.append(((r[i] + r[i + 1]) / 2, i))
        for alto, i in sorted(tramos):
            k = float(np.clip(alto - tubo.rb, 0, 1))
            base = AMBAR if hl[0] <= s[i] <= hl[1] else AZUL
            color = base * (0.55 + 0.45 * (1 - k)) + (1 - k) * 0.35 * (1 - base)
            c = tuple(int(255 * v) for v in np.clip(color, 0, 1))
            d.line([px(u[i], x[i]), px(u[i + 1], x[i + 1])], fill=(40, 40, 40), width=int(PPD_MAPA * 0.95))
            d.line([px(u[i], x[i]), px(u[i + 1], x[i + 1])], fill=c, width=int(PPD_MAPA * 0.75))
        for et, (cx, cu) in p.get("cruces", {}).items():
            if cabo:
                # En la mesa: el punto de la cuerda sobre el cabo más cercano a ese lugar.
                d2 = np.where(en_tubo, (X[:, 0] - cx) ** 2 + (X[:, 1] - cu) ** 2, np.inf)
                i = int(d2.argmin())
                cx, cu = x[i], u[i]
            a, b = px(cu, cx)
            d.rectangle([a - 9, b - 7, a + 9, b + 7], fill=(255, 255, 255), outline=(60, 60, 60))
            d.text((a - 6 if len(et) > 1 else a - 3, b - 6), et, fill=(150, 20, 20))
        titulo = "cabo desenrollado, desde atrás" if cabo else "tubo desenrollado, desde el seno A"
        d.text((10, 8), f"Paso {p['n']} · {titulo}", fill=(30, 30, 30))
        cuadros.append(im)
    filas = (len(cuadros) + COLUMNAS_MAPA - 1) // COLUMNAS_MAPA
    out = Image.new("RGB", (COLUMNAS_MAPA * W, filas * H), (255, 255, 255))
    for k, c in enumerate(cuadros):
        out.paste(c, ((k % COLUMNAS_MAPA) * W, (k // COLUMNAS_MAPA) * H))
    return out


# --------------------------------------------------------------------------
# El puño de mono desenrollado
# --------------------------------------------------------------------------
PPD_PUNO = 90           # píxeles por radián en el puño desenrollado


def mapa_puno(datos: dict, centros: list, radios: list[tuple[float, float]]) -> Image.Image:
    """Un cuadro por paso con el puño de mono desenrollado (nudos/plantillas/puno.py): cada punto
    de las vueltas se mira desde el centro del puño (`centros`, uno por paso) y se dibuja a la
    distancia del polo que le corresponde, alrededor de él (proyección azimutal equidistante);
    el borde del cuadro es la esquina opuesta al polo, por donde no pasa nada. Lo que va más lejos
    del centro se dibuja encima, más oscuro; lo que agrega el paso, en ámbar; cada cruce de las
    vueltas lleva su etiqueta. Solo se dibuja lo que va sobre las vueltas: entre `radios` (lo
    más cerca y lo más lejos del centro de cada paso)."""
    from .plantillas.puno import POLO, _marco_polo, direccion_del_lugar, LEJOS_CARA
    e1, e2 = _marco_polo()
    lado = int(2 * math.pi * PPD_PUNO) + 40

    def plano(d):
        d = np.atleast_2d(d)
        th = np.arccos(np.clip(d @ POLO, -1, 1))
        az = np.arctan2(d @ e2, d @ e1)
        return (lado / 2 + PPD_PUNO * th * np.cos(az), lado / 2 - PPD_PUNO * th * np.sin(az)), th

    cuadros = []
    for p, centro, (r0, r1) in zip(datos["pasos"], centros, radios):
        im = Image.new("RGB", (lado, lado), (246, 246, 243))
        d = ImageDraw.Draw(im)
        d.ellipse([20, 20, lado - 20, lado - 20], outline=(205, 205, 200))
        X = np.asarray(p["puntos"], float) - np.asarray(centro, float)
        r = np.linalg.norm(X, axis=1)
        D = X / np.maximum(r, 1e-9)[:, None]
        (u, v), th = plano(D)
        s = np.arange(len(X)) * p["h"]
        hl = p["resaltado"] or [-1, -1]
        sobre = (r > r0 - 0.6) & (r < r1 + 1.6)
        tramos = [(float(r[i] + r[i + 1]) / 2, i) for i in range(len(X) - 1)
                  if sobre[i] and sobre[i + 1] and abs(u[i + 1] - u[i]) + abs(v[i + 1] - v[i]) < 40]
        for alto, i in sorted(tramos):
            k = float(np.clip((alto - r0) / max(r1 - r0, 1e-6), 0, 1))
            base = AMBAR if hl[0] <= s[i] <= hl[1] else AZUL
            color = base * (0.55 + 0.45 * (1 - k)) + (1 - k) * 0.35 * (1 - base)
            c = tuple(int(255 * x) for x in np.clip(color, 0, 1))
            d.line([(u[i], v[i]), (u[i + 1], v[i + 1])], fill=(40, 40, 40), width=11)
            d.line([(u[i], v[i]), (u[i + 1], v[i + 1])], fill=c, width=8)
        for et, (cx, cy) in p.get("cruces", {}).items():
            if cx < LEJOS_CARA / 2:
                continue   # el nudo simple o la mesa
            (a, b), _ = plano(direccion_del_lugar((cx, cy)))
            a, b = float(a[0]), float(b[0])
            d.rectangle([a - 9, b - 7, a + 9, b + 7], fill=(255, 255, 255), outline=(60, 60, 60))
            d.text((a - 6 if len(et) > 1 else a - 3, b - 6), et, fill=(150, 20, 20))
        d.text((10, 8), f"Paso {p['n']} · puño desenrollado, desde la esquina de atrás a la derecha, arriba",
               fill=(30, 30, 30))
        cuadros.append(im)
    filas = (len(cuadros) + COLUMNAS_MAPA - 1) // COLUMNAS_MAPA
    out = Image.new("RGB", (COLUMNAS_MAPA * lado, filas * lado), (255, 255, 255))
    for k, c in enumerate(cuadros):
        out.paste(c, ((k % COLUMNAS_MAPA) * lado, (k // COLUMNAS_MAPA) * lado))
    return out
