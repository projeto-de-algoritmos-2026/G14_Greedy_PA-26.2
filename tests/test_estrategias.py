"""As estrategias rivais, comparadas no desenho da tese.

Rota de custo 50, centros em 8, 15, 22, 30, 38 e 45, tanque de 20. O quadro
do plano diz: todo centro para 6 vezes, limiar 25% para 3, limiar 10% nao
para nenhuma (e desmaia), guloso e otimo param 2.
"""
import pytest

from greedy.estrategias import (ESTRATEGIAS, MAX_CENTROS_OTIMO, guloso,
                                limiar, otimo, todo_centro)

TESE = [(0, False), (8, True), (15, True), (22, True), (30, True),
        (38, True), (45, True), (50, False)]


def _custos(indices):
    return [TESE[i][0] for i in indices]


class TestQuadroDaTese:
    def test_todo_centro_para_seis_vezes(self):
        assert _custos(todo_centro(TESE, 20)) == [8, 15, 22, 30, 38, 45]

    def test_limiar_25_para_tres_vezes(self):
        # Em 15 sobram 5 de 20, exatamente 25%: para. O mesmo em 30 e 45.
        assert _custos(limiar(25)(TESE, 20)) == [15, 30, 45]

    def test_limiar_10_nao_para_nunca(self):
        # Em 15 sobram 5 (25%), acima do limiar; o proximo centro, em 22, ja
        # esta fora do tanque. Nao para em lugar nenhum: desmaia no caminho.
        assert limiar(10)(TESE, 20) == []

    def test_limiar_50_empata_com_o_25_nesta_rota(self):
        # A energia salta de 12 (60%) direto pra 5 (25%) entre dois centros:
        # nenhum centro cai entre 25% e 50%, e os dois limiares param igual.
        assert _custos(limiar(50)(TESE, 20)) == [15, 30, 45]

    def test_guloso_e_otimo_param_duas_vezes(self):
        assert _custos(guloso(TESE, 20)) == [15, 30]
        assert _custos(otimo(TESE, 20)) == [15, 30]


class TestLimiar:
    def test_limiar_respeita_o_tanque_parcial(self):
        # Comecando com 12, em 8 sobram 4 (20%): o limiar 25% ja para ali.
        assert _custos(limiar(25)(TESE, 20, energia_inicial=12))[0] == 8

    def test_nunca_para_na_origem_nem_no_destino(self):
        marcos = [(0, True), (18, False), (20, True)]
        assert limiar(50)(marcos, 20) == []

    def test_pct_fora_da_faixa_e_erro(self):
        with pytest.raises(ValueError):
            limiar(0)
        with pytest.raises(ValueError):
            limiar(100)

    def test_nome_mostra_o_limiar(self):
        assert limiar(25).__name__ == "limiar_25"


class TestOtimo:
    def test_sem_solucao_devolve_none(self):
        assert otimo([(0, False), (30, True), (60, False)], 20) is None

    def test_recusa_rota_com_centros_demais(self):
        n = MAX_CENTROS_OTIMO + 1
        marcos = [(0, False)] + [(i, True) for i in range(1, n + 1)]
        marcos.append((n + 1, False))
        with pytest.raises(ValueError):
            otimo(marcos, 5)


def test_todas_tem_a_mesma_assinatura():
    for nome, estrategia in ESTRATEGIAS.items():
        resultado = estrategia(TESE, 20, None)
        assert resultado is None or all(TESE[i][1] for i in resultado), nome


def test_registro_tem_as_seis_estrategias():
    assert set(ESTRATEGIAS) == {"guloso", "todo_centro", "limiar_10",
                                "limiar_25", "limiar_50", "otimo"}
