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
8. **El flujo se opera desde la app de Claude,** en conversaciones del proyecto Scouts y con la computadora de Gabriel vinculada.
   - GitHub es la fuente de verdad. Cada sesión empieza clonando el repositorio y termina subiendo los cambios y actualizando la copia en `A:\`.
   - Una skill de Claude, `nudo-nuevo`, contiene el procedimiento, y su fuente vive en el repositorio.
   - No hace falta Claude Code.
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
  skills/           fuente de la skill nudo-nuevo (se guarda en la cuenta de Claude)
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

#### Punto de control 2: después de T5 y T6

- [ ] El anfitrión y las dos cuerdas funcionan.
- [ ] Si el anfitrión no da resultados confiables, los enganches de la tanda 3 pasan a plantillas y se replanifica la fase 4.

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

**Archivos:** `nudos/plantillas/cabeza_turco.py`, `specs/cabeza-de-turco.yaml`, `tests/test_cabeza_de_turco.py`

**Tamaño:** S

#### Punto de control B: después de T7 y T8

- [ ] Los 5 nudos del piloto están publicados.
- [ ] El formato de especificación queda congelado como v1 en `docs/formato-spec.md`. A partir de aquí, cualquier cambio necesita un script de migración.
- [ ] Revisión contigo antes de automatizar.

### Fase 3: el paso de IA y la operación

#### T9: Skill nudo-nuevo

**Descripción:** crear una skill de Claude, guardada en la cuenta de Gabriel y con su fuente en el repositorio, que toma la carpeta de entrada de un nudo (imágenes, descripción y enlace a la fuente) y hace lo siguiente:
- Elige el tipo de generador.
- Escribe el borrador de la especificación.
- Construye el modelo.
- Produce una hoja de revisión privada, con la fuente junto a los renders y la secuencia de cruces de cada paso.

La skill no copia texto de la fuente ni publica imágenes de la fuente.

**Criterios de aceptación:**
- [ ] Pruebas doradas: a partir de las entradas originales del as de guía y de la vuelta de escota, la skill produce especificaciones con las mismas secuencias de cruces ya validadas.
- [ ] Con un nudo nuevo, el ocho, el borrador construye y pasa la validación automática, y tus correcciones quedan registradas.
- [ ] La hoja de revisión queda en `revision/`, fuera de git.

**Verificación:**
- [ ] `pytest tests/test_dorados.py`
- [ ] Manual: ejecutar la skill con las entradas del ocho y revisar la hoja.

**Dependencias:** Punto de control B

**Archivos:** `skills/nudo-nuevo/SKILL.md`, `docs/formato-spec.md`, `nudos/revision.py`, `tests/test_dorados.py`

**Tamaño:** M

#### T10: Estado de producción y registro de pruebas

**Descripción:** agregar a la especificación el campo de estado y el registro de los dos filtros. Cada prueba guarda la fecha, el rol del probador y un código anónimo, para no repetir probador en un nudo que ya conoce. Generar una tabla con el estado de los 35 nudos.

**Criterios de aceptación:**
- [ ] `python -m nudos estado` muestra los 35 nudos con su estado y qué los bloquea.
- [ ] Una prueba impide marcar un nudo como `publicado` si no tiene los dos filtros registrados.
- [ ] El registro solo acepta roles y códigos, no nombres.

**Verificación:**
- [ ] `pytest tests/test_estado.py`
- [ ] `python -m nudos estado`

**Dependencias:** T4

**Archivos:** `nudos/spec.py`, `nudos/estado.py`, `tests/test_estado.py`

**Tamaño:** S

#### Punto de control C: después de T9 y T10

- [ ] Las pruebas doradas pasan, y un nudo nuevo salió de la skill con correcciones menores.
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
