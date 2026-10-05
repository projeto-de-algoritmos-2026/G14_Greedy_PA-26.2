"""Snapshot JSON do benchmark, gerado dos CSVs consolidados de `bench/out/`.

    python -m webdemo.snapshot          # escreve webdemo/dados/benchmark.json

A pagina de Benchmark nao calcula nada: ela desenha o que este arquivo traz.
Os CSVs sao a fonte (estao no git, adicionados a forca apesar do .gitignore);
o JSON existe por ser mais leve de carregar no navegador e por carregar a data
e o commit de onde saiu, pra tela poder dizer "medido em tal commit".

Duas fontes, dois contratos:
- Trabalho 2: `paradas_resumo.csv` e `paradas_cruzamento.csv`, no formato da
  fase 5 (`docs/contrato-benchmark.md`). As cinco premissas do contrato sao
  CONFERIDAS aqui a cada geracao; se uma quebrar, o snapshot nao e escrito.
- Trabalho 1: `rotas.csv` e `partidas_resumo.csv`. A tabela do README do T1 e a
  media de `rotas.csv` com `estado == hp100` (HP cheio, sem Surf), por tamanho e
  algoritmo. O filtro vem de reproduzir a tabela do README (medido em 05/10).
"""

import argparse
import csv
import datetime
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = Path(__file__).resolve().parent / "dados" / "benchmark.json"
PASTA_CSV = RAIZ / "bench" / "out"

ESTADO_DO_README = "hp100"
ALCANCES = ("curto", "medio", "longo")
TAMANHOS = (8, 15, 30)
ALGORITMOS = ("dfs", "bfs", "dijkstra")


class ContratoQuebrado(ValueError):
    """Um CSV deixou de ter o formato que a tela assume."""


def ler(nome):
    caminho = PASTA_CSV / nome
    if not caminho.is_file():
        raise ContratoQuebrado(f"falta {nome} em {PASTA_CSV} (rode: python -m bench)")
    with caminho.open(newline="", encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def _numero(texto):
    valor = float(texto)
    return int(valor) if valor.is_integer() and "." not in texto else valor


# ---------------------------------------------------------------------------
# Trabalho 2
# ---------------------------------------------------------------------------

def validar_resumo(linhas):
    """As cinco premissas de docs/contrato-benchmark.md, nas linhas do resumo."""
    if not linhas:
        raise ContratoQuebrado("paradas_resumo.csv vazio")
    for l in linhas:
        if int(l["chegadas"]) + int(l["desmaios"]) != int(l["execucoes"]):
            raise ContratoQuebrado(f"chegadas + desmaios != execucoes em {_chave(l)}")
        if l["alcance"] not in ALCANCES:
            raise ContratoQuebrado(f"alcance desconhecido: {l['alcance']!r}")
        viaveis, inviaveis = int(l["execucoes"]), int(l["rotas_inviaveis"])
        total = viaveis + inviaveis
        esperado = inviaveis / total if total else 0.0
        if not math.isclose(float(l["taxa_inviavel"]), esperado, abs_tol=1e-3):
            raise ContratoQuebrado(f"taxa_inviavel inconsistente em {_chave(l)}")

    # guloso e otimo tem o mesmo numero de paradas e nenhum dos dois desmaia. A
    # premissa e POR PAR (seed, destino, alcance, algoritmo), nao sobre as medias
    # do resumo: o otimo so roda em rotas com ate 20 centros, entao as medias do
    # resumo vem de conjuntos de rotas diferentes (71 vs 67 execucoes em
    # 30x30/longo/dfs) e nao sao comparaveis. Medido: 1.179 pares, 0 divergentes.
    validar_pares(ler("paradas.csv"))


def validar_pares(linhas):
    por_par = defaultdict(dict)
    for l in linhas:
        chave = (l["tamanho"], l["seed"], l["destino"], l["alcance"], l["algoritmo"])
        por_par[chave][l["estrategia"]] = l
    comparados = 0
    for chave, estrategias in por_par.items():
        if "guloso" in estrategias and "otimo" in estrategias:
            comparados += 1
            g, o = estrategias["guloso"], estrategias["otimo"]
            if g["paradas"] != o["paradas"]:
                raise ContratoQuebrado(f"guloso e otimo divergem em {chave}")
            if g["chegou"] != "1" or o["chegou"] != "1":
                raise ContratoQuebrado(f"guloso ou otimo nao chegou em {chave}")
    if not comparados:
        raise ContratoQuebrado("paradas.csv sem nenhum par guloso/otimo")
    return comparados


def _chave(linha):
    return (linha["tamanho"], linha["alcance"], linha["algoritmo"], linha["estrategia"])


def trabalho_2():
    resumo = ler("paradas_resumo.csv")
    validar_resumo(resumo)
    cruzamento = ler("paradas_cruzamento.csv")

    linhas = [{
        "tamanho": int(l["tamanho"]),
        "alcance": l["alcance"],
        "algoritmo": l["algoritmo"],
        "estrategia": l["estrategia"],
        "execucoes": int(l["execucoes"]),
        "chegadas": int(l["chegadas"]),
        "desmaios": int(l["desmaios"]),
        "taxa_desmaio": float(l["taxa_desmaio"]),
        "paradas_medio": float(l["paradas_medio"]),
        "energia_desperdicada_medio": float(l["energia_desperdicada_medio"]),
        "energia_gasta_medio": float(l["energia_gasta_medio"]),
        "rotas_inviaveis": int(l["rotas_inviaveis"]),
        "taxa_inviavel": float(l["taxa_inviavel"]),
    } for l in resumo]

    cruz = [{
        "tamanho": int(l["tamanho"]),
        "alcance": l["alcance"],
        "destinos_comparados": int(l["destinos_comparados"]),
        "dijkstra_menos_paradas": int(l["dijkstra_menos_paradas"]),
        "empates": int(l["empates"]),
        "dijkstra_mais_paradas": int(l["dijkstra_mais_paradas"]),
    } for l in cruzamento]
    for c in cruz:
        soma = c["dijkstra_menos_paradas"] + c["empates"] + c["dijkstra_mais_paradas"]
        if soma != c["destinos_comparados"]:
            raise ContratoQuebrado(f"cruzamento nao fecha em {c['tamanho']}/{c['alcance']}")

    return {
        "estrategias": sorted({l["estrategia"] for l in linhas}),
        "linhas": linhas,
        "cruzamento": cruz,
    }


# ---------------------------------------------------------------------------
# Trabalho 1
# ---------------------------------------------------------------------------

def _media(valores):
    valores = list(valores)
    return sum(valores) / len(valores)


def trabalho_1():
    rotas = ler("rotas.csv")
    grupos = defaultdict(list)
    for l in rotas:
        if l["estado"] == ESTADO_DO_README and l["encontrou"] == "1":
            grupos[(int(l["tamanho"]), l["algoritmo"])].append(l)
    rota = [{
        "tamanho": tam,
        "algoritmo": alg,
        "rotas": len(g),
        "custo_medio": _media(float(x["custo"]) for x in g),
        "passos_medio": _media(float(x["passos"]) for x in g),
        "nos_expandidos_medio": _media(float(x["nos_expandidos"]) for x in g),
    } for (tam, alg), g in sorted(grupos.items())]

    partidas = [{
        "tamanho": int(l["tamanho"]),
        "algoritmo": l["algoritmo"],
        "execucoes": int(l["execucoes"]),
        "objetivos_medio": float(l["objetivos_medio"]),
        "passos_medio": float(l["passos_medio"]),
        "batalhas_medio": float(l["batalhas_medio"]),
        "hp_perdido_medio": float(l["hp_perdido_medio"]),
    } for l in ler("partidas_resumo.csv")]

    return {"filtro_rota": f"estado == {ESTADO_DO_README}", "rota": rota, "partida": partidas}


# ---------------------------------------------------------------------------

def _commit():
    try:
        saida = subprocess.run(["git", "-C", str(RAIZ), "log", "-1", "--format=%h"],
                               capture_output=True, text=True, timeout=10, check=True)
        return saida.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def gerar():
    return {
        "gerado_em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": _commit(),
        "fonte": "bench/out/*.csv",
        "tamanhos": list(TAMANHOS),
        "algoritmos": list(ALGORITMOS),
        "alcances": list(ALCANCES),
        "t1": trabalho_1(),
        "t2": trabalho_2(),
    }


def escrever(caminho=SAIDA):
    dados = gerar()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return caminho, dados


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera o snapshot JSON do benchmark")
    parser.add_argument("--saida", type=Path, default=SAIDA)
    args = parser.parse_args(argv)
    caminho, dados = escrever(args.saida)
    try:
        mostrado = caminho.relative_to(RAIZ)
    except ValueError:
        mostrado = caminho
    print(f"{mostrado}: {len(dados['t2']['linhas'])} linhas do T2, "
          f"{len(dados['t1']['rota'])} do T1 (commit {dados['commit']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
