"""
teste_simulacao.py
------------------
Lê um arquivo JSON de configuração, executa a simulação e salva os resultados
em arquivos JSON na pasta 'resultados/'.
"""

import json
import os
from pathlib import Path

from icusim import run_simulation


def _converter_para_json(obj):
    """Converte tipos não serializáveis (numpy, etc.) para tipos nativos Python."""
    import numpy as np
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Tipo não serializável: {type(obj)}")


def rodar_e_salvar(caminho_json: str, pasta_saida: str = "resultados") -> None:
    """
    Lê a configuração do JSON, executa a simulação e salva as saídas.

    Parameters
    ----------
    caminho_json : str
        Caminho para o arquivo JSON de configuração.
    pasta_saida : str
        Pasta onde os arquivos de saída serão salvos.
    """
    # --- Leitura da configuração ---
    with open(caminho_json, encoding="utf-8") as f:
        sim_data = json.load(f)

    print(f"Configuração carregada: {caminho_json}")
    print(f"  Leitos: {sim_data['leitos']} | Dias: {sim_data['dias']} | Aquecimento: {sim_data['aquecimento']}")

    # --- Execução da simulação ---
    sim = run_simulation(sim_data)
    print("Simulação concluída.")

    # --- Preparação da pasta de saída ---
    nome_base = Path(caminho_json).stem
    pasta = Path(pasta_saida) / nome_base
    pasta.mkdir(parents=True, exist_ok=True)

    dump_kwargs = {"ensure_ascii": False, "indent": 2, "default": _converter_para_json}

    # --- Saída 1: resumo geral ---
    with open(pasta / "compilado_geral.json", "w", encoding="utf-8") as f:
        json.dump(sim.compilado_geral, f, **dump_kwargs)

    # --- Saída 2: métricas de análise ---
    with open(pasta / "compilado_analise.json", "w", encoding="utf-8") as f:
        json.dump(sim.compilado_analise, f, **dump_kwargs)

    # --- Saída 3: registro detalhado por paciente ---
    with open(pasta / "dados_analise.json", "w", encoding="utf-8") as f:
        json.dump(sim.dados_analise, f, **dump_kwargs)

    print(f"Resultados salvos em: {pasta.resolve()}")
    print(f"  - compilado_geral.json")
    print(f"  - compilado_analise.json")
    print(f"  - dados_analise.json ({len(sim.dados_analise)} pacientes)")


if __name__ == "__main__":
    caminho = os.path.join("icusim", "exemplo_de_uso", "exemplo_simples.json")
    rodar_e_salvar(caminho)
