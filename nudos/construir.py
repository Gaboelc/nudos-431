"""Construye todos los pasos de un nudo, comprueba el resultado y lo guarda."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import BUILD
from .cruces import consistencia
from .errores import construir_error, construir_reverso
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
    error: Resultado | None = None     # el error común, si la especificación lo declara
    reverso: Resultado | None = None   # el último paso volteado: el nudo terminado por detrás (sin anfitrión)


def construir(spec: Spec) -> Modelo:
    fallas = consistencia([(p.n, p.secuencia) for p in spec.pasos])
    resultados = []
    for paso in spec.pasos:
        try:
            r = construir_paso(paso, spec.anfitrion, spec.cuerdas)
        except TrazadoError as e:
            fallas.append(str(e))
            continue
        resultados.append(r)
        fallas.extend(r.fallas)
    fallas.extend(cruces_que_saltan(resultados))
    por_n = {r.n: r for r in resultados}
    error, f_error = construir_error(spec, por_n.get(spec.error.paso) if spec.error else None)
    fallas.extend(f_error)
    reverso = None
    final = por_n.get(len(spec.pasos))
    # Un nudo sobre un anfitrión no se voltea: por detrás se mira desde el otro lado
    # (la vista «detras» de render/escena.js).
    if final is not None and spec.anfitrion is None:
        reverso, f_reverso = construir_reverso(spec, final)
        fallas.extend(f_reverso)
    return Modelo(spec, resultados, fallas, error, reverso)


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
        "pasos": [{"titulo": titulos[r.n][0], "texto": titulos[r.n][1], **_resultado_json(r)}
                  for r in modelo.pasos],
        "error": None if modelo.error is None else _resultado_json(modelo.error),
        "reverso": None if modelo.reverso is None else _resultado_json(modelo.reverso),
    }
    destino = BUILD / spec.slug / "modelo.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
    return destino


def _resultado_json(r: Resultado) -> dict:
    return {
        "n": r.n,
        "h": round(r.h, 6),
        "resaltado": None if r.resaltado is None else [round(v, 4) for v in r.resaltado],
        "cruces": {et: [round(x, 3), round(y, 3)] for et, (x, y) in r.cruces.items()},
        "secuencia": " ".join(r.secuencia),
        "medidas": {k: round(v, 4) for k, v in r.medidas.items()},
        "puntos": [[round(float(v), 4) for v in p] for p in r.puntos],
    }
