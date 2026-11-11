# Tareas: Libro de nudos del Grupo 431

El detalle de cada tarea (criterios, verificación y archivos) está en `tasks/plan.md`.

## Decisiones previas

- [x] D1 Postura de seguridad: ningún nudo sostiene, sube ni baja personas en actividades; la práctica con personas solo con instructor y equipo certificados
- [x] D2 Carta, resorte e imprenta (consecuencias en el plan)
- [ ] D3 Leyenda de los símbolos ✓, + y ★ de la Tropa (antes de T12)
- [x] D4 GitHub Pages en la cuenta personal (`Gaboelc`), repositorio público
- [x] D5 Se trabaja desde la app de Claude con la computadora vinculada
- [ ] D8 Especificaciones de la imprenta: sangrado, color y formato (antes de T13)

## Fase 1: el as de guía de principio a fin

- [x] T1 Repositorio y especificación v0 con el as de guía
- [x] Repositorio público `Gaboelc/nudos-431` creado y T1 subida
- [x] T2 Escena 3D compartida y visor publicado en su URL permanente (M, depende de T1 y del repositorio)
  - [x] Escena compartida, página del visor, `python -m nudos sitio`, `publicados.txt` y pruebas
  - [x] Revisado en Chrome de escritorio y en celular emulado, sin errores ni pedidos fuera del sitio
  - [x] Sitio subido a la rama `gh-pages`
  - [x] Gabriel activa GitHub Pages: Settings → Pages → Deploy from a branch → `gh-pages` / `(root)`
  - [x] La dirección responde y el visor carga en Chrome como celular, sin errores
  - [x] Gabriel abre https://gaboelc.github.io/nudos-431/as-de-guia/ en su celular y revisa los 7 pasos
- [x] Punto de control 1: la especificación reproduce el prototipo y el visor está en línea
- [x] T3 Imágenes de impresión, error común y vistas finales (M, depende de T2)
  - [x] Error común y nudo terminado en la especificación, con sus pruebas (`tests/test_errores.py`)
  - [x] `python -m nudos imprimir`: 11 imágenes a 300 ppp desde la escena del visor, idénticas al construir dos veces
  - [x] Resaltado del paso 2 movido para que el error se vea: el firme llega azul al cruce
  - [x] `prueba.pdf`: página de prueba en color y en escala de grises
  - [x] Gabriel imprime `prueba.pdf` en la Epson a tamaño real y revisa que se distinga qué tramo va encima (aprobada, con los pasos en 3D)
  - [x] Publicar el sitio: el resaltado del paso 2 cambió
  - [x] Borrar `prototipo/` (queda en el historial de git)
- [x] T4 Ficha impresa del as de guía con QR (M, depende de T3, D1 y D2)
  - [x] Texto de la ficha en la especificación: para qué sirve, materiales, verificación y seguridad
  - [x] Plantilla `libro/`, `python -m nudos ficha` y QR vectorial al visor; pliego de dos páginas carta con margen de resorte
  - [x] Prueba de vocabulario (`config/terminos_seccion.txt`) y pruebas de la ficha
  - [x] Gabriel revisa el texto de la ficha: aprobado, sin la frase del 9-1-1 en seguridad (va solo en el material inicial)
  - [x] Gabriel imprime la ficha y escanea el QR
  - [x] Filtro 1: Gabriel ata el as de guía paso a paso con cuerda real, siguiendo la ficha impresa (7 nov)
  - [x] Filtro 2: alguien que nunca lo ha hecho lo ata solo con la ficha impresa (7 nov, P01)
  - [x] Registrar los dos filtros en la especificación (campo `filtros`)
- [x] Punto de control A:
  - [x] La suite pasa, también desde un clon limpio en un entorno nuevo (76 pruebas)
  - [x] El as de guía pasó los dos filtros
  - [x] Decisión entre three.js y Blender para la impresión: se queda three.js
  - [x] Revisión contigo: la ficha se queda como está, con el espacio libre de la página derecha; los nudos de más de 6 pasos se resuelven en T7

## Fase 2: piloto por tipo de nudo

- [ ] T5 Objeto anfitrión con el ballestrinque sobre poste (M, depende de T4; es el mayor riesgo técnico)
  - [x] El poste en la especificación (`anfitrion`, segmentos `{poste: [[x, ángulo], ...]}`) y en la relajación, sin que la cuerda lo atraviese
  - [x] Cruces sobre la superficie desenrollada del poste (`nudos/anfitrion.py`)
  - [x] `specs/ballestrinque.yaml`: 5 pasos con el chicote, error común y texto de la ficha; pruebas en `tests/test_ballestrinque.py`
  - [x] El poste en la escena, el visor y la ficha; el nudo terminado se mira desde el otro lado
  - [ ] Gabriel revisa el texto de la ficha
  - [x] Filtro 1: Gabriel lo ata paso a paso con cuerda real y un palo, siguiendo la ficha impresa (9 nov)
  - [ ] Filtro 2: alguien que nunca lo ha hecho lo ata solo con la ficha impresa (en pausa desde el 9 nov)
  - [ ] Registrar los filtros en la especificación
- [ ] T6 Dos cuerdas con la vuelta de escota (M, depende de T4; puede ir en paralelo con T5)
  - [x] Diseño escrito en el plan (formato, geometría, color, escena); falta implementarlo
  - [x] Formato con `cuerdas` y trazado y secuencia por cuerda, con sus pruebas (`tests/test_spec.py`)
  - [x] Geometría de varias cuerdas: cortes, radio por punto, separación por suma de radios (`tests/test_cuerdas.py`)
  - [x] Escena, impresión, hoja y ficha con dos cuerdas; nudos de una cuerda idénticos píxel por píxel (38 imágenes del as de guía y del ballestrinque, con Edge)
  - [x] `specs/vuelta-de-escota.yaml` y `tests/test_vuelta_de_escota.py`: 4 pasos, error común (el chicote por encima de sí misma) y texto de la ficha; la ficha cabe en el pliego
  - [ ] Gabriel revisa el texto de la ficha
  - [x] Gabriel imprime la ficha (`python -m nudos ficha vuelta-de-escota`) y la revisa (9 nov, ficha 9ec2271)
  - [x] Filtro 1: Gabriel la ata paso a paso con dos cuerdas reales de distinto grosor, siguiendo la ficha impresa (9 nov)
  - [ ] Filtro 2: alguien que nunca lo ha hecho lo ata solo con la ficha impresa (en pausa desde el 9 nov)
  - [x] Registrar el filtro 1 en la especificación
  - [x] Publicar el sitio: la vuelta de escota es nueva y el visor cambió (9 nov, construido desde d352483; revisado en línea)
- [ ] T6b Alternativas y precauciones en la página y la ficha (S, pedido de Gabriel el 9 nov; antes del Punto de control B)
  - [x] Campos `alternativas` y `precauciones` en el formato, con sus pruebas; sin ellos no hay ficha
  - [x] En la ficha (página 2, las tres caben) y en el visor, debajo de los pasos, con para qué sirve, materiales y seguridad
  - [x] Texto propio del as de guía, el ballestrinque y la vuelta de escota (en los dos últimos, el aviso de que se afloja pasó de «usos» a «precauciones»)
  - [ ] Gabriel revisa el texto de los tres nudos
  - [x] Publicar el sitio con «Sobre el nudo» (9 nov, construido desde 9ec2271, a pedido de Gabriel antes de su revisión)
- [x] Punto de control 2: el anfitrión funciona; si no, los enganches pasan a plantillas (aprobado el 9 nov: el ballestrinque y la vuelta de escota pasaron el filtro 1; los enganches siguen con el anfitrión)
- [ ] T7 Plantilla del amarre cuadrado (M, depende de T5)
  - [x] Diseño escrito en el plan (palos, formato, geometría, cruces, escena y ficha)
  - [x] Gabriel aprueba el diseño y responde las cuatro preguntas del final (9 nov: cierre arriba, inicio en un paso, error sin imagen por la tensión, los amarres sí sostienen personas)
  - [x] Formato: anfitrión `cruz`, `plantilla`, pasos con `hasta` y `error` con `variante` y `otros`, con sus pruebas (`nudos/plantillas/`, `tests/test_amarre_cuadrado.py` y `tests/test_spec.py`; nudos publicados idénticos: 3 modelos byte a byte y 49 imágenes píxel por píxel, con Edge)
  - [x] Geometría: la cuerda entera, los pasos como prefijos, la relajación con los dos palos y los cruces por zonas (`nudos/plantillas/amarre.py`, `trazo.py` y `pasos.py`, `tests/test_amarre_cuadrado.py`; 7 pasos sin fallas y 40 cruces con 3 y 3, también con 2 y 2, 4 y 3, 3 y 4 y 6 y 6; las vueltas van en el orden de las referencias y, delante, por fuera del ballestrinque: ver «Cómo se hizo la geometría» en el plan)
  - [x] Gabriel revisa en las imágenes el orden de las vueltas y las vueltas por fuera del ballestrinque de inicio (con la escena) (10 nov: aprobados, con el volteo del terminado; pidió que la cuerda no se viera rígida)
  - [x] Escena, impresión y ficha con los dos palos y el reverso volteado; nudos publicados idénticos (modelos byte a byte, imágenes píxel por píxel) (10 nov: `Cruz.voltear`, la cruz en `render/escena.js`, «Firme» solo en el ballestrinque de inicio, remate en los dos extremos y `error.otros` en la ficha; 3 modelos y 49 imágenes iguales, con Edge; ver «Cómo se hizo la escena» en el plan. La ficha del amarre se arma cuando estén el error construido y el texto)
  - [x] La cuerda abraza los palos: esquinas y ahorcados rehechos (10 nov, a pedido de Gabriel: las esquinas bajan pegadas a las caras de los dos palos y los ahorcados son vueltas tensas; el mismo método y los mismos 40 cruces; sin fallas con 3 y 3, 2 y 2, 4 y 3, 3 y 4 y 6 y 6; nudos publicados idénticos; ver «Cómo se hizo la geometría» en el plan)
  - [x] Gabriel revisa el antes y el después de la cuerda que abraza los palos (10 nov: aprobado)
  - [x] Error común construido: los ahorcados por encima del palo de arriba, como variante de la cuerda, construidos y comprobados como un paso más, junto al paso 5 en la impresión (10 nov: los mismos 38 cruces que el paso 5; sin fallas con 3 y 3, 2 y 2, 4 y 3, 3 y 4 y 6 y 6; ver «Cómo se hizo el error y la especificación» en el plan)
  - [x] `specs/amarre-cuadrado.yaml`: pasos, error común y texto de la ficha; la ficha cabe; de 3 a 4 vueltas regenera los pasos (10 nov: 7 pasos, error y la cuerda floja sin imagen, encuadre; ficha de dos páginas que cabe; nudos publicados idénticos contra 6151f02)
  - [x] Gabriel revisa el texto de la ficha (10 nov: aprobado; al atarlo, Gabriel confirmó que con 4 m de cuerda alcanza)
  - [x] Filtro 1: Gabriel lo ata con dos palos y cuerda real, siguiendo la ficha impresa (10 nov, ficha e745c28; con 4 m de cuerda alcanza)
  - [x] Registrar el filtro 1 en la especificación
  - [x] Publicar el sitio con el amarre cuadrado (10 nov, construido desde 7bcb14c, con el amarre en `publicados.txt`; revisado en línea)
- [ ] T7b Mejoras del render (M, pedido de Gabriel el 10 nov; después de T7 y antes de T8)
  - [x] Página de prueba en color y en gris: hoy contra cada mejora por separado y las cuatro juntas (10 nov: `python -m nudos mejoras`, `build/mejoras/prueba.pdf`, diez hojas; contorno, sombra de contacto, supermuestreo y sombras suaves, detrás de `Imagen.mejoras` y de la opción `mejoras` de la escena, apagadas; nudos publicados idénticos a 563bed6: 4 modelos byte a byte y 67 imágenes píxel por píxel, con Edge; 244 pruebas pasan; ver «Cómo se hizo la página de prueba» en el plan. El nudo terminado apretado pasó a T7c)
  - [x] Gabriel revisa la página de prueba y elige qué mejoras entran (10 nov: la sombra de contacto, el supermuestreo y las sombras suaves; el contorno no, y se quitó del código)
  - [x] Implementar las elegidas en el visor y la impresión, sin cambiar la geometría ni los cruces de los pasos (10 nov: `MEJORAS_ACTIVAS` en las fichas; el visor pasa la sombra de contacto y las sombras suaves; el mapa de sombras se dibuja solo al cambiar de paso; la sombra de contacto, 10 veces más rápida; ver «Cómo se implementaron» en el plan)
  - [x] Nueva referencia de imágenes de los nudos ya aprobados, anotada aquí: desde el commit «T7b: las mejoras elegidas en las fichas y el visor», las imágenes de impresión del as de guía, el ballestrinque, la vuelta de escota y el amarre cuadrado son las nuevas; sus modelos no cambian (byte a byte contra 563bed6), así que los filtros 1 siguen valiendo. Construir dos veces da las mismas 67 imágenes, con Edge; las cuatro fichas se arman y caben; 244 pruebas pasan. Las comparaciones de «nudos publicados idénticos» se hacen desde ese commit
  - [x] Publicar el sitio: el visor cambió (sombra de contacto y sombras suaves) (10 nov, a pedido de Gabriel: construido desde b3ff5ee, gh-pages d4065c8; los cuatro visores cargan en línea sin errores)
  - [ ] Gabriel abre el visor en un celular de gama baja y revisa que cargue y gire con fluidez (en la computadora, armar el paso más largo del amarre tarda 37 ms en vez de 20 y girar cuesta lo mismo)
- [ ] T7c Nudo terminado apretado, con la misma secuencia de cruces que el último paso (M, separada de T7b el 10 nov; antes del Punto de control B)
  - [x] Diseño escrito en el plan (método, dónde vive, pruebas, formato y cada nudo publicado), probado en un experimento fuera del repositorio (10 nov: el as de guía se aprieta dentro de los límites, el ballestrinque casi no cambia, la vuelta de escota es el riesgo y el amarre queda como está)
  - [x] Gabriel aprueba el diseño (11 nov)
  - [x] Referencia: los cuatro nudos publicados construidos e impresos desde `main` antes de tocar el código (11 nov, desde 52cb117, fuera del repositorio)
  - [x] `nudos/apretar.py`, `Modelo.apretado` y `Modelo.reverso_apretado`, con sus pruebas; pasos y error idénticos byte a byte (11 nov: los 4 `modelo.json` sin las claves nuevas, byte a byte, y las 67 imágenes, píxel por píxel, con Edge; `TERMINADO_APRETADO = False`. As de guía 110,0 → 94,7, ballestrinque casi igual, vuelta de escota 118,5 → 112,4 con la gruesa que conserva su forma, amarre sin apretar. Tres cambios al diseño: al soltar no hay corrección de largo, la gruesa queda sujeta y el reverso apretado es el reverso de hoy apretado; ver «Cómo se hizo» de T7c en el plan)
  - [x] Página de prueba `build/mejoras/apretado.pdf`: hoy, a medias y apretado, en color y en gris (11 nov: seis hojas, as de guía, ballestrinque y vuelta de escota)
  - [ ] Gabriel compara en papel y decide si entra (y cuál de las tres). Si entra: `TERMINADO_APRETADO = True`, nueva referencia de las imágenes del terminado y fichas rearmadas; sin publicar el sitio ni repetir filtros 1
- [ ] T8 Plantilla de la cabeza de turco (S, depende de T5)
- [ ] Punto de control B:
  - [ ] Los 5 nudos del piloto están publicados
  - [ ] El formato de especificación v1 está congelado
  - [ ] Revisión contigo

## Fase 3: el paso de IA y la operación

- [ ] T9 Skill nudo-nuevo, con pruebas doradas sobre el as de guía y la escota (M, depende del Punto de control B)
- [ ] T10 Estado de producción y registro de pruebas sin nombres (S, depende de T4)
- [ ] Punto de control C:
  - [ ] Un nudo nuevo salió de la skill con correcciones menores
  - [ ] Decisión sobre usar subagentes

## Fase 4: producción de los 30 nudos restantes

Cada nudo cumple la definición de terminado: pruebas automáticas, error común, imágenes, visor, ficha, filtro 1, filtro 2 y estado `publicado`. El filtro 2 está en pausa desde el 9 de noviembre (ver la definición de terminado en el plan).

### Tanda 1: libres, una cuerda
- [ ] Simple
- [ ] Ocho
- [ ] Ocho doble
- [ ] As de guía español
- [ ] Mariposa alpina
- [ ] Margarita
- [ ] Arnés de hombre
- [ ] Silla de bombero (requiere D1)
- [ ] Punto de control de la tanda 1

### Tanda 2: libres, dos cuerdas o dos extremos
- [ ] Rizo
- [ ] Pescador
- [ ] Nudo aguja (el del manual de la Tropa)
- [ ] Punto de control de la tanda 2

### Tanda 3: sobre anfitrión
- [ ] Ballestrinque doble (*rolling hitch*, entrada en el manual de la Tropa)
- [ ] Leñador o vuelta de braza
- [ ] Media llave y dos cotes
- [ ] Fugitivo
- [ ] Tensor (*trucker's hitch*)
- [ ] Tensor ajustable (*tautline hitch*, sobre una estaca)
- [ ] Constrictor
- [ ] Nudo de liberación rápida (*mooring hitch*)
- [ ] Presilla de alondra
- [ ] Prusik
- [ ] Punto de control de la tanda 3

### Tanda 4: plantillas
- [ ] Amarre redondo
- [ ] Amarre diagonal
- [ ] Amarre trípode
- [ ] Refuerzo de cabo
- [ ] Adujado
- [ ] Puño de mono
- [ ] Punto de control de la tanda 4

### Tanda 5: anfitriones especiales
- [ ] Eslinga de barril
- [ ] Eslinga de andamio (requiere D1)
- [ ] Vuelta de cornamusa (*cleat hitch*, sobre una cornamusa)
- [ ] Punto de control de la tanda 5

## Fase 5: libro y primera edición

- [ ] T11 Material inicial: portada, "cómo leer una ficha", glosario, seguridad e índice (S, depende de D1 y la tanda 1)
- [ ] T12 Anexos de la Wak y de la Tropa (S, depende de D3 y T11)
- [ ] T13 Edición 1: PDF completo, colofón, registro de cambios, etiqueta en git e impresión (S, depende de la fase 4, T11 y T12)
- [ ] Punto de control final: edición 1 impresa y todos sus QR responden
