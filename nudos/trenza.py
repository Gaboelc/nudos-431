"""La trenza de la cuerda (T20): 16 hilos, 2 sobre 2, como texturasTrenza de render/escena.js.

Solo usa numpy, así que la importan nudos/blender.py (la malla con relieve) y los guiones de
Blender (render/blender/, las texturas): los dos ven la misma trenza.

Las coordenadas son las de la malla de la cuerda: u avanza a lo largo de la cuerda, un mosaico
cada π·d·`mosaico` (con `mosaico` 1, como en las fichas, cada hilo va a 45°), y v da la vuelta,
de 0 a 1. En un mosaico, cada dirección tiene 8 hilos: los A suben con u (v + u constante) y los
B bajan (v − u constante). Cada hilo pasa por encima de dos y por debajo de dos.

Dos estilos de cuerda:
- **ficha:** los colores de la ficha (azul, crema, ámbar) con el hilo trazador de las fichas,
  una raya roja cortada en el medio de un hilo A.
- **real:** la cuerda de los filtros (T15e): negra, con dos hilos A vecinos amarillos y la trenza
  más estirada, unos 25° del eje en vez de 45° (medido en las fotos de entradas/t15e).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

HILOS = 8              # hilos de cada dirección en una vuelta


@dataclass(frozen=True)
class Estilo:
    """Cómo es una cuerda: sus colores (sRGB 0-255) y su trenza."""
    claro: tuple
    medio: tuple
    oscuro: tuple
    trazador: tuple
    trazador_claro: tuple | None = None   # el brillo del trazador; si falta, el trazador × 1,25
    mosaico: float = 1.0                  # largo de un mosaico, en π diámetros
    trazador_real: bool = False           # dos hilos A enteros (la cuerda real) o la raya de la ficha
    variacion: float = 0.06               # cuánto cambia el tono de un hilo a otro


ESTILOS = {
    "azul": Estilo((118, 156, 238), (42, 88, 200), (12, 30, 86), (196, 36, 44)),
    "crema": Estilo((255, 250, 238), (236, 225, 198), (138, 124, 96), (196, 36, 44)),
    "ambar": Estilo((255, 214, 140), (222, 140, 34), (92, 46, 6), (150, 30, 30)),
    # La cuerda de los filtros: negra, con el brillo azulado del poliéster, y el trazador amarillo
    # pálido de las fotos de T15e.
    "real": Estilo((92, 98, 112), (22, 23, 27), (4, 4, 6), (238, 226, 84), (252, 248, 178),
                   mosaico=2.0, trazador_real=True, variacion=0.10),
    # La segunda cuerda de un nudo de dos (la crema de la ficha), en el video: clara, con dos hilos
    # rojos, y la trenza de la cuerda real.
    "real-claro": Estilo((252, 250, 244), (228, 224, 212), (118, 110, 94), (196, 40, 36), (226, 70, 60),
                         mosaico=2.0, trazador_real=True, variacion=0.05),
    # El resaltado sobre la cuerda real: el ámbar de la ficha, con la trenza de la cuerda real.
    "real-ambar": Estilo((255, 214, 140), (222, 140, 34), (92, 46, 6), (150, 30, 30),
                         mosaico=2.0, variacion=0.08),
}


def celdas(u, v):
    """Lo que hay en cada punto (u, v) de la trenza: si es un hilo A, el índice del hilo (de 0 a
    HILOS − 1), la posición a lo ancho del hilo (0 a 1) y a lo largo de lo que se ve de él
    (0 a 1, de donde sale de abajo a donde vuelve a entrar), y la altura (0 en el surco, 1 en lo
    más alto)."""
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    pa, pb = HILOS * v + HILOS * u, HILOS * v - HILOS * u
    i, j = np.floor(pa), np.floor(pb)
    fa, fb = pa - i, pb - j
    m = np.mod(i + j, 4)
    es_a = m < 2
    ancho = np.where(es_a, fa, fb)
    largo = np.where(es_a, (m + fb) / 2, (m - 2 + fa) / 2)
    hilo = np.where(es_a, np.mod(i, HILOS), np.mod(j, HILOS)).astype(int)
    perfil = np.sqrt(np.maximum(0.0, 1 - (2 * ancho - 1) ** 2))
    puntas = np.abs(np.sin(np.pi * largo)) ** 0.55
    alto = perfil * (0.3 + 0.7 * puntas)
    return es_a, hilo, ancho, largo, alto, (i, j)


def relieve(u, v) -> np.ndarray:
    """La altura de la trenza para la geometría, de 0 a 1: la de `celdas`, más suave en el
    borde de cada hilo para que la malla no tenga aristas."""
    es_a, _, ancho, largo, _, _ = celdas(u, v)
    perfil = np.sqrt(np.maximum(0.0, 1 - (2 * ancho - 1) ** 2)) ** 0.7
    puntas = np.abs(np.sin(np.pi * largo)) ** 0.8
    return perfil * (0.25 + 0.75 * puntas)


def _hash(n):
    """Un número entre −1 y 1 que depende solo del entero n."""
    x = np.sin(np.asarray(n, float) * 12.9898 + 78.233) * 43758.5453
    return 2 * (x - np.floor(x)) - 1


def es_trazador(estilo: Estilo, es_a, hilo, ancho, ij) -> np.ndarray:
    if estilo.trazador_real:
        return es_a & (hilo <= 1)
    i, j = ij
    return es_a & (hilo == 0) & (np.abs(ancho - 0.5) < 0.2) & (np.mod(np.floor(j / 4), 2) == 0)


def texturas(estilo: Estilo, lado: int = 1024, hilos_finos: int = 12):
    """Las texturas de un mosaico de la trenza, de lado × lado (x a lo largo, y alrededor):
    - el color en sRGB de 0 a 1 (como texturasTrenza, con un poco de variación de un hilo a otro);
    - la altura fina, de 0 a 1: los filamentos de cada hilo (`hilos_finos` a lo ancho), para el
      relieve (bump) encima de la geometría;
    - la máscara de los hilos A (1) y B (0), para la dirección del brillo de filamento.
    Las tres en float32, (lado, lado)."""
    v, u = np.meshgrid((np.arange(lado) + 0.5) / lado, (np.arange(lado) + 0.5) / lado, indexing="ij")
    es_a, hilo, ancho, largo, alto, ij = celdas(u, v)
    fino = 0.9 + 0.1 * np.cos(ancho * np.pi * hilos_finos)
    k = alto * fino
    T, M, L, R = (np.asarray(c, float) / 255 for c in (estilo.claro, estilo.medio, estilo.oscuro,
                                                        estilo.trazador))
    Rc = (np.asarray(estilo.trazador_claro, float) / 255 if estilo.trazador_claro is not None
          else np.minimum(1, R * 1.25))
    tr = es_trazador(estilo, es_a, hilo, ancho, ij)
    # Cada hilo con su tono, un poco distinto (los de A y los de B, cada uno con su número).
    tono = 1 + estilo.variacion * _hash(hilo + np.where(es_a, 0, HILOS))
    base = np.where(tr[..., None], R, M * tono[..., None])
    alto_c = np.where(tr[..., None], Rc, T * tono[..., None])
    t1 = np.minimum(1, k / 0.55)[..., None]
    t2 = np.maximum(0, (k - 0.55) / 0.45)[..., None]
    a = L + (base - L) * t1
    color = np.clip(a + (alto_c - a) * t2 * 0.6, 0, 1)
    finos = (0.5 + 0.5 * np.cos(ancho * np.pi * 2 * hilos_finos)) * np.minimum(1, alto * 2)
    return color.astype(np.float32), finos.astype(np.float32), es_a.astype(np.float32)


def direcciones_hilos(T: np.ndarray, alrededor: np.ndarray, mosaico: float = 1.0):
    """La dirección de los hilos A y B en cada vértice: T es la dirección de la cuerda y
    `alrededor` la de v creciente (las dos unitarias, (..., 3)). En el plano, un hilo A va
    (mosaico, −1) en (largo, vuelta) y uno B, (mosaico, 1), con las dos escalas en diámetros."""
    a = mosaico * T - alrededor
    b = mosaico * T + alrededor
    a /= np.linalg.norm(a, axis=-1, keepdims=True)
    b /= np.linalg.norm(b, axis=-1, keepdims=True)
    return a, b
