# Relatório final: Pokémon CLI, o Caminhoneiro

**Disciplina:** Projeto e Análise de Algoritmos (FGA0124), UnB/FGA
**Grupo 14** | Módulo 2: Algoritmos Ambiciosos (Greedy)

| Matrícula | Aluno | Fases |
| --- | --- | --- |
| 190091681 | Lucas Gabriel Antunes | 0, 1, 2, 6 |
| 202045965 | Augusto Campos Duarte | 3, 4, 5 |

A fase 7 (README, relatório e vídeo) é entrega conjunta; quem fecha cada peça
é a confirmar.

## 1. Introdução

O Trabalho 1 já entregava a rota mais barata entre dois pontos de um jogo de
Pokémon de terminal: o Dijkstra sobre um grafo cujos pesos dependem do estado
do jogador. O Trabalho 2 empilha uma segunda otimização sobre essa rota. Agora
o treinador tem energia limitada, um tanque, e o mapa ganha Centros Pokémon
onde a energia recarrega. A rota não muda; o que se decide é em quais centros
parar para chegar ao destino gastando o mínimo de paradas. É o problema
clássico do posto de gasolina, e é guloso.

A tese que organiza o trabalho inteiro cabe em uma frase: parar tarde não é
parar pouco. A regra intuitiva de um jogador humano, parar sempre que a
energia fica baixa, ou para vezes demais ou desmaia no meio do caminho, e o
guloso que só para no centro mais distante que ainda alcança é ótimo no número
de paradas. Essa afirmação não fica só no papel: ela é provada por extenso na
seção 4, confrontada contra um oráculo de força bruta em centenas de rotas, e
medida num benchmark sobre as rotas do Trabalho 1. A seção 8 mostra o limite dessa afirmação: ela vale sobre os custos fixos de uma rota, e o jogo com batalha aleatória é mais duro.

O relatório segue a ordem das fases. A seção 2 descreve a arquitetura que
mantém o guloso como função pura sobre listas de números, sem mapa e sem jogo.
A seção 3 cobre a modelagem da energia e do Centro (fase 1). A seção 4
apresenta o algoritmo e a prova de otimalidade (fases 2 e 3). A seção 5 trata
das estratégias rivais e do bot (fase 4), e a 6 do benchmark de paradas (fase
5). A seção 7 descreve a interface e a viabilidade do tanque (fase 6). A seção
8 reúne as limitações sem suavizar nenhuma, e a 9 fecha com a conclusão e as
extensões em aberto.

## 2. Arquitetura: o guloso como função pura

O código do caminhoneiro vive em `greedy/` e não conhece o jogo nem o mapa.
Ele opera sobre listas de marcos, pares de `(custo_acumulado, é_centro)`, e
nada mais. Essa é a mesma separação que o Trabalho 1 fez entre a camada de
grafo e o jogo: lá os algoritmos de busca enxergavam só `vizinhos()` e
`arestas()`, aqui as funções de parada enxergam só uma lista de números
ordenada pela rota. O ganho é o mesmo nos dois trabalhos: os testes montam
rotas à mão, sem simular partida, e o oráculo de força bruta da fase 3
confronta o guloso em rotas sintéticas que nunca precisaram de um `Grid`.

A energia é um atributo próprio do `Player`, não um subproduto do HP. O
`Estado` que pesa as arestas (o `dataclass` congelado herdado do Trabalho 1)
passou a carregar também `energia` e `energia_max`, opcionais, mas o custo não
lê nenhum dos dois: o custo de uma aresta continua sendo função pura do HP, do
Surf e do terreno, e a energia é consumida pelo passo, não precificada por ele. Quem converte a rota do grafo numa lista de marcos é
`marcos_da_rota(caminho, mapa, estado)`, que soma o `custo_entrada` de cada
célula a partir da segunda (a origem entra com custo zero, porque o jogador já
está nela, igual ao `_custo_do_caminho` do Trabalho 1 que só soma a partir do
segundo nó). O custo acumulado do último marco é, por construção, o mesmo
custo total que o Dijkstra calculou.

## 3. Modelagem da energia e do Centro (fase 1, Lucas Gabriel Antunes)

### 3.1 Energia não é HP

A primeira decisão de modelagem foi separar energia de HP, e ela não é
estética. O HP cai em batalha aleatória, e no Trabalho 1 o próprio HP já
encarece a grama: com o líder ferido, o custo de atravessar grama sobe de 3
para até 6, pela fórmula de `custo_grama` em `graph/cost.py`. O caminhoneiro
só é ótimo quando o consumo de cada trecho é conhecido antes de sair, porque é
isso que permite o guloso decidir o centro mais distante alcançável sem
surpresa pelo caminho. Amarrar a energia ao HP introduziria consumo que muda
no meio da rota, por sorteio de batalha, e quebraria a premissa do algoritmo.
Por isso a energia virou atributo independente do `Player`.

### 3.2 O consumo é o peso do Trabalho 1

Cada passo gasta de energia exatamente o peso que o grafo do Trabalho 1 dá à
aresta. Entrar numa célula consome `custo_entrada(celula, estado)`, calculado
com o estado de antes do passo e incluindo a penalidade de batalha (8 para
Pokémon selvagem, 12 para treinador). É o mesmo número que o Dijkstra usou
para planejar a rota, o que mantém as duas otimizações coerentes: o Dijkstra
minimiza a soma desses pesos, e o guloso conta paradas sobre a mesma soma.
Cada `Movimento` guarda as duas parcelas separadas, `custo_terreno` e
`custo_conteudo`, para a interface explicar a conta na tela (`-9 = 1 de
concreto + 8 de batalha`) sem recalcular nada.

### 3.3 Centro é prédio, não item

O Centro Pokémon é modelado como prédio, não como item coletável. Não some
quando pisado, e passar por cima dele não recarrega sozinho: recarregar é uma
ação separada, `game.recarregar`, e na tela de jogo humano exige apertar `R`
em cima do centro. A razão é direta: passar por um centro sem parar é
justamente a escolha que o guloso toma quando o tanque ainda alcança o próximo
centro. Se pisar recarregasse automaticamente, a estratégia `todo_centro`
viraria a única possível e a tese desapareceria.

Sem energia para o próximo passo, o treinador desmaia onde está. A partida
termina com o motivo `sem energia`, que conta como derrota, do mesmo jeito que
o time esvaziado em batalha. A regra de energia é opcional: energia `None`
desliga tudo, e o jogo, o bot e o benchmark do Trabalho 1 voltam a funcionar
como antes.

### 3.4 Os mapas do Trabalho 1 ficaram intactos

Juntar as duas fases não podia reescrever o mapa do Trabalho 1, senão os
números de lá deixariam de valer. Os centros são sorteados depois do mapa
inteiro gerado, só em células livres fora da água e da origem. A medição em 90
mapas (tamanhos 8, 15 e 30, com 30 seeds cada) confirmou que nenhuma célula
mudou além das que viraram centro, e que nenhuma distância do Dijkstra mudou.

A densidade de centros começou em 4% e subiu para 8%, mudança registrada no commit `1055fa3`. Com 4%, a mediana de centros na
rota era zero nos mapas 8x8 e 15x15, e numa rota sem centro toda estratégia de
parada empata: ninguém tem onde parar. A 8% o problema passa a ter substância
na maioria das rotas. O contrato de leitura do benchmark confirma que a
mudança de 4% para 8% não altera o Trabalho 1: rodando o benchmark de rotas (tamanhos 8 e 15, 10 seeds) com as duas densidades, as 288 linhas saíram idênticas, descontado o tempo.

## 4. O algoritmo e a prova (fase 2, Lucas; fase 3, Augusto)

### 4.1 O algoritmo

A função `paradas(marcos, alcance, energia_inicial=None)` decide onde parar.
Ela mantém uma `base`, o custo acumulado do último ponto onde o tanque encheu
(a origem, ou a última parada). A cada passo, varre os marcos para a frente
procurando o centro mais distante ainda dentro de `base + alcance`, para nele,
atualiza a base e segue dali. Termina quando o destino cabe no tanque a partir
da base atual, devolvendo a lista de índices dos centros escolhidos. Lista
vazia significa que a rota inteira coube num tanque, zero paradas. `None`
significa rota inviável: algum trecho entre pontos de recarga consecutivos
passa do alcance, e nem parar em todo centro resolve.

A complexidade é O(n) no número de marcos, porque a base só anda para a frente
e cada marco é visitado no máximo duas vezes (uma procurando parada, outra
depois de recarregar). O tanque parcial na origem, que o bot usa quando um
objetivo começa com o que sobrou do anterior, é o mesmo problema com a base
recuada: começar com `energia_inicial` equivale a ter enchido o tanque
`alcance - energia_inicial` antes da origem. Só o primeiro trecho muda, e a
prova de otimalidade não depende de onde a base começa.

### 4.2 A prova de otimalidade (greedy stays ahead)

A prova vale para uma rota fixa, com tanque cheio que recarrega por inteiro,
sem recarga parcial. Fixada a notação: as posições são custos acumulados,
estritamente crescentes, porque cada passo custa pelo menos 1; `A` é o
alcance; a origem está em 0 e o destino em `D`; os centros ficam só entre a
origem e o destino. Uma solução viável é uma sequência de centros
`s_1 < s_2 < ... < s_m` com `s_1 <= A`, `s_{k+1} - s_k <= A` e `D - s_m <= A`.
Recarregar enche o tanque. O guloso escolhe `g_1` como o centro mais distante
com posição no máximo `A`, e `g_{k+1}` como o centro mais distante no
intervalo `(g_k, g_k + A]`; ele para quando `D <= g_k + A`.

**Existência.** Enquanto o guloso ainda não terminou, isto é, enquanto
`D > g_k + A`, sempre existe um centro na janela `(g_k, g_k + A]` se a rota
tem solução. Seja `j` o menor índice da solução ótima com `s_j > g_k`. Esse
índice existe, porque se todos os `s` fossem no máximo `g_k`, teríamos
`D - s_m <= A` com `s_m <= g_k`, logo `D <= g_k + A`, contrariando a hipótese
de que o guloso não terminou. Como `s_{j-1} <= g_k` (ou `j = 1`, e a origem em
0 já está em `g_k` ou atrás dela) e a ótima é viável, vale
`s_j <= s_{j-1} + A <= g_k + A`. Então `s_j` é um centro dentro da janela, e o
guloso tem onde parar. Em consequência, o guloso só devolve `None` quando não
existe solução nenhuma.

**Fica à frente.** Por indução em `k`, afirmamos que `g_k >= s_k` para todo
`k` até `min(m, n)`, onde `n` é o número de paradas do guloso. Base: `s_1 <= A`
e é centro, e `g_1` é o mais distante dentro de `A`, logo `g_1 >= s_1`. Passo:
suponha `g_k >= s_k`. Da viabilidade da ótima, `s_{k+1} <= s_k + A <= g_k + A`.
Se `s_{k+1} <= g_k`, o guloso já está à frente antes mesmo de escolher
`g_{k+1}`. Caso contrário, `s_{k+1}` cai na janela `(g_k, g_k + A]`, e como o
guloso escolhe o centro mais distante dela, `g_{k+1} >= s_{k+1}`.

**Otimalidade.** Suponha, por absurdo, que o guloso faça `n > m` paradas. Antes
da parada de número `m + 1`, o guloso não havia terminado em `g_m`, ou seja,
`D > g_m + A`. Mas a invariante dá `g_m >= s_m`, e a viabilidade da ótima dá
`D - s_m <= A`, logo `D <= s_m + A <= g_m + A`. Contradição. Portanto `n <= m`,
e como a ótima é mínima, `n = m`: o guloso usa o número mínimo de paradas.

### 4.3 A versão por troca, e qual argumento vale

O mesmo resultado sai por um argumento de troca. Tome uma solução ótima e olhe
a primeira parada dela, `s_1`. Como `g_1` é o centro mais distante dentro de
`A` e `s_1 <= A`, trocar `s_1` por `g_1` deixa a próxima parada ainda
alcançável, porque `g_1 >= s_1` só aproxima o resto da rota, e não aumenta o
número de paradas. Repetindo a troca parada a parada, transforma-se qualquer
ótima na solução gulosa sem nunca piorar a contagem, logo o guloso é ótimo. Os
dois argumentos provam a mesma coisa; o relatório usa o greedy stays ahead
como principal, porque é ele que casa diretamente com o invariante conferido
em teste, e deixa a troca como leitura alternativa de um parágrafo.

### 4.4 Como a prova foi testada (fase 3, Augusto)

O argumento no papel é confrontado contra um oráculo de força bruta em
`greedy/forca_bruta.py`. O oráculo testa todos os subconjuntos de centros, do
menor para o maior, e devolve o primeiro que leva ao destino; ele não assume
nada sobre a estrutura do problema, então concordar com ele é evidência
independente de que o guloso é ótimo. São 400 rotas sorteadas em
`tests/test_caminhoneiro_otimalidade.py`, com até 15 centros (o teto que mantém
o `2^k` tratável), passo de custo sorteado entre 1 e 6, a mesma faixa dos pesos
do Trabalho 1 (de concreto a grama ferida).

Três propriedades são conferidas, e nenhuma é redundante. O guloso para
exatamente o mínimo da força bruta em toda rota com solução. O guloso devolve
`None` exatamente quando parar em todo centro também não chega, ou seja, `None`
é propriedade da rota e não falha da estratégia. E o invariante da prova, a
`k`-ésima parada do guloso nunca fica atrás da `k`-ésima parada de nenhuma
ótima, é conferido não contra uma ótima, mas contra todas elas: a função
`solucoes_otimas` devolve a lista inteira das escolhas de tamanho mínimo, e o
teste varre o invariante contra cada uma. Um teste extra garante que o sorteio
cobre os três desfechos (zero paradas, com paradas, sem solução) em pelo menos
5% das rotas cada, para que os outros não passem só com rotas triviais.

## 5. Estratégias rivais e o bot (fase 4, Augusto Campos Duarte)

### 5.1 As rivais

As estratégias existem para mostrar a tese, e todas compartilham a assinatura
do guloso, `estrategia(marcos, alcance, energia_inicial=None) -> indices |
None`. A `todo_centro` para em todo centro da rota: nunca desmaia se a rota tem
solução, mas para demais. A `limiar(pct)` imita o jogador humano, passando
direto pelo centro enquanto a energia está acima de `pct%` do tanque; a conta é
feita em inteiros (`energia * 100 <= pct * alcance`) para que o limite exato,
como 5 de 20 em 25%, não dependa de arredondamento. O `otimo` é a força bruta
exposta como estratégia, e recusa rotas com mais de 20 centros, porque acima
disso o `2^k` deixa de ser referência prática. Só o guloso e o ótimo sabem
quando a rota não tem solução e devolvem `None`; as rivais decidem pela regra
delas, e quem descobre o desmaio é a execução.

A simulação em `greedy/simulacao.py` é a conta que separa as estratégias. Dadas
as paradas, ela devolve se o treinador chegou, quantas vezes parou de fato, em
que marco desmaiou e a energia desperdiçada, que é a soma do que ainda restava
no tanque a cada recarga. Parar cedo demais joga fora energia que levaria mais
longe, e é por isso que parar tarde não é parar pouco nem parar bem.

### 5.2 O quadro da tese, número a número

O desenho da tese está travado em teste com uma rota de custo 50, centros em 8,
15, 22, 30, 38 e 45, e tanque de 20. Refazendo as contas sobre essa rota:

| Estratégia | Paradas | Energia desperdiçada | Resultado |
| --- | --- | --- | --- |
| Todo centro | 6 | 75 | chega |
| Limiar 25% | 3 | 15 | chega |
| Limiar 10% | 0 | - | desmaia no centro de 15 |
| Guloso | 2 | 10 | chega, tanque zerado |

O `todo_centro` para nos seis centros e, a cada recarga, sobra no tanque 12,
13, 13, 12, 12 e 13, somando 75 de desperdício. O limiar 25% para em 15, 30 e
45 (nos três a energia cai a exatamente 25% do tanque), três paradas e 15 de
desperdício. O limiar 10% nunca encontra um centro com energia em 10% ou menos:
passa por 15 com 5 no tanque (25%, acima do limiar) e o próximo centro, em 22,
custa 7, mais do que os 5 que restam. Desmaia no centro de 15, o último marco
alcançado, com a energia zerando entre 15 e 22. O guloso para em 15 e 30: do 30
faltam 20 até o destino, que esvaziam o tanque exato, e ele chega com energia
zero. Duas paradas e 10 de desperdício, o menor dos quatro, empatado com o
ótimo. Esses números estão conferidos em `tests/test_estrategias.py` e
`tests/test_simulacao.py`.

### 5.3 O bot

O bot da fase 4 reaproveita o loop do Trabalho 1 e acrescenta a parada. A
escolha dos objetivos continua sendo a da fase 4 do T1 (score por Dijkstra) em
qualquer caso, de propósito: trocar rota e alvo ao mesmo tempo misturaria duas
variáveis. Com uma estratégia e o jogador usando energia, cada rota planejada
passa pelo caminhoneiro, o bot anda só até a primeira parada escolhida,
recarrega com `game.recarregar` e replaneja dali com o tanque cheio. Quando a
estratégia devolve `None`, o bot para antes de andar, com o motivo `rota sem
recarga possível`, em vez de sair e desmaiar com certeza: é o mesmo tratamento
que a origem ilhada recebeu no Trabalho 1, e não gasta passo nenhum.

## 6. Benchmark de paradas (fase 5, Augusto Campos Duarte)

### 6.1 Decisões de desenho

Quatro decisões, documentadas no próprio código do experimento, sustentam a
validade da comparação. O tanque é uma fração do custo da rota do Dijkstra até
aquele destino: 30%, 50% e 75%, chamados de alcance curto, médio e longo.
Assim ele escala com o mapa e, em rotas de custo maior que 1, a rota ótima não cabe inteira num tanque, o que evita a armadilha de o guloso sempre dar zero paradas (as rotas de custo 1 são a exceção, seção 8). O mesmo tanque vale para
as rotas do DFS e do BFS no mesmo destino, e é isso que permite cruzar os três
algoritmos de rota do Trabalho 1. Rota sem recarga possível (o guloso devolve
`None`) não entra na comparação, porque nela todas desmaiam e o empate só dilui
a média; ela vai para `paradas_descartes.csv`, pois a frequência dela por
algoritmo de rota é resultado, não ruído. O ótimo por força bruta só roda até
20 centros na rota, e as linhas que ele pula somem só dele. Por fim, são
sorteados 10 destinos por mapa, em vez de 3 como no Trabalho 1, porque com
centros a 8% boa parte das rotas ainda não tem solução no tanque curto.

O experimento roda as seis regras sobre as rotas de DFS, BFS e Dijkstra, em
mapas 8x8, 15x15 e 30x30, 30 seeds cada: 7.109 simulações em `paradas.csv` e
3.983 descartes em `paradas_descartes.csv`, dos quais 3.962 por rota sem
recarga possível e 21 por origem ilhada. A simulação (`greedy/simulacao.py`) anda sobre os custos planejados da rota, sem jogo no meio: é um modelo de custos fixos, e a seção 8 mede o que muda quando a batalha entra.


### 6.2 Guloso contra ótimo, e contra todo centro

Em 1.179 pares (mesmo tamanho, seed, destino, alcance e algoritmo), o guloso
parou exatamente o mesmo número de vezes que a força bruta, com zero
divergências e nenhuma chegada diferente. A comparação é par a par porque o
ótimo é exponencial e ficou sem resultado em 7 das 1.186 rotas, todas rotas de
DFS no 30x30 com mais de 20 centros, então as médias dos dois saem de conjuntos
de rotas ligeiramente diferentes.

Contra o `todo_centro`, nos destinos em que ambos chegaram, o guloso nunca
parou mais vezes, e a distância cresce com o mapa: 0,99 contra 1,36 parada no
8x8 (318 destinos), 1,21 contra 2,62 no 15x15 (312 destinos), e 1,69 contra
6,26 no 30x30 (556 destinos). É a tese medida em escala: a estratégia que para
em todo centro paga quase quatro vezes mais paradas no mapa grande para chegar
ao mesmo lugar.

### 6.3 Paradas e desmaios por tamanho

A tabela abaixo recorta a rota do Dijkstra no alcance médio (50% do custo), que
é o cenário em que a tese aparece com mais nitidez. As médias de paradas e
desperdício contam só quem chegou, por isso a coluna de desmaio vem ao lado.

| Tamanho | Estratégia | Rotas com solução | Paradas (quem chegou) | Desmaio | Desperdício (quem chegou) |
| --- | --- | --- | --- | --- | --- |
| 8 | Guloso | 31 | 1,39 | 0% | 10,4 |
| 8 | Ótimo | 31 | 1,39 | 0% | 10,8 |
| 8 | Todo centro | 31 | 1,65 | 0% | 18,3 |
| 8 | Limiar 50% | 31 | 1,24 | 19% | 8,5 |
| 8 | Limiar 25% | 31 | 0,88 | 45% | 1,1 |
| 8 | Limiar 10% | 31 | 0,64 | 55% | 0,2 |
| 15 | Guloso | 46 | 1,70 | 0% | 20,9 |
| 15 | Ótimo | 46 | 1,70 | 0% | 22,5 |
| 15 | Todo centro | 46 | 3,15 | 0% | 73,4 |
| 15 | Limiar 50% | 46 | 1,75 | 30% | 19,7 |
| 15 | Limiar 25% | 46 | 0,38 | 83% | 0,9 |
| 15 | Limiar 10% | 46 | 0,25 | 83% | 0,0 |
| 30 | Guloso | 103 | 1,81 | 0% | 28,6 |
| 30 | Ótimo | 103 | 1,81 | 0% | 47,4 |
| 30 | Todo centro | 103 | 6,28 | 0% | 442,3 |
| 30 | Limiar 50% | 103 | 2,11 | 30% | 57,6 |
| 30 | Limiar 25% | 103 | 1,62 | 61% | 16,0 |
| 30 | Limiar 10% | 103 | 1,36 | 76% | 4,9 |

A leitura precisa começar pela coluna de desmaio. O limiar 10% parece a mais
barata do 15x15, com 0,25 parada em média, mas desmaia em 83% das rotas: a
média é de quem sobreviveu. O limiar 50% chega mais perto do guloso em paradas,
mas ainda desmaia em 30% das rotas no 15x15. Somando os desmaios de todos os
alcances na rota do Dijkstra, o padrão se mantém por tamanho: no 8x8 o limiar
10% desmaia em 69% das rotas, o 25% em 44% e o 50% em 17%; no 15x15 são 71%,
55% e 24%; no 30x30 são 69%, 46% e 19%. O guloso, o ótimo e o `todo_centro` não
desmaiam em nenhuma. A estratégia humana ou chega parando demais, como o
`todo_centro`, ou desmaia tentando economizar, como os limiares. No modelo de custos fixos, o guloso é o único que chega sempre e com o mínimo de paradas; o jogo com batalha aleatória não mantém isso (seção 8).

### 6.4 O cruzamento com os algoritmos de rota

O ponto que liga os dois trabalhos é a pergunta de se a rota mais barata (a do
Dijkstra) também precisa de menos paradas que as do DFS e do BFS. Nos 236
destinos em que as três rotas têm solução no mesmo tanque, a rota do Dijkstra
precisou de menos paradas em 28, empatou em 208 e nunca precisou de mais. É
evidência de que as duas otimizações andam juntas na prática, mas não é
garantia (seção 8).

## 7. Interface e viabilidade do tanque (fase 6, Lucas Gabriel Antunes)

### 7.1 O alcance mínimo

O jogador escolhe o tamanho do tanque na interface, e a tela precisa dizer na
hora se aquela escolha tem solução. A resposta exata está em
`greedy/viabilidade.py`: o alcance mínimo é o maior trecho entre dois pontos de
recarga consecutivos (a origem, cada centro e o destino). Parar em todo centro
é a escolha mais permissiva, porque recarregar enche o tanque e parar a mais
nunca atrapalha; logo o maior desses trechos é um limite exato. Com um tanque
menor que ele, nenhuma escolha de paradas resolve; com ele ou mais, o guloso
resolve. Os testes confirmam as duas metades, contra o guloso e contra a força
bruta, em 300 rotas sorteadas: no mínimo há solução, e um a menos não há.

### 7.2 A viabilidade da missão vem do próprio bot

A tela de alcance não decide a viabilidade pela rota concatenada do Dijkstra, e
sim rodando o próprio bot. A primeira versão estimava sobre a rota concatenada
e errou: prometeu solução em 220 casos dos quais só 40 venciam de verdade,
porque o bot escolhe o próximo objetivo depois de chegar no anterior e segue
com o tanque parcial. Agora a resposta vem de uma simulação real da missão com
o tanque escolhido, determinística pela mesma semeadura do benchmark, e o teste
que trava essa propriedade confere mais de 40 casos sem nenhum falso positivo.

A vitória não é monótona no tanque, e isso tem consequência direta no rótulo da
tela. No mapa 8x8 de seed 3, a busca binária acha 122 como menor tanque, mas o
tanque 46 já vence e o 45 não (caso medido, travado no teste
`test_a_busca_binaria_nao_acha_o_menor_tanque_em_todo_mapa`). A causa provável,
não verificada, é que o tanque muda as paradas, e as paradas mudam a ordem dos
sorteios de batalha. Por isso o número que a busca devolve é chamado de mínimo
verificado, o menor que a busca achou, não uma garantia de que nenhum tanque
menor funcione.

### 7.3 Comparar: seis raias do bot real

A tela de comparação põe as seis estratégias lado a lado, e cada raia é uma
execução real do bot com a mesma seed e o mesmo tanque, não a rota planejada
concatenada. O caso ilustrativo do mapa padrão, medido, é o 8x8 de seed 4 com
tanque 64: o guloso chega com 1 parada e 0 de desperdício, o `todo_centro` com
4 paradas e 192 de desperdício, os três limiares desmaiam no custo 116, e o
ótimo chega com 1 parada. A tela trava o sorteio das batalhas pela seed (`random.seed("8-4")`), por isso
o resultado se repete. O terminal (`main.py --bot --size 8 --seed 4 --energia
64 --estrategia X`) não semeia o sorteio, e o mesmo comando dá resultados
diferentes a cada execução: em 6 execuções, o guloso terminou uma vez em `rota
sem recarga possível` e o limiar 25% desmaiou 2 vezes. O caso é, portanto, um
sorteio fixo que mostra, numa partida só, as três formas de errar e a certa, e
não a regra: em 40 outros sorteios de batalha nesse mesmo mapa e tanque, só 4
partidas terminam em vitória, para qualquer estratégia (34 terminam em `sem
energia` ou `rota sem recarga possível`, 2 em `sem pokemon`).

### 7.4 Consistência e concorrência

O snapshot JSON que a tela de benchmark lê guarda o commit e a data em que foi
gerado, e as premissas de leitura são conferidas a cada geração: que
`chegadas + desmaios = execucoes`, que guloso e ótimo têm o mesmo número de
paradas em todos os pares, e que o guloso é igual ao ótimo conferido par a par,
porque o ótimo só roda até 20 centros. O sorteio do jogo é global, então
simulação, stream e passo do jogo humano disputam a mesma semente; a partida ao
vivo segura uma trava do gerador de sorteio do começo ao fim, com timeout, para
que um pedido de alcance no meio de uma partida não reseede o random e mude as
batalhas que o bot vive. Um teste de concorrência reproduz essa corrida.

## 8. Limitações

A limitação mais estrutural não é defeito de código: o guloso não resolve a
escolha da rota. O Dijkstra minimiza energia, não paradas, e uma rota um pouco
mais cara em energia pode exigir menos paradas. O problema conjunto, escolher a
rota e as paradas de uma vez, não é coberto pela prova da seção 4, que vale só
para uma rota fixa. O cruzamento da seção 6.4 (28 vitórias do Dijkstra em
paradas, 208 empates e zero derrotas em 236 destinos) é evidência empírica
dessa coerência, não garantia dela. Um desvio até um centro fora da rota
transformaria o problema em outro, e o plano decidiu contar só centro no
caminho.

O modelo não é o jogo. O experimento da seção 6 simula as paradas sobre os
custos planejados da rota, sem batalha no meio, e é nesse modelo que o guloso é
ótimo e nunca desmaia. No jogo, a batalha tira HP e o HP encarece a grama (de 3
para até 6), então o custo real de um trecho pode passar do planejado, e o bot
replaneja a cada objetivo com o tanque que sobrou. Para medir o efeito rodamos o
bot de verdade em 15 mapas que o Trabalho 1 vence (8x8 e 15x15), com o tanque em
1,5 vez o mínimo verificado de cada mapa e 20 sorteios de batalha por mapa e
estratégia. O mapa é idêntico entre os sorteios (o `Grid` tem gerador próprio),
só as batalhas mudam: 300 partidas por estratégia.

| Estratégia | Chega | Desmaia (`sem energia`) | Bot não sai (`rota sem recarga possível`) | Sem Pokémon |
| --- | --- | --- | --- | --- |
| Guloso | 230 (77%) | 0 | 43 | 27 |
| Todo centro | 257 (86%) | 19 | 0 | 24 |
| Limiar 50% | 254 (85%) | 19 | 0 | 27 |
| Limiar 25% | 231 (77%) | 42 | 0 | 27 |
| Limiar 10% | 227 (76%) | 46 | 0 | 27 |

O guloso não desmaiou em nenhuma das 300 partidas, mas em 43 (14%) o bot
encontrou um plano sem recarga viável e parou antes de andar, e por isso o
guloso chega menos que o `todo_centro` (77% contra 86%). A diferença entre
desmaiar e não sair é real, porque o bot que não sai não gasta passo nem
energia, mas para a missão as duas são falha. A coluna `Sem Pokémon` (8% a 9%)
é derrota em batalha e não depende da regra de parada; as diferenças pequenas
entre as linhas provavelmente vêm de os sorteios divergirem depois da primeira
parada (não verificado). A
causa provável da recusa é o HP ter caído e encarecido a grama acima do tanque
restante, mas não isolamos isso (a confirmar). Três ressalvas: é uma única
configuração de tanque (1,5x), não uma varredura; a medição está em `bench/jogo_real.py` (`python -m bench.jogo_real`, cerca de 75 s) e reproduz a tabela acima; e o
mínimo verificado vem de um sorteio fixo, então 1,5x dele não é folga garantida
em outro sorteio. O que a medição sustenta é que "o guloso nunca desmaia"
sobrevive ao jogo e "o guloso sempre chega" não.

O bot replaneja a cada objetivo, então as paradas que ele faz são ótimas por
trecho, a rota até o próximo objetivo, não ótimas para a missão inteira. É a
mesma escolha de desenho do Trabalho 1, de replanejar depois de cada alvo, e
tem o mesmo efeito aqui.

As médias do benchmark carregam dois vieses, e nenhum foi escondido. O primeiro
é o viés de descarte: 3.983 dos 5.169 casos (rota x alcance x algoritmo), ou
77%, foram descartados por rota sem recarga possível (3.962) ou origem ilhada
(21), e as médias só contam o que sobrou. O caso extremo é o alcance curto no
8x8: sobraram só 5 rotas, e todas têm custo 1, destino colado na origem, tanque
`max(1, round(0.3 * 1)) = 1` e zero paradas em qualquer estratégia. São rotas
triviais, e servem só de exemplo do viés. O segundo é o viés de sobrevivente
nas médias de paradas e desperdício dos limiares: só contam quem chegou, e por
isso o limiar 10% parece barato, porque quem desmaia não entra na conta. É
exatamente por isso que a tabela da seção 6.3 traz a taxa de desmaio ao lado da
média.

O ótimo não cobre 7 das 1.186 rotas (DFS no 30x30, com mais de 20 centros), e é
por isso que a comparação com o guloso é par a par, sobre 1.179 pares. O guloso
desperdiça menos energia que o ótimo em média (no 15x15 médio, 20,9 contra
22,5; no 30x30 médio, 28,6 contra 47,4). Isso não é contradição: o ótimo só
garante o número mínimo de paradas, e entre as combinações com esse número a
força bruta devolve a primeira que encontra (`otimas[0]`), que tende a parar
cedo. É uma explicação coerente com o código, não uma prova; parte da diferença
também pode vir das 7 rotas que o ótimo não cobre.

Em muitos cenários as estratégias simplesmente empatam, quando há poucos
centros ou o tanque está folgado. A tese só aparece onde o tanque aperta, e o
mapa padrão da interface foi escolhido justamente por mostrar isso.

A interface tem buracos de verificação conhecidos. Não há teste automatizado do
JavaScript: a tela foi conferida só manualmente no navegador. Na tela de jogo
humano, não foram exercitados recarregar em cima de um centro, a vitória, nem a
dica de custo ao passar o mouse. O terminal, por sua vez, pede cinco respostas
interativas antes de começar (nome, gênero, natureza, inicial e o nome do
Pokémon), o que não entra em teste automatizado. O que está coberto por teste é
a camada de regras do servidor, a API de alcance e viabilidade, as estratégias,
a simulação, a prova contra força bruta e a concorrência do sorteio.

A suíte tem 3.376 testes, confirmados rodando
`python3 -m pytest -q -p no:cacheprovider`, que leva cerca de 60 segundos (a
confirmar o tempo exato na máquina do avaliador).

## 9. Conclusão

O trabalho respondeu à pergunta que o motivou: sobre uma rota fixa com energia
limitada, parar tarde não é parar pouco, e o guloso que só para no centro mais
distante alcançável usa o número mínimo de paradas. A afirmação foi provada por
greedy stays ahead e por troca, e confrontada contra um oráculo de força bruta
em 400 rotas sorteadas, com zero divergências. No benchmark sobre as rotas do
Trabalho 1, o guloso igualou o ótimo em todos os 1.179 pares, nunca parou mais
que o `todo_centro` (6,26 contra 1,69 parada no 30x30), e nunca desmaiou no modelo, enquanto os limiares humanos desmaiam em até 83% das rotas num cenário apertado. No jogo com batalha aleatória o quadro é mais duro (seção 8): o guloso continua sem desmaiar, mas o bot se recusa a sair em 14% das partidas medidas e o guloso chega menos que o `todo_centro` (77% contra 86%).

As duas otimizações se empilham sem se atropelar: o Dijkstra minimiza energia e
o guloso minimiza paradas sobre a rota que ele devolve. O cruzamento mostrou
que a rota mais barata também tende a precisar de menos paradas (28 vitórias e
208 empates em 236 destinos), mas o trabalho é honesto em dizer que isso é
tendência medida, não teorema, e que escolher rota e paradas de uma vez é um
problema que a prova não cobre.

Os pontos mais concretos deixados em aberto são três. Primeiro, atacar o
problema conjunto de rota e paradas, que exigiria um algoritmo que não é o
guloso de uma dimensão só. Segundo, modelar recarga parcial, que a prova atual
exclui ao supor que o centro enche o tanque. Terceiro, fechar a verificação da
interface com teste automatizado do JavaScript, hoje conferida só à mão, e
cobrir os caminhos da tela de jogo humano que ficaram fora do teste.
