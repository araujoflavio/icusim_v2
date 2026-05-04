# icusim — Simulador de UTI por Eventos Discretos

`icusim` é uma biblioteca Python para simulação estocástica de Unidades de Terapia Intensiva (UTI) utilizando **Discrete Event Simulation (DES)**. Ela permite modelar o fluxo de pacientes, a ocupação de leitos e a taxa de perda sob diferentes configurações operacionais.

---

## Visão Geral

A biblioteca modela os seguintes elementos:

- **Leitos** como um recurso compartilhado com capacidade limitada e disciplina de fila por prioridade.
- **Grupos de pacientes** com perfis distintos de chegada, tempo de internação e tolerância de espera.
- **Período de aquecimento (warm-up)** para estabilização da simulação antes da coleta de dados.
- **Múltiplas rodadas** com agregação estatística para análise de intervalos de confiança.

### Arquitetura do pacote

```
icusim/
├── __init__.py       ← API pública exportada
├── simulation.py     ← class ICUSim (motor de simulação SimPy)
├── runners.py        ← run_simulation, run_multi_simulation
├── stats.py          ← funções auxiliares de agregação estatística
└── icusim.py         ← shim de compatibilidade retroativa
```

---

## Instalação

### Pré-requisitos

- Python 3.10 ou superior
- Ambiente conda (recomendado): `icusim`

### Via conda

```bash
conda activate icusim
pip install -r requirements.txt
```

### Dependências principais

| Pacote   | Uso |
|----------|-----|
| `simpy`  | Motor de Discrete Event Simulation |
| `numpy`  | Sorteio de distribuições e cálculos numéricos |
| `pandas` | Manipulação de resultados em análises externas |
| `plotly` | Visualizações interativas |
| `scipy`  | Análises estatísticas complementares |

---

## Início Rápido

```python
from icusim import run_simulation

sim_data = {
    "dias": 365,
    "aquecimento": 30,
    "leitos": 20,
    "paciente": [
        {
            "prefixo": "CLI",
            "prioridade": (2, 5),
            "novos_pacientes_dia": 3.0,
            "mean": 9.0,
            "std_dev": 7.0,
            "tempo_max_espera": (12, 96),
            "dias_semana": [0, 1, 2, 3, 4, 5, 6],
        }
    ],
}

sim = run_simulation(sim_data)

print("Ocupação média:  ", round(sim.compilado_analise["ocupacao_media"], 3))
print("Taxa de perda:   ", round(sim.compilado_analise["taxa_perda_total"], 3))
print("Pacientes atendidos:", sim.compilado_geral["pacientes_atendidos"])
```

### Simulação múltipla com varredura de leitos

```python
from icusim import run_multi_simulation
import pandas as pd

tabela = run_multi_simulation(
    sim_data,
    numero_simulacoes=30,
    multi_leitos=(10, 40, 5),  # de 10 a 40 leitos, passo 5
)

df = pd.DataFrame(tabela)
print(df[["leitos", "media_ocupacao_media", "media_taxa_perda_total"]])
```

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [Guia de Uso](guia_uso.md) | Passo a passo com exemplos completos |
| [Referência da API](referencia_api.md) | Parâmetros, retornos e comportamentos de cada símbolo público |
| [Conceitos](conceitos.md) | Teoria por trás do modelo: DES, distribuição Gamma, fila por prioridade |

---

## API Pública Resumida

```python
from icusim import (
    ICUSim,                        # classe do motor de simulação
    run_simulation,                # executa uma única rodada
    run_multi_simulation,          # executa múltiplas rodadas / varredura de leitos
    calcula_media_desvio,          # agrega lista numérica → (média, dp)
    calcula_media_desvio_por_grupo,# agrega lista de dicts → {grupo: (média, dp)}
)
```
