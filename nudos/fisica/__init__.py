"""El motor de física de la cuerda (T15, fase 5 del plan).

La cuerda es una varilla elástica discreta y su contacto es el de IPC (Incremental Potential
Contact), con `ipctk` (D11). Las unidades son diámetros de cuerda para las longitudes y
newtons para las fuerzas.

- `contacto`: la malla de contacto de `ipctk` (la cuerda, los anfitriones y la mesa), la
  distancia mínima y el paso sin atravesarse (CCD).
- `materiales`: los parámetros de cada cuerda (`CUERDA_8MM`).
- `varilla`: la energía de la cuerda sin contacto (estiramiento, flexión y peso), con su
  gradiente y su Hessiano disperso, y el marco material sin torsión.
- `integrador`: Newton con búsqueda en línea y nodos fijos.
"""
