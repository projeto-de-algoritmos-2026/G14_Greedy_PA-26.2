"""O bot jogando com uma estrategia de parada.

Mapa 6x6 de concreto (cada passo custa 1), uma pokebola em (0, 5) e centros
em (0, 2) e (0, 3). A rota do Dijkstra e a linha de cima, custo 5, e o tanque
e de 3: sem parar nao chega.
"""
import pytest

import grid
from bot.runner import executar_bot
from greedy.estrategias import ESTRATEGIAS, guloso, limiar, todo_centro


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


def test_sem_estrategia_anda_a_rota_inteira_e_desmaia(mapa, viajante):
    resultado = executar_bot(mapa, viajante)
    assert resultado.motivo_parada == "sem energia"
    assert resultado.paradas == 0
    assert mapa.posicao == (0, 3)


def test_guloso_para_uma_vez_no_centro_mais_distante(mapa, viajante):
    resultado = executar_bot(mapa, viajante, estrategia=guloso)
    assert resultado.objetivos_visitados == [(0, 5)]
    assert resultado.paradas == 1
    # Chega no centro de (0, 3) com o tanque zerado: nada desperdicado.
    assert resultado.energia_desperdicada == 0
    assert resultado.motivo_parada == "sem objetivos alcançaveis"


def test_todo_centro_para_duas_vezes_e_desperdica(mapa, viajante):
    resultado = executar_bot(mapa, viajante, estrategia=todo_centro)
    assert resultado.objetivos_visitados == [(0, 5)]
    assert resultado.paradas == 2
    # Sobra 1 em (0, 2) e 2 em (0, 3), logo depois de encher.
    assert resultado.energia_desperdicada == 3


def test_recarga_enche_o_tanque_e_replaneja(mapa, viajante):
    resultado = executar_bot(mapa, viajante, estrategia=guloso)
    # Um plano ate a parada, outro dali ate a pokebola, um ultimo sem alvo.
    assert resultado.replanejamentos == 3
    assert viajante.energia == 1
    assert mapa.posicao == (0, 5)


def test_limiar_baixo_desmaia_no_caminho(mapa, viajante):
    # Tanque de 4: em (0, 2) sobram 2 (50%) e em (0, 3) sobra 1 (25%), acima
    # dos 10%. Passa pelos dois centros e desmaia antes da pokebola.
    viajante.energia = viajante.energia_max = 4
    resultado = executar_bot(mapa, viajante, estrategia=limiar(10))
    assert resultado.motivo_parada == "sem energia"
    assert resultado.paradas == 0


def test_estrategia_nao_faz_nada_sem_energia(mapa, jogador):
    """Jogador do trabalho 1 (energia None): a estrategia e ignorada."""
    resultado = executar_bot(mapa, jogador, estrategia=guloso)
    assert resultado.objetivos_visitados == [(0, 5)]
    assert resultado.paradas == 0


@pytest.mark.parametrize("nome", ["guloso", "todo_centro", "limiar_25",
                                  "limiar_50", "otimo"])
def test_estrategias_que_chegam_no_corredor(mapa, viajante, nome):
    resultado = executar_bot(mapa, viajante, estrategia=ESTRATEGIAS[nome])
    assert resultado.objetivos_visitados == [(0, 5)]
    assert resultado.paradas >= 1
