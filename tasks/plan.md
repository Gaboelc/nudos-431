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

#### T20: El aspecto: material, escena, luz y cámara

**T20a, el cuadro final (*hero frame*), con su costo medido (M).** Una orden nueva, `python -m nudos prueba-aspecto`, dibuja en 4K tres tomas: el as de guía a mitad del paso 4, el amarre cuadrado terminado y un primer plano de la trenza. Cada toma va en cuatro aspectos, con Cycles y con EEVEE, y la orden arma `build/aspecto/prueba.pdf` con el tiempo por cuadro y la proyección para los 36 nudos (video largo más reel) contra la meta de 2 semanas, que son unos 4 s por cuadro de 4K en promedio.
- **Aspecto 0:** el de hoy.
- **Aspecto 1, estudio:**
  - La trenza con geometría: 16 hilos, 2 sobre 2, con relieve real en el contorno.
  - Brillo de filamento (anisotropía a lo largo de cada hilo), una pelusa suave (*sheen*) y un poco de variación de color entre hilos.
  - Una mesa de madera que se ve, con textura y cantos, y un fondo curvo de estudio con degradado.
  - Una luz grande de ventana, un contraluz y rebote.
  - Profundidad de campo con el foco en la punta, y viñeta y grano suaves en el compositor.
  - La vista AgX o «Khronos PBR Neutral», la que no lave el azul.
- **Aspecto 2, estudio con la cuerda real:** como el 1, pero con la cuerda de los filtros (negra con trazador amarillo, como en las fotos de T15e) y el chicote con una cinta de color.
- **Aspecto 3, campamento:** la mesa al aire libre, el fondo de árboles desenfocado (el cielo de Blender y un HDRI CC0 de Poly Haven) y sol suave.
- **Los colores de la ficha** (azul, crema, ámbar y remate) quedan en los aspectos 1 y 3.
- **En la misma prueba:**
  - El desenfoque de movimiento, con la velocidad de cada vértice (el atributo `velocity`; si Blender no lo toma bien, un desenfoque vectorial en el compositor).
  - El chicote con una cinta que siempre se ve.

**Cómo se hizo T20a (26 nov):**
- **La orden** `python -m nudos prueba-aspecto` (`nudos/aspecto.py` y `render/blender/aspecto.py`):
  - Saca las tomas del atado guardado de los pilotos (`video.atar` y `video.cuadros_de`) y las guarda en `build/aspecto/tomas.npz`; la segunda vez no hace falta el motor.
  - **Paso 4:** el cuadro más cerca de la mitad del paso con el resaltado entero a la vista, con la cámara del video. (Hoy el resaltado va por índice de nodo y en la mitad del paso queda vacío; lo arregla T21b.)
  - **Amarre:** el último cuadro del video, con una cámara de apertura más baja (1,2 rad desde la vertical) que deja ver el fondo.
  - **Trenza:** el cuello del as de guía terminado, de cerca (7,5 d de alto), con el foco en el centro de sus cruces.
  - **Movimiento:** el cuadro más rápido del paso 4 con un movimiento parejo (la punta a 7,6 d/s, en el acomodar), sin y con desenfoque.
  - Mide cada cuadro con la escena ya en la tarjeta: los «seguidos» cambian solo la malla de la cuerda, como `render/blender/video.py`. Mide también el vertical y el desenfoque, y arma `build/aspecto/prueba.pdf`. `--motores cycles:16,eevee:32` mide con otras muestras, y `--tomas` dibuja solo algunas tomas y deja las demás como estaban.
- **La trenza con geometría** (`nudos/trenza.py` y `malla_trenza` en `nudos/blender.py`):
  - Un anillo cada 0,04 d sobre la Catmull-Rom centrípeta de los nodos (5 por tramo; 10 en el primer plano) y 96 lados (160 en el primer plano).
  - El relieve de los 16 hilos va en el contorno (0,07 d de lo hondo de un surco a lo alto de un hilo), con la sección aplastada de T15g. En el remate, una cinta lisa 0,035 d más gruesa, cerrada en la punta.
  - La trenza sale de la coordenada `s` de cada nodo: hoy, el largo desde el nodo 0; con T21b, σ. El relieve se repite cada π/8 d.
  - Con la misma cantidad de nodos, la misma malla vértice a vértice, que es lo que pide la velocidad del desenfoque.
  - Los atributos `fibra_a` y `fibra_b` dan la dirección de los hilos para el brillo de filamento (la anisotropía de Cycles), y una textura dice qué hilo hay en cada punto.
  - La cuerda real: negra, con dos hilos A vecinos amarillos y la trenza a unos 26° del eje (`mosaico` 2), como en las fotos de T15e.
- **La escena** (`render/blender/aspecto.py`):
  - **Estudio:** una mesa de tablas de 18 d con los cantos biselados sobre un fondo de papel en forma de taza, que se ve igual desde cualquier lado de la mesa. Una ventana grande atrás a la izquierda, un contraluz y un relleno. La madera es toda procedural: anillos, fibras, manchas, juntas y un barniz suave.
  - **Campamento:** el HDRI da la luz y el fondo, girado para que su sol quede atrás a la izquierda de la cámara (el sol de cada HDRI está anotado en `config/recursos.yaml`). En las tomas bajas, lo que ve la cámara se baja unos grados para que entren los árboles; la luz sigue siendo la del HDRI sin bajar. EEVEE saca del HDRI un sol con sombra.
  - **La vista:** AgX con «AgX - Base Contrast», que no lava el azul.
  - **La profundidad de campo:** f/11 de un lente real a la escala de la cuerda de 8 mm (el número f, por 0,008).
  - **Viñeta y grano:** después de Blender, en Python (`vineta_y_grano`), con la semilla del cuadro; en el video irán en `_componer`.
- **El desenfoque de movimiento:** ni Cycles ni EEVEE toman el atributo `velocity` de una malla común (el cuadro sale igual, medido). Funciona con un modificador de Geometry Nodes que corre cada vértice su velocidad por el tiempo de la escena: los dos motores miran la escena al abrir y al cerrar el obturador, y ahí la cuerda ya se movió.
- **Recursos de terceros:** los dos HDRI de Poly Haven (CC0, 57 MB), bajados con permiso de Gabriel, en `recursos/hdri/` de la carpeta de A:. Están fuera de git y en `.git/info/exclude`, registrados con su huella en `config/recursos.yaml`. `nudos/recursos.py` los busca y los comprueba (desde un worktree, con `NUDOS_RECURSOS`).
- **El costo, medido en la RTX 4070** (segundos por cuadro de 4K, el promedio del paso 4 y del amarre; y días para los 36 nudos, con 7200 cuadros de 4K y 3000 del reel cada uno; la meta es 14):

  | Motor | 0 hoy | 1 estudio | 2 cuerda real | 3a Meadow | 3b J&E Gray 02 |
  |---|---|---|---|---|---|
  | Cycles, 64 muestras | 9,9 s, 32 días | 10,3 s, 34 | 10,3 s, 34 | 7,1 s, 24 | 6,6 s, 22 |
  | Cycles, 32 | 7,8 s, 25 (el de T18) | 7,4 s, 24 | 7,1 s, 23 | 4,9 s, 16 | 4,7 s, 15 |
  | Cycles, 16 | | 4,7 s, 15 | 4,6 s, 15 | 3,5 s, 11 | 3,4 s, 11 |
  | EEVEE, 64 | 2,9 s, 10 | 5,8 s, 19 | 5,8 s, 19 | 3,1 s, 10 | 3,0 s, 10 |
  | EEVEE, 32 | | 2,6 s, 9 | 2,6 s, 9 | 1,6 s, 5 | 1,6 s, 5 |
  | EEVEE, 16 | | 1,6 s, 5 | 1,6 s, 5 | 1,1 s, 4 | 1,1 s, 4 |

  - A tamaño real, Cycles con 16 muestras y EEVEE con 16, 32 y 64 se ven casi iguales: el denoiser de Cycles suaviza un poco la trenza, y EEVEE marca más los surcos y no tiene brillo de filamento.
  - El estudio cuesta más que el campamento en los dos motores: las tres luces de área con sombras suaves contra el HDRI.
  - Algunas medidas de una corrida salieron hasta el doble de lentas mientras corría a la vez otro Blender; la tabla es de una corrida con la tarjeta libre, y repite las medidas de la primera.
- **Lo que propuso Claude:** el estudio (1), con EEVEE a 32 muestras: 2,6 s por cuadro de 4K y 9 días para los 36 nudos, con margen para volver a dibujar. Se ve casi igual que Cycles a 64 muestras, que cuesta 4 veces más, y no parpadea, como podría el denoiser de Cycles con pocas muestras. Las fichas siguen en Cycles.

**Lo que eligió Gabriel (26 nov):** la cuerda real en las dos escenas que le gustaron: el estudio (2) para el paso a paso y los errores, y el campamento J&E Gray 02 (3b) para la apertura, la aplicación y el cierre (T22). La prueba de 10 s de T20b va en el estudio. El motor: Cycles con 16 muestras (de 11 a 15 días para los 36, según cuánto sea estudio y cuánto campamento).

**Punto de control:** Gabriel elige el aspecto y el motor de render, con los números a la vista.

**T20b, el aspecto elegido en los videos (M).**
- **`nudos/blender.py`:**
  - La malla de la trenza (o el tubo con desplazamiento, según lo que gane en T20a), con un anillo cada 0,08 d sobre la curva de Catmull-Rom, como en las fichas.
  - La UV, el resaltado, el remate y la cinta van por la coordenada de material σ de cada nodo, que da T21b.
  - El color de cada cuerda sale de la especificación.
- **`render/blender/video.py`:** la escena, los materiales, el foco que sigue la acción, el desenfoque de movimiento, el compositor y la vista de color, con EEVEE o con Cycles.
- **Se quita el modo video viejo** de `render/blender/escena.py`: ya no queda ningún render que lo use.
- **Prueba de 10 s en 4K** del as de guía. Punto de control.

**Cómo se hizo T20b (26 nov):**
- **La escena del video** (`nudos/aspecto.py`, sección «El aspecto de los videos»): `VIDEO` tiene las dos escenas que eligió Gabriel, con la cuerda real; `ESCENA_VIDEO` es la del paso a paso (el estudio; hasta que T22 arme los capítulos, la de todo el video) y `MOTOR_VIDEO`, Cycles con 16 muestras. Los ajustes van en dos partes, la escena y la cuerda (`AJUSTES_ESCENA` y `AJUSTES_CUERDA`), así que el campamento lleva la cuerda real; los de T20a quedan iguales.
- **Lo que se dibuja una vez por video:** la mesa cubre la cuerda de todos los cuadros y el anfitrión (`escenario_video`), y la luz (y el sol del HDRI) se orienta según la cámara del primer cuadro.
- **Lo que cambia en cada cuadro** (`nudos/video.py`, en `dibujar` y `_preparar_malla`, sin tocar la línea de tiempo de T21):
  - La malla de la trenza (`malla_trenza`, un anillo cada 0,04 d sobre la Catmull-Rom), con la velocidad de cada vértice: la de los nodos entre el cuadro anterior y el siguiente, si tienen la misma cantidad de nodos; si no, sin desenfoque en ese cuadro (hasta T21b).
  - El foco, en la punta de la cuerda, con el promedio de medio segundo para que no salte (`focos`).
  - La huella de cada cuadro lleva también el foco, la velocidad, el aspecto y el código de `render/blender/aspecto.py`, `video.py` y `nudos/trenza.py`.
- **`render/blender/video.py`:** arma la escena con las funciones de `render/blender/aspecto.py` (`entorno` y `materiales`) y, en cada cuadro, cambia la malla, la cámara y el foco; el desenfoque, con el modificador de Geometry Nodes, en todos los cuadros.
- **Al armar** (`_componer`): la viñeta y un grano de un píxel, distinto en cada cuadro (`posproceso_video`, unos 0,4 s por cuadro de 4K, en paralelo). `ARMADO` sube a «2».
- **Se quitó el modo video viejo** de `render/blender/escena.py`.
- **Los colores de la ficha pasan a la cuerda del video** (`ESTILO_VIDEO`): el azul, a la cuerda real; la crema de un nudo de dos cuerdas, a una cuerda clara con dos hilos rojos (`real-claro`). Hoy el video arma una sola cuerda por cuadro: el reparto entre dos cuerdas llega con T21b.
- **La prueba de 10 s:** `python -m nudos video <slug> --prueba` dibuja 10 s del medio del paso 4 en 4K, sin audio, en `<slug>-prueba-4k.mp4`. La escena, el foco y la huella de cada cuadro son los del video entero (`dibujar(..., solo=)`), así que el video entero vuelve a usar esos cuadros.
- **Un atasco, arreglado:** la primera prueba se trabó al 41 % mientras otro Blender (un `referencia`) llenaba la memoria de la tarjeta y la máquina estaba muy cargada: Python dejó de guardar los cuadros que Blender terminaba, y Blender se quedó esperando mallas. Ahora el renombre de cada cuadro reintenta (el antivirus puede tener abierto un PNG recién escrito) y, si igual falla, la orden lo dice al momento.
- **Armar sin la tubería:** al armar la prueba, Windows falló con «recursos insuficientes»: cada proceso devolvía 8 cuadros de 4K juntos (unos 200 MB) por la tubería. Ahora cada proceso escribe su cuadro compuesto a un archivo crudo y Python se lo pasa a ffmpeg en orden, con a lo más 2 cuadros por proceso esperando (`EN_VUELO`), así que el disco no se llena aunque ffmpeg vaya más lento.
- **El costo en el video, medido con la prueba:** 585 cuadros de 4K en unos 75 min, 7,7 s por cuadro en promedio, y unos 6 s en los tramos sin otras cosas corriendo en la máquina; T20a medía 4,6 s con la cámara quieta y sin desenfoque. Con 6 s, los 36 nudos (7200 cuadros de 4K y 3000 del reel cada uno) son unos 20 días; con 7,7 s, unos 25. Lo decide Gabriel antes de T19.
- **Las fichas no cambian:** `referencia` desde `main` (d358b3a) y con el código nuevo, y `comparar`. Los 36 `modelo.json`, iguales byte a byte; las imágenes de los 36 nudos con three.js, iguales (dos nudos salieron con unos píxeles en 1 o 2 niveles al imprimir dos corridas a la vez, e iguales al reimprimirlos); y las de Blender de los cuatro pilotos, iguales. El código de Blender que dibuja las fichas es el mismo para todos los nudos.

**Punto de control de T20b:** Gabriel aprobó la prueba de 10 s en 4K del as de guía (26 nov). Preguntó si la cuerda puede tener un largo fijo y solo cruzarse y moverse, en vez de encogerse o estirarse en cada paso: es el diseño de T21 (abajo), que espera su aprobación en el punto de control de T21a.

**T20c, las fichas (S, solo si se nota en papel).** La trenza nueva entra a las imágenes de impresión solo si la página de prueba impresa, en color y en gris, se ve mejor (la regla de T7b). Si no, las fichas no cambian. `referencia` y `comparar` muestran qué se movió.

**T20c no se hace:** Gabriel decidió que no hace falta (26 nov). Las fichas quedan como están, con la cuerda de siempre.

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

**El diseño (se cierra en el punto de control de T21a):**
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
     - Si no hay ninguna, queda en un arco levantado por fuera del nudo y fuera de la toma.
     - Un campo opcional del video (`video: {cola: …}`) la corrige donde la regla falle; las fichas lo ignoran.
   - **En una plantilla:** la pausa es la cuerda hasta el hito, más la cola en la mano, como hoy, y el resto va en la madeja.
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
- Si la madeja no convence a la vista, la cuerda sale del cuadro por la mano.

#### T22: El video completo

**T22a, el diseño (M), que Gabriel aprueba antes de programar.**
- **Los capítulos:**
  - **Apertura** (unos 6 s): el nudo terminado gira despacio, con el nombre y para qué sirve.
  - **Lo que necesitas** (3 s): los materiales, solo si la ficha los dice.
  - **Paso a paso:** el grueso del video. Cada paso lleva su tarjeta, su voz y su movimiento, y el paso 1 también se anima, desde la cuerda estirada.
  - **Cómo saber que quedó bien:** la verificación, con primeros planos y una marca en cada cosa que se revisa.
  - **Errores comunes:** el error con imagen, atado con el motor (T21e) y marcado con ✗, y después el correcto con ✓. Los demás errores van en tarjetas con voz.
  - **En la práctica:** la aplicación.
  - **Seguridad,** si la ficha la tiene.
  - **Cierre:** el nudo apretado con su golpe, el nombre y la dirección del visor.
- **Lo que sale de cada video:**
  - Capítulos para YouTube y subtítulos (`.srt`) de la voz.
  - El reel vertical (de 45 a 60 s), con su propia cámara y un guion corto: el nudo terminado como gancho, el título de cada paso dicho, un error, la aplicación y el cierre, con subtítulos quemados palabra por palabra.
  - En el visor, el capítulo del paso a paso, en 1080p y de 20 MB o menos.
  - Si Gabriel quiere, el nombre o el logo del grupo en el cierre.
- **La voz manda el tiempo.** Cada sección dura lo que su frase, y el movimiento se estira o se acorta un poco para cuadrar. Los cortes de capítulo caen en el pulso de la música.
- **El guion:**
  - Sale de la especificación: `usos`, el texto de cada paso, `verificacion`, `error`, `seguridad` y `precauciones`.
  - Un campo opcional `voz:` por paso, para cuando el texto escrito no suena bien dicho, y `aplicacion:` con la escena y su texto. Es la versión siguiente del formato.
  - Pasa por la misma comprobación de términos de sección que la ficha, y va en tuteo.
  - `python -m nudos guion <slug>` arma una hoja de revisión del guion, en HTML, con la duración estimada de cada parte.
  - **Lo que pidió Gabriel al oír su voz (27 nov):** que la narración suene natural, enganche y no «suene a hecha por IA». El texto de la ficha dicho tal cual suena a lista (en el amarre, «por encima del palo de arriba, por debajo del de abajo…»), y «Paso N de M» en todos los pasos suena monótono. Hay un borrador del guion hablado de los dos pilotos en `config/guion/<slug>.yaml` (`apertura`, un texto por paso, `cierre` y `seguridad`), con su prueba `python -m nudos prueba-guion`, que arma la narración entera con el texto de la ficha y con el guion. T22a decide si esos textos pasan a la especificación como su campo `voz:`.
  - **Cómo se escribe para la voz** (lo que siguió el borrador):
    - El anuncio del paso varía: «Primero», «Paso número dos de siete», «Ahora», «Paso cuatro», nada, «Último paso».
    - Frases cortas y largas mezcladas, en segunda persona y con conectores de quien enseña al lado: «ahora», «fíjate», «listo».
    - Una imagen en vez de una lista: el conejo que sale del pozo, rodea el árbol y vuelve (as de guía); rodear el cruce como si tejieras (amarre).
    - Un gancho en la apertura (una pregunta) y una prueba en el cierre («empuja un palo»).
    - Nada de muletillas de video de IA («en el video de hoy», «¡increíble!», «sin más preámbulos»).
    - Cada instrucción dice lo mismo que la ficha: los «por encima» y «por debajo» no cambian, y la seguridad conserva todo lo que dice la especificación.
    - El reconocimiento de voz revisa que cada locución diga su texto, sin contar las letras que suenan igual.
- **Las tarjetas nuevas,** primero como maqueta animada en HTML que Gabriel abre en el navegador:
  - El número grande en un distintivo de color, «Paso 4 de 7», el título y una barra de avance con un punto por paso.
  - Entran con un rebote suave y salen rápido, sobre un fondo esmerilado (el cuadro de atrás, desenfocado).
  - Tarjetas de capítulo, con ✓ y ✗ en verde y rojo, y formas y fondos animados de lygia.
  - Las dibuja Edge, cuadro por cuadro y con fondo transparente, y Pillow las pone sobre el video, como hoy.
- **La cámara:**
  - Una ruta continua con velocidad suave, sin tramos en línea recta ni paradas en seco.
  - Sigue el punto de acción con un poco de retraso, se acerca en cada cruce nuevo y enfoca donde está la mano.
  - Nunca se congela: en las pausas se desliza muy despacio.
  - Las ideas salen del catálogo de video-shotcraft (tomas, ritmo y entradas de tarjetas).
- **Las aplicaciones de los pilotos,** con texto propio y dentro de D1:
  - **El as de guía:** por ejemplo, una gaza alrededor de un árbol para tender el cabo de un toldo, o un balde izado.
  - **El amarre cuadrado:** una mesa de campamento o un portón. Aquí sí se suben personas.
  - **La eslinga de andamio:** una repisa colgante con ollas, como dicen sus `usos`.
  - **La utilería:** propia o CC0 (Poly Haven), con árboles de la extensión gratuita Sapling Tree Gen y el cielo de Blender.
  - **El nudo,** como en T21e: se coloca con un giro rígido (los anfitriones ya tienen la medida), y sus puntas se asientan hasta sus anclas con el motor.

**Punto de control:** Gabriel aprueba el diseño, el guion de un piloto y la maqueta de las tarjetas.

**T22b, la implementación (L).**
- `nudos/video.py` gana los capítulos, el guion, la cámara nueva, las tarjetas, los errores, la aplicación y el reel. Si crece demasiado, se parte en un paquete `nudos/video/`.
- **El disco:** un video de 2 min en 4K son unos 240 GB de cuadros. Por eso se arma por tramos: cada unos 10 s se codifican en un intermedio sin pérdida y los PNG se borran. `NUDOS_CUADROS` pasa a D:, que tiene 625 GB libres; C: tiene 164.
- **La previa entera** (960 × 540) de los tres pilotos, con voz, música y tarjetas. Punto de control.
- **Los tres pilotos en 4K y en vertical,** de noche. Punto de control.

#### T24: El visor

- **La trenza:** material físico con anisotropía y *sheen* (ya están en three.js 0.160) y un relieve más fino, con ruido de lygia.
- **La luz:** un entorno para los reflejos (RoomEnvironment) y el tonemap AgX, que también trae la 0.160.
- **El postprocesado:** oclusión ambiental (GTAOPass) y SMAA, solo si el equipo aguanta y con la vista quieta.
- **Lo que se copia:** esos complementos de three@0.160.0 y los archivos de lygia que se usen, con sus licencias, van a `sitio/vendor/`, y `sitio/vendor/LEEME.txt` los anota.
- **Opcional, después de T21:** la animación en 3D entre pasos dentro del visor, con los cuadros del motor comprimidos (unos MB por nudo), para girar el nudo mientras se ata. Cambia la lista de tipos del sitio (decisión 7), así que lo decide Gabriel.
- **`exportar()`,** que arma la escena de las fichas, no cambia, y `comparar` lo comprueba.
- **Punto de control:** Gabriel abre el visor en la computadora y en un celular de gama baja (el pendiente de T7b).

**Cómo se hizo T24 (26 nov):**
- **`sitio/fisico.js`,** un módulo nuevo que solo importa el visor (`visor.js`). `render/escena.js` gana unos ganchos (`fisico`) que, sin él, dejan todo como antes: la impresión sigue igual y `exportar()` no cambia. Con `?simple` en la dirección, el visor de antes, para comparar.
- **La trenza:** `MeshPhysicalMaterial` con pelusa (*sheen*, del tono medio de la cuerda), anisotropía con un mapa de la dirección de cada hilo y un relieve fino de fibras con el ruido simplex de lygia; el tramado de lygia, al dibujar directo.
- **La luz:** `RoomEnvironment` para los reflejos y AgX. Solo, el AgX de three.js aplanaba el azul (se veía gris): se le agregó un *look* de contraste y saturación (potencia 1,22 y saturación 1,3), como el «AgX - Base Contrast» de T20a, cambiando el código del tonemap al cargar `fisico.js`.
- **El postprocesado, solo con la cámara quieta:** `GTAOPass` con MSAA ×4. Se mide un cuadro (después del primero, que compila); si tarda más de 90 ms, o no hay WebGL 2, el visor sigue sin postprocesado. En la RTX 4070, unos 2 ms.
- **Sin SMAA:** dejaba un filo claro en el borde de la cuerda y de los palos, porque el fondo del visor es transparente. Por lo mismo, el `OutputPass` divide por el alfa antes del tonemap y vuelve a multiplicar después.
- **Lo copiado** a `sitio/vendor/` (con permiso de Gabriel; anotado en `LEEME.txt`): 13 complementos de three@0.160.0 (el paquete, comprobado contra el hash de npm; el `three.module.min.js` del sitio es idéntico al del paquete) y 7 archivos de lygia del commit aa7580b, como texto dentro de `lygia/lygia.js` (el sitio no publica `.glsl`), con `LICENCIA.txt`.
- **Pruebas:** `tests/test_visor.py`: cada módulo encuentra lo que importa, la impresión no carga el visor físico, lygia va con su licencia y el visor carga sin errores con y sin `?simple`.
- **Publicado** (27 nov, a pedido de Gabriel): el sitio, construido desde 23a88ae (`gh-pages` ac05c20). Como la carpeta de A: era de otra sesión, `scripts/publicar.sh` corrió desde un clon nuevo de GitHub en `main`, con el venv de A:. En línea, los visores del as de guía, el amarre cuadrado y la cabeza de turco cargan sin errores en la consola, con el postprocesado (de 2 a 8 ms por cuadro en la RTX 4070), y con `?simple`, sin él. Falta el punto de control en un celular de gama baja.

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
- **Antes, desde el pulido a fondo (26 nov):** la tabla de aplicaciones de los 36 nudos en texto, que Gabriel aprueba; sus escenas, armadas por familias (en poste, amarres, dos cuerdas…); los guiones revisados, y las voces y la música generadas. El render de los videos es de unas 2 semanas.
1. `referencia` de todos los nudos con el código de antes de la fase, para comparar.
2. Todos los nudos construidos con el motor, a la vez y con todos los núcleos (`nudos/procesos.py`), de noche si hace falta.
3. `comparar` dice qué cambió en cada nudo. Donde la secuencia de algún paso no es la declarada, el paso se corrige (ver «La secuencia declarada sigue mandando» en T15) y se vuelve a correr.
4. Las fichas y los videos de todos, y una página de prueba con todas las fichas, en color y en gris.
5. `relajar()` y `apretar()` se borran: ya ningún nudo los usa.
6. Se publica el sitio, con la misma dirección para cada nudo.

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
