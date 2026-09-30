"""Teste de fumaca da fase 2: o algoritmo do caminhoneiro.

So o exemplo canonico do plano (o desenho da tese) e os contratos de retorno.
Forca bruta, prova de otimalidade e casos de borda completos sao a fase 3.
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
