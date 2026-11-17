from concurrent.futures import ThreadPoolExecutor

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
    (nudos/procesos.py), mientras las demás pruebas siguen; modelos[slug] espera el suyo."""

    def __init__(self):
        self._hilos = ThreadPoolExecutor(64) if en_paralelo() else None
        self._futuros = {}

    def empezar(self, slugs) -> None:
        if self._hilos is None:
            return
        # Primero los de plantilla, que tardan más: así terminan antes de que se pidan.
        for slug in sorted(slugs, key=lambda s: cargar(s).plantilla is None):
            if slug not in self._futuros:
                self._futuros[slug] = self._hilos.submit(construir, cargar(slug))

    def __getitem__(self, slug: str):
        if slug not in self._futuros:
            if self._hilos is None:
                self._futuros[slug] = construir(cargar(slug))
                return self._futuros[slug]
            self.empezar([slug])
        f = self._futuros[slug]
        return f if self._hilos is None else f.result()


_MODELOS = Modelos()


@pytest.fixture(scope="session")
def modelos():
    """Los modelos de todos los nudos de specs/ por slug, cada uno construido una sola vez.
    Las pruebas que recorren todos los nudos piden este; las demás, el de su nudo."""
    return _MODELOS


@pytest.fixture(scope="session", autouse=True)
def _construir_al_empezar(request):
    """Al empezar, lanza a la vez los nudos que van a pedir las pruebas elegidas: todos los
    de «modelado» o más si alguna pide «modelos»; si no, solo los de cada modelo_<slug>."""
    nombres = {n for item in request.session.items for n in getattr(item, "fixturenames", ())}
    if "modelos" in nombres:
        _MODELOS.empezar(modelados())
    else:
        _MODELOS.empezar([s for s in modelados() if f"modelo_{s.replace('-', '_')}" in nombres])


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
