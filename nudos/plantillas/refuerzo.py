"""Plantilla del refuerzo de cabo, sobre la punta de un cabo (anfitrión «cabo»).

El método es el del diseño de la tanda 4 en tasks/plan.md («El cabo y el refuerzo de cabo»):
el cordel se pone a lo largo del cabo, con el extremo corto hacia la punta; con el largo se
dan unas vueltas hacia la punta, sobre el extremo corto; ese extremo se dobla en un seno que
queda sobre las vueltas, con la curva hacia la punta; se dan otras tantas vueltas sobre las
dos ramas del seno; el largo (el chicote) pasa por el seno, y al tirar del extremo corto el
seno se mete bajo las vueltas de encima y arrastra al chicote. Al final se cortan las puntas.

La cuerda se traza en el mapa del cabo: x a lo largo del eje (la punta está en x = 0 y el cabo
sigue hacia x negativo) y u, el arco alrededor del eje a la distancia de una cuerda que lo toca,
creciendo con el ángulo (0 arriba, 90° hacia quien ata). Cada tramo del mapa es una pieza con su
nivel: en un cruce, va encima la de nivel más alto. La altura de cada punto sobre el cabo sale
de sus cruces: donde pasa por encima de otro tramo sube un diámetro sobre él.

A diferencia del amarre, cada paso no es el comienzo de una sola cuerda: el seno, el tirar y el
corte cambian el principio de la cuerda, que es el extremo corto. Por eso la plantilla traza la
cuerda de cada hito entera y dice qué tramo se resalta.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .trazo import MESA, TrazoDePaso

# Cuántas vueltas acepta la plantilla por mitad, en letras.
NUMEROS = {3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho"}
_CAMPOS = {"tipo", "vueltas"}

CABO = 1   # zona: sobre el cabo. Lo que cuelga hasta la mesa va en MESA.

# Medidas en diámetros de cordel; ver el diseño en tasks/plan.md.
PASO_VUELTA = 1.1     # entre dos vueltas vecinas, a lo largo del cabo
CENTRO = 45.0         # el ángulo del medio del seno, de frente a la cámara de los pasos
ANCHO = 7.0           # el arco entre las dos ramas del seno
ESQUINA = 1.2         # radio de las dos esquinas de la curva del seno
FIN_VUELTA = 1.2      # cuánto sigue cada vuelta, en arco, después de pasar sobre el extremo corto
GIRO = 1.0            # radio de las esquinas en el mapa
PUNTA = 4.6           # dónde termina la última vuelta: x = -PUNTA
CURVA_TRAS = 1.0      # cuánto más allá de la última vuelta empieza la curva del seno
COLA = 3.0            # cuánto sigue la rama que vuelve más allá de las primeras vueltas
COLA_TIRADA = 4.0     # y cuánto más, al tirar del extremo corto
PASA = 1.0            # cuánto sigue el chicote sobre el cabo después de pasar bajo la curva
CORTE = 1.0           # cuánto sale cada punta cortada de las vueltas
U_CHICOTE = 1.15      # al tirar, a cuánto del medio del seno van las dos pasadas del chicote
MESETA = 0.6          # cuánto más allá del eje de la otra cuerda sigue arriba la de encima
RAMPA = 2.4           # largo de la subida o bajada de una pasada por encima
APILA = 0.95          # en el mapa, a menos de esto de un tramo más bajo, se va encima de él
VECINO = 3.0          # a lo largo de la cuerda, lo que está más cerca no se apila
PUENTE = 4.5          # entre dos pasadas por encima más cercanas que esto, la cuerda no baja
PASO_MAPA = 0.05      # cada cuánto se traza la cuerda en el mapa
PASO_CONTROL = 0.3    # cada cuánto se toma un punto de control
SOBRE_LA_MESA = 6     # puntos (cada 0,5) de lo que sigue por la mesa después de caer

# Los niveles de cada pieza: en un cruce va encima la de nivel más alto.
NIVEL = {"corto": 0.0, "primeras": 1.0, "rama": 2.0, "curva": 2.0, "chicote": 1.5,
         "entra": 1.5, "sale": 2.5, "encima": 3.0}


@dataclass(frozen=True)
class RefuerzoDeCabo:
    vueltas: int    # las de cada mitad: antes del seno, y otras tantas encima de él

    tipo = "refuerzo-de-cabo"
    ANFITRION = "cabo"
    # El error común que sabe construir, con el primer hito desde el que se ve: el chicote
    # pasa por encima de la curva del seno, en vez de por dentro.
    VARIANTES = {"por-fuera-del-seno": "por-el-seno"}
    # Ningún paso tiene firme: el extremo corto queda bajo las vueltas y se trabaja con el
    # largo, que lleva «Chicote» en su punta.
    CON_FIRME: tuple[str, ...] = ()
    # Los hitos que no llevan «Chicote»: con las puntas cortadas, el chicote ya no está.
    SIN_NOMBRES = ("cortar",)

    @classmethod
    def leer(cls, datos: dict, falla) -> RefuerzoDeCabo:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        v = datos.get("vueltas")
        if not isinstance(v, int) or isinstance(v, bool) or v not in NUMEROS:
            raise falla(f"«vueltas» es un número entero de {min(NUMEROS)} a {max(NUMEROS)}")
        return cls(vueltas=v)

    def comprobar(self, anfitrion, falla) -> None:
        """El refuerzo tiene que caber en el cabo: el cabo sigue al menos 3 diámetros más allá
        de lo que llega más lejos de la punta, la cola de la rama que vuelve al tirar."""
        minimo = largo_minimo(self.vueltas)
        if anfitrion.largo < minimo:
            raise falla(f"con {self.vueltas} vueltas, el refuerzo no cabe en el cabo: «largo» "
                        f"tiene que ser de al menos {minimo:g}")

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, en orden. `vueltas` es lo mismo que la última vuelta antes
        del seno y `seno-vueltas` que la última encima de él."""
        out = {"colocar": 0}
        k = 0
        for i in range(1, self.vueltas + 1):
            k += 1
            out[f"vuelta-{i}"] = k
        out["vueltas"] = k
        k += 1
        out["seno"] = k
        for i in range(1, self.vueltas + 1):
            k += 1
            out[f"seno-vuelta-{i}"] = k
        out["seno-vueltas"] = k
        for nombre in ("por-el-seno", "tirar", "cortar"):
            k += 1
            out[nombre] = k
        return out

    def medidas(self) -> dict[str, str]:
        return {"vueltas": NUMEROS[self.vueltas]}


def inicio_vueltas(n: int) -> float:
    """Dónde empieza la primera vuelta, a lo largo del cabo."""
    return -PUNTA - PASO_VUELTA * (2 * n + 1)


def largo_minimo(n: int) -> float:
    return round(-inicio_vueltas(n) + COLA + COLA_TIRADA + 3.0, 1)


# --------------------------------------------------------------------------
# Piezas de la cuerda en el mapa
# --------------------------------------------------------------------------
@dataclass
class _Pieza:
    nombre: str          # «corto», «vuelta-3», «curva»…: identifica los cruces entre pasos
    tipo: str            # la clave de NIVEL
    M: np.ndarray | None = None   # en el mapa: (x, u)
    P: np.ndarray | None = None   # en la mesa, en 3D (lo que cuelga)


def _recta(a, b, paso: float = PASO_MAPA) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(2, int(math.ceil(np.linalg.norm(b - a) / paso)) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)


def _arco(centro, radio, a0, a1, paso: float = PASO_MAPA) -> np.ndarray:
    """Arco en el mapa de (x, u), con el ángulo medido desde +x hacia +u."""
    n = max(2, int(math.ceil(abs(a1 - a0) * radio / paso)) + 1)
    a = np.linspace(a0, a1, n)
    return np.column_stack([centro[0] + radio * np.cos(a), centro[1] + radio * np.sin(a)])


def _unir(*tramos) -> np.ndarray:
    out = [tramos[0]]
    for t in tramos[1:]:
        if np.linalg.norm(t[0] - out[-1][-1]) < 1e-9:
            t = t[1:]
        out.append(t)
    return np.vstack(out)


def _largo(M) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(M, axis=0), axis=1))])


def _remuestrear(M, paso: float) -> np.ndarray:
    s = _largo(M)
    n = max(1, int(math.ceil(s[-1] / paso)))
    g = np.linspace(0.0, s[-1], n + 1)
    return np.column_stack([np.interp(g, s, M[:, k]) for k in range(M.shape[1])])


def _hermite(P0, T0, P1, T1, n: int) -> np.ndarray:
    d = float(np.linalg.norm(P1 - P0))
    t = np.linspace(0.0, 1.0, n)[:, None]
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * P0 + (t ** 3 - 2 * t ** 2 + t) * d * T0
            + (-2 * t ** 3 + 3 * t ** 2) * P1 + (t ** 3 - t ** 2) * d * T1)


def _puentes(crudo, pieza, paso: float) -> np.ndarray:
    """Entre dos pasadas por encima de una misma pieza que están a menos de PUENTE, la cuerda
    no baja: sigue a la altura de la más baja de las dos."""
    from scipy.ndimage import maximum_filter1d
    out = crudo.copy()
    w = int(round(PUENTE / paso))
    for k in np.unique(pieza):
        en = np.nonzero(pieza == k)[0]
        c = crudo[en]
        if not (c > 0).any():
            continue
        # El máximo a cada lado, hasta w puntos.
        izq = maximum_filter1d(c, size=w + 1, origin=w // 2, mode="constant", cval=0.0)
        der = maximum_filter1d(c, size=w + 1, origin=-(w // 2), mode="constant", cval=0.0)
        out[en] = np.maximum(c, np.minimum(izq, der))
    return out


def _rampas(crudo, paso: float, niveles=None) -> np.ndarray:
    """La altura de cada punto con rampas suaves: el máximo, sobre los demás puntos, de su
    altura cruda por una rampa coseno que va de 1 en el punto a 0 a RAMPA·√altura de él. Lo
    que sube dos capas sube en una rampa más larga, para doblarse lo mismo. Con `niveles`, una
    rampa solo sube a tramos de su nivel o más altos."""
    h = crudo.copy()
    w = RAMPA * np.sqrt(np.maximum(crudo, 1.0)) / paso
    for d in range(1, int(math.ceil(w.max())) + 1):
        f = np.where(d < w, 0.5 + 0.5 * np.cos(np.pi * d / w), 0.0) * crudo
        if niveles is None:
            h[d:] = np.maximum(h[d:], f[:-d])
            h[:-d] = np.maximum(h[:-d], f[d:])
        else:
            h[d:] = np.maximum(h[d:], np.where(niveles[d:] >= niveles[:-d], f[:-d], 0.0))
            h[:-d] = np.maximum(h[:-d], np.where(niveles[:-d] >= niveles[d:], f[d:], 0.0))
    return h


def _unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / max(float(np.linalg.norm(v)), 1e-12)


class Cuerda:
    """Las cuerdas de un refuerzo de cabo, una por hito, con su secuencia de cruces.

    `secuencias` da la secuencia del método en cada hito y `alias` los hitos que equivalen a
    otro (`vueltas` y `seno-vueltas`). `trazo(hito, previo)` da los puntos de control del paso."""

    def __init__(self, p: RefuerzoDeCabo, cabo, variante: str | None = None):
        if variante is not None and variante not in p.VARIANTES:
            raise ValueError(f"el refuerzo de cabo no tiene la variante {variante}")
        self.p, self.cabo, self.variante = p, cabo, variante
        self.rb = cabo.rb
        self.C = 2 * math.pi * cabo.rb
        n = p.vueltas
        self.uc = math.radians(CENTRO) * self.rb   # el medio del seno
        self.u1 = self.uc + ANCHO / 2              # la rama que sale de las vueltas (el corto)
        self.u2 = self.uc - ANCHO / 2              # la rama que vuelve
        self.x0 = inicio_vueltas(n)
        hitos = p.hitos()
        self.alias = {"vueltas": f"vuelta-{n}", "seno-vueltas": f"seno-vuelta-{n}"}
        self.orden = [h for h in sorted(hitos, key=hitos.get) if h not in self.alias]
        self._etiquetas: dict[tuple, str] = {}
        # Un hito que no se puede trazar con estas medidas queda como su error: la falla es
        # del paso que llega a él, no de todo el nudo.
        from ..libre import TrazadoError
        self._pasos, self._errores = {}, {}
        for h in self.orden:
            try:
                self._pasos[h] = self._paso(h)
            except TrazadoError as e:
                self._errores[h] = e
        self.secuencias = {h: self._pasos[h]["secuencia"] if h in self._pasos else ()
                           for h in self.orden}
        for a, h in self.alias.items():
            self.secuencias[a] = self.secuencias[h]

    # --- Las vueltas ----------------------------------------------------------------
    def _x_vuelta(self, u) -> np.ndarray:
        """x de la hélice de las vueltas en el arco desenrollado u (desde donde empieza)."""
        return self.x0 + PASO_VUELTA * (np.asarray(u, float) - (self.u1 + GIRO)) / self.C

    def _vueltas(self, u_fin: float) -> list[_Pieza]:
        """La hélice desde que sale de la esquina del corto hasta u_fin, partida en una pieza
        por vuelta: la vuelta k termina FIN_VUELTA después de pasar sobre el corto por k-ésima
        vez. Las primeras `vueltas` son de las primeras; las demás, de encima."""
        n = self.p.vueltas
        u0 = self.u1 + GIRO
        cortes = [self.u1 + k * self.C + FIN_VUELTA for k in range(1, 2 * n + 2)]
        piezas, a = [], u0
        for k, b in enumerate(cortes, 1):
            b = min(b, u_fin)
            if b <= a:
                break
            u = np.linspace(a, b, max(2, int(math.ceil((b - a) / PASO_MAPA)) + 1))
            tipo = "primeras" if k <= n else "encima"
            piezas.append(_Pieza(f"vuelta-{k}", tipo, M=np.column_stack([self._x_vuelta(u), u])))
            a = b
        return piezas

    def _u_vuelta(self, k: int) -> float:
        """Dónde termina la vuelta k (en el arco desenrollado)."""
        return self.u1 + k * self.C + FIN_VUELTA

    # --- El extremo corto ---------------------------------------------------------
    def _esquina(self) -> np.ndarray:
        """La esquina del corto a la primera vuelta: viene a lo largo del cabo hacia la izquierda
        (x negativo) en u1 y gira hacia u creciente, donde empieza la hélice."""
        c = (self.x0 + GIRO, self.u1 + GIRO)
        return _arco(c, GIRO, -math.pi / 2, -math.pi, PASO_MAPA)

    def _corto_recto(self, hasta_x: float) -> np.ndarray:
        """El corto desde hasta_x (hacia la punta), a lo largo del cabo en u1, hasta la esquina."""
        return _unir(_recta((hasta_x, self.u1), (self.x0 + GIRO, self.u1)), self._esquina())

    def _fin_primeras(self) -> float:
        """Dónde sale el corto de las primeras vueltas: medio paso después de la última."""
        return float(self._x_vuelta(self.u1 + self.p.vueltas * self.C)) + PASO_VUELTA / 2

    def _libre(self) -> float:
        """Desde dónde nada más se apila sobre la última de las primeras vueltas: a más de
        APILA de donde pasa sobre el corto."""
        return self._fin_primeras() - PASO_VUELTA / 2 + APILA + 0.1

    def _x_curva(self) -> float:
        """Dónde está la curva del seno (su tramo recto), en los pasos antes de tirar: un poco
        más allá de la última vuelta."""
        return -PUNTA + CURVA_TRAS + ESQUINA

    def _curva(self, x_ap: float) -> np.ndarray:
        """La curva del seno, de la rama que vuelve (u2) a la del corto (u1): una esquina de
        radio ESQUINA, un tramo recto alrededor del cabo en x_ap y otra esquina. El chicote la
        cruza de frente, en el tramo recto."""
        r = ESQUINA
        x0 = x_ap - r
        a = _arco((x0, self.u2 + r), r, -math.pi / 2, 0.0)
        recto = _recta((x_ap, self.u2 + r), (x_ap, self.u1 - r))
        b = _arco((x0, self.u1 - r), r, 0.0, math.pi / 2)
        return _unir(a, recto, b)

    def _seno(self, x_ap: float, x_cola: float, redonda: bool = False) -> list[_Pieza]:
        """El seno, desde la punta de la rama que vuelve (en x_cola) hasta la esquina del corto:
        la rama que vuelve en u2, la curva y el corto en u1. La curva llega hasta x_ap: plana,
        con su tramo recto ahí, o, al tirar, `redonda`, una media circunferencia de radio
        ANCHO/2."""
        if redonda:
            x_curva = x_ap - ANCHO / 2
            curva = _arco((x_curva, self.uc), ANCHO / 2, -math.pi / 2, math.pi / 2)
        else:
            x_curva = x_ap - ESQUINA
            curva = self._curva(x_ap)
        rama = _recta((x_cola, self.u2), (x_curva, self.u2))
        # El corto, desde que sale de las primeras vueltas, va al nivel del seno: solo pasa bajo
        # las vueltas de encima, y así la curva baja a él sin doblarse.
        x_sale = self._libre()
        sale = _recta((x_curva, self.u1), (x_sale, self.u1))
        corto = self._corto_recto(x_sale)
        return [_Pieza("rama", "rama", M=rama), _Pieza("curva", "curva", M=curva),
                _Pieza("rama-corto", "rama", M=sale), _Pieza("corto", "corto", M=corto)]

    # --- El chicote -----------------------------------------------------------------
    def _por_el_seno(self) -> list[_Pieza]:
        """La última vuelta, que pasa sobre la rama que vuelve, y el chicote, que gira hacia la
        punta en el medio del seno, pasa bajo la curva y sigue hasta pasar la punta del cabo."""
        n = self.p.vueltas
        u_giro = self.uc + (2 * n + 1) * self.C - GIRO   # donde empieza a girar
        piezas = self._vueltas(u_giro)
        x_g = float(self._x_vuelta(u_giro))
        # Gira de ir alrededor (u creciente) a ir hacia la punta (+x), con radio GIRO.
        giro = _arco((x_g + GIRO, u_giro), GIRO, math.pi, math.pi / 2)
        recto = _recta(giro[-1], (0.0, giro[-1][1]))
        piezas.append(_Pieza("chicote", "chicote", M=_unir(giro, recto)))
        return piezas

    def _tirado(self) -> tuple[list[_Pieza], float, float]:
        """Al tirar: la curva del seno entra bajo las vueltas de encima y arrastra al chicote. La
        última vuelta pasa sobre la rama que vuelve y el chicote entra bajo las vueltas del lado
        de esa rama (en uc - U_CHICOTE), pasa bajo la curva, da media vuelta dentro del seno,
        vuelve por encima de la curva del otro lado (en uc + U_CHICOTE) y sale por el borde. La
        última vuelta no pasa por encima de lo que sale.

        La curva es una media circunferencia de radio ANCHO/2 y la media vuelta del chicote
        tiene el mismo centro. Las puntas de las dos, donde van de costado, paralelas a las
        vueltas, quedan entre dos vueltas: si una vuelta pasara justo por ahí, el cruce se
        formaría y se desharía al relajar. Devuelve las piezas desde la última vuelta, hasta
        dónde llega la curva y la x del borde por donde sale el chicote."""
        n = self.p.vueltas
        uc = self.uc + (2 * n + 1) * self.C
        W, U = ANCHO / 2, U_CHICOTE
        u_giro = uc - U - GIRO
        piezas = self._vueltas(u_giro)
        x_g = float(self._x_vuelta(u_giro))
        x_c = self._centro_tirado()
        giro = _arco((x_g - GIRO, u_giro), GIRO, 0.0, math.pi / 2)          # hacia -x
        entra = _unir(giro, _recta(giro[-1], (x_c, uc - U)))
        media = _arco((x_c, uc), U, -math.pi / 2, -3 * math.pi / 2)
        x_sale = -PUNTA + PASO_VUELTA / 2
        sale = _recta(media[-1], (0.0, uc + U))
        piezas.append(_Pieza("entra", "entra", M=_unir(entra, media)))
        piezas.append(_Pieza("sale", "sale", M=sale))
        return piezas, x_c + W, x_sale

    def _centro_tirado(self) -> float:
        """El centro de la curva al tirar (y de la media vuelta del chicote). La punta de la
        media vuelta queda entre dos vueltas, sin pasar bajo las primeras; el chicote pasa
        bajo la curva a más de APILA de donde sale de la última vuelta, y la punta de la curva
        queda bajo las vueltas. Si no cabe, es que las vueltas de encima son pocas."""
        n = self.p.vueltas
        W, U = ANCHO / 2, U_CHICOTE
        u_giro = self.uc + (2 * n + 1) * self.C - U - GIRO
        x_entra = float(self._x_vuelta(u_giro)) - GIRO
        cruce = math.sqrt(W * W - U * U)
        x_ultima = float(self._x_vuelta(self.uc + 2 * n * self.C))   # la última vuelta entera, en uc
        lo = self._libre() + U
        hi = min(x_entra - APILA - 0.3 - cruce, x_ultima - 0.3 - W)
        mejores = [float(self._x_vuelta(self.uc + k * self.C)) + PASO_VUELTA / 2 + U
                   for k in range(1, 2 * n + 1)]
        mejores = [x for x in mejores if lo <= x <= hi]
        if not mejores:
            from ..libre import TrazadoError
            raise TrazadoError(
                f"con {n} vueltas encima del seno no cabe el seno al tirar: hacen falta más "
                "vueltas")
        return max(mejores)

    # --- Lo que cuelga --------------------------------------------------------------
    def _en(self, x, u, h=0.0) -> np.ndarray:
        return self.cabo.punto(x, np.degrees(np.asarray(u) / self.rb), self.rb + np.asarray(h))

    def _caer(self, P0, T0, hacia, largo: float = 4.0) -> np.ndarray:
        """Desde P0 (sobre el cabo, yendo en T0) cae a la mesa en una curva suave, hacia `hacia`
        (en el plano de la mesa), y sigue por la mesa."""
        hacia = _unit(np.array([hacia[0], hacia[1], 0.0]))
        P1 = np.array([P0[0], P0[1], 0.5]) + largo * hacia
        T0 = _unit(T0)
        n = max(6, int(np.linalg.norm(P1 - P0) / PASO_CONTROL) + 1)
        curva = _hermite(np.asarray(P0, float), T0, P1, hacia, n)[1:]
        mesa = [P1 + 0.5 * k * hacia for k in range(1, SOBRE_LA_MESA + 1)]
        return np.vstack([curva, mesa])

    # --- Un hito ----------------------------------------------------------------------
    def _piezas(self, hito: str) -> tuple[list[_Pieza], dict]:
        """Las piezas del mapa de la cuerda del hito, en orden desde el extremo corto, y qué
        cuelga: «antes», el extremo corto (o la cola) que cae a la mesa antes del mapa, y
        «despues», hacia dónde cae lo que sigue."""
        n = self.p.vueltas
        x_cola = self.x0 - COLA
        cuelga = {"antes": None, "despues": None}
        if hito == "colocar":
            M = _recta((0.0, self.u1), (self.x0 - 3.0, self.u1))
            cuelga.update(antes="punta", despues=(-0.6, -0.8))
            return [_Pieza("corto", "corto", M=M)], cuelga
        if hito.startswith("vuelta-"):
            k = int(hito.split("-")[1])
            piezas = [_Pieza("corto", "corto", M=self._corto_recto(0.0))] + self._vueltas(self._u_vuelta(k))
            cuelga.update(antes="punta", despues=(-0.6, -0.8))
            return piezas, cuelga
        if hito == "seno" or hito.startswith("seno-vuelta-"):
            k = n if hito == "seno" else n + int(hito.split("-")[2])
            piezas = self._seno(self._x_curva(), x_cola) + self._vueltas(self._u_vuelta(k))
            cuelga.update(despues=(-0.6, -0.8))
            return piezas, cuelga
        if hito == "por-el-seno":
            piezas = self._seno(self._x_curva(), x_cola) + self._por_el_seno()
            cuelga.update(despues="punta")
            return piezas, cuelga
        tirado, x_curva, x_sale = self._tirado()
        if hito == "tirar":
            # La rama que vuelve salió de debajo de las vueltas lo que entró la curva: su cola
            # sigue por el cabo y cae a la mesa.
            piezas = self._seno(x_curva, self.x0 - COLA - COLA_TIRADA, redonda=True) + tirado
            cuelga.update(despues="punta")
            return piezas, cuelga
        # Cortar: la rama que vuelve, a CORTE de donde sale de las vueltas de encima, y el
        # chicote, a CORTE del borde de la punta.
        x_borde = self._fin_primeras() - PASO_VUELTA / 2
        piezas = self._seno(x_curva, x_borde - CORTE, redonda=True) + tirado
        sale = piezas[-1]
        sale.M = sale.M[sale.M[:, 0] <= x_sale + CORTE]
        return piezas, cuelga

    def _paso(self, hito: str) -> dict:
        piezas, cuelga = self._piezas(hito)
        # El mapa entero, muestreado parejo, con la pieza de cada punto.
        partes, cual = [], []
        for k, pz in enumerate(piezas):
            m = pz.M
            if partes and np.linalg.norm(m[0] - partes[-1][-1]) < 1e-9:
                m = m[1:]
            partes.append(m)
            cual.append(np.full(len(m), k))
        M, cual = np.vstack(partes), np.concatenate(cual)
        s_crudo = _largo(M)
        Q = _remuestrear(M, PASO_MAPA)
        sQ = np.linspace(0.0, s_crudo[-1], len(Q))
        pieza = cual[np.clip(np.searchsorted(s_crudo, sQ, side="right") - 1, 0, len(cual) - 1)]
        cruces = self._cruces(Q, pieza, piezas)
        h = self._alturas(Q, sQ, pieza, piezas, cruces)
        X = self._en(Q[:, 0], Q[:, 1], h)
        # Lo que cuelga antes del mapa, en el orden de la cuerda.
        antes = np.empty((0, 3))
        if cuelga["antes"] == "punta":
            # El corto pasa la punta del cabo y cae a la mesa delante del corte.
            P0 = X[0]
            antes = self._caer(P0, np.array([1.0, 0.0, 0.0]), (1.0, -0.15), largo=max(3.0, P0[2] - 0.5))[::-1]
        elif cuelga["antes"] == "cola":
            antes = self._caer(X[0], X[0] - X[1], (-0.6, -0.8))[::-1]
        despues = np.empty((0, 3))
        if cuelga["despues"] == "punta":
            despues = self._caer(X[-1], np.array([1.0, 0.0, 0.0]), (1.0, -0.15), largo=max(3.0, X[-1][2] - 0.5))
        elif cuelga["despues"] is not None:
            despues = self._caer(X[-1], X[-1] - X[-2], cuelga["despues"])
        secuencia = self._secuencia(cruces, sQ)
        return {"Q": Q, "s": sQ, "pieza": pieza, "piezas": piezas, "X": X, "h": h,
                "antes": antes, "despues": despues, "cruces": cruces, "secuencia": secuencia}

    def _cruces(self, Q, pieza, piezas) -> list[dict]:
        """Los cruces de la cuerda en el mapa, con la pieza de encima y su etiqueta."""
        from .cabeza_turco import cruces_del_mapa
        out = []
        for sa, sb, seno, p in cruces_del_mapa(Q, PASO_MAPA, self.C):
            ia, ib = int(round(sa / PASO_MAPA)), int(round(sb / PASO_MAPA))
            a, b = piezas[pieza[min(ia, len(pieza) - 1)]], piezas[pieza[min(ib, len(pieza) - 1)]]
            if a.nombre == b.nombre:
                continue
            na, nb = self._nivel(a), self._nivel(b)
            if na == nb:
                raise ValueError(f"{a.nombre} y {b.nombre} se cruzan y tienen el mismo nivel")
            clave = (a.nombre, b.nombre, round(p[0], 1), round(p[1] % self.C, 1))
            etiqueta = self._etiquetas.setdefault(clave, str(len(self._etiquetas) + 1))
            out.append({"sa": sa, "sb": sb, "seno": seno, "encima": na > nb, "lugar": p,
                        "etiqueta": etiqueta, "piezas": (a.nombre, b.nombre)})
        return out

    def _nivel(self, pz: _Pieza) -> float:
        if pz.tipo == "chicote" and self.variante == "por-fuera-del-seno":
            return 2.5
        return NIVEL[pz.tipo]

    def _alturas(self, Q, s, pieza, piezas, cruces) -> np.ndarray:
        """Cuánto se aleja cada punto del cabo. Las piezas se apilan de la más baja a la más
        alta: un punto que en el mapa queda a menos de APILA de un tramo más bajo (que no sea su
        vecino a lo largo de la cuerda) va un diámetro sobre él. Después, toda la cuerda sube y
        baja en rampas suaves de RAMPA, así que un tramo que pasa por encima de otro sube antes
        y baja después, aunque cambie de pieza."""
        from scipy.spatial import cKDTree
        niveles = np.array([self._nivel(piezas[k]) for k in pieza])
        h = np.zeros(len(Q))
        Qm = np.column_stack([Q[:, 0], np.mod(Q[:, 1], self.C)])
        # Para cada nivel, los puntos más bajos que cada uno tiene debajo en el mapa.
        debajo = {}
        for nivel in sorted(set(niveles.tolist())):
            bajos = np.nonzero(niveles < nivel)[0]
            aqui = np.nonzero(niveles == nivel)[0]
            if not len(bajos):
                continue
            # El mapa da la vuelta en u: los tramos bajos van también corridos una vuelta.
            B = np.vstack([Qm[bajos] + [0.0, k * self.C] for k in (-1, 0, 1)])
            idx = np.tile(bajos, 3)
            for i, vecinos in zip(aqui, cKDTree(B).query_ball_point(Qm[aqui], APILA)):
                j = idx[vecinos] if vecinos else np.empty(0, int)
                j = j[np.abs(s[j] - s[i]) > VECINO]
                if len(j):
                    debajo[i] = j
        paso = s[1] - s[0]

        def apilar(base):
            """Desde `base`, cada punto va un diámetro sobre lo que tiene debajo, con las rampas
            que suben a tramos de su nivel o más altos. Se repite hasta que nada cambia: lo que
            sube levanta a lo que tiene encima."""
            h = base.copy()
            for _ in range(12):
                crudo = np.zeros(len(Q))
                for i, j in debajo.items():
                    crudo[i] = float(h[j].max()) + 1.0
                crudo = _puentes(crudo, pieza, paso)
                nuevo = np.maximum(base, _rampas(crudo, paso, niveles))
                if np.allclose(nuevo, h, atol=1e-6):
                    break
                h = nuevo
            return h, crudo

        h, crudo = apilar(np.zeros(len(Q)))
        cubierto = np.zeros(len(Q), bool)
        for j in debajo.values():
            cubierto[j] = True
        # Al pasar por el seno, la rampa de la última vuelta baja también al chicote, que sale
        # de ella y no tiene nada encima. Una sola vez: lo que eso levanta se apila otra vez sin
        # bajar de nuevo, así que no da vueltas. Al tirar, el chicote entra enseguida bajo las
        # vueltas, y ahí la rampa levantaría todo lo que va encima.
        chicote = np.array([piezas[k].tipo == "chicote" for k in pieza]) & ~cubierto
        if chicote.any():
            h, _ = apilar(np.where(chicote, np.maximum(h, _rampas(crudo, paso, None)), h))
        # El chicote tampoco baja entre dos subidas cercanas, como en el error, donde sale de
        # la última vuelta y pasa por encima de la curva del seno.
        if chicote.any():
            h = np.where(chicote, np.maximum(h, _puentes(h, chicote.astype(int), paso)), h)
        return h

    def _secuencia(self, cruces, s) -> tuple[str, ...]:
        pasadas = []
        for c in cruces:
            pasadas.append((c["sa"], c["etiqueta"] + ("O" if c["encima"] else "U")))
            pasadas.append((c["sb"], c["etiqueta"] + ("U" if c["encima"] else "O")))
        return tuple(t for _, t in sorted(pasadas))

    # --- El paso ----------------------------------------------------------------------
    def trazo(self, hito: str, previo: str | None) -> TrazoDePaso:
        """Los puntos de control del paso: lo que cuelga antes, la cuerda sobre el cabo y lo
        que cae a la mesa después. Se resalta lo que se mueve en el paso."""
        hito = self.alias.get(hito, hito)
        previo = self.alias.get(previo, previo)
        if self.variante is not None and self.orden.index(hito) > self.orden.index("por-el-seno"):
            raise ValueError("la variante por-fuera-del-seno se ve solo al pasar el chicote")
        if hito in self._errores:
            raise self._errores[hito]
        d = self._pasos[hito]
        paso = max(1, int(round(PASO_CONTROL / PASO_MAPA)))
        idx = np.unique(np.r_[np.arange(0, len(d["X"]), paso), len(d["X"]) - 1])
        Xc = d["X"][idx]
        sc = d["s"][idx]
        P = np.vstack([d["antes"], Xc, d["despues"]])
        Z = np.r_[np.full(len(d["antes"]), MESA), np.full(len(Xc), CABO), np.full(len(d["despues"]), MESA)]
        n0 = len(d["antes"])
        a, b = self._resaltado(hito, previo, d)
        inicio = None if a is None else n0 + int(np.searchsorted(sc, a - 1e-9))
        fin = n0 + int(np.searchsorted(sc, b - 1e-9)) if b is not None else n0 + len(Xc) - 1
        if a is None and b == 0.0:
            inicio, fin = 0, 0
        return TrazoDePaso(P, Z, min(fin, len(P) - 1), inicio)

    def _resaltado(self, hito, previo, d) -> tuple[float | None, float | None]:
        """Desde y hasta dónde se resalta, a lo largo del mapa: None al principio es desde la
        punta de la cuerda; None al final, hasta el final del mapa."""
        s, pieza, piezas = d["s"], d["pieza"], d["piezas"]

        def fin_de(nombre):
            k = [i for i, pz in enumerate(piezas) if pz.nombre == nombre]
            return float(s[pieza == k[0]].max()) if k else None

        def inicio_de(nombre):
            k = [i for i, pz in enumerate(piezas) if pz.nombre == nombre]
            return float(s[pieza == k[0]].min()) if k else None

        n = self.p.vueltas
        if hito == "cortar":
            return None, 0.0
        if hito in ("seno", "tirar"):
            return None, fin_de("curva")
        if hito == "colocar":
            return None, None
        if hito.startswith("vuelta-") or hito.startswith("seno-vuelta-"):
            # Desde donde terminaba el paso anterior.
            k = self._vueltas_de(hito)
            k0 = self._vueltas_de(previo)
            a = inicio_de(f"vuelta-{k0 + 1}") if k0 is not None and k0 < k else inicio_de("vuelta-1")
            return a, None
        if hito == "por-el-seno":
            k0 = self._vueltas_de(previo)
            a = inicio_de(f"vuelta-{k0 + 1}") if k0 is not None else inicio_de("chicote")
            return a, None
        return None, None

    def _vueltas_de(self, hito: str | None) -> int | None:
        """Cuántas vueltas tiene la cuerda en ese hito."""
        n = self.p.vueltas
        if hito is None or hito == "colocar":
            return 0
        if hito.startswith("vuelta-"):
            return int(hito.split("-")[1])
        if hito == "seno":
            return n
        if hito.startswith("seno-vuelta-"):
            return n + int(hito.split("-")[2])
        return None


def buscar_en_el_cabo(X, h: float, zonas, cabo):
    """Los cruces de la cuerda y la altura de sus dos pasadas: sobre el cabo, en su superficie
    desenrollada (x a lo largo del eje y el arco alrededor, con periodo de una vuelta), donde
    encima es lo más lejos del eje, y en la mesa, en la proyección de siempre, donde encima es
    lo más alto. Entre una zona y la otra no se buscan. Cada cruce guarda su lugar en la mesa."""
    from ..cruces import Cruce, cruces_2d
    s = np.arange(len(X)) * h
    x, th, r = cabo.cilindricas(X)
    u = np.unwrap(th) * cabo.rb
    cruces, alturas = [], []
    for zona, M, alto, periodo in ((CABO, np.column_stack([x, u]), r, 2 * math.pi * cabo.rb),
                                   (MESA, X[:, :2], X[:, 2], None)):
        validos = (zonas[:-1] == zona) & (zonas[1:] == zona)
        for sa, sb, seno, _ in cruces_2d(M, validos, h, periodo=periodo):
            p = (float(np.interp(sa, s, X[:, 0])), float(np.interp(sa, s, X[:, 1])))
            cruces.append(Cruce(sa, sb, p, seno))
            alturas.append((float(np.interp(sa, s, alto)), float(np.interp(sb, s, alto))))
    orden = sorted(range(len(cruces)), key=lambda k: cruces[k].sa)
    return [cruces[k] for k in orden], [alturas[k] for k in orden]
