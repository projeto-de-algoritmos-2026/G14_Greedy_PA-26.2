"""Ganchos de observacao do bot para a estrategia de parada (fase 6).

A interface narra a partida enquanto ela acontece, entao precisa saber duas
coisas que o runner decidia por dentro e nao contava pra ninguem: ONDE a
estrategia planejou parar (`ao_paradas`) e QUANDO a recarga aconteceu
(`ao_recarga`). Sao opcionais, no mesmo estilo de `ao_planejar` e `ao_passo`:
sem eles o bot se comporta exatamente como antes.

Mesmo mapa do teste da estrategia: corredor 6x6 de concreto, pokebola em
(0, 5), centros em (0, 2) e (0, 3), tanque de 3.
"""
import pytest

import grid
from bot.runner import executar_bot
from greedy.estrategias import guloso, todo_centro


@pytest.fixture
def mapa():
    g = grid.Grid(size=6, seed=1, centros=0)
    for linha in g.grid:
        for celula in linha:
            celula.occupied_with = grid.LIVRE
            celula.terrain = grid.CONCRETO
    g.celula(0, 5).occupied_with = grid.POKEBOLA
    g.celula(0, 2).occupied_with = grid.CENTRO
    g.celula(0, 3).occupied_with = grid.CENTRO
    return g


@pytest.fixture
def viajante(jogador):
    jogador.energia = jogador.energia_max = 3
    return jogador


class TestAoParadas:
    def test_recebe_os_marcos_e_as_paradas_escolhidas_de_cada_plano(self, mapa, viajante):
        chamadas = []
        executar_bot(mapa, viajante, estrategia=guloso,
                     ao_paradas=lambda marcos, escolhidas: chamadas.append((marcos, escolhidas)))
        # Um plano ate a pokebola e, depois da recarga, outro dali.
        assert len(chamadas) == 2
        marcos, escolhidas = chamadas[0]
        assert marcos[0] == (0, False)
        assert marcos[-1][0] == 5
        assert escolhidas == [3]  # o centro de (0, 3): o mais longe que o tanque de 3 alcanca

    def test_marcos_sao_os_do_plano_e_nao_uma_copia_de_outra_rota(self, mapa, viajante):
        chamadas = []
        executar_bot(mapa, viajante, estrategia=todo_centro,
                     ao_paradas=lambda marcos, escolhidas: chamadas.append(escolhidas))
        assert chamadas[0] == [2, 3]  # todo centro: os dois

    def test_avisa_quando_nao_ha_recarga_possivel(self, mapa, viajante):
        """Guloso sem saida devolve None: a tela precisa receber o None pra dizer
        'sem solucao' em vez de ficar calada."""
        mapa.celula(0, 3).occupied_with = grid.LIVRE
        viajante.energia = viajante.energia_max = 2
        chamadas = []
        resultado = executar_bot(mapa, viajante, estrategia=guloso,
                                 ao_paradas=lambda m, e: chamadas.append(e))
        assert chamadas == [None]
        assert resultado.motivo_parada == "rota sem recarga possivel"

    def test_chega_antes_do_primeiro_passo(self, mapa, viajante):
        ordem = []
        executar_bot(mapa, viajante, estrategia=guloso,
                     ao_paradas=lambda m, e: ordem.append("paradas"),
                     ao_passo=lambda mov, d: ordem.append("passo"))
        assert ordem[0] == "paradas"

    def test_nao_dispara_sem_estrategia(self, mapa, viajante):
        chamadas = []
        executar_bot(mapa, viajante, ao_paradas=lambda m, e: chamadas.append(e))
        assert chamadas == []

    def test_nao_dispara_sem_energia(self, mapa, jogador):
        chamadas = []
        executar_bot(mapa, jogador, estrategia=guloso,
                     ao_paradas=lambda m, e: chamadas.append(e))
        assert chamadas == []


class TestAoRecarga:
    def test_recebe_posicao_quanto_entrou_e_quanto_sobrava(self, mapa, viajante):
        chamadas = []
        executar_bot(mapa, viajante, estrategia=guloso,
                     ao_recarga=lambda pos, entrou, sobrava: chamadas.append((pos, entrou, sobrava)))
        # Chega em (0, 3) com o tanque zerado: entrou 3, sobrava 0.
        assert chamadas == [((0, 3), 3, 0)]

    def test_entrou_mais_sobrava_e_sempre_o_tanque_cheio(self, mapa, viajante):
        chamadas = []
        executar_bot(mapa, viajante, estrategia=todo_centro,
                     ao_recarga=lambda pos, entrou, sobrava: chamadas.append((pos, entrou, sobrava)))
        assert [pos for pos, _, _ in chamadas] == [(0, 2), (0, 3)]
        for _, entrou, sobrava in chamadas:
            assert entrou + sobrava == viajante.energia_max

    def test_soma_do_que_sobrava_e_a_energia_desperdicada_do_resultado(self, mapa, viajante):
        """O numero que a tela acumula e o que o resultado final reporta."""
        sobras = []
        resultado = executar_bot(mapa, viajante, estrategia=todo_centro,
                                 ao_recarga=lambda pos, entrou, sobrava: sobras.append(sobrava))
        assert sum(sobras) == resultado.energia_desperdicada == 3
        assert len(sobras) == resultado.paradas == 2

    def test_dispara_depois_de_o_jogador_ja_estar_recarregado(self, mapa, viajante):
        energia_no_gancho = []
        executar_bot(mapa, viajante, estrategia=guloso,
                     ao_recarga=lambda *a: energia_no_gancho.append(viajante.energia))
        assert energia_no_gancho == [3]

    def test_nao_dispara_sem_estrategia(self, mapa, viajante):
        chamadas = []
        executar_bot(mapa, viajante, ao_recarga=lambda *a: chamadas.append(a))
        assert chamadas == []


class TestSemGanchosNadaMuda:
    @pytest.mark.parametrize("estrategia", [guloso, todo_centro])
    def test_mesmo_resultado_com_e_sem_observador(self, estrategia):
        def jogar(**ganchos):
            g = grid.Grid(size=6, seed=1, centros=0)
            for linha in g.grid:
                for celula in linha:
                    celula.occupied_with = grid.LIVRE
                    celula.terrain = grid.CONCRETO
            g.celula(0, 5).occupied_with = grid.POKEBOLA
            g.celula(0, 2).occupied_with = grid.CENTRO
            g.celula(0, 3).occupied_with = grid.CENTRO
            import models
            p = models.Player("Lucas", "Male", "Fun",
                              [models.Pokemon("Faisca", "Male", "Pikachu", "Electric",
                                              {"Shock": 40, "Tail Whip": 25})],
                              {"pokeball": 0, "potion": 0}, 0, energia=3, energia_max=3)
            r = executar_bot(g, p, estrategia=estrategia, **ganchos)
            return (r.paradas, r.energia_desperdicada, r.replanejamentos,
                    r.motivo_parada, g.posicao, p.energia)

        com = jogar(ao_paradas=lambda m, e: None, ao_recarga=lambda *a: None)
        assert com == jogar()
