# Formato de especificación de nudo (v0)

Cada nudo es un archivo `specs/<slug>.yaml`. Es la fuente de verdad: los modelos 3D, las imágenes y la ficha se generan desde aquí. El formato puede cambiar hasta el Punto de control B del plan; ahí se congela como v1, y desde entonces cualquier cambio lleva un script de migración.

El ejemplo completo es `specs/as-de-guia.yaml`.

## Unidades y ejes

- El diámetro de la cuerda vale 1. Todas las medidas están en diámetros. En un nudo de varias cuerdas, 1 es el diámetro de la cuerda de siempre y cada cuerda declara su grosor.
- x crece hacia la derecha, y hacia el fondo de la mesa (lejos de quien ata) y z hacia arriba desde la mesa.
- La cuerda se recorre desde el firme hasta el chicote. Los primeros puntos del firme quedan fijos. Con varias cuerdas, cada una se recorre desde su firme.

## Campos

| Campo | Obligatorio | Qué es |
|---|---|---|
| `slug` | sí | Identificador permanente, con minúsculas, números y guiones. Es igual al nombre del archivo. Cuando su QR se imprime, ya no cambia. |
| `nombre` | sí | Nombre del nudo en la ficha. |
| `otros_nombres` | no | Lista de otros nombres, cuando una sección lo llama distinto. La ficha los pone bajo el nombre. |
| `familia` | sí | Familia del índice: De tope, De unión, Gazas, De sujeción, Autoblocantes, Corredizos, De ligadura, Amarres… |
| `abok` | no | Número en *The Ashley Book of Knots*. |
| `usos` | para la ficha | Para qué sirve. |
| `materiales` | para la ficha | Qué cuerda y qué objetos hacen falta. |
| `verificacion` | para la ficha | Lista de criterios para revisar el nudo terminado. Cada uno se tiene que poder comprobar mirando o tirando del nudo. |
| `seguridad` | no | Solo cuando aplica. Si el nudo tiene usos con personas, sigue la postura de seguridad del libro (D1 del plan). |
| `encuadre` | no | Zona de la mesa que se muestra, como `x: [mín, máx]` e `y: [mín, máx]`. Si falta, se calcula con todos los pasos. |
| `anfitrion` | no | El objeto alrededor del que se ata el nudo, por ejemplo un poste (ver abajo). |
| `cuerdas` | no | Solo en los nudos de dos o más cuerdas: el nombre, el grosor y el color de cada una (ver abajo). Un nudo de una sola cuerda no lo lleva. |
| `segmentos` | sí | Tramos de cuerda con nombre. Cada uno es una lista de puntos `[x, y]` sobre la mesa, o `{poste: [[x, ángulo], ...]}` sobre el poste. |
| `pasos` | sí | Lista de pasos en orden. |
| `error` | no | El error más común (ver abajo). La ficha lo necesita, así que todo nudo publicado lo lleva. |
| `terminado` | no | Cómo se muestra el nudo terminado (ver abajo). |
| `filtros` | no | Registro de los dos filtros humanos (ver abajo). |

Los campos desconocidos producen un error, así que un error de tipeo se detecta al cargar.

Los campos marcados «para la ficha» se pueden dejar para después mientras se modela el nudo, pero `python -m nudos ficha` no genera la ficha sin ellos ni sin `error`. Todo el texto va en tuteo, es propio y no usa términos de ninguna sección: la ficha no se genera si aparece alguno de `config/terminos_seccion.txt`.

## Segmentos y referencias

Un segmento es una lista de puntos de control por donde pasa la curva. Cada paso encadena segmentos, así que un tramo que no cambia entre pasos se define una sola vez.

| Referencia | Significa | Dónde se usa |
|---|---|---|
| `gaza` | El segmento completo | trazado |
| `gaza[1:]`, `gaza[:-2]` | Un tramo, con la notación de Python | trazado |
| `gaza[0]`, `gaza[-1]` | Un punto del segmento | resaltar |
| `fin` | El último punto del paso | resaltar |

Los índices se cuentan sobre el segmento tal como está definido. Dos puntos seguidos no pueden quedar a menos de 0,05 diámetros.

## Anfitrión

Algunos nudos se atan alrededor de un objeto rígido. Por ahora el único es el poste; los demás (argolla, estaca, tablón, barril, cornamusa, cuerda anfitriona) se agregan con el primer nudo que los necesite.

| Campo | Qué es |
|---|---|
| `tipo` | `poste`. |
| `radio` | Radio del poste, en diámetros de cuerda. Un palo de escoba con una cuerda de 8 mm da alrededor de 1,5. |
| `desde`, `hasta` | Dónde empieza y termina el poste a lo largo de x. |

El poste es horizontal y va a lo largo de x, con el eje en y = 0. Se apoya sobre la cuerda que pasa por debajo, así que su eje queda a la altura `radio + 1`.

Un segmento sobre el poste se escribe `{poste: [[x, ángulo], ...]}`. `x` es la posición a lo largo del eje y `ángulo`, en grados, el giro alrededor del eje: 0 arriba, 90 hacia quien ata, 180 abajo y 270 atrás. El ángulo no vuelve a 0: una vuelta por encima del poste que empieza al frente va, por ejemplo, de 90 a -270, y la siguiente sigue bajando. Así el sentido de cada vuelta queda escrito en los números. No hay capas: qué tramo queda encima en cada cruce lo dice la secuencia, igual que sobre la mesa.

Un paso puede pasar de la mesa al poste y volver. Conviene que la cuerda no suba por el frente del poste para bajar enseguida a la mesa: esa esquina no existe en la cuerda real y la relajación no la resuelve.

## Varias cuerdas

Algunos nudos unen dos cuerdas, a veces de distinto grosor. Se declaran en `cuerdas`, en orden:

```yaml
cuerdas:
  - {nombre: gruesa, grosor: 1.5, color: azul}
  - {nombre: delgada, grosor: 1, color: crema}
```

| Campo | Qué es |
|---|---|
| `nombre` | Nombre de la cuerda, con minúsculas, números y guiones. Es la clave de esa cuerda en el trazado y la secuencia de cada paso. |
| `grosor` | Diámetro de la cuerda, relativo al de la cuerda de siempre, que mide 1. |
| `color` | `azul` o `crema`. Cada cuerda lleva uno distinto. El ámbar queda para el tramo que se mueve en cada paso; en gris, el crema queda claro, el ámbar medio y el azul oscuro. |

En cada paso, `trazado` y `secuencia` pasan a ser mapas con todas las cuerdas:

```yaml
trazado:
  gruesa: [seno]
  delgada: [delgada-firme, delgada-sube]
secuencia:
  gruesa: "1O 2U"
  delgada: "1U 2O"
```

- Cada paso lleva todas las cuerdas. Una cuerda que no pasa por cruces se escribe `""`.
- Los segmentos son de todo el nudo, pero cada uno pertenece a una sola cuerda: si un paso lo pone en otra cuerda, es un error.
- Un tramo resaltado va en una sola cuerda, y ahí `fin` es el último punto de la cuerda donde empieza.
- Por ahora un nudo de varias cuerdas no lleva anfitrión.

## Pasos

| Campo | Qué es |
|---|---|
| `titulo` | Título corto, en imperativo y tuteo. |
| `texto` | Instrucción del paso, en tuteo y con texto propio. |
| `trazado` | Segmentos o tramos en el orden de la cuerda. Cada segmento aparece una sola vez. Con varias cuerdas, un mapa por cuerda (ver arriba). |
| `secuencia` | La secuencia de cruces (ver abajo). Si el paso no tiene cruces, se escribe `""`. Con varias cuerdas, un mapa por cuerda. |
| `resaltar` | Opcional. Con `desde` y `hasta` marca el tramo que se mueve en este paso. |

## Secuencia de cruces

Para escribirla, recorre la cuerda desde el firme y anota cada vez que pasa por un cruce: la etiqueta del cruce más `O` si pasa por encima o `U` si pasa por debajo. Por ejemplo, en el paso 4 del as de guía la secuencia es `1U 2O 3U 1O 2U 3O`.

Con varias cuerdas, cada secuencia recorre su cuerda desde su firme. Un cruce entre las dos cuerdas tiene una pasada en cada secuencia, y un cruce de una cuerda consigo misma tiene las dos en la suya.

Reglas:

- En un paso, cada etiqueta aparece dos veces, una con `O` y otra con `U`. Con varias cuerdas, dos veces entre todas.
- Cada etiqueta nombra un solo cruce en todo el nudo. Un cruce que sigue en el paso siguiente conserva su etiqueta.
- Un cruce no cambia de encima a debajo entre pasos. Si cambia, es otro cruce y lleva otra etiqueta.
- El trazado tiene que formar exactamente esos cruces, en ese orden.

## Error común

Es un paso con algunos cruces al revés: el mismo trazado, pero con otra secuencia. En la ficha va junto al mismo paso bien hecho y con el mismo encuadre. Como no es un paso del nudo, es el único lugar donde un cruce cambia de encima a debajo.

| Campo | Qué es |
|---|---|
| `paso` | Número del paso que se muestra con el error. |
| `invierte` | Etiquetas de los cruces que quedan al revés, por ejemplo `[1]`. Tienen que estar en ese paso. |
| `titulo` | Nombre corto del error. |
| `texto` | Cómo reconocerlo y qué hacer, en tuteo y con texto propio. |
| `encuadre` | Opcional. Zona que se muestra del error y del paso correcto, como el `encuadre` del nudo. Conviene acercarse al cruce. |

Las dos imágenes usan el `resaltar` de ese paso. Para que el error se vea, el resaltado debe empezar o terminar fuera del cruce invertido: así un tramo llega azul y el otro resaltado, y se ve cuál va encima.

## Nudo terminado

El último paso se muestra por delante y por detrás. Sin anfitrión, la vista de detrás se obtiene volteando la cuerda sobre el eje y, como una página, y dejándola asentarse otra vez en la mesa. Al voltear, todos los cruces quedan al revés. Con un anfitrión el nudo no se voltea: se mira desde el otro lado de la mesa.

| Campo | Qué es |
|---|---|
| `encuadre` | Opcional. Zona que se muestra del nudo terminado, por delante. Por detrás se usa la misma zona volteada. |

## Filtros

Cada vez que se prueba la ficha impresa se agrega una entrada, también si no pasa. El filtro 1 es Gabriel atando cada paso con cuerda real; el filtro 2 es alguien que nunca ha hecho el nudo y lo ata solo con la ficha.

| Campo | Qué es |
|---|---|
| `filtro` | 1 o 2. |
| `fecha` | Día de la prueba, como `2026-11-07`. |
| `resultado` | `aprobado` o `no aprobado`. |
| `rol` | En el filtro 2, el rol del probador, por ejemplo «dirigente». Es obligatorio. |
| `codigo` | En el filtro 2, un código anónimo como `P01`. Es obligatorio. La tabla que une códigos con personas vive fuera del repositorio. |
| `ficha` | Opcional. El commit de la ficha que se probó, para saber si un cambio posterior obliga a repetir la prueba. |

Del probador nunca se guarda el nombre: un campo `nombre` es un campo desconocido, y el código solo acepta letras mayúsculas seguidas de números.

## Qué se comprueba al construir

1. La especificación cumple este formato.
2. **Consistencia entre pasos:** cada cruce conserva su encima/debajo en todos los pasos donde aparece. Así se detecta un cruce invertido en un solo paso.
3. En cada paso, después de relajar la cuerda:
   - la secuencia de cruces es la declarada;
   - ningún tramo queda a menos de 0,97 diámetros de otro;
   - el radio de curvatura no baja de 0,9 diámetros;
   - la cuerda no se estira más de 2 %.
   - con un anfitrión, la cuerda no entra en él más de 0,05 diámetros.
4. Un cruce con la misma etiqueta no aparece a más de 2,5 diámetros de donde estaba en el paso anterior. Es una heurística para detectar una etiqueta reutilizada para otro cruce.
5. El error común y el nudo terminado por detrás se construyen como un paso más y cumplen los mismos límites. Además:
   - la secuencia del error, después de relajar, difiere de la del paso correcto exactamente en los cruces de `invierte`;
   - la secuencia del nudo por detrás es la del último paso con todos los cruces al revés.

**Dónde se buscan los cruces.** Sobre la mesa, en la proyección vista desde arriba: encima es lo más alto. Sobre el poste, en su superficie desenrollada (x y el arco alrededor del eje, comparando cada par en la vuelta más cercana): encima es lo más lejos del eje. Un tramo cuenta como «sobre el poste» si sale de un segmento sobre el poste. Los cruces entre un tramo del poste y uno de la mesa no se buscan; ahí solo se comprueba la separación.

**Lo que no se comprueba es si la secuencia corresponde al nudo correcto.** Un cruce mal leído que se repite igual en todos los pasos pasa todas las pruebas. Para eso está el filtro 1: atar cada paso con cuerda real antes de publicar.

## Pendiente para versiones siguientes

- Construir los nudos de varias cuerdas (T6): el formato ya las acepta, pero `python -m nudos construir` todavía no.
- Varias cuerdas sobre un anfitrión.
- Los anfitriones que faltan (argolla, estaca, tablón, barril, cornamusa, cuerda anfitriona), con el primer nudo que los use.
- Cruces entre un tramo sobre un anfitrión y uno sobre la mesa.
- Dibujar el anfitrión en la hoja de revisión (`python -m nudos hoja`): hoy solo dibuja la cuerda.
- Nudos que se voltean sobre la mesa: voltear invierte todos los cruces, y hoy eso obligaría a usar etiquetas nuevas.
