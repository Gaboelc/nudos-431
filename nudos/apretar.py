"""El nudo terminado apretado (T7c): una geometría aparte, solo para las dos vistas del nudo
terminado, con la cuerda ajustada como queda de verdad. Los pasos no cambian.

Al relajar un paso (nudos/libre.py), cada tramo conserva su largo, así que el último paso
queda flojo. Aquí la cuerda se acorta dentro del nudo, como si se tirara de sus cabos, y
después de cada poco se deshacen los choques. Es el método con que se calculan los nudos
apretados (SONO, «shrink on no overlaps»): ningún tramo atraviesa a otro, así que ningún
cruce cambia. Se parte del último paso ya relajado.

Cada punto de la cuerda pertenece a una de tres partes, según dónde estaba en el último paso:
- el nudo: lo que está a menos de DISTANCIA_NUDO, sobre la mesa, de algún cruce. Es lo
  único que se acorta;
- la cola: cada cuerda después de su último cruce, que es su chicote. No se acorta ni se
  sujeta: conserva su largo y el nudo la arrastra;
- lo sujeto: el resto, como el firme lejos del nudo o la gaza grande del as de guía. Se queda
  donde está, como si lo sostuvieras con las manos. La cuerda que se quita del nudo es la
  que sale por ahí, fuera de la imagen.
Con cuerdas de distinto grosor, la más delgada se ajusta alrededor de las más gruesas, que son
más rígidas y conservan su forma: lo que de ellas está en el nudo queda sujeto.

Se aprieta por rondas. En cada una, la cuerda se acorta (cada punto del nudo se acerca al
medio entre sus vecinos, que es lo que hace una cuerda al tensarla, y no puede estirarse), se
suelta (sin acortar y sin gravedad, para que el nudo recupere el largo que necesita para no
chocar) y se vuelve a muestrear a paso parejo. Al soltar, el nudo no tiene corrección de
largo: si se le impidiera encogerse, la cuerda comprimida se pandearía en dientes de sierra.
Cada punto recuerda dónde estaba en el último paso (su coordenada material), así que su
parte y, sobre un poste, si va sobre él no cambian aunque la cuerda se acorte. Después de
cada ronda la cuerda se comprueba como un paso, y el apretado es la ronda más apretada que
cumple la secuencia y los límites. Si ninguna los cumple, es el último paso tal cual, así que
el apretado nunca agrega fallas.

El nudo por detrás apretado no es el apretado volteado: al voltearlo, la relajación de un
paso (que choca a 1,0 y no a HOLGURA) lo estiraba y apoyaba la gruesa de la vuelta de escota
sobre la delgada con radio 0,83. Es el nudo por detrás de siempre (el último paso volteado y
relajado), apretado igual, con la secuencia invertida.

Un nudo de plantilla no se aprieta: su plantilla ya traza la cuerda tensa.

Con la opción del motor (T15d), el apretado es el modo 2 del motor (nudos/fisica/asentar.py,
`apretar`): el último paso asentado, con las manos de nudos/fisica/manos.py (`para_apretar`)
tirando fuerte. Se comprueba como un paso, y sus fallas sí cuentan: el motor no busca la ronda que
cumple, así que si algo falla, se ve. Sirve con cualquier anfitrión (T15f).
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from .cruces import encima, encontrar_cruces, ocurrencias
from .libre import Reparto, Resultado, _colisiones, _limitar_curva, _resultado
from .spec import Paso, Spec

DISTANCIA_NUDO = 6.0   # diámetros, sobre la mesa, desde algún cruce del último paso
# Mientras se aprieta, dos tramos chocan a 1,12 veces la suma de sus radios. Una cuerda
# que abraza a otra del mismo grosor se dobla con radio 1,0, así que un nudo apretado del
# todo queda al borde del límite de curvatura (0,9). Con esta holgura, las vueltas quedan
# con radio de 0,91 o más: en una cuerda de 8 mm es 1 mm de luz.
HOLGURA = 1.12
RONDAS = 30
ITERACIONES_ACORTAR = 20   # por ronda, acortando
ITERACIONES_SOLTAR = 40    # por ronda, sin acortar ni gravedad
TENSION = 0.25             # cuánto se acerca cada punto del nudo al medio de sus vecinos
GRAVEDAD = 0.003           # cuánto cae por iteración lo que no está sujeto, mientras se acorta
FIJOS = 3                  # los primeros puntos de cada firme no se mueven, como al relajar
CORRECCIONES = 3           # vueltas de curva, choques, mesa y largo por iteración
PASADAS_LARGO = 8          # correcciones de largo en cada una

NUDO, COLA, SUJETO = 0, 1, 2


def apretar(r: Resultado, secuencia, pasadas=None, *, rondas: int = RONDAS, anfitrion=None,
            gravedad: Callable | None = None, buscar: Callable | None = None,
            medir: Callable | None = None, registro: list | None = None) -> Resultado:
    """El último paso `r`, apretado. `secuencia` y `pasadas` son las declaradas del paso.

    Devuelve un Resultado como el de un paso, sin resaltado y con su propio número de puntos
    y su propio h. Si ninguna ronda cumple la secuencia y los límites, devuelve `r`.

    Sobre un anfitrión (nudos/anfitrion.py) se pasa lo mismo que a la relajación y a la
    comprobación de un paso: `anfitrion.empujar(X, libre)` saca la cuerda de él,
    `gravedad(X)` dice qué puntos pueden caer, `buscar(X, h, u)` busca los cruces (`u` es la
    coordenada material de cada punto: dónde estaba en el último paso, a lo largo de la
    polilínea) y `medir(X)` agrega medidas y fallas propias. `registro`, si se da, recibe
    una fila por ronda: (ronda, largo, separación, curvatura, estiramiento, cumple)."""
    rep0 = r.reparto or Reparto.una(len(r.puntos))
    h0 = r.h
    u0 = np.arange(len(r.puntos)) * h0
    if buscar is None:
        cruces0 = encontrar_cruces(r.puntos, h0, rep0.seguido)
    else:
        cruces0, _ = buscar(r.puntos, h0, u0)
    partes0 = _partes(r.puntos, h0, rep0, cruces0)

    X, u, rep, h = r.puntos.copy(), u0.copy(), rep0, h0
    mejor, mejor_largo = r, None
    for ronda in range(1, rondas + 1):
        parte = partes0[np.clip(np.round(u / h0).astype(int), 0, len(partes0) - 1)]
        _ronda(X, h, rep, parte, anfitrion, gravedad)
        X, u, rep, h = _remuestrear(X, u, rep, h)
        hh, uu = h, u
        a = _resultado(r.n, X.copy(), h, secuencia, None,
                       buscar=None if buscar is None else (lambda Y: buscar(Y, hh, uu)),
                       medir=medir, reparto=None if r.reparto is None else rep, pasadas=pasadas)
        cumple = not a.fallas
        if registro is not None:
            m = a.medidas
            registro.append((ronda, m["largo"], m["separacion_min"], m["curvatura_min"],
                             m["estiramiento_max"], cumple))
        # No se para en la primera ronda que falla: la curvatura sube y baja unas centésimas
        # de una ronda a otra.
        if cumple and (mejor_largo is None or a.medidas["largo"] < mejor_largo):
            mejor, mejor_largo = a, a.medidas["largo"]
    return mejor


def apretado(spec: Spec, final: Resultado, reverso: Resultado | None = None,
             rondas: int = RONDAS) -> tuple[Resultado | None, Resultado | None]:
    """El último paso de la especificación, ya construido (`final`), apretado, y el nudo por
    detrás (`reverso`, el último paso volteado), apretado. Sobre un poste no hay reverso: se
    mira el mismo nudo desde el otro lado. Con el destorcedor o la estaca, todo el nudo va
    sobre la mesa y se aprieta como sin anfitrión, con el anfitrión sacando la cuerda de él. En un nudo de
    plantilla, que no se aprieta, los dos son None."""
    if spec.plantilla is not None:
        return None, None
    # Por delante y por detrás no dependen uno del otro: se aprietan a la vez, cada uno en un
    # proceso (nudos/procesos.py).
    from .procesos import ejecutor
    ex = ejecutor(1 if reverso is None else 2)
    f_delante = ex.submit(en_otro_proceso, apretado_delante, spec, final, rondas)
    f_detras = None if reverso is None else ex.submit(en_otro_proceso, apretado_detras, spec,
                                                       reverso, rondas)
    return (de_otro_proceso(f_delante.result(), final),
            None if f_detras is None else de_otro_proceso(f_detras.result(), reverso))


def en_otro_proceso(fn, spec: Spec, base: Resultado | None, *args):
    """fn(spec, base, *args), para hacerlo en otro proceso. Si fn devuelve `base` tal cual
    (no se pudo apretar), lo dice en vez de mandarlo: de vuelta llegaría una copia, y quien
    lo usa distingue «es el mismo» con `is`. de_otro_proceso() lo deshace."""
    r = fn(spec, base, *args)
    return (True, None) if r is base and r is not None else (False, r)


def de_otro_proceso(respuesta, base):
    mismo, r = respuesta
    return base if mismo else r


def apretado_delante(spec: Spec, final: Resultado, rondas: int = RONDAS) -> Resultado:
    """El nudo terminado apretado, por delante (lo primero de apretado())."""
    paso: Paso = spec.pasos[-1]
    r = _con_motor(spec, paso, final, paso.secuencia)
    if r is not None:
        return r
    if spec.anfitrion is not None and not spec.anfitrion.en_la_mesa:
        from .anfitrion import apretar_paso
        return apretar_paso(paso, spec.anfitrion, final, rondas)
    return apretar(final, paso.secuencia, paso.pasadas, rondas=rondas, **_mesa(spec, paso))


def apretado_detras(spec: Spec, reverso: Resultado | None, rondas: int = RONDAS) -> Resultado | None:
    """El nudo terminado apretado, por detrás (lo segundo de apretado()). Sobre un poste, o
    sin reverso, None."""
    paso: Paso = spec.pasos[-1]
    if reverso is None or (spec.anfitrion is not None and not spec.anfitrion.en_la_mesa):
        return None
    r = _con_motor(spec, paso, reverso, invertida(paso.secuencia))
    if r is not None:
        return r
    return apretar(reverso, invertida(paso.secuencia), paso.pasadas, rondas=rondas,
                   **_mesa(spec, paso))


def _con_motor(spec: Spec, paso: Paso, base: Resultado, secuencia,
               trayectoria: list | None = None) -> Resultado | None:
    """`base` apretado con el motor, si está la opción; si no, None. Con `trayectoria`, se le
    agrega la cuerda de cada paso del motor (el video de T18)."""
    from .fisica import usar_motor
    if not usar_motor():
        return None
    from .fisica.asentar import apretar as apretar_motor
    from .libre import LIMITES_MOTOR
    solido = buscar = medir = None
    a = spec.anfitrion
    if a is not None and a.en_la_mesa:
        m = _mesa(spec, paso)
        solido, medir = m["anfitrion"], m["medir"]
    elif a is not None:
        from .anfitrion import _buscar, _curva, _medir, sobre_superficie
        solido = sobre_superficie(a)
        X, h, _, sobre = _curva(paso, solido)
        if len(X) != len(base.puntos):
            return None

        def buscar(Y):
            return _buscar(Y, base.h, sobre, solido)
        medir = _medir(paso.n, solido)

    def comprobar(Y):
        return _resultado(base.n, Y, base.h, secuencia, None, buscar=buscar, medir=medir,
                          reparto=base.reparto, pasadas=paso.pasadas, limites=LIMITES_MOTOR)

    # Apretado del todo, un nudo se para sobre la mesa y, visto desde arriba, puede mostrar
    # otro diagrama: queda lo más apretado que todavía se ve como en la ficha (la secuencia
    # declarada y los límites), como en apretar().
    r = apretar_motor(base.puntos, base.reparto, solido, base.cruces.values(),
                      aceptar=lambda Y: not comprobar(Y).fallas, trayectoria=trayectoria)
    if trayectoria is not None:
        del trayectoria[r.aceptado or 0:]
    return base if r.aceptado == 0 else comprobar(r.X)


def _mesa(spec: Spec, paso: Paso) -> dict:
    if spec.anfitrion is None:
        return {}
    from .anfitrion import en_la_mesa
    return en_la_mesa(spec.anfitrion, paso.n)


def invertida(secuencia) -> tuple[str, ...]:
    """La secuencia con todos los cruces al revés, como queda al voltear el nudo."""
    return tuple(t[:-1] + ("U" if encima(t) else "O") for t in secuencia)


def _partes(X, h, rep: Reparto, cruces) -> np.ndarray:
    """La parte (NUDO, COLA o SUJETO) de cada punto del último paso. Lo que las cuerdas más
    gruesas tienen en el nudo queda sujeto: conservan su forma y se ajusta la más delgada."""
    s_cruces = np.array([s for s, _, _ in ocurrencias(cruces)])
    xy = np.array([c.xy for c in cruces]).reshape(-1, 2)
    if len(xy):
        cerca = np.linalg.norm(X[:, None, :2] - xy[None, :, :], axis=2).min(axis=1) <= DISTANCIA_NUDO
    else:
        cerca = np.zeros(len(X), bool)
    s = np.arange(len(X)) * h
    parte = np.full(len(X), SUJETO)
    for a, b in rep.tramos:
        en = s_cruces[(s_cruces >= a * h) & (s_cruces <= b * h)]
        if not len(en):
            continue   # una cuerda sin cruces queda sujeta entera
        k = np.arange(a, b + 1)
        cola = s[k] > en.max()
        parte[k[cola]] = COLA
        if rep.grosor[a] <= rep.grosor.min():
            parte[k[~cola & cerca[k]]] = NUDO
    return parte


def _ronda(X, h, rep: Reparto, parte, anfitrion, gravedad) -> None:
    """Una ronda sobre X, en su lugar: se acorta el nudo y después se suelta."""
    N = len(X)
    nudo, sujeto = parte == NUDO, parte == SUJETO
    libre = np.ones(N, bool)
    for i in rep.inicios:
        libre[i:i + FIJOS] = False
    salto, radio, seguido, interior = rep.salto(h), rep.radio, rep.seguido, rep.interior
    tensa = (nudo & interior & libre)[1:-1, None]
    nudo_seg = nudo[:-1] | nudo[1:]
    agarre = sujeto & libre
    ancla = X[agarre, :2].copy()
    for it in range(ITERACIONES_ACORTAR + ITERACIONES_SOLTAR):
        acorta = it < ITERACIONES_ACORTAR
        if acorta:
            X[1:-1] += TENSION * (X[:-2] + X[2:] - 2 * X[1:-1]) * tensa
            cae = libre & ~sujeto
            if gravedad is not None:
                cae &= gravedad(X)
            X[cae, 2] -= GRAVEDAD
        X[agarre, :2] = ancla
        for _ in range(CORRECCIONES):
            _limitar_curva(X, h, libre, rmin=1.1, ganancia=0.35, grosor=rep.grosor,
                           interior=interior)
            _colisiones(X, salto, libre, rep, radio * HOLGURA)
            X[:, 2] = np.maximum(X[:, 2], radio)
            if anfitrion is not None:
                anfitrion.empujar(X, libre)
            _largos(X, h, libre, nudo_seg, seguido, PASADAS_LARGO, acorta)


def _largos(X, h, libre, nudo_seg, seguido, pasadas, acorta) -> None:
    """Como la corrección de largo de la relajación (Gauss-Seidel rojo-negro), pero en el
    nudo solo impide que la cuerda se estire mientras se acorta, y mientras se suelta no
    corrige nada: ahí la cuerda recupera el largo que necesita para no chocar. Fuera del nudo,
    cada tramo conserva su largo."""
    N = len(X)
    for _ in range(pasadas):
        for paridad in (0, 1):
            i = np.arange(paridad, N - 1, 2)
            i = i[seguido[i] & (acorta | ~nudo_seg[i])]
            seg = X[i + 1] - X[i]
            L = np.linalg.norm(seg, axis=1)
            exceso = L - h
            exceso = np.where(nudo_seg[i], np.maximum(exceso, 0.0), exceso)
            c = (exceso / np.maximum(L, 1e-9))[:, None] * seg
            fa, fb = libre[i], libre[i + 1]
            wa = np.where(fa & fb, 0.5, np.where(fa, 1.0, 0.0))
            wb = np.where(fa & fb, 0.5, np.where(fb, 1.0, 0.0))
            X[i] += wa[:, None] * c
            X[i + 1] -= wb[:, None] * c


def _remuestrear(X, u, rep: Reparto, h):
    """Cada cuerda otra vez a paso parejo, el mismo para todas, como al construir un paso
    (libre._curva): ninguna cambia de largo en más de medio tramo y la posición a lo largo de
    la polilínea sigue siendo índice × h. Cada punto nuevo lleva su coordenada material."""
    partes = []
    for a, b in rep.tramos:
        Xi = X[a:b + 1]
        S = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(Xi, axis=0), axis=1))])
        partes.append((Xi, u[a:b + 1], S))
    tramos = [max(1, int(round(S[-1] / h))) for _, _, S in partes]
    hn = sum(S[-1] for _, _, S in partes) / sum(tramos)
    Xs, us, cs = [], [], []
    for k, ((Xi, ui, S), n) in enumerate(zip(partes, tramos)):
        sg = np.linspace(0.0, S[-1], n + 1)
        Xs.append(np.stack([np.interp(sg, S, Xi[:, j]) for j in range(3)], axis=1))
        us.append(np.interp(sg, S, ui))
        cs.append(np.full(n + 1, k))
    cuerda = np.concatenate(cs)
    grosor = np.array([float(rep.grosor[a]) for a, _ in rep.tramos])[cuerda]
    return np.vstack(Xs), np.concatenate(us), Reparto(cuerda, grosor, rep.nombres), hn
