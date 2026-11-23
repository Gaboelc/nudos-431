# Prueba de concepto de la fase 6: Blender (rama `poc/blender`)

Gabriel pidió el 23 de noviembre de 2026 una prueba de concepto de la fase 6 del plan (`tasks/plan.md`): ver cómo quedan el render en Blender, la cuerda ajustada y un video, antes de decidir D10. Es código de prueba: no entra a `nudos/`, no tiene pruebas automáticas y no cambia ningún nudo. Todo lo que genera queda en `build/poc-blender/`, fuera de git.

No usa nada de Studio in a Folder: los scripts son propios.

## Cómo se corre

Desde la raíz del repositorio, con los nudos de la prueba construidos:

1. `.venv/Scripts/python poc/blender/exportar.py`: construye el as de guía, el ballestrinque y el amarre cuadrado, y escribe en `build/poc-blender/trabajos/` el mismo trabajo que hoy recibe `render/impresion.js` por cada imagen de la prueba. Así Blender dibuja exactamente lo mismo que three.js: los mismos puntos, resaltado, anfitrión, vista y tamaño.
2. Cada imagen, con Blender 5.2 sin interfaz (las rutas, absolutas: Blender no las resuelve desde el repositorio):

   ```
   blender --background --factory-startup --python poc/blender/escena.py -- --trabajo <ruta absoluta del json> --salida <ruta absoluta del png> --muestras 256
   ```

3. `.venv/Scripts/python poc/blender/apretar_amarre.py [rondas]`: aprieta el amarre cuadrado terminado (T15) y deja su trabajo; se renderiza igual que el paso 2.
4. El video: el paso 2 con `--video <carpeta> --segundos 10 --fps 30 --muestras 64` y el trabajo `amarre-cuadrado--video.json`. Después, ffmpeg junta los cuadros (ver «El video»).
5. `.venv/Scripts/python poc/blender/pagina.py`: arma `build/poc-blender/prueba.pdf`, cada imagen como sale hoy y en Blender, a su tamaño impreso (58 × 64 mm), en color y en gris.

## La escena (`escena.py`)

- **La cuerda** es un tubo por la línea central de `modelo.json`, suavizado con Catmull-Rom y con transporte paralelo, para que no se tuerza. Lleva UV: u da la vuelta a la cuerda y v avanza π diámetros por mosaico.
- **La trenza** es la de `render/escena.js` (16 hilos, 2 sobre 2, con el hilo trazador), calculada con numpy a 1024 px y usada como color y como relieve (Bump). Los colores son los de `COLORES` y `AMBAR`.
- **La luz** es la de escena.js hecha luces de área: la clave arriba a la izquierda y el relleno del otro lado, más un cielo claro. La mesa es un *shadow catcher*: la imagen sale con fondo transparente y la sombra encima, y se pone sobre blanco.
- **La cámara** es la de escena.js: 30° en vertical, la vista «3d» y el mismo encuadre iterativo de `pose()`, que centra la caja del nudo y la acerca hasta el 94 %. El encuadre coincide con el de hoy.
- **El color** va con la vista «Standard» y la exposición en −0,55. AgX lavaba el azul de la marca.
- **Lo que falta:** los nombres «Firme» y «Chicote», que hoy son HTML encima de la imagen; los anfitriones que no son poste, cruz, palos ni tubo; y la sombra de contacto de T7b, que aquí sale de la luz y no de la geometría.

## Resultados

- **Tiempo:** cada imagen de la ficha, a 300 ppp y con 256 muestras, tarda de 2,6 a 3,4 s en la RTX 4070 con OptiX, más unos 2 s de arranque de Blender. La primera vez tarda casi un minuto, porque compila los kernels. Las imágenes de un nudo salen en menos de un minuto.
- **Calidad:** la trenza tiene relieve de verdad, la luz es suave y las sombras de contacto, entre vueltas y contra los palos, salen solas. En gris los cruces se leen tan bien como hoy, una vez quitado el brillo de tela (*sheen*), que dejaba un halo claro en el borde.
- **Lo que no cambia:** la cuerda tiesa. Con la misma geometría, el amarre se ve igual de tieso, porque viene de la plantilla, no del render.
- **El amarre apretado (T15):** `apretar()` de `nudos/apretar.py` sirve para un amarre si se le pasan los cruces de la cruz (`nudos/plantillas/pasos.py`, `buscar()`), con las zonas de cada punto por su coordenada material, como hace `apretar_paso()` con el poste. Así cumple la secuencia y los límites. Pero acorta poco: un 5 % en 30 rondas y un 7 % en 200, donde la curvatura llega al límite. Las esquinas se redondean, pero las vueltas no se juntan ni los ahorcados las aprietan hacia el centro. Para eso, T15 tiene que cambiar la plantilla: trazar las vueltas juntas y los ahorcados tirando de ellas, y no solo acortar sin cruzar.
- **El video:** 10 s a 30 cuadros en 1280 × 720 y 64 muestras tardan 19 minutos (3,8 s por cuadro). Queda en `build/poc-blender/amarre-cuadrado.mp4`, de 1,1 MB. El vertical (`amarre-cuadrado-vertical.mp4`, 1080 × 1920) es un recorte del horizontal y corta el amarre: para redes hay que renderizarlo con su propia cámara vertical. Para juntar los cuadros sobre blanco:

  ```
  ffmpeg -framerate 30 -i video/cuadro-%04d.png -filter_complex "color=white:s=1280x720:r=30[f];[f][0:v]overlay=shortest=1,format=yuv420p" -c:v libx264 -crf 18 -movflags +faststart amarre-cuadrado.mp4
  ```

  La cuerda del amarre avanza por su camino (un material la vuelve transparente más allá del largo de cada cuadro) y la cámara gira despacio. En un nudo de plantilla, cada paso es un comienzo más largo de la misma cuerda, así que esta animación ya es correcta. En un nudo libre no alcanza: la cola cambia de forma entre pasos (T17).
