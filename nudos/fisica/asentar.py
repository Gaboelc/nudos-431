"""Asentar y apretar con el motor (T15d): los modos 1 y 2 del plan.

- **Asentar un paso** (`asentar_paso`, reemplaza a `relajar()` con la opción del motor): parte
  del trazado o de la plantilla. Las manos sostienen el firme y el chicote, cada tramo lleva la
  tensión de atado del paso, y todo lo demás pesa, se apoya en la mesa y en el anfitrión y roza.
  La cuerda tiene memoria (`Varilla`, `curvatura`): guarda las curvas con que la dejó la mano.
- **Apretar el terminado** (`apretar`, reemplaza a `apretar()`): el último paso asentado, con
  el firme sostenido y los chicotes y los lazos tirados fuerte (`manos.para_apretar`), sin roce
  y sin memoria, hasta que la cuerda deja de moverse. Sin roce, porque apretar bien un nudo es
  acomodarlo tramo por tramo hasta que no le queda holgura: lo que hacen las manos al tirar de
  cada parte vence el roce, y lo que queda es el nudo tallado, como los nudos apretados de
  Pieranski y otros. En un nudo de plantilla, el terminado apretado es el último paso asentado
  con la tensión «apretada» por tramo (`tensiones_de_amarre`): sus vueltas y sus ahorcados ya
  se tiran al darlos, y el roce guarda esa tensión.

Los dos dan pasos cuasiestáticos (`Sistema.paso`) hasta que ningún nodo se mueve más de
QUIETO en un paso. La comprobación es la de siempre (`libre._resultado`): la secuencia
declarada, la separación, la curvatura y el estiramiento, y la consistencia entre pasos.

**Por qué la memoria.** Una cuerda elástica sin memoria no conserva un lazo suelto sobre la
mesa: la rigidez de la de 8 mm empuja con varios newtons y su peso, con el roce, sostiene
milésimas. Una cuerda trenzada de verdad sí lo conserva, porque sus fibras rozan entre sí al
doblarse. Así que en un paso la curvatura de reposo es la de la forma de partida: la cuerda
queda donde la dejó la mano, y el motor solo la asienta. Al apretar no hay memoria: manda la
tensión.

**El punto de partida no se atraviesa.** La IPC necesita partir sin ningún par a menos de dmin.
El trazado elevado puede tener tramos que se tocan de más, así que antes de asentar se separan
(`separar`): solo choques, largo, mesa y anfitrión, sin gravedad ni alisado.

Unidades: diámetros de la cuerda de grosor 1 y newtons. Con varias cuerdas de distinto grosor,
cada una con su material (`material_de`) y el contacto compuesto (`ContactoCompuesto`).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .contacto import DHAT, DMIN, VECINOS, ContactoCompuesto, MallaContacto, cilindro, rigidez_barrera
from .integrador import Sistema
from .manos import SOSTENIDOS, Manos, cortes_de, para_apretar, sostener
from .materiales import CUERDA_8MM, Material
from .varilla import Varilla

# La tensión de atado de cada tramo, en N. «Ajustada» es lo que deja una mano al acomodar el
# nudo; «apretada», lo que se tira al apretarlo (T14a: 60 N en las vueltas del amarre). Se
# calibran con cuerda real en T15e.
TENSIONES = {"suelta": 0.0, "ajustada": 20.0, "apretada": 60.0}
FACTOR_AHORCADO = 2.5     # un ahorcado se tira más fuerte: 150 N con «apretada» (T14a)
FUERZA_APRETAR = 60.0     # N con que se tira de cada parte del nudo al apretarlo
QUIETO = 1e-3             # diámetros por paso: menos que esto es que la cuerda dejó de moverse
MAX_PASOS = 300
AMORTIGUACION = 2.0       # N/d por nodo, la de los pasos cuasiestáticos (T15c)
# La separación mínima entre ejes que deja `separar`, en sumas de radios: algo más que la
# distancia mínima de la barrera (0,95), porque la IPC mide entre tramos y no entre nodos (hasta
# 0,01 menos con tramos de 0,2); la barrera las termina de separar. Con 1,03, separar doblaba con
# radio 0,29 el comienzo del amarre, que pasa entre la mesa y el palo de abajo, donde cabe justo.
SEPARAR_A = 0.98
# El radio de curvatura mínimo de la cuerda de partida, en diámetros (la comprobación pide 0,9).
RADIO_PARTIDA = 1.1
# La malla de un anfitrión va este tanto (en diámetros de la cuerda) más adentro que la madera:
# la cuerda que la plantilla apoya en la madera queda arriba en la franja de la barrera y no
# apretada de entrada. Sin esto, los ahorcados del amarre, metidos entre los dos palos, quedaban
# acuñados y se estiraban un 4 %. Es lo de T14a (la malla a radio − 0,56).
HOLGURA_SOLIDO = 0.06


class SinMotor(ValueError):
    """El motor todavía no sabe asentar este nudo (su anfitrión llega en T15f)."""


def material_de(grosor: float, base: Material = CUERDA_8MM) -> Material:
    """El material de una cuerda `grosor` veces más gruesa que la de 8 mm, en las unidades de
    esa: la tracción y el peso crecen con el área (g²) y la flexión, con g⁴."""
    g = float(grosor)
    if g == 1.0:
        return base
    return replace(base, EA=base.EA * g ** 2, EI=base.EI * g ** 4, GJ=base.GJ * g ** 4,
                   peso_por_d=base.peso_por_d * g ** 2)


# --------------------------------------------------------------------------
# El contacto: la mesa, el anfitrión y las cuerdas
# --------------------------------------------------------------------------
def solidos(solido, grosor: float = 1.0) -> list:
    """El anfitrión como mallas para el contacto de una cuerda de `grosor`. La malla va un radio
    de cuerda (y HOLGURA_SOLIDO) por dentro de la madera: la barrera deja el eje a dmin + dhat/2
    = un diámetro de ella, donde la cuerda toca la madera. Sin anfitrión, ninguno."""
    from ..anfitrion import Cruz, Poste
    if solido is None:
        return []
    r = grosor / 2 + HOLGURA_SOLIDO * grosor
    if type(solido) is Poste:
        largo = solido.hasta - solido.desde
        centro = ((solido.desde + solido.hasta) / 2, 0.0, solido.zc)
        return [cilindro(centro, (1, 0, 0), solido.radio - r, largo)]
    if type(solido) is Cruz:
        return [cilindro((0, 0, solido.zb), (0, 1, 0), solido.radio - r, solido.largo),
                cilindro((0, 0, solido.zt), (1, 0, 0), solido.radio - r, solido.largo)]
    raise SinMotor(f"el motor todavía no tiene el anfitrión «{type(solido).__name__}» (T15f)")


def contacto(X, cortes, grosores, solido=None):
    """El contacto de las cuerdas de X (sus nodos repartidos por `cortes`, una cuerda por grosor
    de `grosores`) con la mesa, el anfitrión y entre sí."""
    X = np.asarray(X, float)
    N = len(X)
    grosores = [float(g) for g in grosores]
    nodos_por = np.diff(cortes).tolist()
    clases = sorted(set(grosores))

    def malla(nodos, cuerdas, g, con_solidos=True, parches=None, dist=None):
        d = g if dist is None else dist
        return MallaContacto(X[nodos], solidos(solido, g) if con_solidos else (),
                             altura_mesa=0.0 if con_solidos else None,
                             dmin=DMIN * d, dhat=DHAT * d, vecinos=VECINOS * d,
                             nodos_por_cuerda=cuerdas, radio_cuerda=g / 2, parches=parches)

    if len(clases) == 1:
        return malla(np.arange(N), nodos_por, clases[0])
    por_clase = {g: [k for k, gk in enumerate(grosores) if gk == g] for g in clases}

    def nodos_de(ks):
        return np.concatenate([np.arange(cortes[k], cortes[k + 1]) for k in ks])

    partes = [(malla(nodos_de(ks), [nodos_por[k] for k in ks], g), nodos_de(ks))
              for g, ks in por_clase.items()]
    for i, g1 in enumerate(clases):
        for g2 in clases[i + 1:]:
            ks = sorted(por_clase[g1] + por_clase[g2])
            nodos = nodos_de(ks)
            parches = np.concatenate([np.full(nodos_por[k], int(grosores[k] == g2)) for k in ks])
            partes.append((malla(nodos, [nodos_por[k] for k in ks], min(g1, g2), con_solidos=False,
                                 parches=parches, dist=(g1 + g2) / 2), nodos))
    return ContactoCompuesto(partes, N)


# --------------------------------------------------------------------------
# Separar el punto de partida
# --------------------------------------------------------------------------
def separar(X, h, reparto=None, solido=None, iteraciones: int = 2000):
    """X con ningún par de tramos a menos de SEPARAR_A veces la suma de sus radios, apoyada
    sobre la mesa, fuera del anfitrión, sin doblarse más que RADIO_PARTIDA y con cada tramo de
    largo h (a 0,5 %). Solo choques, largo y curva, sin gravedad: la forma cambia lo justo. Los
    primeros nodos de cada cuerda, que sostiene la mano del firme, no se mueven.

    La curva se corrige en la misma vuelta que los choques: los choques doblan la cuerda donde
    no cabe (el comienzo del amarre, entre la mesa y el palo de abajo, quedaba con radio 0,21), y
    la memoria guardaría ese doblez. Si al final quedan tramos a menos de SEPARAR_A − 0,015 (la
    IPC parte de más de 0,95 entre tramos, hasta 0,01 menos que entre nodos), es un
    TrazadoError: la IPC no puede partir de una cuerda que se atraviesa."""
    from ..libre import Reparto, TrazadoError, _colisiones, _largos, _limitar_curva, _separacion
    X = np.array(X, float)
    rep = reparto or Reparto.una(len(X))
    salto, radio, seguido = rep.salto(h), rep.radio, rep.seguido
    libre = np.ones(len(X), bool)
    for i in rep.inicios:
        libre[i:i + SOSTENIDOS] = False
    for _ in range(iteraciones):
        malos = _limitar_curva(X, h, libre, rmin=RADIO_PARTIDA, ganancia=0.35, grosor=rep.grosor,
                               interior=rep.interior)
        largo = np.linalg.norm(np.diff(X, axis=0), axis=1)[seguido] / h - 1
        if (not malos and np.abs(largo).max() < 0.005
                and _separacion(X, h, rep)[0] >= SEPARAR_A + 0.005
                and _penetra(X, rep, solido) <= 1e-3):
            break
        _colisiones(X, salto, libre, rep, radio * (SEPARAR_A + 0.01))
        X[:, 2] = np.maximum(X[:, 2], radio)
        if solido is not None:
            solido.empujar(X, libre)
        _largos(X, h, libre, pasadas=16, seguido=seguido)
    if _separacion(X, h, rep)[0] < SEPARAR_A - 0.015:
        raise TrazadoError("el motor no pudo separar los tramos de la cuerda de partida: dos "
                           f"quedan a {_separacion(X, h, rep)[0]:.2f}")
    return X


def _penetra(X, rep, solido) -> float:
    fuera = float(np.max(rep.radio - X[:, 2]))
    if solido is not None:
        fuera = max(fuera, solido.penetracion(X))
    return fuera


# --------------------------------------------------------------------------
# Los pasos de la cuerda hasta que deja de moverse
# --------------------------------------------------------------------------
@dataclass
class Asentado:
    X: np.ndarray        # (N, 3)
    pasos: int
    movimiento: float    # cuánto se movió el nodo que más se movió en el último paso
    quieto: bool         # si dejó de moverse antes de MAX_PASOS
    newton: int          # iteraciones de Newton en total
    aceptado: int | None = None   # con `aceptar`, el último paso que cumplía (0: el de partida)


def asentar(X, cortes, grosores, manos: Manos, solido=None, memoria: bool = True,
            roce: bool = True, quieto: float = QUIETO, max_pasos: int = MAX_PASOS,
            kappa: float | None = None, largos=None, registro=None,
            amortiguacion: float = AMORTIGUACION, aceptar=None, paciencia: int = 15) -> Asentado:
    """Pasos cuasiestáticos desde X hasta que la cuerda deja de moverse. X ya tiene que estar
    separada (`separar`). `largos` (N,) son los largos de reposo de cada tramo, el que empieza
    en cada nodo (por omisión, los de X): separar estira un poco la cuerda, y ella vuelve a su
    largo. `registro(paso, movimiento, iteraciones, convergio)`, si se da, se llama en cada
    paso. Con `aceptar(x) -> bool`, el resultado es el último paso que cumple (o el de partida,
    si ninguno), aunque la cuerda siga moviéndose después: así se aprieta un nudo hasta donde
    se sigue viendo como en su ficha. Si después de cumplir pasan `paciencia` pasos sin que
    vuelva a cumplir, no se sigue."""
    X = np.asarray(X, float)
    varillas = []
    for k, (a, b) in enumerate(zip(cortes[:-1], cortes[1:])):
        Xk = X[a:b]
        l = (np.linalg.norm(np.diff(Xk, axis=0), axis=1) if largos is None
             else np.asarray(largos, float)[a:b - 1])
        mat = material_de(grosores[k])
        if manos.tension is not None:
            l = l / (1 + manos.tension[a:b - 1] / mat.EA)
        varillas.append(Varilla(l, mat, curvatura=Varilla.curvatura_de(Xk) if memoria else None))
    malla = contacto(X, cortes, grosores, solido)
    if kappa is None:
        # La barrera, para que un nodo que se apoya con la tensión más alta sobre una cuerda
        # quede a media franja (una cuerda con tensión T sobre otra aprieta T·h por nodo).
        h = float(np.mean(np.concatenate([v.l for v in varillas])))
        T = max(float(np.max(np.abs(manos.fuerzas))) if manos.fuerzas.size else 0.0,
                float(np.max(manos.tension)) if manos.tension is not None and manos.tension.size else 0.0)
        kappa = rigidez_barrera(max(1.0, T * h))
    sis = Sistema(varillas, malla, fijos=manos.fijos, fuerzas=manos.fuerzas, kappa=kappa, roce=roce)
    x = X.copy()
    mov, n_newton = np.inf, 0
    mejor, cuando = (x, 0) if aceptar is not None else (None, None)
    for paso in range(1, max_pasos + 1):
        r = sis.paso(x, amortiguacion=amortiguacion)
        mov = float(np.max(np.linalg.norm(r.x - x, axis=1)))
        x = r.x
        n_newton += r.iteraciones
        if registro is not None:
            registro(paso, mov, r.iteraciones, r.convergio)
        if aceptar is not None:
            if aceptar(x):
                mejor, cuando = x, paso
            elif paso - cuando > paciencia:
                break
        if mov < quieto:
            break
    else:
        paso = max_pasos
    return Asentado(x if mejor is None else mejor, paso, mov, mov < quieto, n_newton, cuando)


# --------------------------------------------------------------------------
# Los dos modos
# --------------------------------------------------------------------------
def _cortes_y_grosores(N: int, reparto):
    if reparto is None:
        return np.array([0, N]), [1.0]
    tramos = reparto.tramos
    return cortes_de([b - a + 1 for a, b in tramos]), [float(reparto.grosor[a]) for a, _ in tramos]


def tension_por_tramo(N: int, valor: float | np.ndarray) -> np.ndarray:
    """La tensión de atado (N,) de un valor para todos los tramos (el último nodo no empieza
    ningún tramo; ese lugar se ignora)."""
    return np.broadcast_to(np.asarray(valor, float), (N,)).copy()


def asentar_paso(X, h, reparto=None, solido=None, tension: str | np.ndarray = "ajustada",
                 sostenidos=(), chicote: bool = False, memoria: bool = True,
                 nodos_mano: int = SOSTENIDOS) -> Asentado:
    """El modo 1: la cuerda de un paso (el trazado elevado o la curva de la plantilla),
    separada y asentada con el firme sostenido, la tensión de atado `tension` (un nombre de
    TENSIONES o una por nodo) y la memoria de su forma (`memoria`). `sostenidos` son otros nodos
    sostenidos.

    Con `chicote`, también se sostiene la punta del chicote: la tensión de atado solo dura si
    las dos puntas están sostenidas (con una suelta, la cuerda se acorta T/EA y nada más). En
    un nudo libre no hace falta: la tensión «ajustada» de un paso no cambia un lazo suelto, y
    sostener el chicote dejaba tramos estirados en el reverso de la vuelta de escota. En un
    amarre sí: sus vueltas y sus ahorcados se tiran contra las dos puntas. `nodos_mano` es
    cuántos nodos sostiene cada mano (ver `manos.sostener`)."""
    # Cada tramo mide h en reposo: el trazado se muestrea cada h sobre la mesa y después se
    # eleva en los cruces, así que ahí sus tramos quedan más largos (relajar() los vuelve a h).
    largos = np.full(len(X), float(h))
    X0 = separar(X, h, reparto, solido)
    cortes, grosores = _cortes_y_grosores(len(X0), reparto)
    T = TENSIONES[tension] if isinstance(tension, str) else tension
    manos = sostener(cortes, len(X0), chicotes=chicote, extra=sostenidos, nodos=nodos_mano)
    manos.tension = tension_por_tramo(len(X0), T)
    return asentar(X0, cortes, grosores, manos, solido, memoria=memoria, roce=True, largos=largos)


def apretar(X, reparto=None, solido=None, cruces_xy=(), fuerza: float = FUERZA_APRETAR,
            aceptar=None, **kw) -> Asentado:
    """El modo 2: el nudo terminado X (el último paso asentado), con el firme sostenido y los
    chicotes y los lazos tirados con `fuerza`, sin roce ni memoria. Con `aceptar`, lo más
    apretado que todavía cumple (ver `asentar`)."""
    cortes, grosores = _cortes_y_grosores(len(X), reparto)
    manos = para_apretar(X, cortes, cruces_xy, fuerza)
    return asentar(X, cortes, grosores, manos, solido, memoria=False, roce=False, aceptar=aceptar, **kw)


def tensiones_de_amarre(N: int, s_hitos: dict[str, float], h: float, hasta: float,
                        tension: str) -> np.ndarray:
    """La tensión de atado (N,) de un paso de un amarre: la de `tension` en lo que ya está atado
    (hasta la posición `hasta` a lo largo de la cuerda), FACTOR_AHORCADO veces más en los
    ahorcados (entre el último hito de las vueltas y el último ahorcado) y nada en lo que sigue
    suelto sobre la mesa. `s_hitos` da la posición a lo largo de la cuerda de cada hito."""
    T = TENSIONES[tension]
    s = np.arange(N) * h
    out = np.where(s < hasta, T, 0.0)
    vueltas = [v for k, v in s_hitos.items() if k.startswith("vuelta")]
    ahorcados = [v for k, v in s_hitos.items() if k.startswith("ahorcado")]
    if vueltas and ahorcados:
        en = (s >= max(vueltas)) & (s < max(ahorcados)) & (s < hasta)
        out[en] = T * FACTOR_AHORCADO
    return out
