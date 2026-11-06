"""El error común de un nudo y el nudo terminado visto por detrás.

El error es una variante de un paso: el mismo trazado con algunos cruces al revés.
No es un paso del nudo, así que es el único lugar donde un cruce cambia de encima a
debajo. Se construye y se comprueba igual que un paso, y además se verifica que su
secuencia difiere de la del paso correcto exactamente en los cruces declarados.
"""
from __future__ import annotations

from dataclasses import replace

from .cruces import etiqueta, numerada
from .libre import Resultado, TrazadoError, construir_paso, voltear
from .spec import Spec


def invertir(secuencia, etiquetas) -> tuple[str, ...]:
    """La secuencia con los cruces de `etiquetas` al revés."""
    cambio = {"O": "U", "U": "O"}
    quitar = set(etiquetas)
    return tuple(t[:-1] + cambio[t[-1]] if etiqueta(t) in quitar else t for t in secuencia)


def cruces_distintos(a, b) -> set[str]:
    """Etiquetas de los cruces donde dos secuencias del mismo trazado no coinciden."""
    if len(a) != len(b) or [etiqueta(t) for t in a] != [etiqueta(t) for t in b]:
        raise ValueError("las secuencias no recorren los mismos cruces en el mismo orden")
    return {etiqueta(x) for x, y in zip(a, b) if x != y}


def construir_error(spec: Spec, correcto: Resultado | None) -> tuple[Resultado | None, list[str]]:
    """Construye el error común y lo compara con el paso correcto ya construido.

    Las dos secuencias que se comparan son las obtenidas después de relajar, así que
    la comprobación cubre la geometría de los dos modelos, no solo lo declarado."""
    e = spec.error
    if e is None:
        return None, []
    paso = spec.pasos[e.paso - 1]
    try:
        r = construir_paso(replace(paso, secuencia=invertir(paso.secuencia, e.invierte)))
    except TrazadoError as err:
        return None, [f"Error común: {err}"]
    fallas = [f"Error común: {f}" for f in r.fallas]
    if correcto is None:
        return r, fallas
    # Las obtenidas vienen numeradas en orden de aparición; se traducen las etiquetas declaradas.
    numeros = dict(zip((etiqueta(t) for t in paso.secuencia),
                       (etiqueta(t) for t in numerada(paso.secuencia))))
    declarados = {numeros[x] for x in e.invierte}
    try:
        distintos = cruces_distintos(correcto.secuencia, r.secuencia)
    except ValueError:
        fallas.append(f"Error común: no recorre los cruces del paso {e.paso} en el mismo orden.")
        return r, fallas
    if distintos != declarados:
        fallas.append(
            f"Error común: difiere del paso {e.paso} en los cruces {_lista(distintos)} "
            f"y debía diferir en {_lista(declarados)}.")
    return r, fallas


def construir_reverso(spec: Spec, final: Resultado) -> tuple[Resultado, list[str]]:
    """El último paso volteado, para mostrar el nudo terminado por detrás."""
    r = voltear(final, spec.pasos[-1].secuencia)
    return r, [f"Reverso del nudo terminado: {f}" for f in r.fallas]


def _lista(etiquetas) -> str:
    return ", ".join(sorted(etiquetas, key=int)) or "ninguno"
