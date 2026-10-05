"""Alcance minimo e viabilidade de uma rota (fase 6, decisao D5).

O jogador escolhe o tamanho do tanque na interface, e a tela precisa dizer na
hora se aquela escolha tem solucao. A pergunta ja tem resposta exata no
caminhoneiro: `paradas` devolve None quando algum trecho entre pontos de
recarga consecutivos passa do alcance. O alcance minimo e o menor tanque pra
qual isso nao acontece, isto e, o maior desses trechos quando se para em todo
Centro (parar em mais Centros nunca atrapalha, porque recarregar enche o
tanque).

Os testes conferem a definicao contra duas fontes independentes: o proprio
guloso (`paradas`) e a forca bruta sobre todos os subconjuntos.
"""
import random

import pytest

from greedy import paradas
from greedy.forca_bruta import candidatos, paradas_forca_bruta
from greedy.viabilidade import alcance_minimo, trecho_critico, viabilidade

# Exemplo do plano: rota de custo 50 e centros em 8, 15, 22, 30, 38 e 45. O
# maior trecho entre pontos de recarga e 8 (0 a 8, 22 a 30 e 30 a 38).
PLANO = [(0, False), (8, True), (15, True), (22, True), (30, True), (38, True),
         (45, True), (50, False)]


def rota_sorteada(seed):
    rng = random.Random(seed)
    densidade = rng.choice([0.15, 0.3, 0.5, 0.8])
    marcos = [(0, rng.random() < densidade)]
    acumulado = 0
    for _ in range(rng.randint(1, 30)):
        acumulado += rng.randint(1, 6)
        marcos.append((acumulado, rng.random() < densidade))
    centros = candidatos(marcos)
    if len(centros) > 12:  # a forca bruta e 2^k
        for i in rng.sample(centros, len(centros) - 12):
            marcos[i] = (marcos[i][0], False)
    return marcos


class TestAlcanceMinimo:
    def test_exemplo_do_plano(self):
        assert alcance_minimo(PLANO) == 8

    def test_sem_centro_o_tanque_tem_que_cobrir_a_rota_inteira(self):
        marcos = [(0, False), (3, False), (7, False), (12, False)]
        assert alcance_minimo(marcos) == 12

    def test_so_centros_fora_da_origem_e_do_destino_contam_como_recarga(self):
        """Marcar a origem ou o destino como centro nao cria recarga nova: a
        origem ja e o tanque cheio e o destino e o fim."""
        a = [(0, True), (6, False), (10, True)]
        b = [(0, False), (6, False), (10, False)]
        assert alcance_minimo(a) == alcance_minimo(b) == 10

    def test_centro_no_meio_divide_o_trecho(self):
        marcos = [(0, False), (4, False), (9, True), (14, False), (16, False)]
        # trechos: 0 a 9 (9) e 9 a 16 (7)
        assert alcance_minimo(marcos) == 9

    def test_rota_que_ja_esta_no_destino_pede_tanque_de_1(self):
        """alcance tem que ser positivo (paradas levanta ValueError com 0)."""
        assert alcance_minimo([(0, False)]) == 1

    def test_marcos_vazio_e_erro(self):
        with pytest.raises(ValueError):
            alcance_minimo([])

    @pytest.mark.parametrize("seed", range(300))
    def test_e_a_fronteira_exata_do_guloso(self, seed):
        """Com o alcance minimo o guloso acha solucao; com um a menos, nao."""
        marcos = rota_sorteada(seed)
        minimo = alcance_minimo(marcos)
        assert paradas(marcos, minimo) is not None
        if minimo > 1:
            assert paradas(marcos, minimo - 1) is None

    @pytest.mark.parametrize("seed", range(300))
    def test_concorda_com_a_forca_bruta(self, seed):
        """Independente do guloso: nenhum subconjunto de paradas resolve abaixo
        do minimo, e algum resolve nele."""
        marcos = rota_sorteada(seed)
        minimo = alcance_minimo(marcos)
        assert paradas_forca_bruta(marcos, minimo) is not None
        if minimo > 1:
            assert paradas_forca_bruta(marcos, minimo - 1) is None


class TestTrechoCritico:
    def test_devolve_o_trecho_que_manda_no_minimo(self):
        marcos = [(0, False), (4, True), (13, False), (15, False)]
        # recargas: 0, 4, 15. trechos 4 e 11: o critico e o segundo.
        assert trecho_critico(marcos) == (1, 3, 11)

    def test_em_empate_fica_o_primeiro(self):
        assert trecho_critico(PLANO) == (0, 1, 8)

    def test_o_custo_do_trecho_e_o_alcance_minimo(self):
        for seed in range(100):
            marcos = rota_sorteada(seed)
            _, _, custo = trecho_critico(marcos)
            assert custo == alcance_minimo(marcos) or (custo == 0 and alcance_minimo(marcos) == 1)

    def test_indices_apontam_para_pontos_de_recarga(self):
        marcos = rota_sorteada(7)
        de, ate, _ = trecho_critico(marcos)
        assert de == 0 or marcos[de][1]
        assert ate == len(marcos) - 1 or marcos[ate][1]


class TestViabilidade:
    def test_tanque_folgado_tem_solucao(self):
        v = viabilidade(PLANO, 20)
        assert v["viavel"] is True
        assert v["alcance_minimo"] == 8
        assert v["folga"] == 12

    def test_tanque_no_limite_ainda_tem_solucao_com_folga_zero(self):
        v = viabilidade(PLANO, 8)
        assert v["viavel"] is True
        assert v["folga"] == 0

    def test_tanque_abaixo_do_minimo_nao_tem_solucao_e_diz_quanto_falta(self):
        v = viabilidade(PLANO, 7)
        assert v["viavel"] is False
        assert v["alcance_minimo"] == 8
        assert v["folga"] == -1

    def test_aponta_o_trecho_que_trava(self):
        v = viabilidade(PLANO, 5)
        assert v["trecho_critico"] == {"de": 0, "ate": 1, "custo": 8}

    def test_concorda_com_o_guloso(self):
        for seed in range(200):
            marcos = rota_sorteada(seed)
            for alcance in (3, 6, 12, 25):
                esperado = paradas(marcos, alcance) is not None
                assert viabilidade(marcos, alcance)["viavel"] is esperado

    def test_informa_o_minimo_de_paradas_quando_ha_solucao(self):
        assert viabilidade(PLANO, 20)["paradas_minimas"] == 2
        assert viabilidade(PLANO, 50)["paradas_minimas"] == 0

    def test_sem_solucao_nao_inventa_numero_de_paradas(self):
        assert viabilidade(PLANO, 5)["paradas_minimas"] is None

    def test_alcance_invalido_e_erro(self):
        with pytest.raises(ValueError):
            viabilidade(PLANO, 0)
