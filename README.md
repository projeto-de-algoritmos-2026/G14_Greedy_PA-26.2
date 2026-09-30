# Pokémon CLI: o Caminhoneiro

Projeto de Algoritmos (FGA0124) | Grupo 14 | Módulo 2: Algoritmos Ambiciosos (Greedy)

| Matrícula | Aluno |
| --- | --- |
| 190091681 | Lucas Gabriel Antunes |
| 202045965 | Augusto Campos Duarte |

## Apresentação

Vídeo de apresentação: a publicar.

## Sobre

Continuação do [Trabalho 1](https://github.com/projeto-de-algoritmos-2026/G14_Grafos_PA-26.2),
em que o Dijkstra traçava a rota mais barata num jogo de Pokémon de terminal.
Agora o treinador tem **energia limitada** e o mapa ganha **Centros Pokémon**,
onde ela recarrega. Cada passo gasta de energia exatamente o peso que o grafo
do Trabalho 1 dá para a aresta.

O algoritmo do **caminhoneiro** (o problema clássico do posto de gasolina)
decide em quais centros parar ao longo da rota para chegar ao destino com o
**mínimo de paradas**. São duas otimizações empilhadas: o Dijkstra minimiza a
energia total da rota, e o guloso minimiza o número de paradas sobre ela.

A tese é que **parar tarde não é parar pouco**: a regra intuitiva de parar
quando a energia fica baixa ou para demais ou desmaia no meio do caminho, e o
guloso, que só para no centro mais distante que ainda alcança, é ótimo.

O plano completo, em fases, está em [`docs/plano-trabalho-2.html`](docs/plano-trabalho-2.html).

## Estado

| Fase | Conteúdo | Estado |
| --- | --- | --- |
| 0 | Repositório a partir do Trabalho 1 | feito |
| 1 | Energia e Centro Pokémon | feito |
| 2 | Algoritmo do caminhoneiro | feito |
| 3 | Testes e prova de otimalidade | a fazer |
| 4 | Estratégias rivais e bot | a fazer |
| 5 | Benchmark | a fazer |
| 6 | Interface | a fazer |
| 7 | Entrega | a fazer |

## Modelagem (fase 1)

- **Energia não é HP.** O HP cai em batalha aleatória e já muda o custo da
  grama. O caminhoneiro só é ótimo quando o consumo de cada trecho é conhecido
  antes de sair, então a energia é um atributo próprio do `Player`.
- **Consumo é o peso do Trabalho 1.** Entrar numa célula gasta
  `custo_entrada(celula, estado)`, calculado com o estado de antes do passo,
  incluindo a penalidade de batalha. É o mesmo número que o Dijkstra usou para
  planejar.
- **Centro é prédio, não item.** Não some quando pisado e passar por ele não
  recarrega sozinho: recarregar é uma ação separada (`game.recarregar`), porque
  passar sem parar é justamente a escolha do guloso.
- **Sem energia para o próximo passo, o treinador desmaia** onde está e a
  partida acaba com o motivo `sem energia`.
- **Os mapas do Trabalho 1 não mudaram.** Os centros são sorteados depois do
  mapa inteiro, só em células livres fora da água e da origem. Em 90 mapas
  (8, 15 e 30, 30 seeds cada) nenhuma célula mudou além das que viraram
  centro, e nenhuma distância do Dijkstra mudou.
- **Energia `None` desliga a regra**, e o jogo, o bot e o benchmark do
  Trabalho 1 funcionam como antes.

## O algoritmo (fase 2)

O caminhoneiro é uma função pura em `greedy/caminhoneiro.py`, separada do mapa e
do jogo para poder ser testada com listas de números.

- **`marcos_da_rota(caminho, mapa, estado)`** reduz a rota que o Dijkstra
  devolveu a uma lista de marcos `(custo_acumulado, é_centro)`. A origem entra
  com custo zero (o tanque começa cheio) e o custo acumulado do último marco é,
  por construção, o custo total que o Dijkstra calculou.
- **`paradas(marcos, alcance)`** decide onde parar. A partir do ponto onde o
  tanque encheu, anda até o **centro mais distante ainda dentro do alcance** e
  para nele; repete até o destino caber no tanque. Retorna os índices dos
  centros escolhidos: lista vazia quando a rota inteira cabe num tanque (zero
  paradas) e `None` quando algum trecho entre pontos de recarga passa do
  alcance (rota inviável).
- **`alcance` é o tamanho do tanque** e recarregar num centro enche de novo. É
  linear no tamanho da rota, porque os marcos já vêm ordenados por ela.

A prova de que o guloso é ótimo (`greedy stays ahead`) e os testes de força
bruta vêm na fase 3.

## Como executar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest                  # testes
python -m webdemo                 # interface web do Trabalho 1
python main.py --bot --size 15    # bot no terminal
```

## Trabalho 1

O README e o relatório do Trabalho 1 foram preservados em
[`docs/README-trabalho-1.md`](docs/README-trabalho-1.md) e
[`docs/relatorio-trabalho-1.md`](docs/relatorio-trabalho-1.md).

## Referência

Este projeto parte do jogo original criado por
[elchic00](https://github.com/elchic00/pokemon), adaptado pelos alunos para a
disciplina.
