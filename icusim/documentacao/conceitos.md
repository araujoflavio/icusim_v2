# Conceitos — icusim

Fundamentos teóricos e decisões de modelagem que embasam a biblioteca `icusim`.

---

## Sumário

1. [Discrete Event Simulation (DES)](#1-discrete-event-simulation-des)
2. [Estrutura do modelo de UTI](#2-estrutura-do-modelo-de-uti)
3. [Processo de chegada de pacientes](#3-processo-de-chegada-de-pacientes)
4. [Distribuição do tempo de internação](#4-distribuição-do-tempo-de-internação)
5. [Fila por prioridade](#5-fila-por-prioridade)
6. [Critério de perda](#6-critério-de-perda)
7. [Período de aquecimento (warm-up)](#7-período-de-aquecimento-warm-up)
8. [Múltiplas rodadas e análise estatística](#8-múltiplas-rodadas-e-análise-estatística)
9. [Limitações do modelo](#9-limitações-do-modelo)

---

## 1. Discrete Event Simulation (DES)

A simulação por eventos discretos (DES) modela um sistema como uma sequência de **eventos** que ocorrem em instantes específicos no tempo. Entre dois eventos consecutivos, o estado do sistema não muda — o tempo "avança" diretamente de um evento para o próximo.

No `icusim`, os eventos principais são:
- **Chegada de um paciente** (solicitação de leito)
- **Início de internação** (alocação de leito)
- **Alta hospitalar** (liberação de leito)
- **Perda** (paciente desiste/é descartado após exceder o tempo de espera)
- **Censo diário** (registro do estado do sistema a cada 24 horas)

O motor de DES utilizado é o **SimPy**, uma biblioteca Python de eventos discretos baseada em geradores nativos (`yield`).

### Fluxo de um paciente

```
Chegada (t0)
    │
    ▼
Fila de espera (PriorityResource)
    │
    ├─ leito disponível antes de t0 + tempo_max_espera ──► Internação (t1) ──► Alta (t2)
    │
    └─ leito disponível após  t0 + tempo_max_espera   ──► Perda (t2 = -1)
```

---

## 2. Estrutura do modelo de UTI

O modelo representa a UTI como um **sistema de filas M/G/c/∞** com disciplina de prioridade:

| Elemento | Descrição |
|----------|-----------|
| **Servidores (c)** | Leitos da UTI, representados como `simpy.PriorityResource`. |
| **Chegadas (M)** | Processo de Poisson (distribuição de chegadas exponencial). |
| **Serviço (G)** | Distribuição Gamma para o tempo de internação (distribuição geral). |
| **Fila (∞)** | Sem limite formal de fila, mas com **abandono** baseado em tempo máximo de espera. |
| **Disciplina** | Prioridade com preempção parcial: pacientes de maior prioridade entram na frente da fila, mas **não deslocam** pacientes já internados. |

---

## 3. Processo de chegada de pacientes

O intervalo entre chegadas sucessivas de pacientes de um mesmo grupo segue uma **distribuição de Poisson**:

$$\Delta t \sim \text{Poisson}\left(\frac{24}{\lambda}\right) \text{ horas}$$

onde $\lambda$ = `novos_pacientes_dia` é a taxa média de chegadas por dia.

Isso equivale a assumir que as chegadas seguem um **processo de Poisson homogêneo** (taxa constante), uma hipótese comum em modelagem de fluxo hospitalar para horizontes de médio prazo.

### Restrição por dia da semana

O parâmetro `dias_semana` permite modelar padrões semanais. Quando o dia sorteado para a chegada não está na lista, o paciente é simplesmente descartado (sem recolocar na fila). A taxa efetiva de chegadas é automaticamente reduzida proporcionalmente à quantidade de dias habilitados.

---

## 4. Distribuição do tempo de internação

O tempo de internação é sorteado de uma **distribuição Gamma**, escolhida por:

- Ser definida apenas para valores positivos (tempo não pode ser negativo).
- Possuir cauda longa, representando pacientes com internações muito prolongadas.
- Ser parametrizável pela média e desvio padrão observados em dados históricos.

A parametrização utilizada converte `mean` (dias) e `std_dev` (dias) para os parâmetros nativos da Gamma:

$$\alpha = \frac{\mu^2}{\sigma^2} \quad \text{(shape)}, \qquad \beta = \frac{\sigma^2}{\mu} \quad \text{(scale)}$$

O valor sorteado é convertido de dias para horas e acrescido de um **mínimo de 12 horas**:

$$T_{\text{internação}} = \text{Gamma}(\alpha, \beta) \times 24 + 12 \text{ h}$$

### Calibração a partir de dados históricos

```python
from scipy.stats import gamma
import numpy as np

dados_dias = df["tempo_internacao"] / 24  # converter horas → dias
shape, loc, scale = gamma.fit(dados_dias, floc=0)

mean_cal   = shape * scale
std_cal    = np.sqrt(shape) * scale
```

---

## 5. Fila por prioridade

O SimPy implementa uma fila por prioridade estrita (`PriorityResource`). Quando um leito é liberado, ele é alocado ao paciente **com menor valor numérico de prioridade** que estiver aguardando.

No `icusim`, a prioridade de cada paciente é sorteada uniformemente no intervalo `(prioridade_min, prioridade_max)` definido por grupo. Isso permite modelar heterogeneidade dentro de um mesmo grupo clínico.

> **Convenção SimPy:** prioridade `1` é **mais urgente** que prioridade `5`.

### Interação entre grupos

Quando múltiplos grupos estão configurados, seus pacientes disputam os mesmos leitos. Grupos com intervalo de prioridade baixo (ex.: `(1, 2)`) tendem a obter leitos antes de grupos com prioridade alta (ex.: `(3, 5)`), mesmo que estes tenham chegado primeiro.

---

## 6. Critério de perda

Um paciente é registrado como **perda** quando, no instante em que um leito finalmente é disponibilizado para ele (`t1`), o tempo decorrido desde sua chegada (`t1 - t0`) excede o tempo máximo de espera sorteado:

$$\text{perda} \iff t_1 - t_0 \geq \text{tempo\_max\_espera}$$

O paciente **não é removido da fila** antes disso — ele ocupa posição na fila e só é descartado no momento em que seria atendido. Isso é uma simplificação em relação a cenários onde o paciente abandona a fila ativamente, mas é adequado para modelar encaminhamentos a outros hospitais ou óbito na espera.

### Métricas derivadas

| Métrica | Fórmula |
|---------|---------|
| Taxa de perda (grupo) | $\frac{N_{\text{perdidos}}}{N_{\text{atendidos}} + N_{\text{perdidos}}}$ |
| Delta de espera (perdidos) | $\text{tempo\_max} - (t_1 - t_0)$ — valor negativo indica o quanto excedeu |

---

## 7. Período de aquecimento (warm-up)

Em simulações de sistemas com fila, o estado inicial (fila vazia, todos os leitos livres) é **artificialmente favorável** e não representa o regime estacionário real. Pacientes chegam e são atendidos mais facilmente nos primeiros dias.

O parâmetro `aquecimento` define quantos dias iniciais de simulação são **descartados da coleta**. Durante esse período:
- O processo de chegada e internação ocorre normalmente.
- Nenhum paciente é registrado em `lista_pacientes`.
- Nenhum contador de atendidos/perdidos é incrementado.
- O censo diário não é registrado.

O sistema chega ao estado estacionário ao longo do aquecimento, e apenas os dados posteriores a ele são analisados.

### Quanto tempo de aquecimento usar?

Uma regra empírica para sistemas de fila hospitalar:

$$\text{aquecimento} \geq 2 \times \frac{\mu_{\text{internação}}}{\lambda \times (1 - \rho)}$$

onde $\mu$ é o tempo médio de internação, $\lambda$ a taxa de chegadas e $\rho$ a taxa de utilização esperada. Na prática, **30 dias** é suficiente para a maioria dos cenários de UTI.

---

## 8. Múltiplas rodadas e análise estatística

Por ser estocástica, cada rodada produz um resultado diferente. Para inferência confiável, `run_multi_simulation` executa $n$ rodadas independentes e calcula:

$$\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i \qquad \hat{\sigma} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(x_i - \bar{x})^2}$$

O **intervalo de confiança de 95%** é calculado externamente como:

$$\text{IC}_{95\%} = \bar{x} \pm 1{,}96 \cdot \hat{\sigma}$$

> Para amostras pequenas ($n < 30$), é mais rigoroso usar a distribuição $t$ de Student com $n-1$ graus de liberdade. Para $n \geq 30$ a aproximação normal é adequada.

### Independência entre rodadas

Cada rodada usa um estado diferente do gerador de números aleatórios do NumPy. Para garantir reprodutibilidade em um experimento, fixe a semente antes de chamar a função:

```python
import numpy as np
np.random.seed(42)

tabela = run_multi_simulation(sim_data, numero_simulacoes=50)
```

---

## 9. Limitações do modelo

| Aspecto | Limitação atual |
|---------|----------------|
| **Taxa de chegada** | Processo de Poisson homogêneo — não captura sazonalidade intradiária (pico matutino, noturno) nem sazonal (inverno vs. verão). |
| **Abandono de fila** | O paciente só é descartado quando um leito ficaria disponível; não há abandono antecipado. |
| **Transferência** | Não há modelagem de transferência entre unidades (ex.: da UTI para enfermaria). |
| **Alta condicional** | O tempo de internação é sorteado na chegada e é fixo — não há variação condicional ao estado clínico. |
| **Recursos humanos** | O modelo considera apenas leitos como recurso limitante; médicos, enfermeiros e equipamentos não são modelados. |
| **Não-preempção** | Pacientes de alta prioridade que chegam quando todos os leitos estão ocupados não deslocam pacientes internados de baixa prioridade. |
