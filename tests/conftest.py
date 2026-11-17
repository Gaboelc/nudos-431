import os
import pickle
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from nudos import SPECS
from nudos.construir import construir
from nudos.imprimir import ImpresionError, chrome
from nudos.procesos import en_paralelo
from nudos.spec import ESTADOS, cargar


@pytest.fixture(scope="session")
def con_chrome():
    """Las pruebas que dibujan necesitan Chrome (o NUDOS_CHROME); sin él se saltan."""
    try:
        with chrome():
            pass
    except ImpresionError as e:
        pytest.skip(str(e))


# --- Los nudos de specs/, construidos una sola vez ---------------------------

def modelados() -> list[str]:
    """Los nudos de specs/ en «modelado» o más: los que tienen que construir sin fallas."""
    return sorted(p.stem for p in SPECS.glob("*.yaml")
                  if ESTADOS.index(cargar(p.stem).estado) >= ESTADOS.index("modelado"))


class Modelos:
    """Los modelos de los nudos de specs/, construidos una sola vez para toda la corrida.
    empezar() los construye en hilos, que mandan sus pasos al grupo de procesos
    (nudos/procesos.py), mientras las demás pruebas siguen; modelos[slug] espera el suyo.

    Con pytest-xdist, cada proceso de pruebas tiene su propio Modelos. El primero que llega
    los construye y los deja en la carpeta compartida de la corrida; los demás los leen de
    ahí en vez de construirlos otra vez (compartir())."""

    def __init__(self):
        self._hilos = None
        self._futuros = {}
        self._carpeta = None    # con xdist, la carpeta compartida entre los procesos
        self._construye = True  # con xdist, si este proceso es el que construye
        self._leidos = {}
        self._guardando = None

    def empezar(self, slugs) -> None:
        if not en_paralelo():
            return   # en un solo proceso, cada uno se construye cuando se pide
        if self._hilos is None:
            self._hilos = ThreadPoolExecutor(64)
        # Primero los de plantilla, que tardan más: así terminan antes de que se pidan.
        for slug in sorted(slugs, key=lambda s: cargar(s).plantilla is None):
            if slug not in self._futuros:
                self._futuros[slug] = self._hilos.submit(construir, cargar(slug))

    def compartir(self, carpeta: Path, slugs: list[str]) -> None:
        self._carpeta = carpeta
        try:
            os.close(os.open(carpeta / "modelos.candado", os.O_CREAT | os.O_EXCL))
        except FileExistsError:
            self._construye = False
            return
        self.empezar(slugs)
        self._guardando = threading.Thread(target=self._guardar, args=(slugs,), daemon=True)
        self._guardando.start()

    def _guardar(self, slugs) -> None:
        """Deja cada modelo en la carpeta compartida en cuanto está, para que los demás
        procesos no esperen a todos."""
        pendientes = list(slugs)
        while pendientes:
            listos = [s for s in pendientes if s not in self._futuros or
                      not hasattr(self._futuros[s], "done") or self._futuros[s].done()]
            if not listos:
                time.sleep(0.2)
                continue
            for slug in listos:
                try:
                    dato = ("ok", self._de_aqui(slug))
                except Exception as e:   # el proceso que lo pida dice por qué
                    dato = ("falla", repr(e))
                tmp = self._carpeta / f"{slug}.pickle.tmp"
                tmp.write_bytes(pickle.dumps(dato, pickle.HIGHEST_PROTOCOL))
                os.replace(tmp, self._carpeta / f"{slug}.pickle")
                pendientes.remove(slug)
        (self._carpeta / "modelos.listos").write_text(" ".join(slugs), encoding="utf-8")

    def terminar(self) -> None:
        """El proceso que construye no termina antes de dejar los modelos a los demás."""
        if self._guardando is not None:
            self._guardando.join()

    def _de_aqui(self, slug: str):
        if slug not in self._futuros:
            if self._hilos is None:
                self._futuros[slug] = construir(cargar(slug))
                return self._futuros[slug]
            self.empezar([slug])
        f = self._futuros[slug]
        return f if self._hilos is None else f.result()

    def _leer(self, slug: str):
        if slug not in self._leidos:
            archivo, listos = self._carpeta / f"{slug}.pickle", self._carpeta / "modelos.listos"
            limite = time.monotonic() + 3600
            while not archivo.exists():
                if listos.exists():   # el que construye no lo tenía en su lista
                    return self._de_aqui(slug)
                if time.monotonic() > limite:
                    raise TimeoutError(f"el proceso que construye los modelos no dejó {slug} en una hora")
                time.sleep(0.2)
            self._leidos[slug] = pickle.loads(archivo.read_bytes())
        estado, valor = self._leidos[slug]
        if estado != "ok":
            raise RuntimeError(f"{slug} no se pudo construir: {valor}")
        return valor

    def __getitem__(self, slug: str):
        return self._de_aqui(slug) if self._construye else self._leer(slug)


_MODELOS = Modelos()


@pytest.fixture(scope="session")
def modelos():
    """Los modelos de todos los nudos de specs/ por slug, cada uno construido una sola vez.
    Las pruebas que recorren todos los nudos piden este; las demás, el de su nudo."""
    return _MODELOS


@pytest.fixture(scope="session", autouse=True)
def _construir_al_empezar(request, tmp_path_factory):
    """Al empezar, lanza a la vez los nudos que van a pedir las pruebas elegidas: todos los
    de «modelado» o más si alguna pide «modelos»; si no, solo los de cada modelo_<slug>.
    Con xdist, todos los procesos ven las mismas pruebas y piden los mismos nudos."""
    nombres = {n for item in request.session.items for n in getattr(item, "fixturenames", ())}
    if "modelos" in nombres:
        slugs = modelados()
    else:
        slugs = [s for s in modelados() if f"modelo_{s.replace('-', '_')}" in nombres]
    if os.environ.get("PYTEST_XDIST_WORKER"):
        _MODELOS.compartir(tmp_path_factory.getbasetemp().parent, slugs)
    else:
        _MODELOS.empezar(slugs)
    yield
    _MODELOS.terminar()


@pytest.fixture(scope="session")
def modelo_as_de_guia():
    """El as de guía construido una sola vez para todas las pruebas que lo usan."""
    return _MODELOS["as-de-guia"]


@pytest.fixture(scope="session")
def modelo_ballestrinque():
    """El ballestrinque sobre el poste, construido una sola vez."""
    return _MODELOS["ballestrinque"]


@pytest.fixture(scope="session")
def modelo_vuelta_de_escota():
    """La vuelta de escota, con dos cuerdas, construida una sola vez."""
    return _MODELOS["vuelta-de-escota"]


@pytest.fixture(scope="session")
def modelo_amarre_cuadrado():
    """El amarre cuadrado, la primera plantilla, construido una sola vez."""
    return _MODELOS["amarre-cuadrado"]


@pytest.fixture(scope="session")
def modelo_amarre_diagonal():
    """El amarre diagonal, construido una sola vez."""
    return _MODELOS["amarre-diagonal"]
