"""API do trabalho 2 (fase 6): energia, Centros, recarga e viabilidade do alcance.

Funcoes puras, sem HTTP: `server.py` e so a casca. Nenhuma regra do jogo mora
aqui. O custo de entrar numa celula, o desmaio e a recarga vem de game.mover e
game.recarregar (que usam graph/cost.py, o mesmo peso do Dijkstra), e a
pergunta "esse tanque tem solucao?" vem de greedy.viabilidade. Esta camada so
abre esses resultados em JSON, pra a pagina apresentar sem recalcular nada.
"""

import functools
import json
import queue
from dataclasses import dataclass
from pathlib import Path
import random
import secrets
import threading

import game
import grid as grid_mod
from bench.common import ALGORITMOS, SEEDS, TAMANHOS, silencioso
from bench.partidas import novo_jogador
from bot.objectives import planejar_visita
from bot.runner import executar_bot
from graph import cost
from graph.cost import custo_entrada, custo_terreno
from graph.search import dijkstra
from graph.state import Estado
from greedy import marcos_da_rota
from greedy.estrategias import ESTRATEGIAS
from grid import Grid

from . import api

# Os tres presets de tanque sao multiplos do MENOR TANQUE QUE VENCE a missao
# (medido pela simulacao), nao fracoes do custo planejado. A versao anterior usava
# 30/50/75% do custo planejado, a mesma definicao do bench/paradas.py, mas aquela
# fracao vale pra UMA rota e a tela joga a missao inteira (varios destinos,
# batalhas, replanejamento): em 18 de 18 mapas vencidos nenhum dos tres niveis
# vencia, porque o minimo real e cerca de 2x o custo planejado. As fracoes do
# benchmark continuam valendo na pagina de Benchmark, onde medem rotas.
NIVEIS = {"abaixo": 0.75, "minimo": 1.0, "folgado": 1.5}

ENERGIA_MIN = 1
ENERGIA_MAX = 300
MAX_SESSOES = 20

# Onde webdemo/snapshot.py escreve. Importar dele traria o modulo de CSVs pra esta camada.
SNAPSHOT = Path(__file__).resolve().parent / "dados" / "benchmark.json"

ESTRATEGIA_PADRAO = "guloso"

_TEXTO_ESTRATEGIAS = {
    "guloso": ("Guloso", "Anda até o Centro mais distante que ainda alcança e só então para."),
    "todo_centro": ("Todo centro", "Para em cada Centro da rota, sem olhar o tanque."),
    "limiar_10": ("Limiar 10%", "Para no Centro quando a energia está em 10% do tanque ou menos."),
    "limiar_25": ("Limiar 25%", "Para no Centro quando a energia está em 25% do tanque ou menos."),
    "limiar_50": ("Limiar 50%", "Para no Centro quando a energia está em 50% do tanque ou menos."),
    "otimo": ("Ótimo (força bruta)", "Referência: o mínimo de paradas, testando todas as combinações."),
}


def config():
    return {
        "estrategias": [
            {"id": chave, "nome": _TEXTO_ESTRATEGIAS[chave][0],
             "descricao": _TEXTO_ESTRATEGIAS[chave][1]}
            for chave in ESTRATEGIAS
        ],
        "estrategia_padrao": ESTRATEGIA_PADRAO,
        "niveis": dict(NIVEIS),
        "energia_min": ENERGIA_MIN,
        "energia_max": ENERGIA_MAX,
        "tamanhos": list(TAMANHOS),
        "seeds": SEEDS,
        "meta": game.POKEMON_PARA_VENCER,
        # As constantes do custo de entrar, lidas de graph/cost.py: a dica da tela
        # mostra o custo de qualquer celula sem ter a regra copiada no navegador.
        # A grama depende do HP (3 a 6), por isso vai como faixa, nao como numero.
        "custos": {
            "terreno": {"concrete": cost.CUSTO_CONCRETO, "water": cost.CUSTO_AGUA},
            "grama": {"base": cost.CUSTO_GRAMA_BASE,
                      "cheio": cost.custo_grama(100), "ferido": cost.custo_grama(0)},
            "conteudo": {api.CONTEUDO[k]: v for k, v in cost.PENALIDADE_CONTEUDO.items()},
        },
    }


def benchmark():
    """O snapshot do benchmark (webdemo/snapshot.py), ou o motivo de nao haver."""
    if not SNAPSHOT.is_file():
        return {"erro": "sem snapshot: rode python -m webdemo.snapshot"}
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def limitar_energia(valor, padrao):
    return api.limitar(valor, ENERGIA_MIN, ENERGIA_MAX, padrao)


# ---------------------------------------------------------------------------
# Viabilidade do alcance
#
# A pergunta "esse tanque tem solucao?" e respondida pelo PROPRIO bot: a missao
# roda de verdade, numa copia, com o tanque escolhido. A primeira versao estimava
# sobre a rota do Dijkstra concatenada e errou (dizia "ha solucao" em 220 casos e
# so 40 venciam), porque o bot escolhe o proximo objetivo depois de chegar no
# anterior e segue com o tanque parcial. A simulacao e deterministica (mesma
# semeadura do benchmark) e custa de 30 a 90 ms. O menor tanque que vence sai por
# busca binaria, que SO e exata se a vitoria for monotona no tanque, e ela NAO e:
# medido em 11 mapas vencidos (8x8 e 15x15, seeds 0 a 11), em 8x8 seed 3 a busca
# acha 122 mas 23 tanques menores tambem vencem (o menor real e 46), e em 15x15
# seed 3 ha um tanque acima do minimo que perde. Causa provavel, nao verificada:
# o tanque muda as paradas, isso muda a ordem dos sorteios de batalha. Por isso o
# numero da busca e "o menor que a busca achou", e o que a tela pode afirmar sem
# medo e o `viavel` de cada tanque, que vem sempre de uma simulacao.
# O veredito e do guloso: ele acha solucao sempre que qualquer escolha de paradas
# acharia, entao "o guloso nao vence" e o mesmo que "nada vence".
# ---------------------------------------------------------------------------

VITORIA = "quatro pokemon capturados"

# random e global: simulacao, stream e passo do jogo humano disputam a mesma
# semente. Sem a trava, o slider de alcance desorganizaria uma partida ao vivo.
_TRANCA_RNG = threading.Lock()
# Uma simulacao leva de 30 a 90 ms e uma partida ao vivo, poucos segundos; passar
# disso e trava vazada, nao fila.
TEMPO_MAX_TRANCA = 60


@dataclass(frozen=True)
class ResultadoMissao:
    venceu: bool
    motivo: str
    objetivos: int
    pokemon: int
    passos: int
    paradas: int
    energia_desperdicada: int


@functools.lru_cache(maxsize=2048)
def simular_missao(size, seed, tanque, estrategia="guloso"):
    """Roda a missao inteira do bot com esse tanque e resume como terminou."""
    with _TRANCA_RNG:
        random.seed(f"{size}-{seed}")
        mapa = Grid(size=size, seed=seed)
        jogador = novo_jogador()
        jogador.energia = jogador.energia_max = tanque
        with silencioso():
            r = executar_bot(mapa, jogador, max_passos=10 * size * size,
                             estrategia=ESTRATEGIAS[estrategia])
    return ResultadoMissao(
        venceu=r.motivo_parada == VITORIA,
        motivo=r.motivo_parada,
        objetivos=len(r.objetivos_visitados),
        pokemon=len(jogador.pokemon_list),
        passos=len(r.movimentos),
        paradas=r.paradas,
        energia_desperdicada=r.energia_desperdicada,
    )


@functools.lru_cache(maxsize=256)
def menor_tanque(size, seed):
    """(menor tanque que cumpre a missao, "") ou (None, motivo) se nenhum cumpre.

    Nenhum cumpre quando o proprio Trabalho 1 nao vence o mapa (a origem nasce
    cercada, ou o time cai numa batalha): com energia farta o resultado e o do
    T1, e a energia nao tem o que resolver.
    """
    teto = simular_missao(size, seed, ENERGIA_MAX)
    if not teto.venceu:
        return None, teto.motivo
    baixo, alto = ENERGIA_MIN, ENERGIA_MAX
    while baixo < alto:
        meio = (baixo + alto) // 2
        if simular_missao(size, seed, meio).venceu:
            alto = meio
        else:
            baixo = meio + 1
    return baixo, ""


@functools.lru_cache(maxsize=64)
def _missao(size, seed):
    """Objetivos e custo PLANEJADOS a partir do estado inicial (so estimativa).

    Serve pra dar escala aos niveis curto/medio/longo, que sao fracoes do custo
    da missao como no benchmark. Quem decide se um tanque vence e a simulacao.
    """
    mapa = Grid(size=size, seed=seed)
    estado = api.estado_de(100, False)
    ordem, _, _ = planejar_visita(mapa.posicao, mapa, estado, limite=game.POKEMON_PARA_VENCER)
    caminho = [mapa.posicao]
    atual = mapa.posicao
    for alvo in ordem:
        trecho, _, _ = dijkstra(atual, alvo, mapa, estado)
        if not trecho:
            break
        caminho.extend(trecho[1:])
        atual = alvo
    marcos = marcos_da_rota(caminho, mapa, estado)
    return tuple(caminho), tuple(marcos), tuple(ordem)


def _veredito(size, seed, tanque, minimo):
    sim = simular_missao(size, seed, tanque)
    return {
        "alcance": tanque,
        "viavel": sim.venceu,
        "folga": None if minimo is None else tanque - minimo,
        "motivo": "" if sim.venceu else sim.motivo,
        # `objetivos` conta destinos visitados (pokemon, itens, replanejos);
        # `pokemon` e o tamanho do time, o que a vitoria mede ("2 de 4").
        "objetivos": sim.objetivos,
        "pokemon": sim.pokemon,
        "meta": game.POKEMON_PARA_VENCER,
        "paradas": sim.paradas,
        "energia_desperdicada": sim.energia_desperdicada,
    }


def dados_alcance(size, seed, alcance=None):
    """Os presets de tanque pra missao deste mapa e, se pedido, um alcance livre.

    Cada tanque traz `viavel` (o bot cumpre a missao com ele), `folga` (negativa
    = quanto falta pro menor tanque que vence) e, quando nao cumpre, o motivo.
    Os presets (`NIVEIS`) sao multiplos do menor tanque que vence; num mapa que
    nem o T1 vence nao existe esse minimo, entao `niveis` vem vazio e a tela diz
    `motivo_sem_solucao`.
    """
    _, marcos, objetivos = _missao(size, seed)
    custo = marcos[-1][0]
    minimo, motivo_sem_solucao = menor_tanque(size, seed)

    niveis = {}
    if minimo is not None:
        for nome, fator in NIVEIS.items():
            tanque = max(ENERGIA_MIN, min(ENERGIA_MAX, round(minimo * fator)))
            if fator < 1 and tanque >= minimo:
                # tanque de 1 ou 2: nao ha "abaixo do minimo" inteiro e valido
                continue
            niveis[nome] = {"fator": fator, **_veredito(size, seed, tanque, minimo)}

    # O tanque de partida: o minimo exato, que vence sem sobrar nada; se o mapa
    # nao tem solucao, tanque cheio, que reproduz o T1 (a energia nao resolve).
    recomendado = minimo if minimo is not None else ENERGIA_MAX

    saida = {
        "size": size,
        "seed": seed,
        "objetivos": [list(p) for p in objetivos],
        "custo_missao": custo,
        "centros_na_missao": sum(1 for i in range(1, len(marcos) - 1) if marcos[i][1]),
        "menor_tanque": minimo,
        "motivo_sem_solucao": motivo_sem_solucao,
        "recomendado": recomendado,
        "niveis": niveis,
    }
    if alcance is not None:
        tanque = limitar_energia(alcance, recomendado)
        saida["escolhido"] = _veredito(size, seed, tanque, minimo)
    return saida


# ---------------------------------------------------------------------------
# Modo humano com energia
#
# Mesmo desenho da sessao do trabalho 1: o servidor guarda a partida porque
# quem resolve um passo e game.mover(), e ele muda grid, HP, energia e batalha.
# Reescrever isso no navegador seria duplicar a regra do jogo, que e o que este
# pacote nao faz. Vive em memoria e morre com o processo.
# ---------------------------------------------------------------------------

_sessoes: dict[str, dict] = {}
_tranca = threading.Lock()


def _nova_sessao(mapa, jogador):
    identificador = secrets.token_hex(8)
    with _tranca:
        if len(_sessoes) >= MAX_SESSOES:
            # a mais antiga sai; ninguem volta pra uma partida abandonada
            _sessoes.pop(next(iter(_sessoes)))
        _sessoes[identificador] = {"mapa": mapa, "player": jogador, "tranca": threading.Lock()}
    return identificador


def _obter(identificador):
    with _tranca:
        return _sessoes.get(identificador)


def _resumo(player):
    return {
        **api._resumo_jogador(player),
        "energia": player.energia,
        "energia_max": player.energia_max,
    }


def _custo(terreno, total):
    return {"terreno": terreno, "conteudo": total - terreno, "total": total}


def _vizinhas(mapa, player):
    """O que custaria dar um passo em cada direcao, SEM dar.

    E o aviso que a tela mostra ao passar o mouse numa celula vizinha, e so
    vale se nao mentir: usa as mesmas funcoes de custo que game.mover usa, na
    mesma ordem de checagem (dentro do mapa, acessivel, pisavel).
    """
    estado = Estado.de(player)
    saida = {}
    for tecla, (d_linha, d_coluna) in game.DIRECOES.items():
        linha, coluna = mapa.row_pos + d_linha, mapa.col_pos + d_coluna
        item = {"posicao": [linha, coluna], "valido": False, "motivo": "", "custo": None,
                "desmaia": False, "sobram": None, "conteudo": None}
        if not mapa.dentro(linha, coluna):
            item["motivo"] = "fora do mapa"
        else:
            celula = mapa.celula(linha, coluna)
            item["conteudo"] = api.CONTEUDO.get(celula.occupied_with, "livre")
            if not celula.acessivel:
                item["motivo"] = "celula inacessivel"
            elif not celula.pisavel(player.surf):
                item["motivo"] = "agua sem surf"
            else:
                total = custo_entrada(celula, estado)
                desmaia = total > player.energia
                item.update(
                    valido=True,
                    custo=_custo(custo_terreno(celula, estado), total),
                    desmaia=desmaia,
                    sobram=None if desmaia else player.energia - total,
                )
        saida[tecla] = item
    return saida


def criar_jogo(size, seed, energia=None):
    mapa = Grid(size=size, seed=seed)
    tanque = limitar_energia(energia, dados_alcance(size, seed)["recomendado"])
    jogador = novo_jogador()
    jogador.energia = jogador.energia_max = tanque
    identificador = _nova_sessao(mapa, jogador)
    return {
        "sessao": identificador,
        **api.serializar_grid(mapa),
        "centros": [list(p) for p in mapa.centros()],
        "jogador": _resumo(jogador),
        "vizinhas": _vizinhas(mapa, jogador),
        "alcance": dados_alcance(size, seed, tanque),
    }


def estado_jogo(identificador):
    sessao = _obter(identificador)
    if sessao is None:
        return {"erro": "sessao desconhecida, comece uma partida nova"}
    mapa, jogador = sessao["mapa"], sessao["player"]
    return {
        "sessao": identificador,
        "posicao": list(mapa.posicao),
        "jogador": _resumo(jogador),
        "vizinhas": _vizinhas(mapa, jogador),
    }


def mover_jogo(identificador, direcao):
    sessao = _obter(identificador)
    if sessao is None:
        return {"erro": "sessao desconhecida, comece uma partida nova"}
    direcao = (direcao or "").upper()

    with sessao["tranca"]:
        mapa, jogador = sessao["mapa"], sessao["player"]
        situacao, motivo = api._situacao(jogador)
        if situacao != "jogando":
            return {"erro": f"partida encerrada ({motivo}), comece uma nova"}

        energia_antes = jogador.energia
        # O conteudo da celula de destino ANTES do passo: depois dele a celula
        # vira "visitado" e a tela nao saberia dizer com o que o jogador bateu.
        destino = None
        if direcao in game.DIRECOES:
            d_linha, d_coluna = game.DIRECOES[direcao]
            if mapa.dentro(mapa.row_pos + d_linha, mapa.col_pos + d_coluna):
                destino = mapa.celula(mapa.row_pos + d_linha, mapa.col_pos + d_coluna)
        conteudo = api.CONTEUDO.get(destino.occupied_with, "livre") if destino else None

        # automatico=True mesmo com humano no teclado: battle() le do stdin e
        # penduraria a conexao. Quem anda e a pessoa; o combate resolve sozinho.
        with silencioso():
            movimento = game.mover(mapa, jogador, direcao, automatico=True)

        total = movimento.custo_terreno + movimento.custo_conteudo
        linha, coluna = movimento.posicao
        return {
            "valido": movimento.valido,
            "motivo": movimento.motivo,
            "posicao": [linha, coluna],
            "conteudo": conteudo,
            "batalhou": movimento.batalhou,
            "pegou_pokebola": movimento.pegou_pokebola,
            "pegou_surf": movimento.pegou_surf,
            "hp_perdido": movimento.hp_perdido,
            "em_centro": movimento.em_centro,
            "desmaiou": movimento.desmaiou,
            "custo": _custo(movimento.custo_terreno, total) if total else None,
            "energia_gasta": movimento.energia_gasta,
            "energia_antes": energia_antes,
            "energia_depois": jogador.energia,
            "faltaram": total - energia_antes if movimento.desmaiou else 0,
            "celula": {"posicao": [linha, coluna],
                       **api.serializar_celula(mapa.celula(linha, coluna))},
            "vizinhas": _vizinhas(mapa, jogador),
            "jogador": _resumo(jogador),
        }


def recarregar_jogo(identificador):
    sessao = _obter(identificador)
    if sessao is None:
        return {"erro": "sessao desconhecida, comece uma partida nova"}

    with sessao["tranca"]:
        mapa, jogador = sessao["mapa"], sessao["player"]
        situacao, motivo = api._situacao(jogador)
        if situacao != "jogando":
            return {"erro": f"partida encerrada ({motivo}), comece uma nova"}

        antes = jogador.energia
        if mapa.celula(*mapa.posicao).occupied_with != grid_mod.CENTRO:
            motivo_recusa = "sem centro aqui"
        elif antes >= jogador.energia_max:
            motivo_recusa = "tanque cheio"
        else:
            motivo_recusa = ""

        entrou = 0 if motivo_recusa else game.recarregar(mapa, jogador)
        return {
            "recarregou": not motivo_recusa,
            "motivo": motivo_recusa,
            "entrou": entrou,
            "sobrava": antes,
            "posicao": list(mapa.posicao),
            "vizinhas": _vizinhas(mapa, jogador),
            "jogador": _resumo(jogador),
        }


# ---------------------------------------------------------------------------
# Bot ao vivo
#
# O bot roda numa thread e empurra os eventos pelos ganchos do runner. Nao ha
# replay: o passo chega na pagina depois de game.mover() ter sido chamado de
# verdade, e a recarga depois de game.recarregar(). A sequencia de cada plano e
# `plano`, `paradas`, varios `passo` e, se a estrategia mandou parar, uma
# `recarga`. Como o bot so escolhe o proximo objetivo depois de chegar no
# anterior, a regua da tela cresce a cada plano (decisao D3), e os contadores
# nao tem total: ele nao existe de antemao.
# ---------------------------------------------------------------------------


def eventos_partida(size, seed, algoritmo, energia, estrategia, max_passos=None):
    """Gera os eventos de uma partida do bot com energia ENQUANTO ela acontece.

    `estrategia` e uma chave de greedy.estrategias.ESTRATEGIAS, ou None pra o
    bot andar a rota inteira como no trabalho 1 (e desmaiar, se o tanque nao der).
    """
    if algoritmo not in ALGORITMOS:
        raise ValueError(f"algoritmo desconhecido: {algoritmo}")
    if estrategia is not None and estrategia not in ESTRATEGIAS:
        raise ValueError(f"estrategia desconhecida: {estrategia}")

    # dados_alcance roda a missao inteira quando o cache esta frio, e simular_missao
    # reseeda e consome o random global. Por isso vem ANTES da semeadura abaixo: com
    # ela antes, a 1a chamada (cache frio) e a 2a (cache quente) largavam de estados
    # de RNG diferentes e a mesma partida tinha batalhas diferentes.
    tanque = limitar_energia(energia, dados_alcance(size, seed)["recomendado"])
    alcance = dados_alcance(size, seed, tanque)

    # A trava do RNG cobre do seed ate o ultimo passo do bot. As batalhas, o inicial
    # sorteado e o redirect_stdout de silencioso() sao estado GLOBAL: sem ela, um
    # pedido de alcance (simular_missao) no meio da partida reseedaria o random e
    # mudaria o que o bot vive. Quem solta e a thread do bot, no `finally`, e ela
    # e iniciada ANTES do primeiro yield: se o cliente fechar a aba, nao sobra
    # trava orfa travando o slider de todo mundo. Cliente lento tambem nao a
    # segura: o bot enche a fila na velocidade dele, nao na da tela.
    fila: queue.Queue = queue.Queue()
    # Com timeout de proposito: uma trava vazada travaria o servidor inteiro em
    # silencio. Assim vira um erro que a pagina mostra.
    if not _TRANCA_RNG.acquire(timeout=TEMPO_MAX_TRANCA):
        raise RuntimeError("outra simulacao segura o gerador de sorteio ha tempo demais")
    try:
        # A mesma semeadura da partida medida no benchmark (bench/partidas.py): o
        # que aparece na tela e reproduzivel, batalha por batalha.
        random.seed(f"{size}-{seed}")
        mapa = Grid(size=size, seed=seed)
        jogador = novo_jogador()
        jogador.energia = jogador.energia_max = tanque
        fila.put(("inicio", {
            **api.serializar_grid(mapa),
            "centros": [list(p) for p in mapa.centros()],
            "algoritmo": algoritmo,
            "estrategia": estrategia,
            "jogador": _resumo(jogador),
            "alcance": alcance,
        }))
    except BaseException:
        _TRANCA_RNG.release()
        raise

    # O que havia em cada celula ANTES de o bot passar: depois do passo ela vira
    # "visitado" e o evento nao saberia dizer com o que o bot bateu.
    conteudos: dict[tuple, str] = {}
    corrente = {"energia": tanque}

    rota_corrente: list = []

    def ao_planejar(destino, caminho, custo, nos):
        rota_corrente[:] = [list(p) for p in caminho]
        for posicao in caminho:
            conteudos.setdefault(posicao, api.CONTEUDO.get(
                mapa.celula(*posicao).occupied_with, "livre"))
        fila.put(("plano", {
            "destino": list(destino),
            "caminho": [list(p) for p in caminho],
            "custo": custo,
            "nos_expandidos": nos,
        }))

    def ao_paradas(marcos, escolhidas):
        fila.put(("paradas", {
            "marcos": [[custo, bool(centro)] for custo, centro in marcos],
            "escolhidas": None if escolhidas is None else list(escolhidas),
            "sem_solucao": escolhidas is None,
            "posicoes": [] if escolhidas is None else [rota_corrente[i] for i in escolhidas],
        }))

    def ao_passo(movimento, direcao):
        total = movimento.custo_terreno + movimento.custo_conteudo
        antes = corrente["energia"]
        depois = jogador.energia
        corrente["energia"] = depois
        fila.put(("passo", {
            "direcao": direcao,
            "posicao": list(movimento.posicao),
            "valido": movimento.valido,
            "motivo": movimento.motivo,
            "batalhou": movimento.batalhou,
            "pegou_pokebola": movimento.pegou_pokebola,
            "pegou_surf": movimento.pegou_surf,
            "hp_perdido": movimento.hp_perdido,
            "em_centro": movimento.em_centro,
            "desmaiou": movimento.desmaiou,
            "conteudo": conteudos.get(tuple(_alvo_do_passo(mapa, movimento, direcao))),
            "custo": _custo(movimento.custo_terreno, total) if total else None,
            "energia_gasta": movimento.energia_gasta,
            "energia_antes": antes,
            "energia_depois": depois,
            "faltaram": total - antes if movimento.desmaiou else 0,
            "jogador": _resumo(jogador),
        }))

    def ao_recarga(posicao, entrou, sobrava):
        corrente["energia"] = jogador.energia
        fila.put(("recarga", {
            "posicao": list(posicao),
            "entrou": entrou,
            "sobrava": sobrava,
            "energia_max": jogador.energia_max,
            "jogador": _resumo(jogador),
        }))

    resultado = {}

    def rodar():
        try:
            with silencioso():
                r = executar_bot(
                    mapa, jogador,
                    max_passos=max_passos or 10 * size * size,
                    buscar=ALGORITMOS[algoritmo],
                    ao_planejar=ao_planejar,
                    ao_passo=ao_passo,
                    estrategia=ESTRATEGIAS.get(estrategia),
                    ao_paradas=ao_paradas,
                    ao_recarga=ao_recarga,
                )
            resultado["fim"] = {
                "algoritmo": algoritmo,
                "estrategia": estrategia,
                "objetivos_concluidos": len(r.objetivos_visitados),
                "objetivos": [list(p) for p in r.objetivos_visitados],
                "pokemon": len(jogador.pokemon_list),
                "meta": game.POKEMON_PARA_VENCER,
                "passos": len(r.movimentos),
                "custo_planejado": r.custo_planejado,
                "nos_expandidos": r.nos_expandidos,
                "replanejamentos": r.replanejamentos,
                "batalhas": sum(1 for m in r.movimentos if m.batalhou),
                "hp_perdido": sum(m.hp_perdido for m in r.movimentos),
                "paradas": r.paradas,
                "energia_desperdicada": r.energia_desperdicada,
                "motivo_parada": r.motivo_parada,
                "jogador": _resumo(jogador),
            }
        except Exception as erro:  # a pagina precisa saber, nao ficar girando
            resultado["fim"] = {"algoritmo": algoritmo, "estrategia": estrategia, "erro": repr(erro)}
        finally:
            _TRANCA_RNG.release()
            fila.put((None, None))

    thread = threading.Thread(target=rodar, daemon=True)
    thread.start()
    while True:
        evento, dados = fila.get()
        if evento is None:
            break
        yield evento, dados
    thread.join()
    yield "fim", resultado["fim"]


class _Indisponivel(Exception):
    """A estrategia nao pode rodar nesta rota (o otimo acima de 20 centros)."""


def _tolerante(estrategia):
    def envolvida(*args, **kwargs):
        try:
            return estrategia(*args, **kwargs)
        except ValueError as erro:
            raise _Indisponivel(str(erro)) from erro
    return envolvida


def _raia(size, seed, tanque, algoritmo, chave):
    """Uma execucao real do bot com UMA estrategia e a linha do tempo dela.

    A linha do tempo sai dos ganchos do proprio bot: nada aqui recalcula custo,
    recarga ou desmaio. `c` e o custo acumulado (energia gasta ate ali), o eixo
    da regua. Tipos: `centro` (passou direto), `parada` (recarregou, com o que
    sobrava no tanque), `captura` (o time cresceu) e `desmaio`.
    """
    nome, descricao = _TEXTO_ESTRATEGIAS[chave]
    base = {"estrategia": chave, "nome": nome, "descricao": descricao}
    random.seed(f"{size}-{seed}")
    mapa = Grid(size=size, seed=seed)
    jogador = novo_jogador()
    jogador.energia = jogador.energia_max = tanque
    linha: list[dict] = []
    custo = {"c": 0, "time": len(jogador.pokemon_list)}

    def ao_passo(movimento, direcao):
        if movimento.desmaiou:
            linha.append({"c": custo["c"], "tipo": "desmaio"})
            return
        if not movimento.valido:
            return
        custo["c"] += movimento.energia_gasta
        if len(jogador.pokemon_list) > custo["time"]:
            custo["time"] = len(jogador.pokemon_list)
            linha.append({"c": custo["c"], "tipo": "captura"})
        if movimento.em_centro:
            linha.append({"c": custo["c"], "tipo": "centro"})

    def ao_recarga(posicao, entrou, sobrava):
        # a parada acontece no Centro em que o passo anterior acabou de chegar
        for marco in reversed(linha):
            if marco["tipo"] == "centro":
                marco["tipo"] = "parada"
                marco["sobrava"] = sobrava
                break

    estrategia = ESTRATEGIAS[chave]
    if chave == "otimo":
        estrategia = _tolerante(estrategia)
    try:
        with silencioso():
            r = executar_bot(
                mapa, jogador, max_passos=10 * size * size, buscar=ALGORITMOS[algoritmo],
                estrategia=estrategia, ao_passo=ao_passo, ao_recarga=ao_recarga,
            )
    except _Indisponivel as erro:
        return {**base, "disponivel": False, "motivo_indisponivel": str(erro)}

    venceu = r.motivo_parada == VITORIA
    desmaio = next((m["c"] for m in linha if m["tipo"] == "desmaio"), None)
    return {
        **base,
        "disponivel": True,
        "venceu": venceu,
        "motivo": "" if venceu else r.motivo_parada,
        "pokemon": len(jogador.pokemon_list),
        "meta": game.POKEMON_PARA_VENCER,
        "paradas": r.paradas,
        "energia_desperdicada": r.energia_desperdicada,
        "passos": len(r.movimentos),
        "custo_total": custo["c"],
        "desmaio_em": desmaio,
        "linha": linha,
    }


@functools.lru_cache(maxsize=64)
def _comparar(size, seed, tanque, algoritmo):
    if not _TRANCA_RNG.acquire(timeout=TEMPO_MAX_TRANCA):
        raise RuntimeError("outra simulacao segura o gerador de sorteio ha tempo demais")
    try:
        raias = [_raia(size, seed, tanque, algoritmo, chave) for chave in ESTRATEGIAS]
    finally:
        _TRANCA_RNG.release()

    chegam = [r for r in raias if r["disponivel"] and r["venceu"]]
    menos = min((r["paradas"] for r in chegam), default=None)
    return {
        "size": size,
        "seed": seed,
        "algoritmo": algoritmo,
        "alcance": tanque,
        "meta": game.POKEMON_PARA_VENCER,
        "raias": raias,
        "veredito": {
            "menos_paradas": menos,
            "vencedoras": [r["estrategia"] for r in chegam if r["paradas"] == menos],
            "falharam": [r["estrategia"] for r in raias if r["disponivel"] and not r["venceu"]],
            "indisponiveis": [r["estrategia"] for r in raias if not r["disponivel"]],
        },
    }


def comparar(size, seed, energia=None, algoritmo="dijkstra"):
    """As seis estrategias jogando a MESMA missao, lado a lado (decisao do Lucas).

    Cada raia e uma execucao real do bot, nao a rota planejada concatenada: o bot
    escolhe o proximo objetivo depois de chegar no anterior, e a versao
    concatenada ja prometeu solucao em 220 casos dos quais so 40 venciam. O
    resultado vai pro cache (uma chamada custa de 0,1 a 1,2 s por raia).
    """
    if algoritmo not in ALGORITMOS:
        raise ValueError(f"algoritmo desconhecido: {algoritmo}")
    tanque = limitar_energia(energia, dados_alcance(size, seed)["recomendado"])
    return _comparar(size, seed, tanque, algoritmo)


def _alvo_do_passo(mapa, movimento, direcao):
    """A celula que o passo tentou pisar (a posicao, se ele foi valido)."""
    if movimento.valido:
        return movimento.posicao
    d_linha, d_coluna = game.DIRECOES[direcao]
    return (movimento.posicao[0] + d_linha, movimento.posicao[1] + d_coluna)
