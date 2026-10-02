"""Referencia por forca bruta para o caminhoneiro.

Serve de oraculo: testa todos os subconjuntos de centros, do menor pro maior,
e devolve o primeiro que leva ao destino. Nao assume nada sobre a estrutura do
problema, entao concordar com ele e evidencia independente de que o guloso e
otimo. E exponencial no numero de centros (2^k), por isso so roda em rotas
pequenas: nos testes da fase 3 e como estrategia "otimo" da fase 4.

Mesmo contrato de greedy.caminhoneiro.paradas: indices em `marcos`, origem e
destino nunca sao parada, None quando nao ha solucao.
"""
from itertools import combinations


def viavel(marcos, alcance, escolhidas, energia_inicial=None):
    """As paradas `escolhidas` levam da origem ao destino sem estourar o tanque?

    Verificador independente do guloso: so olha os trechos entre pontos de
    recarga consecutivos (origem, cada parada, destino) e confere que nenhum
    passa do que ha no tanque: `energia_inicial` no primeiro trecho (None e
    tanque cheio) e `alcance` nos outros. Exige paradas em centros, em ordem
    estritamente crescente e fora da origem e do destino.
    """
    destino_idx = len(marcos) - 1
    anterior = 0
    tanque = alcance if energia_inicial is None else energia_inicial
    for i in escolhidas:
        if not (anterior < i < destino_idx) or not marcos[i][1]:
            return False
        if marcos[i][0] - marcos[anterior][0] > tanque:
            return False
        anterior = i
        tanque = alcance
    return marcos[destino_idx][0] - marcos[anterior][0] <= tanque


def candidatos(marcos):
    """Indices que podem virar parada: centros fora da origem e do destino."""
    return [i for i in range(1, len(marcos) - 1) if marcos[i][1]]


def solucoes_otimas(marcos, alcance, energia_inicial=None):
    """Todas as escolhas de paradas de tamanho minimo, ou [] se nao ha nenhuma.

    Os testes usam a lista inteira (e nao so uma otima) pra conferir o
    invariante da prova, de que o guloso fica a frente de QUALQUER otima.
    """
    if alcance <= 0:
        raise ValueError("alcance deve ser positivo")
    if not marcos:
        raise ValueError("marcos vazio: a rota precisa ter ao menos a origem")
    if energia_inicial is not None and not 0 <= energia_inicial <= alcance:
        raise ValueError("energia_inicial deve estar entre 0 e alcance")

    centros = candidatos(marcos)
    for k in range(len(centros) + 1):
        otimas = [list(c) for c in combinations(centros, k)
                  if viavel(marcos, alcance, c, energia_inicial)]
        if otimas:
            return otimas
    return []


def paradas_forca_bruta(marcos, alcance, energia_inicial=None):
    """Uma escolha de paradas de tamanho minimo, ou None se nao ha solucao."""
    otimas = solucoes_otimas(marcos, alcance, energia_inicial)
    return otimas[0] if otimas else None
