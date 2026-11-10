"""Plantilla del amarre cuadrado, sobre dos palos cruzados en ángulo recto (anfitrión «cruz»).

El método es el del diseño de T7 en tasks/plan.md: un ballestrinque en el palo de abajo,
las vueltas alrededor de los dos palos, los ahorcados entre los palos y un ballestrinque
de cierre en el palo de arriba.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Cuántas vueltas y ahorcados acepta la plantilla. El manual de la Tropa pide «tres o
# cuatro» de cada uno; el margen deja probar, y un número se escribe en letras.
NUMEROS = {2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis"}
_CAMPOS = {"tipo", "vueltas", "ahorcados", "inicio", "cierre"}
_CAMPOS_EXTREMO = {"poste", "lado"}
# De qué lado del otro palo puede ir un ballestrinque. El palo de abajo va hacia el fondo
# de la mesa, así que el de arriba lo parte en delante (hacia quien ata) y detrás; el de
# arriba va de izquierda a derecha, y el de abajo lo parte en izquierda y derecha.
LADOS = {"abajo": ("delante", "detras"), "arriba": ("izquierda", "derecha")}


@dataclass(frozen=True)
class Extremo:
    """Dónde va un ballestrinque: en qué palo y de qué lado del otro palo."""
    poste: str   # «abajo» o «arriba»
    lado: str    # uno de LADOS[poste]


@dataclass(frozen=True)
class AmarreCuadrado:
    vueltas: int     # alrededor de los dos palos
    ahorcados: int   # entre los palos, alrededor de las vueltas
    inicio: Extremo  # ballestrinque de inicio
    cierre: Extremo  # ballestrinque de cierre

    tipo = "amarre-cuadrado"
    ANFITRION = "cruz"
    # El error común que sabe construir, con el primer hito desde el que se ve.
    # Los ahorcados por encima del palo de arriba, en lugar de entre los palos.
    VARIANTES = {"ahorcados-por-fuera": "ahorcado-1"}

    @classmethod
    def leer(cls, datos: dict, falla) -> AmarreCuadrado:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        numeros = {}
        for clave in ("vueltas", "ahorcados"):
            v = datos.get(clave)
            if not isinstance(v, int) or isinstance(v, bool) or v not in NUMEROS:
                raise falla(f"«{clave}» es un número entero de {min(NUMEROS)} a {max(NUMEROS)}")
            numeros[clave] = v
        inicio = _extremo(datos.get("inicio"), "inicio", falla)
        cierre = _extremo(datos.get("cierre"), "cierre", falla)
        # Es el método del manual de la Tropa. Empezar en el palo de arriba se agrega
        # cuando un nudo lo necesite.
        if inicio.poste != "abajo" or cierre.poste != "arriba":
            raise falla("por ahora el ballestrinque de inicio va en el palo de abajo y el "
                        "de cierre en el de arriba")
        return cls(inicio=inicio, cierre=cierre, **numeros)

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, con su posición en la cuerda. `vueltas` es lo mismo que
        la última vuelta y `ahorcados` que el último ahorcado: así un paso que dice
        «hasta: vueltas» sigue valiendo si cambia el número de vueltas."""
        out = {"inicio-1": 0, "inicio": 1}
        k = 1
        for nombre, total in (("vuelta", self.vueltas), ("ahorcado", self.ahorcados)):
            for i in range(1, total + 1):
                k += 1
                out[f"{nombre}-{i}"] = k
            out[f"{nombre}s"] = k
        out["cierre-1"] = k + 1
        out["cierre"] = k + 2
        return out

    def medidas(self) -> dict[str, str]:
        return {"vueltas": NUMEROS[self.vueltas], "ahorcados": NUMEROS[self.ahorcados]}


def _extremo(datos, clave: str, falla) -> Extremo:
    if not isinstance(datos, dict) or set(datos) != _CAMPOS_EXTREMO:
        raise falla(f"«{clave}» lleva «poste» (abajo o arriba) y «lado»")
    poste, lado = datos["poste"], datos["lado"]
    if poste not in LADOS:
        raise falla(f"en «{clave}», «poste» es abajo o arriba")
    if lado not in LADOS[poste]:
        raise falla(f"en «{clave}», sobre el palo de {poste} «lado» es {' o '.join(LADOS[poste])}")
    return Extremo(poste, lado)


# --------------------------------------------------------------------------
# La cuerda entera
# --------------------------------------------------------------------------
# Medidas en diámetros de cuerda; ver «Cómo se hizo» de T7 en tasks/plan.md.
PASO_VUELTAS = 1.1      # entre dos vueltas vecinas sobre un palo
HOLGURA = 1.05          # de una esquina al ahorcado que pasa por fuera
MARGEN = 1.0            # lo que sigue recto un ahorcado más allá de la última esquina que cruza
CARRIL = 1.1            # entre los carriles de un ballestrinque: dos vueltas, el firme y el chicote
RADIO_ESQUINA = 1.3     # radio con que se redondean las esquinas de la cuerda
R_CUERDA = 0.5          # radio de la cuerda
# Hacia dónde sale el resto de la cuerda en cada hito, sobre la mesa (antes de reflejar).
SALIDAS = {"inicio-1": (-0.6, -0.8), "inicio": (0.6, -0.8), "vuelta": (0.8, -0.6),
           "ahorcado": (1.0, -0.2), "cierre-1": (0.3, -1.0)}


@dataclass
class Cuerda:
    """La cuerda entera de un amarre, calculada una sola vez.

    `puntos` y `zonas` la recorren desde el chicote corto del ballestrinque de inicio.
    `hitos` dice en qué punto termina cada hito; `restos` da, para cada hito, los puntos de
    control de lo que sigue de la cuerda en ese paso, que sale del amarre y cae a la mesa.
    `secuencias` da la secuencia de cruces del método hasta cada hito."""
    puntos: np.ndarray
    zonas: np.ndarray
    hitos: dict[str, int]
    restos: dict[str, np.ndarray]
    secuencias: dict[str, tuple[str, ...]]
    alias: dict[str, str]   # «vueltas» y «ahorcados»: el hito al que equivalen


def cuerda(p: AmarreCuadrado, cruz) -> Cuerda:
    """Calcula la cuerda entera del amarre sobre la cruz (nudos/anfitrion.py)."""
    from .trazo import ABAJO, ARRIBA, CINTURA, MESA, Plano, Trazo
    n, m = p.vueltas, p.ahorcados
    rb, zb, zt = cruz.rb, cruz.zb, cruz.zt
    z_alta, z_baja = zt - 0.5, zb + 1.0          # entre estas alturas las esquinas bajan rectas
    medio = (zb + zt) / 2                        # donde se tocan los palos
    a0 = rb + 0.05                               # la vuelta más pegada al otro palo
    # Cada vuelta nueva va por fuera de la anterior sobre el palo de arriba y por dentro
    # sobre el de abajo, como en las referencias.
    A = [None] + [a0 + (k - 1) * PASO_VUELTAS for k in range(1, n + 2)]   # sobre el de arriba
    Bt = [None] + [a0 + (n - k) * PASO_VUELTAS for k in range(1, n + 1)]  # bajo el de abajo, detrás
    # El ballestrinque de inicio va delante, pegado al palo de arriba: su primer carril es lo
    # más cerca que deja el palo de arriba sobre el de abajo.
    c1 = math.sqrt(rb ** 2 - (zt - zb - rb) ** 2) + 0.02
    carriles = [-(c1 + k * CARRIL) for k in range(4)]   # vuelta 1, firme, chicote, vuelta 2
    # Delante, las vueltas pasan bajo el palo de abajo por fuera del ballestrinque.
    Bd = [None] + [-carriles[3] + HOLGURA + (n - k) * PASO_VUELTAS for k in range(1, n + 1)]
    centro_ab, centro_ar = np.array([0.0, zb]), np.array([0.0, zt])
    t = Trazo()

    def sobre_arriba(x, Q, sentido):   # en el corte del palo de arriba, en x
        t.rodear(centro_ar, Plano(0, x), Q, sentido, ARRIBA, ARRIBA, rb)

    def sobre_abajo(y, Q, sentido):    # en el corte del palo de abajo, en y
        t.rodear(centro_ab, Plano(1, y), Q, sentido, ABAJO, ABAJO, rb)

    # --- Ballestrinque de inicio, desde el chicote: el orden de atado, al revés ---
    # Va de modo que el firme sale por el costado derecho del palo de abajo y sube recto a la
    # primera vuelta; su cruz queda abajo a la derecha. En el orden de atado el ángulo crece;
    # al recorrerlo al revés, alfa = -40 - psi (alfa en el corte del palo, desde +x hacia arriba).
    psi0 = 0
    ent = np.array([A[1], carriles[1], z_baja])     # de aquí el firme sube a la primera vuelta
    pts, hito1 = [], None
    for v, psi, alto, nombre in reversed(_ballestrinque(*carriles, psi0=psi0)):
        a, r = math.radians(-40 - psi), rb + alto
        pts.append([r * math.cos(a), v, zb + r * math.sin(a)])
        if nombre == "diagonal" and hito1 is None:
            hito1 = len(pts)   # inicio-1: hasta antes de la diagonal
    # El chicote corto asoma un poco del palo, tangente: así la cuerda tiene de dónde correr.
    pts = np.array(pts)
    atras = pts[0] - pts[1]
    atras[2] = max(atras[2], 0.0)                    # sin bajar de la mesa
    t.puntos(pts[0] + 1.2 * _unit(atras), ABAJO)
    t.ir(pts[0], ABAJO)
    t.puntos(pts[:hito1], ABAJO)
    t.marcar("inicio-1")
    t.puntos(pts[hito1 - 1:], ABAJO)
    t.ir(ent, ABAJO)
    t.marcar("inicio")

    # --- Vueltas ---
    t.ir([A[1], carriles[1], zt - 0.5], CINTURA)       # la primera esquina sube recta
    esquinas = [((A[1], carriles[1]), +1)]   # en orden de la cuerda: dónde baja y si sube (+1) o baja
    for k in range(1, n + 1):
        a, bt, bd = A[k], Bt[k], Bd[k]
        sobre_arriba(a, [a, bt, z_alta], -1)                 # por encima, de delante a atrás
        t.ir([a, bt, z_baja], CINTURA)
        esquinas.append(((a, bt), -1))
        sobre_abajo(bt, [-a, bt, z_baja], -1)                # por debajo, de derecha a izquierda
        t.ir([-a, bt, z_alta], CINTURA)
        esquinas.append(((-a, bt), +1))
        sobre_arriba(-a, [-a, -bd, z_alta], +1)              # por encima, de atrás a delante
        t.ir([-a, -bd, z_baja], CINTURA)
        esquinas.append(((-a, -bd), -1))
        sobre_abajo(-bd, [A[k + 1], -bd, z_baja], +1)        # por debajo, de izquierda a derecha
        t.marcar(f"vuelta-{k}")
        if k < n:
            t.ir([A[k + 1], -bd, z_alta], CINTURA)
            esquinas.append(((A[k + 1], -bd), +1))

    # --- Ahorcados: una espiral hacia fuera entre los palos, alrededor de las esquinas ---
    raiz2 = math.sqrt(2)
    s_atras, s_q3, s_q4 = A[1] + Bt[1], A[1] + Bd[1], A[2] + Bd[1]   # x + y de cada grupo de esquinas

    def alto(q, j):
        """Altura de cada ahorcado en cada cuadrante: van uno sobre otro, así que en el mapa de
        la cintura no se cruzan. Delante a la derecha van en la mitad alta de las esquinas."""
        u = (j - 1) / (m - 1)
        return medio + 1.15 + 0.35 * u if q == 4 else medio - 0.4 + 0.8 * u

    # Cada ahorcado va recto por la cintura antes y después de pasar por cada palo, hasta más
    # allá (MARGEN) de la esquina de ese cuadrante más cercana al palo, para cruzar todas las
    # esquinas dentro de la cintura. Lejos (si = 1, con los ahorcados de fuera) eso es más largo.
    def junto(qx, qy, al_de_arriba):
        cs = [c for c, _ in esquinas if np.sign(c[0]) == qx and np.sign(c[1]) == qy]
        return min(cs, key=lambda c: abs(c[1] / c[0]) if al_de_arriba else abs(c[0] / c[1]))

    def recto_arriba(X, qx, qy, d, z):   # |y| donde empieza o termina, en el plano x = X
        cx, cy = junto(qx, qy, True)
        libre = math.sqrt(max(0.0, rb ** 2 - (zt - z) ** 2)) + 0.2   # lo que ocupa el palo
        return max(libre, min(d - abs(X), abs(X * cy / cx)) - MARGEN)

    def recto_abajo(Y, qx, qy, d, z):    # |x| donde empieza o termina, en el plano y = Y
        cx, cy = junto(qx, qy, False)
        libre = math.sqrt(max(0.0, rb ** 2 - (z - zb) ** 2)) + 0.2
        return max(libre, min(d - abs(Y), abs(Y * cx / cy)) - MARGEN)

    # El primer ahorcado sale de la última vuelta derecho hacia abajo del palo de arriba.
    x_cierre = None
    for j in range(1, m + 1):
        o = (j - 1) * PASO_VUELTAS
        x0 = A[n + 1] + o
        d1, d3, d4 = (s + raiz2 * (HOLGURA + o) for s in (s_atras, s_q3, s_q4))
        yt, xi, yd = Bt[1] + HOLGURA + o, A[n] + HOLGURA + o, Bd[1] + HOLGURA + o
        z1, z2, z3, z4 = (alto(q, j) for q in (1, 2, 3, 4))
        sobre_arriba(x0, [x0, recto_arriba(x0, 1, 1, d1, z1), z1], +1)      # por debajo, de delante a atrás
        t.ir([x0, d1 - x0, z1], CINTURA)
        t.ir([d1 - yt, yt, z1], CINTURA)
        t.ir([recto_abajo(yt, 1, 1, d1, z1), yt, z1], CINTURA)
        sobre_abajo(yt, [-recto_abajo(yt, -1, 1, d1, z2), yt, z2], +1)     # por encima, de derecha a izquierda
        t.ir([-(d1 - yt), yt, z2], CINTURA)
        t.ir([-xi, d1 - xi, z2], CINTURA)
        t.ir([-xi, recto_arriba(xi, -1, 1, d1, z2), z2], CINTURA)
        sobre_arriba(-xi, [-xi, -recto_arriba(xi, -1, -1, d3, z3), z3], -1)  # por debajo, de atrás a delante
        t.ir([-xi, -(d3 - xi), z3], CINTURA)
        t.ir([-(d3 - yd), -yd, z3], CINTURA)
        t.ir([-recto_abajo(yd, -1, -1, d3, z3), -yd, z3], CINTURA)
        sobre_abajo(-yd, [recto_abajo(yd, 1, -1, d4, z4), -yd, z4], -1)    # por encima, de izquierda a derecha
        t.ir([d4 - yd, -yd, z4], CINTURA)
        # El último ahorcado lleva al firme del ballestrinque de cierre.
        x_sig = A[n + 1] + j * PASO_VUELTAS if j < m else x0 + PASO_VUELTAS + CARRIL
        t.ir([x_sig, -(d4 - x_sig), z4], CINTURA)
        t.ir([x_sig, -recto_arriba(x_sig, 1, -1, d4, z4), z4], CINTURA)
        t.marcar(f"ahorcado-{j}")
        x_cierre = x_sig

    # --- Ballestrinque de cierre, en el palo de arriba, en orden de atado ---
    bal = _ballestrinque(x_cierre - CARRIL, x_cierre, x_cierre + CARRIL, x_cierre + 2 * CARRIL,
                         psi0=450)
    P = t.fin
    a_ent = math.degrees(_tangente(centro_ar, rb, np.array([P[1], P[2]]), +1)) % 360
    pts = [[x_cierre, rb * math.cos(math.radians(s)), zt + rb * math.sin(math.radians(s))]
           for s in np.arange(a_ent, bal[0][1], 6.0)]
    hito1 = None
    for v, psi, alto, nombre in bal:
        a, r = math.radians(psi), rb + alto
        pts.append([v, r * math.cos(a), zt + r * math.sin(a)])
        if nombre == "vuelta2" and hito1 is None:
            hito1 = len(pts)
    t.puntos(np.array(pts[:hito1]), ARRIBA)
    t.marcar("cierre-1")
    t.puntos(np.array(pts[hito1 - 1:]), ARRIBA)
    a = math.radians(bal[-1][1])     # el chicote sale un poco del palo, tangente
    t.ir(t.fin + 1.5 * np.array([0.0, -math.sin(a), math.cos(a)]), MESA)
    t.marcar("cierre")

    X, Z, hitos = t.muestrear(RADIO_ESQUINA)
    # El trazo lleva el inicio delante y el cierre a la derecha; los otros lados son su reflejo.
    espejo = np.array([-1.0 if p.cierre.lado == "izquierda" else 1.0,
                       -1.0 if p.inicio.lado == "detras" else 1.0, 1.0])
    X = X * espejo
    restos = {}
    for nombre, i in hitos.items():
        if nombre != "cierre":
            sale = SALIDAS[nombre] if nombre in SALIDAS else SALIDAS[nombre.split("-")[0]]
            restos[nombre] = _resto(X[i], _unit(X[i] - X[max(i - 3, 0)]),
                                    _unit(np.array([*sale, 0.0]) * espejo))
    alias = {"vueltas": f"vuelta-{n}", "ahorcados": f"ahorcado-{m}"}
    return Cuerda(X, Z, hitos, restos, _secuencias(p, esquinas), alias)


def _ballestrinque(c_v1, c_firme, c_chicote, c_v2, psi0, paso=6.0):
    """Un ballestrinque sobre un palo, en orden de atado (desde el firme): una lista de
    (posición a lo largo del palo, ángulo en grados, cuánto se aleja del palo, tramo), con el
    ángulo creciente.

    Va en cuatro carriles a lo largo del palo: la primera vuelta, el firme, el chicote y la
    segunda vuelta. El firme llega por su carril y se va a la primera vuelta; la diagonal
    cruza por encima del firme (en psi0 - 10) y del chicote (en psi0 + 20) hasta la segunda
    vuelta, y el chicote vuelve a su carril por debajo de la diagonal. Donde cruza, la
    diagonal va un diámetro más lejos del palo; sube y baja despacio, para no doblarse."""
    out = []

    def tramo(p0, p1, v0, v1, nombre, lineal=False):
        for t in np.linspace(0, 1, max(2, int(abs(p1 - p0) / paso) + 1)):
            psi = p0 + (p1 - p0) * t
            if out and abs(out[-1][1] - psi) < 1e-9:
                continue
            s = t if lineal else t * t * (3 - 2 * t)
            out.append((v0 + (v1 - v0) * s, psi, _levantar(psi - psi0), nombre))

    tramo(psi0 - 40, psi0, c_firme, c_firme, "firme")
    tramo(psi0, psi0 + 90, c_firme, c_v1, "deriva1")
    tramo(psi0 + 90, psi0 + 320, c_v1, c_v1, "vuelta1")
    tramo(psi0 + 320, psi0 + 410, c_v1, c_v2, "diagonal", lineal=True)
    tramo(psi0 + 410, psi0 + 680, c_v2, c_v2, "vuelta2")
    tramo(psi0 + 680, psi0 + 710, c_v2, c_chicote, "deriva2")
    tramo(psi0 + 710, psi0 + 760, c_chicote, c_chicote, "chicote")
    return out


def _levantar(d) -> float:
    """Cuánto se aleja del palo la diagonal de un ballestrinque, d grados después de psi0:
    un diámetro entre sus dos cruces (de 335 a 395), con rampas suaves de 55 grados."""
    sube = np.clip((d - 280) / 55, 0, 1)
    baja = np.clip((450 - d) / 55, 0, 1)
    x = min(sube, baja)
    return float(2 * R_CUERDA * x * x * (3 - 2 * x))


def _tangente(c, r, P, sentido, saliendo=False) -> float:
    """El ángulo del punto del círculo (c, r) donde una recta desde P llega tangente
    (o, con `saliendo`, donde la cuerda lo deja para ir recta a P), girando en `sentido`."""
    d = P - c
    a = math.atan2(d[1], d[0])
    b = math.acos(min(1.0, r / float(np.linalg.norm(d))))
    for ang in (a + b, a - b):
        T = c + r * np.array([math.cos(ang), math.sin(ang)])
        t = sentido * np.array([-math.sin(ang), math.cos(ang)])
        if np.dot((P - T) if saliendo else (T - P), t) > 0:
            return ang
    raise ValueError("no hay tangente")


def _unit(v) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _resto(P, llega, afuera) -> np.ndarray:
    """Puntos de control de lo que sigue de la cuerda después de un hito: sigue un poco como
    venía, gira hacia fuera del amarre y baja en curva hasta la mesa."""
    q1 = P + 1.0 * llega
    q2 = q1 + 1.0 * _unit(llega + afuera)
    q3 = q2 + 1.5 * afuera
    out = [q1, q2, q3]
    for u in (0.2, 0.4, 0.6, 0.8, 1.0):
        q = q3 + 9.0 * u * afuera
        q[2] = 0.5 + (q3[2] - 0.5) * (1 - u * u * (3 - 2 * u))   # baja sin quiebres
        out.append(q)
    out.append(out[-1] + 6.0 * afuera)
    return np.array(out)


def _secuencias(p: AmarreCuadrado, esquinas) -> dict[str, tuple[str, ...]]:
    """La secuencia de cruces del método hasta cada hito.

    El ballestrinque de inicio da los cruces 1 y 2; cada ahorcado pasa por encima de cada
    esquina de las vueltas; el ballestrinque de cierre da los dos últimos. Las vueltas no se
    cruzan entre sí, porque van una junto a otra. Sobre cada esquina, los ahorcados pasan de
    abajo arriba (el primero es el más bajo); cada ahorcado recorre las esquinas en el
    sentido en que gira, desde que pasa bajo el palo de arriba."""
    m = p.ahorcados
    etiqueta = lambda c, j: str(3 + c * m + (j - 1))
    ultimo = 3 + len(esquinas) * m
    # Cada ahorcado entra a la cintura después de pasar bajo el palo de arriba, a la derecha
    # (giro 0), y recorre las esquinas en el sentido en que gira.
    giro0 = 0.0
    por_giro = sorted(range(len(esquinas)),
                      key=lambda c: (math.atan2(esquinas[c][0][1], esquinas[c][0][0]) - giro0) % (2 * math.pi))
    orden = list(p.hitos())
    out = {}
    for hito in orden:
        r = orden.index(hito)
        sec = []
        if r >= orden.index("inicio"):
            sec += ["1U", "1O", "2O", "2U"]
        hechos = [j for j in range(1, m + 1) if r >= orden.index(f"ahorcado-{j}")]
        for c, (_, sube) in enumerate(esquinas):
            for j in (hechos if sube > 0 else hechos[::-1]):
                sec.append(etiqueta(c, j) + "U")
        for j in hechos:
            sec += [etiqueta(c, j) + "O" for c in por_giro]
        if r >= orden.index("cierre-1"):
            sec += [f"{ultimo}U", f"{ultimo}O"]
        if r >= orden.index("cierre"):
            sec += [f"{ultimo + 1}O", f"{ultimo + 1}U"]
        out[hito] = tuple(sec)
    for alias, k in (("vueltas", p.vueltas), ("ahorcados", m)):
        nombre = "vuelta" if alias == "vueltas" else "ahorcado"
        out[alias] = out[f"{nombre}-{k}"]
    return out
