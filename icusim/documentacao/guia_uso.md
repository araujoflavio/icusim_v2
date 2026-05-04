# Guia de Uso — icusim

Este guia apresenta, de forma progressiva, como configurar e executar simulações com a biblioteca `icusim`.

---

## Sumário

1. [Estrutura do dicionário de configuração](#1-estrutura-do-dicionário-de-configuração)
2. [Simulação simples (uma rodada)](#2-simulação-simples-uma-rodada)
3. [Interpretando os resultados](#3-interpretando-os-resultados)
4. [Múltiplos grupos de pacientes](#4-múltiplos-grupos-de-pacientes)
5. [Múltiplas rodadas e intervalos de confiança](#5-múltiplas-rodadas-e-intervalos-de-confiança)
6. [Varredura do número de leitos](#6-varredura-do-número-de-leitos)
7. [Análise por paciente (dados_analise)](#7-análise-por-paciente-dados_analise)
8. [Boas práticas e configurações recomendadas](#8-boas-práticas-e-configurações-recomendadas)

---

## 1. Estrutura do dicionário de configuração

Todas as funções da biblioteca recebem um único dicionário `sim_data` com a seguinte estrutura:

```python
sim_data = {
    # ── Configuração global da simulação ──────────────────────────────────
    "dias": 365,         # int  — duração da simulação (excluindo aquecimento)
    "aquecimento": 30,   # int  — dias de warm-up descartados da análise
    "leitos": 20,        # int  — número de leitos da UTI

    # ── Grupos de pacientes ───────────────────────────────────────────────
    "paciente": [
        {
            "prefixo": "CLI",             # str   — identificador do grupo
            "prioridade": (2, 5),         # tuple — (min, max) da prioridade sorteada
            "novos_pacientes_dia": 3.0,   # float — taxa média de chegadas por dia
            "mean": 9.0,                  # float — média do tempo de internação (dias)
            "std_dev": 7.0,               # float — desvio padrão do tempo de internação (dias)
            "tempo_max_espera": (12, 96), # tuple — (min, max) em horas toleradas na fila
            "dias_semana": [0,1,2,3,4,5,6], # list — dias em que o grupo chega (0=seg, 6=dom)
        }
    ],
}
```

### Detalhamento dos parâmetros

#### Parâmetros globais

| Parâmetro    | Tipo  | Descrição |
|-------------|-------|-----------|
| `dias`      | `int` | Número de dias de simulação efetiva (após o aquecimento). |
| `aquecimento` | `int` | Período de warm-up em dias. Pacientes chegam normalmente, mas **não** são contabilizados nos resultados. Serve para estabilizar o estado do sistema antes da coleta. Recomendado: ao menos o dobro do tempo médio de internação. |
| `leitos`    | `int` | Capacidade total de leitos da UTI. |

#### Parâmetros por grupo de paciente

| Parâmetro              | Tipo             | Descrição |
|-----------------------|------------------|-----------|
| `prefixo`             | `str`            | Rótulo do grupo (ex.: `"CLI"`, `"CIR-eletivo"`). Usado como chave nos dicionários de resultado. |
| `prioridade`          | `tuple(int, int)`| Intervalo para sorteio uniforme da prioridade. **Menor valor = maior prioridade** (comportamento do SimPy). |
| `novos_pacientes_dia` | `float`          | Taxa média de novos pacientes por dia. O intervalo entre chegadas segue distribuição **Poisson** com média `24 / novos_pacientes_dia` horas. |
| `mean`                | `float`          | Média do tempo de internação em **dias**, usado como parâmetro da distribuição **Gamma**. |
| `std_dev`             | `float`          | Desvio padrão do tempo de internação em **dias**. |
| `tempo_max_espera`    | `tuple(int, int)`| Intervalo em **horas** para sorteio do tempo máximo de espera na fila. Se o paciente não for atendido nesse prazo, é registrado como **perda**. |
| `dias_semana`         | `list[int]`      | Dias da semana em que este grupo tem chegadas. `0` = segunda-feira, `6` = domingo. Útil para modelar cirurgias eletivas apenas em dias úteis. |

---

## 2. Simulação simples (uma rodada)

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
```

A função retorna um objeto `ICUSim` com os resultados já compilados em três atributos:

- `sim.compilado_geral` — totais e contagens
- `sim.compilado_analise` — métricas de desempenho
- `sim.dados_analise` — tabela individual por paciente

---

## 3. Interpretando os resultados

### `compilado_geral`

```python
for chave, valor in sim.compilado_geral.items():
    print(chave, "→", valor)
```

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `grupos` | `list[str]` | Lista dos prefixos de grupos presentes na simulação. |
| `total_pacientes` | `dict` | Total de solicitações de internação por grupo. |
| `pacientes_atendidos` | `dict` | Total de pacientes efetivamente internados por grupo. |
| `pacientes_perdidos` | `dict` | Total de pacientes que excederam o tempo máximo de espera por grupo. |
| `pacientes_aguardando` | `dict` | Pacientes que ainda estavam aguardando ao final da simulação por grupo. |
| `dias` | `int` | Número de dias efetivos de coleta (excluindo aquecimento). |
| `tempo_medio_internacao` | `float` | Tempo médio de internação dos pacientes atendidos (em horas). |

### `compilado_analise`

```python
for chave, valor in sim.compilado_analise.items():
    print(chave, "→", valor)
```

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `solicitacao_pendentedia_media` | `float` | Média diária de solicitações pendentes na fila. |
| `ocupacao_media` | `float` | Taxa de ocupação média dos leitos (0 a 1). |
| `dias_100_atendimento` | `float` | Proporção de dias em que a fila estava completamente vazia (taxa de serviço pleno). |
| `atendimento_medio` | `float` | Média de pacientes atendidos por dia. |
| `taxa_perda_grupo` | `dict` | Taxa de perda por grupo: `perdidos / (atendidos + perdidos)`. |
| `taxa_perda_total` | `float` | Taxa de perda agregada de todos os grupos. |
| `media_delta_espera_perdidos_total` | `float\|None` | Tempo médio (em horas) pelo qual os pacientes perdidos excederam o tempo máximo de espera. `None` se não houver perdas suficientes. |
| `media_delta_espera_perdidos_grupo` | `dict` | Idem, por grupo. |
| `media_tempo_espera_atendidos_total` | `float` | Tempo médio de espera na fila dos pacientes efetivamente atendidos (horas). |
| `media_tempo_espera_atendidos_grupo` | `dict` | Idem, por grupo. |

---

## 4. Múltiplos grupos de pacientes

Para modelar perfis distintos de pacientes (ex.: clínicos, cirúrgicos eletivos, cirúrgicos urgentes):

```python
sim_data = {
    "dias": 365,
    "aquecimento": 30,
    "leitos": 30,
    "paciente": [
        {
            "prefixo": "CLI",
            "prioridade": (2, 5),
            "novos_pacientes_dia": 3.0,
            "mean": 9.0,
            "std_dev": 7.0,
            "tempo_max_espera": (12, 96),
            "dias_semana": [0, 1, 2, 3, 4, 5, 6],
        },
        {
            "prefixo": "CIR-eletivo",
            "prioridade": (3, 5),        # menor urgência
            "novos_pacientes_dia": 1.5,
            "mean": 3.0,
            "std_dev": 1.5,
            "tempo_max_espera": (12, 48),
            "dias_semana": [0, 1, 2, 3, 4], # apenas dias úteis
        },
        {
            "prefixo": "CIR-urgente",
            "prioridade": (1, 2),        # alta prioridade
            "novos_pacientes_dia": 0.5,
            "mean": 7.0,
            "std_dev": 3.0,
            "tempo_max_espera": (2, 12), # baixa tolerância de espera
            "dias_semana": [0, 1, 2, 3, 4, 5, 6],
        },
    ],
}

sim = run_simulation(sim_data)
print(sim.compilado_geral["taxa_perda_grupo"])
# Ex.: {'CLI': 0.12, 'CIR-eletivo': 0.03, 'CIR-urgente': 0.21}
```

Os resultados em `compilado_geral` e `compilado_analise` são automaticamente desagregados por grupo via os prefixos definidos.

---

## 5. Múltiplas rodadas e intervalos de confiança

Por ser estocástica, a simulação produz resultados diferentes a cada execução. Para obter estimativas confiáveis, execute diversas rodadas e calcule intervalos de confiança:

```python
from icusim import run_multi_simulation
import pandas as pd

tabela = run_multi_simulation(sim_data, numero_simulacoes=30)
df = pd.DataFrame(tabela)
```

Cada linha de `df` corresponde a uma rodada. As métricas escalares ficam em colunas diretas. Para extrair média ± IC 95% de uma métrica:

```python
import numpy as np

ocupacoes = [t["ocupacao_media"] for t in tabela]
media = np.mean(ocupacoes)
ic95 = 1.96 * np.std(ocupacoes)
print(f"Ocupação: {media:.3f} ± {ic95:.3f}")
```

> **Regra prática**: use ao menos 30 rodadas para métricas agregadas; 50 ou mais para análises de cauda (ex.: dias sem fila).

---

## 6. Varredura do número de leitos

O parâmetro `multi_leitos` permite testar automaticamente uma faixa de configurações:

```python
tabela = run_multi_simulation(
    sim_data,
    numero_simulacoes=30,
    multi_leitos=(10, 40, 5),  # min=10, max=40 (inclusivo), passo=5
)

df = pd.DataFrame(tabela)

# Cada linha agora representa uma configuração de leitos (não uma rodada individual)
# com médias e desvios padrão já calculados
print(df[["leitos", "media_ocupacao_media", "media_taxa_perda_total"]])
```

O resultado inclui, para cada ponto da varredura, tuplas `(média, desvio_padrão)` para todas as métricas. Para extrair e plotar:

```python
import plotly.graph_objects as go

x = df["leitos"]
media = [v[0] for v in df["media_ocupacao_media"]]
dp    = [v[1] for v in df["media_ocupacao_media"]]

fig = go.Figure([
    go.Scatter(x=x, y=media, name="Ocupação média", mode="lines+markers"),
    go.Scatter(x=x, y=[m + 1.96*d for m,d in zip(media,dp)],
               line=dict(dash="dot"), showlegend=False),
    go.Scatter(x=x, y=[m - 1.96*d for m,d in zip(media,dp)],
               line=dict(dash="dot"), showlegend=False),
])
fig.update_layout(xaxis_title="Leitos", yaxis_title="Ocupação")
fig.show()
```

---

## 7. Análise por paciente (`dados_analise`)

`sim.dados_analise` é uma lista de dicionários, um por paciente registrado. Pode ser convertida em DataFrame para análises ad hoc:

```python
import pandas as pd

df_pac = pd.DataFrame(sim.dados_analise)
print(df_pac.columns.tolist())
```

### Colunas disponíveis

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `grupo` | `str` | Prefixo do grupo do paciente. |
| `prioridade` | `int` | Prioridade sorteada. |
| `aguardando` | `bool` | `True` se o paciente ainda estava na fila ao fim da simulação. |
| `aceito` | `bool` | `True` se o paciente obteve um leito. |
| `perda` | `bool\|None` | `True` se excedeu o tempo máximo de espera; `None` se nunca obteve leito. |
| `tempo_espera` | `float\|None` | Tempo na fila em horas. |
| `tempo_internacao` | `float\|None` | Duração efetiva da internação em horas. |
| `tempo_internacao_base` | `float` | Tempo de internação sorteado originalmente (horas). |
| `tempo_max_espera` | `int` | Tempo máximo de espera tolerado (horas). |
| `delta_espera` | `float\|None` | `tempo_max_espera - tempo_espera`. Negativo indica perda. |
| `taxa_espera` | `float\|None` | `tempo_espera / tempo_max_espera`. |
| `t0` | `float` | Instante de solicitação (horas de simulação). |
| `t1` | `float\|None` | Instante de início da internação. |
| `t2` | `float\|None` | Instante de alta (`-1` em caso de perda). |
| `status` | `str` | Estado final: `"solicitacao"`, `"internado"`, `"alta"` ou `"perda"`. |

### Exemplos de análise

```python
# Distribuição do tempo de internação por grupo
df_pac[df_pac["status"] == "alta"].groupby("grupo")["tempo_internacao"].describe()

# Comparar tempo de espera entre grupos
df_pac[df_pac["aceito"]].boxplot(column="tempo_espera", by="grupo")

# Taxa de perda por grupo
df_pac.groupby("grupo").apply(
    lambda g: g["perda"].sum() / (g["aceito"].sum() + g["perda"].sum())
)
```

---

## 8. Boas práticas e configurações recomendadas

### Período de aquecimento

O warm-up deve ser longo o suficiente para que o sistema atinja estado estacionário. Uma heurística simples:

```
aquecimento ≥ 2 × (tempo_médio_internação_em_dias × novos_pacientes_dia × leitos_esperados)
```

Para a maioria dos cenários clínicos, **30 dias** é um mínimo razoável.

### Número de rodadas

| Objetivo | Rodadas recomendadas |
|----------|----------------------|
| Estimativa rápida | 10 |
| Análise de intervalos de confiança | 30–50 |
| Publicação / validação | ≥ 100 |

### Calibração dos parâmetros de distribuição

Os tempos de internação são modelados com distribuição **Gamma**. Para calibrar `mean` e `std_dev` a partir de dados históricos:

```python
from scipy.stats import gamma
import numpy as np

dados = df_historico["tempo_internacao_dias"]
shape, loc, scale = gamma.fit(dados)

# Parâmetros para icusim
mean_calibrado  = shape * scale
std_calibrado   = np.sqrt(shape) * scale

print(f"mean={mean_calibrado:.2f}, std_dev={std_calibrado:.2f}")
```

### Prioridade

O SimPy usa convenção **menor número = maior prioridade**. Valores sugeridos:

| Urgência | Intervalo de prioridade |
|----------|------------------------|
| Emergência / pós-operatório urgente | `(1, 2)` |
| Clínicos graves | `(2, 4)` |
| Cirúrgicos eletivos | `(3, 5)` |
