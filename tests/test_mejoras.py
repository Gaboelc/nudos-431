"""Mejoras del render (T7b): apagadas en las fichas y comparadas en la página de prueba.
Las pruebas que dibujan necesitan Chrome; sin él se saltan."""
from dataclasses import replace

import pytest
from PIL import Image, ImageChops

from nudos.imprimir import CELDA_MM, MEJORAS, MEJORAS_ACTIVAS, dibujar, imagenes, px
from nudos.mejoras import MUESTRAS, VARIANTES, lista


def test_las_fichas_no_llevan_mejoras(modelo_as_de_guia):
    # Hasta que Gabriel elija con la página de prueba impresa, las imágenes de las fichas
    # salen como las de los nudos ya aprobados.
    assert MEJORAS_ACTIVAS == ()
    assert all(i.mejoras == () for i in imagenes(modelo_as_de_guia))


def test_una_mejora_desconocida_no_se_acepta(modelo_as_de_guia):
    img = imagenes(modelo_as_de_guia)[0]
    with pytest.raises(ValueError, match="brillo"):
        replace(img, mejoras=("contorno", "brillo"))


def test_cada_mejora_va_sola_y_tambien_todas_juntas():
    assert VARIANTES[0][2] == ()
    solas = [v[2] for v in VARIANTES[1:-1]]
    assert solas == [(m,) for m in MEJORAS]
    assert VARIANTES[-1][2] == MEJORAS


def test_la_pagina_de_prueba_tiene_cada_muestra_en_cada_variante(
        modelo_as_de_guia, modelo_ballestrinque, modelo_vuelta_de_escota, modelo_amarre_cuadrado):
    modelos = {"as-de-guia": modelo_as_de_guia, "ballestrinque": modelo_ballestrinque,
               "vuelta-de-escota": modelo_vuelta_de_escota,
               "amarre-cuadrado": modelo_amarre_cuadrado}
    muestras = lista(modelos)
    assert [(slug, base.nombre) for slug, base, _ in muestras] == list(MUESTRAS)
    for slug, base, variantes in muestras:
        assert [v.mejoras for v in variantes] == [m for _, _, m, _ in VARIANTES]
        for v, (clave, _, _, _) in zip(variantes, VARIANTES):
            assert v.nombre == f"{clave}/{slug}-{base.nombre}"
            # Fuera del nombre y de las mejoras, es la misma imagen de la ficha.
            assert replace(v, nombre=base.nombre, mejoras=base.mejoras) == base


def test_cada_mejora_cambia_la_imagen_y_sin_ellas_no(con_chrome, modelo_as_de_guia, tmp_path):
    ficha = {i.nombre: i for i in imagenes(modelo_as_de_guia)}["paso-7"]
    variantes = [replace(ficha, nombre=clave, mejoras=m) for clave, _, m, _ in VARIANTES]
    rutas = dibujar([ficha] + variantes, tmp_path)
    ims = [Image.open(r).convert("RGB") for r in rutas]
    assert all(im.size == (px(CELDA_MM[0]), px(CELDA_MM[1])) for im in ims)
    sola, hoy, *con = ims
    assert ImageChops.difference(sola, hoy).getbbox() is None
    for (clave, _, _, _), im in zip(VARIANTES[1:], con):
        assert ImageChops.difference(hoy, im).getbbox() is not None, clave


def test_con_mejoras_dibujar_dos_veces_da_lo_mismo(con_chrome, modelo_ballestrinque, tmp_path):
    img = replace({i.nombre: i for i in imagenes(modelo_ballestrinque)}["error"], mejoras=MEJORAS)
    primera = dibujar([img], tmp_path / "a")[0]
    segunda = dibujar([img], tmp_path / "b")[0]
    with Image.open(primera) as a, Image.open(segunda) as b:
        assert ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None
