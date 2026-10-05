"""API do trabalho 2, parte do bot ao vivo (fase 6).

O bot roda numa thread e empurra os eventos pelos ganchos do runner enquanto a
partida acontece: nao ha replay. O que a pagina ve e o que game.mover() e
game.recarregar() de fato fizeram. Estes testes conferem o contrato dos eventos
e as invariantes que a regua e o diario assumem.

Sequencia por plano: `plano` (rota ate o proximo objetivo), `paradas` (onde a
estrategia resolveu parar), varios `passo` e, se a estrategia mandou parar,
uma `recarga`. Depois, outro plano. A regua cresce a cada plano (decisao D3).
"""
import pytest

from webdemo import api_greedy as api

ENERGIA = 40


def coletar(size=8, seed=1, estrategia="guloso", energia=ENERGIA, algoritmo="dijkstra", **extra):
    return list(api.eventos_partida(size, seed, algoritmo, energia, estrategia, **extra))


def nomes(eventos):
    return [nome for nome, _ in eventos]


def dados_de(eventos, nome):
    return [d for n, d in eventos if n == nome]


def com_recarga(estrategia="todo_centro", energia=12):
    """Primeira (size, seed) em que o bot de fato recarrega: o cenario do teste."""
    for size in (8, 15):
        for seed in range(40):
            eventos = coletar(size, seed, estrategia, energia)
            if dados_de(eventos, "recarga"):
                return size, seed, eventos
    pytest.fail("nenhum mapa com recarga nas 80 primeiras seeds")


class TestEstrutura:
    def test_abre_com_inicio_e_fecha_com_fim(self):
        eventos = coletar()
        assert nomes(eventos)[0] == "inicio"
        assert nomes(eventos)[-1] == "fim"
        assert nomes(eventos).count("inicio") == nomes(eventos).count("fim") == 1

    def test_inicio_traz_mapa_centros_estrategia_e_alcance(self):
        inicio = dados_de(coletar(15, 2, "limiar_25", 30), "inicio")[0]
        assert inicio["size"] == 15 and len(inicio["celulas"]) == 15
        assert inicio["estrategia"] == "limiar_25" and inicio["algoritmo"] == "dijkstra"
        assert inicio["jogador"]["energia"] == inicio["jogador"]["energia_max"] == 30
        assert sorted(inicio["centros"]) == sorted(list(p) for p in __import__("grid").Grid(15, 2).centros())
        assert inicio["alcance"]["escolhido"]["alcance"] == 30

    def test_e_deterministico(self):
        """Mesmos parametros, mesma partida: um resultado visto na apresentacao
        se reproduz depois."""
        assert coletar(15, 3, "guloso", 30) == coletar(15, 3, "guloso", 30)

    def test_estrategia_ou_algoritmo_desconhecidos_sao_erro(self):
        with pytest.raises(ValueError):
            list(api.eventos_partida(8, 1, "dijkstra", 20, "telepatia"))
        with pytest.raises(ValueError):
            list(api.eventos_partida(8, 1, "voo", 20, "guloso"))

    def test_energia_e_presa_na_faixa(self):
        inicio = dados_de(coletar(energia=10 ** 9), "inicio")[0]
        assert inicio["jogador"]["energia_max"] == api.ENERGIA_MAX


class TestPlanoEParadas:
    def test_cada_plano_e_seguido_do_evento_de_paradas(self):
        eventos = coletar(15, 2, "guloso", 60)
        seq = nomes(eventos)
        for i, nome in enumerate(seq):
            if nome == "plano":
                assert seq[i + 1] == "paradas"

    def test_marcos_e_paradas_apontam_para_a_rota_do_plano(self):
        eventos = coletar(15, 2, "guloso", 60)
        for i, (nome, dados) in enumerate(eventos):
            if nome != "plano":
                continue
            paradas = eventos[i + 1][1]
            assert len(paradas["marcos"]) == len(dados["caminho"])
            assert paradas["marcos"][0] == [0, False]
            assert paradas["marcos"][-1][0] == dados["custo"]
            if paradas["escolhidas"] is None:
                assert paradas["sem_solucao"] is True and paradas["posicoes"] == []
                continue
            assert paradas["sem_solucao"] is False
            assert paradas["posicoes"] == [dados["caminho"][k] for k in paradas["escolhidas"]]
            for k in paradas["escolhidas"]:
                assert paradas["marcos"][k][1] is True  # parada so em Centro

    def test_sem_solucao_e_avisado_e_o_bot_nem_sai_do_lugar(self):
        """Tanque de 1: nenhuma rota tem recarga possivel. O evento diz None e o
        bot desiste antes do primeiro passo, em vez de desmaiar de proposito."""
        eventos = coletar(15, 2, "guloso", 1)
        paradas = dados_de(eventos, "paradas")
        assert paradas and paradas[-1]["escolhidas"] is None
        assert paradas[-1]["sem_solucao"] is True
        assert dados_de(eventos, "fim")[0]["motivo_parada"] == "rota sem recarga possivel"
        assert dados_de(eventos, "passo") == []


class TestPasso:
    def test_custo_fecha_em_todo_passo_valido(self):
        total = 0
        for size, seed in [(8, 1), (8, 4), (15, 2), (15, 5)]:
            for _, p in [e for e in coletar(size, seed, "guloso", 60) if e[0] == "passo"]:
                if not p["valido"]:
                    continue
                total += 1
                c = p["custo"]
                assert c["terreno"] + c["conteudo"] == c["total"] == p["energia_gasta"]
                assert p["energia_antes"] - p["energia_depois"] == p["energia_gasta"]
        assert total > 20

    def test_batalha_tem_conteudo_e_custo_de_conteudo(self):
        achou = 0
        for seed in range(30):
            for p in dados_de(coletar(8, seed, "guloso", 100), "passo"):
                if p["valido"] and p["batalhou"]:
                    achou += 1
                    assert p["conteudo"] in ("pokemon", "cpu")
                    assert p["custo"]["conteudo"] in (8, 12)
        assert achou > 0

    def test_passo_livre_nao_cobra_conteudo(self):
        for p in dados_de(coletar(8, 1, "guloso", 100), "passo"):
            if p["valido"] and not p["batalhou"]:
                assert p["custo"]["conteudo"] == 0

    def test_passo_traz_jogador_e_direcao(self):
        p = dados_de(coletar(8, 1, "guloso", 100), "passo")[0]
        assert p["direcao"] in "WASD" and len(p["posicao"]) == 2
        assert "energia" in p["jogador"]


class TestRecarga:
    def test_recarga_enche_o_tanque_e_fecha_a_conta(self):
        _, _, eventos = com_recarga()
        for r in dados_de(eventos, "recarga"):
            assert r["entrou"] + r["sobrava"] == r["energia_max"]
            assert r["jogador"]["energia"] == r["energia_max"]
            assert len(r["posicao"]) == 2

    def test_cada_recarga_fica_em_cima_de_um_centro_da_rota(self):
        _, _, eventos = com_recarga()
        inicio = dados_de(eventos, "inicio")[0]
        centros = {tuple(c) for c in inicio["centros"]}
        for r in dados_de(eventos, "recarga"):
            assert tuple(r["posicao"]) in centros

    def test_soma_das_sobras_e_a_energia_desperdicada_do_fim(self):
        _, _, eventos = com_recarga()
        fim = dados_de(eventos, "fim")[0]
        recargas = dados_de(eventos, "recarga")
        assert sum(r["sobrava"] for r in recargas) == fim["energia_desperdicada"]
        assert len(recargas) == fim["paradas"] > 0

    def test_a_recarga_acontece_depois_do_passo_que_chegou_no_centro(self):
        _, _, eventos = com_recarga()
        seq = nomes(eventos)
        for i, nome in enumerate(seq):
            if nome == "recarga":
                assert seq[i - 1] == "passo"
                assert eventos[i - 1][1]["posicao"] == eventos[i][1]["posicao"]

    def test_todo_centro_para_mais_que_o_guloso_e_desperdica_mais(self):
        """A tese do trabalho, na partida completa: mesmo mapa, mesmo tanque."""
        a = dados_de(coletar(30, 4, "todo_centro", 90), "fim")[0]
        b = dados_de(coletar(30, 4, "guloso", 90), "fim")[0]
        if a["motivo_parada"] == b["motivo_parada"] == "quatro pokemon capturados":
            assert a["paradas"] >= b["paradas"]
            assert a["energia_desperdicada"] >= b["energia_desperdicada"]


class TestDesmaio:
    def test_o_passo_que_desmaia_traz_custo_tentado_e_o_que_faltou(self):
        for seed in range(40):
            eventos = coletar(8, seed, "limiar_10", 6)
            caidos = [p for p in dados_de(eventos, "passo") if p["desmaiou"]]
            if not caidos:
                continue
            p = caidos[0]
            assert p["valido"] is False and p["energia_gasta"] == 0
            assert p["custo"]["total"] > p["energia_antes"]
            assert p["faltaram"] == p["custo"]["total"] - p["energia_antes"]
            fim = dados_de(eventos, "fim")[0]
            assert fim["motivo_parada"] == "sem energia"
            assert fim["jogador"]["situacao"] == "derrota"
            return
        pytest.fail("nenhum desmaio em 40 seeds com tanque 6")

    def test_o_fim_de_quem_caiu_nao_e_vitoria(self):
        for seed in range(40):
            fim = dados_de(coletar(8, seed, "limiar_10", 6), "fim")[0]
            if fim["motivo_parada"] == "sem energia":
                assert fim["jogador"]["situacao"] != "vitoria"


class TestFim:
    def test_resumo_da_partida(self):
        fim = dados_de(coletar(8, 1, "guloso", 100), "fim")[0]
        for campo in ("objetivos_concluidos", "passos", "paradas", "energia_desperdicada",
                      "replanejamentos", "motivo_parada", "jogador", "batalhas", "hp_perdido"):
            assert campo in fim

    def test_passos_do_fim_e_a_contagem_de_eventos_de_passo(self):
        eventos = coletar(15, 2, "guloso", 60)
        assert dados_de(eventos, "fim")[0]["passos"] == len(dados_de(eventos, "passo"))

    def test_estrategia_nenhuma_anda_a_rota_inteira_sem_paradas(self):
        eventos = coletar(8, 1, None, 100)
        assert "paradas" not in nomes(eventos) and "recarga" not in nomes(eventos)


class TestPartidaAoVivoComPedidoConcorrente:
    """O slider de alcance roda `simular_missao`, que reseeda o `random` global.
    A partida ao vivo usa o MESMO global (batalhas, inicial sorteado), entao um
    pedido de alcance no meio dela nao pode mudar o que o bot vive."""

    @staticmethod
    def _assinatura(eventos):
        return [(d["posicao"], d["hp_perdido"], d["batalhou"], d["energia_depois"])
                for n, d in eventos if n == "passo"]

    def test_slider_durante_o_stream_nao_muda_a_partida(self):
        import threading

        # Referencia: a partida sozinha, com os caches ja quentes.
        referencia = self._assinatura(coletar(15, 3, "guloso", 60))
        assert len(referencia) > 5

        divergencias = []
        for rodada in range(8):
            parar = threading.Event()

            def martelar():
                # tanques inéditos a cada volta: simular_missao e lru_cache, so
                # a chamada que nao esta em cache reseeda o random global
                tanque = 61 + rodada * 500
                while not parar.is_set():
                    api.simular_missao(15, 3, min(tanque, api.ENERGIA_MAX))
                    api.simular_missao.cache_clear()

            vizinho = threading.Thread(target=martelar, daemon=True)
            vizinho.start()
            try:
                vivida = self._assinatura(coletar(15, 3, "guloso", 60))
            finally:
                parar.set()
                vizinho.join()
            if vivida != referencia:
                divergencias.append(rodada)

        assert divergencias == []

    def test_cliente_que_fecha_no_meio_nao_deixa_a_trava_presa(self):
        """Fechar a aba derruba o gerador no meio. A trava e da thread do bot,
        nao do gerador: ela tem que voltar sozinha, senao o slider trava pra
        todo mundo ate o processo morrer."""
        gerador = api.eventos_partida(15, 3, "dijkstra", 60, "guloso")
        assert next(gerador)[0] == "inicio"
        gerador.close()  # a aba fechou aqui

        assert api._TRANCA_RNG.acquire(timeout=10), "trava do RNG ficou presa"
        api._TRANCA_RNG.release()

    def test_partida_com_erro_devolve_a_trava_e_avisa_a_pagina(self, monkeypatch):
        # Caches quentes: a sabotagem abaixo nao pode atingir o calculo do alcance
        # (simular_missao tambem chama executar_bot), so o bot da partida ao vivo.
        api.dados_alcance(8, 1, 100)

        def quebrado(*a, **k):
            raise RuntimeError("falha de proposito")
        monkeypatch.setattr(api, "executar_bot", quebrado)

        eventos = coletar(8, 1, "guloso", 100)
        assert "erro" in dados_de(eventos, "fim")[0]
        assert api._TRANCA_RNG.acquire(timeout=10), "trava do RNG ficou presa"
        api._TRANCA_RNG.release()
