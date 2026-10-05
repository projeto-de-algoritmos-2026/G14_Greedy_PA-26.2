# Contrato do benchmark do Trabalho 2: o que a interface lê

Escrito depois de ler a `feature/fase-5-benchmark` (commits das 10:54 de 05/10). O formato que você fez **já é o contrato**: a interface (fase 6) vai ler os seus CSVs como estão. Este arquivo só registra o que eu vou assumir ao ler, e o que eu entrego do meu lado. **Não tem pedido de mudança para você.**

Conferi: rodei o seu `python -m bench.paradas` num worktree temporário (7.109 simulações, 3.983 descartes), os 10 testes passam, `--so paradas` já está no `bench/__main__.py`, e os CSVs commitados batem com o que o código gera.

## 1. O que a interface lê

| Arquivo | Para que serve na tela |
|---|---|
| `paradas_resumo.csv` | gráficos da página "Trabalho 2": paradas, desmaios, energia desperdiçada, por estratégia |
| `paradas_cruzamento.csv` | página "Juntos": a rota do Dijkstra precisa de menos paradas que as do DFS e do BFS? |
| `paradas.csv`, `paradas_descartes.csv` | a tela não lê; ficam de auditoria |

Eu converto os dois primeiros para um JSON leve (`webdemo/dados/`), com data e commit, do meu lado. Você não produz JSON nenhum.

## 2. O que eu vou assumir ao ler

Conferi cada uma nos CSVs commitados:

1. `chegadas + desmaios = execucoes` nas 162 linhas do resumo.
2. `guloso` e `otimo` têm o **mesmo número de paradas** nos 1.179 pares (destino, alcance, algoritmo), e nenhum dos dois desmaia.
3. `taxa_inviavel = rotas_inviaveis / (rotas_inviaveis + execucoes)`.
4. As médias (`paradas_medio`, `energia_*_medio`) contam só as rotas viáveis; as inviáveis ficam em `paradas_descartes.csv`.
5. Os níveis de alcance são `curto`, `medio` e `longo` (30%, 50% e 75% do custo da rota do Dijkstra).

Se algum desses mudar, me avisa; o resto da tela não quebra, só essa leitura.

## 3. O que já conferi sobre juntar as duas fases

- **`grid.py` (4% para 8% de Centros):** não altera o T1. Rodei `bench.rotas` (tamanhos 8 e 15, 10 seeds) com 4% e com 8%: as 288 linhas saíram idênticas, descontado o tempo. Os números do README do T1 continuam valendo.
- **Minha branch** (`feature/fase-6-interface-backend`, ainda local, nada no master) mexe em `game.py` (dois campos novos com valor padrão 0 em `Movimento`), em `bot/runner.py` (dois ganchos opcionais), em `greedy/__init__.py` (só o import novo) e cria `greedy/viabilidade.py`. Testei junto com a sua branch: **3.242 testes passam** (3.232 da minha mais os seus 10). Não encostei em `bench/*`.
- Não há nenhum arquivo em comum entre as duas branches, então a ordem dos PRs não importa. O `greedy/__init__.py` eu alterei do meu lado (só adicionei o import do `greedy/viabilidade` e o nome no `__all__`), mas você não mexe nele, então não conflita.

## 4. Uma correção minha

Eu tinha afirmado que `bench/out/` "não vai para o git". O `.gitignore` ignora a pasta, mas os CSVs consolidados são adicionados à força (o T1 fez assim e você também, nos `paradas*.csv`). Então a interface pode ler os CSVs do próprio repositório. Mantenho o JSON só por ser mais leve de carregar no navegador.
