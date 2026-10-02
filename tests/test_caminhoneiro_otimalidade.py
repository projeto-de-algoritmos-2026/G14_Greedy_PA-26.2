"""O guloso contra a forca bruta em rotas sorteadas (fase 3).

E o teste que sustenta a apresentacao: em centenas de rotas pequenas o guloso
para exatamente tantas vezes quanto o minimo achado testando todos os
subconjuntos de centros.

As rotas sao listas de marcos montadas a mao, sem mapa: o custo de cada passo
sai de 1 a 6, a mesma faixa dos pesos do trabalho 1 (concreto a grama ferida).
"""
import random

import pytest

from greedy import paradas, viavel
from greedy.forca_bruta import candidatos, solucoes_otimas

ROTAS = 400
MAX_CENTROS = 15


def rota_sorteada(seed):
    """Marcos e alcance de uma rota aleatoria, reproduzivel pela seed.

    A densidade de centros e o alcance tambem sao sorteados, pra cobrir desde
    rota sem solucao ate rota que cabe inteira no tanque.
    """
    rng = random.Random(seed)
    passos = rng.randint(1, 40)
    densidade = rng.choice([0.15, 0.3, 0.5, 0.8])
    marcos = [(0, rng.random() < densidade)]
    acumulado = 0
    for _ in range(passos):
        acumulado += rng.randint(1, 6)
        marcos.append((acumulado, rng.random() < densidade))
    # Limita o numero de candidatos pra forca bruta (2^k) caber no teste. O
    # corte e sorteado, e nao o fim da rota, pra nao criar trecho vazio no fim.
    centros = candidatos(marcos)
    if len(centros) > MAX_CENTROS:
        for i in rng.sample(centros, len(centros) - MAX_CENTROS):
            marcos[i] = (marcos[i][0], False)
    # O alcance e proporcional ao tamanho da rota: de um tanque pequeno, que
    # obriga varias paradas, ate um que cobre a rota inteira.
    alcance = max(6, round(acumulado * rng.uniform(0.15, 1.1)))
    return marcos, alcance


@pytest.mark.parametrize("seed", range(ROTAS))
def test_guloso_para_o_minimo_de_vezes(seed):
    marcos, alcance = rota_sorteada(seed)
    guloso = paradas(marcos, alcance)
    otimas = solucoes_otimas(marcos, alcance)

    if not otimas:
        assert guloso is None
        return

    assert guloso is not None
    assert viavel(marcos, alcance, guloso)
    assert len(guloso) == len(otimas[0])


def test_sorteio_cobre_os_tres_desfechos():
    """Sem isso o teste acima poderia passar so com rotas triviais."""
    zero = com_paradas = sem_solucao = 0
    for seed in range(ROTAS):
        resultado = paradas(*rota_sorteada(seed))
        if resultado is None:
            sem_solucao += 1
        elif resultado:
            com_paradas += 1
        else:
            zero += 1
    assert min(zero, com_paradas, sem_solucao) >= ROTAS // 20
