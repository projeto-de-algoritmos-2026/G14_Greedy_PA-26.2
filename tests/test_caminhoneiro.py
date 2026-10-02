"""O algoritmo do caminhoneiro, testado sem mapa.

A fase 2 trouxe o exemplo canonico do plano (o desenho da tese) e os contratos
de retorno; a fase 3 acrescenta os casos de borda. A comparacao com a forca
bruta fica em test_caminhoneiro_otimalidade.py.
"""
import pytest

from greedy import paradas


# O quadro do plano: rota de custo 0 a 50, centros em 8, 15, 22, 30, 38, 45,
# alcance 20. O guloso para em 15 e 30 (2 paradas). Montado a mao: os marcos
# sao (custo_acumulado, e_centro), origem em custo 0 e destino em custo 50.
CUSTOS_CENTROS = [8, 15, 22, 30, 38, 45]


def _marcos_do_exemplo():
    pontos = [(0, False)]  # origem
    pontos += [(c, True) for c in CUSTOS_CENTROS]
    pontos.append((50, False))  # destino
    pontos.sort()
    return pontos


def test_exemplo_da_tese_para_em_15_e_30():
    marcos = _marcos_do_exemplo()
    indices = paradas(marcos, alcance=20)
    # Traduz os indices escolhidos de volta pra custos, pra o assert falar a
    # lingua do desenho e nao depender da posicao na lista.
    custos_parada = [marcos[i][0] for i in indices]
    assert custos_parada == [15, 30]


def test_rota_inteira_no_tanque_da_zero_paradas():
    marcos = _marcos_do_exemplo()
    # Alcance folgado cobre os 50 de uma vez.
    assert paradas(marcos, alcance=100) == []


def test_trecho_maior_que_o_alcance_nao_tem_solucao():
    # Origem, um centro em 30, destino em 60, alcance 20: o primeiro trecho
    # (0 -> 30) ja passa do alcance e nao ha centro antes dele.
    marcos = [(0, False), (30, True), (60, False)]
    assert paradas(marcos, alcance=20) is None


def test_alcance_nao_positivo_e_erro():
    with pytest.raises(ValueError):
        paradas([(0, False), (10, False)], alcance=0)


# Casos de borda (fase 3). Cada um fixa uma fronteira do contrato: onde o <=
# vira <, onde a origem e o destino deixam de ser candidatos a parada, e onde
# o guloso tem que ignorar o que nao e centro.


class TestCasosDeBorda:
    def test_destino_exatamente_no_alcance_nao_precisa_parar(self):
        # O alcance fecha o intervalo: chegar com o tanque zerado e chegar.
        assert paradas([(0, False), (10, True), (20, False)], alcance=20) == []

    def test_destino_um_alem_do_alcance_obriga_a_parar(self):
        assert paradas([(0, False), (10, True), (21, False)], alcance=20) == [1]

    def test_centro_exatamente_no_limite_e_alcancavel(self):
        marcos = [(0, False), (20, True), (40, False)]
        assert paradas(marcos, alcance=20) == [1]

    def test_centro_um_alem_do_limite_torna_a_rota_inviavel(self):
        marcos = [(0, False), (20, True), (40, False)]
        assert paradas(marcos, alcance=19) is None

    def test_trecho_impossivel_no_meio_da_rota(self):
        # O primeiro trecho cabe, mas 10 -> 35 (25) passa do alcance e nao ha
        # centro entre eles: parar em todo centro tambem nao resolveria.
        marcos = [(0, False), (10, True), (35, True), (50, False)]
        assert paradas(marcos, alcance=20) is None

    def test_trecho_impossivel_no_fim_da_rota(self):
        marcos = [(0, False), (15, True), (40, False)]
        assert paradas(marcos, alcance=20) is None

    def test_centro_na_origem_nao_conta_como_parada(self):
        # Parar na origem e inutil: o tanque ja comeca cheio. O guloso nunca
        # devolve o indice 0, e a rota so e viavel se o resto dela for.
        assert paradas([(0, True), (15, False), (30, False)], alcance=20) is None
        assert paradas([(0, True), (10, True), (25, False)], alcance=20) == [1]

    def test_centro_no_destino_nao_conta_como_parada(self):
        # Chegou, acabou: recarregar no destino nao e parada da viagem.
        assert paradas([(0, False), (10, True), (30, True)], alcance=20) == [1]

    def test_rota_so_com_a_origem(self):
        # Origem == destino: nada a percorrer, zero paradas.
        assert paradas([(0, False)], alcance=5) == []

    def test_marcos_vazio_e_erro(self):
        with pytest.raises(ValueError):
            paradas([], alcance=10)

    def test_alcance_negativo_e_erro(self):
        with pytest.raises(ValueError):
            paradas([(0, False), (10, False)], alcance=-1)

    def test_passa_direto_pelos_centros_mais_proximos(self):
        # Centros em 5, 10 e 18, alcance 20: so o de 18 interessa.
        marcos = [(0, False), (5, True), (10, True), (18, True), (30, False)]
        assert paradas(marcos, alcance=20) == [3]

    def test_ponto_que_nao_e_centro_nunca_vira_parada(self):
        # O ponto mais distante dentro do alcance e celula comum (19); o guloso
        # tem que voltar ao centro mais distante (12), nao ao ponto.
        marcos = [(0, False), (6, False), (12, True), (19, False), (30, False)]
        assert paradas(marcos, alcance=20) == [2]

    def test_sem_nenhum_centro_e_rota_longa(self):
        marcos = [(0, False), (8, False), (16, False), (24, False)]
        assert paradas(marcos, alcance=20) is None

    def test_parada_obrigatoria_em_todo_centro(self):
        # Centros espacados exatamente de 20 em 20: nao ha escolha, o minimo e
        # parar em todos. O guloso nao pode pular nenhum.
        marcos = [(0, False), (20, True), (40, True), (60, True), (80, False)]
        assert paradas(marcos, alcance=20) == [1, 2, 3]

    def test_indices_crescentes_e_todos_centros(self):
        marcos = [(0, False)]
        marcos += [(c, c % 3 == 0) for c in range(1, 100)]
        marcos.append((100, False))
        escolhidas = paradas(marcos, alcance=10)
        assert escolhidas == sorted(escolhidas)
        assert all(marcos[i][1] for i in escolhidas)
        assert 0 not in escolhidas and len(marcos) - 1 not in escolhidas


class TestTanqueParcial:
    """O bot comeca cada rota com o que sobrou da anterior, nao cheio."""

    def test_tanque_cheio_e_o_padrao(self):
        marcos = [(0, False), (15, True), (30, True), (50, False)]
        assert paradas(marcos, 20, energia_inicial=20) == paradas(marcos, 20)

    def test_pouca_energia_obriga_a_parar_mais_cedo(self):
        # Cheio, para so em 15 e 30. Com 10 no tanque, o 15 nao e alcancavel e
        # sobra o centro de 8.
        marcos = _marcos_do_exemplo()
        custos = [marcos[i][0] for i in paradas(marcos, 20, energia_inicial=10)]
        assert custos == [8, 22, 38]

    def test_energia_exata_para_o_primeiro_centro(self):
        marcos = [(0, False), (10, True), (25, False)]
        assert paradas(marcos, 20, energia_inicial=10) == [1]
        assert paradas(marcos, 20, energia_inicial=9) is None

    def test_tanque_vazio_so_chega_se_ja_estiver_no_destino(self):
        assert paradas([(0, False)], 20, energia_inicial=0) == []
        assert paradas([(0, False), (1, True), (5, False)], 20,
                       energia_inicial=0) is None

    def test_energia_fora_da_faixa_e_erro(self):
        with pytest.raises(ValueError):
            paradas([(0, False), (10, False)], 20, energia_inicial=21)
        with pytest.raises(ValueError):
            paradas([(0, False), (10, False)], 20, energia_inicial=-1)
