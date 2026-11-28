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
- **Tallar el terminado de un amarre** (`tallar`, prototipo del 28 nov, a prueba): como al
  atarlo de verdad, cada parte se acorta hasta su tensión y la holgura sale por la punta (ver
  abajo). La cuerda tallada se vuelve a muestrear, así que tiene menos nodos que el último paso.

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

from .contacto import DHAT, DMIN, VECINOS, ContactoCompuesto, MallaContacto, rigidez_barrera
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
# Pasos seguidos en que Newton no converge antes de rendirse (T15f). En el paso 3 del adujado,
# Newton gastaba sus 500 iteraciones en cada paso, 90 s cada uno, y con MAX_PASOS el paso
# habría tardado horas. Ningún paso de los pilotos deja de converger ni una vez.
MAX_SIN_CONVERGER = 2
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
# La cornamusa va sin holgura (antes de T19). Bajo cada cuerno cabe justo una cuerda
# (HUECO_CORNAMUSA mide un diámetro), y con la holgura la tensión de atado subía la cuerda contra
# el cuerno hasta 0,06 dentro de la madera, más de lo que acepta la comprobación
# (anfitrion.PENETRACION_MAX, 0,05). Sin holgura, la barrera no la deja entrar más que 1 − DMIN.
HOLGURA_CORNAMUSA = 0.0


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
    de cuerda (y HOLGURA_SOLIDO; en la cornamusa, HOLGURA_CORNAMUSA) por dentro de la madera: la
    barrera deja el eje a dmin + dhat/2 = un diámetro de ella, donde la cuerda toca la madera.
    Sin anfitrión, ninguno."""
    from ..anfitrion import Cornamusa
    from .solidos import mallas
    if solido is None:
        return []
    holgura = HOLGURA_CORNAMUSA if isinstance(solido, Cornamusa) else HOLGURA_SOLIDO
    return mallas(solido, grosor / 2 + holgura * grosor)


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
def separar(X, h, reparto=None, solido=None, iteraciones: int = 2000, quietos=None):
    """X con ningún par de tramos a menos de SEPARAR_A veces la suma de sus radios, apoyada
    sobre la mesa, fuera del anfitrión, sin doblarse más que RADIO_PARTIDA y con cada tramo de
    largo h (a 0,5 %). Solo choques, largo y curva, sin gravedad: la forma cambia lo justo. Los
    primeros nodos de cada cuerda, que sostiene la mano del firme, no se mueven.

    La curva se corrige en la misma vuelta que los choques: los choques doblan la cuerda donde
    no cabe (el comienzo del amarre, entre la mesa y el palo de abajo, quedaba con radio 0,21), y
    la memoria guardaría ese doblez. Si al final quedan tramos a menos de SEPARAR_A − 0,015 (la
    IPC parte de más de 0,95 entre tramos, hasta 0,01 menos que entre nodos), es un
    TrazadoError: la IPC no puede partir de una cuerda que se atraviesa.

    `quietos` son los nodos que la plantilla ya traza sin choques ni dobleces, y que relajar()
    tampoco mueve (el amarre diagonal y el adujado): aquí tampoco se mueven. Moverlos doblaba la
    vuelta de braza del diagonal con radio 0,47."""
    from ..libre import Reparto, TrazadoError, _colisiones, _largos, _limitar_curva, _separacion
    X = np.array(X, float)
    rep = reparto or Reparto.una(len(X))
    salto, radio, seguido = rep.salto(h), rep.radio, rep.seguido
    libre = np.ones(len(X), bool)
    for i in rep.inicios:
        libre[i:i + SOSTENIDOS] = False
    if quietos is not None:
        libre &= ~np.asarray(quietos, bool)
    mejor, mejor_largo = None, np.inf
    for _ in range(iteraciones):
        antes = X.copy()
        malos = _limitar_curva(X, h, libre, rmin=RADIO_PARTIDA, ganancia=0.35, grosor=rep.grosor,
                               interior=rep.interior)
        largo = float(np.abs(np.linalg.norm(np.diff(antes, axis=0), axis=1)[seguido] / h - 1).max())
        if (not malos and _separacion(antes, h, rep)[0] >= SEPARAR_A + 0.005
                and _penetra(antes, rep, solido) <= 1e-3):
            if largo < 0.005:
                break
            # Sin choques ni dobleces, pero con algún tramo todavía largo o corto: se guarda la
            # mejor. Las correcciones pueden pelearse sin llegar nunca (T15f: en la vuelta de
            # escota, a las 200 vueltas quedaba a 0,6 % y a las 2000 doblaba con radio 0,86,
            # y la memoria guardaba ese doblez). El largo lo termina de dar el motor.
            if largo < mejor_largo:
                mejor, mejor_largo = antes, largo
        _colisiones(X, salto, libre, rep, radio * (SEPARAR_A + 0.01))
        X[:, 2] = np.maximum(X[:, 2], radio)
        if solido is not None:
            solido.empujar(X, libre)
        _largos(X, h, libre, pasadas=16, seguido=seguido)
    else:
        if mejor is not None:
            X = mejor
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
            amortiguacion: float = AMORTIGUACION, aceptar=None, paciencia: int = 15,
            trayectoria: list | None = None) -> Asentado:
    """Pasos cuasiestáticos desde X hasta que la cuerda deja de moverse. X ya tiene que estar
    separada (`separar`). `largos` (N,) son los largos de reposo de cada tramo, el que empieza
    en cada nodo (por omisión, los de X): separar estira un poco la cuerda, y ella vuelve a su
    largo. `registro(paso, movimiento, iteraciones, convergio)`, si se da, se llama en cada
    paso. Con `aceptar(x) -> bool`, el resultado es el último paso que cumple (o el de partida,
    si ninguno), aunque la cuerda siga moviéndose después: así se aprieta un nudo hasta donde
    se sigue viendo como en su ficha. Si después de cumplir pasan `paciencia` pasos sin que
    vuelva a cumplir, no se sigue. Con `trayectoria` (una lista), se le agrega la cuerda de
    cada paso: el video (T18) muestra el apretado con ellas."""
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
    margen = malla.margen(X)
    if margen <= 0:
        # La IPC no puede partir de una cuerda que ya está dentro de la barrera: su energía no
        # está definida ahí. Pasa cuando `separar` no llega a una cuerda de partida válida, como
        # en la vuelta de cornamusa y el amarre diagonal (T15f): mejor una falla del paso que un
        # error de ipctk que tumba toda la construcción, o un asentado con avisos.
        from ..libre import TrazadoError
        raise TrazadoError("el motor no puede partir de esta cuerda: un par queda "
                           f"{-margen:.2f} diámetros dentro de la barrera del contacto")
    if kappa is None:
        # La barrera, para que un nodo que se apoya con la tensión más alta sobre una cuerda
        # quede a media franja (una cuerda con tensión T sobre otra aprieta T·h por nodo).
        h = float(np.mean(np.concatenate([v.l for v in varillas])))
        T = max(float(np.max(np.abs(manos.fuerzas))) if manos.fuerzas.size else 0.0,
                float(np.max(manos.tension)) if manos.tension is not None and manos.tension.size else 0.0)
        kappa = rigidez_barrera(max(1.0, T * h))
    sis = Sistema(varillas, malla, fijos=manos.fijos, fuerzas=manos.fuerzas, kappa=kappa, roce=roce)
    x = X.copy()
    mov, n_newton, sin_converger = np.inf, 0, 0
    mejor, cuando = (x, 0) if aceptar is not None else (None, None)
    for paso in range(1, max_pasos + 1):
        r = sis.paso(x, amortiguacion=amortiguacion)
        mov = float(np.max(np.linalg.norm(r.x - x, axis=1)))
        x = r.x
        n_newton += r.iteraciones
        if trayectoria is not None:
            trayectoria.append(x.copy())
        if registro is not None:
            registro(paso, mov, r.iteraciones, r.convergio)
        sin_converger = 0 if r.convergio else sin_converger + 1
        if sin_converger >= MAX_SIN_CONVERGER:
            if aceptar is not None:
                break   # se queda con lo más apretado que cumplía
            from ..libre import TrazadoError
            raise TrazadoError(f"el motor no converge: {sin_converger} pasos seguidos sin que "
                               f"Newton llegue (paso {paso})")
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
                 nodos_mano: int = SOSTENIDOS, quietos=None, separada: bool = False) -> Asentado:
    """El modo 1: la cuerda de un paso (el trazado elevado o la curva de la plantilla),
    separada y asentada con el firme sostenido, la tensión de atado `tension` (un nombre de
    TENSIONES o una por nodo) y la memoria de su forma (`memoria`). `sostenidos` son otros nodos
    sostenidos.

    Con `chicote`, también se sostiene la punta del chicote: la tensión de atado solo dura si
    las dos puntas están sostenidas (con una suelta, la cuerda se acorta T/EA y nada más). En
    un nudo libre no hace falta: la tensión «ajustada» de un paso no cambia un lazo suelto, y
    sostener el chicote dejaba tramos estirados en el reverso de la vuelta de escota. En un
    amarre sí: sus vueltas y sus ahorcados se tiran contra las dos puntas. `nodos_mano` es
    cuántos nodos sostiene cada mano (ver `manos.sostener`).

    `quietos` son los nodos que `separar` no mueve. Con `separada`, X ya es una cuerda de
    partida sin choques ni dobleces y no se separa: la relajada con que se vuelve a asentar un
    paso cuando separar no puede (`libre.asentar_o_relajar`)."""
    # Cada tramo mide h en reposo: el trazado se muestrea cada h sobre la mesa y después se
    # eleva en los cruces, así que ahí sus tramos quedan más largos (relajar() los vuelve a h).
    largos = np.full(len(X), float(h))
    X0 = np.array(X, float) if separada else separar(X, h, reparto, solido, quietos=quietos)
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


def partes_de_amarre(N: int, s_hitos: dict[str, float], h: float) -> np.ndarray:
    """La parte de cada tramo (N − 1) de la cuerda de un amarre, como en `tensiones_de_amarre`:
    0, las vueltas (con el ballestrinque de inicio); 1, los ahorcados (entre el último hito de
    las vueltas y el último ahorcado, con las segundas vueltas del amarre diagonal), y 2, el
    cierre. Sin vueltas o sin ahorcados, todo es la parte 0."""
    s = (np.arange(N - 1) + 0.5) * h
    vueltas = [v for k, v in s_hitos.items() if k.startswith("vuelta")]
    ahorcados = [v for k, v in s_hitos.items() if k.startswith("ahorcado")]
    out = np.zeros(N - 1, int)
    if vueltas and ahorcados:
        out[(s >= max(vueltas)) & (s < max(ahorcados))] = 1
        out[s >= max(ahorcados)] = 2
    return out


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


# --------------------------------------------------------------------------
# Tallar el terminado de un amarre (prototipo del 28 nov, a prueba)
# --------------------------------------------------------------------------
# Gabriel ató el amarre cuadrado con paracord (28 nov, entradas/t15e/amarre-cuadrado-*.jpg): las
# vueltas abrazan los palos en bandas y los ahorcados las aprietan contra el cruce. Asentar el
# último paso con la tensión «apretada» casi no lo cambia: con las dos puntas sostenidas, la
# cuerda solo puede acortarse lo que la estira la tensión (T/EA, 0,3 % con 60 N), y la holgura que
# la plantilla deja en las vueltas (un 5 %) y en los ahorcados (más del 20 %) no tiene por dónde
# salir. Al atar de verdad sale por la punta: se tira de cada vuelta y de cada ahorcado hasta que
# queda tenso.
#
# `tallar` hace eso por partes (`partes_de_amarre`). En cada ronda, la cuerda se asienta unos pasos
# y cada parte que todavía no llega a su tensión se acorta (su largo de reposo), más cuanto más
# floja está. La cuerda acortada se vuelve a muestrear cada h desde el firme
# (`remuestrear_material`): lo que falta al final es lo que salió por la punta, y la coordenada
# material de cada punto dice de qué punto de la cuerda de partida viene (en una plantilla, su
# zona). La memoria sigue a la cuerda: la forma que deja una ronda es la de reposo de la
# siguiente, así que manda la tensión y nada vuelve a la forma de la plantilla. Como al apretar
# un nudo libre, queda la ronda más apretada que todavía cumple (`aceptar`).
#
# Las vueltas van ajustadas y no apretadas: con 60 N, en el amarre cuadrado de hoy, la esquina
# de delante a la derecha de la segunda vuelta se endereza y pasa por fuera del firme más abajo
# de donde la plantilla lo cuenta en el palo de arriba (0,4 d más abajo), y aparece un cruce. Con
# 20 N, los ahorcados se acortan un 15 % antes de que algo cambie: después, el segundo y el
# tercero se montan uno sobre otro bajo el palo de arriba.
TALLAR_TENSIONES = (20.0, 150.0, 60.0)   # N: las vueltas, los ahorcados y el cierre
TALLAR_ACORTA = 0.03     # lo más que se acorta una parte floja en una ronda
TALLAR_MIN = 0.6         # ninguna parte se acorta a menos de este tanto de su largo
TALLAR_RONDAS = 30
TALLAR_PASOS = 8         # pasos del motor por ronda
TALLAR_ASIENTA = 60      # pasos, como mucho, para asentar la cuerda antes de la primera ronda
TALLAR_PACIENCIA = 1     # cuántas rondas seguidas que no cumplen se prueban antes de parar


@dataclass
class Tallado:
    X: np.ndarray            # (M, 3) la cuerda tallada, cada h desde el firme
    material: np.ndarray     # (M,) de qué nodo de la cuerda de partida viene cada punto (fraccionario)
    rondas: int
    aceptada: int | None     # la ronda que quedó; None si ninguna cumple
    tensiones: list          # ronda por ronda, la tensión media de cada parte


def remuestrear_material(Y, h: float) -> tuple[np.ndarray, np.ndarray]:
    """La cuerda Y (N, 3) cada h a lo largo de ella, desde su primer punto y hasta donde alcanza
    (lo que sobra al final, menos que h, se deja). Da también la coordenada material de cada punto
    nuevo: el índice fraccionario del punto de Y donde cae."""
    Y = np.asarray(Y, float)
    seg = np.linalg.norm(np.diff(Y, axis=0), axis=1)
    S = np.concatenate([[0.0], np.cumsum(seg)])
    M = int(np.floor(S[-1] / h + 1e-9)) + 1
    u = np.arange(M) * h
    k = np.clip(np.searchsorted(S, u, side="right") - 1, 0, len(Y) - 2)
    f = np.clip((u - S[k]) / seg[k], 0.0, 1.0)
    return Y[k] + f[:, None] * (Y[k + 1] - Y[k]), k + f


def tallar(X, h: float, partes, solido=None, tensiones=TALLAR_TENSIONES, tension_inicial=None,
           quietos=None, aceptar=None, rondas: int = TALLAR_RONDAS, pasos: int = TALLAR_PASOS,
           paciencia: int = TALLAR_PACIENCIA, registro=None, separada: bool = False) -> Tallado:
    """El terminado de un amarre, tallado (ver arriba). X es la cuerda del último paso (la curva
    de la plantilla), que se separa como al asentar un paso (con `separada`, ya viene separada,
    como la relajada de `libre.asentar_o_relajar`); `partes` (N − 1) da la parte de cada tramo, y
    `tensiones`, la que busca cada parte. `tension_inicial` (N,) es la tensión de atado con que
    parte (por omisión, ninguna). Las dos puntas se sostienen de un nodo, como al asentar un paso
    de un amarre, y la cuerda roza.

    Primero la cuerda se asienta con la tensión de partida, como el apretado de antes (la ronda
    0). Con `aceptar(Y, material) -> bool`, esa cuerda y la de cada ronda se remuestrean y se
    comprueban, y el resultado es la última que cumple; si la ronda 0 no cumple, no se sigue (y
    `aceptada` es None), y después de `paciencia` rondas seguidas que no cumplen, se para. Sin
    `aceptar`, es la última ronda. `registro(fila)`, si se da, recibe lo de cada ronda."""
    X0 = np.array(X, float) if separada else separar(X, h, None, solido, quietos=quietos)
    N = len(X0)
    partes = np.asarray(partes, int)
    objetivo = np.asarray(tensiones, float)
    mat = CUERDA_8MM
    T0 = np.zeros(N) if tension_inicial is None else np.asarray(tension_inicial, float)
    var = Varilla(np.full(N - 1, float(h)) / (1 + T0[:-1] / mat.EA), mat,
                  curvatura=Varilla.curvatura_de(X0))
    cortes = np.array([0, N])
    manos = sostener(cortes, N, chicotes=True, nodos=1)
    malla = contacto(X0, cortes, [1.0], solido)
    if malla.margen(X0) <= 0:   # como en `asentar`: la IPC no puede partir de ahí
        from ..libre import TrazadoError
        raise TrazadoError("el motor no puede tallar desde esta cuerda: un par queda dentro de "
                           "la barrera del contacto")
    sis = Sistema([var], malla, fijos=manos.fijos, fuerzas=manos.fuerzas,
                  kappa=rigidez_barrera(max(1.0, float(objetivo.max()) * h)), roce=True)
    # Primero se asienta como el apretado de antes, con la tensión de partida, hasta que deja de
    # moverse: en el trípode, la cuerda de unos pocos pasos todavía tiene un codo que después se
    # va, y las rondas parten de una cuerda quieta.
    x = X0.copy()
    sin_converger = 0
    for _ in range(TALLAR_ASIENTA):
        r = sis.paso(x)
        mov = float(np.max(np.linalg.norm(r.x - x, axis=1)))
        x = r.x
        sin_converger = 0 if r.convergio else sin_converger + 1
        if mov < QUIETO or sin_converger >= MAX_SIN_CONVERGER:
            break
    # Lo que la plantilla traza quieto (`quietos`, como la vuelta de braza del amarre diagonal)
    # no se acorta.
    acortable = np.ones(N - 1, bool)
    if quietos is not None:
        q = np.asarray(quietos, bool)
        acortable &= ~(q[:-1] | q[1:])
    mejor, aceptada, sin, historia, ronda = None, None, 0, [], 0
    if aceptar is not None:
        Y, m = remuestrear_material(x, h)
        if sin_converger >= MAX_SIN_CONVERGER or not aceptar(Y, m):
            return Tallado(np.zeros((0, 3)), np.zeros(0), 0, None, historia)
        mejor, aceptada = (Y, m), 0
    for ronda in range(1, rondas + 1):
        mov = np.inf
        for _ in range(pasos):
            r = sis.paso(x)
            mov = float(np.max(np.linalg.norm(r.x - x, axis=1)))
            x = r.x
            sin_converger = 0 if r.convergio else sin_converger + 1
            if mov < QUIETO or sin_converger >= MAX_SIN_CONVERGER:
                break
        if sin_converger >= MAX_SIN_CONVERGER:
            break    # como al apretar: queda la última ronda que cumplía
        # La tensión media de cada parte; las flojas se acortan, más cuanto más flojas.
        T = mat.EA * (np.linalg.norm(np.diff(x, axis=0), axis=1) / var.l - 1)
        medias = [float(T[partes == k].mean()) if np.any(partes == k) else np.inf
                  for k in range(len(objetivo))]
        acorta = False
        for k, (Tk, Ok) in enumerate(zip(medias, objetivo)):
            en = (partes == k) & acortable
            if not en.any() or Tk >= Ok:
                continue
            d = float(np.clip(TALLAR_ACORTA * (1 - Tk / Ok), TALLAR_ACORTA / 12, TALLAR_ACORTA))
            nuevo = np.maximum(var.l[en] * (1 - d), TALLAR_MIN * h)
            acorta |= bool(np.any(nuevo < var.l[en]))
            var.l[en] = nuevo
        var.k_estirar = mat.EA / var.l
        var.k_doblar = mat.EI / (var.l[:-1] + var.l[1:])
        var.curvatura = Varilla.curvatura_de(x)     # la memoria sigue a la cuerda
        historia.append([round(t, 1) for t in medias])
        cumple = None
        if aceptar is not None:
            Y, m = remuestrear_material(x, h)
            cumple = bool(aceptar(Y, m))
            if cumple:
                mejor, aceptada, sin = (Y, m), ronda, 0
            else:
                sin += 1
        if registro is not None:
            registro({"ronda": ronda, "movimiento": mov, "tensiones": medias, "cumple": cumple})
        if sin > paciencia:
            break    # también si ninguna cumple desde el principio: queda el apretado de antes
        if not acorta and mov < QUIETO:
            break
    if aceptar is None:
        mejor, aceptada = remuestrear_material(x, h), ronda
    if mejor is None:
        return Tallado(np.zeros((0, 3)), np.zeros(0), ronda, None, historia)
    return Tallado(mejor[0], mejor[1], ronda, aceptada, historia)
