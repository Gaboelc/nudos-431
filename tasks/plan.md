# Plan de implementación: Libro de nudos del Grupo 431

## Resumen

Un solo libro de nudos para la Wak y la Tropa del Grupo 431, impreso por ediciones, que reemplaza al manual v1.2. Cada nudo es una especificación de datos. De ella salen la geometría 3D, las imágenes de impresión, el visor web y la ficha del PDF. La IA interviene en un solo paso, que es convertir las imágenes de referencia en un borrador de especificación. Cada ficha pasa dos filtros humanos antes de publicarse. La primera edición lleva 36 nudos: eran 35 hasta que el pescador pasó a dos fichas, el 13 de noviembre de 2026.

**Ubicación:** el repositorio es [`Gaboelc/nudos-431`](https://github.com/Gaboelc/nudos-431). La carpeta `A:\Scouts\06 Identidad\Diseños Propios\Libro Nudos` es una copia que se actualiza al final de cada sesión, y es el único lugar donde viven las imágenes de `entradas/`.

## Intención confirmada

- **Éxito:** alguien que nunca ha hecho un nudo lo ata bien solo con la ficha impresa, sin que un dirigente le explique.
- **Para quién:** Tsurís y scouts de Tropa, con el mismo texto para ambos y sin simplificar.
- **Ficha:**
  - Nombre, con los dos nombres cuando las secciones lo llaman distinto.
  - Familia, para qué sirve y materiales.
  - Pasos en 3D.
  - El error más común junto al correcto.
  - El nudo terminado desde dos ángulos.
  - Verificación, escrita como criterios observables.
  - Seguridad, cuando aplique.
- **Anexos:** uno por sección, con los nudos de su progresión y quién los valora.
- **Formatos:** el impreso por ediciones es el principal. El digital es el PDF más un visor 3D por nudo, enlazado con QR desde la ficha. Desde el 23 de noviembre de 2026, cada nudo tendrá también un video de cómo atarlo, en su visor y en redes (fase 5).
- **Fuentes:** Animated Knots y el manual de la Tropa son entrada, nunca contenido.
- **Restricciones:**
  - No hay fecha límite.
  - Los QR se mantienen estables entre ediciones.
  - Las fichas no usan términos propios de ninguna sección.
  - Una fuente nueva no obliga a cambiar el flujo.
- **Fuera de alcance:**
  - Material de las fuentes dentro del libro.
  - Una app con 3D que funcione sin conexión.
  - Venta o distribución fuera del grupo.
  - Versiones simplificadas por edad.

## Decisiones de arquitectura

1. **La especificación de cada nudo es la fuente de verdad.** Hay un archivo YAML por nudo en `specs/`, y todo lo demás se deriva de ahí. Una edición nueva es volver a construir el libro. Una fuente nueva solo cambia cómo se escribe la especificación.
2. **La topología se declara y se prueba.** Cada paso declara su secuencia de cruces, es decir, qué tramo pasa por encima en cada cruce. Después de relajar la geometría, una prueba recalcula esa secuencia y la compara con la declarada. Es la única prueba que detecta un encima/debajo equivocado.
3. **Hay dos tipos de generadores.**
   - **Libre:** del trazado y la secuencia de cruces sale el modelo 3D, que luego se relaja con física simple. Así funciona el prototipo del as de guía, y se amplía a varias cuerdas y a objetos anfitriones.
   - **Plantilla:** genera vueltas regulares a partir de medidas. Sirve para los amarres, la cabeza de turco, el puño de mono, el adujado y el refuerzo de cabo.
4. **La IA trabaja en un solo paso y con revisión.** Convierte imágenes y descripción en un borrador de especificación. Nada se procesa en lote sin revisión antes del Punto de control C.
5. **Una sola escena 3D sirve para el visor y para la impresión.** La escena three.js del prototipo genera también las imágenes de impresión con Chrome sin interfaz. Si la página impresa no se lee bien, la alternativa es Blender con la misma geometría. Se decide en el Punto de control A.
6. **El libro se arma en HTML/CSS y se exporta a PDF con Chrome.** Reemplaza el armado con `docx` del v1.2. Usa las mismas herramientas que el visor y da control fino del diseño impreso. A cambio, ya no se edita en Word: los cambios se hacen en las especificaciones y las plantillas.
7. **Los visores viven en direcciones permanentes.** El sitio se publica en GitHub Pages bajo `/<slug>/`. Un slug que ya tiene un QR impreso no cambia nunca, y una prueba lo vigila contra `publicados.txt`.
   - El sitio se construye en la sesión y `scripts/publicar.sh` lo sube a la rama `gh-pages`, siempre desde un `main` ya subido. Así lo publicado es exactamente lo que se revisó, y no hace falta GitHub Actions.
   - three.js y las fuentes van dentro del sitio, con versión fija. El visor no depende de ningún servicio externo mientras existan los QR impresos.
   - El sitio no acepta imágenes ni archivos fuera de una lista corta de tipos, y no se publica si algún nudo tiene fallas.
   - Desde el 11 de noviembre de 2026, el sitio lleva solo los nudos de `publicados.txt`: publicar un nudo es agregarlo a esa lista, así que ninguna dirección queda en línea sin estar protegida.
8. **El flujo se opera desde la app de Claude,** en conversaciones del proyecto Scouts y con la computadora de Gabriel vinculada.
   - GitHub es la fuente de verdad. Desde el 10 de noviembre de 2026, la carpeta del libro en `A:\` es un clon de git y tiene todo, también el venv (`.venv/`): cada sesión empieza con `git pull` ahí y termina subiendo los cambios (detalles en `CLAUDE.md`). Antes cada sesión clonaba el repositorio, armaba su venv y al final copiaba los cambios a `A:\`, y eso le costaba varios minutos.
   - Una skill de Claude, `nudo-nuevo`, contiene el procedimiento. Vive en el repositorio, en `.claude/skills/nudo-nuevo/`, y Claude Code la carga en cada sesión que trabaja en él.
   - Se trabaja desde la pestaña Code de la app de Claude.
   - Los subagentes en paralelo entran solo en la fase 4.
9. **Cada nudo tiene estado y registro de pruebas, sin nombres.** El estado avanza así: `borrador → modelado → cuerda-ok → novato-ok → publicado`. Cada filtro se registra con fecha, rol del probador y un código anónimo, nunca con su nombre.
10. **Las fuentes nunca entran al repositorio publicado.** La carpeta `entradas/` queda fuera de git, y el sitio y el libro se construyen solo desde las especificaciones.

## Estructura propuesta del repositorio

```
nudos-431/
  specs/            una especificación YAML por nudo (fuente de verdad)
  entradas/         imágenes de referencia por nudo (fuera de git)
  nudos/            paquete Python: especificación, cruces, generador libre,
                    anfitriones, plantillas, exportación, ficha, libro
  render/           escena three.js compartida (visor e impresión)
  sitio/            plantillas y página del visor; three.js y fuentes en sitio/vendor/
  scripts/          publicar.sh: sube el sitio a la rama gh-pages
  libro/            plantillas HTML/CSS de ficha, inicio, glosario y anexos
  config/           vocabulario controlado y términos propios de cada sección
  tests/            pruebas por nudo y del sistema
  docs/             formato de especificación y decisiones
  .claude/skills/   la skill nudo-nuevo (Claude Code la carga sola)
  publicados.txt    slugs con QR impreso (no cambian nunca)
```

Comando único: `python -m nudos <construir|imprimir|ficha|sitio|estado|libro> [slug]`.

## Grafo de dependencias

```
D5 entorno ──► T1 spec v0 + generador libre (as de guía)
                 │
  D4 hosting ──► T2 escena 3D compartida + visor publicado
                 │
                 ▼
              T3 imágenes de impresión + error común + 2 vistas
                 │
  D1, D2 ──────► T4 ficha PDF con QR
                 │
          [Punto de control A]
                 │
       ┌─────────┴──────────┐
  T5 anfitrión           T6 dos cuerdas
  (ballestrinque)        (vuelta de escota)
       │                    │
       ├─► T7 amarre cuadrado
       └─► T8 cabeza de turco
                 │
          [Punto de control B: formato de especificación v1 congelado]
                 │
  T9 skill nudo-nuevo      T10 estado y registro de pruebas
                 │
          [Punto de control C]
                 │
  Fase 4: tandas 1 a 5 (30 nudos)
                 │
  Fase 5: T14a prueba del motor ──► [D] ──► T14b prueba del render y del video ──► [E]
                 │
          T15 motor, T16 fichas en Blender, T17 animación, T18 videos (con los pilotos)
                 │
          T20 a T24, el pulido a fondo: el aspecto, el motor al atar, el video completo,
          el sonido y el visor (con los pilotos)
                 │
          T19 todos los nudos a la vez
                 │
  Fase 6:
  T11 material inicial     T12 anexos ◄── D3
                 │
  T13 edición 1
```

## Definición de terminado

### Para cualquier cambio de código

- Las pruebas nuevas fallan sin el cambio y pasan con él, y toda la suite pasa.
- El proyecto se construye desde un clon limpio con un solo comando.
- No queda código muerto ni salidas de depuración.
- La documentación de `docs/` describe el estado actual.

### Para cada nudo

- [ ] La especificación pasa el esquema y construye todos sus pasos.
- [ ] Cada paso cumple las pruebas automáticas:
  - La secuencia de cruces coincide con la declarada.
  - La separación entre tramos es de al menos 0,97 diámetros.
  - El radio de curvatura es de al menos 0,9 diámetros, salvo una excepción documentada.
  - El estiramiento no pasa del 2 %.
- [ ] El error común difiere del correcto exactamente en los cruces declarados.
- [ ] Están completas las imágenes de impresión, el visor en su URL permanente y la ficha PDF.
- [ ] La ficha está en tuteo, con texto propio y sin términos de ninguna sección.
- [ ] **Filtro 1:** tú lo ataste paso a paso con cuerda real siguiendo la ficha impresa. Queda registrada la fecha.
- [ ] **Filtro 2:** alguien que nunca lo había hecho lo ató solo con la ficha impresa. Quedan registrados la fecha, el rol y el código del probador. Si falla, se corrige la ficha y se repite con otra persona.
  - **En pausa desde el 9 de noviembre de 2026, por decisión de Gabriel.** Los nudos avanzan con el filtro 1. Mientras tanto esta definición no cambia: un nudo sin filtro 2 no llega a `publicado`. Propuesta pendiente de confirmar: retomarlo al menos una vez por tipo de nudo antes de su tanda (el ballestrinque por los nudos con anfitrión y la vuelta de escota por los de dos cuerdas), porque un problema de diseño de la ficha que solo ve un principiante se repetiría en todas.
- [ ] El estado queda en `publicado`.

## Tareas

### Decisiones previas

- **D1 Postura de seguridad (resuelta, la decidió Gabriel):**
  - Ningún nudo de este libro se usa para sostener, subir o bajar a una persona en actividades del grupo.
  - Los usos de rescate se explican para conocerlos, no para practicarlos.
  - La práctica con personas solo se hace con instructor y equipo certificados.
  - En una emergencia real, primero se llama al 9-1-1. Esto va solo en el material inicial (T11), no en cada ficha: Gabriel lo quitó de la ficha del as de guía porque sobraba.
  - La silla de bombero y la eslinga de andamio se practican sin carga o con un objeto.
  - Excepción (Gabriel, 9 de noviembre de 2026): los amarres sí sostienen personas, porque con ellos se arman torres, puentes y mesas a los que la gente se sube. Sus fichas no dicen lo contrario; sus cuidados van en `precauciones`.
  - Esta postura va en el material inicial (T11) y en la sección de seguridad de cada ficha que la necesite.
- **D2 Formato impreso (resuelta):** tamaño carta (216 × 279 mm), encuadernación de resorte e impresión en imprenta. Consecuencias:
  - El libro abierto queda plano sobre la mesa mientras se ata. Por eso cada ficha se diseña como un pliego de dos páginas, para no pasar página a mitad del nudo. Se valida en el Punto de control A.
  - Impresión a doble cara, con un margen de al menos 19 mm del lado del resorte.
  - La imprenta recibe un PDF con las fuentes incrustadas y las imágenes a 300 ppp. Las pruebas de los filtros se imprimen en casa.
- **D3 Leyenda de los símbolos ✓, + y ★** de las páginas de la Tropa, y confirmación de que son material oficial de la AGSCR. Se resuelve antes de T12.
- **D4 Hosting (resuelta):** GitHub Pages en la cuenta personal de Gabriel, con el repositorio público [`Gaboelc/nudos-431`](https://github.com/Gaboelc/nudos-431).
  - La URL de cada visor es `https://gaboelc.github.io/nudos-431/<slug>/`.
  - El nombre del repositorio queda en todos los QR, así que no se cambia.
  - Que el repositorio sea público está bien mientras `entradas/` nunca entre a git (ya está excluida) y la tabla de probadores viva fuera del repositorio.
- **D5 Entorno (resuelta):** se trabaja desde la app de Claude con la computadora vinculada (ver la decisión de arquitectura 8).
- **D8 Especificaciones de la imprenta:** sangrado, perfil de color y formato del archivo. Se resuelve antes de T13.
- **D9 Nudos por identificar y nombrar (resuelta, 9 de noviembre de 2026; incluye la que era la pregunta abierta D6):**
  - **Nudo aguja:** va el de la página 25 del manual de la Tropa, el que se ata a un destorcedor. El *needle knot* de pesca con mosca que había llegado a `entradas/` no se usa.
  - **Pescador (Gabriel, 13 de noviembre de 2026):** van dos fichas, una detrás de la otra. «Pescador» enseña el sencillo, con un nudo simple de cada cuerda alrededor de la otra, como la página 01 del manual de la Tropa. «Pescador doble» enseña el de dos vueltas, como las imágenes de Animated Knots. Lo pedía la nota de `entradas/pescador/info.txt`: primero el simple y después el doble. Una ficha no alcanza para los dos, porque el sencillo no es un paso del doble: sus cruces son otros. La edición 1 pasa a 36 nudos.
  - **Ballestrinque doble:** su entrada es la página del manual de la Tropa. Por lo que describe (la cuerda tira a lo largo del mástil), es el *rolling hitch*.
  - **El *tautline hitch* se llama «tensor ajustable»**, para no confundirlo con el tensor (*trucker's hitch*).
  - **El *mooring hitch* se llama «nudo de liberación rápida».** En el manual v0.1 era «nudo de amarre de liberación rápida»; se quitó «amarre» para no confundirlo con los amarres.
- **D10 Render en Blender (resuelta, 24 de noviembre de 2026):** las imágenes de las fichas pasan de three.js con Edge a Blender (T16), y los videos se renderizan en Blender (T18). Reemplaza la decisión de arquitectura 5 en lo que toca a la impresión; el visor sigue en three.js. La compra de Studio in a Folder no hace falta para la implementación, porque las pruebas de concepto no usaron nada del paquete: queda a criterio de Gabriel, y si lo compra, su código nunca entra al repositorio.
- **D11 Pila del motor de física (resuelta, 24 de noviembre de 2026):** `ipctk` (la barrera, la CCD aditiva con LBVH y el roce de IPC) con `numpy` y `scipy`, como en T14a. `numba` entra solo si la varilla resulta lenta, y Warp no se usa.

### Lo hecho

El detalle de cada tarea cerrada (diseño, «Cómo se hizo», ramas y commits) está en `tasks/historial.md`. No hace falta leerlo entero: busca con `grep` el bloque de la tarea que se parece a la tuya.

- **Fase 1, el as de guía de principio a fin (T1 a T4; puntos de control 1 y A):** la especificación v0, la escena 3D compartida y el visor publicado, las imágenes de impresión con el error común y las vistas finales, y la ficha con QR.
- **Fase 2, piloto por tipo de nudo (T5 a T7c; puntos de control 2 y B, 11 nov):** el anfitrión con el ballestrinque sobre el poste (T5), dos cuerdas con la vuelta de escota (T6), alternativas y precauciones (T6b), la plantilla del amarre cuadrado sobre la cruz (T7), las mejoras del render (T7b) y el nudo terminado apretado (T7c). T8, la cabeza de turco sobre el tubo, quedó provisional: Gabriel la deja para el final, y nada nuevo usa su tubo ni su plantilla.
- **Fase 3 (T9 y T10; punto de control C):** la skill `nudo-nuevo`, con su corrida dorada a ciegas, y `python -m nudos estado`, con el registro de filtros.
- **Fase 4, tandas 1 a 4 (12 a 18 nov):** 32 nudos en el sitio, en `cuerda-ok` y con el filtro 1. Entraron los anfitriones destorcedor, estaca, palos y cabo, las plantillas del amarre diagonal, el redondo, el trípode, el refuerzo de cabo, el adujado y el puño de mono, y el formato llegó a la v1.9 (la v1.10, el 23 nov, es `dos_firmes` en una cuerda, para el cordino del prusik). Gabriel cerró el punto de control de la tanda 4 el 23 nov. Desde el 17 nov, construir usa todos los núcleos (`nudos/procesos.py`), y desde el 22 nov `referencia` y `comparar` comprueban en una línea que un cambio no mueve los nudos hechos.
- **Gastar menos tokens (15 y 22 nov):** los borradores van con esfuerzo medio y usan `diagnostico` y `ampliar` en vez de scripts propios; el plan se separó del historial. Las reglas que siguen vigentes están en `CLAUDE.md`.

### Fase 4: producción de los 30 nudos restantes

Cada nudo es una tarea pequeña con la misma definición de terminado. Se trabaja por tandas agrupadas por tipo de generador, para reutilizar lo construido en el piloto.

| Tanda | Tipo | Nudos |
|---|---|---|
| 1 | Libres, una cuerda | simple, ocho, ocho doble, as de guía español, mariposa alpina, margarita, arnés de hombre, silla de bombero (requiere D1) |
| 2 | Libres, dos cuerdas o dos extremos | rizo, pescador, pescador doble, nudo aguja (el del manual de la Tropa) |
| 3 | Sobre anfitrión | ballestrinque doble (*rolling hitch*), leñador o vuelta de braza, media llave y dos cotes, fugitivo, tensor (*trucker's hitch*), tensor ajustable (*tautline hitch*, sobre una estaca), constrictor, nudo de liberación rápida (*mooring hitch*), presilla de alondra, prusik |
| 4 | Plantillas | amarre redondo, amarre diagonal, amarre trípode, refuerzo de cabo, adujado, puño de mono |
| 5 | Anfitriones especiales | eslinga de barril, eslinga de andamio (requiere D1), vuelta de cornamusa (*cleat hitch*, sobre una cornamusa) |

El ocho doble, el tensor ajustable y la vuelta de cornamusa se agregaron el 9 de noviembre de 2026: no estaban en la lista original y Gabriel los sumó a `entradas/`.

**Entradas de cada nudo.** Desde el 9 de noviembre de 2026, cada nudo tiene en `entradas/` una carpeta con el nombre de su especificación. Si hay varios métodos, cada uno va en una subcarpeta. Si la entrada es una página del manual de la Tropa, la carpeta solo tiene un `fuente.md` que dice cuál. `entradas/LEEME.md` lo explica.

| Nudo | Tanda | Carpeta en `entradas/` |
|---|---|---|
| As de guía | T1 | `as-de-guia` |
| Ballestrinque | T5 | `ballestrinque/con-el-chicote`; también `con-dos-gazas` y `con-dos-cotes`, otros métodos |
| Vuelta de escota | T6 | `vuelta-de-escota` |
| Amarre cuadrado | T7 | `amarre-cuadrado` |
| Cabeza de turco | T8 | `cabeza-de-turco` |
| Simple | 1 | `simple` |
| Ocho | 1 | `ocho` |
| Ocho doble | 1 | `ocho-doble` |
| As de guía español | 1 | `as-de-guia-espanol` |
| Mariposa alpina | 1 | `mariposa-alpina` |
| Margarita | 1 | `margarita` |
| Arnés de hombre | 1 | `arnes-de-hombre` |
| Silla de bombero | 1 | `silla-de-bombero` |
| Rizo | 2 | `rizo` |
| Pescador | 2 | `pescador` (apunta a la página 01 del manual de la Tropa) |
| Pescador doble | 2 | `pescador-doble` |
| Nudo aguja | 2 | `nudo-aguja` (apunta al manual de la Tropa) |
| Ballestrinque doble | 3 | `ballestrinque-doble` (apunta al manual de la Tropa) |
| Leñador o vuelta de braza | 3 | `vuelta-de-braza` |
| Media llave y dos cotes | 3 | `media-llave-y-dos-cotes` |
| Fugitivo | 3 | `fugitivo` |
| Tensor (*trucker's hitch*) | 3 | `tensor` |
| Tensor ajustable (*tautline hitch*) | 3 | `tensor-ajustable` |
| Constrictor | 3 | `constrictor/con-el-chicote`, `constrictor/torciendo` |
| Nudo de liberación rápida (*mooring hitch*) | 3 | `nudo-de-liberacion-rapida` |
| Presilla de alondra | 3 | `presilla-de-alondra/con-el-chicote`, `presilla-de-alondra/con-gazas` |
| Prusik | 3 | `prusik` |
| Amarre redondo | 4 | `amarre-redondo` |
| Amarre diagonal | 4 | `amarre-diagonal` |
| Amarre trípode | 4 | `amarre-tripode` |
| Refuerzo de cabo | 4 | `refuerzo-de-cabo` |
| Adujado | 4 | `adujado` |
| Puño de mono | 4 | `puno-de-mono` |
| Eslinga de barril | 5 | `eslinga-de-barril` |
| Eslinga de andamio | 5 | `eslinga-de-andamio` |
| Vuelta de cornamusa | 5 | `vuelta-de-cornamusa` |

Las páginas de `_manual-tropa/` sirven de entrada adicional para los nudos que pide la Tropa. Lo que llegó y no se usa está en `_descartadas/`.

Después de cada tanda hay un punto de control:
- Todos los nudos de la tanda están publicados.
- Toda la suite pasa, sin regresiones en los nudos anteriores.
- Revisión contigo.

**Qué se puede paralelizar:** los borradores de especificación, con subagentes. Los filtros humanos no se pueden paralelizar y marcan el ritmo real.

**Cómo entra un nudo nuevo.**
- **Sin código nuevo:** su sesión escribe el borrador con la skill `nudo-nuevo` (esfuerzo medio), Gabriel revisa la hoja, el nudo pasa a `modelado` y entra a `main`.
- **Con código nuevo** (una plantilla o un anfitrión): su sesión propone el diseño como un bloque de este plan, después de la propuesta de su tanda, y se detiene. Gabriel lo aprueba, se programa y se comprueba con `referencia` y `comparar` que los nudos hechos no cambian. Después se escribe la especificación. Cada anfitrión o plantilla nueva sube el formato una versión; si dos ramas suben a la misma, la gestora renumera al integrar.
- **Después, en los dos casos:** Gabriel hace el filtro 1 con la ficha impresa. El nudo pasa a `cuerda-ok`, con su bloque `filtros` (como en `specs/rizo.yaml`), entra a `publicados.txt` y se publica el sitio. Al cerrar el diseño y el «Cómo se hizo» de una tarea, su bloque pasa a `tasks/historial.md`.

**Lo pendiente de la fase 4.** Las tandas 1 a 5 están en el sitio (35 nudos); la propuesta y el «Cómo se hizo» de la tanda 5 están en el historial.
- **T8, la cabeza de turco,** al final del plan, con el método plano de abajo. La versión sobre el tubo, que Gabriel no entendió, está en el historial (T8).

#### T8 con el método plano (propuesta, 23 nov de 2026; Gabriel la aprobó el mismo día, ver «Lo que decidió Gabriel» al final)

**Por qué otro método.** El 11 nov Gabriel no entendió el nudo tejido vuelta por vuelta sobre el tubo. Ahora trajo un método que se ata plano sobre la mesa (`entradas/cabeza-de-turco/nudo_cabeza_de_turco.pdf`, 5 dibujos, e `images.webp`, los mismos dibujos en color): dos gazas, el chicote rodea el firme, se teje, se sigue la cuerda para doblarla y al final se agranda el centro para darle forma de anillo. Es la misma cabeza de turco de 3 cabos y 4 senos, atada plana: el nudo del dibujo 3 tiene 8 cruces que alternan, y su secuencia es la de la cabeza de turco 3 × 4 (comprobado fuera del repositorio, comparando sus secuencias de cruces). Lo plano tiene dos ventajas sobre el tubo: cada paso se ve entero desde arriba, sin girar nada, y es un nudo libre como los que ya salen bien.

**Los cruces de los dibujos.** Los leí en los dibujos ampliados. Los del dibujo 2 se confirman entre sí: con ellos y el tejido del dibujo 3, la cuerda entera alterna encima y debajo, y si uno estuviera mal leído no alternaría.
- **Dibujo 1, dos gazas.** El firme (el extremo largo, abajo a la izquierda) sube y hace la gaza izquierda; la cuerda cruza por abajo hacia la derecha, hace la gaza derecha y baja hasta el chicote (el extremo corto, a la derecha). Las dos gazas van en el mismo sentido, contrario a las agujas del reloj. Hay dos cruces en la línea que une las gazas: el firme, al subir, pasa por encima de ella, y la bajada de la gaza derecha pasa por debajo.
- **Dibujo 2, el chicote rodea el firme.** La flecha del dibujo 1 lleva el chicote por detrás del firme y lo trae por delante. Al hacerlo, la gaza derecha se mete bajo la izquierda: su bajada queda dentro de la gaza izquierda, a la izquierda del firme. Agrega dos cruces: la parte de arriba de la gaza izquierda pasa sobre la bajada de la gaza derecha, y abajo el chicote pasa sobre el firme. Los dos cruces del dibujo 1 siguen, con su encima y su debajo, aunque la forma cambia.
- **Dibujo 3, el tejido.** La línea punteada del dibujo 2 lleva el chicote hacia la derecha, alrededor de la gaza derecha por fuera, y lo hace volver hacia la izquierda por el medio, cruzando cuatro tramos: por debajo de la parte de abajo de la gaza derecha, por encima del firme que sube, por debajo de la bajada de la gaza derecha y por encima del lado izquierdo de la gaza izquierda. Sale por la izquierda. Son los 8 cruces de la cabeza de turco.
- **Dibujo 4, seguir la cuerda.** El chicote vuelve junto al firme donde este entra al nudo y sigue su camino, siempre del mismo lado, sin cruzarlo. Cada cruce pasa a ser cuatro.
- **Dibujo 5, la forma.** Con el nudo doblado, se agranda el agujero del centro y se acomodan las cuerdas una junto a otra. Los senos de adentro quedan en un borde del anillo y los de afuera en el otro.

**Cómo se dibuja.** Los pasos 1 a 5 son un nudo libre sobre la mesa, escrito con segmentos por la skill `nudo-nuevo`, sin código nuevo. Las dos pasadas a mano son 32 cruces, como el ocho doble, que ya se hizo así. Solo si el borrador se traba en las pasadas paralelas, propondría un segmento que sigue a otro a un lado (código nuevo y chico). El último paso, el anillo, no cabe en un nudo libre, porque sus puntos son `[x, y]` sobre la mesa y el anillo se levanta (ver abajo).

**Los pasos** (6, todos en la página 1, como antes). Las etiquetas se numeran en el orden en que se forma cada cruce. Las secuencias van desde el firme.

| Paso | Título | Cruces nuevos | Secuencia |
|---|---|---|---|
| 1 | Haz dos gazas | 1: el firme sobre la línea entre las gazas. 2: esa línea sobre la bajada de la gaza derecha | `1O 1U 2O 2U` |
| 2 | Rodea el firme | 3: la gaza izquierda, arriba, sobre la bajada de la derecha. 4: el chicote sobre el firme | `4U 1O 3O 2O 1U 3U 2U 4O` |
| 3 | Teje el chicote | 5 a 8: el chicote pasa por debajo, por encima, por debajo y por encima | `4U 1O 6U 3O 8U 2O 1U 5O 3U 7O 2U 4O 5U 6O 7U 8O` |
| 4 | Empieza a seguir la cuerda | La mitad de la segunda pasada, junto al firme | La escribe el borrador |
| 5 | Termina de seguirla | La segunda pasada entera: 9 a 32 | La escribe el borrador |
| 6 | Dale forma de anillo | Ninguno: los mismos 32 | La del paso 5 |

- En el paso 2, a lo largo de la línea entre las gazas, los cruces 1 y 2 cambian de orden, porque la bajada de la gaza derecha pasa al otro lado del firme. Es lo que hace el dibujo, y cada cruce conserva su etiqueta y su encima o debajo.
- En el paso 3 la ficha puede dibujar, como el dibujo 2, por dónde va el chicote. Si cuatro cruces en un paso son muchos, se parte en dos (5 y 6, luego 7 y 8) y la ficha pasa a 7 pasos, que todavía caben.
- Pasos 4 y 5: con cada cruce del paso 3, la segunda pasada forma tres más, 24 en total. El chicote no cruza nunca su primera pasada.
- Nombres: «Firme» en el extremo largo y «Chicote» en el corto, en todos los pasos.

**El último paso, el anillo.** Propongo un código nuevo, de tamaño M: un paso que enrolla el nudo plano del paso anterior en un anillo parado sobre la mesa. Cada punto del nudo plano pasa de su distancia al centro a una altura del anillo (los senos de adentro abajo, los de afuera arriba) y de su ángulo alrededor del centro a un ángulo alrededor del anillo. Lo que iba encima en la mesa queda por fuera del anillo, así que los 32 cruces conservan su etiqueta y la secuencia es la misma. Después se relaja con la misma separación y curvatura de siempre, y los cruces se buscan en la superficie del anillo desenrollada, como ya se hace en el tubo. Las cuerdas quedan una junto a otra, como pide el dibujo 5.
- Sin anfitrión: el anillo solo, como se usa en la pañoleta.
- Es una versión nueva del formato, la que siga cuando entre (la v1.14 está reservada para la tensión de la fase 5).
- La alternativa sin código es dejar el paso 6 plano, con el centro agrandado, y explicar con el texto cómo se levanta. Es más barata, pero ninguna imagen mostraría el anillo, y es la forma que más le cuesta imaginar a quien no lo ha hecho.

**Los extremos.** Al terminar, el firme y el chicote salen por el borde de afuera. En el anillo se cortan cortos y se esconden por dentro, bajo la cuerda de al lado. Propuesta: en el paso 6 se ven cortados, a 1,5 diámetros de su último cruce, y el texto dice cómo esconderlos.

**Error común** (lo eligió Gabriel). Con imagen, en el paso 2: el chicote rodea el firme al revés, primero por delante y después por detrás (`invierte: [3, 4]`). La secuencia del error es `4O 1O 3U 2O 1U 3O 2U 4U`: la gaza derecha queda encima de la izquierda y el chicote, bajo el firme. Desde ahí ningún tejido sale bien. El resaltado es el del paso 2, el chicote desde antes del cruce 3, así que llega azul. Sin imagen (`error.otros`): empezar a tejer por encima en el paso 3 (dos «por encima» seguidos, y el nudo no se traba); que la segunda pasada cruce la primera o cambie de lado, y apretar de una vez tirando de un extremo, que deforma el anillo (se ajusta de a poco, siguiendo la cuerda).

**Encuadre y terminado.**
- Pasos 1 a 5: la vista de los nudos libres, desde arriba, con un mismo encuadre que el borrador elige para que quepa el nudo doblado y el comienzo del firme. El error, más cerca del cruce 5.
- Paso 6 y terminado: el anillo parado, en la vista de 55°, con su propio encuadre. Por delante, el anillo; por detrás, el mismo girado media vuelta alrededor de su eje vertical. Es un giro rígido, como el volteo del amarre: no se relaja otra vez y la secuencia no cambia.
- No se aprieta: el anillo ya sale con las cuerdas juntas. Sería el campo que «El nudo apretado» del formato deja para cuando un nudo no deba apretarse.

**Uso y texto de la ficha.** Familia Decorativos. Usos, con texto propio: un anillo tejido para sujetar la pañoleta al cuello; pasas las dos puntas por dentro y lo subes hasta donde quieras. También sirve de adorno o para forrar un mango. Materiales, por confirmar al atarlo: un cordón de 3 o 4 mm y alrededor de 1 m. No lleva sección de seguridad, porque no sostiene nada. Precaución: si sellas las puntas con fuego, el nylon derretido quema. Nada de los PDF se copia, y el texto no lleva términos de sección.

**La plantilla y el tubo actuales.** Nada publicado los usa. Propongo borrar la plantilla `cabeza-de-turco` (`nudos/plantillas/cabeza_turco.py`, `tests/test_cabeza_de_turco.py` y su sección del formato), que queda en la historia de git, y reescribir `specs/cabeza-de-turco.yaml` desde cero con la skill. Del tubo se aprovecha la búsqueda de cruces en la superficie desenrollada y el `mapa` de la hoja de revisión, para el anillo. El anfitrión `tubo` se borra si el anillo va solo. `nudos/plantillas/pasos.py` se queda como está, porque sirve a las demás plantillas. `referencia` y `comparar` comprueban que los 35 nudos hechos no cambian.

**Orden del trabajo, si Gabriel lo aprueba:**
1. El borrador de los pasos 1 a 5, con la skill `nudo-nuevo` y esfuerzo medio. Gabriel revisa la hoja.
2. El paso del anillo, el terminado sin apretar y el borrado de la plantilla: modelo grande, en su worktree, con `referencia` y `comparar`.
3. El texto de la ficha y la ficha. Filtro 1 con un cordón, la ficha impresa y una pañoleta.

**El borrador (23 nov de 2026).** Gabriel aprobó la hoja de revisión de los pasos 1 a 5 y el nudo pasó a `modelado`. Ya trae el error y el texto de la ficha, y la ficha de 5 pasos cabe. Para el código del anillo: la sombra del nudo es r = 4 + 2 cos(4t/3), con t como ángulo y el centro en (0, 0), girada 225°; la primera pasada va a 0,6 diámetros a la derecha del avance y la segunda, a 0,6 a la izquierda. El chicote termina dentro del seno de afuera por donde entra el firme.

**Lo que decidió Gabriel (23 nov de 2026):**
1. El método es el plano, con estos 6 pasos y estos cruces.
2. El último paso es el anillo en 3D, con el código nuevo.
3. El anillo va solo, parado en la mesa, sin el tubo.
4. Dos pasadas, 32 cruces.
5. El error con imagen es rodear el firme al revés en el paso 2 (`invierte: [3, 4]`); empezar a tejer por encima pasa a los errores sin imagen.
6. Se borran la plantilla `cabeza-de-turco` y el anfitrión `tubo`; del tubo se aprovecha el código de los cruces en la superficie desenrollada y el `mapa` de la hoja, para el anillo.

### Fase 5: render en Blender, motor de física y videos (propuesta, 23 nov)

**De dónde sale.** Gabriel vio los reels de elasthic y su paquete *Studio in a Folder* (Patreon), y pidió evaluar si sirve para el libro: mejores imágenes, una cuerda menos tiesa (sobre todo al ahorcar los amarres) y un video de cómo atar cada nudo.

**Qué es el paquete** (según `00_Start_Here.pdf` y `10_Cheat_Sheet.pdf`, la muestra gratis, v1.1):
- Un método de dirección de arte y un estudio de código: un agente como Claude Code escribe Python para Blender, Blender renderiza cada cuadro con Cycles y un comando arma cada película con ffmpeg. Nada es video generado con IA.
- Trae 11 volúmenes (unas 800 páginas), 15 skills, 8 películas de productos y 24 estilos. Su método pasa por puertas: el brief, un cuadro final aprobado (*hero frame*), una prueba de 10 segundos en movimiento y el máster. Una de sus revisiones es mirar el cuadro en gris, como las fichas.
- Pide Blender 5.2, Python 3.11 y ffmpeg con libx264, y está probado en Windows 11 con una NVIDIA RTX. Esta computadora tiene los tres (Blender 5.2.0 LTS, ffmpeg 9.1 y la RTX 4070).
- **Licencia:** lo que se hace con él es de quien lo compra, también para trabajo pagado; el paquete es solo para esa persona. Así que su código y su texto no entran a este repositorio, que es público. Si se compra, vive en una carpeta fuera de git y se usa como referencia.
- **Lo que no hace:** no simula cuerdas ni nudos. Sus películas son de productos rígidos.

**Qué resuelve y qué no.**
- **La cuerda tiesa no es del render, es de la geometría.** Un nudo de plantilla no se aprieta nunca (`nudos/apretar.py`): la plantilla traza las vueltas y los ahorcados con su forma ideal, y en `modelo.json` del amarre cuadrado `apretado` es `None`. En Blender se vería mejor iluminado, pero igual de tieso. Eso es T15, el motor de física de la cuerda, y mejora a la vez el visor, las fichas y los videos.

**Lo que mostraron las pruebas de concepto (23 nov).** Están en dos ramas que no entran a `main`, cada una con su `LEEME.md`:
- **`poc/blender`:** las imágenes de la ficha en Blender tardan unos 3 s cada una a 300 ppp en la RTX 4070, y en gris se leen tan bien como las de hoy. Un video de 10 s del amarre, en 1280 × 720, tarda 19 minutos.
- **`poc/cuerda-ajustada`:** apretar con `apretar()` llega a un 7 % y después cambia un cruce o pasa el límite de curvatura, porque acerca cada punto al medio de sus vecinos en vez de tirar de los extremos. Cambiar las medidas de la plantilla da un amarre menos tieso, con las mismas secuencias, pero no arregla el lazo de delante ni le da cintura a los ahorcados. Gabriel lo vio y pidió un motor de física (23 nov), lo mejor posible.
- **Las imágenes de las fichas** sí pueden mejorar mucho con Cycles: luz suave, sombras de contacto reales y la trenza con relieve. Es T16.
- **Los videos son lo nuevo y lo más difícil.** Hoy cada paso es una pose fija. Animar es calcular cómo se mueve la cuerda entre un paso y el siguiente sin atravesarse, y eso es nuestro, no del paquete. Es T17, y el video armado es T18.
- **El visor sigue en three.js.** Blender no corre en el navegador. Lo que el visor gana es la geometría de T15 y, en T18, el video.

**Decisiones de esta fase.**
1. **La geometría se sigue calculando en `nudos`.** Blender solo lee `build/<slug>/modelo.json` y dibuja. La especificación sigue siendo la fuente de verdad y las comprobaciones de cruces no cambian.
2. **Blender corre sin interfaz desde Python**, como hoy Edge: `blender --background --python render/blender/escena.py -- <argumentos>`. La ruta sale de `NUDOS_BLENDER`, como la de Edge sale de `NUDOS_CHROME`, y la versión queda fija (5.2 LTS), como three.js en `sitio/vendor/`.
3. **Edge se queda para armar los PDF** (`ficha.html` y el libro); Blender reemplaza solo a las imágenes.
4. **El orden (Gabriel, 23 nov):**
   1. **Prueba de concepto del motor** (T14a), en la rama `poc/motor`. Punto de control D.
   2. **Prueba de concepto del render en Blender y del video, con la cuerda del motor** (T14b), en la rama `poc/render-motor`. Punto de control E: Gabriel decide D10 y D11, y si compra el paquete.
   3. **Recién con las dos aprobadas se implementa:** el motor (T15), las fichas en Blender (T16), la animación (T17) y los videos (T18), probados con los nudos piloto.
   4. **Al final, todos los nudos a la vez** (T19): se calculan, se dibujan sus fichas y se arman sus videos en una sola corrida. No hay tandas ni etapas.

   Las pruebas de concepto viven en sus ramas y no entran a `main`. Lo que se implementa se escribe de nuevo en `nudos/` y `render/`, con sus pruebas. Esta fase va antes del libro y la edición 1 (la fase 6).
5. **Todas las fichas se rehacen** con el render nuevo (Gabriel, 23 nov), también las de los nudos aprobados y publicados.
6. **La forma de la cuerda la da un motor de física propio, en Python** (T15), no la física de Blender. Blender no tiene un simulador de cuerda: se arma con *cloth* o con cadenas de cuerpos rígidos, y una cuerda delgada que choca consigo misma se atraviesa, y en un nudo eso cambia los cruces sin avisar. Además, el visor, las fichas y la comprobación de cruces viven en Python. El motor reemplaza a la relajación y al apretado, y también sirve para animar (T17).

#### T14a y T14b: las pruebas de concepto (cerradas)

Las dos pruebas de concepto y los puntos de control D y E están cerrados (24 nov). Su detalle está en el historial, y el código, en las ramas `poc/motor` y `poc/render-motor`, con su `LEEME.md`. Lo que aprendieron va abajo, en cada tarea.

#### T15: Motor de física de la cuerda (propuesta, 23 nov)

Se implementa después del punto de control E, desde lo aprendido en T14a. Lo que sigue es el diseño completo; la prueba de concepto hace solo su mínimo.

**Para qué.** Que cada paso y cada nudo terminado tengan la forma que toma una cuerda real al atarla: tensa donde se tira, floja donde no, apoyada en los palos, deslizándose o trabada por el roce, y sin atravesarse nunca. Hoy la forma sale de la plantilla o del trazado, y la relajación y el apretado solo la corrigen. Con el motor, la plantilla y el trazado dan solo el punto de partida, con la topología correcta, y la forma final la da la física.

**El criterio (Gabriel, 23 nov: «lo más complejo para el mejor resultado»).** El motor modela todo lo que cambia cómo se ve una cuerda en un nudo: que no se estira, que se dobla y se tuerce con su propia rigidez, que pesa, que roza y que nunca se atraviesa. Cada fenómeno entra con una prueba que lo mide contra la física conocida o contra cuerda real. Lo que no se nota en el papel ni en el video no entra, como en T7b: complejidad que no se ve es costo sin resultado.

**El modelo físico.**
- **La cuerda es una varilla elástica discreta** (*Discrete Elastic Rods*, Bergou y otros, 2008 y 2010): nodos en la línea central y, en cada tramo entre dos nodos, un marco material que dice cuánto está torcida la cuerda. Su energía tiene cuatro partes:
  - **Estiramiento:** casi no se estira; la rigidez a la tracción es muy alta.
  - **Flexión:** la rigidez de doblarse (EI), con la curvatura discreta en cada nodo. Opcional: una curvatura natural, para la «memoria» de una cuerda que estuvo enrollada.
  - **Torsión:** la rigidez de torcerse (GJ). Hace que una vuelta se acueste distinto, y en el render gira la trenza y el hilo trazador.
  - **Peso:** la gravedad, con la densidad de la cuerda.
- **El contacto nunca se atraviesa** (*Incremental Potential Contact*, IPC: Li y otros, 2020; la versión para varillas y telas delgadas, 2021). Entre dos tramos de cuerda hay una barrera que crece sin límite cuando su distancia se acerca a la suma de los radios. Cada paso del integrador se recorta con detección continua de colisiones (CCD), así que ningún tramo atraviesa a otro, ni siquiera entre dos iteraciones. Es lo que garantiza que la topología no cambia, y es lo más importante para el libro.
- **El roce es el de Coulomb, estático y dinámico,** con el método suavizado de IPC: la cuerda se traba hasta que la fuerza supera el roce y después desliza. Hay un coeficiente para cada par: cuerda con cuerda, cuerda con madera y cuerda con metal (el destorcedor y la cornamusa).
- **Los anfitriones son cuerpos rígidos** descritos por su distancia con signo: los cilindros de los palos, el poste y el tubo, la mesa y las mallas del barril, la cornamusa y el destorcedor, con la misma barrera y el mismo roce.
- **Las manos son condiciones de borde:** puntos fijos (el firme que se sostiene), fuerzas (tirar del chicote con una tensión dada) y trayectorias (llevar el chicote por un camino, para animar).

**El integrador.** Newton implícito con búsqueda en línea filtrada por la CCD. En modo cuasiestático, para los pasos y el terminado, minimiza la energía total mientras la tensión de las manos sube de a poco. En modo dinámico, para los videos, usa Euler implícito con un paso de tiempo por cuadro y subpasos. El Hessiano es disperso (la varilla es una banda, más los pares en contacto), se proyecta a semidefinido positivo y se resuelve con Cholesky disperso. Todo en `float64`, en CPU y con un orden fijo, para que construir dos veces dé lo mismo byte a byte, como hoy.

**Lo que tiene que dar en cada modo.**
1. **Asentar un paso (reemplaza a `relajar()`).** Parte del trazado o de la plantilla, como hoy. El firme queda sostenido, el chicote con la tensión que diga el paso (por omisión, «ajustado»: lo que deja una mano al acomodar el nudo) y todo lo demás cae, se apoya y roza. Después se comprueba como hoy: la secuencia de cruces, la separación, la curvatura y la consistencia entre pasos.
2. **Apretar el terminado (reemplaza a `apretar()`).** El mismo paso, con los extremos tirados fuerte, hasta que la cuerda deja de moverse. Así se aprietan también los nudos de plantilla: los ahorcados tiran de las vueltas porque la tensión recorre la cuerda, y no porque se acorte un tramo.
3. **Atar (T17).** El chicote va por un camino hacia la pose del paso siguiente, el resto se mueve con la dinámica y cada cuadro se guarda para Blender. Al final de cada paso, la pose se asienta y tiene que ser la misma que la de la ficha.

**La secuencia declarada sigue mandando.** La IPC garantiza que la cuerda no se atraviesa, pero la secuencia es una vista desde arriba (o desde el palo), y un tramo puede correrse por encima de otro sin atravesarlo. Si al asentar cambia la secuencia, el paso falla como hoy, y se corrige con menos tensión, con otra mano que sostenga o con otro punto de partida. Nunca se cambia la secuencia para que coincida.

**Cómo se arma.**
- Un paquete nuevo, `nudos/fisica/`: `varilla.py` (energías, gradientes y Hessianos de la varilla), `contacto.py` (barrera, CCD y roce con la cuerda y los anfitriones), `integrador.py` (Newton y búsqueda en línea), `manos.py` (condiciones de borde), `asentar.py` y `atar.py` (los modos) y `materiales.py` (los parámetros de cada cuerda).
- **Las bibliotecas se eligen en T14a** con una prueba de velocidad. Las candidatas son `ipctk` (IPC Toolkit, en C++ con enlace a Python; barreras, CCD y roce para tramos y triángulos), `numba` (las energías de la varilla en CPU) y `warp-lang` (NVIDIA Warp, en la GPU). La preferida es `ipctk` con `numba`, porque garantiza el no atravesarse y repite el resultado. Warp sirve si la CPU es demasiado lenta para los videos.
- **Los parámetros de la cuerda** van en `config/cuerdas.yaml`, uno por tipo de cuerda (la de 8 mm de los nudos libres, el cordino del prusik, el cordón de la cabeza de turco), calibrados en T15f. Una especificación puede pedir la tensión de cada paso (`tension: suelta | ajustada | apretada`), con «ajustada» por omisión: es la v1.14 del formato.
- **`modelo.json` no cambia de forma:** sigue con los puntos de cada paso, y gana, opcional, la torsión de cada tramo y la presión de contacto en cada punto, para el render (T16). El visor los ignora.

**Lo que cuesta (medido en T14a y T14b).** Asentar un paso del amarre cuadrado (unos 2300 nodos) con la tensión de atado tarda de 4 a 14 s, y el as de guía, 1 s. Un video del amarre son 270 asentamientos cortos: 744 s con 8 procesos. El costo grande es el render (T16 y T18), no el motor.

**Las subtareas, en orden.** Cada una termina con sus pruebas pasando. Se prueban con los nudos piloto; todos los nudos se calculan juntos en T19.

- **T15a, la pila (S):** `ipctk` (D11) pasa a `pyproject.toml` y su instalación a `CLAUDE.md`, y lo que T14a aprendió de la biblioteca (la tabla de `poc/motor/LEEME.md`: el orden de `Hyperplane`, los filtros nativos, la CCD aditiva, la rigidez baja de la barrera) queda en `nudos/fisica/` con una prueba cada uno. Se decide si `ipctk` va en el venv de A: o en uno fuera de Drive, como en T14a.
- **T15b, la varilla (M):** estiramiento, flexión, torsión y peso, con gradientes y Hessianos comprobados contra diferencias finitas. Pruebas: la catenaria (una cuerda colgada entre dos puntos toma la forma del coseno hiperbólico) y la elástica (un voladizo cae lo que dice la fórmula).
- **T15c, el contacto y el roce (L):** la barrera y la CCD entre tramos y con los anfitriones, y el roce. Pruebas:
  - Dos cuerdas lanzadas una contra otra nunca se atraviesan.
  - La ecuación del cabrestante (Euler-Eytelwein): una cuerda sobre un palo sostiene un peso con una tensión del otro lado que crece como e^(μθ) con el ángulo abrazado θ.
  - Un bloque sobre una tabla inclinada desliza recién pasado el ángulo del roce.
- **T15d, asentar y apretar (L):** los modos 1 y 2 dentro de `construir`, detrás de una opción, primero con los pilotos de la fase 2: el as de guía, el ballestrinque, la vuelta de escota y el amarre cuadrado. Una página de prueba pone cada uno como está hoy y con el motor, en color y en gris, y Gabriel la aprueba en papel. El nudo simple apretado se compara con el largo de cuerda publicado para los nudos ideales apretados (Pieranski y otros).
- **T15e, calibrar con cuerda real (S, con Gabriel):** con la cuerda de los filtros, se mide el diámetro, el peso por metro, la flexión (cuánto cae un voladizo de 20 cm), el roce con madera (en una tabla inclinada) y, con un peso colgado de un palo, el roce en vuelta. Gabriel saca fotos de cuatro nudos apretados desde vistas marcadas, y el motor los asienta con esos parámetros para compararlos.
- **T15f, listo para todos los nudos (M):** `construir` usa el motor en cualquier nudo, libre o de plantilla, sobre cualquier anfitrión, y `referencia` y `comparar` sirven con él. Se comprueba con los pilotos; los demás nudos se calculan en T19.
- **T15g, lo que el motor le da al render (M, va con T16):** la presión de contacto aplana la sección de la cuerda donde aprieta, como una cuerda real, y la torsión gira la trenza y el hilo trazador. Entra solo lo que se note en la página de prueba impresa.

**Cómo se hizo T15a (24 de noviembre de 2026):**
- `ipctk==1.6.1` va en `pyproject.toml` y en el venv de A: (pesa 4,4 MB; `scipy` ya estaba). La versión queda fija porque lo aprendido depende de ella.
- `nudos/fisica/contacto.py` es la capa sobre `ipctk`: `MallaContacto` (la cuerda, los palos como cilindros de 64 lados y la mesa), con el filtro nativo de los vecinos, la distancia mínima sin el cuadrado y el paso sin atravesarse (CCD aditiva con LBVH). `tests/test_fisica_contacto.py` comprueba cada lección de T14a en menos de 1 s, y que calcular dos veces da lo mismo.
- **Lo nuevo: la mesa de T14a no hacía fuerza.** Un `Hyperplane` de `ipctk` solo ve los nodos a menos de (dmin + dhat)/2 = 0,525, y la cuerda apoyada quedaba a 1,0: sin contacto, la sostenía solo la CCD, que recorta el paso sin empujar (por eso Newton avanzaba con pasos cortos sobre la mesa). Ahora la mesa es una malla de dos triángulos, que sí ve hasta dmin + dhat. Una prueba fija el comportamiento del plano, por si cambia con otra versión.

**Cómo se hizo T15b (24 de noviembre de 2026):**
- `nudos/fisica/varilla.py` tiene la varilla: estiramiento (EA/2l · (|e| − l)²), flexión con la curvatura discreta de Bergou (EI·|κb|²/(l₀ + l₁), que es 4·tan²(φ/2) y crece sin límite si la cuerda se dobla sobre sí misma) y peso. Gradiente y Hessiano analíticos, comprobados contra diferencias finitas (1e-10). El Hessiano es un CSR de patrón fijo, armado con `np.add.at` en el orden de los bloques, así que sale simétrico y repetible bit a bit (el ordenamiento de scipy sumaba en otro orden). `proyectar=True` lo deja semidefinido bloque por bloque. Un Hessiano del amarre cuadrado terminado (2335 nodos) tarda 14 ms; proyectado, 24 ms.
- `nudos/fisica/materiales.py` tiene `CUERDA_8MM` con los valores de T14a, en SI y pasados a diámetros: EA = 20 000 N, EI = 31,25 N·d², 45 g/m (0,00353 N/d), roce 0,35 y 0,45. GJ queda como cota alta (EI/1,5) solo para medir. `config/cuerdas.yaml` llega en T15e.
- `nudos/fisica/integrador.py` tiene el Newton mínimo (nodos fijos, búsqueda en línea, el gancho `paso_maximo` para la CCD de T15d). **Lo aprendido:** proyectar siempre la flexión deja a Newton casi lineal (el voladizo de 25 d no llegaba en 300 iteraciones); con el Hessiano exacto primero y el proyectado solo si el exacto no baja, llega en 35. Y la energía de flexión con 1 − cos φ perdía casi todas sus cifras con la cuerda casi derecha (Newton se estancaba en 4·10⁻⁸ N): va con el producto cruz.
- **La tensión de atado de T14a tiraba de más:** acortar l·(1 − T/EA) da T/(1 − T/EA). Ahora es l/(1 + T/EA), y una prueba comprueba los 60 N justos.
- `tests/test_fisica_varilla.py` (1 s): diferencias finitas, la viga en un arco, el Hessiano proyectado semidefinido, la catenaria (4,8 m colgados a 3,2 m: la forma se aparta del coseno hiperbólico menos de 0,1 % de la flecha, con la rigidez real) y la elástica: 8 cm de voladizo caen lo que dice w L⁴/8EI y 20 cm (la medida de T15e, cae más del 20 % del largo) lo que dice la elástica sin linealizar, a 0,5 %. Los nodos 0 y 1 fijos empotran la cuerda medio tramo antes del nodo 1.
- **La torsión no entra en la energía, por las condiciones de borde y no por chica.** En una cuerda redonda sin curvatura natural, la torsión solo cambia la forma si las dos puntas se sostienen sin dejarlas girar: con una suelta, el marco material se acomoda hasta torsión cero y no hace fuerza. En asentar y apretar (T15d) el chicote va suelto o tirado con una fuerza, y la barrera de IPC no hace momento sobre el eje de la cuerda. El marco de equilibrio es entonces el marco paralelo, `marco_paralelo` (probado en un plano y en una hélice), que es lo que T15g usa para girar la trenza. **Medido:** si las dos puntas se sostuvieran sin girar desde la cuerda recta hasta el nudo terminado, la torsión guardada sería la escritura (*writhe*) del nudo, y su momento, GJ·2π·Wr/L, comparado con el de flexión típico del nudo, sería: simple 0,46 (Wr −3,4 en 39 d), ballestrinque 0,28, vuelta de escota 0,19, as de guía 0,16, mariposa 0,14, cabeza de turco 0,12, amarre cuadrado 0,09 y ocho 0 (es aquiral). No es despreciable: si T17 hace que una mano sostenga el chicote sin dejarlo girar, la torsión entra ahí, con GJ medido.
- **Fuera:** la curvatura natural (la «memoria» de la cuerda enrollada) y la flexión anisótropa, que piden el marco material en la energía.

**Cómo se hizo T15c (24 de noviembre de 2026):**
- `contacto.py` gana varias cuerdas en una malla (`nodos_por_cuerda`), la barrera (`barrera`), el roce retrasado (`roce_retrasado`, la fuerza normal y el plano tangente del comienzo del paso) y el roce de cada anfitrión (`Solido.mu`; ipctk promedia el de los dos vértices, así que un anfitrión lleva 2μ − μ_cuerda). `rigidez_barrera` da la rigidez para que un nodo que se apoya con una fuerza dada quede a media franja: la barrera de rigidez 1 empuja 0,51 N por nodo, con cualquier largo de tramo.
- `integrador.py` gana `Sistema.paso`: Euler implícito en la forma de potencial incremental de IPC (la masa de cada nodo sale de su peso), o cuasiestático sin `dt`, con la amortiguación de T14a. Cada iteración de Newton se recorta con la CCD.
- **ipctk corre en un solo hilo.** Con varios, las fuerzas de la barrera se suman en otro orden en cada corrida, y dos choques iguales daban resultados distintos. `construir` ya reparte los pasos en procesos.
- **Un palo lleva un anillo en cada punta, no 24:** un prisma es exacto a lo largo, y armar los contactos pasa de 20 a 0,8 ms. Con eso, el cabrestante bajó de 15 a 1,4 s.
- **Los contactos siguen siendo los de IPC, no los de OGC.** Un nodo sobre una arista de la malla empuja hasta 4 veces más (suma las dos caras, la arista y los vértices), pero eso solo reparte el apoyo: el nodo queda unos 0,03 d más alto y la fuerza total y el roce total son los de la física. OGC empuja parejo, pero su energía salta cuando dos cuerdas se cruzan justo en un nodo de cada una, y Newton se traba ahí.
- **Un solo μ, el estático.** En ipctk 1.6.1, con μ_s > μ_k la fuerza del roce crece con el corrimiento hasta μ_k y nunca llega a μ_s: a 22°, con 0,45 y 0,35, la cuerda desliza por la tabla. Un μ_k aparte solo debilitaría lo que sostiene un nudo; T15e mide el estático. Si los videos (T17) piden el dinámico, va con un roce propio.
- **Los pasos largos pueden llevar la cuerda por el costado de un obstáculo.** Con 1/60 s y una cuerda corta (8 d) que cae a 5 m/s sobre un palo, Newton la lleva por el costado, sin atravesarlo, hasta su meta inercial, 10 d más abajo, en un solo paso. Nada se atraviesa, pero el camino no es físico: T17 anima con subpasos.
- `tests/test_fisica_roce.py` (7 s):
  - La barrera y el roce contra diferencias finitas.
  - Dos cuerdas de 30 d lanzadas una contra otra a 0,5 y a 5 m/s (10 d por paso) no se atraviesan, y una que cae sobre un palo queda arriba.
  - El cabrestante, con 100 N, aguanta al 95 % de e^(μπ) y desliza al 105 %. Medido: aguanta al 97 % y desliza al 103 %.
  - La tabla inclinada sostiene a 20° y a 23° (el ángulo del roce es 24,2°) y deja deslizar a 28° y a 35° con la aceleración g (sen α − μ cos α), a menos de 3 % (medido, 1 %).
  - Dar pasos dos veces da lo mismo bit a bit.
- **Para T15e:** con 10 N, la cuerda de 8 mm desliza por el palo de 4 cm ya al 97 % de e^(μπ), porque con su rigidez no lo abraza del todo (su largo de flexión, √(EI/T) = 1,8 d, se acerca al radio). Con 100 N, o con una cuerda flexible, se cumple la fórmula. Al medir el roce en vuelta, conviene un peso de varios kilos.

**Cómo se hizo T15d (24 de noviembre de 2026):**
- **La opción:** `python -m nudos --motor <orden>` pone `NUDOS_MOTOR=1`, y `construir` asienta los pasos (`libre.asentar_o_relajar` en vez de `relajar()`, también el error común y el reverso) y aprieta el terminado con `nudos/fisica/asentar.py`. Sirve con la mesa, el poste y la cruz de los amarres; con otro anfitrión o plantilla (`SinMotor`), ese nudo sale como siempre (T15f). `nudos/procesos.py` abre un grupo de procesos por cada valor de la opción, porque la heredan al arrancar. **Sin la opción no cambia nada:** `referencia` y `comparar` dan los 36 nudos iguales byte a byte.
- **Los módulos:** `nudos/fisica/manos.py` (`sostener` y `para_apretar`), `nudos/fisica/asentar.py` (`separar`, `asentar`, `asentar_paso`, el modo 1, y `apretar`, el modo 2) y `nudos/prueba_motor.py`, la página (`python -m nudos prueba-motor`, `build/motor/prueba.pdf`).
- **Asentar un paso (modo 1):** el trazado elevado (o la curva del poste o de la plantilla) pasa por `separar`, y el motor lo asienta con el firme sostenido, la tensión de atado del paso, peso, mesa, anfitrión y roce, hasta que ningún nodo se mueve más de 0,001 d en un paso. **Lo nuevo: la cuerda tiene memoria** (`Varilla(curvatura=…)`: la curvatura de reposo es la de la forma de partida, en el marco del mundo; probada contra diferencias finitas). Sin memoria, una cuerda elástica de 8 mm abre cada lazo suelto: su rigidez empuja con newtons y su peso, con el roce, sostiene milésimas. Una cuerda trenzada conserva el lazo porque sus fibras rozan al doblarse. Así que la cuerda queda donde la dejó la mano y el motor solo la asienta: **los pasos con el motor se ven casi iguales a los de hoy** (de 0,05 a 0,15 d en promedio en el as de guía), sin ningún par a menos de dmin, en 1 a 4 s cada uno.
- **`separar`** deja la cuerda de partida sin pares a menos de 0,98 sumas de radios (la IPC necesita partir de más de dmin, 0,95), sin dobleces de radio menor que 1,1, con cada tramo de largo h y fuera del anfitrión, corrigiendo la curva en la misma vuelta que los choques: los choques doblaban el comienzo del amarre (entre la mesa y el palo de abajo, donde la cuerda cabe justo) con radio 0,21, y separando a 1,03 no cabía. Si no lo logra, el paso falla (`TrazadoError`).
- **Las manos al asentar:** el firme sostenido en sus tres primeros nodos y el chicote suelto: en un nudo libre la tensión «ajustada» no cambia un lazo suelto, y sostener el chicote dejaba tramos estirados. En un amarre las dos puntas se sostienen de un nodo (así la tensión de atado dura, y la punta puede girar: con tres nodos, la tensión doblaba la cuerda ahí con radio 0,29), y no hay mano en el hito: sostener la cuerda donde la deja la plantilla comprimía un tramo un 4 %.
- **El reverso con el motor** se arma como un trazado: el último paso volteado, remuestreado cada h sobre la mesa y con cada cruce elevado al revés. Volteado tal cual, lo que estaba en la mesa queda en el aire y la memoria lo dejaría ahí.
- **Apretar el terminado (modo 2):** el último paso asentado, sin roce y sin memoria, con manos que tiran con 60 N, hasta que deja de moverse. Sin roce, porque apretar un nudo es acomodarlo parte por parte, y las manos vencen el roce de cada una; lo que queda es el nudo tallado. **Las manos, medidas con los pilotos:** si la cuerda tiene una gaza, se sostiene la gaza y se tira del firme (60 N) y del chicote (20 N), como se asienta un as de guía; si no, se sostiene el firme en su punta y donde entra al nudo y se tira del chicote. Tirar de la gaza desde un punto la estiraba en una V; tirar solo del chicote del as de guía lo alargaba hasta cruzar la gaza; con el firme sostenido solo en su punta, el nudo viajaba fuera del encuadre; tirar del firme del ballestrinque hacía girar sus vueltas sobre el poste.
- **Apretado del todo, un nudo se para sobre la mesa y desde arriba muestra otro diagrama** (el simple pasa a 4 cruces: la IPC no deja que cambie la topología, pero la vista sí). Como `apretar()`, el terminado es lo más apretado que todavía cumple la secuencia declarada y los límites (`aceptar`, con 15 pasos de paciencia); a diferencia de `apretar()`, sus fallas sí cuentan.
- **En un amarre, el terminado apretado es el último paso asentado con la tensión «apretada»** (60 N en las vueltas, 150 en los ahorcados), con memoria. Sin memoria, como en la prueba de concepto, los ahorcados se corrían sobre las vueltas y el cierre cambiaba la secuencia en los mapas de los palos (42 cruces en vez de 40). **Con memoria, el amarre casi no cambia** (los nodos se mueven 0,1 d en promedio y 0,6 como mucho respecto de hoy; el terminado gasta 466,5 → 464,6 d de cuerda): la memoria guarda la forma de la plantilla, y la tensión de atado solo la asienta. Que se vea más apretado pide atarlo de verdad (T17), no asentarlo.
- **El nudo simple contra Pieranski:** el largo que gasta el nudo, Λ = (L − L′)/D con L′ la distancia entre las puntas tiradas hacia afuera, es 10,1 en el simple ideal (Pieranski, Przybyl y Stasiak, «Tight open knots», Eur. Phys. J. E 6, 2001) y 10,35 medido con cuerda real (Diao y otros). Con el motor, tirado con 60 N y sin roce: **10,68**. Una cuerda con rigidez no llega al ideal; la prueba pide de 0,95 a 1,1 veces el ideal.
- **Lo que T14a dejó abierto, decidido:**
  - **dmin 0,95 contra la separación de 0,97:** dmin se queda en 0,95 (una cuerda tirada sí se aplasta contra otra, y T15g dibuja la sección aplastada), y con el motor la comprobación pide 0,95 (`LIMITES_MOTOR`), que es lo que la IPC garantiza. El 0,97 sigue para la relajación, que no garantiza nada.
  - **Las zonas de las plantillas:** se quedan por nodo. El motor no vuelve a muestrear la cuerda, así que cada nodo conserva la zona donde lo puso la plantilla, y la cuerda del amarre se mueve a lo más 0,6 d. Las zonas geométricas entran cuando un nudo se mueva más (T17, al atar).
  - **La tensión por tramo:** sí, en los amarres, por los nombres de sus hitos (`tensiones_de_amarre`): la del paso en lo ya atado, 2,5 veces más en los ahorcados y nada en lo que sigue suelto sobre la mesa.
  - **La v1.14 (`tension:` por paso):** no entra todavía. A los pilotos les basta la tensión de cada modo; entra cuando un nudo la pida (T15f).
- **Varios grosores:** ipctk tiene una sola distancia mínima por malla, así que la vuelta de escota va con `ContactoCompuesto` (en `contacto.py`): una malla por grosor (con la mesa y el anfitrión a su escala) y una por cada par, solo entre nodos de grosores distintos (`make_vertex_patches_filter`). Una cuerda de grosor g tiene EA·g², EI·g⁴ y peso·g². La malla de un anfitrión va 0,06 d más adentro que la madera, como en T14a.
- **Lo que queda: la vuelta de escota con el motor tiene fallas de curvatura** en el último paso (radio 0,87, contra 0,9), en su error (0,85) y en el reverso (0,77), donde la delgada se apoya sobre la gruesa. Ninguna de las variantes de las manos y de `separar` que probé la sacó del límite. Va en T15f, con el cruce en diagonal de su especificación a la vista.
- **Tiempos (construir con todos los núcleos):** de 1 a 3 minutos cada piloto; la página de prueba, con los ocho modelos y sus imágenes, unos 6. Lo que más cuesta es apretar, que comprueba la secuencia en cada paso.
- **Pruebas:** `tests/test_fisica_asentar.py` (unos 20 s): el material por grosor, el contacto compuesto (a la suma de los radios, y su gradiente), las manos, la tensión del amarre, `separar`, un tramo que baja hasta apoyarse, apretar dos veces da lo mismo y el simple contra Pieranski. `test_fisica_varilla.py` gana la memoria contra diferencias finitas y una curva en S que solo con memoria se queda como estaba.

**Cómo se hicieron los ahorcados apilados del amarre cuadrado (24 de noviembre de 2026):** Gabriel pidió el amarre más apretado al revisar la página del motor. Como el motor conserva la forma de la plantilla, el cambio va en la plantilla. Gabriel aprobó la página de prueba (`build/ahorcados/prueba.pdf`: hoy, apilados y apilados con el motor, en color y en gris) el mismo día.
- **Detrás de una opción:** `alturas_de_ahorcados(..., apilados=True)` solo lo pide `cuerda()` del cuadrado bien hecho. El error (`ahorcados-por-fuera`) y el amarre diagonal, que usa las mismas funciones, salen iguales byte a byte; el diagonal podría apilarse después. Las plantillas de palos paralelos no usan este trazado.
- **La banda:** sobre el palo de abajo, el primero va pegado al palo y cada uno 1,1 más arriba (`APILA`), sobre el arco del anterior. Bajo el palo de arriba, el último pasa a 0,05 del palo y los anteriores escalonados, 0,7 más abajo (`APILA_ARRIBA`) y 0,9 más afuera (`CORRE`) cada uno. Entre los palos, cada uno va pegado a las esquinas a su altura, montado sobre el anterior. Cada ahorcado es más alto que el anterior en todos los ángulos, así que **la secuencia de cruces no cambia** (40 con 3 y 3).
- **El último cuadrante:** cada ahorcado sube suave a la altura del siguiente entre −75° y −20° (`alto` acepta j con decimales), y el último sube igual hacia el cierre: si se quedara a su altura, cruzaría al penúltimo, que ya subió a ella.
- **Por qué escalonados bajo el palo de arriba:** uno debajo de otro, el primero empezaba por debajo de donde termina la última vuelta, y la cuerda tensa se arrugaba en ese hito (radio 0,1 a 0,4, estiramiento 2,2 %). Cinco formas de la salida no lo arreglaron de manera estable. Escalonados, el primero empieza a 4,05 sobre la mesa y la salida de antes sirve sin cambios.
- **El firme en la cintura:** apilados, el primer ahorcado cruza el firme del ballestrinque de inicio más abajo, así que el firme va en la zona de la cintura desde zb + 0,5. Solo cambia la zona: los puntos y el hito `inicio` no, y los pasos 1 a 3 salen iguales byte a byte.
- **Si no caben, van como antes:** si el primero tocaría la mesa bajo el palo de arriba (8 ahorcados o más) o si la banda no cabe junto al firme (con 3 vueltas, de 4 ahorcados en adelante). Apilados sin fallas: 2 y 2, 3 y 3, 4 y 3. Con `CORRE` 0,3, los ahorcados casi coincidían en el mapa del palo y salían cruces de más; con 0,5, el motor doblaba a 0,86.
- **Resultado (3 y 3):** sin el motor, separación 0,99, curvatura de al menos 1,02 y estiramiento 1,1 %; con el motor, 1,04, 0,97 y 0,3 %. La ficha cabe. `comparar` contra 15a2b7d: solo cambian los pasos 4 a 7 del amarre cuadrado. Sus imágenes de los pasos 1 a 3 se ven un poco corridas porque la cámara encuadra la cuerda de todos los pasos juntos. La huella del amarre en `tests/test_apretar.py` es la nueva.
- **Filtro 1 (24 de noviembre):** Gabriel ató otra vez los pasos 4 a 7 y el terminado con la ficha de dd48d6e: aprobado, y el sitio se publicó con el amarre nuevo. El texto del paso 5 dice «cada uno por fuera del anterior», que se cumple sobre el palo de abajo y entre los palos; bajo el palo de arriba, cada uno nuevo va escalonado un poco más cerca del palo.

**Cómo se hizo T15e (25 de noviembre de 2026):** Gabriel midió la cuerda de los filtros y fotografió tres nudos apretados, desde arriba y con cinta métrica (`entradas/t15e/`, fuera de git: `medidas.txt` y dos fotos de cada uno). Falta la foto del amarre cuadrado.
- **`config/cuerdas.yaml`** tiene la cuerda de 8 mm medida, en unidades de catálogo y con de dónde sale cada número. `nudos/fisica/materiales.py` la lee (`cuerda("cuerda-8mm")`) y `CUERDA_8MM` ya es la medida. La de T14a queda como `CUERDA_T14A`, para comparar.
- **Lo medido, contra lo que suponía T14a:**
  - **El peso:** 20,4 g/m, del paquete (612,35 g los 30 m), contra 45.
  - **La flexión:** EI = 5,0·10⁻⁴ N·m² (7,8 N·d²), cuatro veces menos que los 2·10⁻³ de T14a. Sale de voladizos de 10, 15, 20, 30 y 40 cm, que caen 3,4, 8,2, 10,5, 27 y 37 cm. Con la elástica sin linealizar (la rehice con una varilla discreta, minimizando su energía), cada voladizo solo da una EI distinta: de 0,7 a 3,0·10⁻⁴. Una sola EI para los cinco falla hasta un 52 %. Con EI y un ángulo de caída de 18° en el borde donde se sujeta (la cuerda dobla ahí o trae curva del carrete), los errores quedan de −17 % a +13 %. El ángulo no entra al motor; la EI es incierta en un factor de 2 más o menos.
  - **El roce con la madera:** 0,27, de media vuelta sobre un palo: 1,8 kg se sostienen con 0,78 kg, tres veces igual (Euler-Eytelwein: ln(1,8/0,78)/π). Con vuelta y media, P baja solo al quitarle todo el peso a p; la fórmula pide apenas 0,14 kg, así que cuadra. La tabla inclinada fue sobre cartón y no madera (15° a 18°, μ ≈ 0,31), así que no entra. T14a suponía 0,45.
  - **Sin medir:** la tracción (EA), el roce de cuerda con cuerda (0,35) y el de metal (0,3), que se quedan como estaban.
- **Los pilotos con la cuerda medida, sin fallas** (`--motor referencia`), y casi iguales a los de la cuerda de T14a. Asentar un paso no cambia casi nada, porque la memoria guarda la forma de partida. Apretados, cambian un poco:
  - El as de guía queda algo más compacto: 8,1 d de largo en vez de 8,9, con el cuello más pegado al firme, como en las fotos. La curvatura baja de 1,08 a 0,94.
  - La vuelta de escota queda algo más ancha: 9,0 d en vez de 7,3.
  - El ballestrinque y el amarre casi no cambian. La curvatura del ballestrinque baja de 1,51 a 1,02.

  Una cuerda más blanda se dobla más donde se tira, así que las curvaturas bajan, pero ninguna sale del límite.
- **La página de comparación** está en `revision/t15e/` (fuera de git, porque lleva las fotos), en color y en gris: cada foto junto al nudo apretado con la cuerda de T14a y con la medida. En las fotos los nudos se ven más apretados que en el motor, sobre todo la vuelta de escota. Ahí la delgada es paracord de 4 mm, la mitad de la gruesa, y la especificación usa 1,5 a 1. Que el motor apriete más es T17 (atar de verdad), no la cuerda.
- **Pruebas:** las de la física leen el material, así que comprueban la cuerda medida (la catenaria, la elástica y el cabrestante). `test_el_peso_es_el_de_la_cuerda` pasa a 20,4 g/m. Sin la opción `--motor`, nada cambia: el material solo lo usa el motor.

**Cómo se hizo T15f (24 de noviembre de 2026):**
- **Todos los anfitriones tienen malla** (`nudos/fisica/solidos.py`, `mallas`): cada uno pasa a triángulos `adentro` diámetros por dentro de la madera (g/2 + 0,06·g, como en T15d). El poste, la cruz, los palos, el tubo, el cabo, la estaca y el destorcedor son cilindros (`contacto.cilindro`); el tablón, un prisma de su corte desplazado (con cantos de 0,45 y la malla 0,56 adentro, queda de esquinas vivas); la cornamusa, la barra con las puntas redondas (de revolución) y el pie, un estadio parado; el barril, el sólido de revolución de su núcleo desplazado (`Barril._contorno`), sin las ranuras; y los dedos del puño de mono, dos cilindros parados con la punta redonda. El destorcedor roza como metal (`Material.mu_metal`, 0,3, de tabla, sin medir). `asentar.solidos` solo llama a `mallas`, y la del poste y la de la cruz son las mismas de antes.
- **Ya no hay `SinMotor`:** con la opción, ningún nudo sale como siempre en silencio. Un anfitrión nuevo sin malla falla (`SinMalla`), en vez de esconderse.
- **Las plantillas, todas por el motor** (`plantillas/pasos.py`, `construir_paso`): lo ya atado con la tensión del paso y las dos puntas sostenidas de un nodo, lo que sigue suelto sin tensión (`tensiones_de_amarre`; en los amarres, los ahorcados 2,5 veces más), como el amarre cuadrado de T15d. Los puntos `quietos` no se sostienen: la memoria ya guarda la forma de la plantilla. Una plantilla puede fijar su tensión (`TENSION`) y decir que no se aprieta (`APRETAR = False`): el adujado va «suelto» y no se aprieta. El terminado apretado (`apretado_con_motor`) sale en cualquier plantilla, no solo en los amarres.
- **`referencia` y `comparar` con el motor:** `python -m nudos --motor referencia <carpeta>` construye con él y lo anota en `<carpeta>/motor.txt`; `comparar` avisa si una carpeta se armó con el motor y la otra no, y `--reimprimir` construye cada nudo como se armó `<después>`. Así T19 compara el motor contra la referencia de hoy, y un cambio del motor contra el motor de antes.
- **La vuelta de escota: el doblez lo dejaba `separar`, no el motor.** Sus correcciones (choques, largo de cada tramo y curva) se peleaban sin llegar nunca a dejar todos los tramos a 0,5 % de su largo: a las 200 vueltas la cuerda quedaba sin choques ni dobleces y a 0,6 %, y a las 2000 la gruesa doblaba en el seno con radio 0,86, que la memoria guardaba. Ahora `separar` se queda con la vuelta sin choques ni dobleces de menor error de largo, si nunca llega a 0,5 % (el largo lo termina de dar el motor, que parte de los largos de reposo h). Donde sí llegaba, como en los demás pilotos, sale igual que antes. **Con el motor, la vuelta de escota sale sin fallas:** radio 1,16 en el último paso, 1,17 en el error y 0,93 en el reverso. `test_fisica_asentar.py` lo comprueba con el paso 4.
- **Los pilotos con `--motor construir`, sin fallas:** el as de guía (1 min), el ballestrinque (1,5 min), la vuelta de escota (45 s) y el amarre cuadrado (45 s).
- **Los demás nudos con el motor, solo para ver que corren** (se calculan en T19, y ahí se corrigen):
  - Sin ninguna falla: la eslinga de andamio (tablón, 20 s), el nudo aguja (destorcedor, 2 min) y el tensor ajustable (estaca, 1 min), con su reverso y sus apretados. La eslinga de barril, también sin fallas, pero en 16 minutos.
  - Las plantillas, con `--motor construir`: el puño de mono (dedos) y el amarre redondo (dos palos), sin fallas. El amarre trípode (tres palos), con una sola: radio 0,89 en el paso 6.
  - **Fallan donde la cuerda de partida va apretada** y `separar` no le hace lugar: la vuelta de cornamusa (pasos 4 a 6 y el error: la cuerda pasa entre un cuerno, el pie y ella misma), el amarre diagonal (cinco pasos y el error: dos capas de cuerda cruzadas bajo el palo de abajo) y el refuerzo de cabo (dos pasos: las vueltas van una junto a otra, sin holgura). Es la forma de partida de esos nudos y no la malla: la cuerda que toca la cornamusa queda a 1,07 de ella. El amarre diagonal ya fallaba así en `main`, desde T15d.
  - **El adujado se rinde en el paso 3:** ahí Newton no converge, y con la regla nueva (abajo) el paso falla en unos 3 minutos; del paso 4 en adelante, `separar` deja dos tramos a 0,91. Construirlo entero tarda 5 minutos (antes de la regla, un solo paso seguía después de 50).
- **Lo que hacía falta en el motor para que sirva con cualquier nudo** (sin cambiar los pilotos):
  - **La cuerda de partida tiene que quedar fuera de la barrera** (`MallaContacto.margen`, `asentar`). Si `separar` no llega a una cuerda válida, la IPC partía dentro de la barrera: en la vuelta de cornamusa ipctk solo avisaba («Initial distance ≤ d_min») y el paso salía con nodos de la misma cuerda a 0,77; en el amarre diagonal, ipctk no podía proyectar el Hessiano de la barrera y la construcción entera se caía. Ahora el paso falla y dice cuánto queda dentro.
  - **Si Newton no converge dos pasos seguidos, el paso falla** (`MAX_SIN_CONVERGER`). En el paso 3 del adujado gastaba sus 500 iteraciones en cada paso, 90 s cada uno, y con 300 pasos habría tardado horas. Al apretar (con `aceptar`) se queda con lo más apretado que cumplía. Medido: en los cuatro pilotos ningún paso deja de converger ni una vez.
  - **El reverso que no se puede construir es una falla** (`errores.construir_reverso`), no un error que tumba `construir`.
- **Para T19:** `separar` no avisa cuando termina sin llegar; ahora lo dice la barrera, y la cuerda de partida de los nudos apretados (la cornamusa, el diagonal y el refuerzo) se corrige ahí. El filtro de vecinos de ipctk (1,5 d a lo largo de la cuerda, con el largo medio de los tramos) y el de `separar` (1,6 d) no son el mismo: en una cuerda muy doblada, ipctk ve pares que `separar` no separa. Igualarlos cambia los pilotos, así que queda para T19, que los recalcula todos. El barril tarda 16 minutos; su malla, de 5314 vértices, puede ser la causa (no lo medí).
- **Pruebas:** `tests/test_fisica_solidos.py` (1 s): en cada anfitrión, la cuerda que la geometría de siempre apoya en la madera (`empujar`) queda a dmin + dhat/2 + holgura de la malla (1,06), también con una cuerda más gruesa; y el destorcedor es de metal. `test_fisica_asentar.py` gana el paso 4 de la vuelta de escota con el motor (unos 16 s). La suite entera pasa (774, en 4 min 20 s con `-n 4`). **Sin la opción no cambia nada:** `referencia` desde un worktree de 4a6df42 y con el código nuevo, el mismo día, y `comparar --reimprimir`: los 36 `modelo.json` iguales byte a byte. Las imágenes también, salvo el paso 4 del rizo (7 píxeles, 1 nivel), que impreso otra vez desde 4a6df42 sale igual al nuevo: era el navegador.
- **Lo que no entró:** la v1.14 (`tension:` por paso) y `config/cuerdas.yaml`. Ningún piloto pide otra tensión, y los parámetros de la cuerda dependen de T15e.

**Fuera, salvo que una prueba en papel diga lo contrario:** simular los 16 hilos de la trenza (a 58 mm de ancho no se ven; la textura con relieve ya los dibuja) y la pelusa de las fibras.

**Criterios de aceptación de T15:**
- [ ] Las pruebas de física (la catenaria, la elástica, el cabrestante, la tabla inclinada y las cuerdas que no se atraviesan) pasan.
- [ ] Construir dos veces da los mismos `modelo.json` byte a byte.
- [ ] Los pilotos construyen sin fallas con el motor, con la secuencia declarada en cada paso.
- [ ] Gabriel aprueba en papel la página de prueba de los pilotos.

**Dependencias:** el punto de control E. **Tamaño:** XL, en siete subtareas. **Sesión:** modelo grande.

#### T16: Las fichas se renderizan en Blender

**Descripción:** D10 salió a favor (24 nov). `python -m nudos imprimir` dibuja con Blender los pasos, el error junto al paso correcto y el nudo terminado por delante y por detrás, y `ficha` las sigue armando con Edge. Se prueba con los nudos piloto; las fichas de todos los nudos se rehacen en T19.
- **Los nombres** («Firme», «Chicote» y los de cada cuerda) salen de la misma regla que hoy (`nombresDe` en `render/escena.js`), no del primer punto que se ve, como en T14b: en el amarre, hoy va solo «Chicote».

**Criterios de aceptación:**
- [ ] Imprimir dos veces da las mismas imágenes, o diferencias que `comparar` declara ruido. Cycles con semilla fija y un solo denoiser; si la GPU no repite el resultado bit a bit, `comparar` gana una tolerancia documentada.
- [ ] Las fichas siguen cabiendo y se leen en gris.
- [ ] Gabriel revisa en papel las fichas de los pilotos.

**Dependencias:** el punto de control E (D10) y T15; T15g se hace junto con esta. **Tamaño:** M, más el tiempo de render de unos 40 nudos: de 8 a 12 s por imagen a 256 muestras (T14b).

**Cómo se hizo T16 y T15g (25 de noviembre de 2026; Gabriel aprobó la página de prueba el mismo día):**
- **three.js arma, Blender dibuja.** La escena sigue saliendo de `render/escena.js`: Edge la arma como siempre (la cámara, el encuadre de `pose()` y los nombres de `nombresDe` y `colocarNombres`), y la función nueva `exportar()` la devuelve como datos: la matriz de la cámara, el eje de cada cuerda (los puntos de la curva de Catmull-Rom que usa el tubo) con sus tramos (base, resaltado y remate) y las demás mallas (el anfitrión, las tapas y los dedos), ya en coordenadas del mundo y con el papel de su material (`userData.rol`: madera, testa, metal, plástico…). Edge saca además una captura con solo los nombres, sobre fondo transparente (`window.soloNombres()`). Así los nombres, el encuadre y todos los anfitriones son los mismos que hoy sin escribir nada dos veces, y el visor no cambia (solo gana los `userData` y `exportar`; el sitio no se republicó).
- `nudos/blender.py` arma la malla de cada cuerda desde su eje (32 lados, la UV de la trenza un mosaico cada π diámetros, el material de cada tramo) y llama a Blender una vez por nudo con todas sus imágenes (`render/blender/escena.py`, la escena de T14b: Cycles con OptiX, 256 muestras, la trenza de escena.js con relieve, luces de área, la mesa como receptor de sombras, vista «Standard» con exposición −0,55). Después pone el render sobre blanco y los nombres encima. `imprimir` dibuja así por omisión; `NUDOS_RENDER=threejs` vuelve a three.js, y la suite lo usa salvo `tests/test_blender.py`. Blender se encuentra solo en su carpeta de Windows o con `NUDOS_BLENDER`.
- **Tiempos (RTX 4070):** de 33 a 53 s por nudo piloto, con Edge y el arranque de Blender: unos 4 s por imagen. Los 36 nudos, unos 25 minutos.
- **Imprimir dos veces:** con la semilla fija y el denoiser (OpenImageDenoise) en la CPU, quedan unos 80 píxeles sueltos del fondo con 1 nivel de diferencia: la tarjeta no repite bit a bit. `referencia` anota el render en `render.txt`, y `comparar` cuenta como igual, y lo dice aparte, una imagen que difiere en hasta 2 niveles y en no más del 0,5 % de sus píxeles, si las dos carpetas se dibujaron con Blender (`RUIDO_NIVELES`, `RUIDO_PIXELES`). Avisa si una se dibujó con Blender y la otra con three.js.
- **T15g, la sección aplastada:** donde el eje de una cuerda queda a menos de un diámetro de otra, o a menos de un radio de la madera, la sección se aplana contra el plano de contacto y se ensancha de lado, con la misma área (`APLASTAR`). **Medido en los pilotos con el motor:** entre cuerdas nunca pasa, porque el motor las deja a 1,02 diámetros como mínimo (la barrera las separa antes de 0,95); contra la madera se aplasta hasta un 7 % del radio (el ballestrinque y el amarre, por la diferencia entre el palo de 64 lados de three.js y el del motor). En la hoja de T15g de la página de prueba, ni ampliado tres veces se distingue de la cuerda redonda.
- **T15g, la torsión:** la trenza sigue el marco sin torsión del motor (`marco_paralelo`, que empieza lo más cerca de +z). Con el chicote suelto la cuerda no guarda torsión (T15b), así que es el mismo transporte paralelo que ya hacía three.js: no hay nada nuevo que se vea.
- **Las fichas:** `python -m nudos --motor ficha <slug>` de los cuatro pilotos arma su pliego con las imágenes de Blender.
- **La página de prueba:** `python -m nudos prueba-blender` deja `build/blender/prueba.pdf`: cada imagen de la ficha de los cuatro pilotos con three.js junto a la de Blender, las dos con la cuerda del motor, en color y en gris, al 76 %, y la hoja de T15g.
- **Punto de control (Gabriel, 25 nov):** Blender se ve mejor que three.js en todos los casos, y el aplastado queda activo (`APLASTAR = True`).

#### T17: Animación entre pasos (cerrada)

Cerrada el 25 nov: Gabriel aprobó los 10 s de prueba del as de guía y del amarre. El diseño y su «Cómo se hizo» están en el historial. La orden es `python -m nudos prueba-atar`. Lo que dejó abierto para T18:
- **El amarre dura 94 s,** no 40. La mano recoge y vuelve a dar en cada paso los 20 d de cola que la ficha deja sobre la mesa, y no puede ir a más de 10 d/s, que es un nodo por cuadro. Para acortarlo, la mano puede llevar la cola o dar dos nodos por cuadro.
- **Quedan saltos de un cuadro:**
  - 0,6 d en la gaza pequeña del as de guía, porque el lazo nace apretado.
  - De 0,3 a 0,8 d en la punta del amarre, cuando la mano se zafa de un contacto.
- **El encuadre del as de guía** incluye el firme hasta el borde, así que el nudo queda chico y a un lado.
- **Falta el nudo terminado apretado** al final del video (punto 6 del diseño).
- **Una marca oscura chica sobre la mesa** en el video del amarre, sin revisar: puede ser una malla de la escena exportada.

#### T18: Videos

**Descripción:** un video por nudo, renderizado en Blender y armado con ffmpeg, con el título de cada paso en pantalla (el texto propio de la especificación, en tuteo y sin términos de sección).
- **El formato (Gabriel, 24 nov): lo mejor que acepta cada plataforma.**
  - **Horizontal, para YouTube:** 3840 × 2160 a 60 cuadros por segundo y 68 Mbps, el tope de lo que YouTube recomienda para 4K a 60 fps en SDR (de 53 a 68 Mbps). H.264 en `.mp4` con el índice al principio (`-movflags +faststart`), color 4:2:0, tasa variable y la misma tasa de cuadros de punta a punta.
  - **Vertical, para los reels de Instagram:** 1080 × 1920 a 60 fps, con una tasa alta (unos 20 Mbps) para que la recompresión de Instagram pierda poco. Instagram muestra los reels a 1080 × 1920 y baja a eso lo que se sube en 4K, así que renderizarlo en 4K costaría cuatro veces más sin que se vea.
  - **En el visor:** una copia del horizontal en 1920 × 1080 a 60 fps y unos 8 Mbps, sacada del original en 4K con ffmpeg (unos 30 MB por cada 30 s). El original no cabe: 30 s a 68 Mbps son unos 255 MB, y GitHub no acepta archivos de más de 100 MB.
- **En el visor:** horizontal, en la página del QR. El sitio hoy no acepta imágenes ni video, así que la lista de tipos de la decisión de arquitectura 7 gana `.mp4`, con un tope de tamaño. El video vive dentro del sitio, sin YouTube, para que el visor no dependa de servicios externos.
- **En redes:** el horizontal en YouTube y el vertical en Instagram. Dónde y cuándo se publica lo decide Gabriel.

**Diseño (25 nov; Gabriel lo aprobó el mismo día).**

*1. La orden.* `python -m nudos video <slug> [--previa] [--solo horizontal|vertical]` siempre usa el motor (pone `NUDOS_MOTOR=1`) y hace esto, en orden:
1. Construye el nudo. Si tiene fallas, no sigue.
2. Lo ata con el modo «atar» de T17 y guarda los cuadros en `build/<slug>/video/cuadros.npz`, con la huella del `modelo.json` y de la versión de `animar.py` y `fisica/atar.py`. Si la huella no cambió, no lo vuelve a atar: así, cambiar un título o la cámara no cuesta los 20 minutos del motor.
3. Arma la línea de tiempo: la velocidad de cada parte (punto 3), el apretado (punto 6), las pausas, los títulos y las cámaras de los dos formatos.
4. Dibuja cada formato en Blender, cuadro por cuadro, en una carpeta fuera de A: (`NUDOS_CUADROS`; por omisión, `%LOCALAPPDATA%\nudos\cuadros\<slug>\<formato>\`). Un cuadro en 4K pesa unos 12 MB y un nudo tiene unos 2700: son 30 GB que Drive no tiene que respaldar. Se puede retomar: si el render se corta, el cuadro que ya está con la misma huella no se vuelve a dibujar.
5. Arma los videos con ffmpeg en `%USERPROFILE%\Videos\nudos-431\<slug>\` (`NUDOS_VIDEOS`): `<slug>-4k.mp4`, `<slug>-vertical.mp4` y `<slug>-visor.mp4`. Los dos primeros pesan unos 400 y 120 MB, así que tampoco van a A:. La copia del visor se copia además a `videos/<slug>.mp4`, en el repositorio (punto 8).

Con `--previa`, el nudo entero en 960 × 540, 30 fps y 16 muestras, en unos minutos, para ver los tiempos, la cámara y los títulos antes del render largo.

*2. El formato, en ffmpeg.* Los tres videos van sin audio (pregunta 1, abajo), en H.264 4:2:0 y con el índice al principio. El color se pasa a YUV con la matriz BT.709 y se marca como BT.709. Sin eso, el azul de la marca cambia de tono en el reproductor.
- **4K:** `-b:v 68M -maxrate 68M -bufsize 136M`, perfil High y nivel 5.2. Un cuadro clave cada 30 cuadros y dos cuadros B, como pide YouTube.
- **Vertical:** `-b:v 20M -maxrate 25M`.
- **Visor:** sale del 4K, bajado a 1920 × 1080 con Lanczos, con `-crf 20 -maxrate 4M`. Tiene un tope de **20 MB**. Bajé los 8 Mbps de la descripción porque GitHub Pages no publica un sitio de más de 1 GB, y 36 videos de 30 MB ya pasan de ahí. Un fondo blanco con poco movimiento se comprime bien a 4 Mbps, pero eso se revisa en el punto de control. Si un video pasa el tope, la orden falla y dice cuánto pesa.

*3. La duración.* El amarre dura 94 s; la meta es unos 45.
- **En una plantilla, la cola va en la mano.** Hoy, en cada paso, la mano recoge los 20 d de cola que la ficha deja sobre la mesa y los vuelve a dar: en el amarre son 27 s de los 94. En el video, la pausa de cada paso intermedio muestra la cuerda de la ficha hasta el hito del paso, más 4 d de cola en la mano, así que no hay nada que recoger. La pausa del último paso sí es la ficha entera. Esto cambia una regla de T17 («en cada pausa se ve exactamente la pose de la ficha»): en una plantilla, se ve hasta el hito.
- **Lo que se repite va en cámara rápida.** El video recorre la simulación a otra velocidad, sin cambiar la del motor (que se queda en 10 d/s como máximo, sin amontonar nodos). En un paso de plantilla, los primeros 10 d de cuerda nueva van a velocidad normal y lo demás va al doble. En los pasos que terminan una serie (`hasta: vueltas` o `ahorcados`), lo demás va al triple. Cada cambio de velocidad tarda 0,5 s. Un cuadro del video que cae entre dos de la simulación se interpola en línea recta, que es justo lo que `comprobar` verificó como libre entre esos dos cuadros. Donde cambia la cantidad de nodos, se toma el cuadro más cercano.
- **Estimado:** el amarre, unos 45 s, y el as de guía, unos 44 (los 40,6 de hoy más el apretado y la pausa final). El motor tarda lo mismo o menos que en T17, porque ya no recoge ni vuelve a dar la cola.

*4. Los saltos de un cuadro.* La medida `salto_max` pasa a ser una falla: entre dos cuadros de la simulación, ningún nodo se mueve más de **0,35 d**. La mano más rápida mueve 0,17.
- **La gaza pequeña del as de guía (0,6 d).** `_tramo_firme` lleva cada nodo en línea recta de A a B. Por eso, en los primeros cuadros el lazo es una copia chica del final, con mucha curvatura, y el motor lo abre de golpe. La guía de ese tramo pasa a interpolar el ángulo de la tangente a lo largo de la cuerda, y no las posiciones. Con eso, la curvatura en cada cuadro es una fracción de la de B y el radio nunca es menor que el de la ficha: el lazo nace grande y se cierra, como cuando lo hace una mano. Lo que falta para que la punta llegue a su lugar se reparte en línea recta a lo largo del tramo, lo que no agrega curvatura. Las alturas siguen saliendo de `alturas()`. Lo mismo vale para «acomodar».
- **La punta del amarre (de 0,3 a 0,8 d).** La mano tira con un resorte de 200 N/d. Cuando la punta se traba en una vuelta, el resorte se carga y, al zafarse, la punta salta. La mano pasa a esperar a la punta: si la punta queda más de 0,15 d atrás de su meta, la guía no avanza en ese cuadro y repite la meta, así que el resorte nunca guarda más de 30 N. En el video se ve como una mano que se detiene un instante. El tiempo de más se mide; T17 ya cuenta las «esperas».

*5. El encuadre.* Hoy cada toma encierra toda la cuerda que cabe en el encuadre de la ficha, más un margen de 3 d, y eso incluye el firme hasta el borde. Pasa a encerrar solo el nudo: la cuerda desde 6 d antes del primer cruce de A o de B (sin cruces, desde 6 d antes del tramo resaltado) hasta la punta, más lo que mueve la guía. El firme sale del cuadro por el borde, como en una foto de cerca. Si el nudo es muy chico, la toma tiene un mínimo de 8 d de semiancho, para que en los primeros pasos no salga demasiado cerca.

*6. El nudo terminado, al final.*
- **En un nudo libre**, `apretar()` del motor (el modo 2) guarda cada paso cuasiestático hasta el que `aceptar` elige, que es el de `modelo.apretado`. Esos estados se reparten en 1,5 s con arranque y frenado suaves. `comprobar` revisa los cuadros como en T17, y si la recta entre dos pasos no queda libre, se guardan también las iteraciones de Newton de ese paso.
- **En una plantilla**, la tensión pasa de «ajustada» a «apretada» en 1 s, con el mismo registro.
- **Al final**, 2,5 s quieta en el nudo apretado, con la cámara acercándose un 10 %.

*7. El título de cada paso en pantalla.*
- Dice «Paso 4 de 7» en letra chica y, debajo, el título de la especificación («Sube por la gaza»), con `{vueltas}` y `{ahorcados}` ya en letras. Durante la pausa del paso 1 aparece además el nombre del nudo. Antes de dibujar, el texto pasa por la misma comprobación de términos de sección que la ficha.
- Aparece cuando empieza el movimiento del paso y se queda durante su pausa, con fundidos de 0,25 s.
- **Lo dibuja Edge**, en HTML con las fuentes del sitio (`sitio/vendor/fuentes`), sobre fondo transparente, como ya se hace con los nombres de las fichas: una imagen por paso y formato. Pillow la pone sobre cada cuadro, así que el tipo es el mismo de la ficha y del visor. Si un título no cabe en dos líneas, la orden falla.
- **Dónde va:**
  - En el horizontal, abajo a la izquierda, dentro del 90 % seguro del cuadro.
  - En el vertical, arriba, entre el 12 % y el 22 % del alto. Instagram tapa el 25 % de abajo con el texto del reel y los botones, y el borde de la derecha con los íconos.
- Los nombres «Firme» y «Chicote» de las fichas no entran al video: con la cuerda moviéndose, saltarían.

*8. El video en el sitio.*
- **Los archivos.** El sitio se construye desde `main` (`scripts/publicar.sh`), así que la copia del visor vive en git, en `videos/<slug>.mp4`, con una línea por video en `videos/LEEME.txt` que dice de qué commit y de qué fecha es. `python -m nudos sitio` la copia a `build/sitio/<slug>/video.mp4` si el nudo está en `publicados.txt`. La URL del visor (`/<slug>/`) no cambia: el video es un archivo más dentro de esa carpeta, sin QR propio.
- **Las reglas.** `EXTENSIONES` gana `.mp4`, y el sitio falla si un video pasa los 20 MB o si el sitio entero pasa los 900 MB, para quedar bajo el límite de 1 GB de GitHub Pages.
- **En la página.** El visor gana un botón «Ver el video», debajo del modelo 3D. Al tocarlo aparece un `<video controls playsinline preload="none">` horizontal, sin reproducción automática, para no gastar los datos de un celular que solo quería el modelo. Sin video, la página queda igual que hoy. La página no usa póster, porque el sitio sigue sin aceptar imágenes.
- **El costo en el repositorio (pregunta 3).** Son 36 videos de hasta 20 MB: unos 700 MB en `main`, y otro tanto en `gh-pages` cada vez que cambian todos, porque `publicar.sh` agrega un commit encima del anterior. GitHub recomienda repositorios de menos de 1 GB y avisa desde los 5.

*9. La cámara del vertical.* Usa las mismas tomas por paso, con su propio encuadre. `toma()` pasa a encuadrar la caja del nudo dentro de un área útil del cuadro, y no del cuadro entero:
- en el horizontal, el 80 % de arriba, para no tapar el título;
- en el vertical, la franja entre el 22 % y el 75 % del alto.

Como el as de guía es más ancho que alto, en el vertical el ángulo alrededor de la mesa se elige, de 30° en 30° y a no más de 90° del horizontal, para que el nudo salga lo más grande posible (pregunta 2). En una plantilla, sigue mandando que los palos tapen lo menos posible de la cuerda nueva.

*10. La marca oscura sobre la mesa del amarre.* Es la tapa de la punta (`rol: "punta"`) que `escena.js` exporta con la cuerda del paso 1. `mallas_anfitrion` solo saca las mallas con rol «cuerda», así que la tapa se queda fija sobre la mesa en todo el video. Se ve en la prueba de T17, abajo a la izquierda. El arreglo es sacar también «punta» y «dedo». Se confirma listando los roles que exporta.

*11. El costo de render, medido (25 nov, RTX 4070).* Medí 6 cuadros del enhebrado de cada piloto, con la escena de T16:

| Tamaño | Muestras | Denoiser | s por cuadro |
|---|---|---|---|
| 1280 × 720 | 64 | CPU | 3,5 (amarre) y 6,8 (as de guía) |
| 3840 × 2160 | 64 | CPU | 31 |
| 3840 × 2160 | 64 | tarjeta | 12,8 |
| 3840 × 2160 | 32 | tarjeta | 8,5 |
| 3840 × 2160 | 16 | tarjeta | 6,5 |
| 1080 × 1920 | 32 | tarjeta | 2,0 |

- **El denoiser en la CPU es lo que más cuesta en 4K.** En la tarjeta, el cuadro baja de 31 a 13 s. Las fichas lo dejan en la CPU para que imprimir dos veces dé lo mismo. En un video eso no hace falta, así que `video` lo pone en la tarjeta.
- **32 muestras alcanzan.** En el as de guía, 32 y 64 muestras difieren en 0,3 niveles de 255 en promedio, y solo el 0,08 % de los píxeles en más de 8 niveles. La comparación del amarre no vale: el cuadro de 32 muestras salió sin el tramo resaltado. Lo reviso al implementar, porque puede ser un error de la escena.
- **Queda un costo fijo de unos 4 s por cuadro en 4K**, el mismo con 16 que con 64 muestras. Es armar toda la escena en cada cuadro (`vaciar()`, los materiales, las texturas de la trenza de 1024 px, la mesa y el anfitrión), el denoiser y escribir el PNG. `use_persistent_data` casi no lo baja (de 8,5 a 8,0 s). La escena pasa a armarse una vez por llamada a Blender: en cada cuadro solo se cambia la malla de la cuerda, la cámara y, si cambian, las luces. Los PNG se escriben con compresión baja. **Meta: unos 6 s por cuadro en 4K.**
- **Los cuadros repetidos se dibujan una vez.** En las pausas, con la misma pose y la misma cámara, se dibuja un cuadro y se copia. Es cerca del 10 %.
- **Por nudo (unos 45 s, 2700 cuadros):**
  - el horizontal, de 4 a 6 horas (de 6 a 8,5 s por cuadro);
  - el vertical, 1,5 horas;
  - el motor, de 5 a 20 minutos.
- **Los dos pilotos:** de 11 a 15 horas, de noche.
- **Los 36 nudos de T19:** de 200 a 270 horas, de 8 a 11 días de render seguido. Es menos que las 340 a 560 horas que estimaba la descripción, pero sigue siendo mucho (pregunta 4).

*12. Los módulos.*
- `nudos/video.py`: la orden, la línea de tiempo con la velocidad, los títulos, el armado y ffmpeg. Toma de `prueba_atar.py` la línea de tiempo y la cámara, que pasan a este módulo, y `prueba-atar` las importa de aquí.
- `nudos/animar.py`: la cola en la mano, la interpolación por ángulo, el encuadre del nudo y el apretado.
- `nudos/fisica/atar.py`: la mano que espera y la falla por salto.
- `render/blender/escena.py`: el modo video, con la escena armada una sola vez y el denoiser en la tarjeta.
- `render/titulo.html`: el título de cada paso.
- `nudos/exportar.py`, `sitio/plantilla.html` y `sitio/visor.js`: el video en el visor.
- **Pruebas, rápidas:**
  - la velocidad interpola bien y no saca cuadros fuera de la simulación;
  - la interpolación por ángulo no baja del radio de B;
  - la mano que espera no deja saltos de más de 0,35 d con el gancho de T17;
  - los títulos caben;
  - el sitio acepta `.mp4` con el tope y rechaza uno de más;
  - el visor sin video queda igual.

*Lo que decidió Gabriel (25 nov, al aprobar el diseño).*
1. **Sin audio** por ahora. Puede que más adelante quiera agregarle. *(Cambió el 26 nov: los tres videos llevan efectos de sonido sintetizados; ver «Cómo se hizo T18», punto 7.)*
2. **El vertical puede girar el nudo** hasta 90° respecto de la ficha.
3. **Los videos del visor van en `main`.** `publicar.sh` no cambia.
4. **T19 en 4K a 60 fps, sin reescalar, y lo corre Gabriel.** Una sola orden pone todos los nudos en cola y los va haciendo uno tras otro, para dejarla corriendo de noche: `python -m nudos video --todos` (o con varios slugs). Si se corta, al volver a correrla sigue donde quedó: no vuelve a atar los nudos con la misma huella, no vuelve a dibujar los cuadros que ya están y no vuelve a armar los videos que ya están completos. Al terminar cada nudo anota en `NUDOS_VIDEOS/cola.txt` lo hecho, lo que falló y cuánto tardó. Un nudo que falla no detiene la cola. Esto se implementa en T18 y se prueba con los dos pilotos.

**Criterios de aceptación:**
- [ ] `python -m nudos video <slug>` arma los dos formatos.
- [ ] Los dos pilotos se atan sin fallas, sin saltos de más de 0,35 d entre cuadros y terminan con el nudo apretado. El amarre dura 50 s o menos.
- [ ] El visor del as de guía muestra su video, de 20 MB o menos, y la URL del QR no cambia.
- [ ] Gabriel aprueba los videos de los pilotos; los de los demás nudos se arman en T19.

**Dependencias:** T17. **Tamaño:** M, más el tiempo de render. T14b midió unos 7 s por cuadro a 1280 × 720 con 64 muestras, a 30 fps: los 36 nudos en dos formatos, de 30 a 50 horas. Con el formato de arriba, si el tiempo crece con los píxeles y los cuadros, el horizontal cuesta 18 veces eso (9 veces los píxeles y el doble de cuadros) y el vertical, 4,5 veces: de 340 a 560 horas, de dos a tres semanas de render seguido. (El 25 nov se midió el tiempo real: está en el punto 11 del diseño.) T16 mide el tiempo real por cuadro en 4K y busca bajarlo (la GPU, menos muestras con el denoiser) antes de comprometer los 36 videos. El vertical se renderiza con su propia cámara: recortar el horizontal corta el nudo.

**Cómo se hizo T18 (25 y 26 de noviembre de 2026; Gabriel aprobó las previas y el audio el 26 nov; faltan los videos en 4K, que renderiza él):**
- **Los módulos:**
  - `nudos/video.py` tiene la orden (`python -m nudos video <slug> [...] [--todos] [--previa] [--solo …]`), el atado guardado con su huella, la línea de tiempo con la velocidad, la cámara de cada formato, los títulos, Blender, ffmpeg y la cola.
  - Toma de `prueba_atar.py` algunas piezas chicas (`_mirar`, `_tapado`, `_mezclar`, `_tramos` y `mallas_anfitrion`), en vez de moverlas: `prueba-atar` sigue igual.
  - `render/blender/escena.py` gana el modo video: la escena se arma una vez por llamada, cada cuadro cambia solo la cuerda, la cámara y las luces, y el denoiser va en la tarjeta.
  - `nudos/exportar.py`, `sitio/plantilla.html` y `sitio/visor.css` muestran el video en el visor.
- **Dónde quedan las cosas:**
  - El atado y los cuadros, en `NUDOS_CUADROS/<slug>/` (`%LOCALAPPDATA%\nudos\cuadros`). El diseño ponía el atado en `build/<slug>/video/`, pero el del amarre pesa unos 80 MB y queda mejor junto a sus cuadros, fuera de Drive.
  - Los videos, en `build/videos/<slug>/` (Gabriel, 25 nov: los quiere en la carpeta del libro; `NUDOS_VIDEOS` da otra), con un `.json` al lado de cada uno con la firma de sus cuadros. La cola anota cada nudo en `build/videos/cola.txt`.
  - **Los cuadros se borran en cuanto su video queda armado.** Un cuadro en 4K pesa unos 33 MB, no 12, así que el horizontal de un nudo ocupa unos 78 GB mientras se dibuja, y C: tiene 95 GB libres. Volver a correr la orden con un video ya armado no los necesita: lo reconoce por su firma.
  - **Dos renders a la vez en la misma tarjeta** (medido, 25 nov): cada cuadro en 4K tarda 14,6 s en vez de 8,5. Son 7,3 s por cuadro, solo un 15 % más rápido, así que la cola dibuja uno a la vez.
- **Lo que cambió del diseño, medido:**
  - **La gaza pequeña (punto 4).** Interpolar el ángulo de la tangente no sirve: con las colas alineadas, el ángulo de la cola gira 2πu, y corregir la punta estira la cuerda hasta un 30 %. Suavizar la recta tampoco: de A a B la cuerda pasa por una cúspide (doblada sobre sí misma), y llevar cada nodo al medio de sus vecinos no la abre. Lo que funcionó es que la cuerda no siga a la guía donde la guía dobla más cerrado que `RADIO_GUIA` (1,5 d, el radio de la gaza pequeña de la ficha): ahí el resorte hacia la guía se afloja (con el cuadrado del radio sobre 1,5, también 1,5 d a cada lado) y la memoria no pide más curva que esa (`_aflojar`). La cuerda forma el lazo sola, con su rigidez. El salto baja de 0,6 a 0,34 d, y el motor tarda 35 s en ese paso en vez de 300.
  - **La punta del amarre (punto 4).** Que la mano espere a la punta costaba demasiado: la mano siempre queda algo atrás cuando arrastra cuerda con roce, así que el paso 3 repetía 2803 cuadros (47 s). Y al pasar los 30 cuadros de espera, la punta se soltaba igual (0,48 d). Se quitó. En su lugar, `repartir_saltos` reparte un cuadro que salta más de 0,35 d en los subpasos del motor que llevan a él, que son estados reales y ya comprobados. Si un subpaso todavía salta de más, lo reparte en línea recta, que es la que `comprobar` verifica libre entre dos estados. El salto queda en dos a cinco cuadros. En el amarre se agregaron 10 cuadros así (4 en el paso 2 y 6 en el 3), y el salto más grande queda en 0,34 d. En el as de guía no hizo falta.
  - **El apretado (punto 6).** En el as de guía son los pasos del modo 2 del motor, guardados con `trayectoria` (en `asentar` y `apretado_delante`). En el amarre, la recta del último paso al apretado de la ficha queda libre según `comprobar`, así que no hizo falta asentar otra vez. `video` pone `NUDOS_MOTOR=1`: sin eso, el apretado no tomaba el motor, iba en línea recta y la cuerda se atravesaba.
  - **La velocidad (punto 3).** Al doble y al triple, el amarre duraba 55,7 s. Con el triple en lo nuevo después de los primeros 6 d de cada paso, y el quíntuple en los pasos que terminan una serie, dura 48,1 s. El as de guía dura 45,1 s.
  - **Los títulos** se agrandaron en el vertical (×1,6), porque se leen en un celular. El nudo va entre el 29 % y el 76 % del alto.
  - **El encuadre del as de guía (punto 5).** Un paso sin cruces (el 1) se corta desde el primer cruce del paso siguiente.
  - **La marca oscura (punto 10)** era la tapa de la punta del paso 1 (rol «punta»). `mallas_anfitrion` ya no la exporta, y en la previa del amarre no aparece.
- **Pruebas:** `tests/test_video.py` (la velocidad, los fundidos, la cúspide, el reparto de los saltos, la toma dentro del área útil, las series, y el sitio con video, sin video y con un video de más). `tests/test_audio.py` (dónde roza la cuerda, el clic y el golpe en su lugar y su nivel, la pista sin ceros seguidos, pegar el audio sin tocar la imagen y el sello viejo). La suite entera: 800 pruebas en 5 minutos, antes del audio.
- **Las previas** de los dos pilotos se armaron sin fallas (`--previa`, 0,6 s por cuadro).
- **El render, más rápido (Gabriel, 26 nov: «el CPU está casi sin usar»).** Medido durante el render del amarre: en cada cuadro la tarjeta trabaja cerca de 1,5 s y queda sin uso unos 2 s, con un solo núcleo ocupado. Se cambiaron cinco cosas:
  1. **Escena persistente:** el modo video pasó a `render/blender/video.py`, con `use_persistent_data`. La cuerda es siempre el mismo objeto con otra malla, y las luces solo se mueven cuando cambia la toma. Cycles ya no vuelve a subir las texturas ni el anfitrión en cada cuadro.
  2. **El PNG sin comprimir:** en 4K pesa casi lo mismo y no ocupa un núcleo.
  3. **Una sola llamada a Blender por formato,** en vez de una cada 120 cuadros. Mientras dibuja, hasta 8 procesos le preparan las mallas, a lo más 48 cuadros por delante, y Blender espera cada npz. Cada cuadro se guarda en cuanto Blender lo termina, así que si la orden se corta se pierde a lo más uno.
  4. **Armar el video** compone los cuadros sobre blanco, con sus títulos, en hasta 8 procesos y en orden.
  5. **La cola** construye y ata el nudo siguiente en otro hilo mientras Blender dibuja el actual.
  6. **El cuadro entero de una vez** (sin las teselas de 2048 px que Cycles usa por omisión) y **un muestreo adaptativo más permisivo**: umbral de ruido 0,03 en vez de 0,01 (Gabriel, 26 nov). Están en `CYCLES`, en `nudos/video.py`, y van en la huella de cada cuadro, porque el adaptativo puede cambiar un poco el dibujo. Gabriel descartó reescalar y bajar las muestras hasta ver la medición.
  7. **El audio (Gabriel, 26 nov).** Tres efectos sintetizados en `nudos/audio.py`, sin grabaciones ni bancos de sonido, así que no tienen licencia de nadie:
     - **El clic,** al aparecer el título de cada paso: un tono de 2,6 kHz con otro una octava arriba y otro una abajo, con pico a −8 dB.
     - **El golpe,** al terminar de apretar el nudo: un tono grave que baja de 150 a 55 Hz y un chasquido, con pico a −5,5 dB.
     - **El roce:** granos cortos, un impulso o un soplo de ruido por un resonador, como los tirones de la trenza al deslizar. Suena solo donde la cuerda roza, medido en cada cuadro: contra otra parte de la cuerda (el vecino más cercano a menos de 1,12 d que no es la misma parte), contra el anfitrión (sus muestras de superficie, las del aplastado de T15g, así que sirve con cualquier anfitrión) o al arrastrarse por la mesa. Cuanto más largo el roce y más rápido, más granos por segundo, que crecen con la potencia 0,6 del roce para que los grandes no tapen a los chicos. Cada grano tiene su pico (−16 dB), y el volumen sale de cuántos hay.
     - **Cómo se llegó, con dos pruebas sobre las previas:** el primer roce, ruido filtrado con el volumen de la velocidad, «suena más a ruido» (Gabriel). Al roce granular, subirle el volumen y limitarlo aplanaba todos los granos al mismo techo. El clic de la primera prueba le gustó, pero lo quería con más presencia: subió 4,7 dB frente al golpe, que no cambió.
     - **ffmpeg 9.1** deja de entregar el AAC cuando hay segundos de ceros exactos (las pausas) y el video no se arma, así que la pista lleva un ruido a −80 dB. Su `loudnorm` también devolvía una pista vacía con estos audios, así que no se usa.
     - **El audio se pega aparte** (`audio.pegar`, que copia la imagen sin volver a codificarla) y tiene su propio sello: si cambia, se vuelve a pegar en segundos, sin dibujar. La copia del visor lleva el mismo audio.
  8. **El sello de un video ya no depende del código de `nudos/video.py`,** sino de lo que decide su imagen (`firma_imagen`: los cuadros, los títulos, `ARMADO` y la codificación). Como los cuadros se borran al armar el video, antes cualquier cambio a ese archivo obligaba a dibujar todo otra vez. Un video armado con el sello anterior se reconoce por su cantidad de cuadros (`ya_armado`).
  9. **La revisión de Gabriel de las previas (26 nov):** «la cuerda se ve rara en ciertos movimientos», «parece que toda la cuerda brinca» y «se nota que la punta está hueca». Medido en los cuadros del video a 60 fps:
     - **Los brincos venían de recoger cuerda.** El último tramo tomaba en cada cuadro el largo que medía. Al acercarse la mano, quedaba comprimido, y como la cuerda casi no se encoge, empujaba al nodo de al lado: la mano nunca lo alcanzaba, la cuerda de adelante se arrugaba, el último tramo llegaba a 2,3 d y la punta saltaba hasta 2,3 d de un cuadro al siguiente. `salto_max` no lo veía porque solo comparaba cuadros con la misma cantidad de nodos. Ahora, al recoger, el tramo de la mano toma el largo de la guía (`CuadroGuia.recoge`). `saltos` y `repartir_saltos` alinean también los cuadros en que se da o se quita cuerda (`_ajustar`, como `comprobar`), y los de más de 0,35 d al dar cuerda (hasta 0,45) se reparten en los subpasos del motor. Queda en 0,34 d como mucho en el motor. En el video, el amarre llega a 0,40 d por cuadro solo en la punta durante la cámara rápida, que es movimiento y no un salto.
     - **El remate en codo** (de 112° a 133° entre el último tramo y el diámetro de antes) era sobre todo eso mismo. Además, `punta_suave` dibuja el último diámetro y medio sobre una curva suave cuando la cuerda dobla más de 25° en un nodo: queda en 26° como mucho, repartido.
     - **La punta hueca:** en el video la malla de la cuerda no tenía tapas (las de las fichas las pone `escena.js`). `malla_cuerda(..., tapas=True)` cierra cada punta con una cúpula baja, con el material del tramo de esa punta.
     - Pruebas: recoger la cola del gancho sin empujar la cuerda (falla sin el arreglo, con un salto de 1,85 d), los saltos al quitar un nodo, el reparto al dar cuerda, la punta sin codo y la malla cerrada.

  La huella de cada cuadro no cambió, porque el dibujo es el mismo. Probado con 8 cuadros de la previa de cada piloto: cada uno muestra su cuerda, que avanza de un cuadro al siguiente, con el resaltado. Falta medir el 4K cuando termine el render de Gabriel. El modo video viejo de `escena.py` se queda hasta entonces, porque ese render todavía lo usa.
- **El render en 4K, medido:** 8,0 s por cuadro con todo incluido: armar la malla de cada cuadro en Python, Blender con la escena armada una vez y el denoiser en la tarjeta, y escribir el PNG. No llega a la meta de 6 s. Las pausas ahorran el 14 % de los cuadros del as de guía (2338 distintos de 2704). Así, cada piloto en 4K tarda unas 5 horas, y con el vertical (unos 2,5 s por cuadro), unas 7 horas por nudo: los 36 nudos de T19, unos 10 u 11 días de render seguido.

#### El pulido a fondo: T20 a T24 (propuesta del 26 nov; Gabriel la aprobó el mismo día)

**De dónde sale.** Gabriel (26 nov) sintió que el render de Blender, el motor de física y el sonido no tuvieron la profundidad necesaria. Era el pendiente de T18 «Pulir a fondo el render en Blender y el motor de física». Pidió:
- **Render:** más elaborado, un material de cuerda con textura y relieve de verdad, una escena menos plana, videos más fluidos y videos más largos y útiles (paso a paso, errores comunes y una aplicación). Se pueden instalar complementos y programas.
- **Motor:** una cuerda que se mueva con fluidez y que no se encoja en cada paso.
- **Sonido:** más dinámico, con música (la elige o la crea Claude) y con voz.
- **Varios:** la marca naranja del chicote a veces deja de verse cuando la cuerda se encoge, y la tarjeta de los pasos puede ser más llamativa.
- **Repositorios para revisar:** lygia, react-three-rapier, react-postprocessing, librosa y video-shotcraft (abajo, qué se usa).

Va antes de T19: si T19 corriera hoy, gastaría 10 u 11 días de render en un aspecto que se va a cambiar. **El resultado esperado:** un video por nudo que enseña (el paso a paso con voz), corrige (los errores), muestra para qué sirve (la aplicación) y se ve y suena como un producto profesional, con una cuerda que se mueve como cuerda. Las fichas impresas solo cambian si se leen mejor en papel.

**Lo que decidió Gabriel (26 nov):**
1. **Video completo y reel.** Cada nudo tiene un horizontal de unos 2 min con apertura, paso a paso con voz, cómo revisar que quedó bien, errores comunes, aplicación y cierre, y capítulos para YouTube. El visor lleva el capítulo del paso a paso, por el límite de 1 GB del sitio. Además, un reel vertical de 45 a 60 s.
2. **La voz:** primero el mejor modelo local gratis, sin importar cuánto tarde en generarse. Si ninguno convence, ElevenLabs.
3. **Las aplicaciones son con objetos,** y D1 no cambia: solo los amarres sostienen personas. La propia ficha de la eslinga de andamio dice «no la uses como andamio ni como columpio», así que su aplicación es una repisa colgante. Si la ficha tiene sección de seguridad, entra también al video.
4. **Render: unas 2 semanas para los 36 nudos.** La prueba del cuadro final mide Cycles contra EEVEE, y el video usa el que se vea mejor dentro de ese tiempo. Las fichas siguen en Cycles.
5. **La música la elige y la crea Claude** (T23).

**Lo que había (medido el 26 nov):**
- **La cuerda en Blender** es un tubo de 32 lados, con la trenza como textura y relieve (bump), sin geometría, con rugosidad 0,8 y sin brillo de tela (dejaba un halo en el borde de los cruces). En el video hay un anillo cada 0,2 d sin suavizar (las fichas usan 0,08 d con Catmull-Rom), y todas las cuerdas son azules, así que los nudos de dos cuerdas saldrían mal.
- **La escena:** el render va sobre blanco. La mesa solo recibe sombras y nunca se ve, el fondo es de un color plano y hay dos luces de área. La vista es «Standard» con exposición −0,55, porque AgX lavaba el azul. No hay profundidad de campo, ni desenfoque de movimiento, ni compositor.
- **«Encogerse».** Cada paso de la ficha es un dibujo aparte, con su propio largo (el as de guía: 71,0, 87,6, 84,6, 86,8, 94,9, 102,6 y 109,7 d). El video conserva cada pose exacta, así que la mano *recoge* la punta (quita nodos: 2,2 s en los pasos 3 y 4 del as de guía) y después *enhebra* (`_partir` agrega nodos, y la cuerda le sale de la mano).
- **La «marca naranja»** es el resaltado ámbar del tramo que se mueve. Va por índice de nodo (`_tramos` en `prueba_atar.py`), así que desaparece cuando la cuerda se acorta por debajo de su comienzo, o cuando la pausa de una plantilla corta la cuerda en el hito. El remate del chicote (granate oscuro, 0,8 d) casi no se ve con la exposición −0,55.
- **El movimiento:**
  - Cada nodo tiene un resorte de 5 N/d hacia la guía, y la viscosidad (0,2 N·s/d) pesa unas 6000 veces más que la inercia. La cuerda no se mueve como cuerda: se deforma hacia la guía como una masa espesa.
  - «Acomodar» lleva cada nodo en línea recta, que es un morph.
  - Las velocidades de la mano cambian en seco (de 5 a 2,5 d/s cerca de un cruce).
  - Las plantillas van en cámara rápida (×3 y ×5), y `retiempo` toma el cuadro más cercano cuando cambia la cantidad de nodos, que al enhebrar es casi siempre.
- **El video:** dura unos 45 s y solo trae los pasos. El paso 1 no se anima. La cámara mezcla dos tomas en línea recta, se queda quieta 0,5 s y se mueve 0,8 s. La tarjeta es HTML de Edge, con un fundido lineal de 0,25 s.
- **El sonido:** mono, con los tres efectos de T18 (el clic, el golpe y el roce granular, que Gabriel aprobó). No tiene música ni voz, y la sonoridad no está normalizada.
- **El costo:** 8 s por cuadro en 4K, unas 7 h por nudo con el vertical. El motor tarda unos 15 min por piloto.
- **El visor:** three.js 0.160.0 con ACES, sombras VSM y la trenza en un canvas de 512 px. No tiene postprocesado ni mapa de entorno, y el cambio de paso es instantáneo. La versión 0.160 ya trae AgX y la anisotropía del material físico.

**Las tareas:**

| Tarea | Qué | Tamaño | Sesión |
|---|---|---|---|
| T20 | El aspecto: material, escena, luz, cámara; Cycles o EEVEE | L | «El aspecto», en su worktree |
| T21 | El motor al atar: largo fijo, manos que agarran, gravedad en lo que cuelga | XL | La del plan (modelo grande) |
| T22 | El video completo: capítulos, guion, cámara, tarjetas, errores, aplicación, reel | L | La del plan, después de T21 |
| T23 | El sonido: voz, música, diseño sonoro y mezcla | L | «El sonido», en su worktree |
| T24 | El visor: material, luz y postprocesado (lygia y three.js 0.160) | M | «El aspecto» |

Los pilotos son tres: el as de guía (libre), el amarre cuadrado (plantilla) y la eslinga de andamio (anfitrión, y la aplicación que pidió Gabriel).

#### T21: El motor al atar: largo fijo, manos que agarran y gravedad en lo que cuelga

**Solo cambia el modo «atar».** Asentar y apretar no se tocan: todo cambio en `nudos/fisica/` entra con valores por omisión que dejan todo como hoy. `referencia` y `comparar --reimprimir` comprueban que los 36 `modelo.json` y las imágenes no cambian, como en T15f, y la huella de `tests/test_apretar.py` tampoco.

**Lo que hoy lo hace tosco** (medido por la revisión de diseño del 26 nov):
- **La cuerda cambia de largo.** Recoger quita nodos y `_partir` los agrega. Por `_partir`, la mano no puede pasar de 10 d/s, y por eso las plantillas necesitan la cámara rápida.
- **`retiempo` toma el cuadro más cercano** cuando cambia la cantidad de nodos, así que la cámara rápida da saltitos.
- **El resaltado y el remate van por índice de nodo,** y la UV de la trenza sale del largo de cada cuadro: en el modo «firme», la textura camina por la cuerda.
- **La gravedad está apagada en la práctica.** Con 0,2 N·s/d, un nodo suelto cae a 0,0016 d/s, y con el resorte de 5 N/d cuelga 0,00006 d. Nada cuelga ni cae.
- **Las velocidades cambian en seco,** y «acomodar» es un morph.

**Lo que no se vería aunque se agregara: la inercia.** La mano llega a 5 d/s en 0,3 s, y una cola colgando se inclina menos de 1°. El roce cuadrático del aire es 10⁻⁴ del peso. Lo que sí se ve es la gravedad sobre la cuerda libre: que cuelgue, que se acueste y que caiga sobre la mesa.

**La medida de hoy (T21a, 26 nov).** `python -m nudos calidad` mide los cuadros del video tal como se ven (60 por segundo) y deja `build/calidad/<slug>.json`. Un brinco es una aceleración de más de 360 d/s² (0,1 d de diferencia segunda en un cuadro). Una parada en seco es la punta acelerando a más de 50 d/s²: la mano de T17 arranca a unos 17.

| | As de guía | Amarre cuadrado |
|---|---|---|
| Duración | 45,2 s (2710 cuadros) | 48,1 s (2884 cuadros) |
| Nodos | de 357 a 550; cambian 281 veces | de 242 a 2314; cambian 1003 veces |
| Largo de la cuerda | de 71,0 a 109,8 d (35 %) | de 48,2 a 461,8 d (crece con los pasos) |
| Recoger, acomodar (el morph) y encaje | 4,8, 6,6 y 3,6 s | 3,7, 3,0 y 3,1 s |
| Aceleración p99 y máxima | 340 y 906 d/s² | 217 y 868 d/s² |
| Brincos | 7 | 6 |
| Paradas en seco de la punta | 74 | 34 |
| Resaltado vacío o a medias | 144 + 578 de 2351 cuadros (31 %) | 331 + 1080 de 2645 cuadros (53 %) |
| Cámara: paradas, tiempo quieta y aceleración máxima | 14, 14 % y 222 d/s² | 14, 14 % y 852 d/s² |

**La meta de T21:**
- La cantidad de nodos no cambia, y el largo varía ±0,5 %.
- Cero segundos de recoger y de morph.
- Cero brincos y ninguna parada en seco de la punta.
- El resaltado nunca queda vacío ni a medias.

La cámara (las paradas y la aceleración) es de T22.

**El diseño (Gabriel lo aprobó el 27 nov):**
1. **Largo fijo y coordenada de material.**
   - Una sola cuerda para todo el video, en una sola grilla (la h del último paso).
   - El nodo j es siempre el mismo punto de la cuerda, σ_j, medido desde el extremo lejano del firme en un nudo libre o desde el nodo 0 en una plantilla. Así, el resaltado, el remate, la cinta del chicote y la trenza quedan pegados a la cuerda.
   - Desaparecen recoger, `_partir`, `cambio`, `recoge` y `_ajustar`.
2. **Las poses de video, que son las pausas.**
   - **En un nudo libre:**
     - Hay un depósito R de firme fuera del encuadre (lo que el firme gana en todo el nudo), y la cuerda mide L, el largo del último paso.
     - Cada pausa tiene el depósito, el tramo que dibuja la ficha (exacto, a 0,02 d, con su secuencia) y una cola de más, T_k = L − o_k − L_k.
     - En el as de guía, R = 16,6 d y L ≈ 126 d (632 nodos), y las colas de más miden 22,1, 22,1, 25,1, 22,9, 14,8, 7,1 y 0 d.
   - **La cola de más:**
     - Se acuesta en la mesa en la primera dirección, vista desde arriba, que no cruza nada.
     - Si no hay ninguna, queda en un arco levantado por fuera del nudo y fuera de la toma. *Cambió en T21c (Gabriel, 27 nov): el arco del paso 3 del as de guía subía 25 d en diagonal sobre el nudo. Ahora la cuerda de más espera en una bolsa dentro del nudo (ver «Cómo se hizo»).*
     - Un campo opcional del video (`video: {cola: …}`) la corrige donde la regla falle; las fichas lo ignoran.
   - **En una plantilla:** la pausa es la cuerda hasta el hito, más la cola en la mano, como hoy, y el resto va en la madeja. *Cambió en T21d (Gabriel, 27 nov): la madeja no pasa por debajo del palo de abajo, que descansa sobre la cuerda en la mesa, y el plan B tampoco. La cuerda sale de la mano (ver «Cómo se hizo T21d»).*
   - **La regla de la pausa se mantiene, precisada:** el tramo que dibuja la ficha es la pose de la ficha, con su secuencia, y el depósito, la cola y la madeja solo pasan por encima. Así cada transición sigue corriendo en paralelo con las demás. Si cada una partiera del final de la anterior, atar un nudo tardaría de 5 a 6 veces más.
3. **Manos que agarran.**
   - Una pinza sostiene 2 o 3 nodos (su posición y, si hace falta, su dirección), y puede soltar y volver a agarrar.
   - La que lleva el chicote lo toma a 1,5 d de la punta, así que la punta y su cinta siempre se ven.
4. **La guía nueva.**
   - Toma la punta, la lleva por encima de todo, la enhebra por el camino del paso siguiente (los tramos de encima suben con `alturas`, como hoy) y tira de la cola hasta su arco.
   - La cuerda que todavía no pasó cuelga como un seno, así que se recoge sola, sin cúspide.
   - Lo que cuelga flojo pasa siempre por encima, y se comprueba: si quedara debajo de un borde al tirar, se enrollaría en él.
5. **El tiempo.**
   - Arranques y frenadas de tirón mínimo, velocidades suavizadas y fases que se solapan.
   - La velocidad del video es C1, y `retiempo` siempre interpola.
   - Lo repetitivo de las plantillas se simula a 20 o 30 d/s con 3 o 4 subpasos, en vez de la cámara rápida: sin `_partir`, ya se puede.
6. **La gravedad en lo que cuelga.**
   - En los tramos libres (lo flojo y lo levantado), poca amortiguación y sin resorte, para que cuelguen y caigan.
   - Con **memoria plástica:** la curvatura de reposo se relaja hacia la actual, y así un lazo que se suelta no salta (un lazo de 10 d guarda unos 10 N·d de flexión, y un nodo tiene una masa de 2,6·10⁻⁷).
   - Los resortes hacia la guía se quedan, pero entran de a poco en el último 30 % de cada transición y reemplazan a `encajar`. La amortiguación de Rayleigh queda como opción.
7. **Las comprobaciones de cada cuadro:**
   - La cantidad de nodos fija y el largo con ±0,5 %.
   - Ningún par a menos de dmin y la CCD entre cuadros, como hoy.
   - El tope de 0,35 d de desplazamiento pasa a ser un tope a la aceleración (la diferencia segunda), porque un movimiento rápido y un brinco se distinguen por la aceleración. Si la gravedad se ve, el tope deja pasar g (1225 d/s²).

**Las subtareas, cada una con su prueba:**
- **T21a, medir y diseñar (M).** `nudos/fisica/calidad.py` mide en los cuadros guardados:
  - la velocidad, la aceleración y el tirón de cada nodo;
  - los brincos;
  - cuánto cambia el largo;
  - las paradas en seco;
  - cuántos cuadros salen del más cercano.

  La medida de los dos pilotos de hoy queda en este bloque. **Punto de control:** Gabriel aprueba el diseño.
- **T21b, las poses de video y el largo fijo (M).**
  - `animar.poses_video` arma σ, el depósito y la cola de más, validados.
  - `seguir` queda sin `_partir` ni recoger, y con pinzas.
  - Prueba: la misma cantidad de nodos en todo el video; las colas del as de guía a ±0,2 d de las de arriba; solo cruces por encima en lo agregado; y lo mismo dos veces.
- **T21c, la guía nueva, el tiempo y la gravedad (L),** con el as de guía. Prueba de 10 s y punto de control.
- **T21d, la madeja (L),** con el amarre cuadrado. Prueba de 10 s y punto de control.
- **T21e, el error y la aplicación (M).**
  - **El error:** va del paso anterior a su pose, hace una pausa y vuelve atrás (los mismos cuadros al revés, que `comprobar` acepta mientras el movimiento sea casi estático). Después sigue con el paso correcto.
  - **La aplicación:** el nudo apretado se coloca sobre la utilería, con la madera pasando por su lazo, y sus puntas se estiran hasta las anclas con la cuerda del depósito y se asientan con el motor. Ahí no se comprueba la secuencia vista desde arriba (con carga, el nudo se para), sino que nada se atraviese y que el lazo abrace la utilería.

**La prueba de punta a punta (lenta):** el as de guía atado entero, sin dibujar.
- Cero fallas de `comprobar` y la cantidad de nodos fija.
- El largo a ±0,5 %, cero brincos y ningún cuadro tomado del más cercano.
- Cada pausa con la ficha a 0,02 d y con su secuencia.
- No más del doble del tiempo de hoy.

**Lo que cuesta:** hoy, unos 15 min de motor por piloto; con todo, de 20 a 35. El riesgo alto es la gravedad en lo que cuelga, porque Newton pierde la viscosidad que hoy lo estabiliza. El riesgo medio es la guía nueva.

**Planes B:**
- Si la cola de más no se puede acomodar, queda en la madeja («en la mano») o se corrige con el campo del video.
- Si la gravedad no se estabiliza, los resortes se quedan y lo flojo cuelga como una catenaria dentro de la guía.
- Si la madeja no convence a la vista, la cuerda sale del cuadro por la mano. *Tampoco sirve en un amarre: lo que sale del cuadro también tendría que pasar por debajo del palo de abajo (T21d).*

**Cómo se hizo T21b y T21c (27 nov, con el as de guía):**
- **Las poses de video** (`animar.poses_video`): el nodo j es siempre σ = j·h.
  - El depósito es lo que el firme gana en el nudo (16,6 d en el as de guía, al formar la gaza pequeña), y entra por el firme.
  - La cuerda mide lo que pide el paso más largo con lo que todavía le falta al firme. En el as de guía es el último paso: 109,8 d y 550 nodos. No hizo falta el depósito de más del diseño (`DEPOSITO_FINAL` = 0).
  - Las colas de más miden 22,1, 22,1, 25,1, 22,9, 14,9, 7,1 y 0 d.
- **La cola de más:**
  - Se acuesta en la primera dirección que, vista desde arriba, no pasa a menos de 1,5 d de la cuerda, y sale con la dirección y la pendiente de la punta. Con una dirección promedio, el tramo de la ficha se separaba 0,025 d de ella en la punta.
  - En los pasos 3 y 6, la punta está dentro del nudo y ninguna dirección cabe. Primero la cola subía a 60° y salía del cuadro; Gabriel vio en la previa que en el paso 3 subía 25 d en diagonal sobre el nudo (27 nov), y ahora va en una bolsa (abajo).
  - `comprobar_poses` revisa la cantidad de nodos, el tramo de la ficha a 0,02 d (fuera de la bolsa), que tenga en el video los mismos cruces que en la ficha, que lo agregado pase solo por encima, y dmin.
- **La bolsa** (`_bolsas`, `_inflar`; Gabriel, 27 nov):
  - Los 25 d del paso 3 no son un error de cálculo: los cruces del as de guía quedan en el mismo punto de la cuerda en todos los pasos (se corren 0,3 d como mucho), y el chicote crece 2,2, 8,0, 7,8 y 7,1 d en los pasos 4 a 7. Con largo fijo, esa cuerda tiene que estar en algún lado.
  - Si la cola no cabe acostada, la cuerda de más espera en un tramo libre de la ficha (entre dos cruces, o del último cruce a la punta, a 0,75 d de los cruces y a 3 d de la punta) que se infla hasta medir lo que sobra. Toma la forma de una cuerda floja: gira lo mismo que en la ficha pero más despacio, y un giro de más, ψ(t) = Σ a_k sen(kπt), la cierra en sus puntas doblando lo menos posible (una elástica, con Newton y la condición de la punta). No dobla más cerrado que la ficha ni que 1,5 d, ni se acerca a la cuerda más de 1,5 d.
  - Antes, la bolsa se empujaba hacia afuera por la normal, pero con rampas de 3 d hacía codos de radio 0,3. También se probó tirarla hacia el nudo para que saliera más ancha y la cámara abriera menos, y las formas salían raras. El giro de la ficha se reparte en un tramo antes de estirarlo: dobla solo en los nodos, y estirada quedaba con codos.
  - La cuerda de más no vuelve para atrás por un cruce. Los pasos a los que se llega sin que la punta pase por un cruce nuevo comparten la bolsa (la gaza grande de los pasos 1 a 3, también en los que la cola cabía), y la del primer paso de un grupo va en la cuerda que ese paso tiende (la vuelta del collar del paso 6, y no la gaza).
  - En el as de guía, la gaza grande guarda 22,1 d en los pasos 1 y 2 y 25,1 en el 3: sale como una gota de unos 19 × 25 d, contra 14 × 15 en la ficha, y la cámara abre más en esos pasos. La vuelta del collar del paso 6 guarda 7,1 d y sale como una lengua hacia la derecha. Los pasos 4 y 5 llevan la cola acostada (22,9 y 14,9 d).
  - En los pasos con bolsa, la punta de la cuerda es la del chicote de la ficha: se ve, y nada sube fuera del cuadro.
- **La cinta** (`_Cinta`): si la punta de A ya está en el camino de B (a 0,3 d desde arriba y a 1 d de alto) y A tiene bolsa, la mano no la lleva por el aire: la levanta ahí y tira.
  - Lo que pasó por p* sigue el camino, como al enhebrar. La bolsa, desde su comienzo hasta p*, es una mezcla de la forma de A y la de B que mide lo que queda de ese lado, con resortes en toda la cuerda.
  - En el as de guía, el chicote sube por la gaza pequeña mientras la gaza grande se achica hasta su tamaño (paso 4), y baja por ella mientras la vuelta del collar se aprieta (paso 7).
  - La curva empieza en la bolsa y no donde A y B se separan: las fichas de dos pasos, asentadas cada una por su lado, difieren en todo el nudo (el chicote que sube empuja la gaza pequeña más de 0,5 d), y con eso la curva se tragaba los cruces.
- **La mano que acerca el chicote** (`_tramo_largo_firme(mano=True)`): en un paso «punta» en que la punta no pasa por ningún cruce nuevo (el paso 3 del as de guía), la mano toma la cuerda a 1,5 d de la punta y la lleva levantada hasta 1 d a mitad de camino, y todo va guiado nodo a nodo de A a B, con arranque y frenado de quinto grado. Con la punta por el aire y el resto suelto, el chicote se doblaba en un gancho. Con un anfitrión sigue yendo por el aire, porque la recta podría atravesarlo.
- **El barrido y el lazo** (Gabriel, 27 nov: en el paso 5 la cola se enrollaba):
  - En el paso 5 la mano traía la punta, 23 d lejos al final de la cola acostada, hasta junto al nudo para pasarla bajo el firme, y la cola suelta se amontonaba en un rollo.
  - **El barrido** (`_tramo_largo_barrido`, `_mezcla_angular`): la cola gira entera, como un limpiaparabrisas, desde donde el paso se separa del anterior. Cada tramo va de su ángulo en A al de B y la cuerda se arma tramo a tramo, así que no se estira ni se encoge, y pasa por debajo del firme, que sube donde la cruza.
    - Con la cola casi paralela al firme, el cruce corre hasta 1,7 d por cuadro: se sigue con 5 d de tolerancia (`_seguir_cruces(salto=)`), porque con 1 d cada cuadro era un cruce nuevo, con la cola encima, y la guía la subía 8 d.
    - Lo que sube cada tramo se empareja en 9 cuadros (el máximo y después el promedio): el cruce aparecía y desaparecía junto a la punta del firme, que saltaba a 3300 d/s².
    - Dura lo que tarda en girar, a 10 d/s, la cuerda a 15 d de donde empieza: unos 3 s.
  - **El lazo** (`_lazo`, `_tramo_largo_lazo`): en el paso 6, la cola acostada se dobla, con la misma mezcla de ángulos, en una bolsa junto al firme: el camino de B hasta la entrada, inflado con toda la cuerda que sigue. Después la punta cruza el firme por encima y la bolsa se achica con la cinta. Doblarla mezclando los lugares nodo a nodo la dejaba un 1 % más corta a mitad de camino, y el motor la arrugaba.
  - En el paso 5 el lazo no cabe: las dos puntas de la bolsa van casi paralelas junto al nudo, y 21 d de cuerda entre ellas se cruzan a sí mismos, en un ocho.
  - El orden (`_tramo_largo_enhebrar`): la cinta si la punta ya está en el camino; si no, el lazo, el barrido y, si nada cabe o hay un anfitrión, el aire con lo de detrás suelto. En el as de guía: 4 cinta, 5 barrido, 6 lazo y 7 cinta; ninguno va por el aire.
- **El resaltado, hasta la punta de la cuerda:** si la ficha resalta hasta su punta, el video resalta hasta la de la cuerda, con la cola acostada. Es el mismo chicote, y al enhebrar va adelante. En el paso 4 del as de guía, la punta subía por la gaza pequeña sin resaltar, y lo resaltado iba detrás, por el fondo de la gaza grande.
- **La guía** (`_tramo_largo_punta`):
  - La mano toma la cuerda a 1,5 d de la punta: tres nodos, con 200 N/d.
  - La trae por el aire a 10 d/s hasta la entrada, que queda 2,5 d antes del primer cruce nuevo.
  - La enhebra por el camino del paso siguiente a 5 d/s, o a 2,5 cerca de los cruces, con las alturas de T17. Después tira de la cola a 10 d/s.
  - Lo que ya pasó la entrada sigue el camino de la punta.
  - Lo que todavía no pasó va suelto: sin resorte ni viscosidad y con su peso. Su memoria es la forma que tenía al soltarse, que se endereza en 0,5 s (`ENDEREZAR`). Así cuelga, se arrastra y se recoge solo.
  - La pierna que va del nudo a la entrada vuelve a su lugar en los últimos 3 d del recorrido de la mano.
  - Las velocidades se suavizan con dos promedios de 1 d, y el arranque y el frenado son de quinto grado (0,5 s).
  - Al final, 0,4 s con los resortes subiendo hasta 50 N/d, en vez de `encajar`, y 0,15 s hasta la pose exacta: la cuerda queda a menos de 0,03 d.
- **La gaza pequeña** (`_tramo_largo_gaza`, el paso «firme» del as de guía):
  - En línea recta, nodo a nodo, el firme se ondulaba al correr y la gaza nacía de un gancho cerrado. Rizarla interpolando el ángulo de cada tramo dejaba su extremo a 14-17 d de donde llega el firme.
  - Un lazo no sale de una cuerda acostada sin levantarla: visto desde arriba, la cuerda gira una vuelta entera más, y eso pide una cúspide o un tramo que se levante.
  - Se probó que la gaza naciera chica y parada en el cruce y se acostara mientras crecía. Una gaza de menos de unos 7 d no cabe: el motor la arrugaba en la mesa y después la volteaba de golpe.
  - Ahora la cuerda que entra por el firme sale en una bolsa acostada junto al cruce (`_inflar`, hasta 8 d). La bolsa se voltea sobre su eje (`_voltear`): el tramo del chicote pasa por arriba del firme, que se corre por la mesa, como se forma un ojo con la mano, y en su cuello queda el cruce. Después crece hasta la gaza de la ficha mientras el firme sigue corriendo.
  - Los nodos van cada h a lo largo de esa curva, desde un punto fijo del otro lado del cruce, así que el firme corre a lo largo de sí mismo. Lo de más allá va de A a B nodo a nodo (se mueve 0,7 d como mucho), y un ajuste suave deja el primer cuadro en A y el último en B.
  - Los cruces que la bolsa levantada hace vistos desde arriba ya van separados: solo suben los que lo piden, con 0,3 d de holgura. Con la de siempre (1 d), el tramo de encima subía de más sobre el que ya se levantaba y se estiraba un 45 %.
  - Sirve cuando la cuerda que entra por el firme suma una sola gaza, del lado de la bolsa; si no, el paso sigue en línea recta.
  - En el as de guía, el paso dura 3,6 s, y su aceleración más alta bajó de 970 a 146 d/s².
- **El motor** (`atar.seguir`, con `CuadroGuia.largo_fijo`, `viscosidad` y `suelto`):
  - Los largos de reposo son los de la guía.
  - La viscosidad va por nodo (`Sistema.paso` la acepta así, y con una sola da lo mismo bit a bit).
  - Lo suelto lleva la memoria de cuando se soltó. Con la memoria plástica que decía el diseño (la forma de cada cuadro), la cuerda se quebraba en un codo de 66° detrás de la mano.
- **Lo que hubo que arreglar al probar:**
  - Una curvatura NaN en la guía cuando dos de sus puntos quedaban juntos (`_curvatura_segura`).
  - Un cruce de la cola en arco tomado por uno del camino nuevo: los cruces de A solo cuentan en el tramo que ya está en su lugar.
  - La punta se trababa bajo un tramo en el paso 7 porque la altura de la mano entraba después de las alturas de los cruces. En T17 entraba antes, y ahora también.
- **El video:**
  - Las pausas son las poses de video.
  - El resaltado va en σ y la trenza también (`malla_trenza(s=)`), así que no se achican ni caminan.
  - La cámara encuadra solo el tramo de la ficha.
  - El foco va a la punta del paso y pasa a la mano cuando esta se acerca (`Cuadro.foco`).
- **Lo suelto se reacomoda en unos cuadros, no en uno.**
  - Sin roce con el aire y con tan poca masa, la cuerda suelta que se zafaba de otro tramo cambiaba de lugar en un solo cuadro, con hasta 10 875 d/s².
  - Ahora la frena una amortiguación proporcional a su rigidez (de Rayleigh: `atar.RAYLEIGH`, 0,03 s, con `Sistema.paso(rayleigh=)`), que no frena la caída por su peso.
  - Solo va en los cuadros con cuerda suelta: con la cuerda toda guiada, estiraba el firme un 1,5 %.
- **La guía, sin escalones** (los picos que quedaban venían de la guía, no del motor):
  - La mano levantaba el camino solo hasta la punta, y la punta caía entre un nodo levantado y otro no. Su altura iba y venía 1 d cada vez que pasaba un nodo, con hasta 4800 d/s² en la guía, y los tramos que se levantaban sobre ella la seguían. Ahora lo que viene por delante también va levantado.
  - El aire llegaba a la entrada sin las alturas de los cruces del camino. Ahora los últimos 2 d del aire se juntan con el camino en cada cuadro (`MEZCLA`).
  - Los cambios de velocidad de la mano se reparten en 2,5 d, porque con 1 d la punta frenaba en seco al pasar de 10 a 2,5 d/s.
  - Se probó una punta más rígida (20 N/d de la mano al extremo) y empeoró: chocaba más con lo que roza.
- **Sin sacudón al soltar la cola** (el primer cuadro de cada tramo la movía 0,33 d):
  - Los largos de reposo van de los de la pose de partida a los de la de llegada (`_largos_de`). En las fichas del motor, la cuerda asentada queda un 0,1 % más corta que h, y la cola de más medía h. Al soltarse, lo guiado la empujaba a lo largo.
  - La cola se apoya donde descansa la cuerda suelta, a unos 0,55 d, y no a 0,5: el contacto con la mesa la subía 0,1 d de golpe.
  - Ahora el primer cuadro se mueve 0,02-0,04 d.
- **El video:** la velocidad de la línea de tiempo valía 0,9999999999999999 en vez de 1 (el promedio de unos), y `retiempo` corría un cuadro cada tanto.
- **La medida del as de guía, antes y después** (`calidad`, el video entero):

| | T21a (26 nov) | T21c (27 nov) | T21c con la bolsa, el barrido y el lazo (27 nov) | Y la gaza pequeña volteada (27 nov) |
|---|---|---|---|---|
| Duración | 45,2 s | 51,3 s | 40,2 s | 40,5 s |
| Nodos | de 357 a 550; cambian 281 veces | 550; no cambian | 550; no cambian | 550; no cambian |
| Largo de la cuerda | de 71,0 a 109,8 d (35 %) | de 109,64 a 110,12 d (0,44 %) | de 109,63 a 109,97 d (0,31 %) | de 109,67 a 109,97 d (0,28 %) |
| Recoger y morph | 4,8 y 6,6 s | 0 y 3,3 s (la gaza pequeña) | 0 y 3,3 s (y 1,2 s de la mano que acerca el chicote) | 0 y 1,2 s (la mano que acerca el chicote) |
| Aceleración p99 y máxima | 340 y 906 d/s² | 271 y 2192 d/s² (la cuerda que cae y se apoya) | 194 y 970 d/s² (la gaza pequeña) | 156 y 328 d/s² |
| Brincos (más de 360 d/s²) | 7 | 6 | 2 | 0 |
| Picos y temblores | sin medir | 0 y 0 | 0 y 0 | 0 y 0 |
| Paradas en seco de la punta | 74 | 45 (28 frenadas: cambios de rapidez) | 12 (11 frenadas) | 12 (11 frenadas) |
| Resaltado vacío o a medias | 31 % de los cuadros | ninguno | ninguno | ninguno |

  Las fases del nudo, antes de la bolsa: 13,2 s en el aire, 8,3 enhebrando, 8,2 tirando de la cola, 3,3 la gaza pequeña, 2,4 asentando, 0,9 acercando, 1,5 apretando y 13,5 de pausas. Lo que más duraba era traer la punta por el aire, que no enseña nada. Con la bolsa, el barrido y el lazo ya nada va por el aire con la cola suelta. Con la gaza volteada: 3,6 s formando la gaza pequeña (1,1 la bolsa, 0,9 el volteo y 1,7 creciendo), 1,2 acercando el chicote con la mano, 3,2 doblando la cola en el lazo del paso 6, 2,9 barriendo en el 5, 8,6 enhebrando, 2,6 tirando, 2,4 asentando, 0,9 acercando, 1,5 apretando y 13,5 de pausas. La cámara (14 paradas, quieta el 16 % del tiempo) es de T22.
- **Los seis tramos del as de guía:** sin fallas, con el largo entre 0,9984 y 1,0018 del nominal y sin ningún pico ni temblor; unos 3 min de motor los seis a la vez.

**Cómo se hizo T21d (27 y 28 nov, con el amarre cuadrado):**
- **Por qué no hay madeja:**
  - El palo de abajo descansa sobre la cuerda en la mesa. Su eje va a radio + 1 = 3,5 d y su cara de abajo, a 1 d de la mesa, así que debajo cabe una sola cuerda.
  - En las vueltas (pasos 2 y 3) la cuerda pasa seis veces por ahí, con 2,8 a 3,3 m por atar. Por debajo solo puede pasar la punta, con toda la cuerda que la sigue, así que una madeja en la mano no cabe.
  - El plan B tampoco sirve. Una cuerda entre dos puntos fijos no cambia las vueltas que da alrededor de un palo, así que lo que sale del cuadro por la mano también tendría que pasar por debajo.
  - En los ahorcados y en el cierre sí hay lugar, pero la madeja sería más grande que el amarre: 220 d por atar al empezar los ahorcados.
  - Gabriel eligió que la cuerda salga de la mano (27 nov). La otra opción era levantar los palos solo en el video.
- **La cuerda sale de la mano** (`poses_plantilla`, `_tramo_plantilla`, `animar_plantilla`):
  - La mano lleva lo que falta sin que se vea, y la cuerda nueva sale de ella y queda quieta donde la dibuja el paso, como un cable que se tiende desde un carrete.
  - La cuerda tiene siempre los mismos nodos: es la del último paso, con 462,5 d y 2314 nodos.
  - Lo que la mano todavía lleva espera donde va a quedar, sin dibujarse ni chocar. Así nada salta al aparecer, el largo de toda la cuerda no cambia, y la trenza y el resaltado van pegados a ella.
  - Nada se recoge ni se acomoda.
- **Las pausas:**
  - Se ve la ficha hasta el hito y 4 d de cola en la mano, por el camino del paso siguiente, para no moverla al arrancar.
  - Desde 12 d antes del hito, la pose pasa en 10 d de la ficha a ese camino. Junto al hito, la ficha dobla hacia lo que cae a la mesa (hasta 1 d y 39°), y lo atado se corre a lo largo de la cuerda de un paso al siguiente, porque se aprieta (hasta 0,7 d en los 40 d antes del hito).
  - Mezclado en 2,5 d, los tramos de la unión iban de 0,5 a 1,4·h y la trenza se apretaba y se estiraba. En 10 d y repartidos iguales, van de 0,9 a 1,1·h.
  - Lo que no se ve de una pose es lo mismo en la siguiente (`comprobar_poses_plantilla`).
- **La mano:**
  - Va a 5 d/s en los primeros 6 d de cuerda nueva, para que se vean. Después va a 20 d/s, o a 30 en los pasos que repiten (las vueltas y los ahorcados), en vez de la cámara rápida.
  - Va más despacio en las curvas, para que la punta no pase de 200 d/s² (un brinco son 360), y cambia de rapidez a 35 d/s² como mucho (una frenada en seco son 50).
  - Las rapideces se miden a lo largo del largo de verdad del camino, y no de σ. En los bordes de la unión los tramos pasan de h a 1,06·h, y la punta cambiaba de rapidez de golpe.
  - Arranca y frena con el quinto grado de T21c, y llega a 5 d/s. Con el frenado montado sobre la desaceleración, la rapidez cambiaba hasta 46 d/s².
- **Lo que ya se veía** va de la pose A a la B nodo a nodo en todo el paso, porque lo atado se aprieta.
- **El motor** (`seguir`) mueve solo lo que se ve. En cada cuadro agrega, quietos y donde esperaban, los nodos que salieron de la mano (`Cuadros.anadido`), y `comprobar` y `saltos` los conocen.
  - Los resortes van firmes desde el principio (50 N/d, `RESORTE_FIN`). Con los de siempre, al arrancar cada paso el motor acomodaba la cuerda unos 0,04 d en un cuadro, y la punta frenaba en seco.
  - Con los resortes firmes ya no hace falta asentar al final de cada paso.
- **El video:**
  - Cada cuadro sabe hasta dónde se ve la cuerda (`Cuadro.visible`), y se dibuja solo eso, con la punta entre dos nodos (`cuerda_visible`). La punta lleva su σ para la trenza y su velocidad para el desenfoque.
  - La punta va por una curva suave (de Catmull-Rom) entre los nodos de alrededor. En línea recta doblaba de golpe en cada nodo, y en una curva rápida temblaba.
  - La cámara encuadra solo lo que se ve y el foco sigue a la mano.
  - Ya no hay cámara rápida: `retiempo` siempre interpola.
  - `prueba-atar` también dibuja solo lo que se ve.
- **La medida de los dos pilotos** (`calidad`, el video entero; la punta del amarre es la que se ve, donde sale la cuerda de la mano):

| | As de guía, T21c (27 nov) | Amarre cuadrado, T21a (26 nov) | Amarre cuadrado, T21d (27 nov) |
|---|---|---|---|
| Duración | 40,5 s | 48,1 s | 50,0 s |
| Nodos | 550; no cambian | de 242 a 2314; cambian 1003 veces | 2314; no cambian |
| Largo de la cuerda | de 109,67 a 109,97 d (0,28 %) | de 48,2 a 461,8 d (crece con los pasos) | de 460,41 a 462,07 d (0,36 %) |
| Recoger y morph | 0 y 1,2 s (la mano que acerca el chicote) | 3,7 y 3,0 s (y 3,1 de encaje) | 0 y 0 |
| Aceleración p99 y máxima | 156 y 328 d/s² | 217 y 868 d/s² | 200 y 260 d/s² |
| Brincos (más de 360 d/s²) | 0 | 6 | 0 |
| Picos y temblores | 0 y 0 | sin medir | 0 y 0 |
| Paradas en seco de la punta | 12 (11 frenadas) | 34 | 161 (2 frenadas) |
| Resaltado vacío o a medias | ninguno | 53 % de los cuadros | ninguno |

  - **Las paradas en seco del amarre son las curvas:** la mano rodea los palos a 20 o 30 d/s, con hasta 200 d/s² hacia el centro, y la medida cuenta toda aceleración de la punta de más de 50. Lo que se ve como un frenazo son las frenadas, cuando cambia la rapidez.
  - **Las dos frenadas** son casi quietas (de 0,4 a 1,7 d/s), al arrancar el paso 5. La cola del paso 4, que va por el camino del 5, queda junto a lo atado a la distancia en que la barrera empuja, y el motor la aparta 0,04 d en un cuadro. No llega a brinco ni a pico.
  - **Las fases del amarre:** 34,1 s tendiendo la cuerda, 13,5 de pausas, 1,5 apretando y 0,9 acercando a cada pose.
  - **El motor:** de 75 a 811 s por paso, con la máquina ocupada; los seis pasos, en 17 min con tres procesos (`NUDOS_PROCESOS=3`). Con seis a la vez, la máquina se quedó sin memoria mientras otra sesión corría `referencia` con Blender (92 de 94 GB comprometidos).
- **La previa** (`build/videos/amarre-cuadrado/amarre-cuadrado-previa.mp4`): 50,0 s y 7,3 MB. Tardó 46 min en dibujarse (1434 cuadros distintos), con la máquina ocupada.
- **Las fichas no cambian.** Construir e imprimir no usan nada de lo que cambió (`animar.py`, `fisica/atar.py`, `fisica/calidad.py`, `video.py` y `prueba_atar.py`). Para comprobarlo, `referencia` con three.js desde un worktree de `main` (f1c6fef) y con el código nuevo, el mismo día, y `comparar`:
  - Los 36 `modelo.json`, iguales byte a byte.
  - Las imágenes, iguales. Tres nudos salieron con unos píxeles en 1 nivel (de 3 a 16) por imprimir mientras se dibujaba la previa, e iguales al imprimirlos otra vez con los dos códigos.
- **Pruebas** (`tests/test_plantilla_largo_fijo.py`):
  - las poses del amarre;
  - lo que se ve de la cuerda;
  - la guía de las vueltas, con la cuerda quieta donde la deja la mano y la punta sin frenadas en seco ni brincos;
  - una cuerda recta atada con el motor;
  - `comprobar` con los nodos que salen;
  - la calidad con la punta que se ve.

#### T22: El video completo

**T22a, el diseño (M), que Gabriel aprueba antes de programar.** Gabriel lo aprobó entero el 28 nov. Escrito el 27 nov, con el guion de los tres pilotos, su hoja de revisión (`python -m nudos guion <slug>`) y la maqueta de las tarjetas (`python -m nudos prueba-tarjetas`). Lo de abajo cumple lo que pidió Gabriel el 26 nov (los capítulos, el reel, la voz que manda el tiempo, las tarjetas, la cámara y las aplicaciones) y agrega las decisiones que faltaban.

- **Los capítulos.** Las duraciones son las estimadas del as de guía (`guion as-de-guia`): 2:53 en total.

  | Capítulo | Escena | Lo que se ve | La voz | La tarjeta | Dura |
  |---|---|---|---|---|---|
  | Apertura | campamento | El nudo terminado y apretado gira despacio sobre la mesa. | `video.apertura` | El nombre, la familia y el ABOK | 14 s |
  | Lo que necesitas | estudio | La cuerda estirada (y los palos o la tabla, si van), que es de donde parte el paso 1. | `video.materiales` | El `materiales` de la ficha | 6 s |
  | Paso a paso | estudio | Cada paso con su movimiento, desde la cuerda estirada. | `voz` de cada paso | La del paso | 63 s |
  | Cómo saber que quedó bien | estudio | El nudo apretado de cerca: la cámara va a cada cosa (`mira`) y, por detrás, el nudo se voltea. | `video.verificacion` | Una ✓ con su etiqueta sobre cada cosa | 23 s |
  | Errores comunes | estudio | El error atado con el motor (T21e) y la ✗; el nudo terminado con el error falla al usarlo; el paso correcto, la ✓, y el nudo bien hecho aguanta. Después, cada uno de los demás errores con su falla. | `voz` del error y de `otros` | ✗ y ✓, con el cuadro teñido | 24 s |
  | En la práctica | campamento | La aplicación (abajo). | `video.aplicacion.voz` | De capítulo, con el título | 12 s |
  | Seguridad | campamento | La aplicación, de lejos. | `video.seguridad` | El escudo y la voz frase por frase | 22 s |
  | Cierre | campamento | La cámara se aleja; en el golpe entra el nombre. | `video.cierre` | El nombre, la dirección del visor y el grupo | 8 s + 10 s |

  - Cada capítulo empieza con su tarjeta de capítulo, salvo la apertura y el cierre (el nombre) y el paso a paso (la tarjeta del paso 1). El cambio de escena va detrás de esa tarjeta.
  - **La promesa de la apertura** («y al final, cómo revisar que quedó bien») se cumple al terminar los pasos, que es el final de lo que se aprende; en el amarre, «la prueba para saber si aguanta» es la última cosa que se revisa («empuja un palo»). El orden de los capítulos es el del 26 nov.
  - **El golpe** va en el cierre: el acorde final de la música, el golpe del foley y el nombre que entra de golpe caen juntos. El crujido del apretado sigue al final del último paso, con el foley del motor.
  - **La pantalla final:** los últimos 10 s quedan libres a la derecha para los elementos de YouTube (el video que sigue, que nombra el cierre, y suscribirse).
- **La voz manda el tiempo.**
  - Cada parte dura su voz más lo que la imagen necesita: en un paso, el movimiento empieza 0,3 s después de la voz y se estira o se acorta entre 0,75 y 1,35 veces su tiempo del motor para terminar unos 0,8 s después de la voz. Si aun así no cabe, el paso dura más y la música llena; si sobra, la pose final se queda con la cámara deslizándose despacio.
  - La tarjeta de cada paso aparece 0,25 s antes de su voz, con el clic.
  - Los cortes de capítulo caen en el pulso de la música (`musica.al_pulso`): el comienzo de cada capítulo se corre hasta medio pulso (unos 0,3 s), nunca la voz.
  - Cada locución se genera como en `prueba-guion`: sin titubeos y con el reconocimiento de voz revisando que diga su texto (`voz.locuciones_sin_titubeos`). La pista sale de `mezcla.pista()` con todas las voces, las tarjetas, el golpe, el foley del motor y la canción del nudo.
- **El guion pasa a la especificación (formato v1.14).** Era la decisión que faltaba. Cada paso lleva su `voz`, el error y cada uno de `otros` también, y un bloque `video` lleva lo demás: `apertura`, `materiales`, `verificacion` (cada cosa con `voz`, `mira`, `lado` y `etiqueta`), `aplicacion` (`escena`, `titulo` y `voz`), `seguridad`, `cierre` y, si hace falta, `reel`. El detalle está en `docs/formato-spec.md`, en «Video».
  - **Por qué ahí:** la especificación es la fuente de verdad, y la voz de cada paso queda junto a su texto y su secuencia, así que un cambio en uno se ve al lado del otro. Hace falta en todos los pasos de los 36 nudos, no solo «cuando el texto escrito no suena bien dicho», porque el texto de la ficha dicho tal cual suena a lista.
  - Es un cambio compatible: `voz` y `video` no entran al `modelo.json` ni a la ficha, y todos los nudos dan lo mismo. El guion de los dos pilotos dejó `config/guion/`, y `prueba-guion` lo lee de la especificación.
  - `nudos/guion.py` arma el video parte por parte (`partes`, `reel`), revisa lo que falta y el estilo (`problemas`: términos de sección, comparaciones, diminutivos, «así», puntos suspensivos, etiquetas largas y la escena), estima los tiempos y arma la hoja `guion <slug>`. El video no se arma con problemas.
  - **La hoja de revisión** (`build/<slug>/guion/index.html`) muestra cada capítulo con lo que dice la voz, lo que muestra su tarjeta y lo que dura: la voz medida si la locución ya está en el caché, o estimada con lo que T23 midió en la voz de Gabriel (1,44 s más 0,134 s por sílaba, 0,086 por coma y 0,246 por punto; medio segundo de error). Muestra también los capítulos para YouTube, el reel y el costo del render. Con `--oir` genera lo que falte con la voz de los videos y pone cada parte y la narración entera con la música.
- **El guion de los pilotos.** El del as de guía es el que Gabriel revisa en el punto de control; el del amarre cuadrado y el de la eslinga de andamio siguen el mismo estilo.
  - Los pasos, la apertura y la seguridad del as de guía y del amarre son los que Gabriel aprobó el 27 nov. El cierre de los dos cambió: la revisión pasó a su capítulo, y el cierre dice «Ya sabes hacer el…» y el nudo que sigue.
  - Lo nuevo de cada uno: lo que necesitas, cada cosa que se revisa, el error y los otros errores, la aplicación y, en el amarre, la seguridad sacada de sus precauciones (no tiene `seguridad`). La eslinga de andamio tiene todo su guion nuevo.
  - Estimado: el as de guía 2:53, el amarre 3:26 y la eslinga 2:43.
- **Cómo se escribe para la voz** (sin cambios). Gabriel aprobó este estilo el 27 nov, con la tercera versión de los guiones de los pilotos, y vale para los 36:
  - El anuncio del paso varía: «Primero», «Paso número dos de siete», «Ahora», «Paso cuatro», nada, «Último paso».
  - Frases cortas y largas mezcladas, en segunda persona y con conectores de quien enseña al lado: «ahora», «fíjate», «listo».
  - **Sin comparaciones** (Gabriel, 27 nov): «forma una gaza, como un ojo» o «es como un conejo que sale de su pozo» no le gustan. Las instrucciones van dichas tal cual; lo que evita que suenen a lista es el ritmo (frases cortas y largas, un anuncio de paso distinto cada vez), no las imágenes. `estilo_del_guion` marca «como un…», «como una…» y «como si…».
  - **La apertura va directa, sin tono de youtuber** (Gabriel, 27 nov: «¿Necesitas una gaza que no se cierre…?» le sonó a video de Yuya): el nombre del nudo y para qué sirve en la primera frase, y lo que vas a aprender «en siete pasos, y al final, cómo revisar que quedó bien».
  - **Pensado para YouTube,** para que lo vean completo: el nombre del nudo al empezar, una promesa que se cumple al final (la revisión o la prueba, como «empuja un palo»), y el cierre termina con el nudo que sigue, sacado de sus alternativas, para la pantalla final. La seguridad va antes del cierre.
  - **Sin diminutivos ni «así»** («cortito», «pequeñito»): no van con la manera de hablar de Gabriel. **Sin puntos suspensivos:** la voz los dice estirando la palabra de antes («deeel»). `estilo_del_guion` revisa las dos cosas, con la lista `PALABRAS_EVITAR`.
  - Nada de muletillas de video de IA («en el video de hoy», «¡increíble!», «sin más preámbulos»).
  - Cada instrucción dice lo mismo que la ficha: los «por encima» y «por debajo» no cambian, y la seguridad conserva todo lo que dice la especificación.
  - El reconocimiento de voz revisa que cada locución diga su texto, sin contar las letras que suenan igual ni la vocal que se pierde al juntar dos palabras («rodea el» y «rodeal»). Si no lo entiende («forma» que se oye «formo»), esa locución se vuelve a decir con otra semilla, como la que titubea (`revisar` en `voz.locuciones_sin_titubeos`).
  - **Sin titubeos:** `voz.titubeos` marca la palabra estirada (más de 0,35 s por sílaba; 0,60 al final de una frase) o la pausa de duda (más de 0,45 s donde el texto no tiene puntuación), y `voz.locuciones_sin_titubeos` vuelve a decir esa locución con la semilla siguiente, hasta tres tomas. Con la voz de Gabriel, el «del» de «el trabajo del as de guía» duró 0,40 s, y las palabras dichas bien, de 0,08 a 0,32 s por sílaba.
- **Las tarjetas** (la maqueta: `build/tarjetas/maqueta.html`, con los textos del as de guía sobre un cuadro de la prueba en 4K). El código es `render/tarjetas/` (`tarjetas.css` y `tarjetas.js`): cada tarjeta es función del tiempo (`pintar(t)`), así que el mismo código sirve para la maqueta y para dibujar cada cuadro en Edge.
  - **El paso:** el número grande en un distintivo ámbar (el mismo ámbar del tramo resaltado que se mueve), «Paso 4 de 7», el título y una barra de avance con un punto por paso: los hechos llenos, el de ahora con un pulso. Entra con un rebote suave (un resorte con un 5 % de sobrepaso, que se asienta en 0,6 s) y sale en 0,22 s: sale al terminar cada paso y vuelve a entrar con el siguiente (Gabriel lo eligió el 28 nov, frente a la tarjeta que se queda y solo cambia el número).
  - **El capítulo:** un panel que se abre desde la izquierda con rebote, con un ícono, el nombre en Big Shoulders y un fondo que se mueve: ruido simplex de lygia en WebGL, con unas formas que crecen al entrar. Verde la revisión, rojo los errores, verde bosque la práctica, turquesa lo que necesitas y amarillo la seguridad.
  - **La ✓ y la ✗:** un cuadro verde o rojo que rebota, la marca que se dibuja de un trazo y una onda que se abre. En la revisión, la ✓ va sobre lo que se revisa (el punto de `mira`, proyectado con la cámara de cada cuadro) con su etiqueta. En el error, la tarjeta va abajo con el título y el cuadro se tiñe de rojo en los bordes; el correcto, de verde.
  - **La seguridad** lleva lo que dice la voz, frase por frase, para que se entienda también sin sonido.
  - **El nombre y el cierre, con el grupo** (Gabriel, 28 nov: que el nombre «Grupo Guías y Scouts Huetares 431» y el logo del grupo salgan más). En la apertura, el logo junto al nombre del nudo, con una raya que se dibuja y el nombre del grupo debajo. En el cierre, el logo grande y el nombre del nudo entran de golpe con el acorde final, y después el nombre del grupo y la dirección del visor. El logo es `libro/logo-431.svg`, el mismo de la ficha (el vectorial de `A:/Scouts/06 Identidad/431/`, con el recuadro ajustado al emblema).
  - **Sin logo en la esquina** (Gabriel, 28 nov): se probó chico, arriba a la derecha durante todo el video, y Gabriel no lo quiso. El logo sale en la apertura y en el cierre.
  - **La paleta es «Huetares»** (Gabriel la eligió el 28 nov, entre seis que pidió ver): la del logo del grupo, con el azul de la flor de lis, el amarillo del borde y el verde de las cintas; el número del paso va azul sobre el amarillo. Las seis opciones quedan en `render/tarjetas/paletas.json`, con todos los colores de las tarjetas como variables de CSS y los de cada capítulo para el fondo de lygia. «Sitio» (la de hoy), «Huetares» (los colores del logo: el azul, el amarillo y el verde), «Guías y Scouts CR» (el índigo y el rojo de la marca nacional), «Wak y Tropa» (el turquesa y el verde de las dos secciones del libro), «Fogata» (oscura, con letra crema y naranja) y «Campamento» (café, verde bosque y mostaza). Las seis pasan una revisión de contraste (`tarjetas.problemas_de_paleta`): la letra sobre el vidrio con 4,5 sobre un fondo claro, sobre la madera y sobre uno oscuro, y la de los capítulos, las insignias y los subtítulos con 3. La maqueta cambia de paleta con un botón, y `build/tarjetas/paletas.png` las compara lado a lado.
  - **Sobre vidrio esmerilado:** blanco al 66 % sobre el cuadro de atrás desenfocado. Edge dibuja sobre fondo transparente, así que el desenfoque lo hace Pillow con la forma de cada tarjeta (Edge dibuja aparte, en blanco, la forma del vidrio).
  - **Las fuentes** son las del sitio y de la ficha: Big Shoulders Display, IBM Plex Mono y Literata.
  - **De lygia** se usa solo `generative/snoise.glsl` y sus funciones de math/, que tienen licencia MIT y ya están en `sitio/vendor/lygia` (T24). El tramado de lygia (Prosperity, uso no comercial) no va en el video: si el canal de YouTube se monetiza algún día, el video no queda atado a esa licencia.
- **La cámara.**
  - Una sola ruta por capítulo, calculada sobre todos los cuadros antes de dibujar. El blanco, la distancia, el acimut y la altura siguen cada uno a su meta con un resorte críticamente amortiguado (como 0,25 s de retraso), y al final pasan por un filtro suave en los dos sentidos. Así no hay tramos en línea recta ni paradas en seco.
  - **Las metas:** el blanco es la mano (la punta que se mueve) mientras se ata, el cruce nuevo mientras se forma y el centro del nudo en la pausa. La distancia encierra el nudo y la mano; cuando se forma un cruce nuevo, se acerca un 15 % durante 1,5 s y vuelve.
  - **Nunca se congela:** en las pausas, el acimut sigue a 0,6° por segundo. La cámara que se aleja del paso 4 del as de guía, que le encantó a Gabriel, queda como el movimiento de cada final de paso con pausa larga.
  - **La medida:** `calidad` cuenta las paradas de la cámara y el tiempo quieta: hoy 14 paradas y el 16 % quieta en el as de guía; la meta es cero y cero.
  - Las tomas salen del catálogo de video-shotcraft: el giro lento (apertura), el acercamiento al detalle (cruce nuevo), el alejamiento que revela (fin de paso, aplicación y cierre) y el plano cenital (revisión).
- **Los errores, con lo que pasa cuando se hace mal** (Gabriel, 28 nov: que una animación muestre qué pasa si el nudo se hace mal).
  - **El error con imagen:** va del paso anterior a la pose del error (el motor lo ata, T21e) y se queda con la ✗. Después se termina el nudo con el error, rápido, y se usa: se tira del firme, se empuja el palo o se sube la tabla, y falla. Vuelve al paso anterior, ata el paso correcto, que se queda con la ✓, y el nudo bien hecho aguanta el mismo uso. La cámara se acerca al `encuadre` del error y se aleja para la falla.
  - **Los demás errores** van con la ✗ y su título, y cada uno con su falla animada: ya no van sobre el nudo quieto. Solo entran los que tienen `voz`.
  - **Lo que pasa** va en la especificación, en `falla` (del error y de cada uno de `otros`, formato v1.14), y la voz lo dice. En los pilotos: el as de guía con la gaza al revés no traba y se deshace al tirar del firme; en el amarre cuadrado con los ahorcados por encima, y con la cuerda floja, el palo de arriba gira o se corre al empujarlo; en la eslinga de andamio con el seno por debajo, y con una sola eslinga, la tabla se voltea al subirla, y con las vueltas lejos de la punta queda inclinada.
  - **Gabriel comprueba cada falla con cuerda real** antes de dibujarla, como el filtro 1: el video no puede mostrar una falla que no pasa.
  - **Lo que pide al motor:** nudos que se deshacen o se corren con carga, y anfitriones que se mueven (el palo que gira, la tabla que se voltea), que hoy son fijos. Es una parte nueva de T21e.
- **Las aplicaciones de los pilotos** (Gabriel las eligió el 27 nov; dentro de D1: solo los amarres sostienen personas). Las escenas van en `guion.ESCENAS`; la utilería es propia, hecha en Blender, sobre el campamento J&E Gray 02, que ya trae los árboles de fondo, así que Sapling Tree Gen no hace falta para los pilotos.
  - **El nudo trabaja** (Gabriel, 27 nov): en las tres, la cuerda empieza floja, se tensa cuando entra la carga y el nudo aguanta; después la cámara se aleja hasta mostrar el uso. El nudo apretado se coloca con un giro rígido, y la carga es el motor llevando sus puntas hasta sus anclas y asentándolas (T21e), con el crujido del foley. Ahí se comprueba que nada se atraviese y que el lazo abrace la utilería, no la secuencia vista desde arriba.
  - **El as de guía, el cabo de un toldo (`toldo`, unos 11 s):**
    - De 0 a 3 s, el nudo de cerca: la gaza rodea un poste de madera clavado en la tierra, cerca del suelo, y el cabo está flojo.
    - De 3 a 6 s, el toldo jala el cabo: se tensa y la gaza no se cierra.
    - De 6 a 11 s, la cámara se aleja y sube hasta mostrar el toldo armado, movido por el viento.
    - Dice: «En el campamento, el as de guía sirve para tender un toldo. La gaza rodea el poste, y aunque el viento tire del cabo, no se cierra ni se corre.»
  - **El amarre cuadrado, la mesa del campamento (`mesa-de-campamento`, unos 12 s):**
    - De 0 a 3 s, el amarre de una esquina de cerca, en una mesa de palos de 4 cm (cada cruce lleva una copia del mismo nudo).
    - De 3 a 6 s, una olla se apoya en la mesa y nada se mueve.
    - De 6 a 12 s, la cámara se aleja hasta mostrar la mesa entera, con un amarre en cada cruce y ollas encima.
    - Dice: «Con amarres cuadrados se arma la mesa del campamento, uno en cada cruce. Con los mismos amarres se hacen torres y puentes, donde sí se sube la gente: por eso cada amarre tiene que quedar firme.»
  - **La eslinga de andamio, una repisa en la cocina (`repisa-colgante`, unos 11 s):**
    - De 0 a 3 s, una eslinga de cerca, en la punta de la tabla. La tabla cuelga de un palo atravesado entre dos postes, a la altura del pecho, con una eslinga en cada punta (el nudo y su espejo).
    - De 3 a 6 s, se ponen las ollas encima: las eslingas se tensan y la tabla sigue horizontal.
    - De 6 a 11 s, la cámara se aleja hasta mostrar la repisa colgada entre los dos postes, con ollas y tazas.
    - Dice: «En la cocina del campamento, dos eslingas de andamio cuelgan una tabla de un palo, y queda una repisa para las ollas, lejos del suelo.» Su seguridad dice que no sostiene personas.
- **«En la práctica» de los 36 nudos** (Gabriel la aprobó el 27 nov, después de cambiar siete: el ballestrinque, la media llave y dos cotes, el nudo de liberación rápida, el tensor ajustable (el mismo viento, con el nudo de liberación rápida ya hecho en la anilla), el nudo aguja, el pescador y la mariposa alpina, y la palabra «tienda de campaña», que dice la voz la primera vez, y «tienda» después). Cada nudo hace en el campamento lo que dice su ficha, con objetos y dentro de D1: solo los amarres sostienen personas, y aquí ni ellos las muestran. Como en los pilotos, el nudo trabaja (la cuerda floja que se tensa con la carga y el nudo que aguanta, o lo que distingue a ese nudo: el tope que se traba, el nudo que se suelta de un tirón) y después la cámara se aleja hasta mostrar el uso; la escena dura lo que necesite. Las tres de los pilotos son las que eligió Gabriel. Cada nudo tiene su escena en `guion.ESCENAS`, y las de un mismo lugar comparten la utilería, propia y hecha en Blender.
  - **Los lugares**, con su utilería:
    - `comedor`: un toldo entre dos árboles, con su cumbrera, postes clavados en la tierra y un farol.
    - `tienda`: la tienda de campaña, con sus vientos, sus anillas y sus estacas, un árbol cerca, el perímetro de estacas, el palo de la entrada, una mochila y una colchoneta.
    - `cocina`: la mesa de palos, la repisa colgante, un poste, baldes, sacos y ollas.
    - `fogon`: el fuego, con su trípode y una olla.
    - `asta`: dos palos unidos, la roldana arriba, la cornamusa, el destorcedor y la bandera.
    - `lena`: la pila de leña bajo una lona, troncos sueltos y atados.
    - `arboles`: un tendedero entre dos árboles, con ropa y cosas colgadas, y una rama alta.
    - `arroyo`: un puente de palos sobre un arroyo.
    - `almacen`: cuerdas adujadas colgadas de ganchos.

  | Nudo | Lugar | Lo que pasa | Lo que dice la voz |
  |---|---|---|---|
  | As de guía | comedor | La gaza rodea un poste clavado en la tierra y el cabo, flojo, sube a una esquina del toldo. El toldo jala: el cabo se tensa y la gaza no se cierra. La cámara se aleja y sube hasta el toldo armado, movido por el viento. (Elegida por Gabriel.) | «En el campamento, el as de guía sirve para tender un toldo. La gaza rodea el poste, y aunque el viento tire del cabo, no se cierra ni se corre.» (8 s) |
  | Ballestrinque | tienda | El perímetro del campamento: una cuerda alrededor de la tienda de campaña, atada a cada estaca con un ballestrinque. La cuerda llega floja a una estaca, se tensa hacia la siguiente y el ballestrinque no se corre. La cámara sigue la cuerda de estaca en estaca hasta mostrar el perímetro entero alrededor de la tienda. (Pedida por Gabriel.) | «Con ballestrinques se arma el perímetro del campamento alrededor de la tienda de campaña, uno en cada estaca. Se hace rápido, y si hace falta correrlo, se afloja fácil.» (10 s) |
  | Vuelta de escota | comedor | La cuerda gruesa de una esquina del toldo no alcanza el árbol: está unida a un cordel más delgado con una vuelta de escota. El toldo jala, la unión se tensa y no se suelta. La cámara sigue la cuerda desde el nudo hasta el árbol. | «Cuando la cuerda del toldo no alcanza, le unes un cordel con una vuelta de escota. Aunque uno sea más grueso que el otro, la unión aguanta.» (8 s) |
  | Amarre cuadrado | cocina | El amarre de una esquina de la mesa, de cerca. Una olla se apoya en la mesa y nada se mueve. La cámara se aleja hasta la mesa entera, con un amarre en cada cruce y ollas encima. (Elegida por Gabriel.) | «Con amarres cuadrados se arma la mesa del campamento, uno en cada cruce. Con los mismos amarres se hacen torres y puentes, donde sí se sube la gente: por eso cada amarre tiene que quedar firme.» (11 s) |
  | Cabeza de turco | tienda | Una pañoleta cuelga de un gancho en el palo de la tienda, con las dos puntas pasadas por la cabeza de turco. El anillo sube por las puntas hasta donde se quiere y se queda ahí. La cámara gira despacio alrededor del anillo. | «La cabeza de turco es el anillo de la pañoleta: pasas las dos puntas por dentro y lo subes hasta donde quieras.» (7 s) |
  | Simple | comedor | La cuerda de una esquina del toldo pasa por el ojal de la lona y lleva un nudo simple en la punta. El toldo jala, la cuerda corre por el ojal y el nudo se traba contra él. La cámara se aleja hasta la esquina del toldo. | «Con un nudo simple en la punta, la cuerda ya no se sale del ojal. Es el tope más chico, y queda justo contra la lona.» (7 s) |
  | Ocho | asta | La driza de la bandera pasa por la roldana de arriba del asta y lleva un ocho en la punta. La driza se suelta, corre hacia arriba y el ocho se traba en la roldana: no se escapa. La cámara sube por el asta hasta la roldana. | «El ocho en la punta de la driza no la deja escapar por la roldana del asta. Es más grueso que el nudo simple, y después se desata fácil.» (8 s) |
  | Ocho doble | comedor | Un farol cuelga de un mosquetón enganchado en la gaza de un ocho doble, en la punta de una cuerda que baja de la cumbrera. El farol queda colgando: la cuerda se tensa con su peso, el farol se mece y la gaza no se corre. La cámara se aleja hasta el comedor. | «Con un ocho doble cuelgas el farol del comedor de un mosquetón. La gaza no se corre, aguanta el peso y se revisa fácil a la vista.» (8 s) |
  | As de guía español | lena | Un tronco en el suelo, con una de las dos gazas en cada punta. La cuerda de arriba se tensa, las gazas toman el peso y el tronco sube horizontal, sin que se cierren. La cámara se aleja con el tronco colgado. | «Con las dos gazas del as de guía español levantas un tronco, una gaza en cada punta: sube horizontal y las gazas no se cierran.» (7 s) |
  | Mariposa alpina | arboles | Un tendedero entre dos árboles, con varias mariposas a lo largo de la cuerda que hacen de argollas. De ellas se cuelgan cosas: una bolsa, una taza, un farol. La cuerda baja con el peso, el viento mueve lo colgado y las mariposas aguantan. La cámara recorre el tendedero. (Pedida por Gabriel.) | «En la cuerda del tendedero, cada mariposa alpina hace una argolla fija para colgar cosas, y aguanta aunque tire para cualquier lado.» (8 s) |
  | Margarita | arboles | Un tendedero entre dos árboles quedó largo y cuelga. Con una margarita en medio, se le quita lo que sobra: la cuerda queda tensa y se cuelga la ropa. La cámara se aleja hasta el tendedero con la ropa. | «Si el tendedero quedó largo y no alcanzas sus puntas, lo acortas en medio con una margarita, y vuelve a quedar tenso.» (7 s) |
  | Arnés de hombre | lena | Un tronco atado a una cuerda que tiene tres gazas de arnés de hombre, una detrás de otra. Las tres gazas se tensan a la vez hacia fuera del cuadro y el tronco se arrastra por la tierra; ninguna se corre. La cámara acompaña al tronco. | «Para arrastrar un tronco entre varios, haces una gaza de arnés de hombre para cada uno, a lo largo de la misma cuerda: cada gaza es un asa para tirar.» (9 s) |
  | Silla de bombero | lena | Un tronco más grueso de una punta que de la otra, con una gaza en cada punta: una más grande y otra más chica, ajustadas antes de trabarlas. La cuerda se tensa y el tronco se arrastra parejo; los cotes no dejan que las gazas se corran. La cámara acompaña al tronco. | «Con la silla de bombero arrastras un tronco con una gaza en cada punta. Antes de trabarlas, ajustas cada gaza a su grosor.» (7 s) |
  | Rizo | tienda | Una colchoneta enrollada junto a la tienda, atada con una cuerda y un rizo encima. La colchoneta empuja para desenrollarse, la cuerda se tensa y el rizo no se suelta. La cámara se aleja hasta la mochila y la tienda. | «Con un rizo atas la colchoneta enrollada. Queda apretada, el nudo es plano y no molesta, y después se desata fácil.» (7 s) |
  | Pescador | tienda | Un viento de nylon de la tienda se rompió, y sus dos partes están unidas con un pescador. Una ráfaga tensa el viento y la unión no se suelta. La cámara sigue el viento hasta la tienda. | «Si se rompe un viento de la tienda de campaña, unes las dos partes con un pescador. En cuerdas delgadas o resbalosas, donde un rizo se soltaría, el pescador aguanta.» (9 s) |
  | Pescador doble | comedor | Un cordino cerrado en anillo con un pescador doble: es el anillo del prusik, puesto en la cumbrera del toldo. La esquina del toldo tira, el anillo se tensa y la unión no se mueve. La cámara se aleja hasta el toldo. | «Con un pescador doble cierras un cordino en anillo, firme aunque sea resbaloso. Ese anillo es el que se usa en el prusik.» (7 s) |
  | Nudo aguja | asta | En el asta, la driza lleva un destorcedor atado con un nudo aguja, y en él se engancha la bandera. La bandera sube; el viento la hace girar y el destorcedor gira con ella, sin torcer la driza. La cámara sube hasta la bandera en lo alto. | «Con un nudo aguja atas la driza al destorcedor de la bandera: con el viento la bandera gira, y la driza no se tuerce.» (7 s) |
  | Ballestrinque doble | cocina | En el poste de la cocina, una cuerda atada con un ballestrinque doble sostiene un balde que cuelga junto al poste. El balde se llena, la cuerda tira hacia abajo, a lo largo del poste, y el nudo no resbala. La cámara se aleja hasta la cocina. | «Cuando la carga tira a lo largo del palo, el ballestrinque doble no resbala: con él cuelgas un balde de un poste parado.» (7 s) |
  | Vuelta de braza | lena | Un atado de leña con una vuelta de braza. La cuerda se tensa y el atado sube del suelo; cuando se baja y la cuerda se afloja, la vuelta se deshace casi sola. La cámara se aleja hasta la pila de leña. | «Con una vuelta de braza levantas un atado de leña: mientras tiras, aguanta, y cuando dejas de tirar, se deshace casi sola.» (7 s) |
  | Media llave y dos cotes | tienda | Un viento de la tienda va a un árbol, amarrado con una media llave y dos cotes. Una ráfaga mueve la tienda y la cuerda tira hacia un lado y hacia el otro; el nudo aguanta. La cámara se aleja hasta la tienda. | «Cuando un viento de la tienda de campaña va a un árbol, lo amarras con una media llave y dos cotes: aguanta aunque las ráfagas tiren para todos lados, y después se desata fácil.» (10 s) |
  | Fugitivo | lena | Una lona cubre la leña, amarrada a un poste con un fugitivo; el viento la levanta y la cuerda tira. Un tirón del chicote y el nudo se suelta, aunque la lona siga tirando. La cámara se aleja hasta la pila de leña. | «El fugitivo deja algo amarrado por un rato: aunque la cuerda tire, con un tirón del chicote se suelta.» (6 s) |
  | Tensor | comedor | La cumbrera del toldo, una cuerda entre dos árboles, cuelga floja. El tensor se tira desde abajo: el seno trabaja de polea, la cuerda se tensa y el toldo queda firme. La cámara se aleja hasta el toldo armado. | «Con un tensor tensas la cuerda del toldo entre dos árboles. El seno del nudo trabaja de polea: tiras con menos fuerza, y la cuerda queda firme.» (8 s) |
  | Tensor ajustable | tienda | Un viento de la tienda: en la anilla de la tienda ya está hecho el nudo de liberación rápida, y en la otra punta, el tensor ajustable rodea su estaca. El viento está flojo: el tensor se corre por la cuerda, el viento se tensa y la tela de la tienda queda firme; cuando la tienda tira, el nudo se traba. La cámara va de la estaca a la anilla y se aleja hasta la tienda entera. (Pedida por Gabriel.) | «En la tienda de campaña, el viento ya está anclado a la anilla con un nudo de liberación rápida. En la estaca, lo tensas con un tensor ajustable: lo corres por la cuerda para tensar o aflojar, y cuando la cuerda tira, se traba.» (12 s) |
  | Constrictor | cocina | La boca de un saco de arroz, cerrada con un constrictor. El saco se levanta y el peso tira de la boca; el constrictor aprieta y no la suelta. La cámara se aleja hasta la cocina. | «El constrictor aprieta y no suelta: con él cierras la boca de un saco, y aunque lo levantes, no se abre.» (6 s) |
  | Nudo de liberación rápida | tienda | Un viento se ancla a la anilla de la tienda con un nudo de liberación rápida, y en la otra punta se tensa hacia una estaca con un tensor ajustable. La cuerda tira y el nudo aguanta; al desarmar la tienda, un tirón del chicote y se suelta al instante. La cámara va de la anilla a la estaca. (Pedida por Gabriel.) | «En la tienda de campaña, el viento se ancla a la anilla con un nudo de liberación rápida, y en la estaca se tensa con un tensor ajustable. Al desarmar la tienda, un tirón del chicote y se suelta al instante.» (11 s) |
  | Presilla de alondra | tienda | En el palo de la entrada de la tienda, una presilla de alondra con un cordón del que cuelga una linterna. La linterna queda colgando, el cordón se tensa y la presilla no se corre. La cámara se aleja hasta la tienda. | «Con una presilla de alondra cuelgas la linterna del palo de la tienda de campaña. Se hace rápido, y aunque quede tirante, se desata fácil.» (8 s) |
  | Prusik | comedor | En la cumbrera del toldo, un prusik sujeta una esquina. Sin carga, se corre por la cumbrera hasta su lugar; cuando la esquina tira, se aprieta y no se mueve. La cámara se aleja hasta el toldo. | «El prusik se corre por la cuerda cuando está suelto, y con carga se aprieta y no se mueve: con él ajustas la esquina del toldo en la cumbrera.» (8 s) |
  | Amarre redondo | asta | El asta de la bandera, hecha con dos palos unidos a lo largo con dos amarres redondos. La bandera sube, el viento mueve el asta y los palos no se corren. La cámara sube por el asta desde los amarres hasta la bandera. | «Con amarres redondos unes dos palos a lo largo para alargarlos: con ellos se arma el asta de la bandera, y los palos no se corren.» (8 s) |
  | Amarre diagonal | cocina | Las patas de la mesa, reforzadas con dos diagonales que se cruzan; en el cruce, un amarre diagonal. La mesa se carga con ollas, las diagonales tienden a separarse y el amarre las junta: nada se mueve. La cámara se aleja hasta la mesa. | «Las diagonales que refuerzan las patas de la mesa no se cruzan en ángulo recto y tienden a separarse: por eso se unen con un amarre diagonal.» (8 s) |
  | Amarre trípode | fogon | Tres palos unidos por una punta con un amarre trípode, abiertos sobre el fogón; de arriba cuelga una olla. La olla se llena, el peso empuja las patas a abrirse y el amarre las sostiene. La cámara se aleja hasta el fogón. | «Con el amarre trípode unes tres palos por una punta y los paras abiertos: es la base de un fogón, y de arriba puedes colgar la olla.» (8 s) |
  | Refuerzo de cabo | comedor | La punta de una cuerda de algodón, con su refuerzo, pasa una y otra vez por el ojal de la lona sin deshilacharse. La cámara se acerca a la punta. | «Con el refuerzo de cabo, la punta de la cuerda no se deshilacha, aunque pase muchas veces por el ojal. Sirve en las cuerdas que no se pueden fundir, las de algodón.» (9 s) |
  | Adujado | almacen | Una cuerda adujada cuelga de un gancho del almacén. Se suelta y cae, y se desenrolla sin enredarse. La cámara sigue la cuerda hasta el suelo. | «Con el adujado guardas la cuerda sin que se enrede, y cuando la necesitas, la sueltas rápido.» (6 s) |
  | Puño de mono | arboles | La punta de una cuerda con un puño de mono vuela por encima de una rama alta y baja del otro lado, llevada por su peso. La cuerda queda colgada de la rama, lista para subir algo. La cámara sigue el puño. Es la escena más difícil para el motor; si no sale, el puño va de tirador en la cuerda de la campana. | «El peso del puño de mono lleva la cuerda más lejos: con él la lanzas por encima de una rama alta.» (6 s) |
  | Eslinga de barril | arroyo | Un balde lleno de agua, en la orilla del arroyo, con una eslinga de barril. La cuerda se tensa desde el puente y el balde sube parado, sin inclinarse ni derramar. La cámara sube con el balde hasta el puente. | «La eslinga de barril sube un balde lleno de agua sin inclinarlo: aunque esté abierto, no se derrama.» (6 s) |
  | Eslinga de andamio | cocina | Una eslinga de cerca, en la punta de una tabla que cuelga de un palo entre dos postes, con una eslinga en cada punta. Se ponen las ollas encima: las eslingas se tensan y la tabla sigue horizontal. La cámara se aleja hasta la repisa. (Elegida por Gabriel.) | «En la cocina del campamento, dos eslingas de andamio cuelgan una tabla de un palo, y queda una repisa para las ollas, lejos del suelo.» (8 s) |
  | Vuelta de cornamusa | asta | La driza sube la bandera y se asegura en la cornamusa del asta. El viento tira de la bandera, la driza se tensa y la vuelta aguanta; después se suelta en un momento y la bandera baja. La cámara se aleja hasta el asta. | «La driza que sube la bandera se asegura en la cornamusa del asta: aguanta los tirones del viento, y se suelta en un momento, aunque esté tensa.» (8 s) |

  - **Lo que pide al motor:** casi todas son el nudo apretado puesto con un giro rígido y sus puntas llevadas hasta sus anclas (T21e). Piden algo más: la anilla de la tienda, donde se ancla el nudo de liberación rápida (un anfitrión nuevo para el motor, más delgado que el poste de su ficha), los nudos que se sueltan de un tirón (el fugitivo, el de liberación rápida y la vuelta de braza, que se deshace al aflojar), la cuerda adujada que cae y se desenrolla, y el puño de mono que vuela por encima de la rama, que es la más difícil.
  - **Las voces** siguen el estilo del guion (las 36 pasan `estilo_del_guion` y la comprobación de términos de sección) y dicen lo mismo que el `usos` de su ficha. Cada una pasa al `video.aplicacion` de su especificación, con su escena en `guion.ESCENAS`, cuando se escriba el guion de ese nudo, antes de T19.
- **El reel vertical** (45 a 60 s; estimados: el as de guía 54 s, el amarre 58 y la eslinga 46).
  - El gancho (la primera frase de la apertura, hasta los dos puntos: «El as de guía hace una gaza fija en la punta de la cuerda.») sobre el nudo terminado en el campamento, de cerca y girando; el título de cada paso dicho mientras se ata a unas dos veces la velocidad; «El error más común: la gaza pequeña al revés.», con la ✗ y la ✓; la primera frase de la aplicación, y la primera del cierre («Ya sabes hacer el as de guía.»). `video.reel` cambia el gancho o el cierre si hace falta.
  - Su propia cámara, más cerca. El nudo va entre el 22 % y el 62 % del alto (no entre el 29 % y el 76 % de T18), las tarjetas arriba, desde el 12 %, y los subtítulos palabra por palabra, quemados, entre el 65 % y el 75 %: por encima de donde Instagram pone la descripción y los botones.
  - Los subtítulos: de a cuatro palabras, en Literata blanca con sombra, y la palabra que se dice sobre un fondo ámbar. Los tiempos de cada palabra son los del alineador.
- **Lo que sale de cada video:**
  - `<slug>-4k.mp4`, el video completo, y `<slug>-vertical.mp4`, el reel, con su audio, como en T18.
  - `<slug>.srt`, los subtítulos de la voz para YouTube, de las palabras alineadas: hasta dos líneas de 42 letras, cortadas en la puntuación, de 1 a 6 s cada uno.
  - `<slug>-youtube.txt`: los capítulos para la descripción (el primero en 0:00 y cada uno de 10 s o más, como pide YouTube: la apertura va junta con lo que necesitas), la dirección del visor y el nudo que sigue.
  - `<slug>-visor.mp4`: solo el capítulo del paso a paso, en 1080p y de 20 MB o menos. Como el paso a paso dura más que el video de T18 (63 s el as de guía, 83 el amarre), va a 30 cuadros por segundo y en dos pasadas, para que quepa sin perder detalle.
  - El nombre del grupo, «Grupo Guías y Scouts Huetares 431», y su logo van en la apertura y en el cierre (Gabriel, 28 nov).
- **La duración no limita** (Gabriel, 27 nov): el video dura lo que haga falta para explicar bien y que quede claro, y no se recorta ninguna escena ni ninguna explicación para que dure menos. Ya no hay una meta de 2 min. Con el guion completo, los pilotos duran de 2:45 a 3:30, y cada escena puede alargarse si lo necesita. El reel sigue en 45 a 60 s.
- **Lo que cuesta.** Los videos van con EEVEE a 32 muestras (Gabriel, 27 nov; `aspecto.MOTOR_VIDEO`), a unos 3,3 s por cuadro de 4K. El render crece con la duración: el as de guía son unas 9,5 h, y los 36 con sus reels, unos 16 días si duran como los pilotos (3 min en promedio, y 52 s el reel). Los 11 días de la elección de EEVEE suponían videos de 2 min.
  - **El cuadro quieto** (Gabriel, 28 nov): lo que necesitas, la seguridad y la pantalla final van sobre un cuadro quieto del render, con un acercamiento lento hecho en la composición, sin Blender. Los errores no, porque llevan su falla animada. Con eso y las fallas, los 36 con sus reels son unos 14 días de render.
- **Lo que decide Gabriel en el punto de control:**
  1. El diseño, con el guion en la especificación (v1.14): aprobado entero el 28 nov.
  2. El guion del as de guía (`guion as-de-guia`): aprobado el 28 nov.
  3. Las tarjetas de la maqueta: decididas el 28 nov (la del paso sale y vuelve a entrar, la paleta es «Huetares» y el logo no va en la esquina).
  4. Las tres aplicaciones: decididas el 27 nov (el toldo, la mesa y la repisa, con el nudo que se tensa y aguanta).
  5. La duración, el motor y el cuadro quieto: decididos (la duración no limita y EEVEE a 32 muestras, el 27 nov; el cuadro quieto para lo que necesitas, la seguridad y la pantalla final, y los errores con su falla animada, el 28 nov): unos 14 días de render para los 36. El nombre y el logo del grupo van en la apertura y el cierre (decidido el 28 nov).
  6. «En la práctica» de los 36 nudos: aprobada el 27 nov, con siete cambios suyos (abajo).

**Cómo se hizo T22a (27 nov):**
- **El formato v1.14** (`nudos/spec.py`, `docs/formato-spec.md`): `voz` en los pasos (de segmentos y de plantilla), en el error y en `otros`, y el bloque `video` con sus clases (`Video`, `Revisa`, `Aplicacion` y `Reel`). `mira` se comprueba al cargar contra los segmentos o los hitos de la plantilla, y las medidas de la plantilla (`{vueltas}`) se reemplazan también en lo que dice la voz. Las 36 especificaciones cargan igual.
- **El guion de los tres pilotos** está en sus especificaciones. El de los dos de T23 salió de `config/guion/`, que se borró.
- **`nudos/guion.py`** y la orden `guion <slug> [--oir]`. `PALABRAS_EVITAR` y `estilo_del_guion` pasaron de `prueba_sonido.py` a `guion.py`; `prueba_sonido.lineas_del_guion` lee el guion de la especificación, y `narracion` pone la tarjeta de cada capítulo y el golpe en el cierre. `voz.en_cache()` da las locuciones ya generadas sin generar nada, para medir sin la tarjeta.
- **La maqueta:** `render/tarjetas/` (`tarjetas.css`, `tarjetas.js` y `maqueta.html`) y `nudos/tarjetas.py`, con la orden `prueba-tarjetas [--fondo …] [--fondo-vertical …]`. La página lleva dentro las fuentes, lygia y los dos fondos: un cuadro de la prueba en 4K del as de guía, con la tarjeta de hoy borrada, y un recorte vertical del mismo.
- **Pruebas:** `tests/test_guion.py` y `tests/test_tarjetas.py`.
- **El grupo en la ficha** (Gabriel, 28 nov): el logo (`libro/logo-431.svg`) a la izquierda de «Libro de nudos · Grupo Guías y Scouts Huetares 431», arriba de la primera página, y con el nombre del grupo en el pie de las dos (`libro/ficha.html` y `ficha.css`; `html_ficha` lo pone en la página). Antes decía «Grupo Guía y Scout 431».
  - **Sin ocupar alto:** con el logo dentro del flujo (11 mm arriba y 7 mm en el pie), 30 de las 36 fichas dejaban de caber: están justas. Por eso los dos logos van fuera del flujo. El de arriba (8,6 mm) se apoya en la línea y sube hacia el margen, hasta unos 6 mm del borde del papel, y el del pie (6,8 mm) va centrado en su línea, en el hueco que ya había. Las páginas no crecen nada. Los 6 mm del borde se revisan con las especificaciones de la imprenta (D8).
  - El sitio y el README dicen también el nombre completo desde el 28 nov (las cejas, los títulos, los pies y la descripción del índice); el título del proyecto sigue siendo «Libro de nudos del Grupo 431».

**Punto de control:** Gabriel aprueba el diseño, el guion de un piloto y la maqueta de las tarjetas. Cumplido el 28 nov: Gabriel aprobó el diseño completo.

**T22b, la implementación (L).**
- `nudos/video.py` gana los capítulos, el guion (`guion.revisado`), la cámara nueva, las tarjetas (`render/tarjetas/` en Edge, cuadro por cuadro, con el vidrio desenfocado en Pillow), los errores, la aplicación (las escenas de `guion.ESCENAS`) y el reel. Si crece demasiado, se parte en un paquete `nudos/video/`.
- Los subtítulos (`.srt`), la descripción con los capítulos (`-youtube.txt`) y la copia del visor del paso a paso, a 30 fps.
- **El disco:** un video de 3 min en 4K son unos 350 GB de cuadros. Por eso se arma por tramos: cada unos 10 s se codifican en un intermedio sin pérdida y los PNG se borran. `NUDOS_CUADROS` pasa a D:, que tiene 625 GB libres; C: tiene 164.
- **La previa entera** (960 × 540) de los tres pilotos, con voz, música y tarjetas. Punto de control.
- **Los tres pilotos en 4K y en vertical,** de noche. Punto de control.

#### Los repositorios sugeridos: qué se usa y por qué

- **lygia (sí, en la web):** va en el visor (el relieve de la trenza en GLSL, el ruido y el tramado) y en las tarjetas animadas del video, que dibuja Edge.
  - En Blender no sirve: Cycles no corre GLSL y lygia no trae OSL.
  - Su licencia, Prosperity 3.0.0, permite el uso no comercial, y el grupo lo es.
  - Se copian solo los archivos que se usan, con el texto de la licencia, como three.js en `sitio/vendor/`.
- **react-three-rapier (no):** Rapier simula cuerpos rígidos unidos con articulaciones. Una cuerda hecha de eslabones se atraviesa en un nudo apretado y cambia los cruces sin avisar, que es justo lo que impide la IPC con CCD del motor.
- **react-postprocessing (no, pero sí la idea):** el visor no usa React, y `postprocessing` de pmndrs pide three ≥ 0.168. Los pases que hacen falta ya vienen con three.js 0.160 (GTAOPass, SMAAPass y OutputPass), así que se usan esos sin cambiar de versión, y `exportar()` no se mueve.
- **librosa (sí, en el audio):** corta a compás la música generada (la candidata B) y comprueba la sincronía del audio armado. Pide Python ≥ 3.13 y numba: primero se prueba que instale en el 3.14 del venv, y si no, va en el entorno de la música.
- **video-shotcraft (como referencia):** una skill de Remotion con 124 fichas de tomas y notas sobre ritmo, sincronía con el pulso y sonido (Apache-2.0). Sirve de catálogo de ideas para la cámara, las transiciones y las tarjetas; su código no se usa.

#### Costos, orden y verificación del pulido

**Costos:**
- **Render:** 2 semanas para los 36. Cada nudo tiene unos 7200 cuadros del video largo y unos 3000 del reel (que cuestan la cuarta parte), así que hacen falta unos 4 s por cuadro de 4K en promedio. T20a mide si Cycles cabe; si no, va EEVEE.
- **Disco:** los cuadros van por tramos a D:. Con permiso de Gabriel, se borran los 36 GB de cuadros viejos del as de guía en `%LOCALAPPDATA%\nudos\cuadros`.
- **Dinero:** cero con la voz y la música locales. ElevenLabs entra solo si la voz local no convence: un plan mensual, durante uno o dos meses.
- **Instalaciones,** con permiso de Gabriel al momento de bajar cada una:
  - Los modelos de voz y ACE-Step, en entornos fuera de A:.
  - sfizz o FluidSynth, con un banco de instrumentos libre.
  - pyloudnorm y librosa.
  - La extensión Sapling Tree Gen de Blender.
  - Texturas y HDRI CC0 de Poly Haven.
  - Los complementos de three@0.160.0.
  - Los archivos de lygia.

**Orden.** Van en paralelo T20a y T24 (sesión «el aspecto»), T21 (la sesión del plan) y T23a y T23b (sesión «el sonido»). T22 integra todo, y después viene T19. Los puntos de control de Gabriel, cada uno con algo que ver u oír, son estos:
1. El cuadro final con sus costos (T20a).
2. El diseño del motor (T21a) y sus pruebas de 10 s (T21c y T21d).
3. La escucha de voces y músicas (T23).
4. El diseño del video, el guion y la maqueta de las tarjetas (T22a).
5. La previa entera de los tres pilotos (T22b).
6. Los pilotos en 4K.
7. El visor (T24).

**Verificación:**
- **Pruebas rápidas de cada módulo nuevo:**
  - El guion: términos de sección, tuteo y campos.
  - La voz, con un proveedor falso: el caché y los tiempos.
  - La música: los compases caen en los capítulos, y repite con la misma semilla.
  - La mezcla: LUFS, pico y *ducking*.
  - Las tarjetas caben.
  - La velocidad de la cámara es continua.
  - El motor, según T21.
  - La aplicación: la cuerda queda fuera de la utilería y las puntas llegan a sus anclas.
- **Las fichas no cambian** (salvo con T20c): con `referencia` antes y después, `comparar` da los 36 `modelo.json` iguales byte a byte.
- **La suite entera:** `.venv/Scripts/python -m pytest -n 4 --dist loadfile`.
- **De punta a punta:** `python -m nudos video <piloto> --previa` de los tres pilotos, con todo, y después en 4K.

#### T19: Todos los nudos a la vez

**Descripción:** con todo implementado y probado en los pilotos, una sola corrida calcula todos los nudos con el motor, dibuja todas sus fichas en Blender y arma todos sus videos. No hay tandas (Gabriel, 23 nov).
- **Antes, desde el pulido a fondo (26 nov):** la tabla de aplicaciones de los 36 nudos en texto, que Gabriel aprueba (aprobada el 27 nov; está en T22a, «En la práctica» de los 36 nudos); la falla de cada error de los 36, comprobada con cuerda real; sus escenas, armadas por familias (en poste, amarres, dos cuerdas…); los guiones revisados, y las voces y la música generadas. El render de los videos es de unas 2 semanas.
1. `referencia` de todos los nudos con el código de antes de la fase, para comparar.
2. Todos los nudos construidos con el motor, a la vez y con todos los núcleos (`nudos/procesos.py`), de noche si hace falta.
3. `comparar` dice qué cambió en cada nudo. Donde la secuencia de algún paso no es la declarada, el paso se corrige (ver «La secuencia declarada sigue mandando» en T15) y se vuelve a correr.
4. Las fichas y los videos de todos, y una página de prueba con todas las fichas, en color y en gris.
5. `relajar()` y `apretar()` se borran: ya ningún nudo los usa. (Ojo, 27 nov: `relajar()` es ahora la partida de respaldo del motor; ver abajo.)
6. Se publica el sitio, con la misma dirección para cada nudo.

**Antes de T19 (27 y 28 nov):** los 36 nudos construyen sin fallas con el motor; su «Cómo se hizo» está en el historial. Queda una decisión de Gabriel para el paso 5: `relajar()` es ahora la partida de respaldo del motor (cuando `separar` no logra la cuerda de partida de un paso, o el paso queda fuera de los límites), así que no se puede borrar tal cual. Puede quedarse en `nudos/libre.py` o pasar a `nudos/fisica/`. `apretar()` sí se puede borrar.

**Criterios de aceptación:**
- [ ] Todos los nudos construyen sin fallas con el motor, con la secuencia declarada en cada paso, y construir dos veces da lo mismo byte a byte.
- [ ] Todas las fichas caben y se leen en gris, y cada nudo tiene su video en el visor y en vertical para redes.
- [ ] Gabriel revisa en papel todas las fichas y decide en qué nudos se repite el filtro 1 (los que cambiaron de secuencia, si hubo alguno).

**Dependencias:** T15 a T18 y T20 a T24. **Tamaño:** L, casi todo tiempo de cálculo y de render.

#### Punto de control de la fase 5

- [ ] Todos los nudos calculados con el motor en T19, todas las fichas rehechas en Blender y un video por nudo en el visor.

### Fase 6: libro y primera edición

Va después de la fase 5 (Gabriel, 23 nov): las fichas del libro salen con la cuerda del motor y con el render de Blender.

#### T11: Material inicial del libro

**Descripción:** armar la portada, la sección "cómo leer una ficha", el glosario (firme, chicote, seno, gaza, cote, vuelta, mena…), la postura de seguridad que fije D1 y el índice por familia.

**Criterios de aceptación:**
- [ ] Todo término del vocabulario controlado que aparece en las fichas está en el glosario, según una prueba automática.
- [ ] Un probador del filtro 2 usa "cómo leer una ficha" sin ayuda.

**Verificación:**
- [ ] `pytest tests/test_glosario.py`
- [ ] Manual: incluir "cómo leer una ficha" en la siguiente prueba del filtro 2.

**Dependencias:** D1 y al menos la tanda 1

**Archivos:** `libro/inicio.html`, `libro/glosario.yaml`, `tests/test_glosario.py`

**Tamaño:** S

#### T12: Anexos por sección

**Descripción:** generar los anexos de la Wak (U-suré y Sênuk) y de la Tropa (según D3) desde el campo `secciones` de cada especificación.

**Criterios de aceptación:**
- [ ] Cada nudo del PPP y de la lista de la Tropa aparece en su anexo, junto con quién lo valora.
- [ ] Los términos propios de cada sección solo aparecen en su anexo.

**Verificación:**
- [ ] `pytest tests/test_anexos.py`
- [ ] `python -m nudos libro`

**Dependencias:** D3, T11

**Archivos:** `libro/anexos.html`, `nudos/anexos.py`, `tests/test_anexos.py`

**Tamaño:** S

#### T13: Edición 1

**Descripción:** generar el PDF completo con un colofón que indique número de edición y fecha, el registro de cambios y el sitio publicado. Marcar la versión con la etiqueta `edicion-1` en git e imprimir.

**Criterios de aceptación:**
- [ ] Un solo comando construye el libro completo desde un clon limpio.
- [ ] Los 36 nudos están en `publicado` y todos sus QR responden.
- [ ] Revisaste una prueba de la imprenta antes del tiraje.

**Verificación:**
- [ ] `pytest`
- [ ] `python -m nudos libro`
- [ ] Manual: escanear todos los QR del ejemplar impreso.

**Dependencias:** fase 4, la fase 5 (T19: todos los nudos con el motor y con el render de Blender), T11, T12 y D8. La edición 1 se imprime con las imágenes nuevas.

**Archivos:** `nudos/libro.py`, `libro/colofon.html`, `CHANGELOG.md`

**Tamaño:** S

#### Punto de control final

- [ ] Se cumplen todos los criterios y la edición 1 está impresa.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Pulir los renders sin evidencia de un problema de lectura | Bajo | T7b decide con una página de prueba impresa; solo entra lo que se nota en el papel |
| La IA lee mal un cruce de las fotos y el error pasa todas las pruebas automáticas | Alto | Revisar cada especificación nudo por nudo; filtro 1 con cuerda real; pruebas doradas antes de usar subagentes |
| Los nudos sobre poste y los amarres no caben en el modelo plano del prototipo | Alto | Se atacan primero en la fase 2 (T5 y T7); si el anfitrión falla, los enganches pasan a plantillas |
| Un slug cambia y rompe los QR impresos | Alto | Slugs que no cambian nunca; prueba contra `publicados.txt` |
| La dirección base cambia y rompe todos los QR: un cambio de usuario de GitHub, un repositorio renombrado o el paso a otra cuenta | Alto | No renombrar el usuario ni el repositorio; si el sitio cambia de dueño, dejar páginas de redirección en las direcciones viejas |
| Material de las fuentes se filtra al libro o al sitio | Alto | `entradas/` fuera de git; el sitio y el libro se construyen solo desde las especificaciones; revisión de que el texto es propio |
| Contenido de seguridad mal planteado en nudos usados con personas | Alto | Resolver D1 antes de escribir esas fichas |
| El puño de mono y la cabeza de turco son demasiado complejos | Medio | Plantillas con medidas; si fallan, pasan a una edición posterior sin bloquear la primera |
| Los renders de three.js no se leen bien impresos | Medio | Página de prueba en el Punto de control A; alternativa con Blender usando la misma geometría |
| Hay pocos probadores novatos, porque cada prueba gasta un probador por nudo | Medio | Repartir nudos entre Wak, Tropa y gente de fuera; registrar por código qué nudos conoce cada probador |
| Solo tú haces el filtro 1 y se vuelve un cuello de botella | Medio | Sesiones de atado por tandas; otro dirigente con experiencia también puede hacer el filtro 1 |
| El formato de especificación cambia después de modelar muchos nudos | Medio | Formato congelado en el Punto de control B; cualquier cambio posterior lleva un script de migración |
| Aparecen términos de una sola sección en las fichas | Medio | Prueba automática de vocabulario por sección; esos términos solo van en los anexos |
| El proyecto no cierra porque no hay fecha | Medio | La edición 1 se define como los 36 nudos; tabla de estado; puntos de control con revisión |
| El render de Blender no repite la misma imagen y `comparar` deja de servir | Medio | Semilla fija y un solo denoiser; si aun así cambia, una tolerancia documentada en `comparar` (T16) |
| Animar los nudos libres resulta más difícil de lo previsto (la cuerda se atraviesa entre cuadros) | Alto | El motor de T15 no deja que la cuerda se atraviese (IPC con CCD); pilotos con el as de guía y el amarre cuadrado en T17 antes de comprometer los 36 videos; las fichas y el visor no dependen de los videos |
| El motor de física es lento, no converge o no repite el resultado | Alto | La prueba de concepto (T14a) mide las bibliotecas antes de comprometerse; Newton con búsqueda en línea y CCD, en `float64` y en CPU; si es lento para los videos, Warp en la GPU solo para animar |
| Al asentar con el motor, la secuencia de un paso cambia (un tramo se corre por encima de otro sin atravesarlo) | Medio | La secuencia declarada sigue mandando: el paso falla y se corrige con la tensión o las manos, nunca cambiando la secuencia; donde cambia, Gabriel decide si repite el filtro 1 |
| Las bibliotecas del motor no tienen versión para Python 3.14 en Windows | Medio | La prueba de concepto (T14a) lo comprueba primero; las alternativas son compilar `ipctk`, usar Warp o escribir la barrera y la CCD de tramo con tramo en `numba` |
| Complejidad que no se ve en el papel | Medio | Cada fenómeno entra con su prueba física y, si cambia la imagen, con la página de prueba impresa (la regla de T7b) |
| Código o texto de un paquete de pago entra al repositorio público | Alto | El paquete vive fuera de git y solo se usa como referencia; los scripts de Blender del libro son propios |
| El render de los videos ocupa la computadora por días | Bajo | Gabriel acepta el costo; se renderiza por tandas, de noche, empezando por una vista previa a media resolución |
| Los videos largos no caben en las 2 semanas de render | Medio | T20a mide Cycles y EEVEE en 4K antes de elegir el aspecto; los cuadros repetidos se dibujan una vez |
| Un video de 2 min en 4K llena el disco (unos 240 GB de cuadros) | Medio | Se arma por tramos en un intermedio sin pérdida, y los cuadros van a D: |
| La gravedad en lo que cuelga desestabiliza al motor (Newton sin la viscosidad) | Alto | T21c con el as de guía antes que nada; plan B: los resortes se quedan y lo flojo cuelga como una catenaria dentro de la guía |
| Ninguna voz local suena natural en español | Medio | Prueba de escucha a ciegas; si ninguna convence, ElevenLabs (Gabriel, 26 nov) |
| Una aplicación muestra un nudo sosteniendo a una persona | Alto | Solo objetos, salvo los amarres (D1); la sección de seguridad de la ficha entra al video |

## Preguntas abiertas

- **D3 y D8:** las decisiones previas que siguen abiertas.
- **D7:** si la dirigencia de la Tropa participa en la revisión de su anexo y en conseguir probadores.

## Lo que se reutilizó del prototipo

El prototipo del as de guía se portó completo y la carpeta `prototipo/` se borró al cerrar T3. Sigue en el historial de git:

- **`knot.py`:** el generador libre (trazado, cruces, elevación a 3D, relajación y validación). Pasó a `nudos/` en T1.
- **`render.py`:** el render de verificación en numpy. Pasó a `nudos/hoja.py` en T1.
- **`viewer.template.html` y `build_viewer.py`:** la escena three.js y el visor. Pasaron a `render/escena.js` y `sitio/` en T2.
- **`shoot.py`:** el render con Chrome sin interfaz. Pasó a `nudos/imprimir.py` en T3.
