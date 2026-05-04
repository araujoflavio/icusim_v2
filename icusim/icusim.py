# ---------------------------------------------------------------------------
# Shim de compatibilidade retroativa
# ---------------------------------------------------------------------------
# Este módulo existia como implementação monolítica da biblioteca.
# O código foi reorganizado nos módulos:
#   - icusim.simulation  ->  class ICUSim
#   - icusim.runners     ->  run_simulation, run_multi_simulation
#   - icusim.stats       ->  calcula_media_desvio, calcula_media_desvio_por_grupo
#
# Importe preferencialmente a partir do pacote raiz:
#   from icusim import ICUSim, run_simulation, run_multi_simulation
# ---------------------------------------------------------------------------

from .simulation import ICUSim  # noqa: F401
from .runners import run_simulation, run_multi_simulation  # noqa: F401
from .stats import calcula_media_desvio, calcula_media_desvio_por_grupo  # noqa: F401

__all__ = [
    "ICUSim",
    "run_simulation",
    "run_multi_simulation",
    "calcula_media_desvio",
    "calcula_media_desvio_por_grupo",
]

# ---------------------------------------------------------------------------
# Bloco de teste rapido (execucao direta: python -m icusim.icusim)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _sim_data = {
        "dias": 30,
        "aquecimento": 0,
        "leitos": 40,
        "paciente": [
            {
                "prefixo": "cli",
                "prioridade": (1, 4),
                "novos_pacientes_dia": 2,
                "mean": 12,
                "std_dev": 2,
                "tempo_max_espera": (12, 96),
                "dias_semana": [0, 1, 2, 3, 4, 5, 6],
            },
        ],
    }
    _sim = run_simulation(_sim_data)
    print("compilado_geral:")
    for k, v in _sim.compilado_geral.items():
        print(f"  {k}: {v}")
    print("compilado_analise:")
    for k, v in _sim.compilado_analise.items():
        print(f"  {k}: {v}")
