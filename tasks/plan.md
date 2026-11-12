# Plan de implementación: Libro de nudos del Grupo 431

## Resumen

Un solo libro de nudos para la Wak y la Tropa del Grupo 431, impreso por ediciones, que reemplaza al manual v1.2. Cada nudo es una especificación de datos. De ella salen la geometría 3D, las imágenes de impresión, el visor web y la ficha del PDF. La IA interviene en un solo paso, que es convertir las imágenes de referencia en un borrador de especificación. Cada ficha pasa dos filtros humanos antes de publicarse. La primera edición lleva 35 nudos.

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
  - **Ballestrinque doble:** su entrada es la página del manual de la Tropa. Por lo que describe (la cuerda tira a lo largo del mástil), es el *rolling hitch*.
  - **El *tautline hitch* se llama «tensor ajustable»**, para no confundirlo con el tensor (*trucker's hitch*).
  - **El *mooring hitch* se llama «nudo de liberación rápida».** En el manual v0.1 era «nudo de amarre de liberación rápida»; se quitó «amarre» para no confundirlo con los amarres.

### Fase 1: primer corte vertical, el as de guía de principio a fin

#### T1: Repositorio y especificación v0 con el as de guía

**Descripción:** crear la estructura del repositorio y portar a un paquete el generador libre del prototipo. Definir la especificación v0 con el as de guía: metadatos, cuerda, pasos (trazado y secuencia de cruces) y tramos resaltados.

**Criterios de aceptación:**
- [ ] `specs/as-de-guia.yaml` describe los 7 pasos, y `construir` genera sus 7 líneas centrales relajadas.
- [ ] En cada paso, la secuencia de cruces después de relajar coincide con la especificación y se cumplen los límites de separación, curvatura y estiramiento.
- [ ] Una copia de la especificación con un cruce invertido en un solo paso hace fallar la prueba de consistencia entre pasos. Ninguna prueba automática detecta un error que se repite igual en todos los pasos: para eso está el filtro 1.

**Verificación:**
- [ ] `pytest -k as_de_guia`
- [ ] `python -m nudos construir as-de-guia`
- [ ] Manual: la hoja de vista superior coincide con la del prototipo.

**Dependencias:** D5

**Archivos:** `specs/as-de-guia.yaml`, `nudos/spec.py`, `nudos/cruces.py`, `nudos/libre.py`, `tests/test_as_de_guia.py`

**Tamaño:** M. La mayor parte es código portado del prototipo.

#### T2: Escena 3D compartida y visor publicado

**Descripción:** separar la escena three.js del prototipo en un módulo único con la cuerda trenzada, el resaltado, el remate, las luces y el encuadre. Generar desde la especificación el visor del as de guía y publicarlo en su URL permanente.

**Criterios de aceptación:**
- [ ] El visor en `<base>/as-de-guia/` muestra los 7 pasos, con vista superior y 3D, y funciona en el celular.
- [ ] El sitio construido no contiene ninguna imagen de las fuentes.
- [ ] `publicados.txt` incluye el slug, y una prueba falla si su página no está en el sitio.

**Verificación:**
- [ ] `pytest tests/test_sitio.py`
- [ ] `python -m nudos sitio`
- [ ] Manual: abrir la URL en el celular.

**Dependencias:** T1, D4

**Archivos:** `render/escena.js`, `sitio/plantilla.html`, `sitio/visor.js`, `sitio/visor.css`, `sitio/vendor/`, `nudos/exportar.py`, `scripts/publicar.sh`, `publicados.txt`, `tests/test_sitio.py`

**Tamaño:** M

#### Punto de control 1: después de T1 y T2

- [ ] La especificación reproduce el prototipo.
- [ ] El visor está en su URL permanente.

#### T3: Imágenes de impresión, error común y vistas finales

**Descripción:** generar con Chrome sin interfaz las imágenes de cada paso a 300 ppp, desde la escena compartida. Agregar a la especificación el error común, que declara qué cruces se invierten y en qué paso, y las dos vistas del nudo terminado.

**Criterios de aceptación:**
- [ ] Para el as de guía se generan, a 300 ppp en su tamaño impreso:
  - Los 7 pasos.
  - El error (la gaza pequeña al revés) junto al paso correcto.
  - Las 2 vistas finales.
- [ ] La secuencia de cruces del error difiere de la correcta exactamente en los cruces declarados.
- [ ] Construir dos veces produce las mismas imágenes.

**Verificación:**
- [ ] `pytest tests/test_errores.py`
- [ ] `python -m nudos imprimir as-de-guia`
- [ ] Manual: imprimir una página de prueba en la Epson y revisar que se distinga qué tramo cruza por encima.

**Dependencias:** T2

**Archivos:** `nudos/errores.py`, `nudos/imprimir.py`, `render/escena.js`, `specs/as-de-guia.yaml`, `tests/test_errores.py`

**Tamaño:** M

#### T4: Ficha impresa del as de guía con QR

**Descripción:** crear la plantilla HTML/CSS de la ficha con todas sus secciones, que se llena desde la especificación. Incluye un QR al visor y se exporta a PDF con Chrome en tamaño carta, como un pliego de dos páginas con margen de resorte (D2). El texto va en tuteo y es propio.

**Criterios de aceptación:**
- [ ] El PDF tiene todas las secciones de la ficha y el QR abre el visor.
- [ ] La prueba de vocabulario pasa: ningún término propio de una sección aparece en la ficha.
- [ ] El nudo pasa los dos filtros y quedan registrados en la especificación.

**Verificación:**
- [ ] `pytest tests/test_ficha.py`
- [ ] `python -m nudos ficha as-de-guia`
- [ ] Manual: imprimir la ficha, escanear el QR y hacer los filtros 1 y 2.

**Dependencias:** T3, D1, D2

**Archivos:** `libro/ficha.html`, `libro/ficha.css`, `nudos/ficha.py`, `config/terminos_seccion.txt`, `tests/test_ficha.py`

**Tamaño:** M

#### Punto de control A: después de T3 y T4

- [ ] Toda la suite pasa y el proyecto se construye desde un clon limpio.
- [ ] La ficha impresa del as de guía pasó los dos filtros. Si el filtro 2 falla, se corrige la ficha antes de seguir: es la señal más importante del proyecto.
- [ ] Decidir si la impresión se queda con three.js o pasa a Blender, según cómo se ve la página impresa.
- [ ] Revisar contigo el diseño de la ficha y el formato de especificación.

**Resultado (9 de noviembre de 2026):** la impresión se queda con three.js: la prueba impresa y los dos filtros pasaron con esas imágenes, y el visor y la ficha salen de la misma escena. La ficha se queda como está, incluido el espacio libre al final de la página derecha. Cómo caben los nudos de más de 6 pasos se decide en T7, con el amarre cuadrado.

### Fase 2: piloto por tipo de nudo

#### T5: Objeto anfitrión con el ballestrinque sobre poste

**Descripción:** agregar a la especificación objetos anfitriones rígidos: poste, argolla, estaca, tablón, barril, cornamusa y cuerda anfitriona. Agregar a la relajación las colisiones contra ellos. Las vueltas se describen en coordenadas del anfitrión: posición a lo largo, ángulo y capa. Los cruces se verifican sobre la superficie desenrollada del anfitrión, no en la proyección.

**Criterios de aceptación:**
- [ ] El ballestrinque sobre un poste se construye en todos sus pasos sin que la cuerda atraviese el poste.
- [ ] Los cruces sobre el poste coinciden con la especificación.
- [ ] El nudo pasa los dos filtros.

**Verificación:**
- [ ] `pytest -k ballestrinque`
- [ ] `python -m nudos construir ballestrinque`
- [ ] Manual: filtros 1 y 2.

**Dependencias:** T4

**Archivos:** `nudos/anfitrion.py`, `nudos/libre.py`, `render/escena.js`, `specs/ballestrinque.yaml`, `tests/test_ballestrinque.py`

**Tamaño:** M. Es el mayor riesgo técnico del proyecto, por eso va primero en la fase.

**Cómo se hizo (9 de noviembre de 2026):** se implementó solo el poste. La argolla, la estaca, el tablón, el barril, la cornamusa y la cuerda anfitriona se agregan con el primer nudo que los necesite, para no dejar código sin un nudo que lo pruebe. Sobre el poste los puntos van como [x, ángulo], sin capa: qué tramo queda encima lo decide la secuencia, igual que en la mesa, y así el error común funciona sin cambios. Cerca del poste la cuerda se relaja sin gravedad ni suavizado, como si estuviera algo tensa, y con más correcciones de largo. El nudo terminado sobre un anfitrión no se voltea: se mira desde el otro lado (vista «detras»). Se usó el método con el chicote, que sirve en cualquier poste y es el que empieza los amarres.

#### T6: Dos cuerdas con la vuelta de escota

**Descripción:** permitir varias cuerdas por nudo, cada una con su grosor y su color según el rol. La vuelta de escota une cuerdas de distinto grosor. Los cruces entre cuerdas entran en la misma secuencia de cruces.

**Criterios de aceptación:**
- [ ] Dos cuerdas de distinto grosor y color se construyen y se ven bien en el visor y en la impresión.
- [ ] La secuencia de cruces es correcta en cada paso, y la separación usa la suma de los radios.
- [ ] El nudo pasa los dos filtros (el filtro 2, cuando se retome).

**Verificación:**
- [ ] `pytest -k vuelta_de_escota`
- [ ] `python -m nudos construir vuelta-de-escota`
- [ ] Manual: filtros 1 y 2.

**Dependencias:** T4. Puede hacerse en paralelo con T5.

**Archivos:** `nudos/spec.py`, `nudos/libre.py`, `nudos/cruces.py`, `specs/vuelta-de-escota.yaml`, `tests/test_vuelta_de_escota.py`

**Tamaño:** M

**Diseño (9 de noviembre de 2026, antes de implementar).** Referencia: `entradas/vuelta-de-escota/`, 7 imágenes. La cuerda gruesa forma un seno; la delgada sube por el seno, rodea por detrás sus dos ramas y se mete por debajo de sí misma.
- **Formato:** `cuerdas` es una lista con `nombre`, `grosor` (diámetro relativo a la cuerda de siempre, que mide 1) y `color`. Con más de una cuerda, `trazado` y `secuencia` de cada paso pasan a ser mapas por cuerda: `trazado: {gruesa: [...], delgada: [...]}`. Cada secuencia recorre su cuerda desde su firme; cada etiqueta aparece dos veces en total, una con O y otra con U, en la misma cuerda o en las dos. Un nudo de una sola cuerda se sigue escribiendo como hasta ahora.
- **Geometría:** las cuerdas se concatenan en una sola polilínea con cortes entre ellas, y cada punto lleva su cuerda y su radio. Ningún segmento, largo, suavizado ni salto de vecinos cruza un corte. Las colisiones y la separación usan la suma de los radios; el apoyo en la mesa, el radio de cada punto; la curvatura y el estiramiento se miden por cuerda, en sus diámetros. Los cruces se buscan con los segmentos válidos (`_cruces_2d`, que hoy está en `nudos/anfitrion.py`, pasa a `nudos/cruces.py`). Los primeros puntos de cada cuerda quedan fijos.
- **Color:** la gruesa en el azul de siempre y la delgada en un color claro (crema, con trazador rojo). En gris, el rojo de Animated Knots se confundiría con el azul; crema, ámbar y azul quedan claro, medio y oscuro.
- **Escena e impresión:** `datos_escena` lleva una lista de cuerdas por paso, cada una con sus puntos, radio, color y tramo resaltado; los nudos de una cuerda se exportan igual que ahora. Nombres en la imagen: el nombre de cada cuerda junto a su firme y «Chicote» solo en la que se mueve. Hay que revisar la hoja de revisión (`nudos/hoja.py`) y la ficha.
- **Riesgo:** los nudos de una cuerda tienen que seguir dando exactamente las mismas imágenes (comprobado píxel por píxel contra el as de guía y el ballestrinque).

**Cómo se hizo (9 de noviembre de 2026):** se implementó el diseño tal cual, con estos detalles que salieron al hacerlo.
- Todas las cuerdas comparten el mismo paso de muestreo, así que la posición a lo largo de la polilínea es índice × paso. Cada pasada tiene que caer en la cuerda donde se declaró, y las fallas escriben la secuencia de cada cuerda.
- Con varias cuerdas se corrige el largo 12 veces por vuelta, no 4: una gruesa empuja hacia arriba a la delgada que pasa encima, y la delgada se estiraba hasta su firme.
- Una cuerda gruesa que sube sobre otra lo hace en un largo proporcional a su grosor. Con grosor 1 el cálculo es el de siempre.
- Una gruesa que cruza en ángulo recto por encima de una delgada se apoya sobre ella con un radio igual a la suma de los radios (1,25 con grosores 1,5 y 1), que es 0,83 de su diámetro y no pasa la prueba de curvatura. No se cambió la prueba: en la vuelta de escota, la delgada cruza a la gruesa en diagonal en todos esos cruces, también los que quedan al revés en la vista de detrás. Está en `docs/formato-spec.md`.
- La vuelta de escota tiene 4 pasos, con la gruesa de grosor 1,5. El error común es el chicote por encima de sí misma (cruce 6). En el modelo, la delgada pasa por debajo de sí misma justo después de cruzar la rama del chicote de la gruesa, no dentro del seno: es el mismo nudo, porque esa rama queda debajo de las dos pasadas de la delgada.
- Esta computadora no tiene Chrome. Las comparaciones píxel por píxel (38 imágenes, antes y después del cambio) y las pruebas que dibujan se hicieron con Edge, poniendo `NUDOS_CHROME` en la ruta de `msedge.exe`. Las imágenes de un mismo navegador salen idénticas; entre Chrome y Edge pueden cambiar un poco.

#### T6b: Alternativas y precauciones en la página y la ficha

**Descripción:** pedido de Gabriel el 9 de noviembre de 2026. El visor y la ficha impresa muestran, además de los pasos, los detalles del nudo: para qué sirve, qué otros nudos convienen en su lugar y cuándo, y los cuidados y peligros de usarlo. Los `info.txt` de `entradas/` traen esos datos, pero son texto de Animated Knots: se usan como entrada y el texto del libro es propio, como el resto de la ficha.

**Criterios de aceptación:**
- [ ] La especificación lleva `alternativas` (otro nudo y cuándo conviene) y `precauciones` (cuidados y peligros), con texto propio. Sin ellos, la ficha no se genera.
- [ ] El visor muestra para qué sirve, también se llama, alternativas, precauciones y seguridad, debajo de los pasos.
- [ ] La ficha los muestra en la página 2 y sigue cabiendo en el pliego, en los tres nudos.
- [ ] Gabriel revisa el texto de cada nudo.

**Verificación:**
- [ ] `pytest`
- [ ] `python -m nudos ficha <slug>` para los tres nudos
- [ ] Manual: el visor en el celular y las fichas impresas.

**Dependencias:** T4. Va antes del Punto de control B, porque agrega campos al formato.

**Archivos:** `nudos/spec.py`, `nudos/ficha.py`, `libro/ficha.html`, `libro/ficha.css`, `nudos/exportar.py`, `sitio/plantilla.html`, `sitio/visor.css`, `specs/*.yaml`, `docs/formato-spec.md`, `tests/`

**Tamaño:** S

#### Punto de control 2: después de T5 y T6

- [x] El anfitrión y las dos cuerdas funcionan.
- [x] Si el anfitrión no da resultados confiables, los enganches de la tanda 3 pasan a plantillas y se replanifica la fase 4. No hizo falta.

**Aprobado por Gabriel el 9 de noviembre de 2026.** El ballestrinque sobre el poste y la vuelta de escota con dos cuerdas pasaron el filtro 1 con cuerda real, siguiendo la ficha impresa. Los enganches de la tanda 3 siguen con el anfitrión, y la fase 4 no se replanifica. Las revisiones de texto de T5, T6 y T6b siguen pendientes, pero no bloquean este punto.

#### T7: Plantilla del amarre cuadrado

**Descripción:** crear una plantilla que genere los pasos del amarre cuadrado a partir de medidas: diámetro de los postes, número de vueltas, número de ahorcados y los ballestrinques de inicio y de cierre.

**Criterios de aceptación:**
- [ ] Cambiar un parámetro, por ejemplo de 3 a 4 vueltas, regenera todos los pasos sin editar nada a mano.
- [ ] La cuerda no atraviesa los postes ni otras vueltas.
- [ ] El amarre pasa los dos filtros.

**Verificación:**
- [ ] `pytest -k amarre_cuadrado`
- [ ] `python -m nudos construir amarre-cuadrado`
- [ ] Manual: filtros 1 y 2.

**Dependencias:** T5

**Archivos:** `nudos/plantillas/amarre.py`, `specs/amarre-cuadrado.yaml`, `tests/test_amarre_cuadrado.py`, `render/escena.js`

**Tamaño:** M

**Diseño (9 de noviembre de 2026, antes de implementar; Gabriel lo aprobó el mismo día con las respuestas del final).** Referencias: `entradas/amarre-cuadrado/` (18 imágenes) y la página 27 del manual de la Tropa. Las dos usan el mismo método, que es el que sigue la plantilla.
- **Método:**
  - Empieza con un ballestrinque en el palo de abajo, del lado de quien ata y pegado al palo de arriba.
  - Siguen las vueltas alrededor de los dos palos. Cada una pasa por encima del palo de arriba, a los dos lados del de abajo, y por debajo del palo de abajo, a los dos lados del de arriba. Cada vuelta nueva va por dentro de la anterior sobre el palo de arriba y por fuera sobre el de abajo. Así, entre los palos, las vueltas quedan una junto a otra y no unas encima de otras.
  - Después vienen los ahorcados: vueltas entre los dos palos, por debajo del de arriba y por encima del de abajo, que rodean las vueltas por fuera y las aprietan.
  - Termina con un ballestrinque en el palo de arriba.
- **Los dos palos:** son un anfitrión nuevo, `tipo: cruz`, con `radio` (el mismo para los dos, en diámetros de cuerda) y `largo` (el de cada palo).
  - Están sobre la mesa y se cruzan en ángulo recto en x = y = 0. El de abajo va a lo largo de y, hacia el fondo de la mesa. Se apoya en la cuerda que pasa por debajo, así que su eje queda a la altura radio + 1, como el poste de T5. El de arriba va a lo largo de x y se apoya sobre el de abajo.
  - Propuesta: radio 2,5, que es un palo de 4 cm con una cuerda de 8 mm.
  - El ángulo queda fijo en 90°. El amarre diagonal agregará `angulo` cuando llegue. El poste de T5 no cambia.
- **Formato:** un nudo de plantilla no lleva `segmentos`, `trazado` ni `secuencia`. Lleva `plantilla` con sus medidas, y cada paso dice con `hasta` hasta dónde llega:

  ```yaml
  anfitrion: {tipo: cruz, radio: 2.5, largo: 40}
  plantilla:
    tipo: amarre-cuadrado
    vueltas: 3                              # alrededor de los dos palos
    ahorcados: 3                            # entre los palos
    inicio: {poste: abajo, lado: delante}   # ballestrinque de inicio
    cierre: {poste: arriba, lado: derecha}  # ballestrinque de cierre
  pasos:
    - {titulo: Haz un ballestrinque en el palo de abajo, texto: …, hasta: inicio}
    - {titulo: Da la primera vuelta, texto: …, hasta: vuelta-1}
    - {titulo: Da las demás vueltas, texto: …, hasta: vueltas}
    - {titulo: Da el primer ahorcado, texto: …, hasta: ahorcado-1}
    - {titulo: Da los demás ahorcados, texto: …, hasta: ahorcados}
    - {titulo: Empieza el ballestrinque de cierre, texto: …, hasta: cierre-1}
    - {titulo: Termina el ballestrinque, texto: …, hasta: cierre}
  ```

  - `hasta` puede ser `inicio-1`, `inicio`, `vuelta-<n>`, `vueltas`, `ahorcado-<n>`, `ahorcados`, `cierre-1` o `cierre`. Los pasos van en ese orden y el último llega a `cierre`. Un `hasta` que no existe con esas medidas, como `vuelta-4` con 3 vueltas, es un error al cargar.
  - El tramo resaltado es lo que agrega cada paso, así que no se escribe.
  - El texto puede decir `{vueltas}` o `{ahorcados}`, que salen en letras («tres»).
  - Así, pasar de 3 a 4 vueltas es cambiar un número: los pasos, las imágenes y el texto se regeneran solos.
  - Los 3 y 3 son los del manual de la Tropa, que pide «tres o cuatro» de cada uno.
- **Geometría:** la plantilla calcula una sola vez la cuerda entera, desde el chicote corto del ballestrinque de inicio hasta el chicote del cierre.
  - Cada paso es el comienzo de esa cuerda hasta su `hasta`, más el resto, que sale del amarre hacia afuera y cae a la mesa. Así un cruce es el mismo en todos los pasos y conserva su etiqueta.
  - Cada tramo va sobre una superficie, en una capa contada en diámetros desde ella. Las vueltas van sobre la cara de arriba del palo de arriba y la de abajo del palo de abajo, a un diámetro una de otra. Entre los palos, las esquinas de las vueltas bajan de un palo al otro, una junto a otra. Los ahorcados van por fuera de las esquinas, a la altura donde se tocan los palos. Los ballestrinques van sobre su palo, como en T5.
  - Después se pasa la curva suave, se muestrea cada 0,2 diámetros y se relaja como cerca del poste: sin gravedad, porque el amarre va apretado, con choques entre tramos y sin entrar en los palos ni estirarse.
- **Cruces:** como sobre el poste, cada tramo se compara en la superficie desenrollada del cilindro donde va, y encima es lo más lejos del eje.
  - Hay tres cilindros: el palo de abajo, el de arriba y, entre los palos, uno vertical alrededor del cruce (la «cintura» del amarre). En la cintura se cruzan los ahorcados con las esquinas de las vueltas.
  - La plantilla sabe en qué zona va cada tramo. Los cruces entre zonas no se buscan; ahí se comprueba solo la separación, como entre el poste y la mesa.
  - La plantilla escribe la secuencia que corresponde al método. Cada ahorcado pasa por encima de cada vuelta en las cuatro esquinas; las vueltas no se cruzan entre sí, porque van una junto a otra; y cada ballestrinque tiene sus dos cruces. Con 3 vueltas y 3 ahorcados son 40 cruces.
  - Esa secuencia se compara con la que se mide en la cuerda relajada, igual que en los nudos libres. La consistencia entre pasos y la heurística del cruce que salta se aplican igual.
- **Que la cuerda no atraviese nada:** no entra en ninguno de los dos palos más de 0,05 diámetros, como en el poste. Ningún tramo queda a menos de 0,97 diámetros de otro, así que tampoco atraviesa otras vueltas. La curvatura (0,9) y el estiramiento (2 %) se miden como siempre.
- **Error común:** en una plantilla, el error no es un cruce invertido, sino una variante del método que la plantilla sabe construir, por ejemplo `error: {paso: 5, variante: ahorcados-por-fuera, …}`.
  - El del amarre: los ahorcados por encima del palo de arriba, en lugar de entre los palos.
  - Se construye y se comprueba como un paso más, con el mismo encuadre que el paso bien hecho.
  - `invierte` sigue siendo el error de los nudos libres.
  - Hay errores comunes que no se ven en una imagen. El del amarre es no mantener la cuerda tensa mientras se ata, y el amarre queda flojo. Para eso, `error` acepta `otros`, una lista de errores con `titulo` y `texto` y sin imagen. En la ficha y en el visor van debajo del error con imagen. Sirve para cualquier nudo; si no hay `otros`, nada cambia. La tensión también se pide en el texto de los pasos y se comprueba en la verificación: los palos no se mueven ni giran uno respecto al otro.
- **Nudo terminado:** por delante, en la vista de los pasos. Por detrás, el amarre entero, palos y cuerda, se voltea como un marco sobre la mesa. Así queda arriba el palo que estaba abajo y se ven las vueltas que pasan por debajo de él.
  - Es un giro rígido. Como los cruces se miden respecto a los palos y no a la mesa, la secuencia no cambia.
  - Sobre un poste el nudo se mira desde el otro lado. En el amarre eso mostraría la misma cara, porque la de atrás queda contra la mesa.
- **Escena:**
  - Los dos palos son cilindros de madera, como el poste.
  - Nombres: en el paso 1 van «Firme» en la parte larga y «Chicote» en el extremo corto, como en el ballestrinque. Desde el paso 2 se mueve la parte larga, y solo lleva «Chicote», en su punta.
- **Ficha:**
  - 7 pasos: 6 en la página 1 y 1 en la 2.
  - El error, junto al paso 5 bien hecho.
  - El terminado, por delante y por detrás.
  - Materiales: dos palos y una cuerda de unos 3 m (por confirmar al atarlo).
  - La hoja de revisión sigue dibujando solo la cuerda vista desde arriba.
  - Seguridad: con los amarres se arman construcciones que sí sostienen personas, así que la ficha no dice lo contrario (excepción a D1). Los cuidados, como revisar cada amarre y los palos antes de subirse a una construcción, van en `precauciones`. Gabriel los revisa con el texto de la ficha.
- **Lo que no cambia:** el generador libre y el poste. El as de guía, el ballestrinque y la vuelta de escota tienen que dar los mismos `modelo.json`, byte a byte, y las mismas imágenes, píxel por píxel. Se comprueba como en T6.
- **Riesgo:** las esquinas entre los palos. Ahí tres o cuatro vueltas bajan de un palo al otro en poco espacio, y los ahorcados pasan por fuera de ellas. Si no caben a un diámetro con estas medidas, se agranda el radio de los palos o se cambia la forma de las esquinas, mirando las imágenes. Los límites no se aflojan.
- **Lo que decidió Gabriel (9 de noviembre):**
  1. El cierre va en el palo de arriba, como en la propuesta.
  2. El ballestrinque de inicio va en un solo paso, que remite a la ficha del Ballestrinque. Son 7 pasos.
  3. El error con imagen son los ahorcados por fuera de los palos. Además va, sin imagen, no mantener la tensión mientras se ata, porque es muy común que el amarre quede flojo (`error.otros`).
  4. Los amarres sí sostienen personas: para eso son. La ficha no dice que no, y D1 queda con esa excepción.

**Cómo se hizo la geometría (9 de noviembre de 2026; las esquinas y los ahorcados, rehechos el 10):** con el diseño, salvo lo que sigue. Gabriel lo revisó en las imágenes de la escena el 10 de noviembre: aprobó el orden de las vueltas, las vueltas que delante pasan por fuera del ballestrinque y el volteo del terminado, y pidió que la cuerda no se viera rígida («en el ballestrinque la cuerda gira alrededor de la circunferencia del palo, aquí no»). Por eso se rehicieron las esquinas y los ahorcados.
- **El orden de las vueltas es el de las referencias, al revés de lo que decía el diseño.** Cada vuelta nueva va por fuera de la anterior sobre el palo de arriba y por dentro sobre el de abajo (el palo del ballestrinque de inicio), como en las fotos y la descripción de `entradas/amarre-cuadrado/`. Así la última vuelta termina por fuera, junto al palo de arriba, y de ahí sale el primer ahorcado; los ahorcados terminan en el mismo lugar y el cierre empieza ahí mismo, en el palo de arriba a la derecha, sin cruzar nada más. Al revés, la última vuelta termina delante, bajo el palo de abajo, y para llegar al cierre en el palo de arriba la cuerda tendría que pasar por encima de las esquinas de ese lado, con cruces que el método no tiene.
- **Delante, las vueltas pasan por fuera del ballestrinque de inicio.** El ballestrinque va pegado al palo de arriba, como dice el método. En las fotos las vueltas pasan por encima de él, pero dos tramos apilados sobre la misma superficie no se pueden comparar en su mapa. Por eso, delante, las vueltas pasan bajo el palo de abajo más lejos del cruce que detrás: con 3 vueltas, entre 6,6 y 8,8 diámetros, frente a 3,05 y 5,25 detrás. Visto desde arriba, el amarre queda más largo hacia quien ata. Gabriel lo aprobó en las imágenes el 10 de noviembre; la otra salida era apilar las vueltas sobre el ballestrinque y contar esos cruces.
- **El ballestrinque de inicio queda con la cruz abajo a la derecha.** Así el firme sale por el costado del palo de abajo y sube recto a la primera vuelta. Si subiera desde arriba del palo, su esquina sería tan corta que los ahorcados no la cruzarían con seguridad en el mapa de la cintura.
- **Las piezas.** La cuerda se arma con rectas, arcos alrededor de un palo en su plano de corte, curvas suaves y puntos sueltos (`nudos/plantillas/trazo.py` y `amarre.py`), y las esquinas entre dos rectas se redondean con radio 1,3. Lo que va sobre un palo, como el arco de una vuelta o el paso de un ahorcado por debajo o por encima de un palo, va en la zona de ese palo. Las esquinas de las vueltas y los ahorcados, entre los palos, van en la cintura.
- **Las esquinas** (rehechas el 10 de noviembre). Antes eran postes verticales lejos de los palos, con tramos rectos y horizontales hasta cada palo: la cuerda se veía rígida, como una jaula, sobre todo delante. Ahora cada esquina deja un palo siguiendo su arco y llega al otro igual, así que baja pegada a las caras de los dos; entre uno y otro va en una curva suave (de Hermite). Dónde deja cada palo es lo de una cuerda tensa: cada punto es la tangente desde el otro.
  - Con las vueltas a 1,1 sobre los palos, las esquinas rectas de un lado quedarían a 0,78 a media altura, porque la banda que forman se angosta al girar de un palo al otro. Por eso, a media altura, cada esquina se aparta 0,4 de su vecina a lo largo de la banda (`ABRIR`), y las vueltas siguen a 1,1 sobre los palos.
  - Delante, las vueltas pasan bajo el palo de abajo por fuera del ballestrinque de inicio, así que cada esquina sube primero recta, pegada a la cara del palo de abajo, y pasa por encima del ballestrinque. Vistas desde arriba, las esquinas vecinas de delante se cruzan, y la de la vuelta anterior pasa por encima; por eso su tramo recto es un diámetro más alto que el de la siguiente (`ESCALON`). Con 3 vueltas, esos tramos llegan de 4,5 a 6,5 diámetros sobre la mesa; con 6, el más alto llega a la altura del palo de arriba.
  - Delante a la derecha, las esquinas que suben a la vuelta siguiente pasan por fuera del firme, que va pegado al cruce. Desde un poco más abajo de donde pasan, el firme va en la zona del palo de arriba, así que en la cintura solo lo cruzan los ahorcados. En la cuerda real esas vueltas pasan por fuera del firme sin cruzarlo sobre ningún palo; el método no cuenta ese paso, como antes.
- **Los ahorcados** (rehechos el 10 de noviembre) son vueltas tensas entre los palos. En cada cuadrante van por el camino más corto que deja por fuera, a 1,08, todo lo que ya está atado a su altura: las esquinas, los ahorcados anteriores, la salida de la última vuelta y el ballestrinque de inicio. Pasan bajo el palo de arriba y sobre el de abajo justo por fuera de las esquinas, cada uno 1,1 más afuera que el anterior. Su altura sube y baja suave: pasan bajo el palo de arriba cerca de su cara de abajo y sobre el de abajo cerca de su cara de arriba, y entre el primero y el último hay 0,8 de altura, así que en el mapa de la cintura no se cruzan.
- **La salida de la última vuelta** sube por la cara del palo de abajo y se aparta de él, en la zona de ese palo, sin acercarse al ballestrinque a lo largo del palo. Ya lejos del firme, pasa a la zona del palo de arriba y va a pasar bajo él, donde empieza el primer ahorcado. Así, como antes, no se mide como cruce con el firme ni con el ballestrinque.
- **Los cruces de los ballestrinques ya van separados al trazarlos.** La diagonal va un diámetro más lejos del palo donde cruza. Levantarla después, como sobre el poste, estiraba la cuerda un 3 %, porque tenía que correr alrededor del palo.
- **Sin gravedad.** La cuerda se relaja tensa y el resto de cada paso ya va trazado hasta la mesa. Si cae, tira del amarre y lo estira.
- **Resultado** (con las esquinas rehechas). Con 3 vueltas y 3 ahorcados, los 7 pasos salen sin fallas: los 40 cruces del método, separación de al menos 0,99, curvatura de al menos 1,00, estiramiento de hasta 1,3 % y penetración de 0,03 en los palos. También sin fallas con 2 y 2, 4 y 3, 3 y 4 y 6 y 6, con separación de al menos 0,99 y curvatura de al menos 0,95. Construir el amarre tarda cerca de un minuto.
- **Pendiente.** `inicio-1` es la cuerda hasta antes de la diagonal del inicio: es un comienzo de la cuerda, pero no un momento del atado, porque la cuerda empieza en el chicote y el ballestrinque se ata desde el firme. La especificación no lo usa. El error construido está en «Cómo se hizo el error y la especificación».

**Cómo se hizo la escena (10 de noviembre de 2026):** con el diseño, más estos detalles.
- **Los palos.** La escena dibuja la cruz con los datos de `Cruz.datos()`: el palo de abajo a lo largo de y y el de arriba a lo largo de x, de madera como el poste, con el alto de los dos en el encuadre. El visor y la impresión usan la misma escena.
- **Las vistas.** Los pasos y el nudo terminado, por delante y por detrás, van en la vista de los pasos (3D, desde donde se ata). Por detrás, `Cruz.voltear` gira el amarre entero, palos y cuerda, media vuelta alrededor del eje y, como una página, y lo apoya en lo que queda más abajo: el abultamiento del ballestrinque de cierre, así que el palo de arriba queda a dos diámetros de la mesa. No se relaja ni se vuelve a comprobar, porque es un giro rígido. No va en `Modelo.reverso`: la impresión lo calcula del último paso. La ficha dice «Por detrás es como lo ves si volteas los dos palos juntos como la página de un libro».
- **Los nombres.** En el paso del ballestrinque de inicio la cuerda se pasa a la escena al revés, desde la parte larga, para que «Firme» quede en ella y «Chicote» en el extremo corto. Desde la primera vuelta, el paso dice que solo lleva «Chicote» (`nombres`), en la punta de la parte larga. Los dos extremos de la cuerda llevan remate en todos los pasos, para que el extremo corto se vea igual en todos (`dos_remates`). Cuáles pasos tienen firme lo dice la plantilla (`CON_FIRME`).
- **Los errores sin imagen** (`error.otros`) van en la ficha debajo del error con imagen, como «Otro error común». El visor todavía no muestra el error común de ningún nudo, así que tampoco estos.
- **La hoja de revisión** sigue dibujando solo la cuerda, como decía el diseño.
- **El encuadre** lo pone la especificación definitiva. Sin él, la escena encuadra la cuerda de todos los pasos con sus restos, que salen unos 18 diámetros del amarre, y en los pasos el amarre se ve chico. Si con el encuadre el resto queda fuera de la imagen, el paso pierde el nombre «Chicote», que va en su punta.
- **Una ficha de prueba**, con texto de relleno y el paso 5 en lugar del error, cabe en el pliego: 6 pasos en la página 1 y, en la 2, el paso 7, el error con el otro error debajo, el terminado, la verificación, las precauciones y las alternativas, con espacio libre al final.
- **Nudos publicados:** iguales que antes, los 3 modelos byte a byte y las 49 imágenes píxel por píxel, con Edge.

**Cómo se hizo el error y la especificación (10 de noviembre de 2026):**
- **El error es una variante de la cuerda entera** (`cuerda(plantilla, cruz, variante)` en `nudos/plantillas/amarre.py`; `construir_error` en `pasos.py`). Hasta las vueltas es la misma cuerda, punto por punto. En cada ahorcado, donde el bien hecho pasa por debajo del palo de arriba, el error sube en diagonal desde un diámetro por fuera de su cara (`FUERA`), pasa por encima, por fuera de las vueltas, y baja en diagonal por la otra cara. Entre los palos y sobre el palo de abajo va como el bien hecho. Se construye y se comprueba como un paso más, hasta el `hasta` del paso 5, y resalta lo mismo que ese paso.
- **Cruza las mismas esquinas que el paso 5** (38 cruces con 3 y 3): por el lado del palo de arriba no cruza nada. Lo que sube y baja va en la zona de la cintura, y el arco sobre el palo en la del palo de arriba. Las esquinas de las vueltas llegan al palo más arriba de donde el ahorcado empieza a subir, así que cada una lo cruza una vez en el mapa de la cintura. La plantilla escribe esa secuencia para la variante y se compara con la cuerda relajada, como en los pasos.
- **Tres ajustes, para que se cumpla eso y la cuerda relaje bien:**
  1. Cada ahorcado va más bajo que el anterior, al revés que en el bien hecho. Si fuera más alto, pasaría por fuera de donde suben los anteriores y serían cruces que el método no tiene. Por eso, sobre cada esquina, los ahorcados del error pasan en el orden contrario.
  2. Sobre el palo de arriba van 1,6 diámetros más afuera cada uno, y el primero a 1,6 de la última vuelta (`SEPARA_ENCIMA`), no a 1,1.
  3. Cada uno empieza a subir 0,5 más lejos del palo que el anterior (`ABRE_FUERA`).
  Sin los dos últimos, donde un ahorcado baja del palo tiene que rodear enseguida el pie del anterior, y esa esquina quedaba con radio de 0,2 a 0,7. Al relajar, la cuerda la cortaba y lo que sobraba ondulaba la bajada, con radio 0,2. Subiendo recto junto a la cara del palo, la esquina era de 100° y pasaba lo mismo.
- **Resultado** (relajado): sin fallas con 3 y 3 (separación 0,99, curvatura 0,99, estiramiento 1,1 % y penetración 0,03), y también con 2 y 2, 4 y 3, 3 y 4 y 6 y 6. La variante también lleva el ballestrinque de cierre, aunque la especificación no lo muestra.
- **La imagen del error** va junto al paso 5 bien hecho, en la misma escena y con el mismo encuadre. Los ahorcados se ven sobre el palo de arriba, a los dos lados de las vueltas; los dos últimos, en ámbar. No lleva nombres: el error de los otros nudos lleva solo «Firme», y desde el paso 2 el amarre no lo lleva.
- **La especificación** (`specs/amarre-cuadrado.yaml`): 7 pasos con texto propio y `{vueltas}` y `{ahorcados}`, el error y, sin imagen, la cuerda floja mientras se ata (`error.otros`). La verificación pide la tensión: si empujas un palo, no se corre ni gira. Las precauciones piden revisar cada amarre y los palos antes de subirse, y revisarlos otra vez si la construcción queda armada varios días; no hay sección de seguridad ni nada que diga que el amarre no sostiene personas (excepción a D1). Los materiales dicen una cuerda de unos 4 m: la del modelo mide 3,7 m sin los extremos, y Gabriel confirmó al atarlo, el 10 de noviembre, que con 4 m alcanza.
- **El encuadre** es x de −11 a 14 e y de −14 a 10, para los pasos, el error y el terminado. Los restos salen unos 18 diámetros del amarre: en los pasos 5 y 6 su punta queda fuera y no se ve «Chicote».
- **La ficha cabe:** a la página 1 le sobran unos 6 mm (se acortaron los textos de los pasos 1, 2, 4 y 6 para que cada uno ocupe 4 o 5 líneas) y a la 2, unos 26 mm.
- **Nudos publicados:** iguales que en 6151f02, los 3 modelos byte a byte y las 49 imágenes píxel por píxel, con Edge.
- **Filtro 1 (10 de noviembre):** Gabriel revisó y aprobó el texto de la ficha, y ató el amarre con dos palos y cuerda real siguiendo la ficha impresa (e745c28): aprobado, y con 4 m de cuerda alcanza. Queda registrado en la especificación. El filtro 2 sigue en pausa.

#### T7b: Mejoras del render

**Descripción:** mejorar cómo se ven las cuerdas en el visor y en la impresión, empezando por lo que ayuda a leer qué tramo va encima en cada cruce. Pedido de Gabriel el 10 de noviembre de 2026. Las mejoras se deciden con una página de prueba impresa, no mirando la pantalla, y solo entran las que se notan en el papel. En orden de prioridad:

1. **Contorno:** un borde oscuro y fino en cada cuerda, como en los manuales técnicos dibujados. En un cruce, el contorno de la cuerda de encima corta a la de abajo, y eso se lee aun a 58 mm y en gris.
2. **Sombra de contacto:** oscurecer la cuerda de abajo justo donde otra la cruza. Se calcula desde la geometría, para que salga igual cada vez y no dependa de la luz ni del navegador.
3. **Supermuestreo en la impresión:** dibujar cada imagen al doble de resolución y reducirla a 300 ppp, para que los bordes salgan nítidos.
4. **Sombras más suaves:** menos oscuras y de borde más blando, sobre todo la del poste y la de los palos, que oscurecen la mesa.
5. **Nudo terminado apretado:** una geometría aparte, solo para las dos vistas del nudo terminado, con la cuerda ajustada como queda de verdad. Los pasos no cambian. El nudo apretado tiene que tener la misma secuencia de cruces que el último paso y cumplir los mismos límites, y las pruebas lo comprueban.

**Criterios de aceptación:**
- [x] Hay una página de prueba en color y en gris, con las imágenes a su tamaño impreso. Muestra el paso 7 del as de guía, el par del error del ballestrinque, un paso de la vuelta de escota y uno del amarre cuadrado, como están hoy y con cada mejora por separado (`python -m nudos mejoras`; el nudo apretado pasó a T7c).
- [x] Gabriel imprime la página de prueba y elige qué mejoras entran (10 de noviembre: todas menos el contorno).
- [x] La geometría y los cruces de los pasos no cambian, y las pruebas lo comprueban. Así, los filtros 1 ya hechos siguen valiendo (los modelos, byte a byte contra 563bed6).
- [x] Construir dos veces sigue dando las mismas imágenes. Las imágenes nuevas de los nudos ya aprobados quedan como la nueva referencia, y eso queda escrito en `tasks/todo.md`.
- [ ] El visor sigue cargando y girando con fluidez en un celular de gama baja. Medido en la computadora (ver «Cómo se implementaron»); falta abrirlo en el celular.
- [x] Si el nudo apretado necesita un campo en la especificación, queda documentado en `docs/formato-spec.md` antes del Punto de control B (pasó a T7c).

**Verificación:**
- [x] `python -m pytest`
- [x] `python -m nudos imprimir` y `python -m nudos ficha` de cada nudo ya aprobado
- [ ] Manual: imprimir la página de prueba en la Epson y abrir el visor en el celular (la página de prueba, revisada; falta el celular).

**Dependencias:** T7 terminada, porque las dos tocan `render/escena.js`. Va antes de T8 y del Punto de control B: cuantos menos nudos estén aprobados, menos imágenes cambian, y el formato se congela en B.

**Archivos:** `render/escena.js`, `render/impresion.js`, `nudos/imprimir.py`, `nudos/libre.py` o un módulo nuevo para apretar el nudo, `docs/formato-spec.md` si hace falta, y las pruebas correspondientes.

**Tamaño:** M. La mejora 5 es la más cara, porque toca la relajación. Si se complica, se separa en su propia tarea y las otras cuatro siguen. Se separó: es T7c.

**Riesgo:** pulir sin evidencia de un problema de lectura, porque el único filtro 2 hecho pasó con los renders actuales. Por eso la página de prueba decide qué entra.

**Cómo se hizo la página de prueba (10 de noviembre de 2026):** `python -m nudos mejoras` (`nudos/mejoras.py`) construye los cuatro nudos y deja en `build/mejoras/` las imágenes de cada variante y `prueba.pdf`. Son diez hojas carta, una en color y otra en gris por cada imagen, para imprimirlas por las dos caras. Cada hoja pone la misma imagen, a 58 × 64 mm, como sale hoy, con cada mejora sola y con las cuatro juntas. Las imágenes son el paso 7 del as de guía, el par del error del ballestrinque (el paso 5 bien y mal), el paso 4 de la vuelta de escota, donde la delgada pasa bajo sí misma, y el paso 5 del amarre, donde los ahorcados pasan sobre las vueltas.

- **La opción.** Cada imagen lleva sus mejoras en `Imagen.mejoras` (`nudos/imprimir.py`, con los nombres de `MEJORAS`), y la escena las recibe en la opción `mejoras` de `crearEscena` (`render/escena.js`). Las fichas usan `MEJORAS_ACTIVAS`, que hoy está vacía, y el visor no pasa ninguna. Con las mejoras apagadas, los cuatro nudos de `publicados.txt` salen idénticos a `main` (563bed6): los 4 modelos byte a byte y las 67 imágenes de impresión píxel por píxel, con Edge.
- **Contorno (no entró; se quitó del código y queda en da891eb).** Cada malla (cuerdas, tapas y palos) se dibuja otra vez por dentro, engordada a lo largo de sus normales lo justo para que asome un borde de tinta de 0,7 pt (0,25 mm). El borde se adelanta 0,3 diámetros hacia la cámara, para que no lo tape el poste que está justo detrás de la cuerda. Al principio se corría el borde en la pantalla, pero así salía más fino de un lado de la cuerda.
- **Sombra de contacto.** Va como color por vértice. Cada vértice se oscurece hasta un 60 % según lo cerca que tenga el eje de otra cuerda, de un tramo lejano de la misma o de un palo, y según cuánto lo mire. Llega hasta un diámetro. Se calcula en el navegador al armar cada paso, con una rejilla para no comparar todo con todo.
- **Supermuestreo.** El navegador dibuja la página al doble (factor de escala 2) y Pillow la reduce a 300 ppp con Lanczos. Lo hace `nudos/imprimir.py`; la escena no cambia.
- **Sombras suaves.** La mesa se oscurece 0,17 en vez de 0,26 y el sol usa un mapa de sombras de varianza, difuminado, con un borde de 0,45 diámetros en cualquier nudo. Al principio se repartió el sol en 8 luces, pero las sombras salían en copias escalonadas.
- **Para el visor, si se eligen.** El contorno dobla las mallas que hay que dibujar. Las sombras suaves difuminan el mapa de sombras cada vez que se dibuja, así que en el visor habría que actualizarlo solo al cambiar de paso (`shadowMap.autoUpdate = false`): mientras se gira, la escena no cambia. La sombra de contacto solo cuesta al armar cada paso.

**Elección (10 de noviembre de 2026):** Gabriel revisó la página de prueba y eligió la sombra de contacto, el supermuestreo y las sombras suaves. El contorno no entró («me gustaron todos los cambios menos el contorno negro»), así que se quitó del código.

**Cómo se implementaron:**
- **En la impresión.** `MEJORAS` son ahora las tres y `MEJORAS_ACTIVAS` las lleva todas (`nudos/imprimir.py`), así que las imágenes de las fichas salen con ellas. `python -m nudos mejoras` se queda, para volver a mirarlas o probar una nueva: compara las imágenes sin mejoras con cada una y con las tres juntas, que son las de las fichas.
- **En el visor.** `sitio/visor.js` pasa la sombra de contacto y las sombras suaves; el supermuestreo es solo de la impresión, porque en pantalla el lienzo ya sigue la densidad de px. La sombra de la mesa del visor baja como la de la impresión: 0,17 con el tema claro y 0,33 con el oscuro (`sitio/visor.css`).
- **El mapa de sombras se dibuja solo al cambiar de paso** (`shadowMap.autoUpdate = false`), con o sin mejoras: la luz y la cuerda no se mueven al girar la cámara. En el visor, el mapa de las sombras suaves mide 1024 en vez de 2048, para que un celular lo difumine rápido; difuminado, se ve igual.
- **La sombra de contacto se aceleró para el celular.** El eje que oscurece se toma cada 0,25 diámetros (`CONTACTO_MUESTREO`), y cada anillo del tubo junta primero los tramos y los palos que pueden alcanzarlo. En el paso 7 del amarre, el más largo, armar el paso pasó de 335 ms a 37 ms en la computadora de Gabriel; sin la sombra de contacto son 20 ms. Al cambiar de paso, el primer cuadro, que difumina la sombra, sube de unos 6 a unos 15 ms (con el mapa de 2048 de la impresión). Al girar, cada cuadro sigue costando alrededor de 1 ms, con o sin mejoras, porque ya no se redibuja el mapa de sombras.
- **Revisado en el visor** con el navegador de la app, en la computadora y como celular, con los temas claro y oscuro: gira, cambia de paso con las sombras al día y no da errores. Falta abrirlo en un celular de gama baja de verdad, después de publicar.
- **Nueva referencia.** Los modelos de los cuatro nudos aprobados no cambian (byte a byte contra 563bed6), así que los filtros 1 siguen valiendo. Sus imágenes sí cambian, y las que salen desde el commit «T7b: las mejoras elegidas en las fichas y el visor» son la nueva referencia: construir dos veces da las mismas 67 imágenes, píxel por píxel, con Edge. Las cuatro fichas se arman y caben.
- **El nudo terminado apretado se separó en su propia tarea, T7c,** como permitía el tamaño de esta. La relajación de hoy conserva el largo de cada tramo, y apretar el nudo pide tirar de los extremos sin que cambie ningún cruce, con su propia prueba de secuencia y de límites. No está en la página de prueba.

#### T7c: Nudo terminado apretado

**Descripción:** la mejora 5 de T7b, separada el 10 de noviembre de 2026 porque es la más cara. Una geometría aparte, solo para las dos vistas del nudo terminado, con la cuerda ajustada como queda de verdad. Los pasos no cambian. Hoy la relajación conserva el largo de cada tramo, así que hace falta una que tire de los extremos (o acorte la cuerda dentro del nudo) sin que ningún cruce cambie.

**Criterios de aceptación:**
- [x] El nudo apretado tiene la misma secuencia de cruces que el último paso y cumple los mismos límites, y las pruebas lo comprueban, también sobre el poste y en el amarre (que no se aprieta).
- [x] Las dos vistas del nudo terminado salen del nudo apretado; los pasos y sus imágenes no cambian (`TERMINADO_APRETADO = True` desde el 11 de noviembre).
- [x] Construir dos veces da el mismo nudo apretado.
- [x] Si necesita un campo en la especificación, queda documentado en `docs/formato-spec.md` antes del Punto de control B (no lo necesita; «El nudo apretado» explica cómo sale).
- [x] Gabriel compara en papel el terminado de hoy con el apretado y decide si entra (11 de noviembre: entra el apretado).

**Verificación:**
- [x] `python -m pytest`
- [x] `python -m nudos imprimir` de cada nudo ya aprobado
- [x] Manual: imprimir el terminado de hoy junto al apretado (`build/mejoras/apretado.pdf`).

**Dependencias:** T7b, porque toca las mismas imágenes del nudo terminado. Va antes del Punto de control B, porque puede cambiar el formato.

**Archivos:** `nudos/apretar.py` (nuevo), `nudos/construir.py`, `nudos/anfitrion.py`, `nudos/imprimir.py`, `nudos/mejoras.py`, `docs/formato-spec.md`, `tests/test_apretar.py`.

**Tamaño:** M.

**Diseño (10 de noviembre de 2026, antes de implementar; Gabriel lo aprobó el 11 de noviembre).** Se probó en un experimento fuera del repositorio con los tres nudos publicados que no son de plantilla. Los números de abajo salen de ahí.

- **Método: acortar la cuerda dentro del nudo, como si se tirara de sus cabos.** Es el método con que se calculan los nudos apretados (SONO, *shrink on no overlaps*): la cuerda se acorta poco a poco donde está el nudo y, después de cada poco, se deshacen los choques. Así ningún tramo atraviesa a otro y ningún cruce cambia. Se parte del último paso ya relajado.
  - Cada punto de la cuerda pertenece a una de tres partes, según dónde estaba en el último paso:
    - **El nudo:** lo que está a menos de 6 diámetros, sobre la mesa, de algún cruce. Es lo único que se acorta.
    - **La cola:** cada cuerda después de su último cruce, que es su chicote. No se acorta ni se sujeta: conserva el largo que le dio el trazado y el nudo la arrastra.
    - **Lo sujeto:** el resto, como el firme lejos del nudo o la gaza grande del as de guía. Se queda donde está, como si lo sostuvieras con las manos. La cuerda que se quita del nudo es la que sale por ahí, fuera de la imagen.
  - La primera prueba medía la distancia a los cruces a lo largo de la cuerda, no sobre la mesa. Así, en la vuelta de escota, quedaba sujeto el medio de la vuelta que da la delgada por debajo del seno, lejos de los cruces a lo largo de la cuerda pero cerca de ellos en la mesa, y la cuerda se doblaba contra ella con radio 0,53.
  - Se aprieta por rondas. En cada ronda:
    1. **Se acorta.** Cada punto del nudo se acerca al medio entre sus dos vecinos, que es lo que hace una cuerda al tensarla, mientras actúan los choques, la mesa, el poste y el límite de curva. En el nudo la cuerda no puede estirarse; fuera de él conserva su largo.
    2. **Se suelta.** Sin acortar y sin gravedad, se resuelven los choques y la curva. En el nudo la cuerda puede recuperar largo donde lo necesita para no chocar. Sin este paso, la tensión dejaba tramos encimados, a 0,94.
    3. **Se vuelve a muestrear** cada cuerda a paso parejo, como al construir un paso. Cada punto recuerda dónde estaba en el último paso, así que su parte y si va sobre el poste no cambian aunque la cuerda se acorte.
  - Después de cada ronda, la cuerda se comprueba como un paso: la secuencia de cruces del último paso y los mismos límites (sobre el poste, también la penetración). El apretado es la ronda más apretada que los cumple, de 30 como máximo. Si ninguna los cumple, es el último paso tal cual, así que el apretado nunca agrega fallas. No se para en la primera ronda que falla: la curvatura sube y baja unas centésimas de una ronda a otra.
  - Como la cuerda se vuelve a muestrear en cada ronda, la prueba de estiramiento comprueba aquí que los tramos quedaron parejos. El apretado acorta la cuerda a propósito.
  - **Mientras se aprieta, los choques son a 1,12 diámetros.** Una cuerda que abraza a otra del mismo grosor se dobla con radio 1,0, así que un nudo apretado del todo queda al borde del límite de 0,9: en el experimento bajaba a entre 0,78 y 0,86. Con esa holgura, las vueltas quedan con radio de 0,91 o más y el nudo se ve igual de apretado: en una cuerda de 8 mm es 1 mm de luz. La plantilla del amarre hace lo mismo, con 1,08 y 1,1.
  - Un nudo de plantilla no se aprieta: su plantilla ya traza la cuerda tensa.
- **Dónde vive:**
  - `nudos/apretar.py`, nuevo. `apretar(...)` recibe el último paso y devuelve un `Resultado` como el de un paso, sin resaltado y con su propio número de puntos y su propio h. Reusa `_colisiones` y `_limitar_curva` de `nudos/libre.py` sin cambiarlas, y tiene su propia corrección de largo, que en el nudo solo impide que la cuerda se estire o se encoja. `relajar` no cambia.
  - Sobre el poste, `nudos/anfitrion.py` le pasa a `apretar` lo mismo que a `relajar` y a `_resultado`: cómo sacar la cuerda del poste, dónde no cae (cerca del poste no hay gravedad) y cómo buscar los cruces en sus dos mapas.
  - `Modelo` (`nudos/construir.py`) suma `apretado`, el último paso apretado, y `reverso_apretado`, el apretado volteado con `voltear`, como el reverso de hoy. Sus fallas, si las hay, entran en las del nudo. `modelo.json` los lleva aparte, y `pasos` y `error` no cambian, byte a byte.
  - `imprimir.imagenes` saca las dos vistas del terminado del apretado cuando `TERMINADO_APRETADO` es verdadero. Mientras Gabriel decide queda en falso, como `MEJORAS_ACTIVAS` en T7b, así que las fichas no cambian. Si no entra, el código se quita y queda en el historial.
  - El visor no muestra el nudo terminado, así que no cambia y no hay que publicar el sitio.
- **El formato no cambia.** No hace falta ningún campo: qué se aprieta lo deciden los cruces del último paso y el tipo de nudo, y las medidas (6 diámetros, 1,12 y 30 rondas) están en el código. `docs/formato-spec.md` explica en «Nudo terminado» cómo sale el apretado. Si un nudo futuro no debiera apretarse, el campo se agrega con ese nudo: antes del Punto de control B, o después con su migración.
- **Pruebas** (`tests/test_apretar.py`):
  - En el as de guía, el ballestrinque sobre el poste y la vuelta de escota, el apretado tiene la secuencia del último paso y cumple los límites, y su reverso tiene la secuencia invertida.
  - En el as de guía, el nudo se aprieta de verdad: la cuerda mide al menos 5 diámetros menos que en el último paso.
  - Construir dos veces da el mismo apretado, punto por punto.
  - En el amarre, el terminado sigue siendo el último paso y su volteo rígido, como hoy.
  - No se usa una ronda que cambia un cruce: con un nudo pequeño de prueba y una ronda que se hace fallar a propósito, el apretado es la ronda anterior.
  - Los pasos y el error de los cuatro nudos publicados no cambian: sus modelos, byte a byte contra b3ff5ee, como en T7b.
- **Página de prueba:** `python -m nudos mejoras` arma además `build/mejoras/apretado.pdf`. Por cada nudo hay una hoja en color y otra en gris con el terminado, por delante y por detrás, en tres columnas: el de hoy, uno a medias (la mitad de las rondas) y el apretado. Van a su tamaño impreso (58 × 64 mm) y con las mejoras de T7b. La columna a medias está por si el apretado del todo esconde algún cruce. Gabriel elige una de las tres.
- **Qué pasa con cada nudo publicado** (según el experimento):
  - **As de guía:** se aprieta de verdad. Con 30 rondas, la cuerda pasa de 110 a 97 diámetros, la gaza pequeña se cierra sobre el chicote y el collar sobre el firme. Cumple los límites (separación 1,05, curvatura de 0,91 o más y estiramiento de 1,2 % o menos) con los mismos 7 cruces.
  - **Ballestrinque:** casi no cambia, porque cerca del poste la relajación ya deja la cuerda tensa. El firme queda un poco más recto.
  - **Vuelta de escota: es el riesgo.** Apretada del todo conserva los cruces, pero la gruesa queda doblada sobre la delgada con radio de 0,85 a 0,88. Es el caso que ya documenta `docs/formato-spec.md`: una gruesa de 1,5 apoyada sobre una delgada no pasa de 0,83. En el experimento, la curvatura bajaba de 0,9 desde la tercera ronda, así que con la regla de la ronda más apretada que cumple se acortaría solo unos 2 de sus 118 diámetros. Al implementar se prueba una corrección de curva más firme y que la gruesa, que es más rígida, conserve su forma mientras se ajusta la delgada. Si aun así no cumple, queda casi como hoy: los límites no se aflojan.
  - **Amarre cuadrado:** queda como está. La plantilla ya traza la cuerda tensa, con las vueltas y los ahorcados a 1,1 y 1,08 diámetros, más juntos que la holgura del apretado. Por delante sigue siendo el paso 7 y por detrás su volteo rígido.
  - Los filtros 1 siguen valiendo: los pasos no cambian, y el terminado es una vista, no un paso. Si el apretado entra, sus imágenes del terminado pasan a ser la nueva referencia.
- **Costo:** apretar tarda de 5 a 20 segundos por nudo, así que `construir` y las pruebas tardan un poco más.

**Cómo se hizo (11 de noviembre de 2026).** Está como en el diseño (`nudos/apretar.py`, `Modelo.apretado` y `Modelo.reverso_apretado`, el poste en `nudos/anfitrion.py` con `sobre` por coordenada material, `TERMINADO_APRETADO = False` y `tests/test_apretar.py`), con tres cambios que salieron al implementarlo. Los tres están en el docstring de `nudos/apretar.py` y en «El nudo apretado» de `docs/formato-spec.md`.

- **Al soltar, el nudo no tiene corrección de largo.** En el diseño, al soltar se impedía que la cuerda del nudo se encogiera. Así, la cuerda comprimida se pandeaba en dientes de sierra de dos tramos: después de volver a muestrear quedaban tramos de 0,7 h. La curvatura, que se mide cada dos tramos, no lo veía, y la prueba de estiramiento sí. Era el estiramiento de 15,9 % del experimento, no un error al restaurar el estado con dos cuerdas: aquí, en la vuelta de escota, llegó a 50 % entre las rondas 3 y 18. Sin esa corrección, el nudo recupera al soltar el largo que necesita para no chocar, y ninguna ronda de los tres nudos se estira más de 1 %. El as de guía, además, se aprieta más: 94,7 en vez de 96,9.
- **Con cuerdas de distinto grosor, la más gruesa conserva su forma:** lo que tiene en el nudo queda sujeto y solo se acorta la delgada. En la vuelta de escota, la curvatura que fallaba era siempre la de la gruesa al pasar sobre la delgada, de 0,76 a 0,89. Se probó una corrección de curva más firme solo para la gruesa (el radio mínimo por 1,1 y por 1,2, y la corrección tres veces por vuelta), y siguió entre 0,75 y 0,89 en la mayoría de las rondas: solo cumplían de 3 a 5 rondas sueltas. Con la gruesa quieta del todo, la delgada se doblaba demasiado (14 de 30 rondas cumplían). Sin sujetar la gruesa, la ronda 13 cumplía por poco (110,3), pero por detrás la gaza de la gruesa se deformaba. Con la gruesa sujeta, cumplen 23 de 30 rondas y la gaza queda como la de una vuelta de escota de verdad.
- **El nudo por detrás apretado es el reverso de hoy apretado**, con la secuencia invertida, y no el apretado volteado. Voltear el apretado lo relaja con la relajación de los pasos, que choca a 1,0: en el as de guía la cuerda se estiraba 6,9 %, y en la vuelta de escota la gruesa quedaba apoyada sobre la delgada con radio 0,83 (el caso que ya documentaba el formato). Apretar el reverso pasa por la misma guarda, así que tampoco agrega fallas: si ninguna ronda cumple, queda el reverso de hoy.
- **Las partes se deciden una sola vez,** en el último paso, como en el diseño. El experimento medía la distancia a los cruces desde donde estaba la cuerda en cada ronda; con las partes fijas, el as de guía se apretaba igual (110,0 → 96,9 con el soltar del diseño).
- **La guarda** se queda con la ronda más corta entre las que cumplen, de 30 como máximo, y no para en la primera que falla. Si ninguna cumple, `apretar` devuelve el último paso, el mismo objeto, y sus fallas no se cuentan dos veces.

Lo que da cada nudo publicado (largo de la cuerda en diámetros, de hoy al apretado; curvatura mínima del apretado):

| Nudo | Por delante | Por detrás | Rondas que cumplen | Curvatura |
|---|---|---|---|---|
| As de guía | 110,0 → 94,7 | 109,8 → 94,2 | 28 y 30 de 30 | 0,97 y 0,91 |
| Ballestrinque | 62,2 → 62,1 | el mismo nudo, desde el otro lado | 30 de 30 | 1,12 |
| Vuelta de escota | 118,5 → 112,4 | 118,0 → 114,1 | 23 y 27 de 30 | 0,91 y 0,90 |
| Amarre cuadrado | no se aprieta | | | |

En todos, la separación es de 1,05 o más, el estiramiento de 0,9 % o menos y la penetración en el poste de 0,0003. Las rondas que no cumplen fallan solo por curvatura, entre 0,84 y 0,899. Con 30 rondas, la elegida es siempre la última. A medias, con 15, el as de guía queda en 100,2 y 98,6, la vuelta de escota en 114,0 y 114,8, y el ballestrinque igual.

- **Nudos publicados idénticos.** Los cuatro `modelo.json`, sin `apretado` ni `reverso_apretado`, salen byte a byte iguales a los de 52cb117 (el código no cambió desde b3ff5ee). Las imágenes, ver «Elección». Una prueba guarda la huella de los pasos y el error de cada nudo publicado (`test_los_pasos_y_el_error_de_los_nudos_publicados_no_cambian`): si una cambia a propósito, hay que repetir el filtro 1 de ese nudo.
- **Pruebas** (`tests/test_apretar.py`, 19): las del diseño, la de que la gruesa conserva su forma y la de que la guarda no para en la primera ronda que falla. El nudo pequeño es un nudo simple: un trébol abierto con sus tres cruces alternados, que en tres rondas pasa de 69,0 a 68,1 diámetros. La ronda que se hace fallar invierte un cruce al buscarlo. La página de prueba tiene la suya en `tests/test_mejoras.py`.
- **Costo:** apretar tarda de 2 a 7 segundos por vista, así que `construir` tarda de 5 a 13 segundos más por nudo, y la suite, alrededor de un minuto más.
- **Página de prueba:** `python -m nudos mejoras` arma además `build/mejoras/apretado.pdf`: seis hojas, una en color y otra en gris por nudo (as de guía, ballestrinque y vuelta de escota), con el terminado por delante (arriba) y por detrás (abajo), hoy, a medias y apretado, a 58 × 64 mm y con las mejoras de T7b. Cada imagen es como saldría en la ficha, con el encuadre ajustado a su cuerda, y su pie dice cuánta cuerda se quitó del nudo.
**Elección (11 de noviembre de 2026):** Gabriel imprimió la página de prueba y eligió el apretado, con las 30 rondas («Apretado»).

**Cómo entró:**
- `TERMINADO_APRETADO = True` (`nudos/imprimir.py`): las dos vistas del terminado de las fichas salen del apretado. La página de prueba se queda, con la primera columna como «Sin apretar», para volver a mirarla. La prueba de que dos cuerdas se dibujan con su color (`tests/test_cuerdas.py`) dibuja ahora el último paso sin resaltado, como antes: en su nudo sintético, apretado, la vuelta de la delgada se cierra sobre la gruesa y quedaba menos crema que su mínimo.
- **Nueva referencia.** Desde el commit «T7c: las fichas llevan el nudo apretado», las imágenes del terminado del as de guía, el ballestrinque y la vuelta de escota son las nuevas. De las 67 imágenes de impresión de los cuatro nudos publicados (con las de su página de prueba), cambian solo las 6 del terminado y sus 6 copias en gris; las otras 55 salen iguales a las de 52cb117, píxel por píxel, con Edge. Construir dos veces da los mismos `modelo.json`, byte a byte, y las mismas imágenes del terminado. Las cuatro fichas se arman y caben. Los pasos, el error y el visor no cambian, así que no hubo que publicar el sitio ni repetir los filtros 1.
- **El script de comparación de imágenes no veía diferencias.** `comparar.py`, el de T7b (fuera del repositorio), comparaba las imágenes en RGBA, y con Pillow 13 `getbbox()` solo mira el canal alfa, que es opaco en todas. Así, decía «iguales» aunque no lo fueran. Las comparaciones «píxel por píxel» hechas con él, en T7b y en la primera de T7c, no comprobaban nada. Ahora se compara en RGB. Los modelos byte a byte sí valían, y también `test_dibujar_dos_veces_da_las_mismas_imagenes`, que compara los bytes de los archivos.
- **Una variación rara al dibujar.** En la primera de tres construcciones, `error.png` del ballestrinque salió con 25 píxeles distintos, en 1 nivel de 255. En las otras dos y en cuatro dibujos sueltos salió igual a la de 52cb117. No viene de la geometría, porque su modelo es idéntico: es del navegador.

#### T8: Plantilla de la cabeza de turco

**Descripción:** crear una plantilla de cabeza de turco alrededor de un cilindro, parametrizada por cabos y senos, con los pasos del método clásico.

**Criterios de aceptación:**
- [ ] El tejido alterna encima y debajo correctamente sobre el cilindro, según la prueba de cruces.
- [ ] Cambiar el número de cabos o senos regenera el modelo.
- [ ] El nudo pasa los dos filtros.

**Verificación:**
- [ ] `pytest -k cabeza_de_turco`
- [ ] `python -m nudos construir cabeza-de-turco`
- [ ] Manual: filtros 1 y 2.

**Dependencias:** T5

**Archivos:** `nudos/plantillas/cabeza_turco.py`, `specs/cabeza-de-turco.yaml`, `tests/test_cabeza_de_turco.py`. Con el diseño de abajo, además: `nudos/plantillas/pasos.py`, `nudos/anfitrion.py`, `nudos/spec.py`, `nudos/imprimir.py`, `nudos/hoja.py`, `render/escena.js` y `docs/formato-spec.md`.

**Tamaño:** M, no S. Son una plantilla y un anfitrión nuevos, como en T7.

**Diseño (11 de noviembre de 2026, antes de implementar; Gabriel lo aprobó el mismo día con las cuatro propuestas del final).** Las referencias son `entradas/cabeza-de-turco/` (27 imágenes: una de tres cabos tejida alrededor de una tabla, que se gira mientras se teje, y triplicada) y la página 26 del manual de la Tropa (una de tres cabos y cinco senos atada plana sobre la mesa, doblada y pasada después a un objeto cilíndrico). Los números salen de un experimento fuera del repositorio con la cuerda ideal sobre el tubo, sin relajar y sin los extremos.

- **El nudo, sobre el tubo desenrollado.** Si se mira la superficie del tubo desenrollada (a lo largo del eje y alrededor), la cuerda va de un borde al otro y vuelve, como una onda.
  - Da tantas vueltas al tubo como cabos, hace tantos senos en cada borde como senos y se cruza senos × (cabos − 1) veces. Con 3 cabos y 4 senos son 3 vueltas, 4 senos de cada lado y 8 cruces.
  - Los cruces alternan encima y debajo a lo largo de toda la cuerda.
  - Cabos y senos no pueden tener un divisor común aparte del 1. Si lo tienen, salen dos o más cuerdas cerradas y no un nudo de una sola cuerda: con 3 cabos no se puede hacer con 3 ni con 6 senos.
  - Con más pasadas, cada cabo lleva varias cuerdas paralelas que hacen lo mismo, y cada cruce de cabos pasa a ser pasadas × pasadas cruces: 32 con 3 × 4 y dos pasadas.
- **Método: cada vuelta va en su lugar definitivo.** La plantilla teje la cuerda vuelta por vuelta, y cada vuelta pasa por encima o por debajo de lo que ya está, como queda en el nudo terminado. Con 3 cabos, sean cuantos sean los senos, salen los pasos del método clásico de tres cabos:
  1. La primera vuelta no cruza nada.
  2. La segunda cruza la primera siempre por encima: 3 veces con 4 senos.
  3. La tercera teje por debajo, por encima, por debajo… (5 cruces con 4 senos) hasta llegar junto al comienzo.
  4. Cada pasada más sigue el mismo camino junto a la primera, siempre del mismo lado: por encima donde ella va por encima y por debajo donde va por debajo.
  5. Se esconden los chicotes.

  Así cada paso es el comienzo de la cuerda entera, como en el amarre, y un cruce conserva su etiqueta en todos los pasos.
  - En las fotos de `entradas/` se dan dos vueltas casi paralelas y después se cruzan entre sí al trenzar. El manual la ata plana y al final la pasa al tubo. En los dos casos, entre un paso y otro cambian cruces que ya estaban, o la forma entera, y aquí cada cambio sería un cruce nuevo con otra etiqueta. Tejiendo vuelta por vuelta sale el mismo nudo sin mover lo que ya está atado.
  - Con otro número de cabos se teje igual, alternando con lo que ya está, pero la segunda vuelta ya no va toda por encima: con 4 cabos y 5 senos, por ejemplo, pasa por encima y después por debajo. La plantilla lo construye igual. El texto de los pasos se escribe para las medidas de la especificación.
- **El tubo:** un anfitrión nuevo, `tipo: tubo`, con `radio` y `largo`. Es un cilindro horizontal a lo largo de x, centrado en x = 0 y con el eje en y = 0. Se parece al poste, con dos diferencias:
  - Se apoya sobre el nudo, que lo rodea entero. Debajo de cada cruce hay dos capas de cuerda, así que su eje queda a la altura radio + 2 (el del poste está a radio + 1).
  - Se gira en la mano: en cada paso, la plantilla gira el nudo alrededor del eje para que lo que agrega el paso quede de frente (ver «Escena»).
  - El poste y la cruz no cambian.
  - El radio mínimo depende de las medidas (ver «Geometría»). Propuesta: radio 4. Con un cordón de 4 mm es un tubo de 3,2 cm, y con uno de 3 mm, de 2,4 cm, el grosor de un anillo de pañoleta.
- **Formato:**

  ```yaml
  anfitrion: {tipo: tubo, radio: 4, largo: 24}
  plantilla:
    tipo: cabeza-de-turco
    cabos: 3
    senos: 4
    pasadas: 2
  pasos:
    - {titulo: Da la primera vuelta, texto: …, hasta: vuelta-1}
    - {titulo: Cruza por encima, texto: …, hasta: vuelta-2}
    - {titulo: Empieza a tejer, texto: …, hasta: vuelta-3-mitad}
    - {titulo: Termina de tejer, texto: …, hasta: vueltas}
    - {titulo: Sigue el mismo camino, texto: …, hasta: pasadas}
    - {titulo: Esconde los chicotes, texto: …, hasta: remate}
  ```

  - `cabos` va de 2 a 5, `senos` de 2 a 7, sin divisor común con `cabos` aparte del 1, y `pasadas` de 1 a 3. Otra cosa es un error al cargar.
  - `hasta` puede ser, en este orden: `vuelta-1-mitad`, `vuelta-1`, … `vuelta-<cabos>-mitad`, `vuelta-<cabos>` (la primera pasada, por medias vueltas), `pasada-2-mitad`, `pasada-2`, … `pasada-<pasadas>` y `remate`. `vueltas` es lo mismo que la última vuelta y `pasadas` que la última pasada, como `vueltas` y `ahorcados` en el amarre. Cada paso llega más lejos que el anterior y el último llega a `remate`.
  - En el texto, `{cabos}`, `{senos}` y `{pasadas}` salen en letras.
  - Ningún paso tiene firme: el extremo corto se sujeta contra el tubo y se trabaja con la parte larga, que lleva «Chicote» en su punta en todos los pasos. Los dos extremos llevan remate, como en el amarre.
  - Cambiar cabos, senos o pasadas es cambiar un número: la cuerda, los cruces, los pasos y las imágenes se regeneran. El texto sí puede tener que cambiar, porque «cruza por encima tres veces» depende de los senos.
- **Geometría:** la plantilla calcula una sola vez la parte de la cuerda que va sobre el tubo, desde donde entra el extremo corto hasta el chicote, en coordenadas del tubo: posición a lo largo, ángulo y distancia al eje.
  - **El camino** del centro de cada cabo es una onda hecha de arcos de circunferencia. Redondea los senos más que una sinusoide del mismo ancho: en el experimento, con un radio casi del doble. Las pasadas van paralelas, a 1,1 diámetros, del mismo lado de la primera.
  - **La altura.** En cada cruce, la cuerda de encima va 1 diámetro más lejos del eje que la de debajo, que va apoyada en el tubo. Sobre una banda de varias pasadas sigue arriba todo lo que dura la banda, más 0,6, y entre un cruce y el siguiente sube o baja con una curva suave.
  - **El ancho de la onda** lo elige la plantilla según el radio del tubo. A media altura entre los bordes, las cuerdas forman un ángulo con la dirección en que se rodea el tubo. Es el menor entre 45° y 70°, de 5 en 5, con el que la cuerda ideal queda a 1 diámetro de las demás y con un radio de curvatura de al menos 1,2. Con más ángulo, la onda es más ancha y hay más cuerda entre un cruce y el siguiente, así que cabe en un tubo más delgado, pero las cuerdas se cruzan más cerradas. Si no cabe ni con 70°, la falla dice el radio mínimo para esas medidas.

    | Cabos × senos y pasadas | Radio mínimo | Con radio | Ángulo | Ancho del nudo | Cuerda en el nudo | Cruces |
    |---|---|---|---|---|---|---|
    | 3 × 4, una | 2 | 4 | 45° | 5,4 | 105 | 8 |
    | 3 × 4, dos | 2,75 | 4 | 60° | 8,2 | 227 | 32 |
    | 3 × 4, tres | 4 | 5,5 | 60° | 11,4 | 443 | 72 |
    | 3 × 5, dos | 3,5 | 5 | 60° | 8,1 | 275 | 40 |
    | 3 × 5, tres | 5,25 | 6,5 | 65° | 11,6 | 531 | 90 |

    El ancho y la cuerda están en diámetros; la cuerda no incluye los extremos. Con el radio de la tercera columna, la curvatura mínima de la cuerda ideal es de 1,3 a 1,8. Con 4 cabos y 5 senos, con una pasada y radio 4, no cabe con ningún ángulo: con más cabos hay cruces cerca de los senos, más juntos a lo largo de la cuerda, y hace falta un tubo más grueso.
  - **Los extremos** salen del nudo por un mismo seno de un borde. El extremo corto llega desde fuera del nudo, a lo largo del tubo, y entra por la cuerda de más afuera de ese seno. Al final de cada pasada, antes de llegar a donde empezó la anterior, la cuerda se corre a la siguiente por dentro de ese seno, así que no cruza el extremo corto. Ahí es donde hay menos lugar: entre el último cruce y el seno tienen que caber el paso de una pasada a la siguiente y el final del chicote. Es lo que en el amarre fueron las esquinas.
  - **El remate:** cada extremo se mete por debajo de la banda de al lado, entre el nudo y el tubo, y queda escondido. La plantilla escribe esos cruces. Es el único paso en que cambia el extremo corto, que en los demás cuelga hasta la mesa.
  - **Cada paso** es el comienzo de esa cuerda hasta su `hasta`, girado para que quede de frente, más el extremo corto y el resto, que salen del nudo y caen a la mesa. Los dos se trazan en cada paso, porque por dónde caen depende del giro.
  - Después se pasa la curva suave, se muestrea cada 0,2 diámetros y se relaja como el amarre: sin gravedad, con choques entre tramos y sin entrar en el tubo más de 0,05 ni estirarse.
  - Un nudo de plantilla no se aprieta (T7c): la plantilla ya traza la cuerda tensa.
  - `nudos/plantillas/pasos.py` hoy sirve solo al amarre, porque usa la cruz y sus mapas. Pasa a pedirle a cada plantilla su sólido, su cuerda y sus mapas, sin que cambie lo que da el amarre.
- **Cruces sobre el tubo:** como sobre el poste, en la superficie desenrollada del tubo, comparando cada par en la vuelta más cercana; encima es lo más lejos del eje.
  - Hay dos zonas: el tubo, con la parte tejida, y la mesa, con el extremo corto y el resto hasta que llegan al nudo. Los cruces entre zonas no se buscan; ahí solo se comprueba la separación, como entre el poste y la mesa.
  - La plantilla escribe la secuencia del método. Alterna por cabos a lo largo de la cuerda, y cada pasada hace lo mismo que la primera. Las etiquetas se numeran en el orden en que se forma cada cruce, así que un cruce conserva la suya en todos los pasos.
  - Esa secuencia se compara con la que se mide en la cuerda relajada, como en los nudos libres. Es la prueba de que el tejido alterna bien sobre el tubo, el primer criterio de aceptación. Las pruebas comprueban además, para varias medidas, que la secuencia de la plantilla alterna por cabos y tiene senos × (cabos − 1) × pasadas² cruces, más los del remate.
  - Cada cruce guarda su lugar en el mapa del tubo, a lo largo y alrededor, y no en la mesa. Como el nudo se gira entre pasos, en la mesa un mismo cruce se movería, y la heurística del cruce que salta lo tomaría por otro.
- **Error común:** una variante del método, como en el amarre. Propuesta: `empieza-por-encima`.
  - En la tercera vuelta, la cuerda empieza a tejer por encima en vez de por debajo y sigue alternando. Es el error más fácil de cometer, porque la segunda vuelta fue toda por encima. Todos los cruces de la tercera vuelta quedan al revés y el nudo no se traba.
  - Se ve desde `vuelta-3-mitad`. Se construye y se comprueba como un paso más, con el mismo giro y el mismo encuadre que el paso bien hecho.
  - Sin imagen (`error.otros`) irían dos más: que la segunda pasada cambie de lado o se monte sobre la primera, y apretar de una vez tirando de un chicote, que deforma el nudo. Se aprieta de a poco, siguiendo la cuerda.
- **Nudo terminado:** por delante, el último paso. Por detrás, el tubo y el nudo girados media vuelta alrededor del eje. Es un giro rígido, como el volteo del amarre: la secuencia no cambia y no se relaja de nuevo. Entre las dos vistas se ve el nudo entero, también la parte que en la vista de los pasos queda contra la mesa.
- **Escena:**
  - El tubo es un cilindro de madera, como el poste.
  - **El giro de cada paso.** Lo que agrega el paso, o su última media vuelta si es más largo, queda centrado en la cara del tubo que mira la cámara. La cámara de los pasos mira desde arriba y algo por delante, a unos 40° de la vertical. Como el tubo se ve igual girado, en la imagen solo gira la cuerda. El texto dice cuándo girar el tubo: hacia ti, porque la cuerda pasa por encima del tubo hacia el fondo.
  - Nombres: solo «Chicote», en la punta de la parte larga.
- **Hoja de revisión:** sobre el tubo, la vista desde arriba no sirve para revisar 32 cruces. La hoja dibuja además el tubo desenrollado con cada cruce y su etiqueta, que es donde se ve si el tejido alterna.
- **Ficha** (con 3 cabos, 4 senos y dos pasadas):
  - 6 pasos, todos en la página 1. Con tres pasadas son 7, como en el amarre.
  - El error, junto al paso 3 bien hecho, y el terminado, por delante y girado.
  - Materiales, por confirmar al atarlo: un cordón de 3 o 4 mm y unos 1,5 m, y un tubo o un palo redondo de unos 3 cm de grosor. Cuanto más grueso el cordón, más grueso tiene que ser el tubo.
  - Familia nueva: Decorativos. Usos: anillo para sujetar la pañoleta, y adorno o agarre en un bastón o un mango.
  - No lleva sección de seguridad, porque no sostiene nada. En las precauciones: si sellas los chicotes con fuego, el nylon derretido quema.
- **Lo que no cambia:** el generador libre, el poste, la cruz y la plantilla del amarre. Los cuatro nudos de `publicados.txt` tienen que dar los mismos `modelo.json`, byte a byte, y las mismas imágenes, comparadas en RGB, que en 80e3619. Esa referencia ya está construida, fuera del repositorio.
- **Riesgos:**
  1. Los extremos, por lo apretado que queda el seno por donde salen. Si no caben, el extremo corto entra a media diagonal, lejos de los cruces, o se agranda el tubo, mirando las imágenes. Los límites no se aflojan.
  2. Sobre un tubo liso, los senos de las primeras vueltas pueden correrse hasta que la tercera vuelta los traba. El texto pide sujetarlos con el pulgar. El filtro 1 dirá si alcanza o si conviene un tubo que agarre más, como uno de cartón.
  3. Que se lean 32 cruces en una imagen de 58 × 64 mm. Por eso cada paso pone de frente lo que agrega. Con tres pasadas serían 72.
- **Lo que decidió Gabriel (11 de noviembre): las cuatro propuestas.**
  1. El método es tejer vuelta por vuelta. No se trenza como en las fotos ni se ata plana como en el manual, porque las dos cambian cruces entre pasos.
  2. Las medidas son 3 cabos, 4 senos y dos pasadas, sobre un tubo de radio 4 (unos 3 cm), con 6 pasos. No se usan 3 y 5, como en el manual, ni tres pasadas, como en las fotos.
  3. El error con imagen es empezar a tejer la tercera vuelta por encima (`empieza-por-encima`). Van también los dos errores sin imagen: que la segunda pasada cambie de lado o se monte sobre la primera, y apretar de una vez tirando de un chicote.
  4. El terminado va sobre el tubo: por delante, y por detrás girado media vuelta. No se muestra el anillo solo, sin el tubo.

**Cómo se hizo el formato (11 de noviembre de 2026):** como en el diseño, con estos detalles.
- **El tubo** (`anfitrion: {tipo: tubo, radio, largo}`) solo va con una plantilla, como la cruz: sin ella es un error al cargar. Su largo tiene que ser mayor que su grosor.
- **La plantilla** es `CabezaDeTurco`, en `nudos/plantillas/cabeza_turco.py`. Lee `cabos`, `senos` y `pasadas` con los límites del diseño. Si cabos y senos tienen un divisor común, el mensaje dice cuántas cuerdas cerradas saldrían. En el texto, `{pasadas}` con una sola pasada es «una».
- **La variante depende de las medidas.** `VARIANTES` es una propiedad: `empieza-por-encima` existe con tres cabos, y con otro número no hay ninguna, porque la segunda vuelta ya alterna. Si una especificación pide un error con esas medidas, el mensaje dice que la plantilla no sabe construir ningún error común.
- **La combinatoria del camino del centro** también está ahí (`cruces_del_centro`, `encima_del_centro` y `por_vuelta`), porque la variante la necesita. No depende del radio ni de la forma de la onda. Confirma lo del experimento: con 3 cabos y 2, 4, 5 o 7 senos, la segunda vuelta va toda por encima y la tercera empieza por debajo; con 4 cabos y 5 senos, la segunda va por encima y después por debajo.
- **Hay cruces justo al completar una vuelta**, donde la cuerda vuelve al lugar donde empezó: pasa cuando cabos divide a 2k + m, con k la vuelta y m las vueltas entre las dos pasadas. Con 3 × 4, el cruce de la segunda vuelta con la primera que está justo ahí es de la vuelta que termina. Por eso cada vuelta se cuenta hasta volver al comienzo, incluido, y el fin de una vuelta como hito no puede caer justo ahí (lo decide la geometría). Con la cuenta al revés, la segunda vuelta de 3 × 4 daba «OO» y la tercera «OUOUOU».
- **Nudos publicados:** iguales que en 80e3619, los 4 modelos byte a byte y las 67 imágenes en RGB, con Edge. En la primera impresión, `error-correcto.png` de la vuelta de escota salió con 15 píxeles distintos en 1 nivel, mientras la suite dibujaba a la vez; impresa otra vez, salió igual. Es la variación rara del navegador de T7c.

**Cómo se hizo la geometría (11 de noviembre de 2026):** con el diseño, salvo lo que sigue. Está en `nudos/plantillas/cabeza_turco.py` (`Cuerda`), el tubo en `nudos/anfitrion.py` (`Tubo`) y las pruebas en `tests/test_cabeza_de_turco.py`. Falta que Gabriel lo revise en las imágenes, con la escena.
- **El extremo corto entra a media diagonal, no en el ápice del seno A.** Es la salida que el diseño dejaba para el riesgo 1. Con radio 4, entre el último cruce antes de A y su ápice quedan unos 3,5 diámetros alrededor del tubo (P / 6), y la banda de ese cruce ocupa más de uno. Ahí no caben el paso de una pasada a la siguiente (que necesita unos 3 para correrse 1,1 sin doblarse de más), el final del chicote y la curva del extremo corto. Ahora el extremo corto llega desde fuera del nudo, a lo largo del tubo, y entra a la primera pasada en el brazo que sale de A, 2 diámetros antes de su primer cruce. Así el paso a la pasada siguiente pasa sobre el ápice: empieza 0,6 después del último cruce y termina 2,8 antes del primero. Con tres pasadas, la banda es más ancha y todo se corre 0,8 más lejos de los cruces.
- **El chicote** termina 1,1 después del último cruce antes de A. Con 3 × 4 ese cruce es por debajo, así que la punta queda bajo la banda que cruza. El paso de `pasadas` termina antes, a media diagonal, y el remate agrega ese último cruce: el paso 5 tiene 30 cruces y el remate 34.
- **El remate del extremo corto.** En vez de colgar, el extremo corto vuelve por encima del ápice de A, por fuera del borde, cruza la muesca entre A y el seno vecino y se mete por debajo de la banda que baja de ese seno, a media distancia entre su ápice y el cruce (a 1,5 d de A, con d = P / 6). Son dos cruces más, uno por pasada. Esa banda va levantada sobre él desde el primer paso, así que el extremo corto es lo único que cambia en el remate: el cuerpo, con sus alturas, es el mismo con el extremo que cuelga y con el metido. No encontré un lugar más cerca: junto al ápice todas las cuerdas van apoyadas en el tubo, entre dos cruces que no dejan lugar para levantar una banda sobre el extremo, y junto al primer cruce después de A el extremo tendría que volver sobre sí mismo. Queda a la vista el tramo que cruza la muesca, por fuera del borde del nudo. Es lo primero que conviene mirar en las imágenes.
- **Los hitos** caen entre dos pasadas por cruces, en el medio: en un ápice o a media diagonal, lejos de los cruces, porque ahí sale el resto. La vuelta se cuenta hasta volver al comienzo, incluido (ver «Cómo se hizo el formato»). La última vuelta de cada pasada, menos la última pasada, termina donde empieza el paso a la siguiente. Con 3 × 4 y dos pasadas, los pasos de la especificación forman 0, 3, 3, 2, 22 y 4 cruces.
- **Las alturas** van por cada cruce de dos carriles: la de encima sigue arriba 0,6 más allá del eje de la de abajo, a lo largo de la cuerda, y las mesetas de los carriles de una banda se juntan. Es lo mismo que el experimento, pero medido a lo largo de la cuerda y no alrededor del tubo. Por eso la cuerda ideal de 3 × 4 con dos pasadas en radio 4 ya cumple con 55° (curvatura 1,26) y no con 60°, como decía la tabla del diseño: el experimento medía las mesetas en arco alrededor del tubo, que en una diagonal es más largo, y le quedaban más cerca. La plantilla sigue la regla del diseño y elige 55°. Los pasos cumplen igual con 60°.
- **Lo que cae a la mesa** se traza en cada paso, con el giro. El extremo corto que cuelga, si sale por la mitad de arriba del tubo, gira suave por la superficie hacia el costado que baja y cae en un cuarto de circunferencia que se aleja del tubo; si sale por la de abajo, sigue a lo largo del tubo mientras baja. El resto se aleja 2,2 del tubo en 3 diámetros siguiendo la cuerda, lo rodea hacia atrás y cae detrás del tubo. Al principio caía derecho, y vista desde arriba esa caída es un punto: al relajar aparecían cruces falsos.
- **Los cruces del tubo** se buscan en su superficie desenrollada y guardan su lugar en el mapa del nudo. Ese lugar da la vuelta a C / (4 senos), entre dos cruces: los cruces caen siempre en múltiplos de C / (2 senos) alrededor del tubo, también justo debajo de A, y cortando ahí un cruce saltaba 28 diámetros. Dos pasadas a menos de 3 diámetros a lo largo de la cuerda no cuentan como cruce (`CRUCE_MIN`): no pueden serlo, y salían donde la cuerda cae casi vertical al costado del tubo.
- **`nudos/plantillas/pasos.py`** construye los pasos de las dos plantillas igual y le pide a cada una su sólido, su cuerda y cómo buscar sus cruces (`geometria`). El amarre da el mismo `modelo.json`, byte a byte. `Resultado` y `modelo.json` llevan además el giro de cada paso de la cabeza de turco.
- **Resultado** con 3 cabos, 4 senos y dos pasadas en radio 4 (55°): los 6 pasos sin fallas, con separación de al menos 1,00, curvatura de al menos 1,15, estiramiento de hasta 0,8 % y nada dentro del tubo. El error, igual (curvatura 1,15). Construir el nudo tarda unos 30 segundos. Sin fallas también con 3 × 4 con una pasada (45°) y con tres (radio 5,5), 2 × 3 y 3 × 2 con dos pasadas, y 2 × 5, 4 × 5 (radio 6) y 3 × 7 (radio 6) con una.
- **Pendiente: 3 × 5 con dos pasadas no sale**, ni con radio 5, 5,5 ni 6. Su último cruce antes de A es por encima, así que la banda del seno vecino pasa por debajo de él y no le queda lugar para levantarse sobre el extremo corto. Habría que meterlo más lejos, al otro lado del ápice del seno vecino. Se deja para después de que Gabriel revise el remate en las imágenes, porque puede cambiar.

**Cómo se hizo la escena, la impresión y la hoja (11 de noviembre de 2026):** con el diseño, más estos detalles. Falta que Gabriel lo revise en las imágenes.
- **El tubo.** La escena lo dibuja con los datos de `Tubo.datos()`, de madera como el poste, a lo largo de x y centrado en x = 0, y el alto del encuadre lo incluye. El visor y la impresión usan la misma escena.
- **Las vistas.** Los pasos, el error y el terminado van en la vista de los pasos. Por delante, el terminado es el remate, girado como ese paso; por detrás, `Tubo.voltear` gira el tubo y el nudo media vuelta alrededor del eje: un giro rígido, que no se relaja ni se comprueba otra vez y suma 180° al giro. La ficha dice «Por detrás es como lo ves si giras el tubo media vuelta».
- **Los nombres.** Solo «Chicote», en la punta de la parte larga, y los dos extremos con remate, como desde el paso 2 del amarre.
- **El encuadre** va en la especificación: x de −7 a 11 e y de −9 a 9, el nudo con el tubo y el comienzo de lo que cae a la mesa. Lo que cae detrás del tubo sigue 3 diámetros por la mesa, y su punta queda fuera del encuadre en casi todos los pasos. El terminado, sin nada que cuelgue, se ve más grande.
- **La hoja de revisión** (`python -m nudos hoja cabeza-de-turco`) lleva, debajo de la de siempre, el tubo desenrollado de cada paso (`mapa` en `nudos/hoja.py`), desde el seno A, con cada cruce y su etiqueta. Lo que va más lejos del eje se dibuja encima y más oscuro, y lo que agrega el paso, en ámbar.
- **La especificación** (`specs/cabeza-de-turco.yaml`) tiene los 6 pasos, el error y los dos errores sin imagen, con texto provisional: falta el de la ficha.
- **Visto en las imágenes:** en el remate se resalta solo lo que agrega el chicote. El extremo corto metido, que es lo que más cambia, va azul, porque cada paso resalta un solo tramo de la cuerda. Se arregla según lo que decida Gabriel del remate.
- **Nudos publicados:** iguales que en 80e3619, los 4 modelos byte a byte y las 67 imágenes en RGB, con Edge. Una vez, `paso-1.png` del amarre salió con 20 píxeles distintos en 1 nivel mientras se construía otro nudo a la vez; impresa sola, salió igual. Construir la cabeza de turco dos veces da el mismo `modelo.json`, byte a byte.

**Lo que dijo Gabriel al revisar (11 de noviembre de 2026):** no entendió el nudo tejido de esta manera, y duda que un tubo más grueso, con los dos extremos en el seno A, lo arregle. Ya presentó el avance en la junta del grupo. Decidió dejar la cabeza de turco para el final: se sigue con el resto del plan y se vuelve a ella cuando todo lo demás esté terminado. Al volver, conviene empezar por ver con él qué parte no se entiende en las imágenes, antes de tocar la geometría. Lo hecho queda en `main` (formato, geometría, escena, impresión y hoja, con sus pruebas), y la nota de traspaso está fuera del repositorio, con las demás notas de las sesiones. Mientras tanto, `specs/cabeza-de-turco.yaml` sigue en `specs/` con texto provisional, y `construir_sitio` construye todas las especificaciones de esa carpeta: antes de la próxima publicación del sitio hay que dejarla fuera.

#### Punto de control B: después de T7 y T8

- [x] Los nudos del piloto están publicados, sin la cabeza de turco. (11 nov: Gabriel la dejó para el final; los otros cuatro ya están publicados.)
- [x] El formato de especificación queda congelado como v1 en `docs/formato-spec.md`. A partir de aquí, un cambio incompatible necesita un script de migración (ver abajo).
- [x] Revisión contigo antes de automatizar. (11 nov: Gabriel aprobó las tres propuestas de abajo.)

**Cómo se preparó (11 de noviembre de 2026; Gabriel aprobó las tres propuestas el mismo día):** el punto de control se cierra con los cuatro nudos publicados, sin la cabeza de turco.
- **El formato v1** está en `docs/formato-spec.md`, en «Versiones». Precisa qué cambio necesita migración.
  - Un cambio compatible agrega algo que ninguna especificación usa todavía, como un anfitrión, una plantilla o un campo opcional. Las especificaciones anteriores dan el mismo `modelo.json`, byte a byte, así que no hay nada que migrar: la versión sube a 1.1, 1.2…
  - Un cambio incompatible cambia algo que ya existe. Lleva un script de migración que reescribe todas las especificaciones en el mismo commit, y la versión sube a 2.
  - Lo que traen T10 (`estado`), T12 (`secciones`) y las tandas 3 a 5 (anfitriones y plantillas nuevos) son cambios compatibles. Sin esta distinción, cada anfitrión nuevo de la fase 4 llevaría un script de migración sin nada que migrar.
- **La cabeza de turco queda provisional:** el tubo, la plantilla y su variante pueden cambiar sin migración hasta que se publique, porque solo los usa su especificación.
- **Para dejarla fuera del sitio**, el sitio lleva solo los nudos de `publicados.txt`. `construir_sitio` construye esas especificaciones, y no todas las de `specs/`.
  - Publicar un nudo ya es agregarlo a `publicados.txt`: es el último paso de cada nudo. Hoy, en cambio, un nudo nuevo de `specs/` sale en línea con la siguiente publicación del sitio, y su dirección no está protegida hasta que alguien lo agrega a la lista.
  - No espera a T10 ni cambia el formato. El estado de T10 no alcanza solo: el ballestrinque, la vuelta de escota y el amarre están en línea sin el filtro 2, así que no llegan a `publicado`, y el sitio tendría que llevar también estados anteriores, como el de la cabeza de turco.
  - Para ver un nudo nuevo en el sitio antes de publicarlo, `python -m nudos sitio --con <slug>` lo agrega al sitio local. `scripts/publicar.sh` no usa esa opción.
  - Cambian `nudos/exportar.py`, `nudos/__main__.py`, `tests/test_sitio.py`, `CLAUDE.md`, `README.md` y el comentario de `publicados.txt`. La geometría y las pruebas de la cabeza de turco no se tocan.
  - **Cómo se hizo (11 nov):** `nudos_del_sitio`, en `nudos/exportar.py`, dice qué nudos lleva el sitio. Falla si falta la especificación de un nudo de `publicados.txt`. Con `--con cabeza-de-turco`, el sitio sale idéntico al de 378e9d4, archivo por archivo. Sin la opción, solo falta la cabeza de turco: su carpeta y su línea en `index.html` y `404.html`. Los nudos publicados quedan iguales a 378e9d4: los 4 modelos byte a byte y las 67 imágenes en RGB, con Edge. En la primera impresión salieron unos píxeles distintos en 1 nivel en `error.png` de la vuelta de escota, y salieron iguales al imprimirla otra vez. En la referencia, `prueba/paso-7-arriba.png` del amarre tenía 2 píxeles distintos en 1 nivel: impresa otra vez desde 378e9d4, salió igual que ahora. Es la variación rara del navegador de T7c. En la suite, 341 pruebas: falló una vez `test_con_mejoras_dibujar_dos_veces_da_lo_mismo`, que dibuja la misma imagen dos veces, por esa misma variación, y pasó al correr sola.

### Fase 3: el paso de IA y la operación

#### T9: Skill nudo-nuevo

**Descripción:** crear una skill de Claude, guardada en la cuenta de Gabriel y con su fuente en el repositorio, que toma la carpeta de entrada de un nudo (imágenes, descripción y enlace a la fuente) y hace lo siguiente:
- Elige el tipo de generador.
- Escribe el borrador de la especificación.
- Construye el modelo.
- Produce una hoja de revisión privada, con la fuente junto a los renders y la secuencia de cruces de cada paso.

La skill no copia texto de la fuente ni publica imágenes de la fuente.

**Criterios de aceptación:**
- [x] Pruebas doradas: a partir de las entradas originales del as de guía y de la vuelta de escota, la skill produce especificaciones con las mismas secuencias de cruces ya validadas. (12 nov: con el criterio que decidió Gabriel; la vuelta de escota, con la lectura que Gabriel aceptó como el mismo nudo.)
- [x] Con un nudo nuevo, el ocho, el borrador construye y pasa la validación automática, y tus correcciones quedan registradas. (12 nov: sin correcciones.)
- [x] La hoja de revisión queda en `revision/`, fuera de git.

**Verificación:**
- [x] `pytest tests/test_dorados.py`
- [x] Manual: ejecutar la skill con las entradas del ocho y revisar la hoja.

**Dependencias:** Punto de control B

**Archivos:** `skills/nudo-nuevo/SKILL.md`, `docs/formato-spec.md`, `nudos/revision.py`, `tests/test_dorados.py`. Con el diseño de abajo, la skill va en `.claude/skills/nudo-nuevo/SKILL.md`, y además: `nudos/__main__.py` y `tests/dorados/`.

**Tamaño:** M

**Diseño (12 de noviembre de 2026, antes de implementar; Gabriel lo aprobó el mismo día con las cuatro propuestas del final).**

- **Dónde vive la skill:** en `.claude/skills/nudo-nuevo/SKILL.md`, dentro del repositorio. El plan decía `skills/nudo-nuevo/`, con una copia guardada en la cuenta de Claude. Claude Code carga solas las skills de `.claude/skills/` en cada sesión que trabaja en el repositorio, también en un worktree. Así no hay que subirla ni mantener dos copias, y cada cambio de la skill queda en git junto al código que usa.
- **Qué hace** `/nudo-nuevo <slug>`, en este orden:
  1. Lee `entradas/<slug>/`: las imágenes y `info.txt` o `fuente.md`. Son entrada: no copia su texto ni sus imágenes a ninguna parte del repositorio.
  2. Elige el generador: libre, con una cuerda o varias; sobre un anfitrión que ya existe (hoy, el poste), o con una plantilla que ya existe (hoy, la del amarre cuadrado). Si el nudo necesita un anfitrión o una plantilla que no existe, se detiene y lo dice, porque eso es una tarea de código, como T5 o T7, y no un borrador.
  3. Lee las imágenes paso a paso y escribe `specs/<slug>.yaml` con `estado: borrador`: los segmentos, los pasos con su secuencia, el error común, el terminado y el texto de la ficha, en tuteo, propio y sin términos de ninguna sección. Sigue `docs/formato-spec.md` y usa los nudos publicados como ejemplo.
  4. Construye con `python -m nudos construir <slug>` y corrige la geometría hasta que no queden fallas. Si la secuencia medida no coincide con la declarada, vuelve primero a la imagen y no ajusta la secuencia para que coincida: un cruce mal leído es el error que las pruebas no ven.
  5. Arma la hoja de revisión con `python -m nudos revision <slug>` y se detiene para que Gabriel la revise. El nudo sigue en `borrador`: pasa a `modelado` cuando Gabriel lo aprueba.
- **La hoja de revisión** (`nudos/revision.py`) es una página HTML en `revision/<slug>/`, que ya está fuera de git. Por cada paso pone, lado a lado, las imágenes de la fuente que le corresponden, el paso dibujado desde arriba y a 55°, y la secuencia declarada junto a la medida. La skill anota en `revision/<slug>/pasos.yaml` qué imágenes de la fuente usó en cada paso. La página enlaza las imágenes de `entradas/`, sin copiarlas.
- **Las pruebas doradas** (`tests/test_dorados.py`): la skill corre sobre las entradas del as de guía y de la vuelta de escota, y sus borradores se guardan en `tests/dorados/`. La prueba los carga, los construye sin fallas y compara la secuencia de cada paso con la de la especificación validada. No importa cómo se llaman los cruces: los dos se renumeran en el orden en que aparecen. También compara los cruces del error común.
  - La prueba no corre la skill, porque la skill es Claude leyendo imágenes. Comprueba lo que la skill produjo la última vez: cuando la skill cambia, se corre otra vez y se guardan los borradores nuevos.
  - Para que la corrida sea a ciegas, la hace una sesión nueva en un worktree sin `specs/as-de-guia.yaml` ni `specs/vuelta-de-escota.yaml`. Si no, la skill podría copiarlos.
  - Si la skill divide los pasos de otra manera que la especificación validada, la prueba falla, y Gabriel decide si la división nueva es mejor.
  - Los borradores dorados llevan el texto que escribió la skill, que es propio, como el de cualquier especificación.
- **El ocho** es el primer nudo nuevo. La skill escribe su borrador y Gabriel revisa la hoja. Sus correcciones se anotan aquí, en T9: qué cruce o qué texto cambió y por qué. Lo que se repita pasa a la skill como regla, para que el borrador siguiente no lo repita. El ocho sigue después con la tanda 1: su filtro 1 y su publicación son de esa tanda.
- **Lo que no cambia:** el formato, porque la skill escribe v1.1; los nudos publicados, y la cabeza de turco.
- **Preguntas para Gabriel:**
  1. ¿La skill va en `.claude/skills/nudo-nuevo/`, en vez de en `skills/` y subida a tu cuenta?
  2. ¿La corrida dorada la hace una sesión nueva en un worktree sin las dos especificaciones validadas? Es la manera que veo de que sea a ciegas.
  3. ¿Los borradores dorados se guardan en git, en `tests/dorados/`?
  4. ¿Tus correcciones del ocho se anotan en el plan, y las que se repitan pasan a la skill como reglas?
- **Lo que decidió Gabriel (12 de noviembre): las cuatro propuestas.** La skill va en `.claude/skills/nudo-nuevo/`; la corrida dorada la hace una sesión nueva en un worktree sin las dos especificaciones validadas; los borradores dorados van en git, en `tests/dorados/`, y sus correcciones del ocho se anotan aquí, y las que se repitan pasan a la skill.

**Cómo se hizo la hoja, la comparación y la skill (12 de noviembre de 2026):** con el diseño, más estos detalles. Faltan la corrida dorada y el ocho.
- **La hoja de revisión** (`python -m nudos revision <slug>`, `nudos/revision.py`) construye el nudo, guarda su `modelo.json` y arma `revision/<slug>/index.html`. Necesita el modelo en memoria y no solo `modelo.json`, porque ahí está la secuencia declarada además de la medida. Cada paso se dibuja con `nudos/hoja.py`, desde arriba y a 55°, y una secuencia distinta sale en rojo, como las fallas, arriba. Las imágenes de la fuente se enlazan con una ruta relativa, o con su dirección completa si están en otra unidad. En un worktree las entradas no están, y `NUDOS_ENTRADAS` dice dónde buscarlas. Sin `pasos.yaml`, la página muestra arriba todas las imágenes de la fuente. Probada con el as de guía y sus 8 imágenes de `entradas/`.
- **`datos_json`** (`nudos/construir.py`) es el contenido de `modelo.json`, aparte de `guardar`, que lo escribe. La hoja lo usa para dibujar cada paso como la hoja de siempre.
- **La comparación** de las pruebas doradas está en `nudos/dorados.py`: `renumerar` numera los cruces en el orden en que aparecen, y `diferencias` dice en qué difiere un borrador de la especificación validada: el número de pasos, las cuerdas, la secuencia de cada paso, cómo se reparten los cruces entre las cuerdas y el error común. `tests/test_dorados.py` la prueba con el as de guía y la vuelta de escota con otras etiquetas, un cruce al revés, un paso menos y otro error. Las pruebas de los borradores dorados se agregan con ellos.
- **La skill** (`.claude/skills/nudo-nuevo/SKILL.md`) sigue los pasos del diseño: leer la fuente, elegir el generador, decidir los pasos, leer los cruces, trazar, el error y el texto, construir y corregir, y la hoja con su informe. Tiene una sección para la corrida dorada y otra, vacía todavía, para las reglas que salgan de las correcciones de Gabriel.
- **Nudos publicados:** iguales a 378e9d4, los 4 modelos byte a byte (con `datos_json`) y las 67 imágenes en RGB, con Edge, y el sitio igual. Pasan las 371 pruebas.

**El ocho, el primer borrador de la skill (12 de noviembre de 2026):** `specs/ocho.yaml`, en `borrador`, con su hoja en `revision/ocho/`. Falta que Gabriel lo revise.
- **Lo que leí.** Tres pasos: una vuelta con el chicote por encima del firme (imágenes 1 y 2), el chicote por debajo del firme (imágenes 5 y 3, que van en otro orden que sus números) y el chicote por la vuelta, que entra por encima y sale por debajo (imagen 4, el nudo ya ajustado). No hay imagen del chicote entrando a la vuelta, así que los cruces 3 y 4 los leí en el nudo terminado. La secuencia del último paso, `2O 1U 4O 3U 1O 2U 3O 4U`, alterna, como el ocho. Fuera del repositorio comprobé con los 3-coloreos que es un ocho y no un nudo simple.
- **El error común** es el que advierte la fuente: meter el chicote por la vuelta de abajo hacia arriba, con los cruces 3 y 4 al revés. Con los 3-coloreos, sale un nudo simple. Ninguna imagen lo muestra.
- **Construir** salió sin fallas al primer intento: separación de al menos 0,99, curvatura de 1,13 y estiramiento de hasta 1,3 %. La ficha se arma y cabe, sin términos de ninguna sección.
- **Lo que cambió al usar la skill.** La hoja de revisión mostraba las secuencias como las numera la construcción, en el orden en que aparecen los cruces, y no con las etiquetas de la especificación. Ahora usa las de la especificación, que son las que se comparan de un paso a otro. A la skill le agregué que las imágenes se ordenan por lo que muestran y no por el nombre del archivo, que un paso sin imagen se lee en el nudo terminado y que un cruce se amplía en una copia fuera de `entradas/`. `python -m nudos estado` dice ahora que a un borrador con todo el texto le falta la revisión de Gabriel. Las pruebas de T10 ya no suponen qué nudos tienen especificación.
- **Nudos publicados:** los 4 modelos, iguales a 378e9d4 byte a byte. Pasan las 372 pruebas; se saltan las de construir la cabeza de turco y el ocho, que son borradores.

**La corrida dorada (12 de noviembre de 2026):** la hizo una sesión nueva, en un worktree sin las dos especificaciones validadas. Sus borradores están en su rama, `claude/competent-aryabhata-2dc24a` (commit 4aa97d2, `tests/dorados/`), y todavía no en `main`. Los dos construyen sin fallas. La comparación (`nudos/dorados.py`) la hizo después la sesión de `main`, leyendo los borradores desde ese worktree:
- **As de guía:** el nudo terminado y el error común son idénticos a los validados, y cada paso del borrador tiene la secuencia de un paso validado. Solo cambia la división: 5 pasos en vez de 7. El borrador no tiene «Acerca el chicote», que no forma cruces, ni el paso intermedio «Vuelve por encima».
- **Vuelta de escota:** 5 pasos en vez de 4, porque el borrador tiene dos pasos sin cruces al comienzo. La gruesa cruza igual, pero la delgada cruza las dos piernas del seno en el orden contrario. Es el lugar donde la sesión anotó su duda: ahí se tapan las tres cuerdas. Falta saber si es el mismo nudo dibujado de otra manera o uno equivocado. La comparación de los dos nudos terminados está en `revision/dorados/vuelta-de-escota-comparada.png`, fuera de git.
- **Una fuga:** un script de diagnóstico de esa sesión, corrido desde fuera de su worktree, importó el `nudos` de A: y cargó la vuelta de escota validada. Vio que tiene 4 pasos y el error en el 4, pero no sus secuencias. Su borrador ya tenía 5 pasos y el error en el 5, y después solo cambió la geometría.
- **Lo que le faltó a la skill,** según esa sesión: cómo separar una cuerda que pasa justo sobre un cruce (dos lecturas dan la misma cuerda real y secuencias distintas); que en un worktree un script que no corre con `-m` desde su raíz usa el `nudos` de A:; que las fallas digan dónde ocurren y que la hoja dibuje el reverso; de dónde sacar el error común si la fuente no lo trae, y si va un paso de preparar la cuerda, sin cruces.
- **Lo que decidió Gabriel (12 de noviembre):** las pruebas doradas no exigen la misma división de los pasos, porque esa es una decisión de cómo enseñar el nudo y no de cómo leer los cruces. Exigen que cada paso del borrador sea un paso validado, en el mismo orden; que cada cruce sea siempre el mismo cruce validado; el mismo nudo terminado y el mismo error común. Después dijo que la vuelta de escota del borrador es el mismo nudo que la validada y que los dos borradores vienen a `main`.
- **Cómo se hizo:** `diferencias` (`nudos/dorados.py`) compara así, con pruebas para otra división de los pasos, un paso de más sin cruces, pasos en otro orden, un cruce que cambia de nombre entre pasos y otro error. Con ese criterio, el borrador del as de guía no tiene diferencias. El de la vuelta de escota difiere en el último paso, y por eso también en el error común.
- **Lo que le faltó a la skill, corregido:** en `nudos/libre.py`, las fallas de separación y de estiramiento dicen cerca de qué punto ocurren, como ya lo decía la de curvatura. La hoja de revisión dibuja el nudo terminado por detrás. La skill avisa del `nudos` de A: en los scripts de un worktree, dice qué hacer con una cuerda que pasa justo sobre un cruce y de dónde sacar el error común cuando la fuente no lo trae. Queda para Gabriel si va un paso de preparar la cuerda, sin cruces.
- **Nudos publicados:** iguales a 378e9d4, los 4 modelos byte a byte y las 67 imágenes en RGB, con Edge, y el sitio igual. Pasan las 377 pruebas.
- **Los borradores en `main`** (12 nov, con permiso de Gabriel): el commit de la corrida, solo con `tests/dorados/`, entró con `cherry-pick` (8cdee59). `tests/test_dorados.py` comprueba que los dos construyen sin fallas y los compara con las especificaciones validadas. El as de guía no tiene diferencias. La vuelta de escota tiene las tres que Gabriel aceptó, porque es el mismo nudo, y se exigen tal cual (`ACEPTADAS`): cualquier otra, o que una de ellas desaparezca, hace fallar la prueba.
- **El paso de preparar la cuerda** (Gabriel, 12 nov): sí va. El primer paso prepara la cuerda, sin cruces. Está en la skill, en «Decide los pasos».
- **El ocho** (Gabriel, 12 nov): «todo bien», sin correcciones. Pasa a `modelado`. Su filtro 1 y su publicación son de la tanda 1.
- **La suite:** pasan 383 pruebas; se salta la de construir la cabeza de turco, que es un borrador. Desde la última comparación no cambió el código que construye e imprime los nudos publicados.

#### T10: Estado de producción y registro de pruebas

**Descripción:** agregar a la especificación el campo de estado y el registro de los dos filtros. Cada prueba guarda la fecha, el rol del probador y un código anónimo, para no repetir probador en un nudo que ya conoce. Generar una tabla con el estado de los 35 nudos.

**Criterios de aceptación:**
- [x] `python -m nudos estado` muestra los 35 nudos con su estado y qué los bloquea.
- [x] Una prueba impide marcar un nudo como `publicado` si no tiene los dos filtros registrados.
- [x] El registro solo acepta roles y códigos, no nombres.

**Verificación:**
- [x] `pytest tests/test_estado.py`
- [x] `python -m nudos estado`

**Dependencias:** T4

**Archivos:** `nudos/spec.py`, `nudos/estado.py`, `tests/test_estado.py`. Además, `config/edicion-1.yaml`, `nudos/ficha.py`, `nudos/__main__.py`, las cuatro especificaciones publicadas y `docs/formato-spec.md`.

**Tamaño:** S

**Cómo se hizo (11 de noviembre de 2026):**
- **El campo `estado`** es opcional, y sin él una especificación está en `borrador`. Así es un cambio compatible del formato, que pasa a v1.1 sin migración. El as de guía está en `publicado`; el ballestrinque, la vuelta de escota y el amarre, en `cuerda-ok`; la cabeza de turco no lo lleva, así que es un borrador, porque su texto es provisional.
- **Qué pide cada estado** está en `docs/formato-spec.md`, en «Estado». `modelado` pide lo que la ficha necesita de la especificación (`faltan_textos`, que ahora usa también `nudos/ficha.py`), y que construya sin fallas. `cuerda-ok` y `novato-ok` piden que el último registro de su filtro esté aprobado. `publicado` pide además estar en `publicados.txt`. Estar en el sitio no basta para estar en `publicado`: los tres nudos sin filtro 2 están en línea y siguen en `cuerda-ok`.
- **Lo comprueban `nudos/estado.py` y `tests/test_estado.py`,** no la carga de la especificación. Si una prueba no pasa, el nudo sigue construyendo y se puede corregir; lo que falla es la suite, y `python -m nudos estado` dice qué falta. Las pruebas construyen sin fallas los nudos de `modelado` o más, con los modelos de `conftest.py` cuando los hay. La orden no los construye, porque con 35 nudos tardaría minutos; hoy tarda menos de un segundo.
- **Los 35 nudos** están en `config/edicion-1.yaml`, por tanda, con el slug de su carpeta en `entradas/`. Una prueba comprueba que son 35, sin repetir, y que cada especificación y cada nudo publicado están en la lista.
- **Los probadores.** El registro ya aceptaba solo el rol y un código desde T4: no hay campo `nombre`, y el código es como P01. El rol es texto libre que describe a la persona sin nombrarla. La orden lista cada código con los nudos que ya probó, y el estado marca como problema que un mismo código repita el filtro 2 de un nudo: si no pasa, se repite con otra persona.
- **Nudos publicados:** iguales a 378e9d4, los 4 modelos byte a byte y las 67 imágenes en RGB, con Edge; el sitio, igual que sin T10. En la suite, 361 pruebas: falló una vez `test_dibujar_dos_veces_da_las_mismas_imagenes` y pasó al correr sola. Es la variación rara del navegador, que hoy salió en las dos corridas de la suite, cada vez en una prueba distinta de las que dibujan dos veces lo mismo.

#### Punto de control C: después de T9 y T10

- [x] Las pruebas doradas pasan, y un nudo nuevo salió de la skill con correcciones menores. (12 nov: el ocho, sin correcciones.)
- [ ] Decidir si se usan subagentes en paralelo para los borradores de la tanda 1.

### Fase 4: producción de los 30 nudos restantes

Cada nudo es una tarea pequeña con la misma definición de terminado. Se trabaja por tandas agrupadas por tipo de generador, para reutilizar lo construido en el piloto.

| Tanda | Tipo | Nudos |
|---|---|---|
| 1 | Libres, una cuerda | simple, ocho, ocho doble, as de guía español, mariposa alpina, margarita, arnés de hombre, silla de bombero (requiere D1) |
| 2 | Libres, dos cuerdas o dos extremos | rizo, pescador, nudo aguja (el del manual de la Tropa) |
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
| Pescador | 2 | `pescador` |
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
- [ ] Los 35 nudos están en `publicado` y todos sus QR responden.
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
| El proyecto no cierra porque no hay fecha | Medio | La edición 1 se define como los 35 nudos; tabla de estado; puntos de control con revisión |

## Preguntas abiertas

- **D3 y D8:** las decisiones previas que siguen abiertas.
- **D7:** si la dirigencia de la Tropa participa en la revisión de su anexo y en conseguir probadores.

## Lo que se reutilizó del prototipo

El prototipo del as de guía se portó completo y la carpeta `prototipo/` se borró al cerrar T3. Sigue en el historial de git:

- **`knot.py`:** el generador libre (trazado, cruces, elevación a 3D, relajación y validación). Pasó a `nudos/` en T1.
- **`render.py`:** el render de verificación en numpy. Pasó a `nudos/hoja.py` en T1.
- **`viewer.template.html` y `build_viewer.py`:** la escena three.js y el visor. Pasaron a `render/escena.js` y `sitio/` en T2.
- **`shoot.py`:** el render con Chrome sin interfaz. Pasó a `nudos/imprimir.py` en T3.
