# T14b: render y video con el motor (prueba de concepto)

Rama `poc/render-motor`, sobre `poc/motor` (T14a) y con la escena de `poc/blender` (Blender 5.2,
Cycles con OptiX). Nada de esto toca `nudos/`, `render/` ni el sitio: todo vive en `poc/` y sale
a `build/poc-video/`.

## Qué hay

| Archivo | Qué hace |
|---|---|
| `cuadros_amarre.py` | Los cuadros del video del amarre: en cada cuadro, el motor asienta la cuerda de la plantilla hasta el nodo K (la mano avanza por el camino), con la tensión de atado de T14a (60 N en las vueltas, 150 N en los ahorcados). 270 cuadros en 8 procesos. |
| `cuadros_as.py` | Intento de animar el atado del as de guía con resortes hacia el paso siguiente. **No sirve**: queda como evidencia (abajo). |
| `cuadros_as_pasos.py` | El video del as de guía que sí se usa: cada paso de la ficha asentado con el motor, un fundido al siguiente y al final el terminado apretado. |
| `escena_video.py` | Renderiza en Blender los cuadros de un `.npz`, con la escena de `poc/blender/escena.py`, la vista «3d» de las fichas y un giro lento de la cámara. |
| `armar.py` | Fondo blanco, fundidos, el título de cada paso (Big Shoulders Display y Literata, las fuentes del visor, con el texto de la especificación) y ffmpeg (H.264, 30 cps). |
| `nombres.py` | «Firme» y «Chicote» sobre las imágenes de Blender, con el estilo de `render/impresion.js`, en el lugar que escribe `escena.py` (`<imagen>.anclas.json`). |
| `pagina.py` | La página de prueba: hoy (three.js) junto a Blender con el motor, en color y en gris, y cuadros de los videos. |

`poc/blender/escena.py` ahora escribe las anclas de los nombres y `poc/motor/motor.py` tiene
`Motor.objetivos` (resortes hacia un punto), que usa `cuadros_as.py`.

## Cómo se corre

Con el venv del proyecto y `PYTHONUTF8=1`, desde la raíz (el motor necesita `ipctk`, ver
`poc/motor/LEEME.md`). `B` es `blender.exe` y `R` la ruta absoluta de `build/poc-video`
(Blender guarda las rutas relativas en `C:\`).

```sh
python poc/video/cuadros_amarre.py
"$B" --background --factory-startup --python poc/video/escena_video.py -- --cuadros "$R/amarre-cuadros.npz" \
    --salida "$R/amarre-h" --anfitrion "$R/cruz.json" --ancho 1280 --alto 720 --muestras 64
python poc/video/armar.py amarre h          # y lo mismo con v: --ancho 720 --alto 1280
python poc/video/cuadros_as_pasos.py
"$B" … --cuadros "$R/as-pasos-a.npz" --caja "$R/as-pasos-a.npz" --total 438 --salida "$R/as-h-a" --orbita 0.5
"$B" … --cuadros "$R/as-pasos-b.npz" --caja "$R/as-pasos-a.npz" --total 438 --salida "$R/as-h-b" --orbita 0.5
python poc/video/armar.py as h
"$B" --background --factory-startup --python poc/blender/escena.py -- --trabajo <trabajo.json> --salida <png>
python poc/video/nombres.py <png> [--nombres chicote] --reservado <ancho> <alto>
python poc/video/pagina.py
```

## Tiempos (RTX 4070, 8 núcleos)

- Motor, amarre: 270 cuadros en 744 s (8 procesos). As de guía por pasos: unos minutos.
- Blender, 64 muestras con reducción de ruido: 1280 × 720 unos 5 s por cuadro solo en la
  tarjeta, unos 11 s con dos renders a la vez. El amarre (270 cuadros, dos formatos) tomó
  ~55 min; el as de guía (438 + 98 cuadros del fundido por formato), ~1 h 45 min por formato
  compartiendo la tarjeta.
- Una imagen de ficha a 256 muestras: 8 a 12 s.
- Los videos pesan poco: ~1,2 MB el amarre (11,5 s) y ~0,7 MB el as de guía (15,6 s).

Para 36 nudos, con dos formatos cada uno, son del orden de 30 a 50 horas de tarjeta: una
corrida de fin de semana en T19, sin tandas.

## Lo que salió bien

- **El amarre se ata solo**: la mano recorre el camino de la plantilla y el motor asienta lo
  hecho en cada cuadro, sin atravesarse, con las vueltas y los ahorcados ceñidos al palo. Los
  títulos cambian en el paso correcto.
- **Las imágenes de ficha** salen con la escena de Blender, el motor y los nombres en el estilo
  de hoy, en el mismo tamaño. En gris se leen bien los cruces.
- **El formato vertical** (720 × 1280, para redes) sale con su propia cámara, encuadrada para
  ese formato, no recortada del horizontal.

## Lo que falta o no sirve (para T15–T17)

- **Atar un nudo libre necesita planear la mano.** `cuadros_as.py` lleva la cuerda de un paso
  al siguiente con resortes: el motor no deja que se atraviese, pero el chicote se queda encima
  del tramo por el que debía pasar por debajo, y el cruce sale al revés. Una persona levanta el
  tramo o mete el chicote por debajo; eso hay que planearlo (por dónde pasa la mano y a qué
  altura) desde la secuencia declarada. Es T17. Mientras tanto, el video del as de guía muestra
  los pasos asentados con un fundido entre ellos: se entiende, pero no se ve el movimiento.
- **El ballestrinque inicial del amarre queda detrás del palo** desde la vista «3d»: en el
  paso 1 casi no se ve. El video necesita una cámara por tramo (T17), no una sola para todo.
- **El amarre va rápido**: 9 s para siete pasos. Conviene una pausa al final de cada paso y que
  la mano vaya más lenta en los cruces que importan.
- **El encuadre del as de guía** es el de todos los cuadros juntos, y el paso 1 (la cuerda
  larga) lo agranda: el nudo queda chico al final. Conviene un encuadre que acompañe al nudo.
- **«Firme» en el amarre**: la ficha de hoy no lo pone, y aquí se quitó para comparar. En T16
  los nombres deben salir de la misma regla que `render/escena.js` (`nombresDe`), no del
  primer punto que se ve.
- **El cierre del amarre** muestra un cruce más que la ficha (visto en T14a): falta revisar si
  es real o si las zonas del mapa de cruces quedaron viejas.
