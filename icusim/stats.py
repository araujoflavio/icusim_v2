"""
icusim.stats
------------
Funções auxiliares para agregação estatística dos resultados de simulação.
"""

from __future__ import annotations

import numpy as np


def calcula_media_desvio(dados: list) -> tuple[float, float]:
    """
    Calcula a média e o desvio padrão de uma lista numérica.

    Valores ``None`` são substituídos por zero antes do cálculo, pois
    representam grupos ausentes em determinadas rodadas de simulação.

    Parameters
    ----------
    dados : list
        Lista de valores numéricos ou ``None``.

    Returns
    -------
    tuple[float, float]
        Par ``(média, desvio_padrão)``.
    """
    dados = [0 if d is None else d for d in dados]
    return (float(np.mean(dados)), float(np.std(dados)))


def calcula_media_desvio_por_grupo(data: list[dict]) -> dict[str, tuple[float, float]]:
    """
    Calcula média e desvio padrão por chave em uma lista de dicionários.

    Útil para agregar métricas por grupo de pacientes (ex.: ``"cli"``, ``"cirU"``)
    ao longo de múltiplas rodadas de simulação.

    Valores ``None`` são substituídos por zero antes do cálculo.

    Parameters
    ----------
    data : list[dict]
        Lista de dicionários com as mesmas chaves, onde cada dicionário
        representa o resultado de uma rodada de simulação.

    Returns
    -------
    dict[str, tuple[float, float]]
        Dicionário com as mesmas chaves de entrada; cada valor é uma
        tupla ``(média, desvio_padrão)`` calculada entre as rodadas.
    """
    resposta: dict[str, tuple[float, float]] = {}
    for key in data[0]:
        valores = [d[key] for d in data if key in d]
        dados = [0 if d is None else d for d in valores]
        resposta[key] = (float(np.mean(dados)), float(np.std(dados)))
    return resposta
