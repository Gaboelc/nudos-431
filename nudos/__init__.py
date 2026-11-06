"""Libro de nudos del Grupo 431: de la especificación de cada nudo a sus modelos."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SPECS = RAIZ / "specs"
BUILD = RAIZ / "build"

# Dirección del sitio. Va impresa en los QR, así que no cambia nunca.
URL_BASE = "https://gaboelc.github.io/nudos-431/"
