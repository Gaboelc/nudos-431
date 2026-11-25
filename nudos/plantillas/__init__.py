"""Plantillas: nudos que se generan a partir de unas pocas medidas, como los amarres.

Un nudo de plantilla no lleva segmentos, trazado ni secuencia. Cada paso dice con
`hasta` hasta dónde llega, y la plantilla calcula la cuerda (docs/formato-spec.md).

Cada plantilla es una clase con:
- `leer(datos, falla)`: lee y valida sus medidas desde el mapa `plantilla` del YAML;
- `ANFITRION`: el tipo de anfitrión sobre el que se ata y, sobre los palos, `PALOS`, cuántos;
  None si va libre sobre la mesa, como el adujado;
- `hitos()`: los valores que acepta `hasta`, cada uno con su posición en la cuerda;
- `VARIANTES`: los errores comunes que sabe construir con sus medidas, cada uno con el
  primer hito desde el que se ve;
- `medidas()`: las palabras que reemplazan `{vueltas}` y las demás en el texto;
- `CAPAS_DEBAJO` (opcional, en los amarres): cuántas capas de cuerda pasan bajo el palo
  de abajo de la cruz, que fija su altura (Anfitrion.capas);
- `CON_FIRME`: los hitos en que la cuerda tiene firme, que en las imágenes llevan «Firme»
  y «Chicote»; en los demás se mueve la parte larga, y solo llevan «Chicote», en su punta
  (nudos/exportar.py).

Y, si los necesita:
- `SIN_NOMBRES`: los hitos que no llevan ningún nombre, como el refuerzo de cabo con las
  puntas cortadas;
- `comprobar(anfitrion, falla)`: lo que la plantilla pide de las medidas del anfitrión, como
  que el refuerzo quepa en el cabo;
- `nombres(hito)`: los nombres de la imagen de cada hito, cuando la cuerda va del firme al
  chicote, como en el puño de mono; sin él, los dice CON_FIRME;
- `voltear(resultado)`: el nudo terminado por detrás, cuando la plantilla va sin anfitrión y no
  se voltea como un nudo libre, como el puño de mono;
- con el motor (T15f), `TENSION`: la tensión de atado de todos sus pasos, si no es la del
  paso («ajustada», y «apretada» en el terminado apretado), y `APRETAR = False` si el nudo
  terminado no se aprieta. El adujado va «suelto» y no se aprieta.

`ANFITRION = None` quiere decir que la plantilla va sin anfitrión, como el puño de mono: la
especificación no lleva `anfitrion`.
"""
from .adujado import Adujado
from .amarre import AmarreCuadrado
from .amarre_diagonal import AmarreDiagonal
from .cabeza_turco import CabezaDeTurco
from .paralelos import AmarreRedondo, AmarreTripode
from .puno import PunoDeMono
from .refuerzo import RefuerzoDeCabo

TIPOS = {"adujado": Adujado, "amarre-cuadrado": AmarreCuadrado, "amarre-diagonal": AmarreDiagonal,
         "amarre-redondo": AmarreRedondo, "amarre-tripode": AmarreTripode,
         "cabeza-de-turco": CabezaDeTurco, "puno-de-mono": PunoDeMono,
         "refuerzo-de-cabo": RefuerzoDeCabo}
