"""Comparar: as seis estrategias jogando a mesma missao (fase 6, B6).

Decisao do Lucas: cada raia e uma execucao REAL do bot, nao a rota planejada
concatenada (que prometeu solucao em 220 casos dos quais so 40 venciam). Entao
a propriedade que importa e: a raia diz exatamente o que o bot faz quando joga
aquela estrategia, e a linha do tempo bate com o que aconteceu.
"""
import pytest

from greedy import estrategias as estrategias_mod
from greedy.estrategias import ESTRATEGIAS
from webdemo import api_greedy as api

# 8x8 seed 4 com o tanque minimo: onde a tese aparece (limiares desmaiam, todo
# centro para demais, guloso e otimo empatam no minimo).
MAPA = (8, 4, 64)


@pytest.fixture(autouse=True)
def cache_limpo():
    api._comparar.cache_clear()
    yield
    api._comparar.cache_clear()


def raias_por_nome(c):
    return {r["estrategia"]: r for r in c["raias"]}


class TestEstrutura:
    def test_uma_raia_por_estrategia_na_ordem_do_greedy(self):
        c = api.comparar(*MAPA[:2], MAPA[2])
        assert [r["estrategia"] for r in c["raias"]] == list(ESTRATEGIAS)
        assert c["alcance"] == MAPA[2] and c["meta"] == 4

    def test_sem_energia_usa_o_tanque_recomendado(self):
        c = api.comparar(8, 4)
        assert c["alcance"] == api.dados_alcance(8, 4)["recomendado"]

    def test_algoritmo_desconhecido_e_erro(self):
        with pytest.raises(ValueError):
            api.comparar(8, 4, 64, "inventado")

    def test_resultado_e_cacheado(self):
        a = api.comparar(*MAPA[:2], MAPA[2])
        b = api.comparar(*MAPA[:2], MAPA[2])
        assert a is b


class TestFidelidadeAoBot:
    def test_cada_raia_bate_com_uma_execucao_independente(self):
        """`simular_missao` e a fonte independente: mesma semente, mesmo bot."""
        for size, seed, tanque in [MAPA, (8, 1, 150), (15, 3, 91), (8, 3, 122)]:
            c = api.comparar(size, seed, tanque)
            for r in c["raias"]:
                if not r["disponivel"]:
                    continue
                sim = api.simular_missao(size, seed, tanque, r["estrategia"])
                assert (r["venceu"], r["paradas"], r["energia_desperdicada"],
                        r["passos"], r["pokemon"]) == (
                    sim.venceu, sim.paradas, sim.energia_desperdicada, sim.passos, sim.pokemon,
                ), (size, seed, tanque, r["estrategia"])

    def test_e_deterministico(self):
        primeiro = api.comparar(*MAPA[:2], MAPA[2])
        api._comparar.cache_clear()
        assert api.comparar(*MAPA[:2], MAPA[2]) == primeiro

    def test_a_tese_aparece_no_mapa_escolhido(self):
        """Medido em 05/10: no 8x8 seed 4 com tanque 64, os tres limiares
        desmaiam e o todo-centro para muito mais que o guloso."""
        r = raias_por_nome(api.comparar(*MAPA[:2], MAPA[2]))
        assert r["guloso"]["venceu"] and r["otimo"]["venceu"]
        assert r["guloso"]["paradas"] == r["otimo"]["paradas"]
        assert r["todo_centro"]["venceu"]
        assert r["todo_centro"]["paradas"] > r["guloso"]["paradas"]
        assert not r["limiar_10"]["venceu"] and not r["limiar_25"]["venceu"]


class TestLinhaDoTempo:
    def test_custo_acumulado_mede_a_energia_gasta_de_verdade(self):
        """O eixo da regua. Sem esta conta, 'custo nunca desce' passa com uma
        lista de zeros: um custo que nao acumula tem que reprovar aqui."""
        for size, seed, tanque in [MAPA, (8, 1, 150), (15, 3, 91)]:
            for r in api.comparar(size, seed, tanque)["raias"]:
                assert r["custo_total"] > 0, r["estrategia"]
                custos = [m["c"] for m in r["linha"]]
                assert custos == sorted(custos)
                assert max(custos) > 0 and max(custos) <= r["custo_total"]
                if r["venceu"]:
                    # ganhar exige andar ate a ultima captura: o eixo nao e um ponto
                    assert max(custos) >= r["custo_total"] * 0.5

    def test_custo_total_e_a_soma_da_energia_gasta_por_passo(self):
        """Fonte independente: refaz o jogo por fora dos ganchos e soma."""
        import random
        from bench.common import silencioso
        from bench.partidas import novo_jogador
        from bot.runner import executar_bot
        from grid import Grid
        for chave in ("guloso", "todo_centro"):
            size, seed, tanque = MAPA
            random.seed(f"{size}-{seed}")
            mapa, jogador = Grid(size=size, seed=seed), novo_jogador()
            jogador.energia = jogador.energia_max = tanque
            with silencioso():
                r = executar_bot(mapa, jogador, max_passos=640, estrategia=ESTRATEGIAS[chave])
            esperado = sum(m.energia_gasta for m in r.movimentos if m.valido)
            achada = raias_por_nome(api.comparar(size, seed, tanque))[chave]
            assert achada["custo_total"] == esperado

    def test_tantas_paradas_na_linha_quantas_o_bot_fez(self):
        for size, seed, tanque in [MAPA, (8, 1, 150), (15, 3, 91)]:
            for r in api.comparar(size, seed, tanque)["raias"]:
                assert sum(m["tipo"] == "parada" for m in r["linha"]) == r["paradas"], r["estrategia"]

    def test_capturas_na_linha_sao_o_time_menos_o_inicial(self):
        for r in api.comparar(*MAPA[:2], MAPA[2])["raias"]:
            assert sum(m["tipo"] == "captura" for m in r["linha"]) == r["pokemon"] - 1

    def test_desmaio_so_em_quem_nao_venceu_e_e_o_ultimo_marco(self):
        achou = False
        for r in api.comparar(*MAPA[:2], MAPA[2])["raias"]:
            desmaios = [m for m in r["linha"] if m["tipo"] == "desmaio"]
            if r["venceu"]:
                assert desmaios == [] and r["desmaio_em"] is None
            elif r["motivo"] == "sem energia":
                achou = True
                assert len(desmaios) == 1 and r["linha"][-1] is desmaios[0]
                assert r["desmaio_em"] == desmaios[0]["c"] <= r["custo_total"] + 100
        assert achou

    def test_parada_registra_quanto_sobrava_no_tanque(self):
        for r in api.comparar(*MAPA[:2], MAPA[2])["raias"]:
            sobras = [m["sobrava"] for m in r["linha"] if m["tipo"] == "parada"]
            assert sum(sobras) == r["energia_desperdicada"]


class TestVeredito:
    def test_vencedoras_sao_as_que_chegam_com_menos_paradas(self):
        c = api.comparar(*MAPA[:2], MAPA[2])
        v = c["veredito"]
        raias = raias_por_nome(c)
        chegam = [n for n, r in raias.items() if r["disponivel"] and r["venceu"]]
        assert v["menos_paradas"] == min(raias[n]["paradas"] for n in chegam)
        assert set(v["vencedoras"]) == {n for n in chegam if raias[n]["paradas"] == v["menos_paradas"]}
        assert set(v["falharam"]) == {n for n, r in raias.items() if r["disponivel"] and not r["venceu"]}

    def test_ninguem_chega_nao_inventa_vencedora(self):
        c = api.comparar(8, 4, 5)
        assert c["veredito"]["vencedoras"] == [] and c["veredito"]["menos_paradas"] is None
        assert len(c["veredito"]["falharam"]) == len(ESTRATEGIAS)


class TestOtimoAcimaDoLimite:
    def test_otimo_que_estoura_o_limite_vira_indisponivel_e_nao_derruba_a_comparacao(self, monkeypatch):
        monkeypatch.setattr(estrategias_mod, "MAX_CENTROS_OTIMO", 0)
        c = api.comparar(*MAPA[:2], MAPA[2])
        otimo = raias_por_nome(c)["otimo"]
        assert otimo["disponivel"] is False and "centros" in otimo["motivo_indisponivel"]
        assert "venceu" not in otimo
        assert c["veredito"]["indisponiveis"] == ["otimo"]
        outras = [r for r in c["raias"] if r["estrategia"] != "otimo"]
        assert all(r["disponivel"] for r in outras)


class TestTravaDoRNG:
    def test_libera_a_trava_ao_terminar(self):
        api.comparar(*MAPA[:2], MAPA[2])
        assert api._TRANCA_RNG.acquire(timeout=10), "trava do RNG ficou presa"
        api._TRANCA_RNG.release()

    def test_libera_a_trava_mesmo_se_uma_raia_quebrar(self, monkeypatch):
        def quebrado(*a, **k):
            raise RuntimeError("falha de proposito")
        monkeypatch.setattr(api, "executar_bot", quebrado)
        with pytest.raises(RuntimeError):
            api.comparar(*MAPA[:2], MAPA[2])
        assert api._TRANCA_RNG.acquire(timeout=10), "trava do RNG ficou presa"
        api._TRANCA_RNG.release()
