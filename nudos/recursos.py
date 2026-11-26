"""Los recursos de terceros del render (T20): los HDRI y las texturas que se bajan a mano, con
permiso de Gabriel, y viven fuera de git.

config/recursos.yaml dice de dónde salió cada uno, su licencia y su huella. Los archivos están en
recursos/ de la carpeta del libro o en NUDOS_RECURSOS (desde un worktree, la de A:).
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml

from . import RAIZ

REGISTRO = RAIZ / "config" / "recursos.yaml"


class RecursoError(Exception):
    """Falta un recurso o no es el que dice el registro."""


def carpeta() -> Path:
    return Path(os.environ.get("NUDOS_RECURSOS") or RAIZ / "recursos")


def registro() -> dict:
    return yaml.safe_load(REGISTRO.read_text(encoding="utf-8")) or {}


def recurso(nombre: str, comprobar: bool = False) -> Path:
    """La ruta de un recurso del registro. Falla si no está o si su tamaño (y, con `comprobar`,
    su sha256) no es el del registro."""
    datos = registro().get(nombre)
    if datos is None:
        raise RecursoError(f"{nombre} no está en {REGISTRO.name}")
    ruta = carpeta() / nombre
    if not ruta.exists():
        raise RecursoError(f"Falta {ruta}: bájalo de {datos['url']} ({datos['licencia']}, "
                           f"{datos['bytes'] / 1e6:.1f} MB) o define NUDOS_RECURSOS.")
    if ruta.stat().st_size != datos["bytes"]:
        raise RecursoError(f"{ruta} no mide {datos['bytes']} bytes, como dice el registro.")
    if comprobar and hashlib.sha256(ruta.read_bytes()).hexdigest() != datos["sha256"]:
        raise RecursoError(f"{ruta} no tiene la huella del registro.")
    return ruta
