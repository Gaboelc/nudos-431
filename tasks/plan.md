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

#### T17: Animación entre pasos

**Descripción:** calcular el movimiento continuo de la cuerda de un paso al siguiente con el modo «atar» del motor (T15). Una mano lleva el chicote por un camino que sigue, con un margen, la cuerda del paso siguiente, desde su punta, como al pasarla por un lazo. El resto de la cuerda se mueve con la dinámica, el peso y el roce, y al final se asienta en la pose de la ficha. Como el motor nunca deja que la cuerda se atraviese, tampoco entre dos cuadros, la animación hereda esa garantía.
- En una plantilla, cada paso es un comienzo más largo de la misma cuerda: la mano lleva el chicote por el camino final (como el video de `poc/blender`), pero ahora la cuerda que ya está se aprieta con cada vuelta nueva.
- En un nudo libre, la cola cambia de forma entre pasos: la mano la lleva por fuera de todo y la hace entrar por donde dice el paso.

Lo que mostró T14b:
- **En un nudo libre, la mano tiene que planear por encima y por debajo.** Llevar la cuerda al paso siguiente con resortes, sin atravesarse, deja el chicote encima del tramo por el que debía pasar por debajo, y el cruce sale al revés. La mano tiene que levantar el tramo o meter el chicote por debajo, a una altura que sale de la secuencia declarada del paso siguiente.
- **En una plantilla, avanzar la mano por el camino y asentar cada cuadro funciona** (el video del amarre de T14b), con la tensión de atado de T14a.
- **La cámara va por tramos:** desde una sola vista, el ballestrinque inicial del amarre queda detrás del palo. Y el video necesita una pausa al final de cada paso: el amarre en 9 s va demasiado rápido.

El diseño de los caminos de la mano va como bloque de este plan, con un nudo libre (el as de guía) y una plantilla (el amarre cuadrado) de piloto.

**Criterios de aceptación:**
- [ ] Ningún cuadro tiene una cuerda atravesando otra (la CCD del motor), y la pose final de cada paso es la de la ficha, con su secuencia declarada.
- [ ] Gabriel aprueba la prueba de 10 segundos en movimiento del as de guía y del amarre (la puerta del método de elasthic).

**Dependencias:** T15 (al menos T15d). **Tamaño:** L. Es la tarea de más riesgo de la fase.

#### T18: Videos

**Descripción:** un video por nudo, renderizado en Blender y armado con ffmpeg, con el título de cada paso en pantalla (el texto propio de la especificación, en tuteo y sin términos de sección).
- **El formato (Gabriel, 24 nov): lo mejor que acepta cada plataforma.**
  - **Horizontal, para YouTube:** 3840 × 2160 a 60 cuadros por segundo y 68 Mbps, el tope de lo que YouTube recomienda para 4K a 60 fps en SDR (de 53 a 68 Mbps). H.264 en `.mp4` con el índice al principio (`-movflags +faststart`), color 4:2:0, tasa variable y la misma tasa de cuadros de punta a punta.
  - **Vertical, para los reels de Instagram:** 1080 × 1920 a 60 fps, con una tasa alta (unos 20 Mbps) para que la recompresión de Instagram pierda poco. Instagram muestra los reels a 1080 × 1920 y baja a eso lo que se sube en 4K, así que renderizarlo en 4K costaría cuatro veces más sin que se vea.
  - **En el visor:** una copia del horizontal en 1920 × 1080 a 60 fps y unos 8 Mbps, sacada del original en 4K con ffmpeg (unos 30 MB por cada 30 s). El original no cabe: 30 s a 68 Mbps son unos 255 MB, y GitHub no acepta archivos de más de 100 MB.
- **En el visor:** horizontal, en la página del QR. El sitio hoy no acepta imágenes ni video, así que la lista de tipos de la decisión de arquitectura 7 gana `.mp4`, con un tope de tamaño. El video vive dentro del sitio, sin YouTube, para que el visor no dependa de servicios externos.
- **En redes:** el horizontal en YouTube y el vertical en Instagram. Dónde y cuándo se publica lo decide Gabriel.

**Criterios de aceptación:**
- [ ] `python -m nudos video <slug>` arma los dos formatos.
- [ ] El visor del as de guía muestra su video, y la URL del QR no cambia.
- [ ] Gabriel aprueba los videos de los pilotos; los de los demás nudos se arman en T19.

**Dependencias:** T17. **Tamaño:** M, más el tiempo de render. T14b midió unos 7 s por cuadro a 1280 × 720 con 64 muestras, a 30 fps: los 36 nudos en dos formatos, de 30 a 50 horas. Con el formato de arriba, si el tiempo crece con los píxeles y los cuadros, el horizontal cuesta 18 veces eso (9 veces los píxeles y el doble de cuadros) y el vertical, 4,5 veces: de 340 a 560 horas, de dos a tres semanas de render seguido. T16 mide el tiempo real por cuadro en 4K y busca bajarlo (la GPU, menos muestras con el denoiser) antes de comprometer los 36 videos. El vertical se renderiza con su propia cámara: recortar el horizontal corta el nudo.

#### T19: Todos los nudos a la vez

**Descripción:** con todo implementado y probado en los pilotos, una sola corrida calcula todos los nudos con el motor, dibuja todas sus fichas en Blender y arma todos sus videos. No hay tandas (Gabriel, 23 nov).
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

**Dependencias:** T15 a T18. **Tamaño:** L, casi todo tiempo de cálculo y de render.

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

## Preguntas abiertas

- **D3 y D8:** las decisiones previas que siguen abiertas.
- **D7:** si la dirigencia de la Tropa participa en la revisión de su anexo y en conseguir probadores.

## Lo que se reutilizó del prototipo

El prototipo del as de guía se portó completo y la carpeta `prototipo/` se borró al cerrar T3. Sigue en el historial de git:

- **`knot.py`:** el generador libre (trazado, cruces, elevación a 3D, relajación y validación). Pasó a `nudos/` en T1.
- **`render.py`:** el render de verificación en numpy. Pasó a `nudos/hoja.py` en T1.
- **`viewer.template.html` y `build_viewer.py`:** la escena three.js y el visor. Pasaron a `render/escena.js` y `sitio/` en T2.
- **`shoot.py`:** el render con Chrome sin interfaz. Pasó a `nudos/imprimir.py` en T3.
