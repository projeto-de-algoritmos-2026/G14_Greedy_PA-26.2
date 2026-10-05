"""Benchmark comparativo (fase 6 do trabalho 1, fase 5 do trabalho 2).

Os dois primeiros sao do trabalho 1, e a separacao e o ponto principal do desenho:

- `bench.rotas`: rota pura. Mesma origem, mesmo destino, mesmo estado, tres
  algoritmos. E o experimento que sustenta a tese do trabalho, porque isola a
  unica variavel que interessa (a estrategia de busca) e mede custo, passos e
  nos expandidos sem nada mais no meio.

- `bench.partidas`: partida completa. O bot da fase 5 joga do inicio ao fim
  com cada algoritmo escolhendo a rota, e o que se mede e a consequencia:
  batalhas forcadas, HP perdido, objetivos concluidos. Aqui o mapa muda
  durante a execucao (celula virou VISITADO, surf apareceu, HP caiu), entao os
  numeros nao sao comparaveis linha a linha com os do outro experimento.

- `bench.paradas` (trabalho 2): paradas de recarga. Sobre a rota de cada
  algoritmo, cada estrategia de greedy.estrategias escolhe onde recarregar e
  greedy.simulacao conta paradas, desmaios, energia desperdicada e gasta. E o
  experimento da tese "parar tarde nao e parar pouco", e o cruzamento com os
  tres algoritmos liga os dois trabalhos.

Grade: tamanhos 8, 15 e 30 x 30 seeds x 3 algoritmos (e, nas paradas, 3
tanques x 6 estrategias). Saida em CSV em `bench/out/`, mais graficos SVG em
`bench.charts`.
"""
