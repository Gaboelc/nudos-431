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
- **Formatos:** el impreso por ediciones es el principal. El digital es el PDF más un visor 3D por nudo, enlazado con QR desde la ficha. Desde el 23 de noviembre de 2026, cada nudo tendrá también un video de cómo atarlo, en su visor y en redes (fase 6).
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
- **D10 Render en Blender:** si las imágenes de las fichas pasan de three.js con Edge a Blender, y si Gabriel compra Studio in a Folder. Se decide con la página de prueba de T14 (fase 6). Si sale a favor, reemplaza la decisión de arquitectura 5 en lo que toca a la impresión; el visor sigue en three.js.
- **D11 Pila del motor de física:** con qué bibliotecas se arma el motor de T15 (`ipctk` con `numba`, NVIDIA Warp o código propio). Se decide en T15a, con la prueba de velocidad, de que repita el resultado y de que nunca se atraviese.

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

**Lo pendiente de la fase 4.**
- **La tanda 5, anfitriones especiales:** la eslinga de barril, la eslinga de andamio (requiere D1) y la vuelta de cornamusa, sobre una cornamusa. Su propuesta está abajo; Gabriel la aprobó el 23 nov. Los tres anfitriones están hechos y aprobados, en la rama `claude/tanda-5-propuesta-7431fd`; faltan los tres borradores.
- **T8, la cabeza de turco,** al final del plan: ver qué no se entiende en las imágenes antes de tocar la geometría (ver T8 en el historial).

**Propuesta de la tanda 5: anfitriones especiales (23 nov; Gabriel la aprobó el mismo día, con las respuestas que están al final).** Son tres nudos, y cada uno necesita un anfitrión nuevo: el barril, el tablón y la cornamusa. Ninguno necesita plantilla: los tres se dibujan con segmentos, como el ballestrinque sobre el poste, y su borrador lo escribe la skill `nudo-nuevo` cuando su anfitrión esté en `main`. Cada anfitrión es una tarea de código con la forma de T5 y del destorcedor: Gabriel aprueba su diseño, se programa, se comprueba con `referencia` y `comparar` que los 32 nudos hechos no cambian, y después se dibuja el nudo. Las medidas van en diámetros de cuerda y se ajustan al dibujar, como el radio del destorcedor.

Lo común a los tres:
- **La cuerda va pegada al sólido, no solo sobre la mesa.** El poste ya lo resuelve para un cilindro acostado: puntos `[x, ángulo]` que se densifican sobre su superficie, relajación sin gravedad a menos de 2,5 diámetros de él, cruces en su superficie desenrollada y el apretado con la penetración en cada ronda. El tablón es ese mismo camino con otro perfil, y la cornamusa y el barril lo reusan con otra forma. Por eso el primero que se programe separa del poste lo que depende de la forma (`punto`, la superficie desenrollada, `empujar` y `penetracion`) de lo que no (densificar, elevar en los cruces, relajar y comprobar), y los otros dos se apoyan en eso. Los nudos del poste tienen que quedar iguales byte a byte.
- **Los cantos se redondean.** En un canto vivo, la cuerda se dobla con radio 0,5 y el mínimo es 0,9. Los cantos del tablón y los bordes de la tapa y de la base del barril llevan un radio de 0,6, fijo en el código: la cuerda que los rodea se dobla con radio 1,1.
- **El as de guía de las eslingas no se dibuja.** Las dos eslingas terminan uniendo los extremos con un as de guía, por encima de la carga, para colgarla. Ese nudo va en el aire, y la escena no puede sostener cuerda en el aire. Pasa lo mismo que con el pescador doble que cierra el prusik: el último paso lo nombra en el texto y remite a su ficha, y los extremos quedan sobre la mesa, saliendo del encuadre.
- **Por detrás, cada anfitrión sigue a uno que ya existe:** el barril y la cornamusa, que no se voltean, se miran desde el otro lado, como el poste; el tablón se voltea como los palos.

**Eslinga de barril.** La entrada son 13 fotos de Animated Knots (*barrel hitch*: R1 a R8 son el primer método, y R9 a R13, el segundo) y la página 25 del manual de la Tropa. Las dos fuentes atan lo mismo:
- El barril se para sobre la cuerda, y los dos extremos suben por los costados y se cruzan sobre la tapa en un medio nudo.
- El medio nudo se abre, y sus dos asas bajan por el borde hasta abrazar el barril cerca de arriba.
- Los extremos se unen con un as de guía, y el barril se levanta.

Sobre el nombre: lo que Animated Knots llama *barrel sling* es otro nudo (el barril acostado, con una presilla de alondra; ABOK 2163), y la entrada no tiene fotos suyas. El del manual es el *barrel hitch* (ABOK 2176), y es el que se propone.
- **El anfitrión:** `anfitrion: {tipo: barril, radio: 6, alto: 10}`. Es un cilindro de eje vertical en x = y = 0, como el destorcedor y la estaca, pero aquí la cuerda le pasa por debajo, por el costado y por encima. Ninguno de los anfitriones que hay sirve: `Parado` empuja la cuerda solo hacia los lados, porque con él nunca pasa por encima.
  - Se apoya sobre la cuerda que pasa por debajo, así que su base queda a la altura 1, como el poste.
  - `radio` va de 3 a 12, y `alto` es de 4 o más. Con 6 y 10, y una cuerda de 8 mm, es una lata de 10 cm de ancho: más chica que un barril, pero con uno de verdad la cuerda se vería como un hilo en la ficha. El texto dice «un barril, un balde o una lata».
- **Los segmentos** son de tres clases:
  - Sobre la mesa, `[x, y]`, como siempre, también bajo el barril.
  - Sobre el costado, `{barril: [[ángulo, altura], ...]}`. El ángulo se mide alrededor del eje vertical: 0 hacia quien ata, 90 a la derecha, 180 al fondo y 270 a la izquierda. Como en el poste, no vuelve a 0, así que el sentido de cada vuelta queda escrito en los números. La altura se mide desde la mesa.
  - Sobre la tapa, `{tapa: [[x, y], ...]}`.
  - Se densifican sobre la superficie, como en el poste, y al pasar de una cara a otra la cuerda rodea el canto redondeado.
- **Cómo se construye:** por el camino del poste. Cerca del barril va sin gravedad (si no, el anillo resbalaría hasta la mesa), y con gravedad en los extremos que van sobre la mesa. Lo que entra en el barril sale por la cara más cercana: el costado, la tapa o la base. La medida es `penetracion_barril`, con el máximo de siempre, 0,05.
- **Los cruces** se buscan en tres zonas: el costado, en su superficie desenrollada (el arco alrededor del eje y la altura), donde encima es lo más lejos del eje, y la tapa y la mesa, desde arriba. Entre una zona y otra no se buscan, así que ningún cruce va justo en un canto.
- **Los pasos** son tres:
  1. «Pon el barril sobre la cuerda»: la cuerda va a lo largo de x por debajo del centro de la base, con los extremos hacia los lados. No tiene cruces.
  2. «Cruza los extremos sobre la tapa»: los extremos suben por los costados izquierdo y derecho y se cruzan sobre la tapa en un medio nudo flojo, con sus dos cruces cerca del borde, como en el primer dibujo del manual. Son los cruces 1 y 2: en uno, el extremo izquierdo va por encima, y en el otro, por debajo.
  3. «Baja las asas por el borde»: las dos asas bajan por el borde y abrazan el costado, a un diámetro y medio de la tapa. Los cruces quedan en el costado, a la izquierda y a la derecha, donde el extremo que sube se engancha con el asa que llega. Son los mismos dos cruces, pero bajan más de 2,5 diámetros, así que llevan etiquetas nuevas, 3 y 4, como los que se mueven en el paso de tirar del refuerzo de cabo. El texto termina: une los extremos con un as de guía por encima del barril y levanta despacio.
- **Los nombres:** «Firme» en el extremo izquierdo y «Chicote» en el derecho. Los dos extremos trabajan igual y al final los dos cargan. Se proponen así para no tocar el formato: con `dos_firmes`, los dos dirían «Firme».
- **El error común** (`invierte: [3]`, en el paso 3) es «Las asas sin enganchar». Con un cruce al revés, los extremos no se enganchan: solo se apoyan uno sobre otro. Al levantar, el anillo se abre y el barril se cae. En `otros` van dos: el anillo muy abajo (por debajo del centro, el barril se voltea) o muy arriba (se sale por el borde), y la cuerda que no pasa por el centro de la base.
- **Encuadre y terminado:** los pasos se miran a 40°, como siempre, y el encuadre abarca el barril y unos 8 diámetros de cuerda a cada lado. Un barril parado no se voltea: el nudo terminado se aprieta como sobre el poste y se mira por delante y desde el otro lado («Por detrás es como lo ves desde el otro lado del barril»). Los enganches quedan en los costados, de perfil. Si no se leen bien, se gira todo el nudo unos 30° en la especificación, sin tocar el código.
- **Escena y hoja:** de madera, como la estaca. La hoja de revisión lo dibuja color madera, con el costado desenrollado, como el tubo.
- **Seguridad (D1):** la eslinga levanta objetos, no personas. En `precauciones`: nadie se pone debajo de la carga, y se levanta despacio y parejo. No lleva `seguridad`.
- **El formato** suma el tipo `barril` y los segmentos `{barril: …}` y `{tapa: …}`. Es un cambio compatible, y su versión depende de cuándo entre (ver «El orden y las sesiones», abajo).

**Eslinga de andamio.** La entrada es una sola imagen con cuatro dibujos, su `info.txt` y la página 25 del manual de la Tropa. Los «usos comunes» del `info.txt` son de otro nudo (un mosquetón, un anzuelo) y no se usan. Las dos fuentes atan lo mismo:
- Se dan dos vueltas y media al tablón, de modo que la cuerda pasa tres veces por la cara de arriba: la 1, la 2 y la 3, desde el firme hacia la punta del tablón.
- La 1 pasa por encima de la 2 y queda entre la 2 y la 3.
- La 2 pasa por encima de la 1 y de la 3, por la punta del tablón y por debajo de él.
- Se tira de los dos extremos, que suben uno por delante y otro por detrás del tablón y se unen arriba con un as de guía.

Para colgar un tablón se ata una eslinga en cada punta.
- **El anfitrión:** `anfitrion: {tipo: tablon, ancho: 12, grueso: 3, largo: 30}`. Es una tabla acostada a lo largo de x, con los cantos redondeados. La punta está en x = 0, a la derecha, hacia donde avanzan las vueltas, y el resto sigue hacia x negativo hasta `-largo`, como el cabo.
  - Va centrada en y = 0. Se apoya sobre la cuerda que pasa por debajo, así que su cara de abajo queda a la altura 1, como el poste.
  - `ancho` y `grueso` son de 2 o más. Con una cuerda de 8 mm es una tabla de 10 × 2,4 cm.
  - Reusa el poste: es el mismo camino con otro perfil. Los segmentos sobre el tablón se escriben `{tablon: [[x, ángulo], ...]}`, como en el poste: 0 arriba, 90 hacia quien ata, 180 abajo y 270 atrás, sin volver a 0. El ángulo se reparte parejo a lo largo del contorno, así que 0, 90, 180 y 270 caen en el medio de cada cara.
- **Construcción y cruces:** como en el poste. La medida es `penetracion_tablon`. Los cruces se buscan en la superficie desenrollada (x y el largo a lo largo del contorno), donde encima es lo más lejos de la superficie del tablón, no del eje. Los de la mesa se buscan desde arriba.
- **Los pasos** son cuatro:
  1. «Da dos vueltas y media al tablón»: el firme llega por delante, sobre la mesa, y sube por la cara de delante. Las tres pasadas por arriba van a unos 2,5 diámetros una de otra, cerca de la punta, y el chicote cae por detrás. No tiene cruces: las vueltas van una junto a otra.
  2. «Pasa la 1 por encima de la 2»: la 1 sube sobre la 2 y queda entre la 2 y la 3. Tiene el cruce 1, arriba, con la 1 sobre la 2, y probablemente el 2, debajo del tablón, donde se cruzan los tramos de abajo de la 1 y la 2. El borrador los cuenta.
  3. «Pasa la 2 por encima de la 1 y de la 3»: el seno de la 2 sale hacia la punta, por encima de la 1 y la 3, y queda sobre la mesa, más allá de la punta del tablón, como en el tercer dibujo de la entrada. Son los cruces 3 a 6: cada rama del seno pasa sobre la 1 y sobre la 3.
  4. «Mete el seno por debajo y tira de los extremos»: el seno da la vuelta a la punta y queda debajo del tablón, abrazando la 1 y la 3. Sus cruces bajan de la cara de arriba a la de abajo, más de 2,5 diámetros, así que llevan etiquetas nuevas, de la 7 a la 10, como en el barril. El texto termina: une los extremos con un as de guía por encima del tablón, y ata otra eslinga igual en la otra punta.
- **Los nombres:** «Firme» en el extremo de delante y «Chicote» en el de detrás.
- **El error común** (`invierte: [3, 4, 5, 6]`, en el paso 3) es «La 2 por debajo»: el seno pasa por debajo de la 1 y la 3, no las aprieta, y el tablón resbala o se voltea. Se ve desde arriba, porque en ese paso el seno todavía va sobre la cara de arriba. En `otros` van dos: las vueltas muy separadas o lejos de la punta, y colgar el tablón de una sola eslinga.
- **Encuadre y terminado:** el encuadre abarca la punta del tablón y unos 12 diámetros hacia dentro. El nudo terminado se aprieta como sobre el poste y se voltea con el tablón como la página de un libro, como sobre los palos: es un giro rígido, así que la secuencia no cambia. Por detrás se ve la cara de abajo, la que en los pasos queda contra la mesa, donde el seno abraza las vueltas. La ficha dice: «Por detrás es como lo ves si volteas el tablón como la página de un libro».
- **Escena y hoja:** de madera. Se corta en el encuadre, como el cabo, y la hoja lo dibuja color madera.
- **Seguridad (D1):** D1 dice que la eslinga de andamio se practica sin carga o con un objeto. La ficha lleva `seguridad`: en las actividades del grupo no sostiene personas, ni como andamio ni como columpio. Sirve para colgar un tablón como repisa o para subir materiales. Los andamios colgantes de trabajo los arma gente capacitada, con equipo certificado. El manual de la Tropa dice que sirve para subir «hasta personas»: eso no va en la ficha ni en el anexo.
- **El formato** suma el tipo `tablon` y los segmentos `{tablon: …}`.

**Vuelta de cornamusa.** La entrada son 9 fotos (R1 a R9), una vuelta sobre una cornamusa de driza, y su `info.txt`:
- El firme llega a lo largo de la cornamusa y pasa por debajo del cuerno lejano.
- Da la vuelta al pie por debajo del otro cuerno.
- Cruza por encima en diagonal hacia el cuerno lejano y pasa por debajo de él.
- Vuelve en otra diagonal, que cruza a la primera: es el ocho.
- Termina con un cote: una gaza torcida que se engancha en el cuerno cercano, con el chicote por debajo.

El `info.txt` dice que se suelen dar más diagonales que una y que lo esencial es poder soltarla rápido.
- **El anfitrión:** `anfitrion: {tipo: cornamusa, largo: 16, radio: 1}`. Va fija a la mesa, a lo largo de x y centrada en x = y = 0. Con una cuerda de 10 mm es una cornamusa de 16 cm.
  - Los cuernos son una barra de radio `radio`, con las puntas redondeadas. Su eje queda a la altura 1,6 + `radio`, así que bajo cada cuerno queda un hueco de 1,6 diámetros por donde pasa la cuerda.
  - El pie es un bloque en el medio, de 5 diámetros de largo (fijo en el código) y del ancho de la barra, que va de la mesa a la barra. Por ahí no pasa la cuerda.
  - Reusa del poste la forma de escribir lo que pasa sobre la barra, y del destorcedor, la de buscar los cruces desde arriba.
- **Los segmentos:** lo que va bajo los cuernos y alrededor del pie va sobre la mesa, `[x, y]`, y lo que pasa por encima de la barra, `{cornamusa: [[x, ángulo], ...]}`, como en el poste, con el ángulo solo por arriba, entre 90 y −90. Un punto de la mesa bajo el pie es un error al cargar.
- **Construcción:** por el camino del poste, sin gravedad cerca de la cornamusa. Lo que entra en la barra o en el pie sale por la cara más cercana. La medida es `penetracion_cornamusa`.
- **Los cruces se buscan todos desde arriba,** como sobre la mesa: la cornamusa es baja, y donde un tramo pasa sobre un cuerno y otro por debajo de él, hay un cruce de verdad, con encima el de arriba. Es el primer nudo sobre un anfitrión con cruces entre un tramo sobre el anfitrión y uno sobre la mesa, que está en «Lo que se agregará». Donde la cuerda baja casi vertical por el costado de la barra, dos pasadas a menos de 3 diámetros a lo largo de la cuerda no cuentan como cruce, como en el tubo. Si desde arriba no alcanza, lo que va sobre la barra se busca en su superficie desenrollada, como en el poste, y se ve con Gabriel.
- **La orientación:** en las fotos, la cornamusa está a lo largo de y y la driza baja desde el fondo. Así, el cuerno de delante taparía el hueco del de atrás. Se propone ponerla a lo largo de x, con el firme desde la izquierda, por delante de ella, como una driza que baja paralela; el cuerno lejano es el derecho.
- **Los pasos** son cinco. El borrador cuenta los cruces con las fotos: son unos diez.
  1. «Pasa la cuerda por debajo del cuerno lejano»: el firme pasa bajo el cuerno derecho, de delante hacia atrás. No tiene cruces.
  2. «Rodea el pie por debajo del otro cuerno»: la cuerda va por detrás hasta el cuerno izquierdo, pasa por debajo de él hacia delante y cruza sobre el firme (cruce 1).
  3. «Cruza por encima hacia el cuerno lejano»: va en diagonal por encima de la barra, desde delante a la izquierda hasta detrás a la derecha, y pasa bajo el cuerno derecho, más cerca de la punta que la primera vez. Cruza sobre el tramo de detrás.
  4. «Vuelve a cruzar por encima»: va en diagonal hacia el cuerno izquierdo, cruza sobre la primera diagonal en el medio de la barra y pasa bajo el cuerno izquierdo.
  5. «Engancha un cote en el cuerno»: tuerce una gaza de modo que el chicote quede por debajo y engánchala en el cuerno izquierdo. La gaza pasa sobre el cuerno, encima de lo que va debajo de él.
- **Los nombres:** «Firme» en el que viene de la carga (la driza o el cabo del bote) y «Chicote» en el que queda suelto.
- **El error común** (`invierte`, los cruces del cote, en el paso 5) es «El cote al revés»: si la gaza se tuerce hacia el otro lado, el chicote queda encima, no se traba y la vuelta se suelta. En `otros` van dos: empezar por el cuerno cercano, y llenarla de cotes o de vueltas, que se atasca y no se suelta rápido.
- **Encuadre y terminado:** el encuadre abarca la cornamusa y unos 6 diámetros alrededor. El nudo terminado se aprieta y se mira como sobre el poste: por delante y desde el otro lado («Por detrás es como lo ves desde el otro lado de la cornamusa»).
- **Escena y hoja:** de metal gris, como el destorcedor.
- **Seguridad:** D1 no aplica. En `precauciones`: con carga, los dedos no van entre la cuerda y la cornamusa.
- **El formato** suma el tipo `cornamusa` y los segmentos `{cornamusa: …}`.

**El orden y las sesiones.** Se propone una sola sesión para los tres anfitriones, uno detrás de otro, y no tres en paralelo:
- **Los tres tocan el mismo código, no solo las mismas listas.** Los tres extienden el camino del poste (`construir_paso`, `_curva` y `_cruces` de `nudos/anfitrion.py`, la relajación y el apretado). En la tanda 4, los palos y el cabo se programaron en paralelo y al integrar chocaron solo en listas (los anfitriones, la escena, la hoja, el formato), porque cada uno tenía su propio camino. Aquí, tres sesiones separarían del poste lo que depende de la forma tres veces y de tres maneras, y al integrar habría que rehacer el diseño, no juntar listas.
- **Cada cambio al camino del poste toca los nudos ya hechos sobre él,** como el ballestrinque. Con una sesión, se comprueba con `referencia` y `comparar` una vez por anfitrión, sobre lo mismo.
- **El paralelo casi no acorta la tanda:** lo que marca el ritmo es el filtro 1, que Gabriel hace de a un nudo, y una sesión que ya tiene el poste en contexto hace el segundo y el tercer anfitrión más rápido.

El orden: primero el tablón, que es el poste con otro perfil (ahí se separa lo que depende de la forma); después la cornamusa, que reusa la barra del poste y busca los cruces desde arriba, y al final el barril, el más distinto, con su eje vertical y su tapa. Cada anfitrión sube el formato una versión: el tablón, la v1.11; la cornamusa, la v1.12, y el barril, la v1.13. La v1.10 es `dos_firmes` por cuerda, para el prusik. La sesión de código va con el modelo grande y el esfuerzo de siempre, y se detiene después de cada anfitrión para que Gabriel lo vea. El borrador de cada nudo puede ir en una sesión aparte, con esfuerzo medio, apenas su anfitrión entra a `main`: solo toca su especificación, así que no choca con el código del siguiente.

**Preguntas para Gabriel:**
1. **Barril, el método:** ¿el del manual, con el medio nudo abierto sobre la tapa, o el segundo de Animated Knots, con el medio nudo tendido en el suelo y el barril encima? Se propone el del manual.
2. **Barril, el nombre:** ¿va «Eslinga de barril», como en el manual, con el ABOK 2176 del *barrel hitch*? El *barrel sling* de Animated Knots es otro nudo.
3. **Las dos eslingas, el as de guía:** ¿está bien que no se dibuje y que el último paso remita a su ficha?
4. **Las dos eslingas, los nombres:** ¿«Firme» y «Chicote», o los dos extremos como firmes?
5. **Andamio, la cara de abajo:** la entrada no muestra cómo queda el seno 2 bajo el tablón, y de eso dependen el paso 4 y el terminado por detrás. ¿Puedes atarla en una tabla y dejar en `entradas/eslinga-de-andamio/` unas fotos de arriba y de abajo?
6. **Andamio, D1:** ¿confirmas que la ficha dice que no se usa ni como andamio ni como columpio para personas, y que se practica sin carga o con un objeto?
7. **Cornamusa:** ¿a lo largo de x, con el firme desde la izquierda, y con dos diagonales antes del cote, como en las fotos?
8. **Sesiones:** ¿una sola sesión de código para los tres anfitriones, en el orden de arriba?

**Las respuestas de Gabriel (23 nov):**
- Las preguntas 1, 2, 3, 6, 7 y 8 van como se recomienda: el método del manual, «Eslinga de barril» con el ABOK 2176, el as de guía sin dibujar, la seguridad del andamio tal como está, la cornamusa a lo largo de x con dos diagonales antes del cote, y una sola sesión de código, empezando por el tablón.
- Pregunta 4: las dos eslingas llevan «Firme» y «Chicote».
- Pregunta 5: no habrá fotos de la eslinga de andamio. La sesión deduce la cara de abajo del tablón, y Gabriel la revisa en la hoja y en el filtro 1.
- La v1.10 del formato ya es `dos_firmes` por cuerda, para el prusik, así que los anfitriones son la v1.11 (el tablón), la v1.12 (la cornamusa) y la v1.13 (el barril).

**Cómo se hizo el tablón (23 nov; falta que Gabriel lo vea).** Está como en la propuesta, en la rama `claude/tanda-5-propuesta-7431fd`, salvo lo que sigue.
- **El camino del poste no se partió en dos:** bastó con que el tablón (`Tablon`, en `nudos/anfitrion.py`) tenga la misma cara que el poste. Su `rb` es el radio de un círculo del mismo perímetro que el contorno que sigue el eje de una cuerda que lo toca, y `cilindricas` da como «distancia al eje» rb más lo que el punto se aleja de ese contorno. Con eso, `_curva`, `_cruces`, `construir_paso` y `apretar_paso` sirven igual, sin cambiar: solo eligen el sólido con `sobre_superficie`. La cornamusa y el barril no podrán hacer lo mismo del todo (la cornamusa busca los cruces desde arriba y el barril tiene tres zonas), así que lo que dependa de la forma se separa cuando llegue su turno.
- **El sólido:** empuja y mide la penetración en 3D, con los cantos redondeados también en la punta. `Anfitrion` lleva ahora `ancho` y `grueso`, y `radio` es opcional, porque el tablón no lo tiene. Los segmentos sobre él se escriben `{tablon: …}` (`CLAVE_SOBRE`, en `nudos/spec.py`).
- **Por detrás** se voltea el nudo apretado con el tablón, como los palos (`Tablon.voltear`). La hoja de revisión lo dibuja además en `revision`, porque ahí es donde Gabriel revisa la cara de abajo de la eslinga.
- **El nudo de prueba** (`tests/test_tablon.py`) es el ballestrinque de `specs/` sobre un listón de 4 × 2,4, corrido 8 diámetros hacia dentro: los mismos segmentos, con `{tablon: …}`. Construye sin fallas. Con un listón de 4 × 2, el error común quedaba en el límite de separación (0,97).
- **Los nudos hechos no cambian.** La referencia se armó desde `main` (9898f79) en un worktree aparte. Los 32 `modelo.json` son iguales byte a byte. Tres nudos (el pescador, el pescador doble y el prusik) diferían en 1 nivel en 1 a 12 píxeles, también con `--reimprimir`. Impresos otra vez desde 9898f79, salen iguales a la rama, así que la variación era de la primera corrida de referencia.
- **Pasan 658 pruebas y 1 se salta** (`tests/test_tablon.py` es nueva).
- **Gabriel, al ver las imágenes (23 nov): «el tablón se confunde con un poste».** Las imágenes eran las del ballestrinque sobre el listón angosto, y los cantos iban redondeados con radio 0,6. Pidió quitarlos. Vivos del todo no pueden ir: la cuerda que pasa por un canto vivo se dobla con radio 0,5, y el mínimo es 0,9. `CANTO` bajó a 0,45, lo menos que se puede con algo de holgura (la cuerda se dobla con 0,95), y la escena dibuja las testas más oscuras, como madera cortada a través de la veta. Para verlo con las medidas de la propuesta, `tests/test_tablon.py` lleva otro nudo de prueba: las dos vueltas y media del primer paso de la eslinga sobre un tablón de 12 × 3, sin fallas.
- **Gabriel aprobó el tablón el 23 nov** y pidió seguir con la cornamusa. El borrador de la eslinga de andamio puede ir en su sesión apenas el tablón esté en `main`.

**Cómo se hizo la cornamusa (23 nov; falta que Gabriel la vea).** En la misma rama, como en la propuesta, salvo lo que sigue.
- **La barra se apoya en la cuerda, como el poste.** La propuesta dejaba bajo cada cuerno un hueco de 1,6 diámetros. Así, la cuerda que baja de la barra para pasar bajo un cuerno se doblaba con radio 0,13, porque tenía que bajar y meterse debajo en muy poco espacio. Con el hueco de una cuerda (`HUECO_CORNAMUSA` = 1, en `nudos/spec.py`), el eje de la barra queda a `radio + 1`, como el del poste. Entonces la cuerda puede rodear un cuerno como a un poste: `{cornamusa: [[x, ángulo], ...]}` vale para cualquier ángulo, no solo por encima de la barra. Solo no puede rodearla por debajo donde está el pie, ni pasar por el pie sobre la mesa: los dos son errores al cargar.
- **El sólido** (`Cornamusa`, en `nudos/anfitrion.py`) tiene el `punto` del poste y una `cilindricas` que mide la distancia a la barra con sus puntas redondas. Así, más allá de un cuerno hay gravedad: con la del poste, que es un cilindro infinito, la cuerda que daba la vuelta junto a la punta quedaba sin gravedad y se arrugaba. Empuja fuera de la barra y del pie, que visto desde arriba tiene las puntas redondas.
- **Los cruces se buscan desde arriba** (`Cornamusa.cruces`), sin contar dos pasadas a menos de 3 diámetros a lo largo de la cuerda. `construir_paso` y `apretar_paso` los piden con `_buscar`, que para el poste y el tablón sigue usando `_cruces`. Al construir no se eleva un cruce cuyas dos pasadas ya están separadas en altura, como una sobre un cuerno y otra por debajo (`Cornamusa.separados`). Esto vale solo para la cornamusa.
- **Al dibujar:** la cuerda que sube de la mesa a la barra necesita llegar con espacio, unos 2,5 diámetros. Al bajar, tiene que salir por debajo del cuerno, no por su frente: rodeando el frente, la relajación la dejaba caer a la mesa y el sobrante se arrugaba. Está en el formato, para el borrador.
- **El nudo de prueba** (`tests/test_cornamusa.py`) no es del libro: el firme sube a la barra y la cruza en diagonal, rodea el cuerno derecho por debajo y, en el paso 2, vuelve por delante y pasa bajo el cuerno izquierdo, por debajo de la diagonal. Construye sin fallas. Sus imágenes están en `revision/cornamusa/`, fuera de git.
- **Los nudos hechos no cambian:** los 32 `modelo.json` son iguales byte a byte a la referencia de 9898f79. Seis nudos diferían en 1 o 2 niveles en 1 a 12 píxeles al imprimir los 32 juntos. Reimpresos, o impresos desde 9898f79 o solos, salen iguales: es la variación del navegador.
- **Pasan 675 pruebas y 1 se salta** (`tests/test_cornamusa.py` es nueva).
- **Gabriel aprobó la cornamusa el 23 nov** y pidió seguir con el barril.

**Cómo se hizo el barril (23 nov).** En la misma rama, como en la propuesta, salvo lo que sigue.
- **El sólido** (`Barril`, en `nudos/anfitrion.py`) es un cilindro parado con la base a la altura 1 y los bordes de la tapa y de la base redondeados con radio 0,6 (`CANTO_BARRIL`, en `nudos/spec.py`). Empuja la cuerda fuera de él por la cara o el borde más cercano, y su «distancia al eje» es la de la superficie más rb, así que cerca del barril no hay gravedad, también sobre la tapa y bajo la base.
- **Lo que depende de la forma va en el barril:** su curva (`Barril.curva`), cómo se separa el tramo de encima en un cruce (`separar`: hacia arriba en la mesa, hacia afuera de la superficie en el barril) y los cruces (`cruces`). `_curva` y `construir_paso` los usan si el sólido los tiene; el poste, el tablón y la cornamusa siguen por su camino de siempre.
- **Al pasar de una cara a otra, la cuerda rodea el borde sola,** en el ángulo del punto del costado más cercano: sube por el costado hasta el borde, lo rodea y sigue por la tapa, o sale por el borde de la base si el punto de la mesa está debajo del barril. Desde la mesa, fuera del barril, sube sola. De la tapa a la mesa sin pasar por el costado es un error al cargar, y también un punto del costado fuera de los bordes o de la tapa fuera de su parte plana.
- **Las zonas** de cada punto son la mesa, el costado, la tapa o un borde. Los cruces se buscan en las tres primeras, como en la propuesta; en los bordes, no.
- **En la especificación,** el costado se escribe `[ángulo, altura]`: los grados van primero, al revés que en el poste. Los segmentos `{tapa: …}` llevan `tapa` en `Segmento` y en `Paso`.
- **La hoja** lo dibuja color madera y, como el tubo, lleva su costado desenrollado, con el frente en el medio (`python -m nudos hoja` y `revision`).
- **El nudo de prueba** (`tests/test_barril.py`) no es del libro: el firme pasa por debajo del barril, sube, cruza la tapa dos veces (un cruce en la tapa) y rodea el costado sobre la subida (un cruce en el costado). Construye sin fallas a la primera. Sus imágenes están en `revision/barril/`, fuera de git, con la hoja y el costado desenrollado.
- **Los nudos hechos no cambian:** los 32 `modelo.json` son iguales byte a byte a la referencia de 9898f79. Las imágenes que diferían en 1 nivel en 1 a 4 píxeles salen iguales impresas desde 9898f79 (el pescador, el pescador doble, el prusik y la presilla de alondra) o reimpresas: es la variación del navegador.
- **Pasan 692 pruebas y 1 se salta** (`tests/test_barril.py` es nueva).
- **Gabriel, al ver las imágenes (23 nov): «¿puedes hacerlo más estilo cubeta?»,** con la foto de una cubeta de plástico roja con la tapa blanca. Ahora el barril tiene forma de cubeta, también para la cuerda: se angosta hacia la base (`FONDO_CUBETA`, el 86 %), arriba tiene una banda que sobresale (`BANDA_CUBETA`, `ESCALON_CUBETA`) con dos ranuras, que solo se dibujan y van hacia dentro, y la tapa, crema. Su forma es un perfil en el plano (distancia al eje, altura) que se gira alrededor del eje (`Barril._perfil`): el sólido mide la distancia a ese perfil, y la cuerda va por el meridiano a 1,1 de él (`Barril._contorno`), tanto en el costado como al rodear los bordes. Roja, en gris la cubeta se oscurecía tanto como la cuerda azul, y los anillos del costado no se veían; naranja y rojo claro, igual. Amarilla y blanca quedan claras en gris, y Gabriel eligió amarilla el 23 nov (las pruebas están en `revision/barril/_colores*.png`). El asa no va: la cuerda pasaría por ella. Este cambio toca solo el barril (su clase, su parte de la escena y de la hoja), así que no se volvió a armar `referencia`; pasan otra vez 692 pruebas y 1 se salta.
- **Gabriel aprobó el barril como cubeta amarilla el 23 nov.** El código de la tanda 5 está hecho: el tablón, la cornamusa y el barril, en la rama `claude/tanda-5-propuesta-7431fd`. Falta que la gestora la integre en `main`; después, los tres borradores pueden ir cada uno en su sesión, con esfuerzo medio.


### Fase 5: libro y primera edición

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

**Dependencias:** fase 4, T11, T12 y D8. También T15 y, si D10 sale a favor de Blender, T16: la edición 1 se imprime con las imágenes nuevas.

**Archivos:** `nudos/libro.py`, `libro/colofon.html`, `CHANGELOG.md`

**Tamaño:** S

#### Punto de control final

- [ ] Se cumplen todos los criterios y la edición 1 está impresa.

### Fase 6: render en Blender, cuerda que se ajusta y videos (propuesta, 23 nov)

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
4. **El orden lo eligió Gabriel:** la prueba, la cuerda, las fichas y al final los videos. Y él decide la compra del paquete después de ver la prueba.
5. **Todas las fichas se rehacen** con el render nuevo (Gabriel, 23 nov), también las de los nudos aprobados y publicados.
6. **La forma de la cuerda la da un motor de física propio, en Python** (T15), no la física de Blender. Blender no tiene un simulador de cuerda: se arma con *cloth* o con cadenas de cuerpos rígidos, y una cuerda delgada que choca consigo misma se atraviesa, y en un nudo eso cambia los cruces sin avisar. Además, el visor, las fichas y la comprobación de cruces viven en Python. El motor reemplaza a la relajación y al apretado, y también sirve para animar (T17).

#### T14: Prueba de Blender

**Descripción:** un script de Blender propio, `render/blender/escena.py`, que lee `modelo.json` y dibuja la cuerda (un tubo por la línea central, con la trenza, el hilo trazador y el resaltado de los colores de `nudos/spec.py`), la mesa, el anfitrión y la luz. Con él se arma una página de prueba como la de T7b: el paso 7 del as de guía, el par del error del ballestrinque y el paso de los ahorcados y el terminado del amarre cuadrado, cada uno como sale hoy y en Blender, a su tamaño impreso, en color y en gris.

**Criterios de aceptación:**
- [ ] `python -m nudos prueba-blender` arma `build/blender/prueba.pdf` desde un clon con los nudos construidos.
- [ ] Cada imagen dice cuánto tardó, para estimar el costo de T16 y de los videos.
- [ ] Gabriel imprime la página en la Epson y decide D10: si el render pasa a Blender y si compra el paquete.

**Verificación:**
- [ ] `python -m pytest`
- [ ] Manual: la página impresa, en color y en gris.

**Dependencias:** ninguna. **Tamaño:** M. **Sesión:** el diseño del render va con el modelo grande; si se compra el paquete, se lee su método de luz y material antes de ajustar la escena.

#### T15: Motor de física de la cuerda (propuesta, 23 nov)

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
- **Las bibliotecas se eligen en T15a** con una prueba de velocidad. Las candidatas son `ipctk` (IPC Toolkit, en C++ con enlace a Python; barreras, CCD y roce para tramos y triángulos), `numba` (las energías de la varilla en CPU) y `warp-lang` (NVIDIA Warp, en la GPU). La preferida es `ipctk` con `numba`, porque garantiza el no atravesarse y repite el resultado. Warp sirve si la CPU es demasiado lenta para los videos.
- **Los parámetros de la cuerda** van en `config/cuerdas.yaml`, uno por tipo de cuerda (la de 8 mm de los nudos libres, el cordino del prusik, el cordón de la cabeza de turco), calibrados en T15f. Una especificación puede pedir la tensión de cada paso (`tension: suelta | ajustada | apretada`), con «ajustada» por omisión: es la v1.14 del formato.
- **`modelo.json` no cambia de forma:** sigue con los puntos de cada paso, y gana, opcional, la torsión de cada tramo y la presión de contacto en cada punto, para el render (T16). El visor los ignora.

**Lo que cuesta (a confirmar en T15a).** El amarre cuadrado tiene unos 2300 nodos y el as de guía unos 500. Si un paso de Newton con contactos tarda de 0,05 a 0,2 s, asentar un paso son de 200 a 1000 pasos: de 1 a 3 minutos. Un nudo serían de 10 a 30 minutos, y los 40 nudos, una noche o dos. Gabriel ya aceptó ese costo.

**Las subtareas, en orden.** Cada una termina con sus pruebas pasando y se revisa antes de seguir.

- **T15a, la espiga (S):** instalar y probar las bibliotecas candidatas en esta computadora (Python 3.14, Windows), con una cuerda sobre un palo y un nudo simple apretado. Se mide la velocidad, si repite el resultado byte a byte y si alguna vez se atraviesa. Sale la pila del motor (D11).
- **T15b, la varilla (M):** estiramiento, flexión, torsión y peso, con gradientes y Hessianos comprobados contra diferencias finitas. Pruebas: la catenaria (una cuerda colgada entre dos puntos toma la forma del coseno hiperbólico) y la elástica (un voladizo cae lo que dice la fórmula).
- **T15c, el contacto y el roce (L):** la barrera y la CCD entre tramos y con los anfitriones, y el roce. Pruebas:
  - Dos cuerdas lanzadas una contra otra nunca se atraviesan.
  - La ecuación del cabrestante (Euler-Eytelwein): una cuerda sobre un palo sostiene un peso con una tensión del otro lado que crece como e^(μθ) con el ángulo abrazado θ.
  - Un bloque sobre una tabla inclinada desliza recién pasado el ángulo del roce.
- **T15d, asentar y apretar (L):** los modos 1 y 2 dentro de `construir`, detrás de una opción, primero con los pilotos de la fase 2: el as de guía, el ballestrinque, la vuelta de escota y el amarre cuadrado. Una página de prueba pone cada uno como está hoy y con el motor, en color y en gris, y Gabriel la aprueba en papel. El nudo simple apretado se compara con el largo de cuerda publicado para los nudos ideales apretados (Pieranski y otros).
- **T15e, calibrar con cuerda real (S, con Gabriel):** con la cuerda de los filtros, se mide el diámetro, el peso por metro, la flexión (cuánto cae un voladizo de 20 cm), el roce con madera (en una tabla inclinada) y, con un peso colgado de un palo, el roce en vuelta. Gabriel saca fotos de cuatro nudos apretados desde vistas marcadas, y el motor los asienta con esos parámetros para compararlos.
- **T15f, migrar los nudos (L):** todos los nudos pasan por el motor, por tandas, con `referencia` y `comparar`. Donde la secuencia de un paso no cambia, el filtro 1 sigue valiendo. Donde cambia, el paso se corrige (ver «La secuencia declarada sigue mandando») y Gabriel decide si repite el filtro. `relajar()` y `apretar()` se borran cuando ningún nudo los use.
- **T15g, lo que el motor le da al render (M, va con T16):** la presión de contacto aplana la sección de la cuerda donde aprieta, como una cuerda real, y la torsión gira la trenza y el hilo trazador. Entra solo lo que se note en la página de prueba impresa.

**Fuera, salvo que una prueba en papel diga lo contrario:** simular los 16 hilos de la trenza (a 58 mm de ancho no se ven; la textura con relieve ya los dibuja) y la pelusa de las fibras.

**Criterios de aceptación de T15:**
- [ ] Las pruebas de física (la catenaria, la elástica, el cabrestante, la tabla inclinada y las cuerdas que no se atraviesan) pasan.
- [ ] Construir dos veces da los mismos `modelo.json` byte a byte.
- [ ] Todos los nudos construyen sin fallas con el motor, con la secuencia declarada en cada paso.
- [ ] Gabriel aprueba en papel la página de prueba de los pilotos y, después, cada tanda.

**Dependencias:** ninguna en código; va después de T14 por el orden que eligió Gabriel. **Tamaño:** XL, en siete subtareas. **Sesión:** el modelo grande para T15a a T15d y T15g; T15f por tandas, como la fase 4.

#### T16: Las fichas se renderizan en Blender

**Descripción:** solo si D10 sale a favor. `python -m nudos imprimir` dibuja con Blender los pasos, el error junto al paso correcto y el nudo terminado por delante y por detrás, y `ficha` las sigue armando con Edge. Después se vuelven a imprimir todas las fichas y se publica el sitio.

**Criterios de aceptación:**
- [ ] Imprimir dos veces da las mismas imágenes, o diferencias que `comparar` declara ruido. Cycles con semilla fija y un solo denoiser; si la GPU no repite el resultado bit a bit, `comparar` gana una tolerancia documentada.
- [ ] Las fichas siguen cabiendo y se leen en gris.
- [ ] Gabriel revisa en papel las fichas rehechas de los nudos ya aprobados.

**Dependencias:** T14 (D10) y T15; T15g se hace junto con esta. **Tamaño:** M, más el tiempo de render de unos 40 nudos: unos 3 s por imagen (`poc/blender`).

#### T17: Animación entre pasos

**Descripción:** calcular el movimiento continuo de la cuerda de un paso al siguiente con el modo «atar» del motor (T15). Una mano lleva el chicote por un camino que sigue, con un margen, la cuerda del paso siguiente, desde su punta, como al pasarla por un lazo. El resto de la cuerda se mueve con la dinámica, el peso y el roce, y al final se asienta en la pose de la ficha. Como el motor nunca deja que la cuerda se atraviese, tampoco entre dos cuadros, la animación hereda esa garantía.
- En una plantilla, cada paso es un comienzo más largo de la misma cuerda: la mano lleva el chicote por el camino final (como el video de `poc/blender`), pero ahora la cuerda que ya está se aprieta con cada vuelta nueva.
- En un nudo libre, la cola cambia de forma entre pasos: la mano la lleva por fuera de todo y la hace entrar por donde dice el paso.

El diseño de los caminos de la mano va como bloque de este plan, con un nudo libre (el as de guía) y una plantilla (el amarre cuadrado) de piloto.

**Criterios de aceptación:**
- [ ] Ningún cuadro tiene una cuerda atravesando otra (la CCD del motor), y la pose final de cada paso es la de la ficha, con su secuencia declarada.
- [ ] Gabriel aprueba la prueba de 10 segundos en movimiento del as de guía y del amarre (la puerta del método de elasthic).

**Dependencias:** T15 (al menos T15d). **Tamaño:** L. Es la tarea de más riesgo de la fase.

#### T18: Videos

**Descripción:** un video por nudo, renderizado en Blender y armado con ffmpeg, con el título de cada paso en pantalla (el texto propio de la especificación, en tuteo y sin términos de sección).
- **En el visor:** horizontal, en la página del QR. El sitio hoy no acepta imágenes ni video, así que la lista de tipos de la decisión de arquitectura 7 gana `.mp4`, con un tope de tamaño. El video vive dentro del sitio, sin YouTube, para que el visor no dependa de servicios externos.
- **En redes:** vertical. Dónde y cuándo se publica lo decide Gabriel.

**Criterios de aceptación:**
- [ ] `python -m nudos video <slug>` arma los dos formatos.
- [ ] El visor del as de guía muestra su video, y la URL del QR no cambia.
- [ ] Gabriel aprueba el video del as de guía antes de renderizar los demás.

**Dependencias:** T17. **Tamaño:** M, más el tiempo de render: en `poc/blender`, 3,8 s por cuadro a 1280 × 720 con 64 muestras, unos 20 minutos por cada 10 s de video. El vertical se renderiza con su propia cámara: recortar el horizontal corta el nudo.

#### Punto de control de la fase 6

- [ ] D10 y D11 decididas, todos los nudos construidos con el motor, todas las fichas rehechas (si D10 sale a favor) y un video por nudo en el visor.

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
| El motor de física es lento, no converge o no repite el resultado | Alto | T15a mide las bibliotecas antes de comprometerse; Newton con búsqueda en línea y CCD, en `float64` y en CPU; si es lento para los videos, Warp en la GPU solo para animar |
| Al asentar con el motor, la secuencia de un paso cambia (un tramo se corre por encima de otro sin atravesarlo) | Medio | La secuencia declarada sigue mandando: el paso falla y se corrige con la tensión o las manos, nunca cambiando la secuencia; donde cambia, Gabriel decide si repite el filtro 1 |
| Las bibliotecas del motor no tienen versión para Python 3.14 en Windows | Medio | T15a lo comprueba primero; las alternativas son compilar `ipctk`, usar Warp o escribir la barrera y la CCD de tramo con tramo en `numba` |
| Complejidad que no se ve en el papel | Medio | Cada fenómeno entra con su prueba física y, si cambia la imagen, con la página de prueba impresa (la regla de T7b) |
| Código o texto de un paquete de pago entra al repositorio público | Alto | El paquete vive fuera de git y solo se usa como referencia; los scripts de Blender del libro son propios |
| El render de los videos ocupa la computadora por días | Bajo | Gabriel acepta el costo; se renderiza por tandas, de noche, empezando por una vista previa a media resolución |

## Preguntas abiertas

- **D3, D8 y D10:** las decisiones previas que siguen abiertas.
- **D7:** si la dirigencia de la Tropa participa en la revisión de su anexo y en conseguir probadores.

## Lo que se reutilizó del prototipo

El prototipo del as de guía se portó completo y la carpeta `prototipo/` se borró al cerrar T3. Sigue en el historial de git:

- **`knot.py`:** el generador libre (trazado, cruces, elevación a 3D, relajación y validación). Pasó a `nudos/` en T1.
- **`render.py`:** el render de verificación en numpy. Pasó a `nudos/hoja.py` en T1.
- **`viewer.template.html` y `build_viewer.py`:** la escena three.js y el visor. Pasaron a `render/escena.js` y `sitio/` en T2.
- **`shoot.py`:** el render con Chrome sin interfaz. Pasó a `nudos/imprimir.py` en T3.
