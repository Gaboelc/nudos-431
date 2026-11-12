"""La cabeza de turco: la segunda plantilla, tejida sobre un tubo (anfitrión «tubo»)."""
import copy

import numpy as np
import pytest

from nudos.anfitrion import PENETRACION_MAX, Tubo
from nudos.construir import DESPLAZAMIENTO_MAX, construir, guardar
from nudos.exportar import datos_visor
from nudos.hoja import mapa
from nudos.imprimir import imagenes
from nudos.cruces import numerada
from nudos.libre import LIMITES, Resultado, TrazadoError
from nudos.plantillas.cabeza_turco import (MESA, TUBO as TUBO_ZONA, CabezaDeTurco, Cuerda,
                                           buscar_en_el_tubo, cruces_del_centro, elegir_angulo,
                                           encima_del_centro, por_vuelta)
from nudos.spec import Anfitrion, SpecError, desde_datos

PASOS = [
    ("Da la primera vuelta", "vuelta-1"),
    ("Cruza por encima", "vuelta-2"),
    ("Empieza a tejer", "vuelta-3-mitad"),
    ("Termina de tejer", "vueltas"),
    ("Sigue el mismo camino", "pasadas"),
    ("Esconde los chicotes", "remate"),
]


def datos(**cambios):
    base = {
        "slug": "cabeza-de-turco",
        "nombre": "Cabeza de turco",
        "familia": "Decorativos",
        "anfitrion": {"tipo": "tubo", "radio": 4, "largo": 24},
        "plantilla": {"tipo": "cabeza-de-turco", "cabos": 3, "senos": 4, "pasadas": 2},
        "pasos": [{"titulo": t, "texto": "Texto.", "hasta": h} for t, h in PASOS],
        "error": {"paso": 3, "variante": "empieza-por-encima", "titulo": "Empieza por encima",
                  "texto": "Texto."},
    }
    base.update(copy.deepcopy(cambios))
    return base


def con(**cambios_plantilla):
    d = datos()
    d["plantilla"].update(cambios_plantilla)
    return d


# --- La especificación ----------------------------------------------------
def test_la_especificacion_se_lee():
    spec = desde_datos(datos())
    assert spec.anfitrion.tipo == "tubo"
    assert (spec.anfitrion.radio, spec.anfitrion.largo) == (4, 24)
    assert spec.plantilla == CabezaDeTurco(cabos=3, senos=4, pasadas=2)
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]
    assert all(p.puntos.shape == (0, 2) and p.secuencia == () for p in spec.pasos)
    assert spec.error.variante == "empieza-por-encima" and spec.error.invierte == ()


def test_los_hitos_siguen_la_cuerda():
    hitos = CabezaDeTurco(3, 4, 3).hitos()
    orden = ["vuelta-1-mitad", "vuelta-1", "vuelta-2-mitad", "vuelta-2", "vuelta-3-mitad",
             "vuelta-3", "pasada-2-mitad", "pasada-2", "pasada-3-mitad", "pasada-3", "remate"]
    assert [hitos[h] for h in orden] == list(range(len(orden)))
    # «vueltas» es la última vuelta y «pasadas» la última pasada.
    assert hitos["vueltas"] == hitos["vuelta-3"]
    assert hitos["pasadas"] == hitos["pasada-3"]


def test_con_una_pasada_las_pasadas_son_las_vueltas():
    hitos = CabezaDeTurco(2, 3, 1).hitos()
    assert list(hitos) == ["vuelta-1-mitad", "vuelta-1", "vuelta-2-mitad", "vuelta-2",
                           "vueltas", "pasadas", "remate"]
    assert hitos["pasadas"] == hitos["vueltas"] == hitos["vuelta-2"]
    d = con(cabos=2, senos=3, pasadas=1)
    d["pasos"] = [{"titulo": "T", "texto": "T.", "hasta": h} for h in ("vuelta-1", "vueltas", "remate")]
    del d["error"]
    assert [p.hasta for p in desde_datos(d).pasos] == ["vuelta-1", "vueltas", "remate"]


def test_las_medidas_salen_en_letras_en_todo_el_texto():
    d = con(pasadas=3)
    d["pasos"][1]["texto"] = "Cruza la primera vuelta {senos} menos una veces."
    d["pasos"][4]["titulo"] = "Completa las {pasadas} pasadas"
    d["error"]["otros"] = [{"titulo": "Apretado de una vez", "texto": "Son {cabos} vueltas."}]
    d["verificacion"] = ["Cuenta {senos} senos en cada borde."]
    spec = desde_datos(d)
    assert spec.pasos[1].texto == "Cruza la primera vuelta cuatro menos una veces."
    assert spec.pasos[4].titulo == "Completa las tres pasadas"
    assert spec.error.otros[0].texto == "Son tres vueltas."
    assert spec.verificacion == ("Cuenta cuatro senos en cada borde.",)
    assert CabezaDeTurco(5, 7, 1).medidas() == {"cabos": "cinco", "senos": "siete", "pasadas": "una"}


def test_una_medida_que_no_existe_en_el_texto():
    d = datos()
    d["pasos"][0]["texto"] = "Da {vueltas} vueltas."
    with pytest.raises(SpecError, match=r"«\{vueltas\}» no es una medida de la plantilla; puede "
                                        r"ser \{cabos\} o \{senos\} o \{pasadas\}"):
        desde_datos(d)


def test_cambiar_las_medidas_es_cambiar_un_numero():
    spec = desde_datos(con(senos=5, pasadas=3))
    assert spec.plantilla == CabezaDeTurco(3, 5, 3)
    assert [p.hasta for p in spec.pasos] == [h for _, h in PASOS]


@pytest.mark.parametrize("cambio, pista", [
    ({"tipo": "cabeza-de-moro"}, "«tipo» es uno de: amarre-cuadrado, cabeza-de-turco"),
    ({"cabos": 1}, "«cabos» es un número entero de 2 a 5"),
    ({"cabos": 6}, "«cabos» es un número entero de 2 a 5"),
    ({"senos": 8}, "«senos» es un número entero de 2 a 7"),
    ({"senos": 4.0}, "«senos» es un número entero"),
    ({"pasadas": 0}, "«pasadas» es un número entero de 1 a 3"),
    ({"pasadas": True}, "«pasadas» es un número entero"),
    ({"senos": 6}, "con 3 cabos y 6 senos salen 3 cuerdas cerradas"),
    ({"senos": 3}, "no pueden tener un divisor común aparte del 1"),
    ({"cabos": 4, "senos": 2}, "salen 2 cuerdas cerradas"),
    ({"vueltas": 3}, "campos desconocidos: vueltas"),
])
def test_una_plantilla_mal_escrita_se_detecta(cambio, pista):
    with pytest.raises(SpecError, match=pista):
        desde_datos(con(**cambio))


@pytest.mark.parametrize("cambio, pista", [
    ({"radio": 0.3}, "el radio del tubo es de al menos medio diámetro"),
    ({"largo": 8}, "«largo» es el largo del tubo; tiene que ser mayor que su grosor"),
    ({"desde": -10}, "campos desconocidos: desde"),
    ({"largo": None}, "falta «largo»"),
])
def test_un_tubo_mal_escrito_se_detecta(cambio, pista):
    d = datos()
    d["anfitrion"].update(cambio)
    if cambio == {"largo": None}:
        del d["anfitrion"]["largo"]
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_la_plantilla_necesita_el_tubo():
    with pytest.raises(SpecError, match="la plantilla cabeza-de-turco va sobre el anfitrión tubo"):
        desde_datos(datos(anfitrion={"tipo": "cruz", "radio": 2.5, "largo": 40}))
    sin = datos()
    del sin["anfitrion"]
    with pytest.raises(SpecError, match="va sobre el anfitrión tubo"):
        desde_datos(sin)


def test_el_tubo_necesita_una_plantilla():
    d = datos(segmentos={"a": [[0, 0], [1, 0]]},
              pasos=[{"titulo": "T", "texto": "T.", "trazado": ["a"], "secuencia": ""}])
    del d["plantilla"], d["error"]
    with pytest.raises(SpecError, match="el anfitrión tubo va con una plantilla, como cabeza-de-turco"):
        desde_datos(d)


@pytest.mark.parametrize("cambio, pista", [
    ({"hasta": "vuelta-4"}, "«hasta» es uno de: vuelta-1-mitad, vuelta-1, vuelta-2-mitad"),
    ({"hasta": "pasada-1"}, "«hasta» es uno de"),
    ({"trazado": ["a"]}, "no lleva «trazado»"),
    ({"secuencia": ""}, "no lleva «secuencia»"),
])
def test_errores_de_un_paso_de_plantilla(cambio, pista):
    d = datos()
    d["pasos"][1].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_los_pasos_avanzan_por_la_cuerda():
    d = datos()
    d["pasos"][3]["hasta"] = "vuelta-3-mitad"   # lo mismo que el paso 3
    with pytest.raises(SpecError, match="paso 4: «hasta: vuelta-3-mitad» no avanza"):
        desde_datos(d)
    d = con(pasadas=1)
    del d["pasos"][4]   # «pasadas» es «vueltas»: el paso 5 ya no avanzaría
    assert [p.hasta for p in desde_datos(d).pasos][-2:] == ["vueltas", "remate"]
    d = con(pasadas=1)
    with pytest.raises(SpecError, match="paso 5: «hasta: pasadas» no avanza"):
        desde_datos(d)


def test_el_ultimo_paso_llega_al_remate():
    d = datos()
    d["pasos"].pop()
    with pytest.raises(SpecError, match="paso 5: el último paso llega a «remate»"):
        desde_datos(d)


@pytest.mark.parametrize("cambio, pista", [
    ({"variante": "ahorcados-por-fuera"}, "«variante» es una de: empieza-por-encima"),
    ({"invierte": [1]}, "es una «variante» del método"),
    ({"paso": 2}, "se ve desde «vuelta-3-mitad», y el paso 2 llega solo a vuelta-2"),
])
def test_el_error_de_la_cabeza_de_turco(cambio, pista):
    d = datos()
    d["error"].update(cambio)
    with pytest.raises(SpecError, match=pista):
        desde_datos(d)


def test_empezar_por_encima_es_el_error_de_tres_cabos():
    for senos in (2, 4, 5, 7):
        assert CabezaDeTurco(3, senos, 1).VARIANTES == {"empieza-por-encima": "vuelta-3-mitad"}
    assert CabezaDeTurco(2, 3, 2).VARIANTES == {} and CabezaDeTurco(4, 5, 2).VARIANTES == {}
    d = con(cabos=4, senos=5)
    with pytest.raises(SpecError, match="con estas medidas, la plantilla cabeza-de-turco no sabe "
                                        "construir ningún error común"):
        desde_datos(d)
    del d["error"]
    assert desde_datos(d).plantilla == CabezaDeTurco(4, 5, 2)


# --- El camino del centro -----------------------------------------------------
@pytest.mark.parametrize("cabos, senos", [(2, 3), (2, 7), (3, 2), (3, 4), (3, 5), (3, 7), (4, 5),
                                          (5, 2), (5, 7)])
def test_el_centro_se_cruza_senos_por_cabos_menos_uno_veces(cabos, senos):
    cruces = cruces_del_centro(cabos, senos)
    assert len(cruces) == senos * (cabos - 1)
    # Alterna a lo largo de la cuerda, y cada cruce tiene una pasada por encima y otra por debajo.
    pasadas = encima_del_centro(cabos, senos)
    assert all(a != b for (_, a, _), (_, b, _) in zip(pasadas, pasadas[1:]))
    lados = {}
    for _, o, k in pasadas:
        lados.setdefault(k, []).append(o)
    assert all(sorted(v) == [False, True] for v in lados.values())
    # Ningún cruce cae a menos de P / (2 cabos) de un ápice (P = 1).
    for t in (t for c in cruces for t in c):
        assert min(t % 0.5, 0.5 - t % 0.5) >= 1 / (2 * cabos) - 1e-9


@pytest.mark.parametrize("senos, segunda, tercera", [
    (2, "OO", "UO"), (4, "OOO", "UOUOU"), (5, "OOOO", "UOUOUO"), (7, "OOOOO", "UOUOUOUOU")])
def test_con_tres_cabos_la_segunda_vuelta_va_toda_por_encima(senos, segunda, tercera):
    """El método clásico: la primera vuelta no cruza nada, la segunda cruza la primera siempre
    por encima y la tercera teje empezando por debajo."""
    vueltas = ["".join("O" if o else "U" for o in v) for v in por_vuelta(3, senos)]
    assert vueltas == ["", segunda, tercera]


def test_con_cuatro_cabos_la_segunda_vuelta_ya_alterna():
    assert ["".join("O" if o else "U" for o in v) for v in por_vuelta(4, 5)][1] == "OU"


def test_ningun_paso_tiene_firme():
    assert CabezaDeTurco.CON_FIRME == ()


# --- El tubo ------------------------------------------------------------------
TUBO = Anfitrion("tubo", radio=4.0, largo=24.0)


def test_el_tubo_se_apoya_sobre_dos_capas_de_cuerda():
    t = Tubo(TUBO)
    assert t.zc == pytest.approx(6.0) and t.rb == pytest.approx(4.5)
    x, a, r = t.cilindricas(np.array([t.punto(2.0, 90.0), t.punto(-3.0, 0.0, r=5.5)]))
    assert np.allclose(x, [2, -3]) and np.allclose(np.degrees(a), [90, 0]) and np.allclose(r, [4.5, 5.5])
    assert t.punto(0.0, 90.0)[1] < 0   # 90° es hacia quien ata


def test_empujar_saca_lo_que_entro_al_tubo():
    t = Tubo(TUBO)
    X = np.array([[1.0, 0.0, t.zc + 2.0], [13.0, 0.0, t.zc], [0.0, 0.0, t.zc + 6.0]])
    assert t.penetracion(X) == pytest.approx(t.rb - 2.0)
    t.empujar(X, np.ones(3, bool))
    assert t.penetracion(X) == pytest.approx(0, abs=1e-9)
    assert np.allclose(X[1], [13, 0, t.zc])   # fuera del largo del tubo no se toca
    assert np.allclose(X[2], [0, 0, t.zc + 6])


def test_girar_media_vuelta_es_rigido():
    t = Tubo(TUBO)
    X = np.array([t.punto(1.0, 30.0), t.punto(-2.0, 200.0, r=5.5)])
    r = Resultado(n=6, puntos=X, h=0.2, resaltado=(0, 1), cruces={"1": (1.0, 2.0)},
                  secuencia=["1O", "1U"], esperada=["1O", "1U"], medidas={"altura_max": 0.0},
                  giro=10.0)
    v = t.voltear(r)
    _, a, rr = t.cilindricas(v.puntos)
    assert np.allclose(np.degrees(a) % 360, [210, 20]) and np.allclose(rr, [4.5, 5.5])
    assert v.cruces == r.cruces and v.secuencia == r.secuencia and v.resaltado is None
    assert v.giro == 190.0


# --- La cuerda entera -------------------------------------------------------------
def la_cuerda(cabos=3, senos=4, pasadas=2, radio=4.0, variante=None):
    p = CabezaDeTurco(cabos, senos, pasadas)
    tubo = Tubo(Anfitrion("tubo", radio=radio, largo=24.0))
    return Cuerda(p, tubo, elegir_angulo(p, radio), variante)


def test_el_angulo_es_el_menor_con_el_que_cabe():
    """Con 3 cabos, 4 senos y dos pasadas, en un tubo de radio 4: 55°. Con una pasada cabe con
    45°, y en un tubo de radio 2 con dos pasadas no cabe con ninguno: la falla dice el mínimo."""
    assert elegir_angulo(CabezaDeTurco(3, 4, 2), 4.0) == 55.0
    assert elegir_angulo(CabezaDeTurco(3, 4, 1), 4.0) == 45.0
    with pytest.raises(TrazadoError, match="no cabe en un tubo de radio 2: .* El radio mínimo es [0-9]"):
        elegir_angulo(CabezaDeTurco(3, 4, 2), 2.0)


@pytest.mark.parametrize("cabos, senos, pasadas, radio", [
    (3, 4, 2, 4.0), (3, 4, 1, 4.0), (3, 4, 3, 5.5), (2, 3, 2, 4.0), (4, 5, 1, 6.0), (3, 7, 1, 6.0)])
def test_la_secuencia_del_metodo(cabos, senos, pasadas, radio):
    """Senos × (cabos − 1) × pasadas² cruces, más uno por pasada del extremo corto metido, que
    va por debajo. A lo largo de la cuerda alterna por cabos: cada cabo pasa por todas las
    pasadas del otro en un cruce del centro del mismo lado, y en el siguiente, del otro."""
    c = la_cuerda(cabos, senos, pasadas, radio)
    sec = c.secuencias["remate"]
    assert len(sec) // 2 == senos * (cabos - 1) * pasadas ** 2 + pasadas
    corto = [x for x in c.cruces if x.T[0] is None]
    assert len(corto) == pasadas and all(not x.encima for x in corto)
    o = c.onda
    centro = np.array(sorted(t for par in cruces_del_centro(cabos, senos, o.P) for t in par))
    pasadas_cuerpo = sorted((T, (x.encima if i == 0 else not x.encima))
                            for x in c.cruces if x not in corto for i, T in enumerate(x.T))
    grupos = []
    for T, arriba in pasadas_cuerpo:
        k = int(np.abs(((T % o.LC) - centro + o.LC / 2) % o.LC - o.LC / 2).argmin())
        clave = (k, T // o.LC)
        if grupos and grupos[-1][0] == clave:
            grupos[-1][1].append(arriba)
        else:
            grupos.append((clave, [arriba]))
    assert all(len(set(v)) == 1 for _, v in grupos)
    lados = [v[0] for _, v in grupos]
    assert all(a != b for a, b in zip(lados, lados[1:]))


def test_los_hitos_avanzan_por_la_cuerda():
    c = la_cuerda()
    orden = [h for h in c.p.hitos() if h not in c.alias]
    T = [c.hitos_T[h] for h in orden]
    assert c.t0 < T[0] and all(a < b for a, b in zip(T, T[1:]))
    assert c.T_de("vueltas") == c.hitos_T["vuelta-3"] and c.T_de("pasadas") == c.hitos_T["pasada-2"]
    # Con tres cabos, la segunda vuelta va toda por encima: los tres cruces que forma.
    assert [t for t in c.secuencias["vuelta-2"] if t[-1] == "O"] == ["1O", "2O", "3O"]
    assert len(c.secuencias["vuelta-1"]) == 0 and len(c.secuencias["vuelta-2"]) == 6
    assert len(c.secuencias["vueltas"]) // 2 == 8 and len(c.secuencias["pasadas"]) // 2 == 30


def test_el_extremo_corto_es_lo_unico_que_cambia_en_el_remate():
    """El cuerpo, con sus alturas, es el mismo con el extremo corto que cuelga y con el metido:
    la banda que lo tapa va por encima desde el principio."""
    c = la_cuerda()
    h_cuelga, _ = c.alturas(False)
    h_metido, _ = c.alturas(True)
    n = len(c._M)
    assert np.allclose(h_cuelga[-n:], h_metido[-n:])


def test_el_error_empieza_a_tejer_por_encima():
    """La tercera vuelta del error forma los mismos cruces que la bien hecha, todos al revés; lo
    de antes no cambia."""
    bien = la_cuerda().secuencias
    mal = la_cuerda(variante="empieza-por-encima").secuencias
    assert mal["vuelta-2"] == bien["vuelta-2"]
    distintos = {t[:-1] for t, u in zip(bien["vuelta-3-mitad"], mal["vuelta-3-mitad"]) if t != u}
    assert distintos == {"4", "5", "6"}
    assert [t[:-1] for t in bien["vueltas"]] == [t[:-1] for t in mal["vueltas"]]
    with pytest.raises(ValueError, match="no tiene la variante"):
        la_cuerda(cabos=4, senos=5, pasadas=1, radio=6.0, variante="empieza-por-encima")


def test_los_cruces_del_tubo_se_buscan_en_su_superficie():
    """Dos tramos que se cruzan alrededor del tubo: encima, el más lejos del eje. Si uno va en
    la zona de la mesa, no se busca."""
    t = Tubo(TUBO)
    a = np.array([t.punto(x, 30.0 + 10 * x) for x in np.linspace(-1, 1, 11)])
    b = np.array([t.punto(x, 30.0 - 10 * x, r=5.5) for x in np.linspace(1, -1, 11)])
    X = np.vstack([a, b])
    zonas = np.full(len(X), TUBO_ZONA)
    zonas[10] = -1   # el salto entre los dos tramos no es cuerda
    cruces, alturas = buscar_en_el_tubo(X, 1.0, zonas, t, 0.0, 4)
    assert len(cruces) == 1 and alturas[0][1] > alturas[0][0]
    zonas[11:] = MESA
    assert buscar_en_el_tubo(X, 1.0, zonas, t, 0.0, 4)[0] == []


# --- El nudo ------------------------------------------------------------------
@pytest.fixture(scope="module")
def modelo():
    """La cabeza de turco de datos(): 3 cabos, 4 senos y dos pasadas en un tubo de radio 4."""
    return construir(desde_datos(datos()))


def test_todos_los_pasos_se_construyen_sin_fallas(modelo):
    assert modelo.fallas == []
    assert [r.n for r in modelo.pasos] == list(range(1, 7))
    assert modelo.error is not None and modelo.error.n == 3
    assert modelo.apretado is None   # un nudo de plantilla no se aprieta


def test_la_cuerda_no_atraviesa_el_tubo_ni_otras_vueltas(modelo):
    for r in [*modelo.pasos, modelo.error]:
        m = r.medidas
        assert m["penetracion_tubo"] <= PENETRACION_MAX, r.n
        assert m["separacion_min"] >= LIMITES["separacion_min"], r.n
        assert m["curvatura_min"] >= LIMITES["curvatura_min"], r.n
        assert m["estiramiento_max"] <= LIMITES["estiramiento_max"], r.n


def test_el_tejido_alterna_sobre_el_tubo(modelo):
    """El primer criterio de aceptación: la secuencia de cada paso, medida en la cuerda
    relajada sobre el tubo, es la del método, que alterna por cabos."""
    c = la_cuerda()
    for r, (_, hasta) in zip(modelo.pasos, PASOS):
        assert r.secuencia == r.esperada == numerada(c.secuencias[hasta]), r.n
    assert len(modelo.pasos[-1].secuencia) // 2 == 34   # 32 y los 2 del extremo corto metido
    e = modelo.error
    variante = la_cuerda(variante="empieza-por-encima").secuencias["vuelta-3-mitad"]
    assert e.secuencia == e.esperada == numerada(variante)


def test_cada_paso_resalta_lo_que_agrega_y_lo_pone_de_frente(modelo):
    for r in modelo.pasos:
        desde, hasta = r.resaltado
        assert hasta > desde, r.n
    assert len({round(r.giro) for r in modelo.pasos}) == len(modelo.pasos)


def test_un_cruce_conserva_su_etiqueta_y_su_lugar_en_el_mapa(modelo):
    final = modelo.pasos[-1].cruces
    for r in modelo.pasos[:-1]:
        assert set(r.cruces) <= set(final), r.n
        for et, (x, u) in r.cruces.items():
            assert np.hypot(x - final[et][0], u - final[et][1]) <= DESPLAZAMIENTO_MAX, (r.n, et)


@pytest.mark.parametrize("cabos, senos, pasadas, radio", [(3, 4, 1, 4.0), (2, 3, 2, 4.0), (3, 4, 3, 5.5)])
def test_otras_medidas_se_regeneran_sin_fallas(cabos, senos, pasadas, radio):
    d = datos(anfitrion={"tipo": "tubo", "radio": radio, "largo": 24})
    d["plantilla"].update(cabos=cabos, senos=senos, pasadas=pasadas)
    pasos = ["vuelta-1", f"vuelta-{cabos}-mitad", "vueltas"]
    pasos += (["pasadas"] if pasadas > 1 else []) + ["remate"]
    d["pasos"] = [{"titulo": "T", "texto": "T.", "hasta": h} for h in pasos]
    if cabos != 3:
        del d["error"]
    else:
        d["error"]["paso"] = 2   # el error se ve desde la mitad de la tercera vuelta
    m = construir(desde_datos(d))
    assert m.fallas == []
    assert len(m.pasos[-1].secuencia) // 2 == senos * (cabos - 1) * pasadas ** 2 + pasadas


# --- Escena, impresión y hoja -------------------------------------------------
def test_la_escena_dibuja_el_tubo(modelo):
    d = datos_visor(modelo)
    assert d["anfitrion"] == Tubo(TUBO).datos() == {"tipo": "tubo", "radio": 4.0, "largo": 24.0, "z": 6.0}
    assert d["dos_remates"] is True
    # Ningún paso tiene firme: la cuerda va desde el extremo corto y solo lleva «Chicote».
    for paso, r in zip(d["pasos"], modelo.pasos):
        p = np.reshape(paso["p"], (-1, 3))
        assert np.allclose(p[0], r.puntos[0], atol=1e-3) and paso["nombres"] == ["chicote"], r.n


def test_cada_paso_guarda_su_giro(modelo, tmp_path, monkeypatch):
    import json

    import nudos.construir as c
    monkeypatch.setattr(c, "BUILD", tmp_path)
    datos = json.loads(guardar(modelo).read_text(encoding="utf-8"))
    assert [p["giro"] for p in datos["pasos"]] == [round(r.giro, 4) for r in modelo.pasos]
    assert "giro" in datos["error"]


def test_las_imagenes_de_la_cabeza_de_turco(modelo):
    imgs = imagenes(modelo)
    assert [i.nombre for i in imgs] == [f"paso-{n}" for n in range(1, 7)] + [
        "error-correcto", "error", "terminado-frente", "terminado-reverso"]
    assert {i.vista for i in imgs} == {"3d"}   # todo como los pasos, también el terminado
    por_nombre = {i.nombre: i for i in imgs}
    bien, mal = por_nombre["error-correcto"], por_nombre["error"]
    assert bien.escena is mal.escena and [p["n"] for p in bien.escena["pasos"]] == [3, 3]
    # Por delante, el remate; por detrás, el mismo nudo girado media vuelta con el tubo.
    frente, reverso = por_nombre["terminado-frente"], por_nombre["terminado-reverso"]
    X = np.reshape(frente.escena["pasos"][0]["p"], (-1, 3))
    Y = np.reshape(reverso.escena["pasos"][0]["p"], (-1, 3))
    assert np.allclose(Y[:, 0], X[:, 0]) and np.allclose(Y[:, 1], -X[:, 1], atol=2e-3)
    assert np.allclose(Y[:, 2] + X[:, 2], 2 * Tubo(TUBO).zc, atol=2e-3)
    assert frente.escena["anfitrion"] == reverso.escena["anfitrion"] == Tubo(TUBO).datos()


def test_la_hoja_desenrolla_el_tubo(modelo, tmp_path, monkeypatch):
    import json

    import nudos.construir as c
    monkeypatch.setattr(c, "BUILD", tmp_path)
    datos = json.loads(guardar(modelo).read_text(encoding="utf-8"))
    im = mapa(datos, Tubo(TUBO), 4)
    assert im.width > im.height > 0
    a = np.asarray(im.convert("RGB")).astype(int)
    rojo = (a[..., 0] > 120) & (a[..., 1] < 60) & (a[..., 2] < 60)   # las etiquetas de los cruces
    assert rojo.any()
