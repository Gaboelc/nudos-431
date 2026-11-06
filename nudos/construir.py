"""Construye todos los pasos de un nudo, comprueba el resultado y lo guarda."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import BUILD
from .cruces import consistencia
from .libre import Resultado, TrazadoError, construir_paso
from .spec import Spec

# Cuánto puede moverse un cruce con la misma etiqueta entre dos pasos en que
# aparece. Más que esto sugiere que la etiqueta se reutilizó para otro cruce.
DESPLAZAMIENTO_MAX = 2.5   # diámetros


@dataclass
class Modelo:
    spec: Spec
    pasos: list[Resultado]
    fallas: list[str]


def construir(spec: Spec) -> Modelo:
    fallas = consistencia([(p.n, p.secuencia) for p in spec.pasos])
    resultados = []
    for paso in spec.pasos:
        try:
            r = construir_paso(paso)
        except TrazadoError as e:
            fallas.append(str(e))
            continue
        resultados.append(r)
        fallas.extend(r.fallas)
    fallas.extend(cruces_que_saltan(resultados))
    return Modelo(spec, resultados, fallas)


def cruces_que_saltan(resultados: list[Resultado]) -> list[str]:
    """Cruces que, con la misma etiqueta, aparecen lejos de donde estaban."""
    fallas = []
    ultimo: dict[str, tuple[int, tuple[float, float]]] = {}
    for r in resultados:
        for et, (x, y) in r.cruces.items():
            if et in ultimo:
                n0, (x0, y0) = ultimo[et]
                d = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
                if d > DESPLAZAMIENTO_MAX:
                    fallas.append(
                        f"Paso {r.n}: el cruce {et} está a {d:.1f} diámetros de donde estaba "
                        f"en el paso {n0}. ¿Es el mismo cruce? Si no, lleva otra etiqueta.")
            ultimo[et] = (r.n, (x, y))
    return fallas


def guardar(modelo: Modelo) -> Path:
    """Escribe build/<slug>/modelo.json y devuelve su ruta."""
    spec = modelo.spec
    titulos = {p.n: (p.titulo, p.texto) for p in spec.pasos}
    datos = {
        "slug": spec.slug,
        "nombre": spec.nombre,
        "familia": spec.familia,
        "abok": spec.abok,
        "encuadre": None if spec.encuadre is None else
        {"x": list(spec.encuadre.x), "y": list(spec.encuadre.y)},
        "fallas": modelo.fallas,
        "pasos": [
            {
                "n": r.n,
                "titulo": titulos[r.n][0],
                "texto": titulos[r.n][1],
                "h": round(r.h, 6),
                "resaltado": None if r.resaltado is None else [round(v, 4) for v in r.resaltado],
                "cruces": {et: [round(x, 3), round(y, 3)] for et, (x, y) in r.cruces.items()},
                "secuencia": " ".join(r.secuencia),
                "medidas": {k: round(v, 4) for k, v in r.medidas.items()},
                "puntos": [[round(float(v), 4) for v in p] for p in r.puntos],
            }
            for r in modelo.pasos
        ],
    }
    destino = BUILD / spec.slug / "modelo.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
    return destino
