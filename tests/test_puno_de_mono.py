"""El puño de mono: la plantilla sin anfitrión, con los tres juegos de vueltas en dos dedos y el
nudo simple escondido en el centro (nudos/plantillas/puno.py)."""
import copy
import math

import numpy as np
import pytest

from nudos.construir import construir, datos_json
from nudos.cruces import etiqueta
from nudos.exportar import datos_visor
from nudos.hoja import mapa_puno
from nudos.imprimir import imagenes
from nudos.libre import LIMITES
from nudos.plantillas.pasos import geometria
from nudos.plantillas.puno import (CAPA, DEDO_RADIO, ENCIMA, K0, K1, K2, K3, LEJOS_CARA, POLO,
                                   Cuerda, Dedos, Forma, FormaDedos, PunoDeMono,
                                   direccion_del_lugar, lugar_en_la_cara, mapa_del_puno)
from nudos.spec import SpecError, desde_datos

PASOS = [
    ("Da {vueltas} vueltas alrededor de dos dedos", "juego-1"),
    ("Pasa el chicote entre los dedos", "vuelta-2-1"),
    ("Da las demás", "juego-2"),
    ("Pasa el chicote por dentro de las primeras", "vuelta-3-1"),
    ("Da las demás", "juego-3"),
    ("Esconde el chicote y aprieta", "apretar"),
]


def datos(**cambios):
    base = {
        "slug": "puno-de-prueba",
        "nombre": "Puño de prueba",
        "familia": "Decorativos",
        "plantilla": {"tipo": "puno-de-mono", "vueltas": 3},
        "pasos": [{"titulo": t, "texto": "Texto.", "hasta": h} for t, h in PASOS],
        "error": {"paso": 5, "variante": "tercero-por-fuera", "titulo": "Por fuera",
                  "texto": "Texto."},
    }
    base.update(copy.deepcopy(cambios))
    return base


# --- La especificación ----------------------------------------------------
def test_la_especificacion_se_lee():
    spec = desde_datos(datos())
    assert spec.anfitrion is None
    assert spec.plantilla == PunoDeMono(vueltas=3)
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]
    assert spec.pasos[0].titulo == "Da tres vueltas alrededor de dos dedos"


def test_los_hitos_van_en_el_orden_del_metodo():
    hitos = PunoDeMono(3).hitos()
    alias = {f"juego-{j}": f"vuelta-{j}-3" for j in (1, 2, 3)}
    assert all(hitos[a] == hitos[h] for a, h in alias.items())
    orden = sorted((h for h in hitos if h not in alias), key=hitos.get)
    assert orden == [f"vuelta-{j}-{k}" for j in (1, 2, 3) for k in (1, 2, 3)] + ["apretar"]


@pytest.mark.parametrize("cambio, pista", [
    ({"plantilla": {"tipo": "puno-de-mono", "vueltas": 2}}, "de 3 a 4"),
    ({"plantilla": {"tipo": "puno-de-mono", "vueltas": 5}}, "de 3 a 4"),
    ({"plantilla": {"tipo": "puno-de-mono", "vueltas": 3, "bola": 1}}, "desconocidos"),
    ({"anfitrion": {"tipo": "poste", "radio": 3, "desde": -10, "hasta": 10}}, "sin anfitrión"),
])
def test_un_puno_mal_escrito_se_detecta(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(datos(**cambio))


def test_las_otras_plantillas_siguen_pidiendo_su_anfitrion():
    d = {"slug": "x", "nombre": "X", "familia": "Amarres",
         "plantilla": {"tipo": "amarre-cuadrado", "vueltas": 3, "ahorcados": 3,
                       "inicio": {"poste": "abajo", "lado": "delante"},
                       "cierre": {"poste": "arriba", "lado": "derecha"}},
         "pasos": [{"titulo": "T", "texto": "T.", "hasta": "cierre"}]}
    with pytest.raises(SpecError, match="anfitrión cruz"):
        desde_datos(d)


def test_el_ultimo_paso_aprieta():
    d = datos()
    d["pasos"] = d["pasos"][:-1]
    with pytest.raises(SpecError, match="apretar"):
        desde_datos(d)


def test_el_error_va_desde_el_tercer_juego():
    with pytest.raises(SpecError, match="vuelta-3-1"):
        desde_datos(datos(error={"paso": 3, "variante": "tercero-por-fuera",
                                 "titulo": "T", "texto": "Texto."}))


# --- La forma del puño ----------------------------------------------------
def test_cada_juego_va_encima_en_dos_caras_y_debajo_en_otras_dos():
    """El segundo sobre el primero en ±y, el tercero sobre el segundo en ±z y el primero sobre
    el tercero en ±x: cada juego va CAPA más lejos del centro donde va encima."""
    f = Forma(3, apretado=True)
    assert ENCIMA == {("B", "A"), ("C", "B"), ("A", "C")}
    for j in "ABC":
        assert np.allclose(f.capa(j, [0.0, math.pi]), CAPA)          # sus caras ±u
        assert np.allclose(f.capa(j, [math.pi / 2, -math.pi / 2]), 0.0)   # sus caras ±v
    mal = Forma(3, apretado=True, variante="tercero-por-fuera")
    assert np.allclose(mal.capa("C", [0.0, math.pi / 2]), CAPA)       # el tercero, por fuera
    assert np.allclose(mal.capa("A", [0.0, math.pi / 2]), 0.0)        # y el primero, debajo


def test_las_vueltas_de_un_juego_van_a_un_diametro():
    f = Forma(3, apretado=True)
    for j in "ABC":
        P = f.en(j, [0.3, 0.3 + 2 * math.pi])
        assert np.linalg.norm(P[1] - P[0]) >= 1.05


def test_cada_juego_empieza_donde_termino_el_anterior():
    """Los juegos se encadenan por las esquinas del puño: el primero termina en K1, donde
    empieza el segundo; el segundo termina en K2, donde empieza el tercero, que termina en K3. El
    firme llega por K0. Las esquinas del polo del mapa no las usa nada."""
    f = Forma(3, apretado=True)
    total = 2 * math.pi * 3

    def esquina(P):
        return np.sign(P)

    assert (esquina(f.en("A", 0.0)[0])[:2] == np.sign(K0)[:2]).all() and f.en("A", 0.0)[0][2] < 0
    for K, j, t in ((K1, "A", total), (K1, "B", 0.0), (K2, "B", total), (K2, "C", 0.0),
                    (K3, "C", total)):
        assert (esquina(f.en(j, t)[0]) == np.sign(K)).all(), (j, t)
    for K in (K0, K1, K2, K3):
        assert abs(K @ POLO) < 0.9


def test_en_los_dedos_cada_juego_rodea_lo_que_debe():
    """Suelto, el primer juego rodea los dos dedos; el segundo, al primero por la mitad, entre
    los dedos, y el tercero, al segundo, entre los dedos y por dentro del primero. Cada juego va
    lejos del que tapa."""
    f = FormaDedos(3)
    total = 2 * math.pi * 3
    t = np.linspace(0.0, total, 4000)
    A, B, C = (f.en(j, t) for j in "ABC")
    # El primero, por fuera de los dedos; el segundo y el tercero, entre ellos.
    assert np.abs(A[:, 0]).max() > f.dedo_x + DEDO_RADIO + 1.0
    assert np.abs(B[:, 0]).max() < f.dedo_x - DEDO_RADIO - 1.0
    assert np.abs(C[:, 0]).max() <= f.dedo_x - DEDO_RADIO - 1.0 + 1e-9   # medio diámetro de aire
    # El segundo, por fuera del primero a los costados (±y); el tercero, sobre el segundo
    # arriba y abajo (±z), y por dentro del primero a los costados (|y| menor).
    assert np.abs(B[:, 1]).max() > np.abs(A[:, 1]).max() + 1.0
    assert np.abs(C[:, 2]).max() > np.abs(B[:, 2]).max() + 1.0
    assert np.abs(C[:, 1]).max() + 1.0 < np.abs(A[:, 1]).max()
    # Ningún juego entra en los dedos.
    dedos = Dedos(f.dedo_x, DEDO_RADIO, 30.0)
    for P in (A, B, C):
        assert dedos.penetracion(P + [0.0, 0.0, 10.0]) == 0.0


def test_los_dedos_empujan_la_cuerda_hacia_afuera():
    dedos = Dedos(5.0, 1.0, 10.0)
    X = np.array([[5.2, 0.3, 4.0], [-5.0, 0.0, 9.8], [0.0, 0.0, 4.0]])
    assert dedos.penetracion(X) > 1.0
    dedos.empujar(X, np.ones(3, bool))
    assert dedos.penetracion(X) == pytest.approx(0.0, abs=1e-9)
    assert X[1, 2] > 9.8                            # sobre la punta, sale hacia arriba
    assert np.allclose(X[2], [0.0, 0.0, 4.0])       # entre los dedos, no se mueve


def test_el_mapa_del_puno_no_tiene_costura():
    """El mapa (proyección desde la esquina opuesta al polo) es continuo en todas las caras, y
    el lugar de un cruce en su cara se puede volver a leer."""
    d = np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0], [-1.0, 0.2, 0.1]])
    d /= np.linalg.norm(d, axis=1)[:, None]
    M, r = mapa_del_puno(d * 5.0, np.zeros(3))
    assert np.isfinite(M).all() and np.allclose(r, 5.0)
    for v in d:
        p = lugar_en_la_cara(v)
        assert p[0] > LEJOS_CARA / 2
        assert np.allclose(direccion_del_lugar(p), v)


# --- La cuerda del método -------------------------------------------------
@pytest.fixture(scope="module")
def modelo():
    return construir(desde_datos(datos()))


@pytest.fixture(scope="module")
def cuerda(modelo):
    return geometria(modelo.spec).cuerda()


def test_los_cruces_del_metodo(cuerda):
    """Cada vuelta del segundo juego pasa sobre las del primero en sus dos caras; cada una del
    tercero, sobre las del segundo y bajo las del primero; y el nudo simple tiene tres."""
    n = 3
    cuantos = {h: len(s) // 2 for h, s in cuerda.secuencias.items()}
    for k in range(1, n + 1):
        assert cuantos[f"vuelta-1-{k}"] == 0
        assert cuantos[f"vuelta-2-{k}"] == 2 * n * k
        assert cuantos[f"vuelta-3-{k}"] == 2 * n * n + 4 * n * k
    assert cuantos["apretar"] == 6 * n * n + 3


def test_encima_va_el_juego_que_dice_el_metodo(cuerda):
    """En el puño apretado, cada cruce entre dos juegos tiene encima al que dice ENCIMA, y lo
    que está encima es lo más lejos del centro."""
    d = cuerda.paso("apretar")
    for et, clave, c in d["cruces"]:
        if clave[0] == "nudo":
            continue
        a, b, cara = clave
        i, j = int(round(c.sa / 0.1)), int(round(c.sb / 0.1))
        primero, segundo = str(d["pieza"][i]), str(d["pieza"][j])
        arriba = (primero[0], segundo[0]) in ENCIMA
        ra = np.linalg.norm(d["P"][i] - d["centro"])
        rb = np.linalg.norm(d["P"][j] - d["centro"])
        assert (ra > rb) == arriba, (et, clave)


def test_todos_los_pasos_se_construyen_sin_fallas(modelo):
    assert modelo.fallas == []
    for r in modelo.pasos + [modelo.error]:
        assert r.medidas["separacion_min"] >= LIMITES["separacion_min"]
        assert r.medidas["curvatura_min"] >= LIMITES["curvatura_min"]
        assert r.medidas["estiramiento_max"] <= LIMITES["estiramiento_max"]
    # En las vueltas, la cuerda no entra en los dedos; al apretar ya no están.
    for r in modelo.pasos[:5]:
        assert r.medidas["penetracion_dedos"] <= 0.05
    assert "penetracion_dedos" not in modelo.pasos[5].medidas


def test_con_cuatro_vueltas_tambien():
    m = construir(desde_datos(datos(plantilla={"tipo": "puno-de-mono", "vueltas": 4})))
    assert m.fallas == []
    c = geometria(m.spec).cuerda()
    assert len(c.secuencias["apretar"]) // 2 == 6 * 16 + 3


def test_los_cruces_conservan_su_etiqueta_al_apretar(cuerda):
    """Los cruces de las vueltas son los mismos en los dedos y apretados, en el mismo lugar de
    su cara. Al apretar se agregan los tres del nudo simple."""
    def etiquetas(hito):
        return {e: (k, c.xy) for e, k, c in cuerda.paso(hito)["cruces"]}
    suelto, apretado = etiquetas("juego-3"), etiquetas("apretar")
    assert len(apretado) == len(suelto) + 3 and suelto.keys() <= apretado.keys()
    for e in suelto:
        assert suelto[e][0] == apretado[e][0]
        assert np.hypot(*np.subtract(suelto[e][1], apretado[e][1])) < 2.5


def test_el_error_es_el_tercer_juego_por_fuera_del_primero(modelo, cuerda):
    error = geometria(modelo.spec).cuerda("tercero-por-fuera")

    def encima(c):
        """Cada cruce, por sus dos piezas y su cara: si la primera pasada va encima."""
        d = c.paso("juego-3")
        pasadas = sorted((x.sa, et, k) for et, k, x in d["cruces"])
        primera = {}
        tokens = iter(d["secuencia"])
        for s, et, k in sorted([(x.sa, et, k) for et, k, x in d["cruces"]]
                               + [(x.sb, et, None) for et, k, x in d["cruces"]]):
            t = next(tokens)
            assert etiqueta(t) == et
            if k is not None:
                primera[k] = t.endswith("O")
        assert len(primera) == len(pasadas)
        return primera

    bien, mal = encima(cuerda), encima(error)
    assert bien.keys() == mal.keys()
    distintos = [k for k in bien if bien[k] != mal[k]]
    # Los 2n² cruces del primero con el tercero quedan al revés, y ningún otro.
    assert len(distintos) == 2 * 9
    assert all({k[0][0], k[1][0]} == {"A", "C"} for k in distintos)
    assert modelo.error is not None and modelo.error.n == 5


def test_los_nombres_y_los_dedos(modelo):
    pasos = datos_visor(modelo)["pasos"]
    assert all(p["nombres"] == ["firme", "chicote"] for p in pasos[:5])
    assert pasos[5]["nombres"] == ["firme"]
    assert pasos[-1]["hl"] is None
    assert datos_visor(modelo).get("anfitrion") is None
    # Los dedos van en los pasos de las vueltas y no al apretar.
    assert all(p["dedos"]["x"][0] < 0 < p["dedos"]["x"][1] for p in pasos[:5])
    assert "dedos" not in pasos[5]


def test_por_detras_el_puno_se_voltea_como_una_pagina(modelo):
    final = modelo.pasos[-1]
    volteado = modelo.spec.plantilla.voltear(final)
    X, Y = final.puntos, volteado.puntos
    # El puño (lo que no es el firme) es el mismo, girado media vuelta alrededor de y: las
    # distancias entre sus puntos no cambian, y nada entra en la mesa.
    cola_x, cola_y = X[-200:], Y[-200:]
    dx = np.linalg.norm(cola_x[::20, None] - cola_x[None, ::20], axis=-1)
    dy = np.linalg.norm(cola_y[::20, None] - cola_y[None, ::20], axis=-1)
    assert np.allclose(dx, dy, atol=1e-6)
    assert np.allclose(cola_y[:, 1], cola_x[:, 1])
    assert Y[:, 2].min() >= 0.5 - 1e-6
    assert volteado.secuencia == final.secuencia and volteado.resaltado is None


def test_las_imagenes_del_puno(modelo):
    imgs = imagenes(modelo)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 7)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]
    assert {i.vista for i in imgs} == {"3d"}
    # El error y su paso bien hecho van sin dedos: el tercer juego del error pasaría por ellos.
    error = next(i for i in imgs if i.nombre == "error")
    assert all("dedos" not in p for p in error.escena["pasos"])


def test_la_hoja_lleva_el_puno_desenrollado(modelo, cuerda):
    d = datos_json(modelo)
    d = {**d, "pasos": d["pasos"][-2:]}
    centros = [cuerda.paso(h)["centro"] for h in ("juego-3", "apretar")]
    plano = mapa_puno(d, centros, [(2.0, 12.0), (5.5, 6.6)])
    assert plano.width > 0 and plano.height > 0
    imagen = np.asarray(plano.convert("RGB")).astype(float) / 255
    assert (np.abs(imagen - [0.10, 0.25, 0.75]).sum(-1) < 0.6).mean() > 0.01   # hay cuerda


def test_la_cuerda_de_la_variante_es_solo_la_del_tercer_juego():
    c = Cuerda(PunoDeMono(3), "tercero-por-fuera")
    assert set(c.orden) == {"vuelta-3-1", "vuelta-3-2", "vuelta-3-3"}
    with pytest.raises(ValueError):
        c.trazo("apretar", None)
