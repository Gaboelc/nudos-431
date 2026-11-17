"""Procesos para construir: cada paso de un nudo se relaja en un núcleo propio.

Los pasos de un nudo no dependen unos de otros, así que se construyen a la vez en procesos
aparte (en Windows, los procesos arrancan con spawn e importan nudos de nuevo). Cada uno hace
exactamente las mismas cuentas que en un solo proceso: los resultados son idénticos byte a
byte, solo llegan antes.

NUDOS_PROCESOS dice cuántos procesos usar; con NUDOS_PROCESOS=1 todo se construye en este
proceso, uno detrás de otro, como antes. Por omisión, uno por hilo de la computadora.

Los procesos del grupo arrancan con OPENBLAS_NUM_THREADS=1. Sin eso, numpy reserva al
importarse los búferes de OpenBLAS para todos sus hilos: 1,5 GB de memoria comprometida por
proceso, y 28 procesos agotan la de la computadora. La física no hace cuentas grandes de
álgebra lineal, así que con un hilo da lo mismo.
"""
from __future__ import annotations

import multiprocessing
import multiprocessing.context
import os
import sys
import threading
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor

_ejecutores: dict[int, ProcessPoolExecutor] = {}   # uno por tamaño; ninguno se cierra a medias
_candado = threading.Lock()
_en_trabajador = False   # True dentro de un proceso del grupo: ahí no se abre otro grupo


def cuantos() -> int:
    """Cuántos procesos usar: NUDOS_PROCESOS o, si no está, los hilos de la computadora."""
    valor = os.environ.get("NUDOS_PROCESOS", "").strip()
    if valor:
        try:
            return max(1, int(valor))
        except ValueError:
            raise ValueError(f"NUDOS_PROCESOS tiene que ser un número entero, no «{valor}».") from None
    return os.cpu_count() or 1


class _EnLinea:
    """Un ejecutor que hace cada tarea en el acto, en este proceso."""

    def submit(self, fn, /, *args, **kwargs) -> Future:
        f: Future = Future()
        try:
            f.set_result(fn(*args, **kwargs))
        except Exception as e:   # se vuelve a lanzar en f.result(), como desde un proceso
            f.set_exception(e)
        return f


EN_LINEA = _EnLinea()


class _ProcesoDeUnHilo(multiprocessing.context.SpawnProcess):
    """Un proceso que arranca con OPENBLAS_NUM_THREADS=1. El proceso hijo copia el entorno
    al arrancar, así que se pone solo mientras arranca y después vuelve a lo que era."""

    def start(self):
        with _candado_entorno:
            antes = os.environ.get("OPENBLAS_NUM_THREADS")
            os.environ["OPENBLAS_NUM_THREADS"] = "1"
            try:
                super().start()
            finally:
                if antes is None:
                    del os.environ["OPENBLAS_NUM_THREADS"]
                else:
                    os.environ["OPENBLAS_NUM_THREADS"] = antes


class _Contexto(multiprocessing.context.SpawnContext):
    Process = _ProcesoDeUnHilo


_candado_entorno = threading.Lock()


def _marcar() -> None:
    global _en_trabajador
    _en_trabajador = True


def en_paralelo() -> bool:
    """Si se pueden abrir procesos desde aquí: no con NUDOS_PROCESOS=1, ni dentro de un proceso
    del grupo o de otro grupo de multiprocessing (sus procesos no pueden tener hijos), ni desde
    un programa leído de stdin, que los procesos nuevos no pueden volver a importar."""
    archivo = getattr(sys.modules.get("__main__"), "__file__", None)
    return (cuantos() > 1 and not _en_trabajador
            and not multiprocessing.current_process().daemon
            and (archivo is None or os.path.exists(archivo)))


def ejecutor(tareas: int = 2):
    """El grupo de procesos, compartido por todo el programa, o EN_LINEA si no conviene abrirlo:
    con una sola tarea, arrancar los procesos tarda más que hacerla aquí. Si NUDOS_PROCESOS
    cambia, se abre otro grupo y el anterior sigue para lo que ya tenía."""
    if tareas < 2 or not en_paralelo():
        return EN_LINEA
    n = cuantos()
    with _candado:
        if n not in _ejecutores:
            _ejecutores[n] = ProcessPoolExecutor(n, mp_context=_Contexto(), initializer=_marcar)
        return _ejecutores[n]


def mapa(fn, argumentos: list[tuple]) -> list[Future]:
    """Lanza fn(*a) para cada a de `argumentos` y devuelve sus futuros, en el mismo orden."""
    ex = ejecutor(len(argumentos))
    return [ex.submit(fn, *a) for a in argumentos]


def construir_varios(specs) -> list:
    """Construye varios nudos a la vez y devuelve sus modelos en el mismo orden. Cada nudo se
    arma en un hilo de este proceso; sus pasos van todos al mismo grupo de procesos."""
    from .construir import construir
    specs = list(specs)
    if len(specs) < 2 or not en_paralelo():
        return [construir(s) for s in specs]
    with ThreadPoolExecutor(len(specs)) as hilos:
        return list(hilos.map(construir, specs))
