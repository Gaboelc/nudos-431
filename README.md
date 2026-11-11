# Libro de nudos del Grupo 431

Son fichas de nudos para la Wak y la Tropa del Grupo Guía y Scout 431, con modelos 3D propios de cada paso. Cada nudo se describe en una especificación en `specs/`, y de ella salen sus modelos, sus imágenes, su ficha y su visor 3D en `https://gaboelc.github.io/nudos-431/<slug>/`.

## Instalar

Con Python 3.11 o más reciente:

```
python -m pip install -e .[dev]
```

## Usar

```
python -m nudos construir as-de-guia
python -m nudos hoja as-de-guia
python -m nudos imprimir as-de-guia
python -m nudos ficha as-de-guia
python -m nudos mejoras
python -m nudos sitio
python -m pytest
```

`imprimir` necesita Google Chrome instalado (o la ruta de otro Chrome en la variable `NUDOS_CHROME`). Deja en `build/<slug>/impresion/` las imágenes a 300 ppp y `prueba.pdf`, una página de prueba en color y en escala de grises. `ficha` genera esas imágenes y arma con ellas `build/<slug>/ficha.pdf`, el pliego de dos páginas con QR al visor. `mejoras` arma `build/mejoras/prueba.pdf`, la página de prueba de las mejoras del render: algunas imágenes sin mejoras, con cada una y con todas, que son las de las fichas, para mirarlas en papel.

Para publicar el sitio, desde `main` ya subido: `scripts/publicar.sh`. Sube el sitio a la rama `gh-pages`, que es la que sirve GitHub Pages.

## Carpetas

| Carpeta | Contenido |
|---|---|
| `specs/` | Una especificación por nudo (formato en `docs/formato-spec.md`) |
| `nudos/` | Código |
| `render/` | Escena 3D compartida por el visor y las imágenes de impresión |
| `libro/` | Plantilla de la ficha impresa |
| `config/` | Términos propios de cada sección, que las fichas no usan |
| `sitio/` | Plantillas y página del visor; en `sitio/vendor/`, three.js y las fuentes |
| `scripts/` | `publicar.sh` |
| `publicados.txt` | Nudos con QR impreso: su dirección no cambia nunca |
| `tests/` | Pruebas |
| `docs/` | Documentación del formato |
| `tasks/` | Plan y lista de tareas |
| `entradas/`, `build/` | Fuentes de referencia y archivos generados, fuera de git |
