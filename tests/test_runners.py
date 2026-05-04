"""
Testes para icusim.runners (run_simulation, run_multi_simulation).
"""
import pytest

from icusim import run_simulation, run_multi_simulation


class TestRunSimulation:

    def test_retorna_compilado_geral(self, sim_data_simples):
        sim = run_simulation(sim_data_simples)
        assert hasattr(sim, "compilado_geral")
        assert "total_pacientes" in sim.compilado_geral
        assert "pacientes_atendidos" in sim.compilado_geral
        assert "pacientes_perdidos" in sim.compilado_geral

    def test_retorna_compilado_analise(self, sim_data_simples):
        sim = run_simulation(sim_data_simples)
        assert hasattr(sim, "compilado_analise")
        assert "ocupacao_media" in sim.compilado_analise
        assert "taxa_perda_total" in sim.compilado_analise

    def test_retorna_dados_analise(self, sim_data_simples):
        sim = run_simulation(sim_data_simples)
        assert hasattr(sim, "dados_analise")
        assert isinstance(sim.dados_analise, list)
        assert len(sim.dados_analise) > 0

    def test_campos_por_paciente(self, sim_data_simples):
        sim = run_simulation(sim_data_simples)
        paciente = sim.dados_analise[0]
        campos_esperados = {
            "grupo", "prioridade", "aceito", "perda",
            "tempo_espera", "tempo_internacao", "t0", "status",
        }
        assert campos_esperados.issubset(set(paciente.keys()))

    def test_ocupacao_entre_0_e_1(self, sim_data_simples):
        sim = run_simulation(sim_data_simples)
        ocupacao = sim.compilado_analise["ocupacao_media"]
        assert 0.0 <= ocupacao <= 1.0

    def test_dias_simulados_corretos(self, sim_data_simples):
        sim = run_simulation(sim_data_simples)
        assert sim.compilado_geral["dias"] == sim_data_simples["dias"]

    def test_grupos_corretos(self, sim_data_multiplos_grupos):
        sim = run_simulation(sim_data_multiplos_grupos)
        grupos = set(sim.compilado_geral["grupos"])
        assert grupos == {"CLI", "CIR"}

    def test_chave_faltando_levanta_value_error(self, sim_data_simples):
        del sim_data_simples["leitos"]
        with pytest.raises(ValueError, match="leitos"):
            run_simulation(sim_data_simples)

    def test_grupo_sem_prefixo_levanta_value_error(self, sim_data_simples):
        del sim_data_simples["paciente"][0]["prefixo"]
        with pytest.raises(ValueError):
            run_simulation(sim_data_simples)

    def test_lista_paciente_vazia_levanta_value_error(self, sim_data_simples):
        sim_data_simples["paciente"] = []
        with pytest.raises(ValueError):
            run_simulation(sim_data_simples)


class TestRunMultiSimulation:

    def test_retorna_lista(self, sim_data_simples):
        resultado = run_multi_simulation(sim_data_simples, numero_simulacoes=3)
        assert isinstance(resultado, list)
        assert len(resultado) == 3

    def test_cada_item_tem_simulacao(self, sim_data_simples):
        resultado = run_multi_simulation(sim_data_simples, numero_simulacoes=3)
        for item in resultado:
            assert "simulacao" in item

    def test_multi_leitos_retorna_um_item_por_leito(self, sim_data_simples):
        sim_data_simples["leitos"] = 10
        resultado = run_multi_simulation(
            sim_data_simples,
            numero_simulacoes=2,
            multi_leitos=(10, 12, 1),
        )
        # leitos 10, 11, 12 → 3 pontos
        assert len(resultado) == 3

    def test_multi_leitos_tem_media_ocupacao(self, sim_data_simples):
        sim_data_simples["leitos"] = 10
        resultado = run_multi_simulation(
            sim_data_simples,
            numero_simulacoes=2,
            multi_leitos=(10, 11, 1),
        )
        for item in resultado:
            assert "media_ocupacao_media" in item
