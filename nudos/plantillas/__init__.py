"""Plantillas: nudos que se generan a partir de unas pocas medidas, como los amarres.

Un nudo de plantilla no lleva segmentos, trazado ni secuencia. Cada paso dice con
`hasta` hasta dónde llega, y la plantilla calcula la cuerda (docs/formato-spec.md).

Cada plantilla es una clase con:
- `leer(datos, falla)`: lee y valida sus medidas desde el mapa `plantilla` del YAML;
- `ANFITRION`: el tipo de anfitrión sobre el que se ata;
- `hitos()`: los valores que acepta `hasta`, cada uno con su posición en la cuerda;
- `VARIANTES`: los errores comunes que sabe construir con sus medidas, cada uno con el
  primer hito desde el que se ve;
- `medidas()`: las palabras que reemplazan `{vueltas}` y las demás en el texto;
- `CON_FIRME`: los hitos en que la cuerda tiene firme, que en las imágenes llevan «Firme»
  y «Chicote»; en los demás se mueve la parte larga, y solo llevan «Chicote», en su punta
  (nudos/exportar.py).
"""
from .amarre import AmarreCuadrado
from .cabeza_turco import CabezaDeTurco

TIPOS = {"amarre-cuadrado": AmarreCuadrado, "cabeza-de-turco": CabezaDeTurco}
