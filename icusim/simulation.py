"""
icusim.simulation
-----------------
Contém a classe principal :class:`ICUSim`, que modela uma UTI usando
Discrete Event Simulation (DES) via SimPy.
"""

from __future__ import annotations

import random
from typing import Generator

import numpy as np
import simpy


class ICUSim:
    """
    Simula uma Unidade de Terapia Intensiva (UTI) usando Discrete Event Simulation.

    Não instancie esta classe diretamente. Use as funções :func:`~icusim.run_simulation`
    ou :func:`~icusim.run_multi_simulation`, que configuram o ambiente SimPy e
    compilam os resultados após a execução.

    Parameters
    ----------
    env : simpy.Environment
        Ambiente de simulação SimPy.
    leitos : int
        Número de leitos disponíveis na UTI.
    aquecimento : int
        Número de dias de aquecimento (warm-up) cujos dados são descartados
        da análise final.

    Attributes
    ----------
    LEITOS : int
        Número total de leitos (constante de configuração).
    AQUECIMENTO : int
        Número de dias de aquecimento (constante de configuração).
    recurso_leitos : simpy.PriorityResource
        Recurso SimPy que representa os leitos da UTI.
    pacientes_solicitacao : int
        Contador de pacientes aguardando leito no instante atual.
    pacientes_internados : int
        Contador de pacientes internados no instante atual.
    total_pacientes : dict
        Total de solicitações por grupo (apenas após aquecimento).
    pacientes_atendidos : dict
        Total de pacientes internados com sucesso por grupo.
    pacientes_perdidos : dict
        Total de pacientes perdidos (excederam tempo máximo de espera) por grupo.
    lista_pacientes : dict
        Registro detalhado de cada paciente criado após o aquecimento.
    pacientedia : list
        Série temporal diária do número de pacientes internados.
    solicitacaopendentedia : list
        Série temporal diária do número de solicitações pendentes.
    fila : list
        Registro diário do estado da fila de espera.
    """

    def __init__(self, env: simpy.Environment, leitos: int, aquecimento: int) -> None:
        self.LEITOS = leitos
        self.AQUECIMENTO = aquecimento
        self._inicio_analise: float = aquecimento * 24

        self.env = env

        self.pacientes_solicitacao: int = 0
        self.pacientes_internados: int = 0

        self.fila: list = []

        self.total_pacientes: dict = {}
        self.pacientes_atendidos: dict = {}
        self.pacientes_perdidos: dict = {}
        self.lista_pacientes: dict = {}
        self.pacientedia: list = []
        self.solicitacaopendentedia: list = []

        # Nomeado 'recurso_leitos' para evitar colisão com o atributo LEITOS (int).
        self.recurso_leitos = simpy.PriorityResource(self.env, capacity=self.LEITOS)

    @property
    def _em_coleta(self) -> bool:
        """Verdadeiro quando o instante atual está fora do período de aquecimento."""
        return self.env.now >= self._inicio_analise

    def paciente(
        self,
        nome: str,
        prioridade: int,
        tempo_max_espera: int,
        tempo_internacao: float,
    ) -> Generator:
        """
        Modela o ciclo de vida completo de um paciente na simulação.

        O paciente é criado, entra na fila, aguarda um leito com base em sua
        prioridade e, se atendido dentro do tempo máximo de espera, permanece
        internado pelo tempo sorteado. Caso contrário, é registrado como perda.
        Somente pacientes que chegam após o período de aquecimento são contabilizados.

        Parameters
        ----------
        nome : str
            Identificador único do paciente no formato ``"{prefixo}_{sequencial:06}"``.
        prioridade : int
            Prioridade na fila SimPy (menor valor = maior prioridade).
        tempo_max_espera : int
            Tempo máximo tolerado na fila de espera, em horas.
        tempo_internacao : float
            Duração da internação sorteada, em horas.
        """
        t0 = self.env.now
        # Verifica se o paciente chegou após o aquecimento; usa t0 (tempo de
        # chegada) em todas as verificações subsequentes para garantir que apenas
        # pacientes que CHEGARAM no período de análise sejam contabilizados.
        em_coleta = t0 >= self._inicio_analise

        if em_coleta:
            self.adiciona_paciente(
                nome, prioridade, tempo_max_espera, tempo_internacao,
                t0=t0, status="solicitacao",
            )
            self.total_pacientes[nome.split("_")[0]] += 1

        self.pacientes_solicitacao += 1

        with self.recurso_leitos.request(priority=prioridade) as req:
            req.name = nome
            req.priority = prioridade
            yield req

            t1 = self.env.now

            if t1 - t0 < tempo_max_espera:
                self.pacientes_solicitacao -= 1

                if em_coleta:
                    self.adiciona_paciente(
                        nome, prioridade, tempo_max_espera, tempo_internacao,
                        t0=t0, t1=t1, status="internado",
                    )

                self.pacientes_internados += 1
                yield self.env.timeout(tempo_internacao)
                t2 = self.env.now
                self.pacientes_internados -= 1

                if em_coleta:
                    self.pacientes_atendidos[nome.split("_")[0]] += 1
            else:
                # Paciente excedeu o tempo máximo de espera: registra como perda.
                self.pacientes_solicitacao -= 1

                if em_coleta:
                    self.pacientes_perdidos[nome.split("_")[0]] += 1

                t2 = -1

            if em_coleta:
                self.adiciona_paciente(
                    nome, prioridade, tempo_max_espera, tempo_internacao,
                    t0=t0, t1=t1, t2=t2,
                    status="perda" if t2 == -1 else "alta",
                )

    def cria_paciente(
        self,
        prefixo: str,
        prioridade: tuple[int, int],
        novos_pacientes_dia: float,
        mean: float,
        std_dev: float,
        tempo_max_espera: tuple[int, int],
        dias_semana: list[int],
    ) -> Generator:
        """
        Gerador SimPy que produz novos pacientes continuamente durante a simulação.

        O intervalo entre chegadas segue uma distribuição de Poisson com taxa
        média de ``novos_pacientes_dia`` por dia. O tempo de internação é sorteado
        de uma distribuição Gamma parametrizada por ``mean`` e ``std_dev`` (em dias)
        e convertida para horas, com acréscimo de 12 horas de internação mínima.

        Parameters
        ----------
        prefixo : str
            Identificador do grupo de pacientes (ex.: ``"cli"``, ``"cirU"``).
        prioridade : tuple[int, int]
            Intervalo ``(min, max)`` para sorteio uniforme da prioridade.
        novos_pacientes_dia : float
            Taxa média de novos pacientes por dia.
        mean : float
            Média do tempo de internação em dias (parâmetro da distribuição Gamma).
        std_dev : float
            Desvio padrão do tempo de internação em dias (parâmetro da distribuição Gamma).
        tempo_max_espera : tuple[int, int]
            Intervalo ``(min, max)`` em horas para sorteio do tempo máximo de espera.
        dias_semana : list[int]
            Dias da semana em que este grupo pode chegar (0 = segunda, 6 = domingo).
        """
        paciente_nome = 0
        self.pacientes_perdidos[prefixo] = 0
        self.pacientes_atendidos[prefixo] = 0
        self.total_pacientes[prefixo] = 0

        while True:
            yield self.env.timeout(np.random.poisson(24 / novos_pacientes_dia))

            if (self.env.now // 24) % 7 not in dias_semana:
                continue

            # Tempo de internação sorteado de distribuição Gamma, mínimo 12 horas.
            tempo_internacao = (
                np.random.gamma(mean**2 / std_dev**2, std_dev**2 / mean) * 24 + 12
            )

            prioridade_sorteada = random.randint(*prioridade)
            tempo_max_espera_sorteado = random.randint(*tempo_max_espera)

            self.env.process(
                self.paciente(
                    f"{prefixo}_{paciente_nome:06}",
                    prioridade_sorteada,
                    tempo_max_espera_sorteado,
                    tempo_internacao,
                )
            )
            paciente_nome += 1

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
    ) -> None:
        """
        Registra ou atualiza o estado de um paciente no dicionário de rastreamento.

        Chamado múltiplas vezes ao longo do ciclo do paciente (``"solicitacao"``,
        ``"internado"``, ``"alta"`` ou ``"perda"``), sobrescrevendo a entrada
        anterior a cada transição de estado.

        Parameters
        ----------
        nome : str
            Identificador do paciente.
        prioridade : int
            Prioridade do paciente.
        tempo_max_espera : int
            Tempo máximo de espera tolerado, em horas.
        tempo_internacao : float
            Duração da internação sorteada, em horas.
        t0 : float
            Instante de solicitação (chegada), em horas de simulação.
        t1 : float, optional
            Instante de início da internação, em horas de simulação.
        t2 : float, optional
            Instante de alta, em horas de simulação, ou ``-1`` em caso de perda.
        status : str, optional
            Estado atual: ``"solicitacao"``, ``"internado"``, ``"alta"`` ou ``"perda"``.
        """
        self.lista_pacientes[nome] = {
            "prioridade": prioridade,
            "tempo_max": tempo_max_espera,
            "tempo_internacao": tempo_internacao,
            "t0": t0,
            "t1": t1,
            "t2": t2,
            "status": status,
        }

    def checa_censo(self) -> Generator:
        """
        Gerador SimPy que registra o censo diário da UTI.

        Disparado a cada 24 horas de simulação. Após o período de aquecimento,
        registra o número de pacientes internados, o estado da fila e o número
        de solicitações pendentes (pacientes com status ``"solicitacao"`` ainda
        ativos no dicionário de rastreamento).

        Notes
        -----
        Pacientes que excederam o tempo máximo de espera já foram removidos dos
        contadores de solicitação, portanto não são contabilizados como pendentes,
        mesmo que ainda apareçam na lista para fins de análise histórica.
        """
        while True:
            yield self.env.timeout(24)

            if self._em_coleta:
                self.fila.append(
                    [(req.name, req.priority) for req in self.recurso_leitos.queue]
                )
                self.pacientedia.append(self.pacientes_internados)

                self.solicitacaopendentedia.append(
                    sum(
                        self.lista_pacientes[p]["status"] == "solicitacao"
                        for p in self.lista_pacientes
                    )
                )
