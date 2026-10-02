"""O oraculo de forca bruta, testado antes de ser usado como juiz do guloso.

Se o oraculo errasse, o teste de otimalidade passaria por acidente. Por isso
os casos aqui tem resposta conhecida a mao e nao passam pelo guloso.
"""
import pytest

from greedy.forca_bruta import (candidatos, paradas_forca_bruta,
                                solucoes_otimas, viavel)


TESE = [(0, False), (8, True), (15, True), (22, True), (30, True),
        (38, True), (45, True), (50, False)]


class TestViavel:
    def test_paradas_do_desenho_da_tese_sao_viaveis(self):
        assert viavel(TESE, 20, [2, 4])

    def test_sem_paradas_quando_tudo_cabe(self):
        assert viavel(TESE, 50, [])
        assert not viavel(TESE, 49, [])

    def test_trecho_longo_entre_paradas(self):
        # 8 -> 30 (22) estoura o alcance 20.
        assert not viavel(TESE, 20, [1, 4])

    def test_rejeita_parada_que_nao_e_centro(self):
        marcos = [(0, False), (10, False), (20, False)]
        assert not viavel(marcos, 15, [1])

    def test_rejeita_origem_destino_e_ordem_errada(self):
        assert not viavel(TESE, 20, [0, 2, 4])
        assert not viavel(TESE, 20, [2, 4, 7])
        assert not viavel(TESE, 20, [4, 2])
        assert not viavel(TESE, 20, [2, 2, 4])


def test_candidatos_excluem_origem_e_destino():
    marcos = [(0, True), (5, True), (9, False), (12, True)]
    assert candidatos(marcos) == [1]


class TestForcaBruta:
    def test_minimo_do_desenho_da_tese_e_2(self):
        # Conta a mao: a 1a parada tem que estar em <= 20 (8 ou 15) e a 2a em
        # >= 30 pra o destino caber. Partindo de 8 o tanque so vai ate 28, sem
        # centro >= 30. Sobra uma unica otima: 15 e 30.
        assert solucoes_otimas(TESE, 20) == [[2, 4]]
        assert paradas_forca_bruta(TESE, 20) == [2, 4]

    def test_varias_otimas_empatadas(self):
        # Centros em 10, 12 e 14, destino em 25, alcance 15: qualquer um dos
        # tres sozinho resolve.
        marcos = [(0, False), (10, True), (12, True), (14, True), (25, False)]
        assert solucoes_otimas(marcos, 15) == [[1], [2], [3]]

    def test_zero_paradas(self):
        assert paradas_forca_bruta(TESE, 50) == []

    def test_sem_solucao(self):
        marcos = [(0, False), (30, True), (60, False)]
        assert solucoes_otimas(marcos, 20) == []
        assert paradas_forca_bruta(marcos, 20) is None

    def test_parada_unica_forcada(self):
        marcos = [(0, False), (20, True), (40, False)]
        assert solucoes_otimas(marcos, 20) == [[1]]

    def test_erros_iguais_ao_guloso(self):
        with pytest.raises(ValueError):
            paradas_forca_bruta(TESE, 0)
        with pytest.raises(ValueError):
            paradas_forca_bruta([], 10)


class TestTanqueParcial:
    def test_viavel_cobra_o_primeiro_trecho_com_a_energia_inicial(self):
        marcos = [(0, False), (10, True), (25, False)]
        assert viavel(marcos, 20, [1], energia_inicial=10)
        assert not viavel(marcos, 20, [1], energia_inicial=9)

    def test_depois_da_parada_o_tanque_esta_cheio(self):
        # 10 no tanque ate o centro em 10; dali, 20 cobre ate o destino em 30.
        marcos = [(0, False), (10, True), (30, False)]
        assert viavel(marcos, 20, [1], energia_inicial=10)

    def test_sem_parada_vale_a_energia_inicial(self):
        marcos = [(0, False), (10, True), (15, False)]
        assert viavel(marcos, 20, [], energia_inicial=15)
        assert not viavel(marcos, 20, [], energia_inicial=14)
        assert solucoes_otimas(marcos, 20, energia_inicial=14) == [[1]]

    def test_energia_fora_da_faixa_e_erro(self):
        with pytest.raises(ValueError):
            solucoes_otimas(TESE, 20, energia_inicial=21)
