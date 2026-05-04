"""
icusim
------
Biblioteca para simulação de Unidades de Terapia Intensiva (UTI)
via Discrete Event Simulation (DES).

Uso básico::

    from icusim import ICUSim, run_simulation, run_multi_simulation
"""

from .simulation import ICUSim
from .runners import run_simulation, run_multi_simulation
from .stats import calcula_media_desvio, calcula_media_desvio_por_grupo

__all__ = [
    "ICUSim",
    "run_simulation",
    "run_multi_simulation",
    "calcula_media_desvio",
    "calcula_media_desvio_por_grupo",
]
