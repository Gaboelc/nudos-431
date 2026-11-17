# Formato de especificación de nudo (v1.7)

Cada nudo es un archivo `specs/<slug>.yaml`. Es la fuente de verdad: los modelos 3D, las imágenes y la ficha se generan desde aquí. Esta es la versión 1.5 del formato. Cómo puede cambiar desde aquí, y qué parte es todavía provisional, está al final, en «Versiones».

Los ejemplos son los nudos publicados: `specs/as-de-guia.yaml`, el más completo, con una cuerda sobre la mesa; `specs/ballestrinque.yaml`, sobre un poste; `specs/vuelta-de-escota.yaml`, con dos cuerdas, y `specs/amarre-cuadrado.yaml`, con una plantilla.

## Unidades y ejes

- El diámetro de la cuerda vale 1. Todas las medidas están en diámetros. En un nudo de varias cuerdas, 1 es el diámetro de la cuerda de siempre y cada cuerda declara su grosor.
- x crece hacia la derecha, y hacia el fondo de la mesa (lejos de quien ata) y z hacia arriba desde la mesa.
- La cuerda se recorre desde el firme hasta el chicote. Los primeros puntos del firme quedan fijos. Con varias cuerdas, cada una se recorre desde su firme. Un nudo en medio de la cuerda se recorre desde uno de sus dos firmes hasta el otro (ver «En medio de la cuerda»).

## Campos

| Campo | Obligatorio | Qué es |
|---|---|---|
| `slug` | sí | Identificador permanente, con minúsculas, números y guiones. Es igual al nombre del archivo. Cuando su QR se imprime, ya no cambia. |
| `nombre` | sí | Nombre del nudo en la ficha. |
| `otros_nombres` | no | Lista de otros nombres, cuando una sección lo llama distinto. La ficha los pone bajo el nombre. |
| `familia` | sí | Familia del índice: De tope, De unión, Gazas, De sujeción, Autoblocantes, Corredizos, De ligadura, Amarres, Decorativos, De acortamiento… |
| `abok` | no | Número en *The Ashley Book of Knots*. |
| `usos` | para la ficha | Para qué sirve. |
| `materiales` | para la ficha | Qué cuerda y qué objetos hacen falta. |
| `verificacion` | para la ficha | Lista de criterios para revisar el nudo terminado. Cada uno se tiene que poder comprobar mirando o tirando del nudo. |
| `precauciones` | para la ficha | Lista de cuidados y peligros al usar el nudo: cuándo se afloja, se corre o se aprieta demasiado, y qué hacer. Lo que va en `seguridad` no se repite aquí. |
| `alternativas` | para la ficha | Lista de otros nudos que convienen en su lugar, cada uno con `nudo` (su nombre) y `cuando` (en qué caso conviene más que este). Si el otro nudo está en el libro, usa el mismo nombre de su ficha. |
| `seguridad` | no | Solo cuando aplica. Si el nudo tiene usos con personas, sigue la postura de seguridad del libro (D1 del plan). |
| `encuadre` | no | Zona de la mesa que se muestra, como `x: [mín, máx]` e `y: [mín, máx]`. Si falta, se calcula con todos los pasos. |
| `anfitrion` | no | El objeto alrededor del que se ata el nudo, por ejemplo un poste o los dos palos de un amarre (ver abajo). |
| `dos_firmes` | no | Solo en un nudo que se ata en medio de la cuerda, como la mariposa alpina: `true` dice que la cuerda termina en otro firme y no en un chicote (ver «En medio de la cuerda»). Sin él, `false`. |
| `cuerdas` | no | Solo en los nudos de dos o más cuerdas: el nombre, el grosor y el color de cada una (ver abajo). Un nudo de una sola cuerda no lo lleva. |
| `segmentos` | sí, salvo con `plantilla` | Tramos de cuerda con nombre. Cada uno es una lista de puntos `[x, y]` sobre la mesa, o `{poste: [[x, ángulo], ...]}` sobre el poste. |
| `plantilla` | no | En un nudo que se genera a partir de unas pocas medidas, como un amarre, el tipo de plantilla y sus medidas (ver abajo). Entonces el nudo no lleva `segmentos`. |
| `pasos` | sí | Lista de pasos en orden. |
| `error` | no | El error más común (ver abajo). La ficha lo necesita, así que todo nudo publicado lo lleva. |
| `terminado` | no | Cómo se muestra el nudo terminado (ver abajo). |
| `filtros` | no | Registro de los dos filtros humanos (ver abajo). |
| `estado` | no | Estado de producción: `borrador`, `modelado`, `cuerda-ok`, `novato-ok` o `publicado` (ver abajo). Sin él, `borrador`. |

Los campos desconocidos producen un error, así que un error de tipeo se detecta al cargar.

Los datos de `entradas/` (por ejemplo, los `info.txt` de Animated Knots) sirven para saber qué escribir en estos campos, pero el texto se escribe de nuevo: nunca se copia. La ficha y la página del visor muestran los mismos campos.

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

Algunos nudos se atan alrededor de un objeto rígido. Por ahora son el poste, la cruz de los amarres, los palos paralelos, el tubo de la cabeza de turco, el cabo del refuerzo de cabo, el destorcedor y la estaca; los demás (argolla, tablón, barril, cornamusa, cuerda anfitriona) se agregan con el primer nudo que los necesite.

| Campo | Qué es |
|---|---|
| `tipo` | `poste`, `cruz`, `palos`, `tubo`, `cabo`, `destorcedor` o `estaca`. |
| `radio` | Radio del poste, en diámetros de cuerda. Un palo de escoba con una cuerda de 8 mm da alrededor de 1,5. |
| `desde`, `hasta` | Dónde empieza y termina el poste a lo largo de x. |

La cruz son dos palos del mismo grosor, cruzados en ángulo recto sobre la mesa, para los amarres. Solo se usa con una `plantilla`.

| Campo | Qué es |
|---|---|
| `tipo` | `cruz`. |
| `radio` | Radio de los dos palos, en diámetros de cuerda. Un palo de 4 cm con una cuerda de 8 mm da 2,5. |
| `largo` | Largo de cada palo. Los dos están centrados en el cruce. |

Los palos se cruzan en x = y = 0. El de abajo va a lo largo de y, hacia el fondo de la mesa, y se apoya en la cuerda que pasa por debajo: su eje queda a la altura `radio + 1`, como el del poste. El de arriba va a lo largo de x y se apoya sobre el de abajo. Con el amarre diagonal, bajo el palo de abajo se cruzan las dos diagonales, así que se apoya en dos capas de cuerda y su eje queda a `radio + 2,1`: la décima de más es aire, para que la capa de abajo no quede apretada contra la mesa. La especificación no lo escribe: lo dice la plantilla.

Los palos paralelos son dos o tres palos del mismo grosor, acostados uno junto al otro, para el amarre redondo y el trípode. Solo se usan con una `plantilla`.

| Campo | Qué es |
|---|---|
| `tipo` | `palos`. |
| `cantidad` | Cuántos palos: 2 (el amarre redondo) o 3 (el trípode). Cada plantilla pide los suyos. |
| `radio` | Radio de los palos, en diámetros de cuerda. Un palo de 4 cm con una cuerda de 8 mm da 2,5. |
| `largo` | Largo de cada palo. Están centrados en x = 0. |

```yaml
anfitrion: {tipo: palos, cantidad: 2, radio: 2.5, largo: 30}
```

Van a lo largo de x, uno junto al otro a lo largo de y y simétricos alrededor de y = 0, con un hueco de 1,1 diámetros entre sus caras: por ahí bajan los ahorcados, que en la cuerda real apartan los palos lo mismo. El de delante es el de y negativa, hacia quien ata. Sus ejes quedan a la altura `radio + 2,1`: por debajo del hueco pasan dos capas de cuerda, la vuelta y el ahorcado que la rodea, con algo de holgura. Así ninguna cuerda baja de la mesa, pero los palos quedan un poco sobre ella en todos los pasos.

El poste es horizontal y va a lo largo de x, con el eje en y = 0. Se apoya sobre la cuerda que pasa por debajo, así que su eje queda a la altura `radio + 1`.

El tubo es un cilindro alrededor del que se teje la cabeza de turco. Solo se usa con una `plantilla`. Es provisional, como la plantilla de la cabeza de turco (ver «Versiones»).

| Campo | Qué es |
|---|---|
| `tipo` | `tubo`. |
| `radio` | Radio del tubo, en diámetros de cuerda. Con un cordón de 4 mm, un radio de 4 es un tubo de 3,2 cm. |
| `largo` | Largo del tubo. Está centrado en x = 0. |

Es horizontal y va a lo largo de x, con el eje en y = 0, como el poste, pero el nudo lo rodea entero y se apoya sobre él: debajo de cada cruce hay dos capas de cuerda, así que su eje queda a la altura `radio + 2`. Se gira en la mano: en cada paso, el nudo se gira alrededor del eje para que lo que agrega el paso quede de frente.

Un segmento sobre el poste se escribe `{poste: [[x, ángulo], ...]}`. `x` es la posición a lo largo del eje y `ángulo`, en grados, el giro alrededor del eje: 0 arriba, 90 hacia quien ata, 180 abajo y 270 atrás. El ángulo no vuelve a 0: una vuelta por encima del poste que empieza al frente va, por ejemplo, de 90 a -270, y la siguiente sigue bajando. Así el sentido de cada vuelta queda escrito en los números. No hay capas: qué tramo queda encima en cada cruce lo dice la secuencia, igual que sobre la mesa.

Un paso puede pasar de la mesa al poste y volver. Conviene que la cuerda no suba por el frente del poste para bajar enseguida a la mesa: esa esquina no existe en la cuerda real y la relajación no la resuelve.

El destorcedor es el ojo de un destorcedor de pesca, como en el nudo aguja: un cilindro corto, parado sobre la mesa, con el eje vertical en x = y = 0. La cuerda le da la vuelta a ras de la mesa y nunca pasa por encima de él.

| Campo | Qué es |
|---|---|
| `tipo` | `destorcedor`. |
| `radio` | Radio del cilindro, en diámetros de cuerda. |
| `alto` | Alto del cilindro desde la mesa. Es mayor que 1, para que la cuerda que lo rodea no quede por encima. Solo cambia el dibujo. |

```yaml
anfitrion: {tipo: destorcedor, radio: 1.5, alto: 2}
```

Con el destorcedor, todo el nudo va sobre la mesa: los segmentos son `[x, y]`, como sin anfitrión, y un segmento `{poste: …}` es un error. El paso se construye como un nudo libre, pero al relajar la cuerda no puede entrar en el destorcedor: lo que entra se empuja hacia afuera, en el plano de la mesa. Traza la cuerda que lo rodea con su eje a `radio + 0,5` del centro, o un poco más, con puntos cada medio diámetro: así la curva suave no lo corta por dentro y la cuerda no se estira al salir. En las imágenes y en el visor es de metal, gris; en la hoja de revisión, gris.

La estaca es la del tensor ajustable, clavada en el suelo: el mismo cilindro parado que el destorcedor, en x = y = 0, de madera y más alto. La cuerda le da la vuelta a ras del suelo, que es la mesa, y todo lo que dice el párrafo anterior vale igual para ella.

| Campo | Qué es |
|---|---|
| `tipo` | `estaca`. |
| `radio` | Radio de la estaca, en diámetros de cuerda. |
| `alto` | Lo que sale la estaca del suelo. Es mayor que 1, como en el destorcedor, y solo cambia el dibujo. Una estaca muy alta tapa, en la vista de los pasos, la parte de la cuerda que pasa detrás de ella, y echa una sombra larga: con 5 se ve como estaca y no tapa casi nada. |

```yaml
anfitrion: {tipo: estaca, radio: 1.5, alto: 5}
```

En las imágenes y en el visor es de madera, como los palos; en la hoja de revisión, color madera. Al encuadrar, su alto no agranda la zona que se muestra: se encuadra su tapa, para que se vea entera sin achicar el nudo.

El cabo es la punta de una cuerda gruesa, para el refuerzo de cabo: la cuerda del nudo es el cordel con que se refuerza, y todas las medidas van en diámetros del cordel. Solo se usa con una `plantilla`.

| Campo | Qué es |
|---|---|
| `tipo` | `cabo`. |
| `radio` | Radio del cabo, en diámetros del cordel, de 1,5 a 8. Un cabo de 12 mm con un cordel de 2 mm da 3. |
| `largo` | Lo que se ve del cabo, desde la punta. La plantilla pide que el refuerzo quepa. |

```yaml
anfitrion: {tipo: cabo, radio: 3, largo: 30}
```

Es un sólido, un cilindro horizontal a lo largo de x con el eje en y = 0, como el poste y el tubo, pero se dibuja como una cuerda gruesa, crema y con la trenza de las cuerdas. La punta, cortada, está en x = 0, a la derecha, y el cabo sigue hacia x negativo hasta `-largo`. Se apoya en la mesa sobre las vueltas del cordel, así que su eje queda a la altura `radio + 1`, como el del poste. Más allá de la punta el cordel puede pasar libre, por delante del corte. Alrededor del eje, un ángulo se mide como sobre el poste: 0 arriba, 90 hacia quien ata. En la hoja de revisión es color crema y va además desenrollado, como el tubo.

## En medio de la cuerda

Algunos nudos se atan en medio de la cuerda, sin usar sus extremos, como la mariposa alpina. Tienen dos firmes y ningún chicote. Se declaran con `dos_firmes: true`, y la cuerda se recorre desde uno de los dos firmes, normalmente el que queda quieto, hasta el otro, que es con el que se trabaja.

- En las imágenes y en el visor, los dos extremos llevan «Firme» y ninguno lleva «Chicote». El primero va donde la cuerda entra al encuadre y el otro donde sale o, si no sale, junto a su final. Las imágenes del error común también llevan los dos.
- Solo cambian los nombres. La cuerda, los cruces, el remate del final y el nudo apretado son los de siempre: después de su último cruce, el otro firme es la cola, que el nudo arrastra al apretarse (ver «El nudo apretado»).
- En el texto, el otro firme no se llama «chicote». Puede ser «el otro firme» o «el firme de la izquierda».
- Por ahora, solo un nudo de una sola cuerda y sin plantilla lleva `dos_firmes`. Con varias cuerdas, cada una ya lleva su nombre junto a su firme, y en un nudo de plantilla es la plantilla la que dice qué nombres lleva cada paso.

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
  gruesa: [gruesa-firme]
  delgada: [delgada-firme, delgada-cruza]
secuencia:
  gruesa: "1U"
  delgada: "1O"
```

Aquí la delgada cruza una vez por encima de la gruesa. El ejemplo no es de ningún nudo del libro.

- Cada paso lleva todas las cuerdas. Una cuerda que no pasa por cruces se escribe `""`.
- Los segmentos son de todo el nudo, pero cada uno pertenece a una sola cuerda: si un paso lo pone en otra cuerda, es un error.
- Un tramo resaltado va en una sola cuerda, y ahí `fin` es el último punto de la cuerda donde empieza.
- Por ahora un nudo de varias cuerdas no lleva anfitrión.
- Donde una cuerda gruesa pasa por encima de una más delgada, dibuja el cruce en diagonal, a unos 60° o menos. En ángulo recto, la gruesa se apoya sobre la delgada con un radio igual a la suma de los dos radios, que es menos de 0,9 de su diámetro, y la prueba de curvatura falla. En diagonal se apoya más abierta. Como el nudo terminado se voltea para verlo por detrás, y entonces cada cruce queda al revés, esto vale para todos los cruces entre una gruesa y una delgada.
- En las imágenes, cada cuerda lleva su nombre junto a su firme («gruesa» se escribe «Gruesa») y «Chicote» va en la que se mueve en ese paso. En una imagen sin resaltado, como el nudo terminado, va en la última que se movió.

## Plantillas

Algunos nudos no se dibujan punto por punto: se generan a partir de unas pocas medidas, como los amarres. Un nudo así lleva `plantilla` y no lleva `segmentos`; sus pasos no llevan `trazado`, `secuencia` ni `resaltar`, sino `hasta`, que dice hasta dónde llega cada uno. La plantilla calcula la cuerda entera y cada paso es su comienzo hasta ese punto, así que cambiar una medida, por ejemplo de 3 a 4 vueltas, regenera todos los pasos.

Hay siete: el amarre cuadrado y el amarre diagonal, sobre una `cruz`; el amarre redondo y el trípode, sobre los `palos` paralelos; la cabeza de turco, sobre un `tubo`; el refuerzo de cabo, sobre un `cabo`, y el puño de mono, sin anfitrión. Una plantilla sin anfitrión no lleva `anfitrion`: si lo lleva, es un error al cargar. En el refuerzo de cabo, el seno y el tirar cambian el principio de la cuerda, que es el extremo corto, así que ahí cada paso no es el comienzo de una sola cuerda: la plantilla da la cuerda de cada paso entera, y dice qué tramo se resalta. En el puño de mono es igual, porque meter el nudo y apretar cambian el puño entero.

### Amarre cuadrado

```yaml
anfitrion: {tipo: cruz, radio: 2.5, largo: 40}
plantilla:
  tipo: amarre-cuadrado
  vueltas: 3
  ahorcados: 3
  inicio: {poste: abajo, lado: delante}
  cierre: {poste: arriba, lado: derecha}
pasos:
  - {titulo: Haz un ballestrinque en el palo de abajo, texto: …, hasta: inicio}
  - {titulo: Da la primera vuelta, texto: …, hasta: vuelta-1}
  - {titulo: Da las demás vueltas, texto: …, hasta: vueltas}
```

| Campo | Qué es |
|---|---|
| `tipo` | `amarre-cuadrado`. |
| `vueltas` | Vueltas alrededor de los dos palos, de 2 a 6. |
| `ahorcados` | Ahorcados entre los palos, alrededor de las vueltas, de 2 a 6. |
| `inicio` | Dónde va el ballestrinque de inicio: `poste` (`abajo` o `arriba`) y `lado`. Sobre el palo de abajo, el lado es `delante` (hacia quien ata) o `detras`; sobre el de arriba, `izquierda` o `derecha`. |
| `cierre` | Dónde va el ballestrinque de cierre, igual que `inicio`. |

Por ahora el inicio va en el palo de abajo y el cierre en el de arriba, que es el método del manual de la Tropa.

`hasta` puede ser, en este orden: `inicio-1` (el ballestrinque de inicio hasta antes de su diagonal, desde el chicote), `inicio`, `vuelta-1` … `vuelta-<n>`, `ahorcado-1` … `ahorcado-<n>`, `cierre-1` (el ballestrinque de cierre hasta que su diagonal cruza el firme) y `cierre`. `vueltas` es lo mismo que la última vuelta y `ahorcados` que el último ahorcado: así un paso que dice `hasta: vueltas` sigue valiendo si cambia el número de vueltas. Cada paso llega más lejos que el anterior y el último llega a `cierre`. Un `hasta` que no existe con esas medidas, como `vuelta-4` con 3 vueltas, es un error al cargar.

En todo el texto del nudo, `{vueltas}` y `{ahorcados}` se reemplazan por el número en letras («tres»). Otra palabra entre llaves es un error. En los nudos sin plantilla las llaves se dejan como están.

En las imágenes se ven los dos extremos de la cuerda, y los dos llevan remate. El paso del ballestrinque de inicio (`inicio-1` o `inicio`) lleva «Firme» en la parte larga y «Chicote» en el extremo corto, como el ballestrinque. Desde la primera vuelta se mueve la parte larga, y los pasos solo llevan «Chicote», en su punta.

### Amarre diagonal

```yaml
anfitrion: {tipo: cruz, radio: 3.0, largo: 44}
plantilla:
  tipo: amarre-diagonal
  vueltas: 3                              # en cada diagonal
  ahorcados: 3                            # entre los palos
  cierre: {poste: arriba, lado: derecha}  # ballestrinque de cierre
pasos:
  - {titulo: Haz una vuelta de braza alrededor de los dos palos, texto: …, hasta: inicio}
  - {titulo: Da la primera vuelta en diagonal, texto: …, hasta: vuelta-1}
  - {titulo: Completa las {vueltas} vueltas, texto: …, hasta: vueltas}
  - {titulo: Cambia a la otra diagonal, texto: …, hasta: segunda-1}
```

| Campo | Qué es |
|---|---|
| `tipo` | `amarre-diagonal`. |
| `vueltas` | Vueltas en cada diagonal, de 2 a 4. Las dos diagonales llevan las mismas. |
| `ahorcados` | Ahorcados entre los palos, alrededor de las vueltas, de 2 a 6. |
| `cierre` | Dónde va el ballestrinque de cierre, como en el amarre cuadrado. Por ahora va en el palo de arriba (`poste: arriba`), a la `derecha` o a la `izquierda`. |

No lleva `inicio`: empieza siempre con una vuelta de braza alrededor de los dos palos, que al tirar del firme los junta. Su chicote rodea el firme y se enrolla tres veces en su propio tramo, en la cara de delante del palo de arriba, como en la ficha de la vuelta de braza.

Cada vuelta va en diagonal, a 45° de los dos palos. Las de la primera diagonal van una junto a otra, junto a la vuelta de braza. Las de la segunda las cruzan por fuera, por encima del palo de arriba y por debajo del de abajo. Después vienen los ahorcados y el ballestrinque de cierre, como en el amarre cuadrado. Con el cierre a la derecha, la primera diagonal va de delante a la izquierda hacia atrás a la derecha; a la izquierda, todo el amarre es su reflejo, como en las fotos de la fuente.

Cada vuelta tiene que bajar entre los dos palos y no por encima de uno de ellos, así que las de una diagonal tienen que caber en el grosor de los palos. Con palos de radio 3 caben 3 vueltas en cada diagonal y con radio 4 caben 4. Si no caben, construir el nudo falla y lo dice.

`hasta` puede ser, en este orden: `inicio` (la vuelta de braza entera), `vuelta-1` … `vuelta-<n>` (la primera diagonal), `segunda-1` … `segunda-<n>` (la segunda), `ahorcado-1` … `ahorcado-<n>`, `cierre-1` y `cierre`. `vueltas`, `segundas` y `ahorcados` son lo mismo que el último de cada uno. No hay `inicio-1`: la cuerda se calcula desde el chicote, y la vuelta de braza sin las vueltas del chicote no es un comienzo de ella.

En todo el texto del nudo, `{vueltas}` y `{ahorcados}` se reemplazan por el número en letras, como en el amarre cuadrado.

En el paso de la vuelta de braza, la parte larga lleva «Firme» y el extremo corto «Chicote», como en la vuelta de braza. Desde la primera vuelta, los pasos solo llevan «Chicote», en la punta de la parte larga.

### Amarre redondo

```yaml
anfitrion: {tipo: palos, cantidad: 2, radio: 2.5, largo: 30}
plantilla:
  tipo: amarre-redondo
  vueltas: 6
  ahorcados: 2
pasos:
  - {titulo: Haz un ballestrinque en un palo, texto: …, hasta: inicio}
  - {titulo: Da la primera vuelta, texto: …, hasta: vuelta-1}
  - {titulo: Completa las {vueltas} vueltas, texto: …, hasta: vueltas}
  - {titulo: Da el primer ahorcado, texto: …, hasta: ahorcado-1}
  - {titulo: Completa los {ahorcados} ahorcados, texto: …, hasta: ahorcados}
  - {titulo: Empieza el ballestrinque de cierre, texto: …, hasta: cierre-1}
  - {titulo: Termina el ballestrinque, texto: …, hasta: cierre}
```

| Campo | Qué es |
|---|---|
| `tipo` | `amarre-redondo`. Va sobre dos `palos`. |
| `vueltas` | Vueltas alrededor de los dos palos, de 2 a 6. |
| `ahorcados` | Ahorcados en el hueco entre los palos, alrededor de las vueltas, 2 o 3. Van uno junto a otro por encima y por debajo de las vueltas; con más, se saldrían del hueco. |

El método: un ballestrinque en el palo de delante, a la izquierda; las vueltas alrededor de los dos palos, de izquierda a derecha y una junto a otra (por encima, por detrás del de atrás, por debajo y por delante del de delante); los ahorcados, que bajan por el hueco a la derecha de las vueltas, pasan por debajo, suben a la izquierda y pasan por encima, cada uno junto al anterior, y un ballestrinque de cierre en el palo de delante, a la derecha de los ahorcados. No lleva `inicio` ni `cierre`: el método los pone siempre ahí.

`hasta` puede ser, en este orden, lo mismo que en el amarre cuadrado: `inicio-1`, `inicio`, `vuelta-1` … `vuelta-<n>`, `ahorcado-1` … `ahorcado-<n>`, `cierre-1` y `cierre`, con `vueltas` y `ahorcados` como la última vuelta y el último ahorcado. En el texto, `{vueltas}` y `{ahorcados}` salen en letras, y los nombres en las imágenes son los del amarre cuadrado: «Firme» y «Chicote» en el paso del ballestrinque de inicio, y desde la primera vuelta solo «Chicote», en la punta de la parte larga.

Cada ahorcado pasa por encima de cada vuelta, por debajo y por encima de ellas, salvo por encima de la primera: ahí la vuelta es el firme que sale del ballestrinque, a la izquierda de los ahorcados. Con `n` vueltas y `m` ahorcados son `m × (2n − 1) + 4` cruces, 26 con 6 y 2.

### Amarre trípode

Es el amarre redondo con tres palos: `tipo: amarre-tripode`, sobre tres `palos`, con las mismas medidas. `ahorcados` es cuántos van en cada hueco. Las vueltas van alrededor de los tres palos. Primero se ahorca el hueco de atrás, entre el palo del medio y el de atrás, y después el de delante; la cuerda pasa de uno al otro por encima del palo del medio, a la derecha de los ahorcados, y el cierre va en el palo de delante, como en el redondo.

Los ahorcados se numeran a lo largo de la cuerda, de `ahorcado-1` hasta el doble de `ahorcados`: primero los del hueco de atrás. `hueco-1` es lo mismo que el último del hueco de atrás, y `ahorcados`, que el último de todos:

```yaml
pasos:
  - {titulo: Haz un ballestrinque en un palo de afuera, texto: …, hasta: inicio}
  - {titulo: Da la primera vuelta, texto: …, hasta: vuelta-1}
  - {titulo: Completa las {vueltas} vueltas, texto: …, hasta: vueltas}
  - {titulo: Ahorca el hueco de atrás, texto: …, hasta: hueco-1}
  - {titulo: Ahorca el hueco de delante, texto: …, hasta: ahorcados}
  - {titulo: Empieza el ballestrinque de cierre, texto: …, hasta: cierre-1}
  - {titulo: Termina el ballestrinque, texto: …, hasta: cierre}
```

En el hueco de delante, cada ahorcado pasa además por encima de la cuerda que va de la última vuelta al hueco de atrás. Con `n` vueltas y `m` ahorcados por hueco son `m × (4n − 1) + 4` cruces, 50 con 6 y 2. La ficha muestra el trípode cerrado, sobre la mesa, como se ata; cómo se abren las patas va en el texto.

### Cabeza de turco (provisional)

Esta plantilla y su anfitrión, el tubo, no entran todavía en v1 y pueden cambiar cuando se retome el nudo (ver «Versiones»).

```yaml
anfitrion: {tipo: tubo, radio: 4, largo: 24}
plantilla:
  tipo: cabeza-de-turco
  cabos: 3
  senos: 4
  pasadas: 2
pasos:
  - {titulo: Da la primera vuelta, texto: …, hasta: vuelta-1}
  - {titulo: Cruza por encima, texto: …, hasta: vuelta-2}
  - {titulo: Empieza a tejer, texto: …, hasta: vuelta-3-mitad}
  - {titulo: Termina de tejer, texto: …, hasta: vueltas}
  - {titulo: Sigue el mismo camino, texto: …, hasta: pasadas}
  - {titulo: Esconde los chicotes, texto: …, hasta: remate}
```

| Campo | Qué es |
|---|---|
| `tipo` | `cabeza-de-turco`. |
| `cabos` | Vueltas que da la cuerda al tubo, de 2 a 5. |
| `senos` | Senos que hace en cada borde del nudo, de 2 a 7. No puede tener un divisor común con `cabos` aparte del 1: si lo tiene, salen dos o más cuerdas cerradas y no un nudo de una sola cuerda. Con 3 cabos no se puede hacer con 3 ni con 6 senos. |
| `pasadas` | Veces que la cuerda recorre el mismo camino, de 1 a 3. Cada pasada más va junto a la primera, siempre del mismo lado. |

El método es tejer vuelta por vuelta: cada vuelta pasa por encima o por debajo de lo que ya está, como queda en el nudo terminado, así que entre un paso y otro ningún cruce cambia. Con 3 cabos, la primera vuelta no cruza nada, la segunda cruza la primera siempre por encima y la tercera teje por debajo, por encima, por debajo… hasta llegar junto al comienzo. Cada pasada más sigue el mismo camino, y al final los dos extremos se esconden bajo la banda de al lado. Con otro número de cabos se teje igual, pero la segunda vuelta ya no va toda por encima. Se cruza `senos × (cabos − 1) × pasadas²` veces, más los cruces del remate.

`hasta` puede ser, en este orden: `vuelta-1-mitad`, `vuelta-1`, … `vuelta-<cabos>-mitad`, `vuelta-<cabos>` (la primera pasada, por medias vueltas), `pasada-2-mitad`, `pasada-2`, … `pasada-<pasadas>` y `remate` (los dos extremos escondidos). `vueltas` es lo mismo que la última vuelta y `pasadas` que la última pasada; con una sola pasada, `pasadas` es lo mismo que `vueltas`. Cada paso llega más lejos que el anterior y el último llega a `remate`.

En todo el texto del nudo, `{cabos}`, `{senos}` y `{pasadas}` se reemplazan por el número en letras («tres», y «una» pasada). Cambiar una medida regenera la cuerda, los cruces, los pasos y las imágenes, pero el texto puede tener que cambiar: «cruza por encima tres veces» depende de los senos.

Ningún paso tiene firme: el extremo corto se sujeta contra el tubo y se trabaja con la parte larga, que lleva «Chicote» en su punta en todos los pasos. Los dos extremos llevan remate.

Lo que hace la plantilla con esas medidas (`nudos/plantillas/cabeza_turco.py`; ver «Cómo se hizo la geometría» de T8 en el plan):

- **La onda.** El ancho de la onda depende del ángulo con que las cuerdas cruzan la dirección en que se rodea el tubo. La plantilla elige el menor entre 45° y 70°, de 5 en 5, con el que la cuerda ideal (las pasadas cerradas, sin los extremos) queda a 1 diámetro de las demás y con un radio de curvatura de al menos 1,2. Si no cabe con ninguno, ningún paso se construye y la falla dice el radio mínimo del tubo para esas medidas.
- **Los extremos** salen por un mismo seno de un borde, el seno A. El extremo corto llega desde fuera del nudo, a lo largo del tubo, y entra a la primera pasada a media diagonal del brazo que sale de A, lejos de los cruces. Al volver a A, después de su último cruce, cada pasada se corre a la siguiente por dentro del seno, sobre el ápice, antes de llegar a donde entra el extremo corto, así que no lo cruza. La última pasada termina, en el paso de `pasadas`, a media diagonal antes de su último cruce.
- **El remate** agrega dos cosas: el chicote pasa por su último cruce, por donde le toca, y termina justo después; y el extremo corto, en vez de colgar, vuelve por encima del ápice de A y se mete por debajo de la banda que baja del seno vecino, antes del último cruce. Esa banda va levantada desde el principio, así que el extremo corto es lo único que cambia en el remate. Son las pasadas por cruces del chicote y uno más por cada pasada de esa banda.
- **Cada paso se gira** alrededor del eje para que lo que agrega, o su última media vuelta si es más largo, quede de frente a la cámara de los pasos (40° desde arriba hacia quien ata). En el remate queda de frente lo que se esconde. `modelo.json` guarda el giro de cada paso (`giro`, en grados).
- **Lo que cae a la mesa.** En cada paso antes del remate, el extremo corto cuelga desde fuera del nudo: si sale por la mitad de arriba del tubo, lo rodea por un costado y cae a la mesa; si sale por la de abajo, sigue a lo largo del tubo mientras baja. El resto de la cuerda se aleja del tubo siguiendo la cuerda, lo rodea por fuera hacia atrás, en el sentido en que se teje, y cae detrás del tubo.

### Refuerzo de cabo

```yaml
anfitrion: {tipo: cabo, radio: 3, largo: 30}
plantilla:
  tipo: refuerzo-de-cabo
  vueltas: 4
pasos:
  - {titulo: Da la primera vuelta, texto: …, hasta: vuelta-1}
  - {titulo: Completa las {vueltas} vueltas, texto: …, hasta: vueltas}
  - {titulo: Haz un seno con el extremo corto, texto: …, hasta: seno}
  - {titulo: Da {vueltas} vueltas sobre el seno, texto: …, hasta: seno-vueltas}
  - {titulo: Pasa el chicote por el seno, texto: …, hasta: por-el-seno}
  - {titulo: Tira del extremo corto, texto: …, hasta: tirar}
  - {titulo: Corta las puntas, texto: …, hasta: cortar}
```

| Campo | Qué es |
|---|---|
| `tipo` | `refuerzo-de-cabo`. |
| `vueltas` | Vueltas de cada mitad: las que se dan sobre el extremo corto y otras tantas sobre el seno. De 4 a 8. Hoy construyen sin fallas 4, la del libro, y 8; con 5, 6 y 7 se dobla la cuerda en el paso de cortar, y `construir` lo dice. |

El método es el de la fuente: el cordel va a lo largo del cabo con el extremo corto hacia la punta; con el largo se dan vueltas hacia la punta, sobre el extremo corto; ese extremo se dobla en un seno sobre las vueltas, con la curva hacia la punta; se dan otras tantas vueltas sobre las dos ramas del seno; el chicote pasa por el seno, y al tirar del extremo corto el seno lo arrastra bajo las vueltas. Al final se cortan las puntas.

`hasta` puede ser, en este orden: `colocar` (el cordel a lo largo del cabo, sin vueltas), `vuelta-1` … `vuelta-<n>`, `seno`, `seno-vuelta-1` … `seno-vuelta-<n>`, `por-el-seno`, `tirar` y `cortar`. `vueltas` es lo mismo que `vuelta-<n>` y `seno-vueltas` que `seno-vuelta-<n>`. Cada paso llega más lejos que el anterior y el último llega a `cortar`. En el texto, `{vueltas}` sale en letras.

Lo que hace la plantilla (`nudos/plantillas/refuerzo.py`; ver «El cabo y el refuerzo de cabo» en el plan):

- **Las vueltas** van a 1,1 una de otra, hacia la punta, y por delante del cabo bajan. El seno va de frente a la cámara de los pasos: sus ramas a 7 diámetros de arco una de otra, el extremo corto a 106° y la rama que vuelve a −16°, con una curva plana de esquinas de radio 1,2.
- **Al pasar el chicote,** la última vuelta pasa otra vez sobre la rama que vuelve y el chicote gira hacia la punta en el medio del seno, pasa bajo su curva y cae a la mesa por delante del corte. Con `n` vueltas son 4n + 2 cruces.
- **Al tirar,** la curva queda apretada contra el borde de las vueltas, con el chicote enganchado y todavía a la vista; la rama que vuelve sale lo que se acortó el seno.
- **Al cortar,** el seno queda escondido bajo las vueltas de encima y el chicote, cortado, pasa bajo su curva y termina dentro de él. Es una simplificación, aprobada por Gabriel: en la cuerda real el chicote se dobla alrededor de la curva y vuelve a salir por el borde, donde se corta. Por fuera se ve igual: vueltas y la punta corta de la rama que vuelve.
- **La altura de cada tramo** sale de lo que tiene debajo: donde pasa sobre otro, va un diámetro más arriba, con subidas y bajadas suaves.
- **Los nombres:** «Chicote», en la punta del largo, desde el paso 1 hasta el de tirar; ninguno al cortar. Los dos extremos llevan remate.

### Puño de mono

```yaml
plantilla:
  tipo: puno-de-mono
  vueltas: 3
pasos:
  - {titulo: Da {vueltas} vueltas alrededor de dos dedos, texto: …, hasta: juego-1}
  - {titulo: Pasa el chicote entre los dedos, texto: …, hasta: vuelta-2-1}
  - {titulo: Da {vueltas} vueltas alrededor de las primeras, texto: …, hasta: juego-2}
  - {titulo: Pasa el chicote por dentro de las primeras, texto: …, hasta: vuelta-3-1}
  - {titulo: Da {vueltas} vueltas alrededor de las segundas, texto: …, hasta: juego-3}
  - {titulo: Haz un nudo simple y mételo en el centro, texto: …, hasta: centro}
  - {titulo: Aprieta las vueltas, texto: …, hasta: apretar}
```

| Campo | Qué es |
|---|---|
| `tipo` | `puno-de-mono`. No lleva `anfitrion`. |
| `vueltas` | Vueltas de cada juego. 3 o 4. |

El método es el de la fuente, en los dedos y sin bola en el centro: con el chicote se dan las vueltas alrededor de dos dedos parados (el primer juego); el chicote pasa entre los dedos y da otras tantas alrededor de las primeras, por la mitad (el segundo); después pasa por dentro de las primeras y da otras tantas alrededor de las segundas (el tercero), y sale por el centro, junto al firme. Se sacan los dedos, se hace un nudo simple en el chicote, se mete en el centro y se aprieta.

`hasta` puede ser, en este orden: `vuelta-1-1` … `vuelta-1-<n>`, `vuelta-2-1` … `vuelta-2-<n>`, `vuelta-3-1` … `vuelta-3-<n>`, `nudo` (el nudo simple en la mesa), `centro` y `apretar`. `juego-<j>` es lo mismo que `vuelta-<j>-<n>`. Cada paso llega más lejos que el anterior y el último llega a `apretar`. En el texto, `{vueltas}` sale en letras.

Lo que hace la plantilla (`nudos/plantillas/puno.py`; ver «El puño de mono» en el plan):

- **Los juegos** van alrededor de z (el primero, con las vueltas una sobre otra, acostado en la mesa), de x (el segundo) y de y (el tercero). Cada juego va encima de otro en dos caras opuestas y debajo del tercero en otras dos: el segundo sobre el primero en ±y, el tercero sobre el segundo en ±z y el primero sobre el tercero en ±x. Donde va encima, una vuelta va 1,05 más lejos del centro. Las vueltas de un juego van a 1,1 una de otra.
- **Suelto y apretado.** Hasta meter el nudo en el centro, el puño es un óvalo, como lo dejan los dedos; al apretar, una esfera. Los dedos no se dibujan.
- **Los cambios de juego** van por las esquinas del puño, donde no pasa ninguna vuelta, y no cruzan nada. El chicote, al final del tercer juego, entra al centro donde termina la última vuelta, entre dos caras; al terminar ese juego, cruza el centro y sale junto al firme.
- **El nudo simple** es un trébol abierto, con sus dos puntas dobladas hacia afuera. En la mesa, el chicote sale del puño y llega a él; en el centro, queda dentro del puño.
- **Los cruces:** con `n` vueltas, `vuelta-1-<k>` no tiene; `vuelta-2-<k>`, 2nk; `vuelta-3-<k>`, 2n² + 4nk, y `nudo`, `centro` y `apretar`, 6n² + 3.
- **Los nombres:** «Firme» en todos los pasos y «Chicote» mientras se ve, hasta el tercer juego. Desde que el nudo simple está en el centro, solo «Firme». Los dos extremos llevan remate.

## Pasos

| Campo | Qué es |
|---|---|
| `titulo` | Título corto, en imperativo y tuteo. |
| `texto` | Instrucción del paso, en tuteo y con texto propio. |
| `trazado` | Segmentos o tramos en el orden de la cuerda. Cada segmento aparece una sola vez. Con varias cuerdas, un mapa por cuerda (ver arriba). |
| `secuencia` | La secuencia de cruces (ver abajo). Si el paso no tiene cruces, se escribe `""`. Con varias cuerdas, un mapa por cuerda. |
| `resaltar` | Opcional. Con `desde` y `hasta` marca el tramo que se mueve en este paso. |
| `hasta` | Solo en un nudo de plantilla, en lugar de `trazado`, `secuencia` y `resaltar`: hasta dónde llega el paso (ver arriba). El tramo que se mueve es lo que agrega el paso. |

## Secuencia de cruces

Para escribirla, recorre la cuerda desde el firme y anota cada vez que pasa por un cruce: la etiqueta del cruce más `O` si pasa por encima o `U` si pasa por debajo. Por ejemplo, `1U 2O 1O 2U` dice que, desde el firme, la cuerda pasa por debajo en el cruce 1, por encima en el 2, por encima en el 1 y por debajo en el 2. El ejemplo no es de ningún nudo del libro: así sirve también para las pruebas doradas de la skill `nudo-nuevo`, que no tienen que ver las secuencias de los nudos validados.

Con varias cuerdas, cada secuencia recorre su cuerda desde su firme. Un cruce entre las dos cuerdas tiene una pasada en cada secuencia, y un cruce de una cuerda consigo misma tiene las dos en la suya.

Reglas:

- En un paso, cada etiqueta aparece dos veces, una con `O` y otra con `U`. Con varias cuerdas, dos veces entre todas.
- Cada etiqueta nombra un solo cruce en todo el nudo. Un cruce que sigue en el paso siguiente conserva su etiqueta.
- Un cruce no cambia de encima a debajo entre pasos. Si cambia, es otro cruce y lleva otra etiqueta.
- El trazado tiene que formar exactamente esos cruces, en ese orden.

## Error común

Es un paso con algunos cruces al revés: el mismo trazado, pero con otra secuencia. En la ficha va junto al mismo paso bien hecho y con el mismo encuadre. Como no es un paso del nudo, es el único lugar donde un cruce cambia de encima a debajo.

En un nudo de plantilla, el error no son cruces al revés sino una variante del método (`variante`): la plantilla calcula la cuerda de esa variante y el error es su comienzo hasta el mismo `hasta` que el paso del error. Se construye y se comprueba como un paso más, con la secuencia de cruces que la plantilla escribe para la variante, y resalta lo mismo que el paso bien hecho.

| Campo | Qué es |
|---|---|
| `paso` | Número del paso que se muestra con el error. |
| `invierte` | Etiquetas de los cruces que quedan al revés, por ejemplo `[1]`. Tienen que estar en ese paso. |
| `titulo` | Nombre corto del error. |
| `texto` | Cómo reconocerlo y qué hacer, en tuteo y con texto propio. |
| `variante` | Solo en un nudo de plantilla, en lugar de `invierte`: el error del método que la plantilla sabe construir. El amarre cuadrado y el diagonal tienen `ahorcados-por-fuera` (por encima del palo de arriba, en lugar de entre los palos), que se ve desde `ahorcado-1`. Sus ahorcados cruzan las mismas esquinas que los bien hechos, porque por donde pasan el palo de arriba no cruzan nada; lo que cambia es por qué lado del palo pasan. La cabeza de turco de 3 cabos tiene `empieza-por-encima`: en la tercera vuelta, la cuerda empieza a tejer por encima en vez de por debajo y sigue alternando, así que todos los cruces de esa vuelta quedan al revés. Se ve desde `vuelta-3-mitad`. Con otro número de cabos no hay variante. El amarre redondo y el trípode tienen `sin-ahorcados`: después de las vueltas, la cuerda va directo al ballestrinque de cierre. Se ve desde `cierre-1`; hasta las vueltas es la misma cuerda, y en el error los hitos de los ahorcados son lo mismo que la última vuelta. El refuerzo de cabo tiene `por-fuera-del-seno`: el chicote pasa por encima de la curva del seno en vez de por dentro, así que el seno sale sin arrastrarlo. Se ve desde `por-el-seno` y solo en ese paso. El puño de mono tiene `tercero-por-fuera`: el tercer juego pasa por fuera del primero, alrededor de todo el puño, en vez de por dentro, así que sus 2n² cruces con el primero quedan al revés. Se ve desde `vuelta-3-1` y solo en el tercer juego. |
| `encuadre` | Opcional. Zona que se muestra del error y del paso correcto, como el `encuadre` del nudo. Conviene acercarse al cruce. |
| `otros` | Opcional. Errores comunes que no se ven en una imagen, como no mantener la cuerda tensa. Es una lista; cada uno lleva `titulo` y `texto`. En la ficha van debajo del error con imagen, como «Otro error común». |

Las dos imágenes usan el `resaltar` de ese paso. Para que el error se vea, el resaltado debe empezar o terminar fuera del cruce invertido: así un tramo llega azul y el otro resaltado, y se ve cuál va encima.

## Nudo terminado

El último paso se muestra por delante y por detrás, apretado (ver «El nudo apretado», abajo). Sin anfitrión, la vista de detrás se obtiene volteando la cuerda sobre el eje y, como una página, y dejándola asentarse otra vez en la mesa. Al voltear, todos los cruces quedan al revés. Con el destorcedor es igual: se voltea con el nudo y, como está en x = 0, queda en el mismo lugar. Con la estaca también, como si la sacaras, voltearas el nudo y la volvieras a clavar. Sobre un poste el nudo no se voltea: se mira desde el otro lado de la mesa.

Sobre la cruz se voltea el amarre entero, palos y cuerda, como un marco sobre la mesa: media vuelta alrededor del eje y, como una página, hasta apoyarse en lo que queda más abajo. El palo de abajo queda encima y se ven las vueltas que pasaban por debajo de él. Es un giro rígido: la cuerda no se relaja otra vez y, como los cruces se miden respecto a los palos, la secuencia no cambia. Por delante y por detrás se mira como los pasos.

Sobre los palos paralelos es igual que sobre la cruz: los palos y la cuerda se voltean juntos como una página, con media vuelta alrededor del eje y, y se apoyan en lo más bajo. Siguen a lo largo de x y el de delante sigue delante; se ven los ahorcados bajo las vueltas y la parte de atrás de los ballestrinques. La ficha dice: «Por detrás es como lo ves si volteas los palos juntos como la página de un libro».

Sobre el cabo es igual: por delante, el refuerzo cortado, y por detrás el cabo y el cordel girados media vuelta alrededor del eje, como se gira el cabo en la mano, y apoyados otra vez en la mesa. Es un giro rígido y la secuencia no cambia. Por delante y por detrás se mira como los pasos.

En el puño de mono, que no tiene anfitrión, el nudo tampoco se voltea como un nudo libre: sus cruces se miden desde el centro del puño, así que voltearlo como una página, con media vuelta alrededor del eje y, es un giro rígido y la secuencia no cambia. El puño se apoya en lo más bajo, y el firme sale de él hacia afuera y cae a la mesa hacia atrás. Por delante y por detrás se mira como los pasos. La ficha dice la frase de los nudos sin anfitrión: «Por detrás es como lo ves si lo volteas como la página de un libro».

Sobre el tubo, por delante es el remate, girado como ese paso, y por detrás el tubo y el nudo girados media vuelta alrededor del eje, como se gira el tubo en la mano. Es un giro rígido: la secuencia no cambia y no se relaja otra vez. Entre las dos vistas se ve el nudo entero, también la parte que en la vista de los pasos queda contra la mesa. Por delante y por detrás se mira como los pasos.

| Campo | Qué es |
|---|---|
| `encuadre` | Opcional. Zona que se muestra del nudo terminado, por delante. Por detrás se usa la misma zona volteada. |

### El nudo apretado

Cada tramo del último paso conserva el largo que le dio el trazado, así que el nudo queda flojo, como cuando se termina de pasar la cuerda y todavía no se tira de ella. Además del último paso, al construir sale el nudo terminado apretado (`nudos/apretar.py`), una geometría aparte solo para sus dos vistas. Los pasos no cambian. No hace falta ningún campo: qué se aprieta lo deciden los cruces del último paso y el tipo de nudo, y las medidas están en el código.

- **Cómo sale.** La cuerda se acorta dentro del nudo, como si se tirara de sus cabos, y después de cada poco se deshacen los choques, así que ningún tramo atraviesa a otro y ningún cruce cambia. Se acorta lo que está a menos de 6 diámetros, sobre la mesa, de algún cruce del último paso. El chicote después de su último cruce no se acorta: el nudo lo arrastra. El resto, como el firme o la gaza grande del as de guía, se queda donde está, como si lo sostuvieras con las manos. Con cuerdas de distinto grosor solo se acorta la más delgada: la gruesa, que es más rígida, conserva su forma y la delgada se ajusta alrededor.
- **Mientras se aprieta, los tramos chocan a 1,12 veces la suma de sus radios.** Una cuerda que abraza a otra del mismo grosor se dobla con radio 1, así que un nudo apretado del todo quedaría al borde del límite de curvatura. Con esa holgura las vueltas quedan con radio de 0,9 o más; en una cuerda de 8 mm es 1 mm de luz.
- **Se aprieta por rondas, 30 como máximo, y cada una se comprueba como un paso:** la secuencia del último paso y los mismos límites (con un anfitrión, también la penetración). El apretado es la ronda más apretada que los cumple. Si ninguna los cumple, es el último paso tal cual, así que el apretado nunca agrega fallas.
- **Por detrás** es el nudo por detrás de siempre, el último paso volteado y relajado, apretado igual y con la secuencia invertida. Sobre el poste no hay reverso: se mira el mismo nudo apretado desde el otro lado.
- **Un nudo de plantilla no se aprieta,** porque su plantilla ya traza la cuerda tensa. El amarre terminado sigue siendo el último paso y su volteo rígido.

`modelo.json` lleva los dos aparte, en `apretado` y `reverso_apretado` (`null` donde no hay). Las dos vistas del terminado en la ficha salen del apretado (`TERMINADO_APRETADO` en `nudos/imprimir.py`): Gabriel lo eligió el 11 de noviembre de 2026 con la página de prueba, `build/mejoras/apretado.pdf` de `python -m nudos mejoras`, que compara el terminado sin apretar, a medias y apretado. Si un nudo futuro no debiera apretarse, el campo se agrega con ese nudo.

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

Del probador nunca se guarda el nombre: un campo `nombre` es un campo desconocido, y el código solo acepta letras mayúsculas seguidas de números. El rol describe a la persona sin nombrarla, como «joven de la Wak» o «dirigente».

## Estado

Cada nudo avanza así: `borrador → modelado → cuerda-ok → novato-ok → publicado`. El estado lo escribe quien trabaja el nudo, y `python -m nudos estado` y las pruebas comprueban que no diga más de lo que muestran los hechos. Cada estado pide lo del anterior y algo más:

| Estado | Qué tiene el nudo |
|---|---|
| `borrador` | La especificación. Es el estado de un borrador recién escrito y el de una especificación sin `estado`. Pasa a `modelado` cuando Gabriel revisa el borrador, y `python -m nudos estado` lo dice cuando ya tiene todo el texto. |
| `modelado` | Construye todos sus pasos sin fallas y tiene lo que la ficha necesita de la especificación: `usos`, `materiales`, `verificacion`, `precauciones`, `alternativas` y `error`. |
| `cuerda-ok` | El último filtro 1 registrado está aprobado. |
| `novato-ok` | El último filtro 2 registrado está aprobado. |
| `publicado` | Está en `publicados.txt`, así que su visor está en el sitio. |

- Vale el último registro de cada filtro: si una prueba no pasa, se corrige la ficha y se repite.
- Un mismo código hace una sola vez el filtro 2 de un nudo: si no pasa, se repite con otra persona.
- Estar en `publicados.txt` no basta para estar en `publicado`. El ballestrinque, la vuelta de escota y el amarre cuadrado tienen su visor en el sitio y siguen en `cuerda-ok`, porque el filtro 2 está en pausa desde el 9 de noviembre de 2026.
- Los 36 nudos de la edición 1 están en `config/edicion-1.yaml`, por tanda, con el slug que tiene o tendrá su especificación. Cada especificación de `specs/` tiene que estar en esa lista.

`python -m nudos estado` muestra los 36 nudos con su estado y lo que les falta para el siguiente, y los códigos del filtro 2 con los nudos que ya probó cada uno, para no repetir un probador en un nudo que ya conoce. Falla si algún nudo dice un estado que no tiene. Que el nudo construya sin fallas no lo comprueba esa orden, porque construir todos tarda minutos: lo comprueban las pruebas (`tests/test_estado.py`).

## Qué se comprueba al construir

1. La especificación cumple este formato.
2. **Consistencia entre pasos:** cada cruce conserva su encima/debajo en todos los pasos donde aparece. Así se detecta un cruce invertido en un solo paso.
3. En cada paso, después de relajar la cuerda:
   - la secuencia de cruces es la declarada; con varias cuerdas, además, cada pasada cae en la cuerda donde se declaró;
   - ningún tramo queda a menos de 0,97 diámetros de otro; con varias cuerdas, a menos de 0,97 veces la suma de los radios de los dos tramos, que es la distancia a la que se tocan;
   - el radio de curvatura no baja de 0,9 diámetros, medidos en los diámetros de cada cuerda;
   - la cuerda no se estira más de 2 %.
   - con un anfitrión, la cuerda no entra en él más de 0,05 diámetros.
4. Un cruce con la misma etiqueta no aparece a más de 2,5 diámetros de donde estaba en el paso anterior. Es una heurística para detectar una etiqueta reutilizada para otro cruce.
5. El error común y el nudo terminado por detrás se construyen como un paso más y cumplen los mismos límites. Además:
   - la secuencia del error, después de relajar, difiere de la del paso correcto exactamente en los cruces de `invierte`; en un nudo de plantilla, es la que la plantilla escribe para la variante;
   - la secuencia del nudo por detrás es la del último paso con todos los cruces al revés. El amarre volteado con sus palos no se construye otra vez: es un giro rígido del último paso.
6. El nudo terminado apretado, por delante y por detrás, tiene la secuencia del último paso (por detrás, invertida) y cumple los mismos límites. Lo garantiza cómo se elige: entre las rondas que los cumplen (ver «El nudo apretado»).

**Dónde se buscan los cruces.** Sobre la mesa, en la proyección vista desde arriba: encima es lo más alto. Con el destorcedor y la estaca también, porque la cuerda no sale de la mesa. Con varias cuerdas, se buscan dentro de cada una y entre ellas, nunca en el salto entre el final de una cuerda y el comienzo de la siguiente. Sobre el poste, en su superficie desenrollada (x y el arco alrededor del eje, comparando cada par en la vuelta más cercana): encima es lo más lejos del eje. Sobre el tubo y el cabo, igual, en la superficie desenrollada del cilindro. Un tramo cuenta como «sobre el poste» si sale de un segmento sobre el poste. Los cruces entre un tramo del poste y uno de la mesa no se buscan; ahí solo se comprueba la separación.

Sobre los palos paralelos hay una zona por palo, otra por cada hueco entre dos palos, los costados de los ahorcados y la mesa. En cada palo los cruces se buscan en su superficie desenrollada, como en el poste: ahí van los ballestrinques y los arcos de las vueltas. En cada hueco, en la superficie de un cilindro acostado a lo largo de y, con el eje en el medio de las vueltas (x = 0) a la altura de los ejes de los palos, como la cintura de la cruz acostada: ahí van las rectas de las vueltas que pasan de un palo al otro por encima y por debajo del hueco, y las partes de los ahorcados que pasan sobre y bajo ellas. Encima es lo más lejos del eje. Donde los ahorcados bajan por el hueco, uno junto a otro a lo largo de x, no se buscan cruces: es una zona sin mapa, y ahí solo se comprueba la separación.

Sobre el tubo de la cabeza de turco es igual: hay dos zonas, el tubo, con la parte tejida, y la mesa, con el extremo corto que cuelga y el resto hasta que llegan al nudo. Los cruces del tubo se buscan en su superficie desenrollada, y cada uno guarda su lugar en el mapa del nudo (a lo largo del tubo y alrededor, desde el seno A) y no en la mesa: como el nudo se gira entre pasos, en la mesa un mismo cruce se movería. Alrededor del tubo, ese lugar da la vuelta a mitad de camino entre dos cruces, donde no hay ninguno. Dos pasadas de una misma cuerda a menos de 3 diámetros a lo largo de ella no cuentan como cruce: ahí la cuerda no puede volver sobre sí misma, y vista desde arriba, donde cae casi vertical al costado del tubo, se pliega sobre sí misma al relajar.

En el puño de mono, sin anfitrión, hay tres zonas. Las vueltas se buscan en el puño desenrollado: cada punto se mira desde el centro del puño, y su dirección se proyecta desde la esquina opuesta al polo (proyección estereográfica). El polo va por dos esquinas opuestas del puño por donde no pasa nada, así que el mapa no tiene costura. Encima es lo más lejos del centro. El nudo simple, dentro del puño, se busca mirándolo desde su cara de arriba, y la mesa, desde arriba, como siempre. Lo que va de una zona a otra, como el chicote que entra al centro o lo que sale del puño y cae, no entra en ningún mapa. Cada cruce de las vueltas guarda su lugar en la cara del puño más cercana, en diámetros, y los del nudo simple, en el marco del nudo, así que un cruce queda en el mismo lugar con el puño suelto y apretado, y con el nudo en la mesa y en el centro.

**Lo que no se comprueba es si la secuencia corresponde al nudo correcto.** Un cruce mal leído que se repite igual en todos los pasos pasa todas las pruebas. Para eso está el filtro 1: atar cada paso con cuerda real antes de publicar.

## Versiones

Este es el formato v1.8. La versión 1 se congeló el 11 de noviembre de 2026, en el Punto de control B del plan, con los cuatro nudos publicados del piloto: el as de guía, el ballestrinque, la vuelta de escota y el amarre cuadrado. Desde entonces cambia solo de dos maneras:

- **Un cambio compatible** agrega algo que ninguna especificación usa todavía: un tipo de anfitrión, una plantilla, una variante de error, un campo opcional o un valor nuevo de un campo. Toda especificación anterior se carga igual y da el mismo `modelo.json`, byte a byte. No lleva migración: la versión sube a 1.1, 1.2…, y el cambio se anota abajo, en el registro.
- **Un cambio incompatible** cambia algo que ya existe: el nombre, los valores, las unidades o el significado de un campo. También lo es quitar algo o volver obligatorio un campo opcional. La versión sube a 2, y el cambio lleva un script de migración en `scripts/` que reescribe todas las especificaciones de `specs/` en el mismo commit. Después de migrar, los nudos publicados dan el mismo `modelo.json`, byte a byte.

Las especificaciones no llevan número de versión: todas viven en este repositorio y se migran juntas.

El formato es lo que se escribe en la especificación. Cómo se construye el nudo a partir de ella puede mejorar sin cambiar la versión, como las mejoras del render (T7b) o el nudo apretado (T7c). Pero si cambian los pasos de un nudo publicado, es decir, su cuerda o sus cruces, su filtro 1 ya no vale y hay que repetirlo.

### Lo provisional

La cabeza de turco no entra en v1: el anfitrión `tubo`, la plantilla `cabeza-de-turco` con su variante `empieza-por-encima`, y lo que dicen del tubo «Nudo terminado» y «Dónde se buscan los cruces». Gabriel la dejó para el final del plan el 11 de noviembre de 2026, y puede cambiar cuando se retome. Hasta que se publique, cambia sin migración, porque solo la usa su especificación. Al publicarla entra al formato como un cambio compatible.

### Lo que se agregará

Son cambios compatibles que ya se conocen:

- `secciones`, en qué progresión de cada sección está el nudo y quién lo valora, para los anexos (T12).
- Los anfitriones que faltan (argolla, tablón, barril, cornamusa, cuerda anfitriona), con el primer nudo que los use.
- La plantilla de la tanda 4 que falta: el adujado.
- Varias cuerdas sobre un anfitrión, y cruces entre un tramo sobre un anfitrión y uno sobre la mesa.
- Nudos que se voltean sobre la mesa: voltear invierte todos los cruces, y hoy eso obligaría a usar etiquetas nuevas.

Fuera del formato, la hoja de revisión (`python -m nudos hoja` y `revision`) dibuja la cuerda y el anfitrión: el destorcedor en gris; la estaca, el poste, la cruz y los palos paralelos color madera, y el cabo color crema. El poste, los palos y el cabo se cortan en el encuadre, más un margen. Del tubo de la cabeza de turco y del cabo del refuerzo dibuja además su superficie desenrollada, con cada cruce, y del puño de mono, el puño desenrollado mirado desde su centro. La vista inclinada se centra a la altura de la cuerda, la misma en todos los pasos, para que un nudo sobre el poste no salga del cuadro.

### Registro

- **v1** (11 de noviembre de 2026; Gabriel lo aprobó en el Punto de control B, con la cabeza de turco provisional): el formato de los cuatro nudos del piloto. Desde v0, que era el del as de guía en T1, se agregaron el error común y el nudo terminado (T3), el texto de la ficha y `filtros` (T4), el anfitrión y el poste (T5), las varias cuerdas (T6), `alternativas` y `precauciones` (T6b), y la cruz, las plantillas, `hasta` y el error con `variante` y `otros` (T7).
- **v1.1** (11 de noviembre de 2026): el campo `estado` (T10). Es un cambio compatible: sin él, una especificación está en `borrador`.
- **v1.2** (12 de noviembre de 2026): el campo `dos_firmes`, para un nudo en medio de la cuerda, como la mariposa alpina (fase 4, tanda 1). Es un cambio compatible: sin él, la cuerda termina en un chicote, como antes, y los nudos publicados dan el mismo `modelo.json` y las mismas imágenes.
- **v1.3** (14 de noviembre de 2026): el anfitrión `destorcedor`, un cilindro corto parado sobre la mesa, para el nudo aguja (fase 4, tanda 2). Es un cambio compatible: ninguna especificación anterior lo usa, y los nudos publicados dan el mismo `modelo.json` y las mismas imágenes.
- **v1.4** (15 de noviembre de 2026): el anfitrión `estaca`, el mismo cilindro parado que el destorcedor, de madera y más alto, para el tensor ajustable (fase 4, tanda 3). Es un cambio compatible: ninguna especificación anterior lo usa, y los nudos publicados dan el mismo `modelo.json` y las mismas imágenes.
- **v1.5** (16 de noviembre de 2026): la plantilla `amarre-diagonal`, con sus hitos y la variante `ahorcados-por-fuera`, y con ella la cruz con dos capas de cuerda bajo el palo de abajo (fase 4, tanda 4). Es un cambio compatible: ninguna especificación anterior la usa, y los nudos publicados dan el mismo `modelo.json` y las mismas imágenes.
- **v1.6** (16 de noviembre de 2026; entró a `main` el 17, después del amarre diagonal): el anfitrión `palos`, dos o tres palos paralelos, y las plantillas `amarre-redondo` y `amarre-tripode`, con la variante `sin-ahorcados` (fase 4, tanda 4). Es un cambio compatible: ninguna especificación anterior los usa, y los nudos publicados dan el mismo `modelo.json` y las mismas imágenes.
- **v1.7** (17 de noviembre de 2026; entró a `main` después de los palos paralelos): el anfitrión `cabo` y la plantilla `refuerzo-de-cabo`, con su variante de error `por-fuera-del-seno`, para el refuerzo de cabo (fase 4, tanda 4). Es un cambio compatible: ninguna especificación anterior lo usa, y los nudos publicados dan el mismo `modelo.json` y las mismas imágenes. Si otro anfitrión de la tanda 4 entra antes, este pasa a ser el número siguiente.
- **v1.8** (17 de noviembre de 2026; la gestora la renumera al integrar): las plantillas sin anfitrión y la plantilla `puno-de-mono`, con su variante de error `tercero-por-fuera`, para el puño de mono (fase 4, tanda 4). Es un cambio compatible: ninguna especificación anterior las usa, y los nudos publicados dan el mismo `modelo.json` y las mismas imágenes.
