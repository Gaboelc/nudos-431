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
- **Formatos:** el impreso por ediciones es el principal. El digital es el PDF más un visor 3D por nudo, enlazado con QR desde la ficha.
- **Fuentes:** Animated Knots y el manual de la Tropa son entrada, nunca contenido.
- **Restricciones:**
  - No hay fecha límite.
  - Los QR se mantienen estables entre ediciones.
  - Las fichas no usan términos propios de ninguna sección.
  - Una fuente nueva no obliga a cambiar el flujo.
- **Fuera de alcance:**
  - Material de las fuentes dentro del libro.
  - Animaciones del proceso de atar.
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
- **La tanda 5, anfitriones especiales:** la eslinga de barril, la eslinga de andamio (requiere D1) y la vuelta de cornamusa, sobre una cornamusa. Su propuesta está abajo; Gabriel la aprobó el 23 nov, y el código empieza por el tablón.
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

**Dependencias:** fase 4, T11, T12 y D8

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

## Preguntas abiertas

- **D3 y D8:** las decisiones previas que siguen abiertas.
- **D7:** si la dirigencia de la Tropa participa en la revisión de su anexo y en conseguir probadores.

## Lo que se reutilizó del prototipo

El prototipo del as de guía se portó completo y la carpeta `prototipo/` se borró al cerrar T3. Sigue en el historial de git:

- **`knot.py`:** el generador libre (trazado, cruces, elevación a 3D, relajación y validación). Pasó a `nudos/` en T1.
- **`render.py`:** el render de verificación en numpy. Pasó a `nudos/hoja.py` en T1.
- **`viewer.template.html` y `build_viewer.py`:** la escena three.js y el visor. Pasaron a `render/escena.js` y `sitio/` en T2.
- **`shoot.py`:** el render con Chrome sin interfaz. Pasó a `nudos/imprimir.py` en T3.
