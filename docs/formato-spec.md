# Formato de especificación de nudo (v0)

Cada nudo es un archivo `specs/<slug>.yaml`. Es la fuente de verdad: los modelos 3D, las imágenes y la ficha se generan desde aquí. El formato puede cambiar hasta el Punto de control B del plan; ahí se congela como v1, y desde entonces cualquier cambio lleva un script de migración.

El ejemplo completo es `specs/as-de-guia.yaml`.

## Unidades y ejes

- El diámetro de la cuerda vale 1. Todas las medidas están en diámetros.
- x crece hacia la derecha, y hacia el fondo de la mesa (lejos de quien ata) y z hacia arriba desde la mesa.
- La cuerda se recorre desde el firme hasta el chicote. Los primeros puntos del firme quedan fijos.

## Campos

| Campo | Obligatorio | Qué es |
|---|---|---|
| `slug` | sí | Identificador permanente, con minúsculas, números y guiones. Es igual al nombre del archivo. Cuando su QR se imprime, ya no cambia. |
| `nombre` | sí | Nombre del nudo en la ficha. |
| `familia` | sí | Familia del índice: De tope, De unión, Gazas, De sujeción, Autoblocantes, Corredizos, De ligadura, Amarres… |
| `abok` | no | Número en *The Ashley Book of Knots*. |
| `encuadre` | no | Zona de la mesa que se muestra, como `x: [mín, máx]` e `y: [mín, máx]`. Si falta, se calcula con todos los pasos. |
| `segmentos` | sí | Tramos de cuerda con nombre. Cada uno es una lista de puntos `[x, y]`. |
| `pasos` | sí | Lista de pasos en orden. |

Los campos desconocidos producen un error, así que un error de tipeo se detecta al cargar.

## Segmentos y referencias

Un segmento es una lista de puntos de control por donde pasa la curva. Cada paso encadena segmentos, así que un tramo que no cambia entre pasos se define una sola vez.

| Referencia | Significa | Dónde se usa |
|---|---|---|
| `gaza` | El segmento completo | trazado |
| `gaza[1:]`, `gaza[:-2]` | Un tramo, con la notación de Python | trazado |
| `gaza[0]`, `gaza[-1]` | Un punto del segmento | resaltar |
| `fin` | El último punto del paso | resaltar |

Los índices se cuentan sobre el segmento tal como está definido. Dos puntos seguidos no pueden quedar a menos de 0,05 diámetros.

## Pasos

| Campo | Qué es |
|---|---|
| `titulo` | Título corto, en imperativo y tuteo. |
| `texto` | Instrucción del paso, en tuteo y con texto propio. |
| `trazado` | Segmentos o tramos en el orden de la cuerda. Cada segmento aparece una sola vez. |
| `secuencia` | La secuencia de cruces (ver abajo). Si el paso no tiene cruces, se escribe `""`. |
| `resaltar` | Opcional. Con `desde` y `hasta` marca el tramo que se mueve en este paso. |

## Secuencia de cruces

Para escribirla, recorre la cuerda desde el firme y anota cada vez que pasa por un cruce: la etiqueta del cruce más `O` si pasa por encima o `U` si pasa por debajo. Por ejemplo, en el paso 4 del as de guía la secuencia es `1U 2O 3U 1O 2U 3O`.

Reglas:

- En un paso, cada etiqueta aparece dos veces, una con `O` y otra con `U`.
- Cada etiqueta nombra un solo cruce en todo el nudo. Un cruce que sigue en el paso siguiente conserva su etiqueta.
- Un cruce no cambia de encima a debajo entre pasos. Si cambia, es otro cruce y lleva otra etiqueta.
- El trazado tiene que formar exactamente esos cruces, en ese orden.

## Qué se comprueba al construir

1. La especificación cumple este formato.
2. **Consistencia entre pasos:** cada cruce conserva su encima/debajo en todos los pasos donde aparece. Así se detecta un cruce invertido en un solo paso.
3. En cada paso, después de relajar la cuerda:
   - la secuencia de cruces es la declarada;
   - ningún tramo queda a menos de 0,97 diámetros de otro;
   - el radio de curvatura no baja de 0,9 diámetros;
   - la cuerda no se estira más de 2 %.
4. Un cruce con la misma etiqueta no aparece a más de 2,5 diámetros de donde estaba en el paso anterior. Es una heurística para detectar una etiqueta reutilizada para otro cruce.

**Lo que no se comprueba es si la secuencia corresponde al nudo correcto.** Un cruce mal leído que se repite igual en todos los pasos pasa todas las pruebas. Para eso está el filtro 1: atar cada paso con cuerda real antes de publicar.

## Pendiente para versiones siguientes

- Varias cuerdas con grosor y color por rol (T6).
- Objetos anfitriones como poste, argolla o estaca, y cruces sobre su superficie (T5).
- Error común y vistas finales (T3).
- Nudos que se voltean sobre la mesa: voltear invierte todos los cruces, y hoy eso obligaría a usar etiquetas nuevas.
