# Libro de nudos del Grupo 431

Son fichas de nudos para la Wak y la Tropa del Grupo Guía y Scout 431, con modelos 3D propios de cada paso. Cada nudo se describe en una especificación en `specs/`, y de ella salen sus modelos, sus imágenes y su ficha.

## Instalar

Con Python 3.11 o más reciente:

```
python -m pip install -e .[dev]
```

## Usar

```
python -m nudos construir as-de-guia
python -m nudos hoja as-de-guia
python -m pytest
```

## Carpetas

| Carpeta | Contenido |
|---|---|
| `specs/` | Una especificación por nudo (formato en `docs/formato-spec.md`) |
| `nudos/` | Código |
| `tests/` | Pruebas |
| `docs/` | Documentación del formato |
| `tasks/` | Plan y lista de tareas |
| `prototipo/` | Prototipo original del as de guía, de referencia |
| `entradas/`, `build/` | Fuentes de referencia y archivos generados, fuera de git |
