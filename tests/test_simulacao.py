"""A simulacao das paradas e o quadro da tese completo.

Rota de custo 50, centros em 8, 15, 22, 30, 38 e 45, tanque de 20.
"""
import random

import pytest

from greedy import ESTRATEGIAS, paradas, viavel
from greedy.estrategias import guloso, limiar, todo_centro
from greedy.forca_bruta import candidatos
from greedy.simulacao import simular

TESE = [(0, False), (8, True), (15, True), (22, True), (30, True),
        (38, True), (45, True), (50, False)]


class TestQuadroDaTese:
    def test_todo_centro_chega_com_seis_paradas_e_desperdica_muito(self):
        s = simular(TESE, 20, todo_centro(TESE, 20))
        assert (s.chegou, s.paradas) == (True, 6)
        # Sobra no tanque a cada recarga: 12, 13, 13, 12, 12, 13.
        assert s.energia_desperdicada == 75

    def test_limiar_25_chega_com_tres_paradas(self):
        s = simular(TESE, 20, limiar(25)(TESE, 20))
        assert (s.chegou, s.paradas, s.energia_desperdicada) == (True, 3, 15)

    def test_limiar_10_desmaia(self):
        # Passa pelo 15 com 5 no tanque e o 22 custa 7: desmaia no centro de
        # 15, o ultimo marco alcancado. No desenho do plano o tanque acaba no
        # 20, entre os dois centros.
        s = simular(TESE, 20, limiar(10)(TESE, 20))
        assert (s.chegou, s.paradas) == (False, 0)
        assert TESE[s.desmaio_em][0] == 15
        assert (s.energia_gasta, s.energia_final) == (15, 5)

    def test_guloso_chega_com_duas_paradas_e_desperdica_menos(self):
        s = simular(TESE, 20, guloso(TESE, 20))
        assert (s.chegou, s.paradas, s.energia_desperdicada) == (True, 2, 10)
        # Recarrega em 30 e os 20 que faltam esvaziam o tanque: chega com 0.
        assert (s.energia_gasta, s.energia_final) == (50, 0)


class TestRegras:
    def test_sem_paradas_e_rota_curta(self):
        s = simular([(0, False), (10, False)], 20, [])
        assert s == simular([(0, False), (10, False)], 20, ())
        assert (s.chegou, s.energia_final, s.desmaio_em) == (True, 10, None)

    def test_energia_exata_ainda_chega(self):
        assert simular([(0, False), (20, False)], 20, []).chegou

    def test_desmaio_no_primeiro_passo(self):
        s = simular([(0, False), (5, False)], 20, [], energia_inicial=4)
        assert (s.chegou, s.desmaio_em, s.energia_gasta) == (False, 0, 0)

    def test_parada_depois_do_desmaio_nao_conta(self):
        marcos = [(0, False), (25, True), (30, False)]
        s = simular(marcos, 20, [1])
        assert (s.chegou, s.paradas) == (False, 0)

    def test_parada_fora_do_contrato_e_erro(self):
        with pytest.raises(ValueError):
            simular(TESE, 20, [0])
        with pytest.raises(ValueError):
            simular(TESE, 20, [7])
        with pytest.raises(ValueError):
            simular([(0, False), (5, False), (9, False)], 20, [1])


def _rota(seed):
    rng = random.Random(seed)
    marcos, acumulado = [(0, False)], 0
    for _ in range(rng.randint(1, 30)):
        acumulado += rng.randint(1, 6)
        marcos.append((acumulado, rng.random() < 0.3))
    centros = candidatos(marcos)
    for i in centros[15:]:
        marcos[i] = (marcos[i][0], False)
    return marcos, max(6, round(acumulado * rng.uniform(0.15, 1.1)))


@pytest.mark.parametrize("seed", range(200))
def test_simulacao_concorda_com_o_verificador(seed):
    """Para qualquer estrategia, chegar na simulacao e o mesmo que a escolha
    ser viavel. Sao duas contas independentes da mesma regra."""
    marcos, alcance = _rota(seed)
    for estrategia in ESTRATEGIAS.values():
        escolhidas = estrategia(marcos, alcance)
        if escolhidas is None:
            continue
        assert simular(marcos, alcance, escolhidas).chegou == viavel(
            marcos, alcance, escolhidas)


@pytest.mark.parametrize("seed", range(200))
def test_quem_chega_nunca_para_menos_que_o_guloso(seed):
    marcos, alcance = _rota(seed)
    minimo = paradas(marcos, alcance)
    for nome, estrategia in ESTRATEGIAS.items():
        escolhidas = estrategia(marcos, alcance)
        if escolhidas is None:
            continue
        s = simular(marcos, alcance, escolhidas)
        if s.chegou:
            assert s.paradas >= len(minimo), nome
