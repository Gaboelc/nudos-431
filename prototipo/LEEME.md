# Prototipo: as de guía

Código del prototipo que validó el enfoque. Ya está todo portado: `knot.py` y `render.py` al paquete `nudos/` en T1, `viewer.template.html` y `build_viewer.py` a `render/` y `sitio/` en T2, y `shoot.py` a `nudos/imprimir.py` en T3. Cuando Gabriel apruebe la prueba impresa de T3, esta carpeta se borra.

## Archivos

- **`knot.py`:** contiene el diseño propio de los 7 pasos (puntos de control) y todo el proceso:
  - Curva suave a partir de los puntos de control.
  - Cálculo de cruces y comparación con la secuencia de referencia.
  - Elevación a 3D.
  - Relajación: cuerda inextensible, gravedad, mesa, colisiones y límite de curvatura.
  - Validación.

  Uso: `python knot.py out`. Genera `out/steps.npy` y `out/meta.json`.
- **`render.py`:** render de verificación hecho en numpy, con la cuerda como tubo de esferas y sombras. Uso: `python render.py out top` para la vista superior, o `python render.py out 55` para la vista inclinada.
- **`viewer.template.html` y `build_viewer.py`:** el visor three.js, con la textura trenzada generada por código, el resaltado, el remate y las etiquetas. Uso: `python build_viewer.py out viewer.template.html as-de-guia.html`.
- **`shoot.py`:** abre la página en Chrome sin interfaz (con Playwright) y toma capturas. La ruta de Chrome está fija para Linux (`/usr/bin/google-chrome`); en Windows hay que cambiarla.

## Dependencias

- Python 3.11+ con numpy, scipy y Pillow.
- Playwright, solo para `shoot.py`.
- Three.js 0.160.0, que se carga desde jsDelivr.

## Validación del prototipo

- La secuencia de cruces coincide con la referencia en los 7 pasos.
- La separación mínima entre tramos es de 0,99 diámetros.
- El estiramiento máximo es de 1,3 %.
- El radio de curvatura local mínimo es de 1,03 diámetros.

## No incluido

No van aquí las imágenes de referencia de Animated Knots, porque son entrada, no contenido.
