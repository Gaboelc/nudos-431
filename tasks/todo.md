# Tareas: Libro de nudos del Grupo 431

Lo pendiente. El detalle de cada tarea está en `tasks/plan.md`; lo cerrado, con sus fechas, ramas y commits, en `tasks/historial.md`. El estado de cada nudo lo da `python -m nudos estado`.

## Decisiones previas

- [x] D1 Postura de seguridad: ningún nudo sostiene, sube ni baja personas en actividades; la práctica con personas solo con instructor y equipo certificados
- [x] D2 Carta, resorte e imprenta (consecuencias en el plan)
- [ ] D3 Leyenda de los símbolos ✓, + y ★ de la Tropa (antes de T12)
- [x] D4 GitHub Pages en la cuenta personal (`Gaboelc`), repositorio público
- [x] D5 Se trabaja desde la app de Claude con la computadora vinculada
- [ ] D8 Especificaciones de la imprenta: sangrado, color y formato (antes de T13)
- [ ] D10 Render en Blender y compra de Studio in a Folder (se decide con la página de prueba de T14)

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
- [ ] Eslinga de barril
- [ ] Eslinga de andamio (requiere D1)
- [ ] Vuelta de cornamusa (*cleat hitch*, sobre una cornamusa)
- [ ] Punto de control de la tanda 5

## Fase 5: libro y primera edición

- [ ] T11 Material inicial: portada, "cómo leer una ficha", glosario, seguridad e índice (S, depende de D1 y la tanda 1)
- [ ] T12 Anexos de la Wak y de la Tropa (S, depende de D3 y T11)
- [ ] T13 Edición 1: PDF completo, colofón, registro de cambios, etiqueta en git e impresión (S, depende de la fase 4, T11, T12, T15 y, si D10 sale a favor de Blender, T16)
- [ ] Punto de control final: edición 1 impresa y todos sus QR responden

## Fase 6: render en Blender, cuerda que se ajusta y videos (propuesta del 23 nov, por aprobar)

El orden lo eligió Gabriel: la prueba, la cuerda, las fichas y los videos.

- [ ] Gabriel aprueba la propuesta de la fase 6 en `tasks/plan.md`
- [ ] T14 Prueba de Blender: `render/blender/escena.py` y `python -m nudos prueba-blender`, la página de prueba en color y en gris (M)
- [ ] Gabriel imprime la prueba y decide D10
- [ ] T15 La cuerda se ajusta en las plantillas: el diseño como bloque del plan, la aprobación de Gabriel y el código (L)
- [ ] T16 Las fichas se renderizan en Blender y se rehacen todas, si D10 sale a favor (M)
- [ ] T17 Animación entre pasos, con el as de guía y el amarre cuadrado de piloto (L)
- [ ] T18 Videos: horizontal en el visor, vertical para redes (M)
- [ ] Punto de control de la fase 6
