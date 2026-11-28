# Tareas: Libro de nudos del Grupo 431

Lo pendiente. El detalle de cada tarea está en `tasks/plan.md`; lo cerrado, con sus fechas, ramas y commits, en `tasks/historial.md`. El estado de cada nudo lo da `python -m nudos estado`.

## Decisiones previas

- [x] D1 Postura de seguridad: ningún nudo sostiene, sube ni baja personas en actividades; la práctica con personas solo con instructor y equipo certificados
- [x] D2 Carta, resorte e imprenta (consecuencias en el plan)
- [ ] D3 Leyenda de los símbolos ✓, + y ★ de la Tropa (antes de T12)
- [x] D4 GitHub Pages en la cuenta personal (`Gaboelc`), repositorio público
- [x] D5 Se trabaja desde la app de Claude con la computadora vinculada
- [ ] D8 Especificaciones de la imprenta: sangrado, color y formato (antes de T13)
- [x] D10 Las fichas y los videos se renderizan en Blender; la compra del paquete no hace falta (24 nov)
- [x] D11 El motor usa `ipctk` con `numpy` y `scipy` (24 nov)

## Pendientes de Gabriel

- [ ] Revisar el texto de las fichas de T5 (ballestrinque), T6 (vuelta de escota) y T6b (los tres nudos de T6b)
- [ ] Decidir si el visor anima en 3D los pasos con los cuadros del motor, para girar el nudo mientras se ata (lo opcional de T24, después de T21; cambia la lista de tipos del sitio, decisión 7)
- [ ] Confirmar los números ABOK: el simple (46), el arnés de hombre (153), la silla de bombero (1100), el rizo (1402), el pescador (1414), el pescador doble (294), el constrictor (la sesión puso 1249 y la fuente dice 1188), el adujado (3089) y los amarres redondo y trípode, que quedaron sin número
- [ ] El paso de preparar del ocho (abierto desde el punto de control de la tanda 1)
- [ ] Filtro 2 de todos los nudos: alguien que nunca lo ha hecho lo ata solo con la ficha impresa (en pausa desde el 9 nov); se registra en cada especificación

## Fases 1 a 3

- [x] T1 a T7c y T9 a T10, con los puntos de control 1, A, 2, B y C
- [ ] T8 Cabeza de turco (provisional; Gabriel la deja para el final del plan)
  - [x] Al volver: Gabriel trajo un método plano; la propuesta está en el plan (T8 con el método plano)
  - [x] Gabriel aprueba el diseño plano y responde sus preguntas (23 nov)
  - [x] Borrador de los pasos 1 a 5 con la skill `nudo-nuevo` (esfuerzo medio); Gabriel lo aprueba (23 nov) y pasa a `modelado`
  - [ ] El paso del anillo, el terminado sin apretar y el borrado de la plantilla y el tubo, con `referencia` y `comparar`
  - [ ] Error construido y `specs/cabeza-de-turco.yaml` con el texto de la ficha; la ficha cabe (hecho con los pasos 1 a 5; falta comprobarlo con el anillo)
  - [x] Gabriel revisa el texto de la ficha (23 nov, con los pasos 1 a 5)
  - [x] Filtro 1 de los pasos 1 a 5, con la ficha de e1a2f47 (23 nov). Cuando entre el paso del anillo, Gabriel lo ata y se anota otra vez
  - [x] Registrar el filtro 1 y publicar el sitio con la cabeza de turco en `publicados.txt` (23 nov, con los pasos 1 a 5)

## Fase 4: producción de los 30 nudos restantes

Las tandas 1 a 5 están en el sitio, en `cuerda-ok` y con el filtro 1 (35 nudos con el as de guía, el ballestrinque, la vuelta de escota y el amarre cuadrado del piloto). A todos les falta el filtro 2.


## Fase 5: render en Blender, motor de física y videos (propuesta del 23 nov)

El orden lo eligió Gabriel el 23 nov: primero las dos pruebas de concepto, en ramas que no entran a `main`; con las dos aprobadas, la implementación, probada con los nudos piloto; y al final todos los nudos a la vez, sin tandas.

- [x] T14a y T14b, las pruebas de concepto del motor y del render y el video, con los puntos de control D y E (24 nov)
- [ ] T15 Motor de física de la cuerda (XL)
  - [x] T15a La pila elegida en `nudos/fisica/` y `pyproject.toml` (S) (24 nov)
  - [x] T15b La varilla: estiramiento, flexión y peso (la torsión, medida y fuera), con la catenaria y la elástica (M) (24 nov)
  - [x] T15c El contacto y el roce sin atravesarse (IPC y CCD), con el cabrestante y la tabla inclinada (L) (24 nov)
  - [x] T15d Asentar y apretar dentro de `construir` (`--motor`), con los pilotos de la fase 2 y su página de prueba (L) (24 nov)
    - [x] Gabriel revisa en papel `build/motor/prueba.pdf` (24 nov): le gustan los terminados del as de guía y del ballestrinque, los pasos casi iguales a los de hoy se ven bien y en gris se distingue. El amarre lo quiere más apretado
    - [x] Amarre cuadrado más apretado: los ahorcados apilados uno sobre otro, en una sola banda, en vez de uno al lado del otro. Gabriel aprobó la página de prueba (`build/ahorcados/prueba.pdf`) el 24 nov
    - [x] Filtro 1 del amarre cuadrado otra vez, de los pasos 4 a 7 y del terminado, con la ficha nueva: aprobado por Gabriel el 24 nov (dd48d6e), y el sitio publicado con el amarre nuevo
    - [x] Las fallas de curvatura de la vuelta de escota con el motor (radio 0,87 en el último paso, 0,85 en el error y 0,77 en el reverso), en T15f (24 nov)
  - [ ] T15e Calibrar con cuerda real: Gabriel mide la cuerda y fotografía cuatro nudos apretados (S)
    - [x] Gabriel midió la cuerda y fotografió tres nudos (25 nov); `config/cuerdas.yaml` con la cuerda medida y los pilotos con ella, sin fallas
    - [x] Punto de control: Gabriel aprobó la cuerda medida con `revision/t15e/t15e-color.pdf` (25 nov)
    - [ ] La foto del amarre cuadrado apretado
  - [x] T15f `construir` usa el motor en cualquier nudo y anfitrión, comprobado con los pilotos (M) (24 nov)
    - [x] Las mallas de todos los anfitriones, las plantillas por el motor, `referencia` y `comparar` con él, y los cuatro pilotos sin fallas (24 nov)
    - [x] Punto de control: Gabriel revisó «Cómo se hizo T15f» en el plan (24 nov)
  - [x] T15g La sección aplastada y la torsión en el render, con T16 (M) (25 nov)
    - [x] El aplastado contra la madera y entre cuerdas, y la trenza con el marco sin torsión, medidos en los pilotos (25 nov)
    - [x] Punto de control: Gabriel aprobó la página de prueba y dejó el aplastado activo (25 nov)
- [x] T16 Las fichas se renderizan en Blender, probado con los pilotos (M) (25 nov)
  - [x] `imprimir` dibuja con Blender, con la escena, la cámara y los nombres de three.js; `comparar` tolera el ruido de Cycles (25 nov)
  - [x] Punto de control: Gabriel aprobó `build/blender/prueba.pdf`: Blender se ve mejor en todos los casos (25 nov)
- [x] T17 Animación entre pasos con el modo «atar» del motor, con el as de guía y el amarre cuadrado de piloto (L) (25 nov)
  - [x] Diseño de los caminos de la mano, aprobado por Gabriel (25 nov)
  - [x] `prueba-atar`: los dos pilotos atados sin fallas y los 10 s en Blender (25 nov)
  - [x] Punto de control: Gabriel aprobó los videos de prueba (25 nov)
- [ ] T18 Videos: horizontal en 4K a 60 fps y 68 Mbps (YouTube, y una copia en 1080p en el visor) y vertical en 1080 × 1920 a 60 fps (Instagram), con los pilotos (M)
  - [x] Diseño en el plan, con el costo de render medido (25 nov)
  - [x] Punto de control: Gabriel aprobó el diseño y respondió sus cuatro preguntas (25 nov)
  - [x] `python -m nudos video` con los dos pilotos: las previas, con el audio (26 nov)
  - [x] Punto de control: Gabriel aprobó las previas corregidas (punta cerrada, remate sin codo, sin brincos al recoger) y el audio (26 nov)
  - [x] Pulir a fondo el render en Blender y el motor de física: Gabriel lo discutió el 26 nov y salió el pulido a fondo (T20 a T24, abajo)
  - [ ] Los pilotos en 4K y su video en el visor pasan a T22, con el aspecto y la estructura nuevos. Quedan sin efecto el render de los pilotos con el código de hoy y la medida del umbral 0,01 contra el 0,03
  - [x] Quitar el modo video viejo de `render/blender/escena.py` (en T20b, 26 nov)
- [ ] **El pulido a fondo** (propuesta del 26 nov, aprobada el mismo día; el diseño está en el plan)
  - [ ] T20 El aspecto: material, escena, luz y cámara (L; sesión «el aspecto»)
    - [x] T20a El cuadro final en cuatro aspectos, con Cycles y EEVEE y su costo (`prueba-aspecto`, `build/aspecto/prueba.pdf`) (26 nov)
    - [x] Punto de control: Gabriel eligió la cuerda real en el estudio (paso a paso y errores) y en el campamento J&E Gray 02 (apertura, aplicación y cierre), con Cycles a 16 muestras (26 nov)
    - [x] T20b El aspecto elegido en los videos (`nudos/aspecto.py`, `render/blender/video.py`), sin el modo video viejo de `escena.py`, y la prueba de 10 s en 4K (`video <slug> --prueba`) (26 nov)
    - [x] Punto de control: Gabriel aprobó la prueba de 10 s en 4K del as de guía (26 nov)
    - [x] Gabriel decidió el costo del render (27 nov): los videos a 60 fps con EEVEE a 32 muestras. Lo eligió con el mismo cuadro del video en Cycles 16, EEVEE 16 y EEVEE 32: unos 3,3 s por cuadro de 4K y unos 11 días para los 36, contra 19 a 25 con Cycles 16. Las fichas siguen en Cycles
    - [ ] La prueba de 10 s en 4K con EEVEE 32
    - [x] T20c Las fichas: Gabriel decidió que no hace falta (26 nov); las fichas quedan como están
  - [ ] T21 El motor al atar: largo fijo, manos que agarran y gravedad en lo que cuelga (XL; la sesión del plan)
    - [x] T21a Medir el movimiento de hoy: `python -m nudos calidad` (`nudos/fisica/calidad.py`), con la medida de los dos pilotos en el plan (26 nov)
    - [x] Punto de control: Gabriel aprobó el diseño de T21, con la medida y la meta (27 nov)
    - [x] T21b Las poses de video y el largo fijo (`animar.poses_video`, 27 nov)
    - [x] T21c La guía nueva con el as de guía (27 nov): la mano que agarra, lo suelto con su peso, el tiempo de quinto grado y una manera de atar por paso: la gaza pequeña volteando una bolsa (2), la mano que acerca el chicote (3), la cinta (4 y 7), el barrido (5) y el lazo (6); la cuerda de más espera en una bolsa dentro del nudo. La previa dura 40,5 s, sin brincos, picos ni temblores, con 12 paradas en seco de la punta, y la prueba de 10 s en 4K es del paso 4. El detalle está en «Cómo se hizo T21b y T21c» del plan
      - [x] Punto de control: Gabriel aprobó la previa y la prueba en 4K (27 nov). Antes pidió que la cuerda de más no subiera en diagonal en el paso 3 y que la cola no se enrollara en el paso 5, y le encantó el paso 4, con la cámara que se aleja y la gaza que se recoge
    - [ ] T21d La madeja, con el amarre cuadrado; prueba de 10 s y punto de control
    - [ ] T21e El error y la aplicación
  - [ ] T22 El video completo: capítulos, guion, cámara, tarjetas, errores, aplicación y reel (L)
    - [x] Borrador del guion hablado de los dos pilotos (`config/guion/`) y su prueba (`prueba-guion`), a pedido de Gabriel, para que la voz suene natural (27 nov)
    - [x] Gabriel oyó el primer borrador: le gustó, pero la apertura sonaba a youtuber, no dice diminutivos ni «así», y los puntos suspensivos estiraban palabras. Segunda versión, con el estilo en el plan y las tomas sin titubeos (27 nov)
    - [x] Gabriel no quiere comparaciones («como un ojo», el conejo): tercera versión, sin ellas (27 nov)
    - [x] Gabriel aprobó el estilo del guion hablado con la tercera versión de los dos pilotos (27 nov): las reglas están en el plan, en el guion de T22a, y valen para los guiones de los 36 nudos
    - [x] T22a El diseño en el plan, el guion de los tres pilotos en su especificación (formato v1.14), la hoja `guion <slug>` y la maqueta de las tarjetas (`prueba-tarjetas`) (27 nov)
    - [ ] Punto de control de T22a: Gabriel aprueba el diseño y decide si los capítulos quietos van sobre un cuadro quieto (con EEVEE a 32 y la duración libre, los 36 son unos 16 días de render, y unos 13 con los cuadros quietos)
      - [x] Gabriel eligió las tres aplicaciones (el cabo de un toldo en un poste, la mesa del campamento y la repisa en la cocina) y que en ellas el nudo se tense y aguante (27 nov)
      - [x] Gabriel decidió que la duración no limita: el video dura lo que haga falta para explicar bien, sin recortar escenas (27 nov)
      - [x] Gabriel aprobó «En la práctica» de los 36 nudos, con siete cambios suyos y «tienda de campaña» en vez de «carpa», también en las fichas de la margarita, la media llave y dos cotes y el tensor ajustable (27 nov)
      - [x] La tarjeta del paso sale y vuelve a entrar en cada paso, y el nombre «Grupo Guías y Scouts Huetares 431» con el logo del grupo van en la apertura, en el cierre y en la ficha (Gabriel, 28 nov)
      - [x] Gabriel eligió la paleta «Huetares», la del logo del grupo, y no quiso el logo en la esquina (28 nov)
      - [x] Gabriel aprobó el guion del as de guía (28 nov)
    - [ ] T22b La implementación y la previa entera de los tres pilotos; punto de control
    - [ ] Los tres pilotos en 4K y en vertical; punto de control
  - [x] T23 El sonido (26 y 27 nov): la voz de Gabriel clonada como de estudio (Qwen3-TTS desde su muestra del DJI, con Sidon; la muestra, fuera de git en `entradas/_voz/`), cinco canciones compuestas en código con el motivo en celesta, el foley del motor y la mezcla a −14 LUFS (`nudos/voz.py`, `musica.py`, `foley.py`, `mezcla.py`; `prueba-voz`, `prueba-musica`, `prueba-mezcla` y `prueba-voz-propia`). El detalle, en el historial
  - [x] T24 El visor (26 y 27 nov): material físico, RoomEnvironment, AgX con contraste, oclusión ambiental con la cámara quieta y lygia (`sitio/fisico.js`), publicado en el sitio. Gabriel lo abrió en la computadora y en un celular de gama baja, y todo anduvo bien (27 nov). El detalle, en el historial
  - [x] Borrar los cuadros del as de guía en `%LOCALAPPDATA%\nudos\cuadros` (con permiso de Gabriel, 27 nov): los 1080 viejos del 25 nov (35,9 GB) y los 585 de la prueba de 10 s (14,6 GB). Quedan los `atado` de los dos pilotos
- [ ] T19 Todos los nudos a la vez: el motor, las fichas y los videos en una sola corrida, `comparar` contra la referencia de antes, y se borran `relajar()` y `apretar()` (L). Antes, los guiones, las voces y la música de los 36 (la tabla de aplicaciones ya está aprobada, en T22a)
- [ ] Punto de control de la fase 5

## Fase 6: libro y primera edición

Va después de la fase 5: las fichas del libro salen con la cuerda del motor y el render nuevo.

- [ ] T11 Material inicial: portada, "cómo leer una ficha", glosario, seguridad e índice (S, depende de D1 y la tanda 1)
- [ ] T12 Anexos de la Wak y de la Tropa (S, depende de D3 y T11)
- [ ] T13 Edición 1: PDF completo, colofón, registro de cambios, etiqueta en git e impresión (S, depende de la fase 4, la fase 5 (T19), T11 y T12)
- [ ] Punto de control final: edición 1 impresa y todos sus QR responden
