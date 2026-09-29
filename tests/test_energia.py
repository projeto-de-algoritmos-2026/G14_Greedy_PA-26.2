"""Energia e Centro Pokemon (trabalho 2, fase 1).

Energia e o combustivel do caminhoneiro: cada passo gasta o mesmo peso que o
Dijkstra do trabalho 1 usa na aresta, e o Centro Pokemon e o posto onde ela
recarrega. Energia None desliga tudo e deixa o jogo do trabalho 1 intacto.
"""
import pytest

import game
import grid
import models
from graph.cost import custo_entrada
from graph.state import Estado


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
                         energia=10, energia_max=10)


class TestPlayerEEstado:
    def test_player_padrao_nao_usa_energia(self):
        jogador = models.Player()
        assert jogador.energia is None
        assert jogador.usa_energia is False
        assert jogador.desmaiado is False

    def test_estado_carrega_a_energia(self, viajante):
        estado = Estado.de(viajante)
        assert estado.energia == 10
        assert estado.energia_max == 10

    def test_estado_e_retrato_e_nao_acompanha_o_player(self, viajante):
        estado = Estado.de(viajante)
        viajante.energia = 3
        assert estado.energia == 10

    def test_energia_nao_muda_o_custo_da_celula(self, mapa):
        """A energia decide ate onde se vai sem parar, nao quanto custa andar.
        Se ela entrasse no peso, o Dijkstra e o caminhoneiro dependeriam um do
        outro e nenhum dos dois seria otimo."""
        celula = mapa.celula(0, 1)
        cheio = Estado(hp_lider=100, energia=50, energia_max=50)
        quase_vazio = Estado(hp_lider=100, energia=1, energia_max=50)
        assert custo_entrada(celula, cheio) == custo_entrada(celula, quase_vazio)


class TestGastoDeEnergia:
    def test_passo_gasta_o_custo_de_entrada(self, mapa, viajante):
        res = game.mover(mapa, viajante, "D")
        assert res.valido is True
        assert res.energia_gasta == 1
        assert viajante.energia == 9

    def test_grama_gasta_mais_que_concreto(self, mapa, viajante):
        mapa.celula(0, 1).terrain = grid.GRAMA
        res = game.mover(mapa, viajante, "D")
        assert res.energia_gasta == 3
        assert viajante.energia == 7

    def test_gasto_e_o_mesmo_numero_que_o_grafo_usa(self, mapa, viajante, monkeypatch):
        """Inclui a penalidade de batalha, calculada com o estado de ANTES do
        passo: e o peso que o Dijkstra viu ao planejar."""
        monkeypatch.setattr(game, "battle", lambda *a, **k: None)
        viajante.energia = viajante.energia_max = 20
        mapa.celula(0, 1).occupied_with = grid.CPU
        esperado = custo_entrada(mapa.celula(0, 1), Estado.de(viajante))
        res = game.mover(mapa, viajante, "D", automatico=True)
        assert res.energia_gasta == esperado == 13
        assert viajante.energia == 7

    def test_energia_exata_ainda_anda(self, mapa, viajante):
        viajante.energia = 1
        res = game.mover(mapa, viajante, "D")
        assert res.valido is True
        assert viajante.energia == 0
        assert viajante.desmaiado is False

    def test_sem_energia_desmaia_e_nao_anda(self, mapa, viajante):
        viajante.energia = 2
        mapa.celula(0, 1).terrain = grid.GRAMA
        res = game.mover(mapa, viajante, "D")
        assert res.valido is False
        assert res.desmaiou is True
        assert res.motivo == "sem energia"
        assert mapa.posicao == (0, 0)
        assert viajante.energia == 2
        assert viajante.desmaiado is True

    def test_desmaio_encerra_a_partida(self, mapa, viajante):
        viajante.energia = 0
        game.mover(mapa, viajante, "D")
        assert game.partida_encerrada(viajante) == "sem energia"

    def test_desmaio_nao_consome_a_celula(self, mapa, viajante):
        viajante.energia = 0
        mapa.celula(0, 1).occupied_with = grid.POKEBOLA
        game.mover(mapa, viajante, "D")
        assert mapa.celula(0, 1).occupied_with == grid.POKEBOLA
        assert viajante.bag["pokeball"] == 0

    def test_movimento_invalido_por_outro_motivo_nao_gasta(self, mapa, viajante):
        mapa.celula(0, 1).occupied_with = grid.INACESSIVEL
        game.mover(mapa, viajante, "D")
        assert viajante.energia == 10
        assert viajante.desmaiado is False


class TestCentro:
    def test_centro_nao_some_quando_pisado(self, mapa, viajante):
        mapa.celula(0, 1).occupied_with = grid.CENTRO
        res = game.mover(mapa, viajante, "D")
        assert res.em_centro is True
        assert mapa.celula(0, 1).occupied_with == grid.CENTRO

    def test_passar_pelo_centro_nao_recarrega_sozinho(self, mapa, viajante):
        """Passar sem parar e justamente a escolha do caminhoneiro."""
        mapa.celula(0, 1).occupied_with = grid.CENTRO
        game.mover(mapa, viajante, "D")
        assert viajante.energia == 9

    def test_recarregar_no_centro_enche_o_tanque(self, mapa, viajante):
        mapa.celula(0, 1).occupied_with = grid.CENTRO
        game.mover(mapa, viajante, "D")
        game.mover(mapa, viajante, "A")
        game.mover(mapa, viajante, "D")
        assert viajante.energia == 7
        assert game.recarregar(mapa, viajante) == 3
        assert viajante.energia == 10

    def test_recarregar_fora_do_centro_nao_faz_nada(self, mapa, viajante):
        game.mover(mapa, viajante, "D")
        assert game.recarregar(mapa, viajante) == 0
        assert viajante.energia == 9

    def test_recarregar_com_tanque_cheio_devolve_zero(self, mapa, viajante):
        mapa.celula(0, 0).occupied_with = grid.CENTRO
        assert game.recarregar(mapa, viajante) == 0

    def test_recarregar_sem_energia_ligada_nao_faz_nada(self, mapa):
        jogador = models.Player()
        mapa.celula(0, 0).occupied_with = grid.CENTRO
        assert game.recarregar(mapa, jogador) == 0
        assert jogador.energia is None

    def test_centro_custa_so_o_terreno(self, mapa):
        celula = mapa.celula(0, 1)
        celula.occupied_with = grid.CENTRO
        celula.terrain = grid.GRAMA
        assert custo_entrada(celula, Estado(hp_lider=100)) == 3


class TestCentrosNoMapa:
    def test_mapa_tem_centros_por_padrao(self):
        g = grid.Grid(size=15, seed=1)
        assert len(g.centros()) == round(15 * 15 * grid.DENSIDADE_CENTRO)

    def test_quantidade_explicita(self):
        assert len(grid.Grid(size=15, seed=1, centros=5).centros()) == 5
        assert grid.Grid(size=15, seed=1, centros=0).centros() == []

    def test_mesma_seed_mesmos_centros(self):
        assert grid.Grid(size=15, seed=7).centros() == grid.Grid(size=15, seed=7).centros()

    def test_centro_nunca_na_origem_nem_na_agua(self):
        for seed in range(50):
            g = grid.Grid(size=15, seed=seed)
            for r, c in g.centros():
                assert (r, c) != (0, 0)
                assert g.celula(r, c).terrain != grid.AGUA

    def test_centros_nao_mudam_o_resto_do_mapa_do_trabalho_1(self):
        """O sorteio dos centros vem depois do mapa inteiro. Tirando as
        celulas que viraram centro, o mapa e o mesmo de uma seed sem centro,
        e por isso o benchmark do trabalho 1 continua reproduzivel."""
        for seed in range(20):
            com = grid.Grid(size=15, seed=seed)
            sem = grid.Grid(size=15, seed=seed, centros=0)
            for r in range(15):
                for c in range(15):
                    a, b = com.celula(r, c), sem.celula(r, c)
                    assert a.terrain == b.terrain
                    if a.occupied_with == grid.CENTRO:
                        assert b.occupied_with == grid.LIVRE
                    else:
                        assert a.occupied_with == b.occupied_with

    def test_centro_tem_emoji_proprio(self):
        assert grid.EMOJI[grid.CENTRO] == "\U0001F3E5"


def test_partida_sem_energia_continua_igual_ao_trabalho_1(mapa):
    """Energia None: passo nao gasta nada e nunca desmaia."""
    jogador = models.Player()
    for _ in range(3):
        res = game.mover(mapa, jogador, "D")
        assert res.valido is True
        assert res.energia_gasta == 0
    assert jogador.energia is None
    assert game.partida_encerrada(jogador) == "sem pokemon"
