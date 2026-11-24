# Prueba de concepto de T15: la cuerda tiesa (rama `poc/cuerda-ajustada`)

Gabriel pidió el 23 de noviembre de 2026 una prueba de concepto de T15: ver cómo se arregla que los amarres se vean tiesos, sobre todo al ahorcar. Sale de la rama `poc/blender` y usa su escena (`poc/blender/escena.py`) para dibujar. Es código de prueba: no cambia `nudos/` ni ningún nudo. Lo que genera queda en `build/poc-cuerda/`, fuera de git.

## Dos caminos probados

### 1. Apretar el amarre ya trazado (`apretar.py`): no alcanza

`nudos/apretar.py` sirve para un amarre si se le pasan los cruces de la cruz, con la zona de cada punto por su coordenada material (ver `poc/blender/LEEME.md`). Lo probado:

| Variante | Resultado |
|---|---|
| Como está | 7 % menos de cuerda en 45 rondas; después, la curvatura del ballestrinque de inicio pasa el límite. |
| Todo el amarre como «nudo» (`--todo`) | Igual: ya lo era entero (2322 puntos de nudo, 13 de cola, 0 sujetos). |
| Tensión 0,6 | Igual de lejos; falla antes el ballestrinque de inicio: un cruce cambia de orden (`1U 2U 1O 3O` en vez de `1U 1O 2O 2U`) y una curva baja de 0,9. |
| Ballestrinques quietos, vueltas suaves (0,1) y ahorcados fuertes (0,6) (`--cincha`) | Falla en la ronda 9: al cerrarse fuerte, los ahorcados se corren sobre el ballestrinque en el mapa del palo y aparece otro cruce. Dejando quietos 40 diámetros más, igual. |

Por qué: el apretado acorta la cuerda acercando cada punto al medio de sus vecinos. Eso redondea las esquinas, pero no tira de las vueltas ni hace que los ahorcados las junten. Y en un amarre, cualquier corrimiento grande cambia los cruces, que se miden en los mapas de los palos. Lo más que da sin fallas es un 7 %, y apenas se nota.

### 2. Cambiar las medidas de la plantilla (`plantilla.py`): funciona

La plantilla (`nudos/plantillas/amarre.py`) ya traza las vueltas tensas, por la tangente de cada palo. Lo tieso sale de sus medidas, elegidas con margen en T7: escalones y separaciones de más, y esquinas de radio 1,3 que dejan los ahorcados como polígonos. `plantilla.py` las cambia para una corrida y construye el amarre cuadrado con todas las comprobaciones de siempre.

| Medida | Hoy | v2 | Qué es |
|---|---|---|---|
| `RADIO_ESQUINA` | 1,3 | 3,5 | Radio con que se redondean las esquinas entre dos rectas, sobre todo las de los ahorcados. |
| `ESCALON` | 1,0 | 0,25 | Delante, cuánto más alto sube cada esquina que la vecina. |
| `HOLGURA` | 1,05 | 1,0 | Delante, entre el ballestrinque de inicio y la vuelta más cercana. |
| `ABRIR` | 0,4 | 0,15 | Cuánto se apartan, a media altura, dos esquinas vecinas. |
| `PASO_VUELTAS` | 1,1 | 1,02 | Entre dos vueltas vecinas sobre un palo. |
| `CARRIL` | 1,1 | 1,02 | Entre los carriles de un ballestrinque. |
| `LIBRE` | 1,08 | 1,02 | Lo que deja un ahorcado entre él y cualquier otro tramo. |
| cintura (nueva) | 0 | 0,3 | Cada esquina de una vuelta se mete hacia el eje del cruce a media altura, como al ahorcarla. |

- **La v2 construye sin fallas.** La cuerda baja de 466,5 a 451,1 diámetros; la separación mínima queda en 0,990 y la curvatura en 1,110.
- **La topología es la misma:** las secuencias de los siete pasos y la del error son idénticas a las de hoy, así que el filtro 1 del amarre sigue valiendo.
- **Se nota con los dos renders:** en Blender y en el de hoy (three.js), los ahorcados quedan redondos y pegados al haz, y las vueltas, juntas. Las imágenes, en `build/poc-cuerda/render/` y `build/poc-cuerda/threejs/`.
- **El límite:** la cintura no pasa de 0,3. Los ahorcados pasan bajo el palo de arriba justo por fuera de donde las esquinas tocan los palos, y su camino es la envolvente convexa de las esquinas (`_cadena`). Con 0,6 los puntos de paso quedan dentro de esa envolvente y la plantilla no puede trazar.

## Lo que falta para T15

1. **Las medidas de la v2 como punto de partida.** Son constantes compartidas: las usan también el amarre diagonal, el redondo y el trípode (`ahorcados_y_cierre`), así que hay que construirlos y compararlos con `referencia` y `comparar` antes de cambiarlas.
2. **Lo que la v2 no arregla: el lazo de delante.** Delante, las vueltas pasan bajo el palo de abajo por fuera del ballestrinque de inicio, a 7 a 9 diámetros del cruce, y los ahorcados tienen que rodear eso. Que las vueltas pasen por encima del ballestrinque, o que los ahorcados se metan en el ángulo entre los palos, cambia la secuencia del método (`_secuencias`): es diseño, como un bloque del plan, y pide repetir el filtro 1.
3. **La cintura de verdad:** que los ahorcados pasen más adentro y las esquinas se metan más de 0,3 pide recalcular dónde pasan los ahorcados bajo el palo de arriba (`extremos`) con las esquinas ya metidas.

## Cómo se corre

Desde la raíz del repositorio, con `NUDOS_CHROME` apuntando a Edge para las imágenes de three.js:

```
.venv/Scripts/python poc/cuerda/plantilla.py --nombre hoy
.venv/Scripts/python poc/cuerda/plantilla.py --nombre v2 RADIO_ESQUINA=3.5 ESCALON=0.25 HOLGURA=1.0 ABRIR=0.15 PASO_VUELTAS=1.02 CARRIL=1.02 LIBRE=1.02 CINTURA=0.3
.venv/Scripts/python poc/cuerda/apretar.py --paso 7 --rondas 60 [--todo | --cincha] [--tension 0.6]
```

Los trabajos quedan en `build/poc-cuerda/trabajos/`; se dibujan con `poc/blender/escena.py` como en `poc/blender/LEEME.md`.
