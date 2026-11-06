# Tareas: Libro de nudos del Grupo 431

El detalle de cada tarea (criterios, verificación y archivos) está en `tasks/plan.md`.

## Decisiones previas

- [x] D1 Postura de seguridad: ningún nudo sostiene, sube ni baja personas en actividades; la práctica con personas solo con instructor y equipo certificados
- [x] D2 Carta, resorte e imprenta (consecuencias en el plan)
- [ ] D3 Leyenda de los símbolos ✓, + y ★ de la Tropa (antes de T12)
- [x] D4 GitHub Pages en la cuenta personal (`Gaboelc`), repositorio público
- [x] D5 Se trabaja desde la app de Claude con la computadora vinculada
- [ ] D8 Especificaciones de la imprenta: sangrado, color y formato (antes de T13)

## Fase 1: el as de guía de principio a fin

- [x] T1 Repositorio y especificación v0 con el as de guía
- [x] Repositorio público `Gaboelc/nudos-431` creado y T1 subida
- [x] T2 Escena 3D compartida y visor publicado en su URL permanente (M, depende de T1 y del repositorio)
  - [x] Escena compartida, página del visor, `python -m nudos sitio`, `publicados.txt` y pruebas
  - [x] Revisado en Chrome de escritorio y en celular emulado, sin errores ni pedidos fuera del sitio
  - [x] Sitio subido a la rama `gh-pages`
  - [x] Gabriel activa GitHub Pages: Settings → Pages → Deploy from a branch → `gh-pages` / `(root)`
  - [x] La dirección responde y el visor carga en Chrome como celular, sin errores
  - [x] Gabriel abre https://gaboelc.github.io/nudos-431/as-de-guia/ en su celular y revisa los 7 pasos
- [x] Punto de control 1: la especificación reproduce el prototipo y el visor está en línea
- [ ] T3 Imágenes de impresión, error común y vistas finales (M, depende de T2)
- [ ] T4 Ficha impresa del as de guía con QR (M, depende de T3, D1 y D2)
- [ ] Punto de control A:
  - [ ] La suite pasa
  - [ ] El as de guía pasó los dos filtros
  - [ ] Decisión entre three.js y Blender para la impresión
  - [ ] Revisión contigo

## Fase 2: piloto por tipo de nudo

- [ ] T5 Objeto anfitrión con el ballestrinque sobre poste (M, depende de T4; es el mayor riesgo técnico)
- [ ] T6 Dos cuerdas con la vuelta de escota (M, depende de T4; puede ir en paralelo con T5)
- [ ] Punto de control 2: el anfitrión funciona; si no, los enganches pasan a plantillas
- [ ] T7 Plantilla del amarre cuadrado (M, depende de T5)
- [ ] T8 Plantilla de la cabeza de turco (S, depende de T5)
- [ ] Punto de control B:
  - [ ] Los 5 nudos del piloto están publicados
  - [ ] El formato de especificación v1 está congelado
  - [ ] Revisión contigo

## Fase 3: el paso de IA y la operación

- [ ] T9 Skill nudo-nuevo, con pruebas doradas sobre el as de guía y la escota (M, depende del Punto de control B)
- [ ] T10 Estado de producción y registro de pruebas sin nombres (S, depende de T4)
- [ ] Punto de control C:
  - [ ] Un nudo nuevo salió de la skill con correcciones menores
  - [ ] Decisión sobre usar subagentes

## Fase 4: producción de los 27 nudos restantes

Cada nudo cumple la definición de terminado: pruebas automáticas, error común, imágenes, visor, ficha, filtro 1, filtro 2 y estado `publicado`.

### Tanda 1: libres, una cuerda
- [ ] Simple
- [ ] Ocho
- [ ] As de guía español
- [ ] Mariposa alpina
- [ ] Margarita
- [ ] Arnés de hombre
- [ ] Silla de bombero (requiere D1)
- [ ] Punto de control de la tanda 1

### Tanda 2: libres, dos cuerdas o dos extremos
- [ ] Rizo
- [ ] Pescador
- [ ] Nudo aguja (falta confirmar qué nudo es)
- [ ] Punto de control de la tanda 2

### Tanda 3: sobre anfitrión
- [ ] Ballestrinque doble (por confirmar si es el *rolling hitch*)
- [ ] Leñador o vuelta de braza
- [ ] Media llave y dos cotes
- [ ] Fugitivo
- [ ] Tensor
- [ ] Constrictor
- [ ] *Mooring hitch*
- [ ] Presilla de alondra
- [ ] Prusik
- [ ] Punto de control de la tanda 3

### Tanda 4: plantillas
- [ ] Amarre redondo
- [ ] Amarre diagonal
- [ ] Amarre trípode
- [ ] Refuerzo de cabo
- [ ] Adujado
- [ ] Puño de mono
- [ ] Punto de control de la tanda 4

### Tanda 5: anfitriones especiales
- [ ] Eslinga de barril
- [ ] Eslinga de andamio (requiere D1)
- [ ] Punto de control de la tanda 5

## Fase 5: libro y primera edición

- [ ] T11 Material inicial: portada, "cómo leer una ficha", glosario, seguridad e índice (S, depende de D1 y la tanda 1)
- [ ] T12 Anexos de la Wak y de la Tropa (S, depende de D3 y T11)
- [ ] T13 Edición 1: PDF completo, colofón, registro de cambios, etiqueta en git e impresión (S, depende de la fase 4, T11 y T12)
- [ ] Punto de control final: edición 1 impresa y todos sus QR responden
