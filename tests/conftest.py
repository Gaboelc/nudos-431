import pytest

from nudos.construir import construir
from nudos.spec import cargar


@pytest.fixture(scope="session")
def modelo_as_de_guia():
    """El as de guía construido una sola vez para todas las pruebas que lo usan."""
    return construir(cargar("as-de-guia"))


@pytest.fixture(scope="session")
def modelo_ballestrinque():
    """El ballestrinque sobre el poste, construido una sola vez."""
    return construir(cargar("ballestrinque"))
