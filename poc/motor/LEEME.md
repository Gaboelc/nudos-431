# T14a: prueba de concepto del motor de física (rama `poc/motor`)

Esta es la primera prueba de concepto de la fase 5 del plan (`tasks/plan.md`, T14a), del 23 de noviembre de 2026. Es código de prueba: no entra a `main`, no cambia `nudos/` ni ningún nudo, y lo que genera queda en `build/poc-motor/`, fuera de git. Usa la escena de Blender de `poc/blender` y la v2 de la plantilla de `poc/cuerda-ajustada`, que esta rama trae copiadas.

## El entorno

Las bibliotecas van en un entorno aparte, fuera de A: (Drive no respalda cientos de MB de paquetes):

```
python -m venv %LOCALAPPDATA%\nudos-431\venv-motor
%LOCALAPPDATA%\nudos-431\venv-motor\Scripts\python -m pip install -e . ipctk numba warp-lang
```

Las tres instalaron sin problema en Windows con Python 3.14: `ipctk` 1.6.1, `numba` 0.68.1 y `warp-lang` 1.19.0. El motor de esta prueba usa solo `ipctk`, `numpy` y `scipy`. Numba no hizo falta todavía, y Warp no se probó más allá de instalarlo.

## El motor (`motor.py`)

- **La varilla:** estiramiento (EA = 20 000 N), flexión (EI = 31 N·d², lo de una cuerda de 8 mm), peso (45 g/m) y manos (nodos fijos y fuerzas). Las unidades son diámetros y newtons. La torsión no entró.
- **El contacto:** la barrera de IPC de `ipctk` entre tramos de cuerda, con los palos (mallas de triángulos fijas) y con la mesa (un plano). `dmin` es 0,95: la cuerda se comprime hasta un 5 %. La barrera actúa entre 0,95 y 1,05 diámetros.
- **El roce:** el de Coulomb de `ipctk`, retrasado: la fuerza normal y la base tangente son las del paso anterior.
- **El integrador:** pasos cuasiestáticos con un término proximal que amortigua. En cada paso, Newton con el Hessiano proyectado a semidefinido (CLAMP), `spsolve` y una búsqueda en línea recortada por la CCD.

### Lo que aprendí de `ipctk` (para T15)

| Tema | Lo que hace |
|---|---|
| `Hyperplane` | Recibe primero la normal y después el origen, al revés de lo que sugiere la documentación. Con el orden cambiado, la mesa quedó a media altura de la cuerda y la trabó. |
| Distancias | `compute_minimum_distance` las devuelve al cuadrado. `dhat` y `dmin` son distancias normales, y la barrera actúa entre `dmin` y `dmin + dhat`. |
| Contacto entre tramos paralelos | Se suaviza hasta cero si los tramos son exactamente paralelos (el *mollifier* de IPC). Para medir la barrera hay que usar tramos cruzados. |
| Vecinos a lo largo de la cuerda | Con nodos cada 0,2 y la cuerda de 1, se excluyen los pares a menos de 1,5 diámetros a lo largo de la cuerda. Con una función de Python en `can_collide` se traba (llama a Python desde hilos de C++). Hay que usar filtros nativos: `make_static_obstacle_filter & make_sparse_filter`. |
| La CCD | La que viene por defecto (Tight Inclusion) tarda de 7 a 11 s por llamada y es muy conservadora con `dmin`. La aditiva (`AdditiveCCD`, con `LBVH`) tarda de 0,005 a 0,08 s y deja pasos 15 veces más largos. |
| Las mallas de los palos | Bastan 64 × 24 caras: la superficie se aparta menos de 0,003 de la redonda. |
| La rigidez de la barrera | Si la geometría de partida ya tiene contactos dentro de la franja de la barrera, una rigidez alta los aprieta «de fábrica», y ese apriete da un roce falso que traba la cuerda. Sirve una rigidez baja (0,3) y la malla de los palos un poco por dentro (radio − 0,56), para que la plantilla quede arriba en la franja. |

## Las pruebas (`pruebas.py`)

- **El cabrestante** (Euler-Eytelwein): una cuerda abraza media vuelta de un palo, con μ = 0,45, así que el límite es e^(μπ) = 4,11. Con un cociente de 3, el extremo se corre apenas 0,012 diámetros (elasticidad y la franja del roce); con 5,5, desliza (0,79 diámetros en 40 pasos, y sigue). **Pasa.** Tarda de 6 a 13 s.
- **No atravesarse:** el nudo simple apretado con 20 y con 200 N de cada lado conserva su secuencia, y ningún par baja de 0,95. **Pasa.** Tarda 1 s. No se aprieta más porque la ficha ya lo dibuja tallado.
- **Repetir el resultado bit a bit:** no se midió. Queda para T15 (`ipctk` arma los contactos en paralelo).

## Los nudos

### El as de guía terminado (`asentar_as.py`)

La punta del firme fija, la gaza tirada hacia abajo con 60 N y el chicote con 20 N.
- Desde el paso 7 de la ficha: asienta en 11 pasos y 2 s, sin fallas, pero casi no cambia y queda menos apretado que el terminado de hoy (el apretado de T7c).
- **Desde el apretado de hoy** (`--desde-apretado`, el que pidió Gabriel): asienta en 4 pasos y 1 s, sin fallas (separación 0,994, curvatura 1,041, estiramiento 0,96 %), y queda tallado.

### El amarre cuadrado (`atar_amarre.py`)

| Cómo | Resultado |
|---|---|
| **Atar por hitos:** asentar hasta cada hito y empalmar el tramo siguiente de la plantilla | El ballestrinque de inicio y la primera vuelta asientan bien (la cuerda desliza 2,5 diámetros hacia la mano). Pero en la segunda vuelta el tramo de la plantilla atraviesa la vuelta anterior, que ya se corrió al apretarse: la plantilla pone cada vuelta nueva por dentro de la anterior sobre el palo de abajo. Empalmar la plantilla sobre una cuerda que ya se movió no sirve. |
| **Cada paso de una vez, con una mano tirando en el final de cada hito** (`--simultaneo`) | Una mano en medio de la cuerda tensa lo que queda atrás, pero empuja lo que viene adelante, que se pandea: los ahorcados se inflan en lazos sobre el palo de arriba. En los ahorcados y el cierre cambia la secuencia, en el cruce del ballestrinque de inicio y con cruces nuevos en los mapas de los palos. No llega a quedar quieto en 150 pasos (de 5 a 10 minutos por paso). |
| **Sin roce, el chicote corto fijo y una sola mano en el final** (`--simultaneo --sin-roce --solo-punta`) | Queda en equilibrio en 3 pasos (10 s), sin fallas en el terminado, y la cuerda pasa de 466,5 a 466,4 diámetros: no cambia. |
| **Tensión de atado, sin manos** (`--simultaneo --atado`): los dos extremos fijos y cada tramo con su largo de reposo acortado T/EA, 60 N en el ballestrinque de inicio y las vueltas, 150 N en los ahorcados y 60 N en el cierre | **El que vale.** De 4 a 14 s por paso (5 pasos cada uno). Los ahorcados quedan redondos y aprietan las vueltas, sin lazos inflados; el terminado queda compacto. Las vueltas (238,3 → 237,6) y los ahorcados (411,5 → 409,5) no tienen fallas. En el cierre (466,5 → 464,3) aparece un cruce de más: el ballestrinque de cierre pasa por encima de un ahorcado en el mapa del palo de arriba. Puede ser real o venir de las zonas viejas (ver abajo). |

Gabriel vio la página (24 nov). Le gustó el motor, salvo el final del amarre con las manos en cada hito, que estiraba la cuerda (los lazos inflados), y pidió el as de guía más tallado. Con la tensión de atado y el as de guía asentado desde el apretado de hoy, las dos cosas quedan resueltas.

**La tensión de atado** es la versión estática de cómo se ata: una vuelta que se tiró al darla queda tensa porque el roce guarda esa tensión. Acortar el largo de reposo de cada tramo pone esa tensión sin que una mano empuje lo que viene adelante, y los ahorcados, más tensos, juntan las vueltas. Para la ficha, alcanza. Para el video hace falta atar de verdad (ver abajo).

**Lo que se aprendió antes de la tensión de atado.** La plantilla ya traza las vueltas tensas por la tangente de los palos, y con el chicote corto fijo no queda holgura que sacar. Así que el amarre de hoy ya es el equilibrio de una cuerda tensa sin roce. Lo «tieso» no es cuerda floja: es el camino que la plantilla le da y una tensión pareja en toda la cuerda. En un amarre real, la cintura y los ahorcados que aprietan salen de la historia del atado: cada vuelta se tira al darla, el roce guarda esa tensión, y los ahorcados se tiran más fuerte que las vueltas y las juntan. Asentar la forma final de una vez, con o sin roce, no puede dar eso.

## Lo que dice para la fase

1. **El motor sirve:** no deja que la cuerda se atraviese, el roce cumple la ley del cabrestante, y con la CCD aditiva y los filtros nativos corre en segundos. Para D11 propongo `ipctk` con `numpy` y `scipy`, y `numba` si las energías de la varilla se vuelven el cuello de botella.
2. **Para la ficha, la tensión de atado basta:** asentar la forma de la plantilla con una tensión por tramo (más en los ahorcados) da un amarre apretado, en segundos. Tirar de manos en medio de la cuerda la pandea, y asentar sin tensión de atado no cambia nada.
3. **Para el video hay que atar de verdad:** una mano que lleva el chicote alrededor de los palos, con la cuerda que ya está apretándose bajo el roce (el modo «atar» de T15 y T17). Empalmar tramos de la plantilla sobre una cuerda asentada no sirve: el tramo nuevo atraviesa la cuerda que se corrió. Es lo que tiene que probar T14b.
4. **La comprobación de cruces de las plantillas tiene que usar zonas geométricas,** calculadas por dónde está cada nodo y no por dónde lo puso la plantilla. Cuando la cuerda desliza, la zona de la plantilla queda vieja.
5. **`dmin` tiene que ser 0,97 o más,** o la comprobación de separación (0,97) tiene que aceptar que la cuerda se comprima contra sí misma.
6. **Lo que faltó:** la torsión, la comprobación de que repite el resultado y Warp.

## Cómo se corre

En el entorno de la prueba (`%LOCALAPPDATA%\nudos-431\venv-motor\Scripts\python`), desde la raíz del repositorio:

```
python poc/motor/pruebas.py cabrestante
python poc/motor/pruebas.py simple
python poc/motor/asentar_as.py
python poc/motor/atar_amarre.py                      # por hitos (se detiene en la segunda vuelta)
python poc/motor/atar_amarre.py --simultaneo         # cada paso de una vez, con roce
python poc/motor/atar_amarre.py --simultaneo --sin-roce --solo-punta --sufijo=-sin-roce --hitos cierre
python poc/motor/atar_amarre.py --simultaneo --atado --hitos cierre ahorcado-3 vuelta-3   # el que vale
python poc/motor/asentar_as.py --desde-apretado                                          # el que vale
python poc/motor/exportar.py
```

Y con el `.venv` del proyecto: `python poc/motor/pagina.py`, que dibuja con Blender y arma `build/poc-motor/prueba.pdf`.
