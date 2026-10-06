"""Medicao no jogo real: o que acontece quando a batalha entra (secao 8 do relatorio).

O experimento de paradas (bench/paradas.py) simula as estrategias sobre os
custos PLANEJADOS da rota, sem batalha no meio. Aqui o bot joga de verdade: a
batalha tira HP, o HP encarece a grama e o tanque que sobra pode nao bastar.

O mapa de cada seed e o mesmo em todos os sorteios (o Grid tem gerador proprio);
so as batalhas mudam, porque o sorteio global do jogo e semeado por partida. O
tanque de cada mapa e `multiplo` vezes o menor tanque que o bot vence (o
"minimo verificado" da interface), igual pra todas as estrategias.

Nao grava nada em bench/out/: imprime a tabela. Leva alguns minutos com os
valores padrao (15 mapas x 5 estrategias x 20 sorteios).

    python -m bench.jogo_real
    python -m bench.jogo_real --tamanhos 8 --mapas 5 --sorteios 10

Depende de webdemo.api_greedy (menor_tanque, novo_jogador e a trava do sorteio
global), que e onde a interface decide a viabilidade do tanque.
"""
import argparse
import random
from collections import Counter

from bot.runner import executar_bot
from greedy.estrategias import ESTRATEGIAS
from grid import Grid
from webdemo import api_greedy

# O otimo fica de fora: nas rotas longas a forca bruta e cara e, por
# construcao, ele devolve as mesmas paradas do guloso.
ESTRATEGIAS_MEDIDAS = ("guloso", "todo_centro", "limiar_50", "limiar_25", "limiar_10")
VITORIA = "quatro pokemon capturados"
MOTIVOS = ("sem energia", "rota sem recarga possivel", "sem pokemon")


def jogar(tamanho, seed_mapa, tanque, estrategia, sorteio):
    """Motivo de parada de uma partida do bot com esse tanque e esse sorteio."""
    with api_greedy._TRANCA_RNG:
        random.seed(str(sorteio))
        mapa = Grid(size=tamanho, seed=seed_mapa)
        jogador = api_greedy.novo_jogador()
        jogador.energia = jogador.energia_max = tanque
        with api_greedy.silencioso():
            resultado = executar_bot(mapa, jogador, max_passos=10 * tamanho * tamanho,
                                     estrategia=ESTRATEGIAS[estrategia])
    return resultado.motivo_parada


def escolher_mapas(tamanhos, mapas_por_tamanho, multiplo):
    """(tamanho, seed, tanque) dos mapas que o bot vence com algum tanque."""
    escolhidos = []
    for tamanho in tamanhos:
        for seed in range(mapas_por_tamanho):
            minimo, _ = api_greedy.menor_tanque(tamanho, seed)
            if minimo is not None:
                escolhidos.append((tamanho, seed, round(minimo * multiplo)))
    return escolhidos


def medir(tamanhos=(8, 15), mapas_por_tamanho=14, sorteios=20, multiplo=1.5):
    """Devolve (mapas, {estrategia: Counter de motivo de parada})."""
    mapas = escolher_mapas(tamanhos, mapas_por_tamanho, multiplo)
    desfechos = {nome: Counter() for nome in ESTRATEGIAS_MEDIDAS}
    for tamanho, seed, tanque in mapas:
        for nome in ESTRATEGIAS_MEDIDAS:
            for sorteio in range(sorteios):
                desfechos[nome][jogar(tamanho, seed, tanque, nome, sorteio)] += 1
    return mapas, desfechos


def tabela(desfechos):
    linhas = ["| Estrategia | Partidas | Chega | Sem energia | Rota sem recarga | Sem pokemon | Outros |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for nome, c in desfechos.items():
        n = sum(c.values())
        outros = n - c[VITORIA] - sum(c[m] for m in MOTIVOS)
        linhas.append(f"| {nome} | {n} | {c[VITORIA]} ({100 * c[VITORIA] / n:.0f}%) | "
                      f"{c['sem energia']} | {c['rota sem recarga possivel']} | "
                      f"{c['sem pokemon']} | {outros} |")
    return "\n".join(linhas)


def main(argv=None):
    p = argparse.ArgumentParser(description="Estrategias de parada no jogo real, com batalha aleatoria")
    p.add_argument("--tamanhos", type=int, nargs="+", default=[8, 15])
    p.add_argument("--mapas", type=int, default=14, help="seeds de mapa por tamanho (0 a N-1)")
    p.add_argument("--sorteios", type=int, default=20, help="sorteios de batalha por mapa e estrategia")
    p.add_argument("--multiplo", type=float, default=1.5, help="tanque = multiplo x minimo verificado")
    args = p.parse_args(argv)
    mapas, desfechos = medir(tuple(args.tamanhos), args.mapas, args.sorteios, args.multiplo)
    print(f"{len(mapas)} mapas que o bot vence, tanque {args.multiplo}x o minimo verificado, "
          f"{args.sorteios} sorteios de batalha por mapa e estrategia")
    print(tabela(desfechos))


if __name__ == "__main__":
    main()
