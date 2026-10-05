"""Alcance minimo e viabilidade de uma rota (fase 6).

O jogador escolhe o tamanho do tanque na interface, e a tela precisa dizer na
hora se aquela escolha tem solucao. A resposta ja existe no caminhoneiro:
`paradas` devolve None quando algum trecho entre pontos de recarga consecutivos
passa do alcance. Aqui essa condicao vira um numero, o ALCANCE MINIMO: o menor
tanque com o qual existe alguma escolha de paradas que chega ao destino.

Como se calcula. Os pontos de recarga sao a origem, cada Centro e o destino
(que fecha o ultimo trecho). Parar em TODO Centro e a escolha mais permissiva,
porque recarregar enche o tanque: nunca atrapalha. Logo o maior trecho entre
dois pontos de recarga consecutivos e um limite exato. Com um tanque menor que
ele, nenhuma escolha de paradas resolve; com ele (ou mais), o guloso resolve.
Os testes confirmam as duas metades contra o guloso e contra a forca bruta.

Vale pro tanque cheio na origem, o estado de uma partida nova. Em meio a uma
partida o tanque pode estar parcial; ai a pergunta e `paradas(marcos, alcance,
energia_inicial)`, que esta no caminhoneiro e nao aqui.

Funcoes puras: so listas de marcos (custo_acumulado, e_centro), como as de
greedy.caminhoneiro.
"""
from .caminhoneiro import paradas


def _pontos_de_recarga(marcos):
    """Origem, cada Centro entre a origem e o destino, e o destino."""
    ultimo = len(marcos) - 1
    centros = [i for i in range(1, ultimo) if marcos[i][1]]
    return [0, *centros, ultimo] if ultimo > 0 else [0]


def trecho_critico(marcos):
    """O trecho entre recargas consecutivas que manda no alcance minimo.

    Devolve (de, ate, custo): indices em `marcos` dos dois pontos e a energia
    que o trecho gasta. Em empate fica o primeiro da rota. E o que a tela
    aponta quando o tanque nao basta ("o problema esta entre aqui e aqui").
    """
    if not marcos:
        raise ValueError("marcos vazio: a rota precisa ter ao menos a origem")
    pontos = _pontos_de_recarga(marcos)
    if len(pontos) == 1:
        return (0, 0, 0)
    melhor = (pontos[0], pontos[1], marcos[pontos[1]][0] - marcos[pontos[0]][0])
    for a, b in zip(pontos[1:], pontos[2:]):
        custo = marcos[b][0] - marcos[a][0]
        if custo > melhor[2]:
            melhor = (a, b, custo)
    return melhor


def alcance_minimo(marcos):
    """Menor tanque (inteiro, pelo menos 1) com o qual a rota tem solucao."""
    return max(1, trecho_critico(marcos)[2])


def viabilidade(marcos, alcance):
    """Diz se `alcance` resolve a rota e, se nao, o que falta.

    Devolve um dicionario pronto pra virar JSON:
      viavel           existe alguma escolha de paradas que chega ao destino
      alcance          o que foi perguntado
      alcance_minimo   o menor tanque que resolveria
      folga            alcance - alcance_minimo (negativo = quanto falta)
      trecho_critico   {de, ate, custo}: onde a rota trava
      paradas_minimas  o minimo de paradas com esse tanque, None se nao ha solucao
    """
    if alcance <= 0:
        raise ValueError("alcance deve ser positivo")
    de, ate, custo = trecho_critico(marcos)
    minimo = max(1, custo)
    escolhidas = paradas(marcos, alcance)
    return {
        "viavel": escolhidas is not None,
        "alcance": alcance,
        "alcance_minimo": minimo,
        "folga": alcance - minimo,
        "trecho_critico": {"de": de, "ate": ate, "custo": custo},
        "paradas_minimas": None if escolhidas is None else len(escolhidas),
    }
