"""Viabilidade do alcance pela simulacao da missao real (fase 6, D5 revisado).

A primeira versao estimava a viabilidade sobre a rota do Dijkstra concatenada e
errou: dizia "ha solucao" em 220 casos e so 40 venciam de verdade, porque o bot
escolhe o proximo objetivo depois de chegar no anterior e segue com o tanque
parcial. Agora a resposta vem do proprio bot, rodando a missao com o tanque
escolhido. Estes testes travam a propriedade que importa: a tela nunca promete
uma vitoria que o bot nao entrega.
"""
import random

import pytest

import game
from bench.common import silencioso
from bench.partidas import novo_jogador
from bot.runner import executar_bot
from greedy.estrategias import ESTRATEGIAS
from grid import Grid
from webdemo import api_greedy as api

VITORIA = "quatro pokemon capturados"


def jogar_de_novo(size, seed, tanque, estrategia="guloso"):
    """Execucao independente, do jeito do benchmark: a referencia da simulacao."""
    random.seed(f"{size}-{seed}")
    mapa = Grid(size=size, seed=seed)
    jogador = novo_jogador()
    jogador.energia = jogador.energia_max = tanque
    with silencioso():
        return executar_bot(mapa, jogador, max_passos=10 * size * size,
                            estrategia=ESTRATEGIAS[estrategia])


def time_final(size, seed, tanque, estrategia="guloso"):
    """Tamanho do time ao fim de uma execucao independente (referencia do campo `pokemon`)."""
    random.seed(f"{size}-{seed}")
    mapa = Grid(size=size, seed=seed)
    jogador = novo_jogador()
    jogador.energia = jogador.energia_max = tanque
    with silencioso():
        executar_bot(mapa, jogador, max_passos=10 * size * size,
                     estrategia=ESTRATEGIAS[estrategia])
    return len(jogador.pokemon_list)


def mapas_vencidos(tamanhos=(8,), seeds=range(20)):
    """Mapas em que o T1 vence (energia farta), onde a pergunta faz sentido."""
    return [(s, seed) for s in tamanhos for seed in seeds
            if api.simular_missao(s, seed, api.ENERGIA_MAX).venceu]


class TestSimularMissao:
    def test_igual_a_uma_execucao_independente(self):
        for size, seed, tanque in [(8, 3, 34), (8, 11, 45), (15, 2, 60), (8, 0, 20)]:
            sim = api.simular_missao(size, seed, tanque)
            real = jogar_de_novo(size, seed, tanque)
            assert (sim.motivo, sim.paradas, sim.energia_desperdicada, sim.passos,
                    sim.objetivos) == (real.motivo_parada, real.paradas,
                                       real.energia_desperdicada, len(real.movimentos),
                                       len(real.objetivos_visitados))
            assert sim.venceu == (real.motivo_parada == VITORIA)

    def test_energia_farta_reproduz_o_trabalho_1(self):
        """Quando a energia sobra, a missao termina como no T1: a energia so
        atrapalha quando falta."""
        for seed in range(10):
            farta = api.simular_missao(8, seed, api.ENERGIA_MAX)
            random.seed(f"8-{seed}")
            mapa, jogador = Grid(size=8, seed=seed), novo_jogador()
            with silencioso():
                t1 = executar_bot(mapa, jogador, max_passos=640)
            assert farta.motivo == t1.motivo_parada

    def test_e_deterministica(self):
        assert api.simular_missao(8, 3, 34) == api.simular_missao(8, 3, 34)


class TestMenorTanque:
    def test_e_a_fronteira_exata(self):
        """Com o minimo o bot vence; com um a menos, nao."""
        achou = 0
        for size, seed in mapas_vencidos():
            minimo, _ = api.menor_tanque(size, seed)
            assert jogar_de_novo(size, seed, minimo).motivo_parada == VITORIA
            if minimo > api.ENERGIA_MIN:
                assert jogar_de_novo(size, seed, minimo - 1).motivo_parada != VITORIA
            achou += 1
        assert achou >= 5

    def test_vitoria_e_monotona_acima_do_minimo(self):
        """Amostra: nos 8 primeiros mapas 8x8 e 4 tanques por mapa, todo tanque
        maior que o minimo tambem vence. NAO prova monotonia: ver o teste abaixo."""
        for size, seed in mapas_vencidos()[:8]:
            minimo, _ = api.menor_tanque(size, seed)
            for tanque in (minimo + 1, minimo + 7, minimo * 2, api.ENERGIA_MAX):
                assert api.simular_missao(size, seed, tanque).venceu, (size, seed, tanque)

    def test_a_busca_binaria_nao_acha_o_menor_tanque_em_todo_mapa(self):
        """Caso MEDIDO (varredura 1..300): em 8x8 seed 3 a busca binaria devolve 122,
        mas 46 ja vence. A vitoria nao e monotona no tanque, entao `menor_tanque` e
        'o menor que a busca achou'. Se este teste falhar, o fato mudou: ou o jogo
        mudou, ou a busca foi trocada por uma exata. Atualize o comentario de
        api_greedy e o texto da tela antes de apagar o teste."""
        achado, _ = api.menor_tanque(8, 3)
        assert achado == 122
        assert api.simular_missao(8, 3, 46).venceu
        assert api.simular_missao(8, 3, 45).venceu is False

    def test_mapa_que_o_proprio_t1_nao_vence_nao_tem_solucao_e_diz_porque(self):
        for seed in range(30):
            if not api.simular_missao(8, seed, api.ENERGIA_MAX).venceu:
                minimo, motivo = api.menor_tanque(8, seed)
                assert minimo is None
                assert motivo in ("sem objetivos alcançaveis", "sem pokemon")
                return
        pytest.fail("todos os mapas vencem?")


class TestDadosAlcance:
    def test_a_previsao_nunca_promete_vitoria_que_o_bot_nao_entrega(self):
        """O teste que a primeira versao reprovaria: 180 falsos positivos."""
        falsos = []
        confere = 0
        for size, seed in mapas_vencidos((8, 15), range(15)):
            minimo, _ = api.menor_tanque(size, seed)
            for tanque in {max(1, minimo - 3), minimo, minimo + 4, int(minimo * 1.5), minimo * 3}:
                prevista = api.dados_alcance(size, seed, tanque)["escolhido"]["viavel"]
                real = jogar_de_novo(size, seed, tanque).motivo_parada == VITORIA
                confere += 1
                if prevista != real:
                    falsos.append((size, seed, tanque, prevista, real))
        assert confere > 40
        assert falsos == []

    def test_abaixo_do_minimo_diz_quanto_falta_e_porque(self):
        size, seed = mapas_vencidos()[0]
        minimo, _ = api.menor_tanque(size, seed)
        escolhido = api.dados_alcance(size, seed, minimo - 1)["escolhido"]
        assert escolhido["viavel"] is False
        assert escolhido["folga"] == -1
        assert escolhido["motivo"] in ("rota sem recarga possivel", "sem energia")

    def test_no_minimo_a_folga_e_zero_e_vence(self):
        size, seed = mapas_vencidos()[0]
        minimo, _ = api.menor_tanque(size, seed)
        escolhido = api.dados_alcance(size, seed, minimo)["escolhido"]
        assert escolhido["viavel"] is True and escolhido["folga"] == 0
        # `objetivos` conta destinos visitados (pokemon, itens, replanejos), nao
        # pokemon capturados: vencer exige PELO MENOS os 4, nunca exatamente 4.
        assert escolhido["objetivos"] >= game.POKEMON_PARA_VENCER
        assert escolhido["motivo"] == ""

    def test_niveis_sao_multiplos_do_menor_tanque_que_vence(self):
        for size, seed in mapas_vencidos()[:4]:
            d = api.dados_alcance(size, seed)
            minimo = d["menor_tanque"]
            assert set(d["niveis"]) <= set(api.NIVEIS)
            for nome, fator in api.NIVEIS.items():
                if nome in d["niveis"]:
                    assert d["niveis"][nome]["fator"] == fator
                    esperado = max(api.ENERGIA_MIN, min(api.ENERGIA_MAX, round(minimo * fator)))
                    assert d["niveis"][nome]["alcance"] == esperado

    def test_presets_contam_a_historia_abaixo_falha_minimo_e_folgado_vencem(self):
        """O motivo de os presets existirem: com fracoes do custo planejado, 18 de
        18 mapas vencidos tinham os TRES niveis inviaveis e os botoes nao serviam.

        `minimo` vence por construcao (e o tanque que a busca testou). `folgado` e
        `abaixo` NAO: a vitoria nao e monotona no tanque (ver o comentario de
        api_greedy), entao exigimos que o veredito bata com a simulacao e que a
        historia se conte na MAIORIA dos mapas, nao em todos."""
        total = com_abaixo_falhando = 0
        for size, seed in mapas_vencidos((8, 15), range(12)):
            n = api.dados_alcance(size, seed)["niveis"]
            assert n["minimo"]["viavel"] is True and n["minimo"]["folga"] == 0
            for nome, nivel in n.items():
                assert nivel["viavel"] is api.simular_missao(size, seed, nivel["alcance"]).venceu
                assert (nivel["folga"] >= 0) == (nivel["alcance"] >= api.menor_tanque(size, seed)[0])
            total += 1
            com_abaixo_falhando += "abaixo" in n and n["abaixo"]["viavel"] is False
        assert total >= 8
        assert com_abaixo_falhando >= total * 0.8

    def test_veredito_traz_o_time_contra_a_meta(self):
        """`pokemon` e o tamanho do time ao fim da missao: bate com uma execucao
        independente, e so chega na meta quando o bot vence."""
        achou_derrota = False
        for size, seed in mapas_vencidos((8, 15), range(8)):
            for n in api.dados_alcance(size, seed)["niveis"].values():
                time = time_final(size, seed, n["alcance"])
                assert n["pokemon"] == time
                assert n["meta"] == game.POKEMON_PARA_VENCER
                assert (n["pokemon"] >= n["meta"]) == n["viavel"]
                achou_derrota = achou_derrota or not n["viavel"]
        assert achou_derrota

    def test_cada_nivel_traz_o_veredito_da_simulacao(self):
        for size, seed in mapas_vencidos()[:4]:
            d = api.dados_alcance(size, seed)
            for n in d["niveis"].values():
                real = jogar_de_novo(size, seed, n["alcance"]).motivo_parada == VITORIA
                assert n["viavel"] is real

    def test_recomendado_vence_quando_o_mapa_permite(self):
        for size, seed in mapas_vencidos((8, 15), range(12)):
            d = api.dados_alcance(size, seed)
            assert d["menor_tanque"] is not None
            assert d["recomendado"] >= d["menor_tanque"]
            assert jogar_de_novo(size, seed, d["recomendado"]).motivo_parada == VITORIA

    def test_mapa_sem_solucao_nao_inventa_minimo(self):
        for seed in range(30):
            if not api.simular_missao(8, seed, api.ENERGIA_MAX).venceu:
                d = api.dados_alcance(8, seed)
                assert d["menor_tanque"] is None and d["motivo_sem_solucao"]
                # sem minimo nao ha ancora pros presets, e o tanque cheio
                # reproduz o T1: a energia nao e o que impede de vencer
                assert d["niveis"] == {}
                assert d["recomendado"] == api.ENERGIA_MAX
                return
        pytest.fail("nenhum mapa sem solucao nas 30 primeiras seeds")

    def test_sem_alcance_escolhido_nao_traz_o_campo(self):
        assert "escolhido" not in api.dados_alcance(8, 3)

    def test_alcance_escolhido_e_preso_na_faixa(self):
        d = api.dados_alcance(8, 3, 10 ** 9)
        assert d["escolhido"]["alcance"] == api.ENERGIA_MAX
