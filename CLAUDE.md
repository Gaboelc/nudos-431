# Libro de nudos del Grupo 431

Es un libro de nudos impreso por ediciones para la Wak y la Tropa del Grupo Guía y Scout 431. Cada paso de cada nudo tiene un render 3D propio, y cada nudo tiene un visor 3D enlazado con QR desde su ficha. Reemplaza al manual de nudos v1.2.

**Criterio de éxito:** alguien que nunca ha hecho un nudo lo ata bien solo con la ficha impresa, sin que un dirigente le explique.

El plan está en `tasks/plan.md` y la lista de tareas en `tasks/todo.md`. Trabaja una tarea a la vez, marca lo que termines y detente en cada punto de control para que Gabriel revise. Las decisiones que siguen pendientes están en la sección «Decisiones previas» del plan.

## Comandos

Desde la raíz del repositorio, con Python 3.11 o más reciente:

- `python -m pip install -e .[dev]`: instala lo necesario.
- `python -m nudos construir <slug>`: construye y comprueba todos los pasos y escribe `build/<slug>/modelo.json`.
- `python -m nudos hoja <slug> [--vista arriba|55]`: genera la hoja de revisión en `build/<slug>/`.
- `python -m nudos sitio`: construye todos los nudos y el sitio en `build/sitio/`. Falla si algún nudo tiene fallas o si falta la página de un nudo de `publicados.txt`.
- `scripts/publicar.sh -m "Co-Authored-By: …"`: publica el sitio en la rama `gh-pages`, que es la que sirve GitHub Pages. Solo corre desde un `main` limpio y ya subido. Esa rama no se toca de otra forma.
- `python -m pytest`: corre todas las pruebas.

## Reglas

- La especificación de cada nudo (`specs/<slug>.yaml`) es la fuente de verdad. Su formato está en `docs/formato-spec.md`. Todo lo demás se genera, así que nunca edites `build/` a mano.
- Las fuentes (Animated Knots, el manual de la Tropa y cualquier otra) son entrada, nunca contenido. Viven en `entradas/`, que está fuera de git. No copies su texto ni sus imágenes al repositorio, al sitio ni al libro.
- El texto va en español, en tuteo y es propio. Las fichas no usan términos propios de una sección, como Tsurí, Trillo, Consejo de Wak o patrulla. Esos términos van solo en los anexos de cada sección.
- Cruces: cada etiqueta nombra un solo cruce en todo el nudo y conserva su encima/debajo entre pasos. Si un cruce cambia, es otro cruce y lleva otra etiqueta.
- Las pruebas automáticas no detectan un cruce mal leído si el error se repite igual en todos los pasos. Por eso el filtro 1 es obligatorio antes de publicar: Gabriel ata cada paso con cuerda real.
- De los probadores se registran solo el rol y un código anónimo, nunca nombres. La tabla que une códigos con personas vive fuera del repositorio.
- Una URL que ya tiene un QR impreso no cambia nunca. Desde T2, esas URL se registran en `publicados.txt`. Las URL tienen la forma `https://gaboelc.github.io/nudos-431/<slug>/`, así que ni el usuario de GitHub ni el repositorio se renombran.
- Seguridad: ningún nudo del libro se usa para sostener, subir o bajar a una persona en actividades del grupo. Los usos de rescate se explican como conocimiento, y la práctica con personas solo se hace con instructor y equipo certificados.
- `sitio/vendor/` tiene three.js 0.160.0 y las fuentes, con versión fija, para que el visor no dependa de servicios externos. Si alguno cambia, se actualiza `sitio/vendor/LEEME.txt`. El sitio no acepta imágenes.
- `prototipo/` contiene el prototipo original del as de guía y sirve de referencia para portar el visor (T2) y el render de impresión (T3). Se borra cuando T3 esté terminada.

## Dónde vive y cómo se trabaja

El trabajo se hace desde la app de Claude, en el proyecto Scouts, con la computadora de Gabriel vinculada. El repositorio de GitHub, [`Gaboelc/nudos-431`](https://github.com/Gaboelc/nudos-431), es la fuente de verdad: cada sesión empieza clonándolo y termina subiendo los cambios. La copia en `A:\Scouts\06 Identidad\Diseños Propios\Libro Nudos` se actualiza al final de cada sesión. Ahí también viven `entradas/` y `build/`, que están fuera de git.
