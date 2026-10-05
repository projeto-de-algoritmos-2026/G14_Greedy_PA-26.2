"""O custo de entrar numa celula, separado em terreno e conteudo (fase 6).

A interface precisa dizer "3 de grama + 8 de batalha" e, quando o jogador
desmaia, quanto a entrada cobrava. Essa conta nasce em mover(), com as mesmas
funcoes de graph/cost.py que o Dijkstra usa como peso de aresta: uma so
definicao da regra, e a pagina so repete o que o jogo calculou.

O contrato: em passo valido, custo_terreno + custo_conteudo == energia_gasta.
No desmaio o passo nao acontece (energia_gasta fica 0), mas os dois campos
trazem o que a entrada cobraria.
"""
import random

import pytest

import game
import grid
import models
from game import Movimento


@pytest.fixture
def mapa():
    g = grid.Grid(size=4, seed=5, centros=0)
    for linha in g.grid:
        for celula in linha:
            celula.occupied_with = grid.LIVRE
            celula.terrain = grid.CONCRETO
    g.row_pos, g.col_pos = 0, 0
    return g


@pytest.fixture
def viajante():
    return models.Player("Lucas", "Male", "Fun",
                         [models.Pokemon("Faisca", "Male", "Pikachu", "Electric",
                                         {"Shock": 40, "Tail Whip": 25})],
                         {"pokeball": 0, "potion": 0}, 0,
                         energia=30, energia_max=30)


@pytest.fixture(autouse=True)
def batalha_sem_efeito(monkeypatch):
    """Aqui so importa a conta de energia; a batalha em si e aleatoria e imprime."""
    monkeypatch.setattr(game, "battle", lambda *a, **k: None)


def test_movimento_antigo_continua_valido_sem_os_campos_novos():
    """Quem constroi Movimento sem passar o custo (testes do T1, o bot) nao quebra."""
    m = Movimento(True, (0, 0))
    assert m.custo_terreno == 0
    assert m.custo_conteudo == 0


class TestPassoValido:
    def test_concreto_livre_so_tem_custo_de_terreno(self, mapa, viajante):
        res = game.mover(mapa, viajante, "D")
        assert (res.custo_terreno, res.custo_conteudo) == (1, 0)
        assert res.energia_gasta == 1

    @pytest.mark.parametrize("conteudo, penalidade", [(grid.POKEMON, 8), (grid.CPU, 12)])
    def test_batalha_separa_o_terreno_da_penalidade(self, mapa, viajante, conteudo, penalidade):
        mapa.celula(0, 1).terrain = grid.GRAMA
        mapa.celula(0, 1).occupied_with = conteudo
        res = game.mover(mapa, viajante, "D", automatico=True)
        assert res.batalhou is True
        assert res.custo_terreno == 3
        assert res.custo_conteudo == penalidade
        assert res.energia_gasta == 3 + penalidade

    @pytest.mark.parametrize("hp, grama", [(100, 3), (50, 5), (0, 6)])
    def test_grama_acompanha_o_hp_do_lider(self, mapa, viajante, hp, grama):
        """O terreno e o unico pedaco que depende do HP; o conteudo nao."""
        viajante.pokemon_list[0].health = hp
        mapa.celula(0, 1).terrain = grid.GRAMA
        res = game.mover(mapa, viajante, "D")
        assert res.custo_terreno == grama
        assert res.custo_conteudo == 0

    def test_pokebola_nao_cobra_conteudo(self, mapa, viajante):
        mapa.celula(0, 1).occupied_with = grid.POKEBOLA
        res = game.mover(mapa, viajante, "D")
        assert res.pegou_pokebola is True
        assert (res.custo_terreno, res.custo_conteudo) == (1, 0)

    def test_celula_visitada_nao_cobra_a_batalha_de_novo(self, mapa, viajante):
        """A batalha so acontece na primeira passagem. Na volta a celula e VISITADO
        e a conta do jogo e a do grafo: so o terreno."""
        mapa.celula(0, 1).occupied_with = grid.POKEMON
        primeira = game.mover(mapa, viajante, "D", automatico=True)
        game.mover(mapa, viajante, "A")
        segunda = game.mover(mapa, viajante, "D")
        assert primeira.custo_conteudo == 8
        assert segunda.custo_conteudo == 0
        assert segunda.energia_gasta == segunda.custo_terreno == 1

    def test_soma_fecha_em_todo_passo_valido_de_varios_mapas(self, viajante):
        """A invariante que a interface assume, varrida em mapas reais: nunca ha
        passo em que o gasto de energia nao seja terreno mais conteudo."""
        passos = 0
        for size in (8, 15):
            for seed in range(12):
                mapa = grid.Grid(size=size, seed=seed)
                jogador = models.Player(
                    "Lucas", "Male", "Fun",
                    [models.Pokemon("Faisca", "Male", "Pikachu", "Electric",
                                    {"Shock": 40, "Tail Whip": 25})],
                    {"pokeball": 0, "potion": 0}, 0,
                    energia=10 ** 6, energia_max=10 ** 6, surf=True)
                sorteio = random.Random(f"{size}-{seed}")
                for _ in range(150):
                    res = game.mover(mapa, jogador, sorteio.choice("WASD"), automatico=True)
                    if not res.valido:
                        continue
                    passos += 1
                    assert res.custo_terreno + res.custo_conteudo == res.energia_gasta
                    assert res.custo_terreno >= 1
                    assert (res.custo_conteudo > 0) == res.batalhou
        assert passos > 500  # a varredura nao pode ter passado vazia


class TestDesmaio:
    @pytest.fixture
    def batalha_cara(self, mapa, viajante):
        """Pokemon selvagem em grama: entrar custa 3 + 8 = 11, e o tanque tem 5."""
        mapa.celula(0, 1).terrain = grid.GRAMA
        mapa.celula(0, 1).occupied_with = grid.POKEMON
        viajante.energia = 5
        return mapa

    def test_informa_o_que_a_entrada_cobraria(self, batalha_cara, viajante):
        res = game.mover(batalha_cara, viajante, "D", automatico=True)
        assert res.desmaiou is True
        assert res.valido is False
        assert (res.custo_terreno, res.custo_conteudo) == (3, 8)

    def test_nao_gasta_nada_e_nao_anda(self, batalha_cara, viajante):
        res = game.mover(batalha_cara, viajante, "D", automatico=True)
        assert res.energia_gasta == 0
        assert viajante.energia == 5
        assert viajante.desmaiado is True
        assert batalha_cara.posicao == (0, 0)
        assert res.batalhou is False

    def test_a_falta_sai_da_conta_sem_a_pagina_recalcular(self, batalha_cara, viajante):
        """'Entrou com 5, a batalha cobrava 11, faltaram 6' usa so o que o jogo devolveu."""
        antes = viajante.energia
        res = game.mover(batalha_cara, viajante, "D", automatico=True)
        assert (res.custo_terreno + res.custo_conteudo) - antes == 6


class TestSemEnergia:
    """Trabalho 1: energia None desliga a regra, e os campos novos ficam zerados."""

    def test_passo_do_t1_nao_preenche_o_custo(self, mapa):
        jogador = models.Player()
        mapa.celula(0, 1).terrain = grid.GRAMA
        res = game.mover(mapa, jogador, "D")
        assert res.valido is True
        assert (res.energia_gasta, res.custo_terreno, res.custo_conteudo) == (0, 0, 0)

    @pytest.mark.parametrize("direcao", ["W", "A", "X"])
    def test_passo_recusado_nao_preenche_o_custo(self, mapa, viajante, direcao):
        res = game.mover(mapa, viajante, direcao)
        assert res.valido is False
        assert (res.custo_terreno, res.custo_conteudo) == (0, 0)
