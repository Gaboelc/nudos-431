"""Los parámetros de cada cuerda para el motor (T15).

Las unidades son las del motor: longitudes en diámetros de la cuerda y fuerzas en newtons, así
que una rigidez a la flexión va en N·d² y un peso por largo, en N por diámetro. Los valores de
`CUERDA_8MM` son los de partida de T14a; los de `config/cuerdas.yaml`, uno por tipo de cuerda,
se calibran con cuerda real en T15e.
"""
from __future__ import annotations

from dataclasses import dataclass

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


# La cuerda trenzada de 8 mm de los nudos libres (T14a): se estira un 0,5 % con 100 N, su
# rigidez a la flexión es la de 2·10⁻³ N·m² y pesa 45 g/m. La torsión es una cota alta, la de
# una varilla maciza con coeficiente de Poisson 0,5 (GJ = EI/(1 + ν)); una cuerda trenzada se
# tuerce con menos. El roce es el de T14a.
CUERDA_8MM = Material.desde_si(
    diametro_m=0.008, EA_n=20000.0, EI_nm2=2.0e-3, GJ_nm2=2.0e-3 / 1.5,
    masa_kg_m=0.045, mu_cuerda=0.35, mu_madera=0.45)
