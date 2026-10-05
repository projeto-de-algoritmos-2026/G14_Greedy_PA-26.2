"""API do trabalho 2, parte do jogo humano (fase 6).

Como em test_webdemo.py, tudo bate nas funcoes puras de `webdemo/api_greedy.py`,
sem abrir socket. O que precisa de garantia aqui e o contrato que a pagina
consome: o custo aberto em terreno e conteudo, o desmaio que diz o porque, e as
quatro vizinhas que avisam ANTES de o jogador pisar.
"""
import pytest

import game
import grid
from bench.partidas import novo_jogador
from greedy.estrategias import ESTRATEGIAS
from webdemo import api_greedy as api


@pytest.fixture(autouse=True)
def batalha_sem_efeito(monkeypatch):
    """So importa a conta de energia; a batalha real e aleatoria e imprime."""
    monkeypatch.setattr(game, "battle", lambda *a, **k: None)


def mapa_de_concreto(size=5):
    g = grid.Grid(size=size, seed=5, centros=0)
    for linha in g.grid:
        for celula in linha:
            celula.occupied_with = grid.LIVRE
            celula.terrain = grid.CONCRETO
    g.row_pos, g.col_pos = 0, 0
    return g


def sessao(mapa, energia):
    """Registra uma partida com o mapa montado a mao e devolve (id, player)."""
    jogador = novo_jogador()
    jogador.pokemon_list[0].health = 100
    jogador.energia = jogador.energia_max = energia
    return api._nova_sessao(mapa, jogador), jogador


class TestConfig:
    def test_lista_todas_as_estrategias_do_greedy(self):
        ids = [e["id"] for e in api.config()["estrategias"]]
        assert ids == list(ESTRATEGIAS)

    def test_cada_estrategia_tem_nome_e_descricao(self):
        for e in api.config()["estrategias"]:
            assert e["nome"] and e["descricao"]

    def test_niveis_de_alcance_sao_multiplos_do_menor_tanque(self):
        """0,75x, 1x e 1,5x do menor tanque que vence. Nao sao as fracoes do
        benchmark (30/50/75% do custo de UMA rota): aquelas deixavam os tres
        presets inviaveis em todo mapa vencido da missao inteira."""
        assert api.config()["niveis"] == {"abaixo": 0.75, "minimo": 1.0, "folgado": 1.5}

    def test_limites_do_tanque(self):
        c = api.config()
        assert 1 <= c["energia_min"] < c["energia_max"]


class TestCriarJogo:
    def test_traz_mapa_centros_e_jogador_com_energia(self):
        dados = api.criar_jogo(8, 3, energia=20)
        assert dados["size"] == 8 and len(dados["celulas"]) == 8
        assert dados["jogador"]["energia"] == dados["jogador"]["energia_max"] == 20
        assert dados["posicao"] == [0, 0]
        assert dados["sessao"]

    def test_lista_os_centros_do_mapa(self):
        dados = api.criar_jogo(15, 2, energia=20)
        esperado = sorted(list(p) for p in grid.Grid(size=15, seed=2).centros())
        assert sorted(dados["centros"]) == esperado
        for r, c in dados["centros"]:
            assert dados["celulas"][r][c]["conteudo"] == "centro"

    def test_energia_e_presa_na_faixa(self):
        c = api.config()
        assert api.criar_jogo(8, 3, energia=10 ** 9)["jogador"]["energia_max"] == c["energia_max"]
        assert api.criar_jogo(8, 3, energia=-4)["jogador"]["energia_max"] == c["energia_min"]

    def test_sem_energia_usa_o_tanque_recomendado(self):
        dados = api.criar_jogo(15, 2)
        assert dados["jogador"]["energia_max"] == api.dados_alcance(15, 2)["recomendado"]

    def test_devolve_as_quatro_vizinhas(self):
        dados = api.criar_jogo(8, 3, energia=20)
        assert set(dados["vizinhas"]) == {"W", "A", "S", "D"}

    def test_duas_partidas_nao_dividem_estado(self):
        a = api.criar_jogo(8, 3, energia=20)["sessao"]
        b = api.criar_jogo(8, 3, energia=20)["sessao"]
        assert a != b
        api.mover_jogo(a, "D")
        assert api.estado_jogo(b)["posicao"] == [0, 0]


class TestMover:
    def test_passo_de_concreto_gasta_so_terreno(self):
        mapa = mapa_de_concreto()
        sid, jogador = sessao(mapa, 10)
        r = api.mover_jogo(sid, "D")
        assert r["valido"] is True
        assert r["custo"] == {"terreno": 1, "conteudo": 0, "total": 1}
        assert r["energia_gasta"] == 1
        assert (r["energia_antes"], r["energia_depois"]) == (10, 9)

    def test_batalha_abre_o_custo_em_terreno_e_batalha(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).terrain = grid.GRAMA
        mapa.celula(0, 1).occupied_with = grid.POKEMON
        sid, _ = sessao(mapa, 30)
        r = api.mover_jogo(sid, "D")
        assert r["batalhou"] is True
        assert r["custo"] == {"terreno": 3, "conteudo": 8, "total": 11}
        assert r["conteudo"] == "pokemon"
        assert r["energia_depois"] == 19

    def test_treinador_cobra_mais_que_pokemon(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).occupied_with = grid.CPU
        sid, _ = sessao(mapa, 30)
        r = api.mover_jogo(sid, "D")
        assert r["conteudo"] == "cpu"
        assert (r["custo"]["terreno"], r["custo"]["conteudo"]) == (1, 12)

    def test_entrar_no_centro_avisa_e_nao_recarrega(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).occupied_with = grid.CENTRO
        sid, _ = sessao(mapa, 10)
        r = api.mover_jogo(sid, "D")
        assert r["em_centro"] is True
        assert r["energia_depois"] == 9  # pisar nao enche o tanque

    def test_parede_e_agua_sem_surf_nao_custam_nada(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).terrain = grid.AGUA
        sid, _ = sessao(mapa, 10)
        r = api.mover_jogo(sid, "D")
        assert r["valido"] is False and r["motivo"] == "agua sem surf"
        assert r["custo"] is None and r["desmaiou"] is False
        assert r["energia_depois"] == 10

    def test_fora_do_mapa(self):
        sid, _ = sessao(mapa_de_concreto(), 10)
        r = api.mover_jogo(sid, "W")
        assert r["valido"] is False and r["motivo"] == "fora do mapa"


class TestDesmaio:
    @pytest.fixture
    def batalha_cara(self):
        """Pokemon selvagem em grama: entrar custa 3 + 8 = 11, o tanque tem 5."""
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).terrain = grid.GRAMA
        mapa.celula(0, 1).occupied_with = grid.POKEMON
        sid, _ = sessao(mapa, 5)
        return sid

    def test_diz_quanto_custava_quanto_tinha_e_quanto_faltou(self, batalha_cara):
        r = api.mover_jogo(batalha_cara, "D")
        assert r["desmaiou"] is True and r["valido"] is False
        assert r["custo"] == {"terreno": 3, "conteudo": 8, "total": 11}
        assert r["energia_antes"] == 5
        assert r["faltaram"] == 6

    def test_nao_anda_e_nao_gasta(self, batalha_cara):
        r = api.mover_jogo(batalha_cara, "D")
        assert r["energia_gasta"] == 0 and r["energia_depois"] == 5
        assert r["posicao"] == [0, 0]

    def test_a_partida_acaba_com_motivo(self, batalha_cara):
        api.mover_jogo(batalha_cara, "D")
        depois = api.mover_jogo(batalha_cara, "S")
        assert "erro" in depois and "sem energia" in depois["erro"]
        assert api.estado_jogo(batalha_cara)["jogador"]["situacao"] == "derrota"

    def test_explica_o_que_era_a_entrada_mesmo_sendo_batalha(self, batalha_cara):
        r = api.mover_jogo(batalha_cara, "D")
        assert r["conteudo"] == "pokemon"
        assert r["batalhou"] is False  # a batalha nao aconteceu: ele caiu antes


class TestVizinhas:
    def test_avisam_o_custo_exato_que_sera_cobrado(self):
        """A dica so vale se nao mentir: pra cada direcao, o custo previsto e o
        que o passo de verdade cobra."""
        for tecla in "DS":
            mapa = mapa_de_concreto()
            mapa.celula(0, 1).terrain = grid.GRAMA
            mapa.celula(0, 1).occupied_with = grid.CPU
            mapa.celula(1, 0).terrain = grid.GRAMA
            sid, _ = sessao(mapa, 40)
            previsto = api.estado_jogo(sid)["vizinhas"][tecla]["custo"]
            real = api.mover_jogo(sid, tecla)["custo"]
            assert previsto == real

    def test_marcam_a_que_desmaia(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).occupied_with = grid.CPU
        sid, _ = sessao(mapa, 5)
        v = api.estado_jogo(sid)["vizinhas"]
        assert v["D"]["desmaia"] is True and v["D"]["sobram"] is None
        assert v["S"]["desmaia"] is False and v["S"]["sobram"] == 4

    def test_dizem_porque_nao_da_pra_ir(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).terrain = grid.AGUA
        sid, _ = sessao(mapa, 10)
        v = api.estado_jogo(sid)["vizinhas"]
        assert v["D"]["valido"] is False and v["D"]["motivo"] == "agua sem surf"
        assert v["W"]["valido"] is False and v["W"]["motivo"] == "fora do mapa"
        assert v["D"]["custo"] is None

    def test_sao_recalculadas_apos_cada_passo(self):
        mapa = mapa_de_concreto()
        sid, _ = sessao(mapa, 10)
        depois = api.mover_jogo(sid, "D")["vizinhas"]
        assert depois["A"]["posicao"] == [0, 0]
        assert depois["D"]["posicao"] == [0, 2]


class TestRecarregar:
    def test_enche_o_tanque_e_diz_quanto_sobrava(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).occupied_with = grid.CENTRO
        sid, _ = sessao(mapa, 10)
        api.mover_jogo(sid, "D")
        r = api.recarregar_jogo(sid)
        assert r["recarregou"] is True
        assert (r["entrou"], r["sobrava"]) == (1, 9)
        assert r["jogador"]["energia"] == 10

    def test_fora_de_um_centro_nao_faz_nada_e_diz_porque(self):
        sid, _ = sessao(mapa_de_concreto(), 10)
        r = api.recarregar_jogo(sid)
        assert r["recarregou"] is False and r["motivo"] == "sem centro aqui"

    def test_tanque_cheio_nao_recarrega(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 0).occupied_with = grid.CENTRO
        sid, _ = sessao(mapa, 10)
        r = api.recarregar_jogo(sid)
        assert r["recarregou"] is False and r["motivo"] == "tanque cheio"

    def test_depois_do_desmaio_nao_recarrega(self):
        mapa = mapa_de_concreto()
        mapa.celula(0, 1).occupied_with = grid.CPU
        sid, _ = sessao(mapa, 3)
        api.mover_jogo(sid, "D")
        assert "erro" in api.recarregar_jogo(sid)


class TestSessao:
    def test_desconhecida(self):
        assert "erro" in api.mover_jogo("nao-existe", "D")
        assert "erro" in api.recarregar_jogo("nao-existe")
        assert "erro" in api.estado_jogo("nao-existe")

    def test_a_mais_antiga_sai_ao_passar_do_limite(self):
        primeira = api.criar_jogo(8, 1, energia=10)["sessao"]
        for seed in range(api.MAX_SESSOES):
            api.criar_jogo(8, seed, energia=10)
        assert "erro" in api.estado_jogo(primeira)
