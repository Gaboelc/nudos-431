"""El motor de física de la cuerda (T15, fase 5 del plan).

La cuerda es una varilla elástica discreta y su contacto es el de IPC (Incremental Potential
Contact), con `ipctk` (D11). Las unidades son diámetros de cuerda para las longitudes y
newtons para las fuerzas.

- `contacto`: la malla de contacto de `ipctk` (las cuerdas, los anfitriones y la mesa), la
  distancia mínima, el paso sin atravesarse (CCD), la barrera y el roce.
- `materiales`: los parámetros de cada cuerda (`CUERDA_8MM`).
- `varilla`: la energía de la cuerda sin contacto (estiramiento, flexión y peso), con su
  gradiente y su Hessiano disperso, y el marco material sin torsión.
- `integrador`: Newton con búsqueda en línea y nodos fijos, y `Sistema.paso`, el paso de la
  cuerda con su contacto (dinámico o cuasiestático).
- `manos`: las condiciones de borde, qué se sostiene y de qué se tira (T15d).
- `asentar`: los modos de T15d, asentar un paso y apretar el terminado, que `construir` usa
  con la opción del motor (`usar_motor`).
"""
import os


def usar_motor() -> bool:
    """Si `construir` usa el motor (T15d): la opción `--motor`, que pone NUDOS_MOTOR=1. Se lee
    en cada llamada, así que los procesos de nudos/procesos.py la heredan. Está aquí y no en
    `asentar` para no cargar ipctk cuando no se usa."""
    return os.environ.get("NUDOS_MOTOR", "") == "1"
