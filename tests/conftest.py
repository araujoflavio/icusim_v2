"""
Fixtures e configurações compartilhadas entre os testes.
"""
import pytest


@pytest.fixture
def sim_data_simples():
    """Configuração mínima de simulação para uso nos testes."""
    return {
        "dias": 30,
        "aquecimento": 7,
        "leitos": 10,
        "paciente": [
            {
                "prefixo": "CLI",
                "prioridade": [2, 5],
                "novos_pacientes_dia": 2.0,
                "mean": 5.0,
                "std_dev": 2.0,
                "tempo_max_espera": [12, 48],
                "dias_semana": [0, 1, 2, 3, 4, 5, 6],
            }
        ],
    }


@pytest.fixture
def sim_data_multiplos_grupos():
    """Configuração com múltiplos grupos de pacientes."""
    return {
        "dias": 30,
        "aquecimento": 7,
        "leitos": 15,
        "paciente": [
            {
                "prefixo": "CLI",
                "prioridade": [2, 5],
                "novos_pacientes_dia": 2.0,
                "mean": 5.0,
                "std_dev": 2.0,
                "tempo_max_espera": [12, 48],
                "dias_semana": [0, 1, 2, 3, 4, 5, 6],
            },
            {
                "prefixo": "CIR",
                "prioridade": [1, 3],
                "novos_pacientes_dia": 1.0,
                "mean": 3.0,
                "std_dev": 1.5,
                "tempo_max_espera": [6, 24],
                "dias_semana": [0, 1, 2, 3, 4],
            },
        ],
    }
