---
name: nudo-nuevo
description: Escribe el borrador de la especificación de un nudo nuevo del libro de nudos del Grupo 431 a partir de sus entradas (las imágenes y la descripción de entradas/<slug>/), lo construye hasta que no tenga fallas y arma la hoja de revisión privada para que Gabriel lo revise. Úsala para modelar un nudo de config/edicion-1.yaml que todavía no tiene especificación, y en la corrida dorada de T9.
---

# Nudo nuevo

Convierte las entradas de un nudo en el borrador de `specs/<slug>.yaml`. Es el único paso del libro en que trabaja la IA, y siempre termina en la revisión de Gabriel (decisión de arquitectura 4 del plan).

Uso: `/nudo-nuevo <slug>`. El slug es el del nudo en `config/edicion-1.yaml`, que es también el nombre de su carpeta en `entradas/`.

## Antes de empezar

- Lee `CLAUDE.md` y `docs/formato-spec.md` completo. En el plan (`tasks/plan.md`), lee la tanda del nudo en la fase 4 y D1, si el nudo tiene usos con personas.
- Usa como ejemplo las especificaciones de `specs/` del mismo tipo: `as-de-guia` (libre, una cuerda), `ballestrinque` (sobre un poste), `vuelta-de-escota` (dos cuerdas) y `amarre-cuadrado` (plantilla). En una corrida dorada falta la del nudo que se prueba, y a veces otras. No las busques en el historial de git ni en ninguna otra parte (ver «Corrida dorada»).
- Las entradas están en `entradas/<slug>/` de la carpeta de A: (`A:\Scouts\06 Identidad\Diseños Propios\Libro Nudos\entradas`). En un worktree no existen: léelas desde esa ruta y corre `python -m nudos revision` con `NUDOS_ENTRADAS` apuntando a esa carpeta.
- Si `specs/<slug>.yaml` ya existe, detente y pregunta: la skill no sobrescribe un nudo.
- Los comandos van con el venv de A: (`.venv/Scripts/python -m nudos …`) y `PYTHONUTF8=1`, desde la raíz del repositorio o del worktree.
- **En un worktree, cuidado con los scripts propios.** El venv de A: tiene instalado el `nudos` de A:. `python -m nudos` desde la raíz del worktree usa la copia del worktree, pero un script que corres desde otra carpeta importa el de A:, con sus especificaciones. Corre tus scripts con `PYTHONPATH` en la raíz del worktree. En una corrida dorada, ese error deja ver las especificaciones que no tienes que ver.

## Reglas que no cambian

- **Las entradas son entrada, nunca contenido.** No copies su texto, ni traducido, ni sus imágenes, al repositorio. Todo lo que escribes en la especificación es propio.
- **El texto** va en español, en tuteo, y no usa ningún término de `config/terminos_seccion.txt`.
- **Seguridad (D1):** ningún nudo del libro sostiene, sube ni baja a una persona en actividades del grupo; los usos de rescate se explican como conocimiento, y la práctica con personas solo se hace con instructor y equipo certificados. Los amarres son la excepción: con ellos se arman construcciones a las que la gente se sube.
- **El borrador queda en `estado: borrador`.** No toques `publicados.txt`, `build/` ni ninguna otra especificación. Haz commit solo si quien te pidió el borrador lo pide, y entonces solo de `specs/<slug>.yaml`.

## 1. Lee la fuente

- Recorre las imágenes en orden. De cada una, anota qué cambió desde la anterior: qué tramo se movió y por dónde pasó. Ordénalas por lo que muestran y no por el nombre del archivo: a veces los números no siguen el orden en que se ata.
- Distingue el firme, la parte larga que no se mueve, del chicote, el extremo que trabaja.
- `info.txt` o `fuente.md` dicen para qué sirve, otros nombres y errores comunes. Úsalos para saber qué escribir, no para copiarlo.

## 2. Elige el generador

| El nudo | Cómo se escribe | Ejemplo |
|---|---|---|
| Una cuerda sobre la mesa | libre: `segmentos` y pasos con `trazado` y `secuencia` | `as-de-guia` |
| Dos cuerdas | libre con `cuerdas` | `vuelta-de-escota` |
| Alrededor de un palo o una barra | libre con `anfitrion: {tipo: poste}` | `ballestrinque` |
| Amarre cuadrado: vueltas y ahorcados regulares sobre dos palos | `plantilla: {tipo: amarre-cuadrado}` | `amarre-cuadrado` |

Si el nudo necesita algo que no existe (otro anfitrión, como una argolla, una estaca, una cornamusa, un barril u otra cuerda; otra plantilla, o varias cuerdas sobre un anfitrión), detente y no lo fuerces con lo que hay. Di en tu informe qué haría falta: es una tarea de código, como fueron T5 y T7.

## 3. Decide los pasos

- Un paso por cada cosa nueva que tiene que hacer quien ata. Casi siempre es una imagen de la fuente por paso, pero dos imágenes pueden ser un solo paso, y una imagen que solo aprieta no es un paso.
- **El primer paso prepara la cuerda, sin cruces** (Gabriel, 12 de noviembre de 2026): dónde va el firme, cuál es el chicote y cuánto chicote dejar.
- La ficha lleva bien hasta 7 pasos: seis en la página izquierda y el resto en la derecha.
- Anota en `revision/<slug>/pasos.yaml` qué imágenes usaste en cada paso y tus dudas. La hoja de revisión las pone junto a cada paso:

  ```yaml
  pasos:
    1: [imagen-01.png]
    2: [imagen-02.png, imagen-03.png]
  error: [imagen-02.png]
  dudas:
    3: El cruce 2 lo tapa la mano; lo leí en la imagen siguiente.
    error: Ninguna imagen lo muestra; lo elegí porque…
  ```

## 4. Lee los cruces

Aquí un borrador puede quedar mal sin que ninguna prueba lo note: un cruce mal leído que se repite igual en todos los pasos pasa todas las pruebas. Lee cada cruce con cuidado.

- En cada paso, busca todos los lugares donde la cuerda pasa sobre sí misma o sobre la otra cuerda, y mira cuál va encima.
- Numera los cruces 1, 2, 3… en el orden en que se forman. Un cruce conserva su número en todos los pasos siguientes, y su encima/debajo no cambia. Si en una imagen posterior parece al revés, vuelve a mirar: o lo leíste mal, o es otro cruce y lleva otro número.
- Escribe la secuencia recorriendo la cuerda desde el firme: el número del cruce y `O` si pasa por encima o `U` si pasa por debajo. Cada número aparece dos veces en el paso, una con `O` y otra con `U`.
- Si una imagen no deja ver un cruce, por una mano o una sombra, léelo en otra y anota la duda en `pasos.yaml`.
- **Una cuerda que pasa justo sobre un cruce,** como cuando tres cuerdas se tapan en un punto, no se dibuja ahí: córrela hacia el lado por donde la ves pasar en la foto. Las dos maneras de correrla pueden ser la misma cuerda real y dar secuencias distintas, así que la que vale es la de la foto. Anota cuál elegiste y por qué en las dudas. Si falta la imagen de un paso, lee sus cruces en el nudo terminado y dilo en las dudas.
- Para mirar un cruce de cerca, amplía la imagen en una copia fuera del repositorio, nunca en `entradas/`.

## 5. Traza la cuerda

- Las medidas van en diámetros de cuerda, con x hacia la derecha, y hacia el fondo de la mesa y el firme quieto (ver «Unidades y ejes» en el formato).
- Empieza por el último paso: dibuja la forma entera con los cruces separados y las curvas abiertas. Después arma los pasos anteriores reusando sus segmentos, para que un tramo que no cambia se escriba una sola vez.
- **Dibuja el nudo como en la foto, no su imagen en espejo.** El espejo da la misma secuencia y es el nudo al revés, y ninguna prueba lo nota. Comprueba que la primera vuelta gire hacia el mismo lado que en la foto.
- Cada paso resalta lo que se mueve en él (`resaltar`).
- Sigue los consejos del formato: el cruce de una cuerda gruesa sobre una delgada va en diagonal, y sobre un poste la cuerda no sube por el frente para bajar enseguida a la mesa.
- Pon un `encuadre` que muestre el nudo entero en todos los pasos.

## 6. Error común y texto de la ficha

- **El error común** es el más frecuente al atarlo, con los cruces que quedan al revés (`invierte`). Si la fuente lo dice, es ese. Si no lo dice, elige el que más probablemente comete quien lo ata por primera vez, casi siempre un cruce al revés en el paso que define el nudo, y dilo en las dudas. Su resaltado empieza o termina fuera del cruce invertido, para que se vea cuál va encima. Los errores que no se ven en una imagen van en `otros`.
- **El texto:** `usos`, `materiales`, `verificacion` (criterios que se comprueban mirando o tirando del nudo), `precauciones`, `alternativas` (con el nombre de su ficha si el otro nudo está en el libro), `seguridad` cuando aplica y `otros_nombres` cuando una sección lo llama distinto. La familia es una de las que ya usan los demás nudos, salvo que no encaje en ninguna.

## 7. Construye y corrige

`python -m nudos construir <slug>` construye cada paso, lo relaja y lo comprueba. Lee la tabla y corrige hasta que no queden fallas:

- **Secuencia distinta:** la cuerda trazada no forma los cruces declarados. Vuelve primero a la imagen. Si la leíste bien, corrige el trazado, nunca la secuencia para que coincida.
- **Separación:** dos tramos quedan muy cerca; sepáralos en ese punto.
- **Curvatura:** una curva es muy cerrada; ábrela o agrégale puntos.
- **Estiramiento:** al relajar, la cuerda se estiró o se encogió más de 2 % en algún punto, casi siempre porque tuvo que separar tramos muy apretados. Abre esa zona o dale más cuerda.
- La separación, la curvatura y el estiramiento dicen cerca de qué punto de la mesa ocurren. El nudo terminado por detrás se construye y se comprueba como un paso más, y sus fallas también cuentan: la hoja de revisión lo dibuja al final.
- **Un cruce que salta:** la misma etiqueta quedó en otro lugar en el paso siguiente; probablemente es otro cruce.

`python -m nudos hoja <slug>` y `--vista 55` dibujan todos los pasos en una imagen, para mirar rápido. Si después de varios intentos queda una falla, detente y di cuál es y qué probaste.

## 8. Hoja de revisión e informe

- `python -m nudos revision <slug>` arma `revision/<slug>/index.html`, con las imágenes de la fuente junto a cada paso y la secuencia declarada al lado de la medida. Mírala tú primero, paso por paso contra la fuente.
- Después informa: qué generador elegiste, qué imágenes van en cada paso, de qué cruces dudas, qué fallas corregiste y dónde está la hoja. Gabriel la revisa y decide si el nudo pasa a `modelado`. Sus correcciones se anotan en T9 del plan, y las que se repiten pasan a «Lo que aprendimos», abajo.

## Corrida dorada

Las pruebas doradas de T9 (`tests/test_dorados.py`) comparan lo que escribe esta skill con un nudo ya validado. La corrida se hace en un worktree sin la especificación de ese nudo, con una sesión que no la ha visto, para que la skill trabaje a ciegas.

- Trabaja exactamente como con un nudo nuevo. No leas la especificación borrada, ni en el historial de git, ni en otra rama, ni en la carpeta de A:.
- Cuando el borrador no tenga fallas, cópialo a `tests/dorados/<slug>.yaml`. Haz commit solo de ese archivo: la especificación borrada no se borra en git.

## Lo que aprendimos

Las correcciones de Gabriel que se repiten, como reglas para el borrador siguiente. Todavía no hay ninguna: en el primer borrador, el del ocho, no corrigió nada (12 de noviembre de 2026). El paso de preparar la cuerda es una decisión suya, y está en «Decide los pasos».
