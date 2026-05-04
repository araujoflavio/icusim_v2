# Referência da API — icusim

Documentação completa de todos os símbolos públicos exportados pelo pacote `icusim`.

```python
from icusim import (
    ICUSim,
    run_simulation,
    run_multi_simulation,
    calcula_media_desvio,
    calcula_media_desvio_por_grupo,
)
```

---

## Sumário

- [`run_simulation(sim_data)`](#run_simulationsim_data)
- [`run_multi_simulation(sim_data, numero_simulacoes, multi_leitos)`](#run_multi_simulationsim_data-numero_simulacoes-multi_leitos)
- [`ICUSim`](#icusim-1)
  - [`__init__`](#icusiminit)
  - [Atributos de resultado](#atributos-de-resultado)
  - [`paciente()`](#icusimpaciente)
  - [`cria_paciente()`](#icusimcria_paciente)
  - [`adiciona_paciente()`](#icusimadiciona_paciente)
  - [`checa_censo()`](#icusimcheca_censo)
- [`calcula_media_desvio(dados)`](#calcula_media_desviodados)
- [`calcula_media_desvio_por_grupo(data)`](#calcula_media_desvio_por_grupodata)

---

## `run_simulation(sim_data)`

**Módulo:** `icusim.runners`

Executa uma única rodada de simulação e retorna o objeto `ICUSim` com os resultados compilados.

### Assinatura

```python
def run_simulation(sim_data: dict) -> ICUSim
```

### Parâmetros

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `sim_data` | `dict` | Dicionário de configuração da simulação. Ver estrutura completa em [Guia de Uso § 1](guia_uso.md#1-estrutura-do-dicionário-de-configuração). |

**Chaves obrigatórias de `sim_data`:**

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `dias` | `int` | Duração da simulação em dias (excluindo aquecimento). |
| `aquecimento` | `int` | Dias de warm-up descartados da análise. |
| `leitos` | `int` | Número de leitos da UTI. |
| `paciente` | `list[dict]` | Lista de grupos de pacientes (ao menos um). |

**Chaves obrigatórias por grupo em `paciente`:**

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `prefixo` | `str` | Identificador do grupo. |
| `prioridade` | `tuple(int, int)` | Intervalo `(min, max)` para sorteio da prioridade. |
| `novos_pacientes_dia` | `float` | Taxa média de chegadas diárias. |
| `mean` | `float` | Média do tempo de internação em dias (parâmetro Gamma). |
| `std_dev` | `float` | Desvio padrão do tempo de internação em dias (parâmetro Gamma). |
| `tempo_max_espera` | `tuple(int, int)` | Intervalo `(min, max)` em horas para tolerância na fila. |
| `dias_semana` | `list[int]` | Dias de chegada (0 = segunda, 6 = domingo). |

### Retorno

Objeto `ICUSim` com os atributos:

| Atributo | Tipo | Conteúdo |
|----------|------|----------|
| `compilado_geral` | `dict` | Totais e contagens gerais. |
| `compilado_analise` | `dict` | Métricas de desempenho operacional. |
| `dados_analise` | `list[dict]` | Registro individual de cada paciente. |

### Exceções

| Exceção | Condição |
|---------|----------|
| `ValueError` | Chave obrigatória ausente em `sim_data` ou em um grupo de paciente. |

### Exemplo

```python
from icusim import run_simulation

sim = run_simulation({
    "dias": 90, "aquecimento": 14, "leitos": 15,
    "paciente": [{
        "prefixo": "CLI", "prioridade": (2, 4),
        "novos_pacientes_dia": 2.0, "mean": 7.0, "std_dev": 5.0,
        "tempo_max_espera": (12, 72), "dias_semana": [0,1,2,3,4,5,6],
    }]
})

print(sim.compilado_analise["ocupacao_media"])   # → float [0, 1]
print(sim.compilado_analise["taxa_perda_total"]) # → float [0, 1]
```

---

## `run_multi_simulation(sim_data, numero_simulacoes, multi_leitos)`

**Módulo:** `icusim.runners`

Executa múltiplas rodadas de simulação e agrega os resultados estatisticamente. Suporta dois modos: **ponto fixo** (repete o mesmo número de leitos) e **varredura de leitos** (itera sobre uma faixa).

### Assinatura

```python
def run_multi_simulation(
    sim_data: dict,
    numero_simulacoes: int = 10,
    multi_leitos: tuple[int, int, int] | bool = False,
) -> list[dict]
```

### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `sim_data` | `dict` | — | Configuração da simulação (mesma estrutura de `run_simulation`). |
| `numero_simulacoes` | `int` | `10` | Número de rodadas por configuração de leitos. |
| `multi_leitos` | `tuple(int,int,int)` ou `False` | `False` | Tupla `(min, max_inclusivo, passo)` para varredura de leitos. Quando `False`, usa `sim_data["leitos"]` fixo. |

### Retorno

#### Com `multi_leitos=False` (ponto fixo)

Lista de dicionários, um por rodada, com os campos brutos de `compilado_geral` + `compilado_analise` + `{"simulacao": i}`.

#### Com `multi_leitos=(min, max, passo)` (varredura)

Lista de dicionários, um por configuração de leitos testada. Cada dicionário contém:

| Chave | Tipo | Descrição |
|-------|------|-----------|
| `leitos` | `int` | Número de leitos desta configuração. |
| `media_dias` | `float` | Média do número de dias de coleta entre as rodadas. |
| `simulacoes` | `int` | Número de rodadas executadas. |
| `total_pacientes_criados` | `dict` | Total acumulado de solicitações por grupo em todas as rodadas. |
| `media_pacientes_criados` | `dict[str, tuple]` | `{grupo: (média, dp)}` de solicitações por rodada. |
| `media_pacientes_criados_dia` | `dict[str, tuple]` | `{grupo: (média, dp)}` de solicitações por dia. |
| `media_pacientes_atendidos` | `dict[str, tuple]` | `{grupo: (média, dp)}` de internações por dia. |
| `media_pacientes_perdidos` | `dict[str, tuple]` | `{grupo: (média, dp)}` de perdas por dia. |
| `media_pacientes_aguardando` | `dict[str, tuple]` | `{grupo: (média, dp)}` de pendentes ao final. |
| `media_tempo_medio_internacao` | `tuple(float, float)` | `(média, dp)` do tempo médio de internação (horas). |
| `media_ocupacao_media` | `tuple(float, float)` | `(média, dp)` da taxa de ocupação. |
| `media_dias_100_atendimento` | `tuple(float, float)` | `(média, dp)` da proporção de dias com fila vazia. |
| `media_taxa_perda_total` | `tuple(float, float)` | `(média, dp)` da taxa de perda total. |
| `taxa_perda_grupo` | `dict[str, tuple]` | `{grupo: (média, dp)}` da taxa de perda por grupo. |
| `media_delta_espera_perdidos_total` | `tuple(float, float)` | `(média, dp)` do excesso de espera dos pacientes perdidos (horas). |
| `media_delta_espera_perdidos_grupo` | `dict[str, tuple]` | Idem, por grupo. |
| `media_tempo_espera_atendidos_total` | `tuple(float, float)` | `(média, dp)` do tempo de espera dos atendidos (horas). |
| `media_tempo_espera_atendidos_grupo` | `dict[str, tuple]` | Idem, por grupo. |

> As tuplas `(média, dp)` permitem construir intervalos de confiança de 95% como `média ± 1,96 × dp`.

### Exceções

| Exceção | Condição |
|---------|----------|
| `ValueError` | Chave obrigatória ausente em `sim_data`. |

### Exemplo

```python
from icusim import run_multi_simulation
import pandas as pd

tabela = run_multi_simulation(
    sim_data, numero_simulacoes=30, multi_leitos=(10, 30, 5)
)
df = pd.DataFrame(tabela)

# Extrair média e IC 95% da ocupação
df["ocupacao_media"]  = df["media_ocupacao_media"].apply(lambda t: t[0])
df["ocupacao_ic95"]   = df["media_ocupacao_media"].apply(lambda t: 1.96 * t[1])
```

---

## `ICUSim`

**Módulo:** `icusim.simulation`

Classe principal do motor de simulação. Encapsula o estado da UTI, os processos SimPy e os contadores de eventos.

> **Não instancie diretamente.** Use `run_simulation()` ou `run_multi_simulation()`.

---

### `ICUSim.__init__`

```python
ICUSim(env: simpy.Environment, leitos: int, aquecimento: int)
```

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `env` | `simpy.Environment` | Ambiente de simulação SimPy. |
| `leitos` | `int` | Capacidade de leitos. |
| `aquecimento` | `int` | Dias de warm-up. |

---

### Atributos de resultado

Disponíveis após a execução de `run_simulation()`:

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `LEITOS` | `int` | Capacidade configurada (constante). |
| `AQUECIMENTO` | `int` | Dias de warm-up configurados (constante). |
| `recurso_leitos` | `simpy.PriorityResource` | Recurso SimPy dos leitos com disciplina de fila por prioridade. |
| `pacientes_internados` | `int` | Contador corrente de pacientes internados (estado no fim da simulação). |
| `pacientes_solicitacao` | `int` | Contador corrente de pacientes aguardando leito. |
| `total_pacientes` | `dict[str, int]` | Total de solicitações por grupo após o aquecimento. |
| `pacientes_atendidos` | `dict[str, int]` | Total de internações por grupo. |
| `pacientes_perdidos` | `dict[str, int]` | Total de perdas por grupo. |
| `lista_pacientes` | `dict[str, dict]` | Registro bruto de cada paciente (ver estrutura abaixo). |
| `pacientedia` | `list[int]` | Série temporal diária do censo de internados. |
| `solicitacaopendentedia` | `list[int]` | Série temporal diária de solicitações pendentes. |
| `fila` | `list[list]` | Estado diário da fila (nome e prioridade de cada solicitação pendente). |
| `compilado_geral` | `dict` | Compilado geral — injetado por `run_simulation()`. |
| `compilado_analise` | `dict` | Métricas de desempenho — injetado por `run_simulation()`. |
| `dados_analise` | `list[dict]` | Tabela por paciente — injetada por `run_simulation()`. |

**Estrutura de `lista_pacientes[nome]`:**

```python
{
    "prioridade": int,
    "tempo_max": int,        # tempo máximo de espera (horas)
    "tempo_internacao": float, # sorteado originalmente (horas)
    "t0": float,             # instante de solicitação
    "t1": float | None,      # instante de início da internação
    "t2": float | None,      # instante de alta (-1 se perda)
    "status": str,           # "solicitacao" | "internado" | "alta" | "perda"
}
```

---

### `ICUSim.paciente()`

```python
def paciente(
    self,
    nome: str,
    prioridade: int,
    tempo_max_espera: int,
    tempo_internacao: float,
) -> Generator
```

Gerador SimPy que modela o ciclo completo de um paciente: chegada → fila → internação → alta (ou perda por tempo de espera excedido).

**Transições de status registradas em `lista_pacientes`:**

```
chegada → "solicitacao" → (leito disponível a tempo) → "internado" → "alta"
                        → (leito tardio)              → "perda"
```

---

### `ICUSim.cria_paciente()`

```python
def cria_paciente(
    self,
    prefixo: str,
    prioridade: tuple[int, int],
    novos_pacientes_dia: float,
    mean: float,
    std_dev: float,
    tempo_max_espera: tuple[int, int],
    dias_semana: list[int],
) -> Generator
```

Gerador SimPy infinito que produz novos pacientes ao longo da simulação.

**Distribuições utilizadas:**

| Variável | Distribuição | Parâmetro |
|----------|-------------|-----------|
| Intervalo entre chegadas | Poisson | λ = `24 / novos_pacientes_dia` horas |
| Tempo de internação | Gamma | shape = `mean²/std_dev²`, scale = `std_dev²/mean` (em dias, convertido para horas) + 12 h mínimo |
| Prioridade | Uniforme discreta | `[prioridade[0], prioridade[1]]` |
| Tempo máximo de espera | Uniforme discreta | `[tempo_max_espera[0], tempo_max_espera[1]]` horas |

---

### `ICUSim.adiciona_paciente()`

```python
def adiciona_paciente(
    self,
    nome: str,
    prioridade: int,
    tempo_max_espera: int,
    tempo_internacao: float,
    t0: float,
    t1: float | None = None,
    t2: float | None = None,
    status: str | None = None,
) -> None
```

Registra ou atualiza a entrada de um paciente em `lista_pacientes`. Chamado internamente em cada transição de estado.

---

### `ICUSim.checa_censo()`

```python
def checa_censo(self) -> Generator
```

Gerador SimPy disparado a cada 24 horas. Após o aquecimento, registra:
- `pacientedia` — número de internados no instante de coleta.
- `solicitacaopendentedia` — solicitações com status `"solicitacao"` ainda ativas.
- `fila` — snapshot da fila de espera (nome e prioridade).

---

## `calcula_media_desvio(dados)`

**Módulo:** `icusim.stats`

```python
def calcula_media_desvio(dados: list) -> tuple[float, float]
```

Calcula média e desvio padrão de uma lista numérica. Valores `None` são substituídos por `0`.

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `dados` | `list` | Lista de valores numéricos ou `None`. |

**Retorna:** `(média, desvio_padrão)` como `tuple[float, float]`.

```python
from icusim import calcula_media_desvio

calcula_media_desvio([10, 12, None, 8, 11])
# → (8.2, 4.26...)  # None tratado como 0
```

---

## `calcula_media_desvio_por_grupo(data)`

**Módulo:** `icusim.stats`

```python
def calcula_media_desvio_por_grupo(data: list[dict]) -> dict[str, tuple[float, float]]
```

Calcula média e desvio padrão por chave em uma lista de dicionários. Valores `None` substituídos por `0`.

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `data` | `list[dict]` | Lista de dicionários com as mesmas chaves, representando rodadas de simulação. |

**Retorna:** `{chave: (média, desvio_padrão)}`.

```python
from icusim import calcula_media_desvio_por_grupo

data = [
    {"CLI": 12, "CIR": 3},
    {"CLI": 14, "CIR": 4},
    {"CLI": 11, "CIR": 2},
]
calcula_media_desvio_por_grupo(data)
# → {"CLI": (12.33, 1.24), "CIR": (3.0, 0.81)}
```
