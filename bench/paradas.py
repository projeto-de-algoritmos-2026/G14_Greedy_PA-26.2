"""Experimento 3 (trabalho 2): paradas de recarga sobre a rota.

A rota vem pronta da busca do trabalho 1 e o que muda e ONDE parar pra
recarregar. Cada linha e uma estrategia de greedy.estrategias executada sobre
uma rota por greedy.simulacao, sem jogo no meio: mesmo mapa, mesma rota, mesmo
tanque, so a regra de parada muda. E o recorte em que "parar tarde nao e parar
pouco" pode ser afirmado sem ressalva.

Decisoes de desenho que precisam estar no relatorio:

1. O tanque e uma fracao do custo da rota do Dijkstra ate aquele destino
   (30%, 50% e 75%). Assim ele escala com o mapa e a rota otima nunca cabe
   inteira num tanque: a armadilha do 8x8, em que o guloso sempre da zero
   paradas, nao acontece. O mesmo tanque vale pras rotas do DFS e do BFS no
   mesmo destino, e e isso que deixa cruzar os algoritmos do trabalho 1.
2. Rota sem recarga possivel (o guloso devolve None) nao entra na comparacao
   das estrategias: nela todas desmaiam e o empate so dilui a media. Ela vai
   pra `paradas_descartes.csv`, como a origem ilhada do trabalho 1, porque a
   frequencia dela por algoritmo de rota e resultado, nao ruido.
3. O otimo por forca bruta so roda ate MAX_CENTROS_OTIMO centros na rota. Ele
   e a referencia que confirma o guloso, nao uma estrategia jogavel, e nas
   rotas longas do DFS no 30x30 o 2^k deixa de ser pratico. As linhas que ele
   pula somem so dele: a coluna `execucoes` do resumo mostra quantas sobraram.
4. Os destinos sao sorteados como em `bench.rotas` (componente alcancavel sem
   surf, sorteio reproduzivel), so que 10 por mapa em vez de 3: com centros a
   8% boa parte das rotas ainda nao tem solucao no tanque curto, e 3 destinos
   deixavam o 8x8 com amostra pequena demais.
"""

import argparse
from pathlib import Path

from graph.search import dijkstra
from greedy import marcos_da_rota
from greedy.estrategias import ESTRATEGIAS, MAX_CENTROS_OTIMO, guloso
from greedy.forca_bruta import candidatos
from greedy.simulacao import simular
from grid import Grid

from .common import (
    ALGORITMOS,
    SAIDA_PADRAO,
    SEEDS,
    TAMANHOS,
    agrupar,
    escrever_csv,
    media,
)
from .rotas import ESTADOS, ORIGEM, sortear_destinos

DESTINOS_POR_MAPA = 10
ESTADO = ESTADOS["hp100"]

# Fracao do custo da rota do Dijkstra que cabe no tanque. A ordem importa: e
# a ordem das linhas dos resumos.
ALCANCES = {
    "curto": 0.30,
    "medio": 0.50,
    "longo": 0.75,
}

CAMPOS = [
    "tamanho", "seed", "destino", "alcance", "tanque", "algoritmo",
    "custo_rota", "centros_na_rota", "estrategia", "chegou", "paradas",
    "energia_desperdicada", "energia_gasta",
]

CAMPOS_RESUMO = [
    "tamanho", "alcance", "algoritmo", "estrategia", "execucoes", "chegadas",
    "desmaios", "taxa_desmaio", "paradas_medio", "energia_desperdicada_medio",
    "energia_gasta_medio", "rotas_inviaveis", "taxa_inviavel",
]

CAMPOS_DESCARTE = [
    "tamanho", "seed", "destino", "alcance", "tanque", "algoritmo", "motivo",
]

CAMPOS_CRUZAMENTO = [
    "tamanho", "alcance", "destinos_comparados", "dijkstra_menos_paradas",
    "empates", "dijkstra_mais_paradas",
]


def tanque(custo_referencia, fracao):
    """Tamanho do tanque pra um destino. Nunca menos de 1."""
    return max(1, round(custo_referencia * fracao))


def medir_rota(marcos, alcance, estrategia):
    """Paradas da estrategia simuladas sobre os marcos, ou None se ela nao roda.

    So o otimo deixa de rodar, e so quando a rota tem centros demais pra forca
    bruta.
    """
    if estrategia == "otimo" and len(candidatos(marcos)) > MAX_CENTROS_OTIMO:
        return None
    escolhidas = ESTRATEGIAS[estrategia](marcos, alcance)
    return simular(marcos, alcance, escolhidas)


def rodar(tamanhos=TAMANHOS, seeds=SEEDS, destinos_por_mapa=DESTINOS_POR_MAPA):
    """Roda a grade inteira e devolve (linhas, descartes)."""
    linhas, descartes = [], []
    for tamanho in tamanhos:
        for seed in range(seeds):
            mapa = Grid(size=tamanho, seed=seed)
            destinos = sortear_destinos(mapa, destinos_por_mapa)
            if not destinos:
                descartes.append({
                    "tamanho": tamanho, "seed": seed, "destino": "",
                    "alcance": "", "tanque": "", "algoritmo": "",
                    "motivo": "origem sem componente alcancavel sem surf",
                })
                continue
            for destino in destinos:
                rotas = {nome: algoritmo(ORIGEM, destino, mapa, ESTADO)[0]
                         for nome, algoritmo in ALGORITMOS.items()}
                _, custo_referencia, _ = dijkstra(ORIGEM, destino, mapa, ESTADO)
                for nome_alcance, fracao in ALCANCES.items():
                    alcance = tanque(custo_referencia, fracao)
                    base = {
                        "tamanho": tamanho,
                        "seed": seed,
                        "destino": f"{destino[0]}-{destino[1]}",
                        "alcance": nome_alcance,
                        "tanque": alcance,
                    }
                    for nome_algoritmo, caminho in rotas.items():
                        marcos = marcos_da_rota(caminho, mapa, ESTADO)
                        if guloso(marcos, alcance) is None:
                            descartes.append({
                                **base, "algoritmo": nome_algoritmo,
                                "motivo": "rota sem recarga possivel",
                            })
                            continue
                        for estrategia in ESTRATEGIAS:
                            simulacao = medir_rota(marcos, alcance, estrategia)
                            if simulacao is None:
                                continue
                            linhas.append({
                                **base,
                                "algoritmo": nome_algoritmo,
                                "custo_rota": marcos[-1][0],
                                "centros_na_rota": len(candidatos(marcos)),
                                "estrategia": estrategia,
                                "chegou": int(simulacao.chegou),
                                "paradas": simulacao.paradas,
                                "energia_desperdicada": simulacao.energia_desperdicada,
                                "energia_gasta": simulacao.energia_gasta,
                            })
    return linhas, descartes


def resumir(linhas, descartes):
    """Media por (tamanho, alcance, algoritmo, estrategia).

    `rotas_inviaveis` vem dos descartes e e o mesmo pra toda estrategia da
    mesma rota: e a parte da amostra que nenhuma estrategia atravessa.
    """
    inviaveis = agrupar(
        [d for d in descartes if d["motivo"] == "rota sem recarga possivel"],
        ["tamanho", "alcance", "algoritmo"],
    )
    resumo = []
    for (tamanho, alcance, algoritmo, estrategia), grupo in agrupar(
        linhas, ["tamanho", "alcance", "algoritmo", "estrategia"]
    ).items():
        chegadas = sum(int(linha["chegou"]) for linha in grupo)
        sem_solucao = len(inviaveis.get((tamanho, alcance, algoritmo), []))
        resumo.append({
            "tamanho": tamanho,
            "alcance": alcance,
            "algoritmo": algoritmo,
            "estrategia": estrategia,
            "execucoes": len(grupo),
            "chegadas": chegadas,
            "desmaios": len(grupo) - chegadas,
            "taxa_desmaio": round((len(grupo) - chegadas) / len(grupo), 3),
            "paradas_medio": media(grupo, "paradas"),
            "energia_desperdicada_medio": media(grupo, "energia_desperdicada"),
            "energia_gasta_medio": media(grupo, "energia_gasta"),
            "rotas_inviaveis": sem_solucao,
            "taxa_inviavel": round(sem_solucao / (sem_solucao + len(grupo)), 3),
        })
    return resumo


def cruzar(linhas):
    """Paradas do guloso na rota do Dijkstra contra a melhor das outras rotas.

    E o ponto que liga os dois trabalhos: a rota mais barata tende a precisar
    de menos paradas, mas nao sempre, porque o guloso conta paradas e o
    Dijkstra minimiza custo. So entra destino em que as tres rotas tem
    solucao naquele tanque.
    """
    gulosas = [linha for linha in linhas if linha["estrategia"] == "guloso"]
    contagem = {}
    for (tamanho, seed, destino, alcance), grupo in agrupar(
        gulosas, ["tamanho", "seed", "destino", "alcance"]
    ).items():
        paradas = {linha["algoritmo"]: int(linha["paradas"]) for linha in grupo}
        if set(paradas) != set(ALGORITMOS):
            continue
        outras = min(valor for nome, valor in paradas.items() if nome != "dijkstra")
        item = contagem.setdefault((tamanho, alcance), {
            "tamanho": tamanho, "alcance": alcance, "destinos_comparados": 0,
            "dijkstra_menos_paradas": 0, "empates": 0, "dijkstra_mais_paradas": 0,
        })
        item["destinos_comparados"] += 1
        if paradas["dijkstra"] < outras:
            item["dijkstra_menos_paradas"] += 1
        elif paradas["dijkstra"] == outras:
            item["empates"] += 1
        else:
            item["dijkstra_mais_paradas"] += 1
    return list(contagem.values())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark de paradas de recarga (fase 5)")
    parser.add_argument("--tamanhos", type=int, nargs="+", default=list(TAMANHOS))
    parser.add_argument("--seeds", type=int, default=SEEDS)
    parser.add_argument("--destinos", type=int, default=DESTINOS_POR_MAPA)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args(argv)

    linhas, descartes = rodar(args.tamanhos, args.seeds, args.destinos)
    escrever_csv(args.saida / "paradas.csv", CAMPOS, linhas)
    escrever_csv(args.saida / "paradas_resumo.csv", CAMPOS_RESUMO, resumir(linhas, descartes))
    escrever_csv(args.saida / "paradas_descartes.csv", CAMPOS_DESCARTE, descartes)
    escrever_csv(args.saida / "paradas_cruzamento.csv", CAMPOS_CRUZAMENTO, cruzar(linhas))
    print(f"paradas: {len(linhas)} simulacoes, {len(descartes)} descartes -> {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
