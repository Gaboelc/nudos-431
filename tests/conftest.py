import pytest

from nudos.construir import construir
from nudos.imprimir import ImpresionError, chrome
from nudos.spec import cargar


@pytest.fixture(scope="session")
def con_chrome():
    """Las pruebas que dibujan necesitan Chrome (o NUDOS_CHROME); sin él se saltan."""
    try:
        with chrome():
            pass
    except ImpresionError as e:
        pytest.skip(str(e))


@pytest.fixture(scope="session")
def modelo_as_de_guia():
    """El as de guía construido una sola vez para todas las pruebas que lo usan."""
    return construir(cargar("as-de-guia"))


@pytest.fixture(scope="session")
def modelo_ballestrinque():
    """El ballestrinque sobre el poste, construido una sola vez."""
    return construir(cargar("ballestrinque"))


@pytest.fixture(scope="session")
def modelo_vuelta_de_escota():
    """La vuelta de escota, con dos cuerdas, construida una sola vez."""
    return construir(cargar("vuelta-de-escota"))
