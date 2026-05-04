"""
Testes para icusim.stats.
"""
import pytest

from icusim.stats import calcula_media_desvio, calcula_media_desvio_por_grupo


class TestCalculaMediaDesvio:

    def test_lista_simples(self):
        media, desvio = calcula_media_desvio([1.0, 2.0, 3.0])
        assert media == pytest.approx(2.0)

    def test_none_substituido_por_zero(self):
        media, desvio = calcula_media_desvio([None, None, 3.0])
        assert media == pytest.approx(1.0)

    def test_retorna_tupla_de_floats(self):
        resultado = calcula_media_desvio([1, 2, 3])
        assert isinstance(resultado, tuple)
        assert all(isinstance(v, float) for v in resultado)


class TestCalculaMediaDesvioPorGrupo:

    def test_estrutura_de_saida(self):
        dados = [{"A": 1.0, "B": 2.0}, {"A": 3.0, "B": 4.0}]
        resultado = calcula_media_desvio_por_grupo(dados)
        assert set(resultado.keys()) == {"A", "B"}

    def test_valores_corretos(self):
        dados = [{"X": 0.0}, {"X": 2.0}]
        media, _ = calcula_media_desvio_por_grupo(dados)["X"]
        assert media == pytest.approx(1.0)

    def test_none_substituido_por_zero(self):
        dados = [{"X": None}, {"X": 4.0}]
        media, _ = calcula_media_desvio_por_grupo(dados)["X"]
        assert media == pytest.approx(2.0)
