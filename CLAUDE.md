# Libro de nudos del Grupo 431

Es un libro de nudos impreso por ediciones para la Wak y la Tropa del Grupo Guía y Scout 431. Cada paso de cada nudo tiene un render 3D propio, y cada nudo tiene un visor 3D enlazado con QR desde su ficha. Reemplaza al manual de nudos v1.2.

**Criterio de éxito:** alguien que nunca ha hecho un nudo lo ata bien solo con la ficha impresa, sin que un dirigente le explique.

El plan está en `tasks/plan.md` y la lista de tareas en `tasks/todo.md`; los dos tienen solo lo vigente y lo pendiente. Lo cerrado (diseños, «Cómo se hizo», ramas y commits de cada tarea) está en `tasks/historial.md`: no lo leas entero, busca con `grep` el bloque de la tarea que se parece a la tuya. Al cerrar una tarea, su diseño y su «Cómo se hizo» pasan del plan al historial, y en la lista queda solo lo que falta. Trabaja una tarea a la vez, marca lo que termines y detente en cada punto de control para que Gabriel revise. Las decisiones que siguen pendientes están en la sección «Decisiones previas» del plan.

## Comandos

Desde la raíz del repositorio, con Python 3.11 o más reciente:

- `python -m pip install -e .[dev]`: instala lo necesario.
- `python -m nudos construir <slug>`: construye y comprueba todos los pasos y escribe `build/<slug>/modelo.json`.
- `python -m nudos hoja <slug> [--vista arriba|55] [--pasos 2,4-5]`: genera la hoja de revisión en `build/<slug>/`. Con `--pasos`, solo esos pasos.
- `python -m nudos diagnostico <slug> [--pasos 2,4-5] [--todo]`: construye solo esos pasos, en segundos, y dice en pocas líneas qué falla o está cerca del límite y cerca de qué punto del YAML, como `gaza[3]`. Con `--todo`, también el error común, el nudo por detrás y los apretados. Los borradores lo usan en vez de scripts propios.
- `python -m nudos ampliar <imagen> --zona x0,y0,x1,y1`: copia ampliada de una zona de una imagen de la fuente, con cuadrícula, en `revision/_ampliadas/` (fuera de git).
- `python -m nudos imprimir <slug>`: genera en `build/<slug>/impresion/` las imágenes de impresión a 300 ppp (pasos, error común junto al paso correcto y nudo terminado por delante y por detrás) y `prueba.pdf`, la página de prueba en color y en gris. Necesita Google Chrome.
- `python -m nudos mejoras`: construye los nudos de muestra y arma en `build/mejoras/prueba.pdf` la página de prueba de las mejoras del render (T7b): unas imágenes sin mejoras, con cada una y con todas, que son las de las fichas, en color y en gris. Arma también `build/mejoras/apretado.pdf`, la del nudo terminado apretado (T7c): por delante y por detrás, hoy, a medias y apretado. Necesita Google Chrome.
- `python -m nudos ficha <slug>`: genera las imágenes y arma `build/<slug>/ficha.pdf`, el pliego de dos páginas tamaño carta con QR al visor. No la genera si falta texto de la ficha en la especificación, si aparece un término de sección o si algo no cabe.
- `python -m nudos sitio`: construye los nudos de `publicados.txt` y el sitio en `build/sitio/`. Las demás especificaciones de `specs/` no salen en línea: publicar un nudo es agregarlo a esa lista. Con `--con <slug>`, agrega un nudo al sitio local para verlo antes de publicarlo; `scripts/publicar.sh` no usa esa opción. Falla si algún nudo tiene fallas o si falta un nudo de `publicados.txt`.
- `python -m nudos revision <slug>`: construye el nudo y arma en `revision/<slug>/` (fuera de git) la hoja de revisión privada de un borrador, con las imágenes de la fuente junto a cada paso y la secuencia declarada al lado de la medida. En un worktree, `NUDOS_ENTRADAS` dice dónde están las entradas.
- `/nudo-nuevo <slug>`: la skill de `.claude/skills/nudo-nuevo/` escribe el borrador de un nudo nuevo desde sus entradas y arma su hoja de revisión. El borrador queda en `borrador` hasta que Gabriel lo revisa.
- `python -m nudos estado`: muestra el estado de producción de los 36 nudos de la edición 1 (`config/edicion-1.yaml`), con lo que le falta a cada uno para el siguiente, y los códigos de los probadores con los nudos que ya conocen. Falla si algún nudo dice un estado que no tiene. Cuando un nudo avanza, actualiza su `estado` en la especificación.
- `scripts/publicar.sh -m "Co-Authored-By: …"`: publica el sitio en la rama `gh-pages`, que es la que sirve GitHub Pages. Solo corre desde un `main` limpio y ya subido. Esa rama no se toca de otra forma.
- `python -m nudos referencia <carpeta> [slug ...]`: construye a la vez los nudos de `modelado` o más (o los nombrados) y deja en `<carpeta>/<slug>/` su `modelo.json` y sus imágenes de impresión, fuera de `build/`. Conviene una carpeta fuera de A:, porque Drive bloquea borrar.
- `python -m nudos comparar <antes> <después> [--reimprimir]`: compara dos carpetas de `referencia`, los `modelo.json` byte a byte y las imágenes en RGB, y dice qué cambió y cuánto. Con `--reimprimir`, vuelve a imprimir solos los nudos con el modelo igual y alguna imagen distinta, que suele ser variación del navegador. Para comprobar que un cambio de código no mueve los nudos hechos: `referencia` desde un worktree de `main` antes del código, `referencia` con el código nuevo y `comparar`. No escribas scripts propios para esto. Edge se actualiza solo, y con otra versión todas las imágenes cambian un poco: arma las dos carpetas el mismo día (`comparar` avisa si sus versiones no coinciden).
- `python -m pytest`: corre todas las pruebas, en unos 7 minutos. Con `-n 4 --dist loadfile` (pytest-xdist), en unos 4.

## Reglas

- La especificación de cada nudo (`specs/<slug>.yaml`) es la fuente de verdad. Su formato está en `docs/formato-spec.md`. Todo lo demás se genera, así que nunca edites `build/` a mano.
- Las fuentes (Animated Knots, el manual de la Tropa y cualquier otra) son entrada, nunca contenido. Viven en `entradas/`, que está fuera de git. No copies su texto ni sus imágenes al repositorio, al sitio ni al libro.
- El texto va en español, en tuteo y es propio. Las fichas no usan términos propios de una sección, como Tsurí, Trillo, Consejo de Wak o patrulla. Esos términos van solo en los anexos de cada sección.
- Cruces: cada etiqueta nombra un solo cruce en todo el nudo y conserva su encima/debajo entre pasos. Si un cruce cambia, es otro cruce y lleva otra etiqueta.
- Las pruebas automáticas no detectan un cruce mal leído si el error se repite igual en todos los pasos. Por eso el filtro 1 es obligatorio antes de publicar: Gabriel ata cada paso con cuerda real.
- De los probadores se registran solo el rol y un código anónimo, nunca nombres. La tabla que une códigos con personas vive fuera del repositorio.
- Una URL que ya tiene un QR impreso no cambia nunca. Desde T2, esas URL se registran en `publicados.txt`. Las URL tienen la forma `https://gaboelc.github.io/nudos-431/<slug>/`, así que ni el usuario de GitHub ni el repositorio se renombran.
- Seguridad: ningún nudo del libro se usa para sostener, subir o bajar a una persona en actividades del grupo. La excepción son los amarres: con ellos se arman construcciones a las que la gente se sube, así que sus fichas no dicen lo contrario. Los usos de rescate se explican como conocimiento, y la práctica con personas solo se hace con instructor y equipo certificados.
- `sitio/vendor/` tiene three.js 0.160.0 y las fuentes, con versión fija, para que el visor no dependa de servicios externos. Si alguno cambia, se actualiza `sitio/vendor/LEEME.txt`. El sitio no acepta imágenes.

## Dónde vive y cómo se trabaja

El trabajo se hace desde la pestaña Code de la app de Claude, en la computadora de Gabriel. El repositorio de GitHub, [`Gaboelc/nudos-431`](https://github.com/Gaboelc/nudos-431), es la fuente de verdad. Su copia de trabajo es la carpeta `A:\Scouts\06 Identidad\Diseños Propios\Libro Nudos`, que es un clon de git en `main` y tiene todo: también `entradas/`, `build/` y el venv `.venv/`, que están fuera de git.

- **Al empezar:** `git pull` en esa carpeta. **Al terminar:** commit y `git push`. No hay copia aparte que actualizar.
- **Los commits** van con el autor `Gabriel León <29740351+Gaboelc@users.noreply.github.com>`, ya configurado en el clon.
- **El venv** es `.venv/`, en la raíz del repositorio. Los comandos se corren desde ahí con `.venv/Scripts/python -m …`. Si cambian las dependencias de `pyproject.toml`, se reinstala con `.venv/Scripts/python -m pip install -e .[dev]`. Si falta (por ejemplo, en un clon nuevo), se crea con `python -m venv .venv` y esa misma instalación. Esa instalación trae también `ipctk` 1.6.1, el contacto del motor de física (`nudos/fisica/`, T15), con la versión fija.
- **Esta computadora no tiene Chrome:** `imprimir`, `ficha` y las pruebas que dibujan usan Edge con `NUDOS_CHROME="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"`. Con `PYTHONUTF8=1`, la salida de `construir` no falla en Windows.
- **Construir usa todos los núcleos:** los pasos de un nudo, su error, su reverso y su apretado se relajan a la vez en procesos (`nudos/procesos.py`), con resultados idénticos byte a byte. `NUDOS_PROCESOS=1` vuelve a un solo proceso; `NUDOS_PROCESOS=n`, a n. Un script que construya nudos protege su punto de entrada con `if __name__ == "__main__":`, porque en Windows los procesos arrancan con spawn; un script leído desde stdin construye en un solo proceso. La suite construye una sola vez, al empezar, todos los nudos de `modelado` o más (`modelos` en `tests/conftest.py`).
- **Modelo y esfuerzo de cada sesión** (Gabriel, 15 y 22 nov), para gastar menos tokens:
  - Los borradores de nudos sin código nuevo arrancan con esfuerzo medio.
  - El diseño y el código de plantillas y anfitriones van con el modelo grande y el esfuerzo de siempre.
  - Las sesiones que solo leen, construyen, comparan, integran o publican van con un modelo más barato, como Sonnet.
- **Menos sesiones encadenadas** (Gabriel, 22 nov): cada sesión nueva arranca en frío y vuelve a leer `CLAUDE.md`, el plan y el código. Una tarea corta, o una que sigue a lo que una sesión ya tiene en contexto, se hace en esa misma sesión. Se abre otra solo para trabajo largo que pueda ir en paralelo, en su worktree, como el diseño de una plantilla. Las sesiones terminadas y ya integradas en `main` se archivan, para que la lista de sesiones enlazadas siga corta. `.claude/settings.json` apaga en este proyecto los plugins que no usa (datos, diseño, gestión de plugins y agent-skills).
- **Una sola sesión a la vez trabaja en la carpeta de A:.** Una sesión en paralelo trabaja en su propio worktree de git, con el venv de A: (`A:/Scouts/06 Identidad/Diseños Propios/Libro Nudos/.venv/Scripts/python`) y desde la raíz de su worktree, para que importe su copia de `nudos`. Sus cambios llegan a `main` con un merge o un rebase.
- **Google Drive respalda la unidad A: entera**, también `.git/` y `.venv/`. Si git no puede escribir un archivo porque Drive lo tiene abierto, se reintenta. Si el clon se daña, se vuelve a clonar desde GitHub: todo lo que importa está subido.
