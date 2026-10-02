"""O algoritmo do caminhoneiro: minimo de paradas de recarga sobre uma rota fixa.

Contexto. O Dijkstra do trabalho 1 ja entrega a rota mais barata da origem ao
destino. Aqui o treinador tem energia limitada (o "tanque") e o mapa tem
Centros Pokemon, onde a energia recarrega. A rota nao muda: o que se decide e
em quais centros parar pra chegar ao destino gastando o MINIMO de paradas.

Por que e guloso, e por que e otimo. Andar ate o centro mais distante que o
tanque ainda alcanca, e so entao parar, e a estrategia gulosa classica de
"gas station"/interval-cover. O argumento de otimalidade e greedy stays ahead:
qualquer solucao otima que pare antes do centro mais distante alcancavel pode
ter essa parada trocada pelo centro mais distante sem aumentar o numero de
paradas, e a partir dai o guloso cobre pelo menos tanto quanto a otima. A prova
por troca vai escrita no relatorio (fase 3/7); aqui fica o algoritmo e a
validacao contra forca bruta (fase 3).

Modelo do alcance (decisao 3, opcao A, batida pelo Lucas). `alcance` e a energia
maxima, o tamanho do tanque. Um trecho entre dois pontos de recarga consecutivos
(origem ou centro) e viavel quando o custo acumulado nele nao passa de `alcance`.
Recarregar num centro ENCHE o tanque; nao ha recarga parcial. Esse e o modelo do
desenho da tese (alcance 20, enche no centro), e e o que torna o problema um
guloso limpo.

As funcoes aqui sao puras: nao olham o grid nem o jogo, so listas de numeros.
Isso deixa o teste de forca bruta da fase 3 montar rotas a mao, sem simular
partida, e e a mesma separacao que graph/ fez entre algoritmo e mapa.
"""


def marcos_da_rota(caminho, mapa, estado):
    """Reduz uma rota do grafo a lista de marcos (custo_acumulado, e_centro).

    `caminho` e a lista de posicoes (r, c) que o Dijkstra/BFS/DFS devolve, com a
    origem na frente. `mapa` e o Grid e `estado` e o graph.state.Estado usado no
    custo (o mesmo par que pesou as arestas na busca).

    Cada marco carrega o custo ACUMULADO de energia desde a origem ate aquela
    posicao e se ela e um Centro Pokemon. A origem entra sempre, com custo 0: e
    o ponto de partida com o tanque cheio, e a funcao `paradas` conta com ele na
    frente. O custo de entrar na origem nao existe (o jogador ja esta la), igual
    ao _custo_do_caminho do graph.search, que so soma a partir do segundo no.

    Devolver todos os pontos como marco (nao so os centros) e a opcao A da
    decisao 2: mantem o guloso linear e o teste trivial de montar. `paradas` e
    quem ignora os pontos que nao sao centro.
    """
    import grid as grid_mod
    from graph.cost import custo_entrada

    marcos = []
    acumulado = 0
    for i, (r, c) in enumerate(caminho):
        celula = mapa.celula(r, c)
        if i > 0:
            acumulado += custo_entrada(celula, estado)
        e_centro = celula.occupied_with == grid_mod.CENTRO
        marcos.append((acumulado, e_centro))
    return marcos


def paradas(marcos, alcance, energia_inicial=None):
    """Minimo de paradas de recarga sobre uma rota ja escolhida.

    Entrada:
      marcos   lista de (custo_acumulado, e_centro), ordenada pela rota, com a
               origem em marcos[0] (custo 0). O ultimo marco e o destino.
      alcance  energia maxima (tamanho do tanque). alcance > 0.
      energia_inicial
               quanto ha no tanque na origem, de 0 a `alcance`. None e tanque
               cheio. O bot precisa disso: cada objetivo comeca com o que
               sobrou do anterior, nao com o tanque cheio.

    Saida:
      lista dos INDICES (em `marcos`) dos centros onde parou, na ordem da rota
      (opcao A da decisao 1). Lista vazia quando a rota inteira cabe num tanque,
      ou seja zero paradas. `None` quando nenhuma escolha de paradas leva ao
      destino: algum trecho entre pontos de recarga consecutivos passa do
      alcance, e nem parar em todo centro possivel resolve.

    O algoritmo. Mantem `base`, o custo acumulado do ultimo ponto onde o tanque
    encheu (origem ou ultima parada). Varre os marcos pra frente procurando o
    centro mais distante ainda dentro de `base + alcance`; para nele, atualiza a
    base e continua dali. Se antes de achar destino ou um proximo centro
    alcancavel um marco ja estoura o alcance, nao ha como avancar: retorna None.

    Tanque parcial na origem e o mesmo problema com a base recuada: comecar
    com `energia_inicial` e como ter enchido o tanque `alcance -
    energia_inicial` antes da origem. So o primeiro trecho muda, e a prova de
    otimalidade nao depende de onde a base comeca.

    Complexidade O(n): cada marco e visitado no maximo duas vezes (uma
    procurando parada, uma depois de recarregar), porque a base so anda pra
    frente.
    """
    if alcance <= 0:
        raise ValueError("alcance deve ser positivo")
    if not marcos:
        raise ValueError("marcos vazio: a rota precisa ter ao menos a origem")
    if energia_inicial is None:
        energia_inicial = alcance
    if not 0 <= energia_inicial <= alcance:
        raise ValueError("energia_inicial deve estar entre 0 e alcance")

    destino_idx = len(marcos) - 1
    custo_destino = marcos[destino_idx][0]

    # Onde o tanque "encheu" pela ultima vez. Com tanque cheio e a origem;
    # com tanque parcial, um ponto virtual antes dela.
    base = marcos[0][0] - (alcance - energia_inicial)
    escolhidas = []
    i = 1

    while True:
        # Ja alcanca o destino a partir da base atual? Fim.
        if custo_destino - base <= alcance:
            return escolhidas

        # Procura o centro mais distante dentro do alcance a partir da base.
        melhor_centro = None
        j = i
        while j < destino_idx:
            custo_j, e_centro = marcos[j]
            if custo_j - base > alcance:
                break  # daqui pra frente tudo esta fora do alcance
            if e_centro:
                melhor_centro = j
            j += 1

        # Nenhum centro alcancavel e o destino tambem nao (checado acima):
        # o proximo ponto obrigatorio esta longe demais. Rota inviavel.
        if melhor_centro is None:
            return None

        escolhidas.append(melhor_centro)
        base = marcos[melhor_centro][0]
        i = melhor_centro + 1
