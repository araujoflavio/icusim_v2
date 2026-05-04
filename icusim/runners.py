"""
icusim.runners
--------------
Funções de alto nível para execução de simulações simples e múltiplas.
"""

from __future__ import annotations

import copy

import numpy as np
import simpy

from .simulation import ICUSim
from .stats import calcula_media_desvio, calcula_media_desvio_por_grupo

_CHAVES_SIM = {"dias", "aquecimento", "leitos", "paciente"}
_CHAVES_PACIENTE = {
    "prefixo", "prioridade", "novos_pacientes_dia",
    "mean", "std_dev", "tempo_max_espera", "dias_semana",
}


def _validar_sim_data(sim_data: dict) -> None:
    """
    Valida o dicionário de configuração da simulação.

    Parameters
    ----------
    sim_data : dict
        Configuração a ser validada.

    Raises
    ------
    ValueError
        Se alguma chave obrigatória estiver ausente ou com tipo inválido.
    """
    faltando = _CHAVES_SIM - set(sim_data)
    if faltando:
        raise ValueError(f"sim_data está faltando as chaves obrigatórias: {faltando}")

    if not isinstance(sim_data["paciente"], list) or len(sim_data["paciente"]) == 0:
        raise ValueError("'paciente' deve ser uma lista com ao menos um grupo.")

    for i, p in enumerate(sim_data["paciente"]):
        faltando_p = _CHAVES_PACIENTE - set(p)
        if faltando_p:
            raise ValueError(
                f"Grupo de paciente [{i}] (prefixo: '{p.get('prefixo', '?')}') "
                f"está faltando as chaves: {faltando_p}"
            )


def run_simulation(sim_data: dict) -> ICUSim:
    """
    Executa uma única rodada de simulação.

    Parameters
    ----------
    sim_data : dict
        Configuração da simulação. Chaves obrigatórias:

        - ``dias`` (*int*): duração da simulação em dias, excluindo o aquecimento.
        - ``aquecimento`` (*int*): dias de warm-up descartados da análise.
        - ``leitos`` (*int* ou *tuple*): número de leitos. Quando for uma tupla
          (ex.: uso via :func:`run_multi_simulation`), utiliza o primeiro elemento.
        - ``paciente`` (*list[dict]*): lista de grupos de pacientes. Cada grupo
          deve conter as chaves ``prefixo``, ``prioridade``, ``novos_pacientes_dia``,
          ``mean``, ``std_dev``, ``tempo_max_espera`` e ``dias_semana``.

    Returns
    -------
    ICUSim
        Objeto com os resultados disponíveis em:

        - ``compilado_geral`` (*dict*): totais e estatísticas gerais da simulação.
        - ``compilado_analise`` (*dict*): métricas de desempenho (ocupação, perda,
          tempo de espera).
        - ``dados_analise`` (*list[dict]*): registro detalhado de cada paciente.

    Raises
    ------
    ValueError
        Se ``sim_data`` não contiver as chaves obrigatórias.

    Examples
    --------
    >>> sim_data = {
    ...     "dias": 30, "aquecimento": 7, "leitos": 10,
    ...     "paciente": [{
    ...         "prefixo": "cli", "prioridade": (1, 3),
    ...         "novos_pacientes_dia": 2, "mean": 5, "std_dev": 2,
    ...         "tempo_max_espera": (12, 48), "dias_semana": [0,1,2,3,4,5,6],
    ...     }]
    ... }
    >>> sim = run_simulation(sim_data)
    >>> sim.compilado_geral["pacientes_atendidos"]
    """
    _validar_sim_data(sim_data)

    env = simpy.Environment()

    leitos = (
        sim_data["leitos"]
        if isinstance(sim_data["leitos"], int)
        else sim_data["leitos"][0]
    )
    sim = ICUSim(env, leitos=leitos, aquecimento=sim_data["aquecimento"])

    for p in sim_data["paciente"]:
        env.process(
            sim.cria_paciente(
                prefixo=p["prefixo"],
                prioridade=p["prioridade"],
                novos_pacientes_dia=p["novos_pacientes_dia"],
                mean=p["mean"],
                std_dev=p["std_dev"],
                tempo_max_espera=p["tempo_max_espera"],
                dias_semana=p["dias_semana"],
            )
        )

    env.process(sim.checa_censo())
    env.run(until=(sim_data["dias"] + sim_data["aquecimento"]) * 24)

    # --- Pós-processamento: métricas gerais ---
    ocupacao_media = sum(sim.pacientedia) / (len(sim.pacientedia) * sim.LEITOS)
    solicitacao_pendentedia_media = sum(sim.solicitacaopendentedia) / len(
        sim.solicitacaopendentedia
    )
    dias_100_atendimento = sim.solicitacaopendentedia.count(0) / len(
        sim.solicitacaopendentedia
    )
    pacientes_atendidos_total = sum(sim.pacientes_atendidos.values())
    atendimento_medio = pacientes_atendidos_total / len(sim.pacientedia)
    tempo_medio_internacao = sum(sim.pacientedia) / sum(
        sim.lista_pacientes[s]["t2"] not in [-1, None]
        for s in sim.lista_pacientes
    )

    # --- Pós-processamento: tabela por paciente ---
    tabela = []
    for nome, dados in sim.lista_pacientes.items():
        grupo = nome.split("_")[0]

        if dados["t1"] is not None:
            tempo_espera = dados["t1"] - dados["t0"]
            aceito = True
            perda = dados["tempo_max"] < tempo_espera
        else:
            tempo_espera = None
            aceito = False
            perda = None

        tempo_internacao = (
            dados["t2"] - dados["t1"]
            if dados["t2"] is not None and dados["t2"] > 0
            else None
        )
        aguardando = tempo_internacao is None and not aceito

        tabela.append({
            "grupo": grupo,
            "prioridade": dados["prioridade"],
            "aguardando": aguardando,
            "aceito": aceito,
            "perda": perda,
            "delta_espera": dados["tempo_max"] - tempo_espera if tempo_espera is not None else None,
            "taxa_espera": tempo_espera / dados["tempo_max"] if tempo_espera is not None else None,
            "tempo_espera": tempo_espera,
            "tempo_internacao": tempo_internacao,
            "tempo_internacao_base": dados["tempo_internacao"],
            "tempo_max_espera": dados["tempo_max"],
            "t0": dados["t0"],
            "t1": dados["t1"],
            "t2": dados["t2"],
            "status": dados["status"],
        })

    sim.dados_analise = tabela

    # --- Pós-processamento: contagens por grupo ---
    grupos = list(set(d["grupo"] for d in tabela))

    def _contagem(status_filtro: list[str]) -> dict[str, int]:
        d = [p["grupo"] for p in tabela if p["status"] in status_filtro]
        return {i: d.count(i) for i in set(d)}

    total_perdidos = _contagem(["perda"])
    total = _contagem(["solicitacao", "internado", "alta", "perda"])
    total_aguardando = _contagem(["solicitacao"])
    total_aceito = _contagem(["internado", "alta"])

    taxa_perda_grupo = {
        i: total_perdidos[i] / (total_aceito.get(i, 0) + total_perdidos[i])
        for i in total_perdidos
    }
    taxa_perda_total = sum(total_perdidos.values()) / (
        sum(total_aceito.values()) + sum(total_perdidos.values())
    )

    def _calculo_media(dados: list) -> float | None:
        """
        Calcula a média de uma lista de valores.

        Retorna ``None`` quando a lista está vazia ou contém apenas um elemento,
        pois não há dados suficientes para uma estimativa representativa. Este é
        o comportamento esperado — o chamador deve tratar ``None`` como ausência
        de dado, não como zero.

        Parameters
        ----------
        dados : list
            Lista de valores numéricos.

        Returns
        -------
        float or None
            Média dos valores, ou ``None`` se a lista tiver 0 ou 1 elemento.
        """
        if len(dados) > 1:
            return float(np.mean(dados))
        return None

    sim.compilado_geral = {
        "grupos": grupos,
        "total_pacientes": total,
        "pacientes_atendidos": total_aceito,
        "pacientes_perdidos": total_perdidos,
        "pacientes_aguardando": total_aguardando,
        "dias": len(sim.pacientedia),
        "tempo_medio_internacao": tempo_medio_internacao,
    }

    sim.compilado_analise = {
        "solicitacao_pendentedia_media": solicitacao_pendentedia_media,
        "ocupacao_media": ocupacao_media,
        "dias_100_atendimento": dias_100_atendimento,
        "atendimento_medio": atendimento_medio,
        "taxa_perda_grupo": taxa_perda_grupo,
        "taxa_perda_total": taxa_perda_total,
        "media_delta_espera_perdidos_total": _calculo_media(
            [-d["delta_espera"] for d in tabela if d["perda"]]
        ),
        "media_delta_espera_perdidos_grupo": {
            g: _calculo_media(
                [-d["delta_espera"] for d in tabela if d["grupo"] == g and d["perda"]]
            )
            for g in grupos
        },
        "media_tempo_espera_atendidos_total": np.mean(
            [d["tempo_espera"] for d in tabela if d["aceito"] and not d["perda"]]
        ),
        "media_tempo_espera_atendidos_grupo": {
            g: np.mean(
                [d["tempo_espera"] for d in tabela if d["grupo"] == g and d["aceito"] and not d["perda"]]
            )
            for g in grupos
        },
    }

    return sim


def run_multi_simulation(
    sim_data: dict,
    numero_simulacoes: int = 10,
    multi_leitos: tuple[int, int, int] | bool = False,
) -> list[dict]:
    """
    Executa múltiplas rodadas de simulação e agrega os resultados estatisticamente.

    Pode operar em dois modos:

    - **Ponto fixo**: usa ``sim_data["leitos"]`` e repete ``numero_simulacoes`` vezes,
      retornando a tabela bruta de resultados individuais.
    - **Varredura de leitos**: quando ``multi_leitos`` é fornecido, itera sobre uma
      faixa de valores de leitos e executa ``numero_simulacoes`` para cada ponto,
      retornando médias e desvios padrão agregados.

    Parameters
    ----------
    sim_data : dict
        Configuração da simulação (mesma estrutura de :func:`run_simulation`).
    numero_simulacoes : int, optional
        Número de repetições por configuração de leitos. Padrão: ``10``.
    multi_leitos : tuple[int, int, int] or False, optional
        Tupla ``(min, max, passo)`` definindo a faixa de leitos a varrer.
        O valor ``max`` é inclusivo. Quando ``False``, usa o valor fixo de
        ``sim_data["leitos"]``.

    Returns
    -------
    list[dict]
        - Com ``multi_leitos``: lista de dicionários com médias e desvios padrão
          agregados por configuração de leitos.
        - Sem ``multi_leitos``: tabela bruta com os resultados de cada simulação
          individual.

    Raises
    ------
    ValueError
        Se ``sim_data`` não contiver as chaves obrigatórias.

    Examples
    --------
    >>> resultado = run_multi_simulation(sim_data, numero_simulacoes=20,
    ...                                  multi_leitos=(10, 30, 5))
    >>> import pandas as pd
    >>> pd.DataFrame(resultado)["media_ocupacao_media"]
    """
    _validar_sim_data(sim_data)

    if multi_leitos:
        leitos_range = range(multi_leitos[0], multi_leitos[1] + 1, multi_leitos[2])
    else:
        leitos_range = range(sim_data["leitos"], sim_data["leitos"] + 1)

    resultado = []

    for leitos in leitos_range:
        tabela = []
        for i in range(numero_simulacoes):
            # deepcopy garante que a lista de grupos de pacientes não seja
            # compartilhada entre iterações (evita mutação silenciosa).
            sim_data_copia = copy.deepcopy(sim_data)
            sim_data_copia["leitos"] = leitos
            sim = run_simulation(sim_data_copia)
            tabela.append({"simulacao": i, **sim.compilado_geral, **sim.compilado_analise})

        dias = [t["dias"] for t in tabela]
        media_dias = float(np.mean(dias))

        data_total = [t["total_pacientes"] for t in tabela]
        total_pacientes_criados = {k: sum(d[k] for d in data_total) for k in data_total[0]}
        media_pacientes_criados = calcula_media_desvio_por_grupo(data_total)
        media_pacientes_criados_dia = calcula_media_desvio_por_grupo(
            [{k: d[k] / dias[i] for k in d} for i, d in enumerate(data_total)]
        )

        media_pacientes_atendidos = calcula_media_desvio_por_grupo(
            [{k: d[k] / dias[i] for k in d} for i, d in enumerate(
                [t["pacientes_atendidos"] for t in tabela]
            )]
        )
        media_pacientes_perdidos = calcula_media_desvio_por_grupo(
            [{k: d[k] / dias[i] for k in d} for i, d in enumerate(
                [t["pacientes_perdidos"] for t in tabela]
            )]
        )
        media_pacientes_aguardando = calcula_media_desvio_por_grupo(
            [t["pacientes_aguardando"] for t in tabela]
        )

        media_tempo_medio_internacao = calcula_media_desvio(
            [t["tempo_medio_internacao"] for t in tabela]
        )
        media_solicitacao_pendentedia_media = calcula_media_desvio(
            [t["solicitacao_pendentedia_media"] for t in tabela]
        )
        media_ocupacao_media = calcula_media_desvio(
            [t["ocupacao_media"] for t in tabela]
        )
        media_dias_100_atendimento = calcula_media_desvio(
            [t["dias_100_atendimento"] for t in tabela]
        )
        media_atendimento_medio = calcula_media_desvio(
            [t["atendimento_medio"] for t in tabela]
        )
        taxa_perda_grupo = calcula_media_desvio_por_grupo(
            [t["taxa_perda_grupo"] for t in tabela]
        )
        media_taxa_perda_total = calcula_media_desvio(
            [t["taxa_perda_total"] for t in tabela]
        )
        media_delta_espera_perdidos_total = calcula_media_desvio(
            [t["media_delta_espera_perdidos_total"] for t in tabela]
        )
        media_delta_espera_perdidos_grupo = calcula_media_desvio_por_grupo(
            [t["media_delta_espera_perdidos_grupo"] for t in tabela]
        )
        media_tempo_espera_atendidos_total = calcula_media_desvio(
            [t["media_tempo_espera_atendidos_total"] for t in tabela]
        )
        media_tempo_espera_atendidos_grupo = calcula_media_desvio_por_grupo(
            [t["media_tempo_espera_atendidos_grupo"] for t in tabela]
        )

        resultado.append({
            "media_dias": media_dias,
            "simulacoes": len(tabela),
            "leitos": leitos,
            "total_pacientes_criados": total_pacientes_criados,
            "media_pacientes_criados": media_pacientes_criados,
            "media_pacientes_criados_dia": media_pacientes_criados_dia,
            "media_pacientes_atendidos": media_pacientes_atendidos,
            "media_pacientes_perdidos": media_pacientes_perdidos,
            "media_pacientes_aguardando": media_pacientes_aguardando,
            "media_tempo_medio_internacao": media_tempo_medio_internacao,
            "media_solicitacao_pendentedia_media": media_solicitacao_pendentedia_media,
            "media_ocupacao_media": media_ocupacao_media,
            "media_dias_100_atendimento": media_dias_100_atendimento,
            "media_atendimento_medio": media_atendimento_medio,
            "taxa_perda_grupo": taxa_perda_grupo,
            "media_taxa_perda_total": media_taxa_perda_total,
            "media_delta_espera_perdidos_total": media_delta_espera_perdidos_total,
            "media_delta_espera_perdidos_grupo": media_delta_espera_perdidos_grupo,
            "media_tempo_espera_atendidos_total": media_tempo_espera_atendidos_total,
            "media_tempo_espera_atendidos_grupo": media_tempo_espera_atendidos_grupo,
        })

    if multi_leitos:
        return resultado
    else:
        return tabela
