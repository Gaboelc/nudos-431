# Tareas: Libro de nudos del Grupo 431

Lo pendiente. El detalle de cada tarea está en `tasks/plan.md`; lo cerrado, con sus fechas, ramas y commits, en `tasks/historial.md`. El estado de cada nudo lo da `python -m nudos estado`.

## Decisiones previas

- [x] D1 Postura de seguridad: ningún nudo sostiene, sube ni baja personas en actividades; la práctica con personas solo con instructor y equipo certificados
- [x] D2 Carta, resorte e imprenta (consecuencias en el plan)
- [ ] D3 Leyenda de los símbolos ✓, + y ★ de la Tropa (antes de T12)
- [x] D4 GitHub Pages en la cuenta personal (`Gaboelc`), repositorio público
- [x] D5 Se trabaja desde la app de Claude con la computadora vinculada
- [ ] D8 Especificaciones de la imprenta: sangrado, color y formato (antes de T13)
- [ ] D10 Render en Blender y compra de Studio in a Folder (se decide en el punto de control E, con T14b)
- [ ] D11 Pila del motor de física (se propone en T14a y se decide en el punto de control E)

## Pendientes de Gabriel

- [ ] Revisar el texto de las fichas de T5 (ballestrinque), T6 (vuelta de escota) y T6b (los tres nudos de T6b)
- [ ] Abrir el visor en un celular de gama baja y revisar que cargue y gire con fluidez (T7b; en la computadora, armar el paso más largo del amarre tarda 37 ms en vez de 20 y girar cuesta lo mismo)
- [ ] Confirmar los números ABOK: el simple (46), el arnés de hombre (153), la silla de bombero (1100), el rizo (1402), el pescador (1414), el pescador doble (294), el constrictor (la sesión puso 1249 y la fuente dice 1188), el adujado (3089) y los amarres redondo y trípode, que quedaron sin número
- [ ] El paso de preparar del ocho (abierto desde el punto de control de la tanda 1)
- [ ] Filtro 2 de todos los nudos: alguien que nunca lo ha hecho lo ata solo con la ficha impresa (en pausa desde el 9 nov); se registra en cada especificación

## Fases 1 a 3

- [x] T1 a T7c y T9 a T10, con los puntos de control 1, A, 2, B y C
- [ ] T8 Cabeza de turco (provisional; Gabriel la deja para el final del plan)
  - [ ] Al volver: ver con Gabriel qué no se entiende en las imágenes, antes de tocar la geometría
  - [ ] Error construido y `specs/cabeza-de-turco.yaml` con el texto de la ficha; la ficha cabe
  - [ ] Gabriel revisa el texto de la ficha
  - [ ] Filtro 1: Gabriel la ata con un cordón y un tubo, siguiendo la ficha impresa
  - [ ] Registrar el filtro 1 y publicar el sitio con la cabeza de turco en `publicados.txt`

## Fase 4: producción de los 30 nudos restantes

Las tandas 1 a 4 están en el sitio, en `cuerda-ok` y con el filtro 1 (32 nudos con el as de guía, el ballestrinque, la vuelta de escota y el amarre cuadrado del piloto). A todos les falta el filtro 2.


### Tanda 5: anfitriones especiales
- [x] Propuesta de diseño de los tres anfitriones, en el plan (23 nov)
- [x] Gabriel revisa la propuesta y responde sus ocho preguntas (23 nov: aprobada)
- [x] El tablón (v1.11), en una sola sesión de código con la cornamusa y el barril (23 nov: código y pruebas; Gabriel lo aprobó el mismo día)
- [x] La cornamusa (v1.12) (23 nov: código y pruebas; Gabriel la aprobó el mismo día)
- [x] El barril (v1.13) (23 nov: código y pruebas, con forma de cubeta amarilla; Gabriel lo aprobó el mismo día)
- [ ] Eslinga de barril (23 nov: Gabriel aprobó el borrador; filtro 1 aprobado el mismo día; en `cuerda-ok` y en el sitio. Falta el filtro 2, en pausa)
- [ ] Eslinga de andamio (23 nov: Gabriel aprobó el borrador; filtro 1 aprobado el mismo día; en `cuerda-ok` y en el sitio. Falta el filtro 2, en pausa)
- [ ] Vuelta de cornamusa (23 nov: Gabriel aprobó el borrador; filtro 1 aprobado el mismo día; en `cuerda-ok` y en el sitio. Falta el filtro 2, en pausa)
- [ ] Punto de control de la tanda 5

## Fase 5: render en Blender, motor de física y videos (propuesta del 23 nov)

El orden lo eligió Gabriel el 23 nov: primero las dos pruebas de concepto, en ramas que no entran a `main`; con las dos aprobadas, la implementación, probada con los nudos piloto; y al final todos los nudos a la vez, sin tandas.

- [ ] Gabriel aprueba la propuesta de la fase 5 en `tasks/plan.md`
- [ ] T14a Prueba de concepto del motor (rama `poc/motor`): las bibliotecas, la varilla, el contacto y el roce mínimos; el amarre cuadrado y el as de guía asentados; la página de prueba (L)
- [ ] Punto de control D: Gabriel aprueba la prueba del motor
- [ ] T14b Prueba de concepto del render en Blender y del video, con la cuerda del motor (rama `poc/render-motor`): la página de prueba, los nombres sobre las imágenes y los videos del amarre y del as de guía, horizontal y vertical (L)
- [ ] Punto de control E: Gabriel decide D10, D11 y la compra del paquete, y aprueba la implementación
- [ ] T15 Motor de física de la cuerda (XL)
  - [ ] T15a La pila elegida en `nudos/fisica/` y `pyproject.toml` (S)
  - [ ] T15b La varilla: estiramiento, flexión, torsión y peso, con la catenaria y la elástica (M)
  - [ ] T15c El contacto y el roce sin atravesarse (IPC y CCD), con el cabrestante y la tabla inclinada (L)
  - [ ] T15d Asentar y apretar dentro de `construir`, con los pilotos de la fase 2 y su página de prueba (L)
  - [ ] T15e Calibrar con cuerda real: Gabriel mide la cuerda y fotografía cuatro nudos apretados (S)
  - [ ] T15f `construir` usa el motor en cualquier nudo y anfitrión, comprobado con los pilotos (M)
  - [ ] T15g La sección aplastada y la torsión en el render, con T16 (M)
- [ ] T16 Las fichas se renderizan en Blender, si D10 sale a favor, probado con los pilotos (M)
- [ ] T17 Animación entre pasos con el modo «atar» del motor, con el as de guía y el amarre cuadrado de piloto (L)
- [ ] T18 Videos: horizontal en el visor y vertical para redes, con los pilotos (M)
- [ ] T19 Todos los nudos a la vez: el motor, las fichas y los videos en una sola corrida, `comparar` contra la referencia de antes, y se borran `relajar()` y `apretar()` (L)
- [ ] Punto de control de la fase 5

## Fase 6: libro y primera edición

Va después de la fase 5: las fichas del libro salen con la cuerda del motor y el render nuevo.

- [ ] T11 Material inicial: portada, "cómo leer una ficha", glosario, seguridad e índice (S, depende de D1 y la tanda 1)
- [ ] T12 Anexos de la Wak y de la Tropa (S, depende de D3 y T11)
- [ ] T13 Edición 1: PDF completo, colofón, registro de cambios, etiqueta en git e impresión (S, depende de la fase 4, la fase 5 (T19), T11 y T12)
- [ ] Punto de control final: edición 1 impresa y todos sus QR responden
