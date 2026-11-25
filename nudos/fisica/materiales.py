"""Los parámetros de cada cuerda para el motor (T15).

Las unidades son las del motor: longitudes en diámetros de la cuerda y fuerzas en newtons, así
que una rigidez a la flexión va en N·d² y un peso por largo, en N por diámetro. Los valores de
cada cuerda están en `config/cuerdas.yaml`, en unidades de catálogo (`cuerda`). Los de la de 8 mm
(`CUERDA_8MM`) se midieron con cuerda real en T15e; `CUERDA_T14A` son los de partida de T14a,
para comparar.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import yaml

GRAVEDAD = 9.81  # m/s²


@dataclass(frozen=True)
class Material:
    """Una cuerda, en las unidades del motor."""
    diametro_m: float       # el diámetro, en metros: la unidad de largo del motor
    EA: float               # N: la rigidez a la tracción (estirarse un 1 % pide EA/100)
    EI: float               # N·d²: la rigidez a la flexión
    GJ: float               # N·d²: la rigidez a la torsión (hoy solo para medir; ver varilla.py)
    peso_por_d: float       # N por diámetro de largo
    mu_cuerda: float        # el roce de cuerda con cuerda (T15c)
    mu_madera: float        # el roce de cuerda con madera (T15c)
    # El roce de cuerda con metal (el destorcedor, T15f): el de una cuerda de nailon sobre acero,
    # de tabla. No se mide en T15e; si un nudo de metal lo pide, se mide como el de la madera.
    mu_metal: float = 0.3

    @classmethod
    def desde_si(cls, diametro_m: float, EA_n: float, EI_nm2: float, GJ_nm2: float,
                 masa_kg_m: float, mu_cuerda: float, mu_madera: float) -> "Material":
        """Desde las unidades de un catálogo o de una medición: N, N·m² y kg/m."""
        d = diametro_m
        return cls(diametro_m=d, EA=EA_n, EI=EI_nm2 / d ** 2, GJ=GJ_nm2 / d ** 2,
                   peso_por_d=masa_kg_m * GRAVEDAD * d, mu_cuerda=mu_cuerda, mu_madera=mu_madera)


CUERDAS = Path(__file__).resolve().parents[2] / "config" / "cuerdas.yaml"


def cuerda(nombre: str, ruta: Path = CUERDAS) -> Material:
    """La cuerda `nombre` de config/cuerdas.yaml. La torsión, que el motor no usa (T15b), es una
    cota alta: la de una varilla maciza con coeficiente de Poisson 0,5 (GJ = EI/1,5)."""
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if nombre not in datos:
        raise KeyError(f"config/cuerdas.yaml no tiene la cuerda «{nombre}»")
    c = datos[nombre]
    m = Material.desde_si(diametro_m=c["diametro_mm"] / 1000, EA_n=float(c["EA_n"]),
                          EI_nm2=float(c["EI_n_m2"]), GJ_nm2=float(c["EI_n_m2"]) / 1.5,
                          masa_kg_m=c["peso_g_m"] / 1000, mu_cuerda=float(c["roce_cuerda"]),
                          mu_madera=float(c["roce_madera"]))
    return replace(m, mu_metal=float(c["roce_metal"]))


# La cuerda trenzada de 8 mm de los nudos libres, medida en T15e.
CUERDA_8MM = cuerda("cuerda-8mm")

# La de partida de T14a, antes de medir: cuatro veces más rígida, el doble de pesada y con más
# roce con la madera (2·10⁻³ N·m², 45 g/m y 0,45).
CUERDA_T14A = Material.desde_si(
    diametro_m=0.008, EA_n=20000.0, EI_nm2=2.0e-3, GJ_nm2=2.0e-3 / 1.5,
    masa_kg_m=0.045, mu_cuerda=0.35, mu_madera=0.45)
