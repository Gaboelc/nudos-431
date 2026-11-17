"""El amarre redondo y el trípode, las plantillas sobre los palos paralelos
(nudos/plantillas/paralelos.py)."""
import copy

import numpy as np
import pytest

from nudos.anfitrion import PENETRACION_MAX, Palos
from nudos.construir import DESPLAZAMIENTO_MAX, construir
from nudos.cruces import numerada
from nudos.exportar import datos_visor
from nudos.imprimir import imagenes
from nudos.libre import LIMITES, catmull_rom, remuestrear
from nudos.plantillas import pasos as PS
from nudos.plantillas.paralelos import AmarreRedondo, AmarreTripode, cuerda
from nudos.plantillas.trazo import COSTADO, HUECO, PALO
from nudos.spec import SpecError, desde_datos

PASOS = {
    "redondo": ["inicio", "vuelta-1", "vueltas", "ahorcado-1", "ahorcados", "cierre-1", "cierre"],
    "tripode": ["inicio", "vuelta-1", "vueltas", "hueco-1", "ahorcados", "cierre-1", "cierre"],
}
TIPOS = ("redondo", "tripode")


def datos(tipo="redondo", vueltas=6, ahorcados=2, **cambios):
    base = {
        "slug": f"amarre-{tipo}", "nombre": "Amarre", "familia": "Amarres",
        "anfitrion": {"tipo": "palos", "cantidad": 2 if tipo == "redondo" else 3,
                      "radio": 2.5, "largo": 30},
        "plantilla": {"tipo": f"amarre-{tipo}", "vueltas": vueltas, "ahorcados": ahorcados},
        "pasos": [{"titulo": f"Paso {h}", "texto": "Da {vueltas} vueltas y {ahorcados} ahorcados.",
                   "hasta": h} for h in PASOS[tipo]],
        "error": {"paso": 6, "variante": "sin-ahorcados", "titulo": "Sin ahorcados",
                  "texto": "Texto."},
    }
    base.update(copy.deepcopy(cambios))
    return base


def la_cuerda(tipo="redondo", variante=None, **medidas):
    spec = desde_datos(datos(tipo, **medidas))
    return cuerda(spec.plantilla, Palos(spec.anfitrion), variante)


def cruces_del_trazo(tipo, hito, variante=None, **medidas):
    """Los cruces que se miden en la cuerda de un paso antes de relajarla."""
    spec = desde_datos(datos(tipo, **medidas))
    g = PS.geometria(spec)
    t = g.cuerda(variante).trazo(hito, None)
    D, ctrl = catmull_rom(t.puntos)
    X, h, s_ctrl = remuestrear(D, ctrl)
    s = np.arange(len(X)) * h
    tramo = np.clip(np.searchsorted(s_ctrl, s, side="right") - 1, 0, len(t.puntos) - 1)
    sig = np.minimum(tramo + 1, len(t.puntos) - 1)
    zonas = np.where(t.zonas[tramo] == t.zonas[sig], t.zonas[tramo], -1)
    return g.buscar(X, h, zonas, t)[0]


# --- La especificación ----------------------------------------------------
def test_las_plantillas_se_leen():
    r = desde_datos(datos("redondo")).plantilla
    t = desde_datos(datos("tripode")).plantilla
    assert isinstance(r, AmarreRedondo) and (r.vueltas, r.ahorcados) == (6, 2)
    assert isinstance(t, AmarreTripode) and t.total_ahorcados == 4


def test_los_hitos():
    r = AmarreRedondo(6, 2).hitos()
    assert list(r)[:3] == ["inicio-1", "inicio", "vuelta-1"]
    assert r["vueltas"] == r["vuelta-6"] and r["ahorcados"] == r["ahorcado-2"]
    assert max(r, key=r.get) == "cierre"
    t = AmarreTripode(6, 2).hitos()
    assert t["hueco-1"] == t["ahorcado-2"] and t["ahorcados"] == t["ahorcado-4"]
    assert "hueco-1" not in r


def test_las_medidas_salen_en_letras():
    spec = desde_datos(datos("tripode", vueltas=5, ahorcados=3))
    assert spec.pasos[0].texto == "Da cinco vueltas y tres ahorcados."


@pytest.mark.parametrize("cambio, pista", [
    ({"vueltas": 1}, "vueltas"),
    ({"vueltas": 7}, "vueltas"),
    ({"ahorcados": True}, "ahorcados"),
    ({"ahorcados": 4}, "ahorcados"),   # con cuatro o más se salen del hueco
    ({"inicio": {"poste": "abajo", "lado": "delante"}}, "campos desconocidos"),
])
def test_una_plantilla_mal_escrita_se_detecta(cambio, pista):
    d = datos()
    d["plantilla"].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_un_hasta_que_no_existe_con_esas_medidas():
    d = datos(vueltas=3)
    d["pasos"][2]["hasta"] = "vuelta-4"
    with pytest.raises(SpecError, match="hasta"):
        desde_datos(d)
    d = datos("redondo")
    d["pasos"][3]["hasta"] = "hueco-1"   # el redondo tiene un solo hueco
    with pytest.raises(SpecError, match="hasta"):
        desde_datos(d)


def test_el_error_se_ve_desde_el_cierre():
    with pytest.raises(SpecError, match="se ve desde"):
        desde_datos(datos(error={"paso": 5, "variante": "sin-ahorcados", "titulo": "E", "texto": "T."}))
    with pytest.raises(SpecError, match="variante"):
        desde_datos(datos(error={"paso": 6, "variante": "ahorcados-por-fuera", "titulo": "E",
                                 "texto": "T."}))


# --- La cuerda entera -------------------------------------------------------
@pytest.mark.parametrize("tipo", TIPOS)
@pytest.mark.parametrize("vueltas, ahorcados", [(2, 2), (6, 2), (4, 3), (2, 3), (6, 3)])
def test_la_secuencia_del_metodo(tipo, vueltas, ahorcados):
    """Cada ahorcado pasa por encima de cada vuelta, por debajo y por encima de ellas, salvo
    por encima de la primera, que es el firme que sale del ballestrinque; en el trípode, en el
    hueco de delante pasa también sobre la cuerda que va al hueco de atrás. Las vueltas no se
    cruzan entre sí, ni los ahorcados entre ellos, y cada ballestrinque tiene sus dos cruces."""
    c = la_cuerda(tipo, vueltas=vueltas, ahorcados=ahorcados)
    sec = c.secuencias["cierre"]
    n, m = vueltas, ahorcados
    esperados = m * (2 * n - 1) + 4 if tipo == "redondo" else m * (4 * n - 1) + 4
    assert len(sec) // 2 == esperados
    assert sec[:4] == ("1U", "1O", "2O", "2U")
    vueltas_ = [t for t in sec[4:-4] if t.endswith("U")]
    assert all(t.endswith("O") for t in sec[4 + len(vueltas_):-4])   # los ahorcados, siempre encima
    assert len(c.secuencias["vueltas"]) == 4
    if tipo == "redondo":
        assert len(c.secuencias["ahorcado-1"]) // 2 == (2 * n - 1) + 2
    else:
        assert len(c.secuencias["hueco-1"]) // 2 == m * (2 * n - 1) + 2


@pytest.mark.parametrize("tipo", TIPOS)
def test_los_hitos_avanzan_por_la_misma_cuerda(tipo):
    c = la_cuerda(tipo)
    p = desde_datos(datos(tipo)).plantilla
    indices = [c.hitos[c.alias.get(h, h)] for h in p.hitos()]
    assert indices == sorted(indices)
    assert c.hitos["cierre"] == len(c.puntos) - 1
    assert set(c.restos) == set(c.hitos) - {"cierre"}
    for nombre, resto in c.restos.items():
        assert resto[-1][2] == pytest.approx(0.5), nombre   # el resto termina sobre la mesa


@pytest.mark.parametrize("tipo", TIPOS)
@pytest.mark.parametrize("vueltas, ahorcados", [(2, 2), (4, 3), (6, 3)])
def test_la_cuerda_trazada_tiene_los_cruces_del_metodo(tipo, vueltas, ahorcados):
    """Antes de relajar, la cuerda de cada paso ya cruza lo que dice el método."""
    c = la_cuerda(tipo, vueltas=vueltas, ahorcados=ahorcados)
    for hito in PASOS[tipo]:
        sec = c.secuencias[hito]
        assert len(cruces_del_trazo(tipo, hito, vueltas=vueltas, ahorcados=ahorcados)) == len(sec) // 2, hito


def test_las_zonas_de_la_cuerda():
    c = la_cuerda("tripode")
    usadas = set(np.unique(c.zonas))
    assert {PALO[0], PALO[1], PALO[2], HUECO[0], HUECO[1], COSTADO} <= usadas


@pytest.mark.parametrize("tipo", TIPOS)
def test_el_error_es_el_mismo_amarre_hasta_las_vueltas(tipo):
    bien, mal = la_cuerda(tipo), la_cuerda(tipo, "sin-ahorcados")
    i = bien.hitos["vuelta-6"]
    assert mal.hitos["vuelta-6"] == i
    assert np.array_equal(mal.puntos[:i + 1], bien.puntos[:i + 1])
    # Sin ahorcados, solo quedan los cruces de los dos ballestrinques, con sus etiquetas.
    assert mal.secuencias["cierre"] == bien.secuencias["cierre"][:4] + bien.secuencias["cierre"][-4:]
    assert mal.alias["ahorcados"] == mal.alias["ahorcado-1"] == "vuelta-6"
    # El cierre va en el mismo lugar.
    assert np.allclose(mal.puntos[-40:], bien.puntos[-40:])


def test_una_variante_que_la_plantilla_no_sabe_construir():
    spec = desde_datos(datos())
    with pytest.raises(ValueError, match="no tiene la variante ahorcados-por-fuera"):
        cuerda(spec.plantilla, Palos(spec.anfitrion), "ahorcados-por-fuera")


# --- Los nudos ------------------------------------------------------------------
@pytest.fixture(scope="module", params=TIPOS)
def modelo(request):
    """Cada amarre, construido una sola vez (tarda cerca de un minuto)."""
    return request.param, construir(desde_datos(datos(request.param)))


def test_todos_los_pasos_se_construyen_sin_fallas(modelo):
    tipo, m = modelo
    assert m.fallas == []
    assert [r.n for r in m.pasos] == list(range(1, 8))
    assert m.error is not None and m.error.n == 6
    assert m.reverso is None   # por detrás, el amarre se voltea con los palos (Palos.voltear)


def test_la_cuerda_no_atraviesa_los_palos_ni_otras_vueltas(modelo):
    _, m = modelo
    for r in m.pasos + [m.error]:
        md = r.medidas
        assert md["penetracion_palos"] <= PENETRACION_MAX, r.n
        assert md["separacion_min"] >= LIMITES["separacion_min"], r.n
        assert md["curvatura_min"] >= LIMITES["curvatura_min"], r.n
        assert md["estiramiento_max"] <= LIMITES["estiramiento_max"], r.n


def test_los_cruces_coinciden_con_el_metodo(modelo):
    tipo, m = modelo
    c = la_cuerda(tipo)
    for r, hasta in zip(m.pasos, PASOS[tipo]):
        assert r.secuencia == r.esperada == numerada(c.secuencias[hasta]), r.n
    assert len(m.pasos[-1].secuencia) // 2 == (26 if tipo == "redondo" else 50)
    e = m.error
    assert e.secuencia == e.esperada == numerada(la_cuerda(tipo, "sin-ahorcados").secuencias["cierre-1"])


def test_cada_paso_resalta_lo_que_agrega(modelo):
    _, m = modelo
    previo = 0.0
    for r in m.pasos:
        desde, hasta = r.resaltado
        assert desde == pytest.approx(previo, abs=0.01) and hasta > desde, r.n
        previo = hasta


def test_un_cruce_conserva_su_etiqueta_y_su_lugar(modelo):
    _, m = modelo
    final = m.pasos[-1].cruces
    for r in m.pasos[:-1]:
        assert set(r.cruces) <= set(final), r.n
        for et, (x, y) in r.cruces.items():
            assert np.hypot(x - final[et][0], y - final[et][1]) <= DESPLAZAMIENTO_MAX, (r.n, et)


def test_la_escena_y_las_imagenes(modelo):
    tipo, m = modelo
    d = datos_visor(m)
    assert d["anfitrion"]["tipo"] == "palos" and len(d["anfitrion"]["y"]) == (2 if tipo == "redondo" else 3)
    assert d["dos_remates"] is True
    pasos = d["pasos"]
    assert "nombres" not in pasos[0]
    assert all(p["nombres"] == ["chicote"] for p in pasos[1:])
    imgs = imagenes(m)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 8)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]
    por_nombre = {i.nombre: i for i in imgs}
    assert {i.vista for i in imgs} == {"3d"}
    # Por detrás, los palos volteados con la cuerda: siguen en las mismas y, a otra altura.
    atras = por_nombre["terminado-reverso"].escena["anfitrion"]
    assert atras["y"] == d["anfitrion"]["y"] and atras["z"] != d["anfitrion"]["z"]


def test_de_6_a_4_vueltas_se_regeneran_los_pasos():
    m = construir(desde_datos(datos("redondo", vueltas=4, ahorcados=3)))
    assert m.fallas == []   # también las del error
    assert len(m.pasos) == 7
    assert len(m.pasos[-1].secuencia) // 2 == 3 * (2 * 4 - 1) + 4
