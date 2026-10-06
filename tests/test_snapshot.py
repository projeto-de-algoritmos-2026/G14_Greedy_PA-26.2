"""Snapshot JSON do benchmark (fase 6, B7).

A pagina de Benchmark so desenha o que o snapshot traz, entao o que precisa de
garantia e: (1) os numeros batem com a fonte (README do T1, CSVs do T2), e
(2) um CSV que sai do formato que a tela assume e recusado, nao desenhado errado.
"""

import csv
import json

import pytest

from webdemo import snapshot


@pytest.fixture(scope="module")
def dados():
    return snapshot.gerar()


class TestTrabalho1:
    def test_bate_com_a_tabela_do_readme_do_t1(self, dados):
        """Os numeros do README (8x8, HP cheio) sao a media de rotas.csv com
        estado == hp100. Se mudarem, o README e o snapshot discordam."""
        esperado = {("dfs", 8): (43.3, 9.5, 17.6), ("bfs", 8): (28.0, 6.5, 15.1),
                    ("dijkstra", 8): (25.1, 6.7, 14.9), ("dfs", 15): (83.8, 19.8, 49.8),
                    ("dijkstra", 15): (47.2, 13.4, 51.9)}
        achado = {(r["algoritmo"], r["tamanho"]): r for r in dados["t1"]["rota"]}
        for chave, (custo, passos, nos) in esperado.items():
            r = achado[chave]
            assert (round(r["custo_medio"], 1), round(r["passos_medio"], 1),
                    round(r["nos_expandidos_medio"], 1)) == (custo, passos, nos), chave

    def test_tese_do_t1_menos_passos_nao_e_menor_custo(self, dados):
        """A frase da tela: o BFS anda menos (ou igual) e paga mais que o Dijkstra."""
        r = {(x["algoritmo"], x["tamanho"]): x for x in dados["t1"]["rota"]}
        for tam in snapshot.TAMANHOS:
            assert r[("dijkstra", tam)]["custo_medio"] <= r[("bfs", tam)]["custo_medio"]
            assert r[("dijkstra", tam)]["custo_medio"] < r[("dfs", tam)]["custo_medio"]

    def test_tem_os_tres_algoritmos_nos_tres_tamanhos(self, dados):
        assert {(r["algoritmo"], r["tamanho"]) for r in dados["t1"]["rota"]} == {
            (a, t) for a in snapshot.ALGORITMOS for t in snapshot.TAMANHOS}
        assert {(p["algoritmo"], p["tamanho"]) for p in dados["t1"]["partida"]} == {
            (a, t) for a in snapshot.ALGORITMOS for t in snapshot.TAMANHOS}


class TestTrabalho2:
    def test_cobre_a_grade_inteira(self, dados):
        chaves = {(l["tamanho"], l["alcance"], l["algoritmo"], l["estrategia"])
                  for l in dados["t2"]["linhas"]}
        esperadas = {(t, a, al, e) for t in snapshot.TAMANHOS for a in snapshot.ALCANCES
                     for al in snapshot.ALGORITMOS for e in dados["t2"]["estrategias"]}
        assert chaves == esperadas

    def test_as_premissas_do_contrato_valem(self, dados):
        for l in dados["t2"]["linhas"]:
            assert l["chegadas"] + l["desmaios"] == l["execucoes"]
            assert 0 <= l["taxa_inviavel"] <= 1

    def test_guloso_iguala_o_otimo_par_a_par(self):
        """A premissa 2 do contrato, no nivel certo: por par, nao pela media."""
        comparados = snapshot.validar_pares(snapshot.ler("paradas.csv"))
        assert comparados > 1000

    def test_cruzamento_fecha(self, dados):
        assert len(dados["t2"]["cruzamento"]) == 9
        for c in dados["t2"]["cruzamento"]:
            assert (c["dijkstra_menos_paradas"] + c["empates"] + c["dijkstra_mais_paradas"]
                    == c["destinos_comparados"])

    def test_dado_real_contraria_o_protótipo(self, dados):
        """O prototipo ilustrava 'Dijkstra precisa de menos paradas sobre todas as
        rotas'. O medido e mais modesto: empata na maioria e nunca perde. A tela
        tem que dizer isso, nao a estimativa."""
        menos = sum(c["dijkstra_menos_paradas"] for c in dados["t2"]["cruzamento"])
        empates = sum(c["empates"] for c in dados["t2"]["cruzamento"])
        mais = sum(c["dijkstra_mais_paradas"] for c in dados["t2"]["cruzamento"])
        assert mais == 0 and empates > menos > 0


class TestContratoQuebrado:
    def test_resumo_que_nao_fecha_e_recusado(self):
        linha = {"tamanho": "8", "alcance": "medio", "algoritmo": "dfs", "estrategia": "guloso",
                 "execucoes": "10", "chegadas": "7", "desmaios": "1", "rotas_inviaveis": "0",
                 "taxa_inviavel": "0.0"}
        with pytest.raises(snapshot.ContratoQuebrado, match="chegadas"):
            snapshot.validar_resumo([linha])

    def test_nivel_de_alcance_desconhecido_e_recusado(self):
        linha = {"tamanho": "8", "alcance": "enorme", "algoritmo": "dfs", "estrategia": "guloso",
                 "execucoes": "10", "chegadas": "10", "desmaios": "0", "rotas_inviaveis": "0",
                 "taxa_inviavel": "0.0"}
        with pytest.raises(snapshot.ContratoQuebrado, match="alcance"):
            snapshot.validar_resumo([linha])

    def test_taxa_inviavel_que_nao_bate_e_recusada(self):
        linha = {"tamanho": "8", "alcance": "medio", "algoritmo": "dfs", "estrategia": "guloso",
                 "execucoes": "10", "chegadas": "10", "desmaios": "0", "rotas_inviaveis": "10",
                 "taxa_inviavel": "0.9"}
        with pytest.raises(snapshot.ContratoQuebrado, match="taxa_inviavel"):
            snapshot.validar_resumo([linha])

    def test_guloso_diferente_do_otimo_no_mesmo_par_e_recusado(self):
        base = {"tamanho": "8", "seed": "0", "destino": "1-1", "alcance": "medio",
                "algoritmo": "dfs", "chegou": "1"}
        with pytest.raises(snapshot.ContratoQuebrado, match="divergem"):
            snapshot.validar_pares([{**base, "estrategia": "guloso", "paradas": "2"},
                                    {**base, "estrategia": "otimo", "paradas": "1"}])

    def test_csv_ausente_diz_qual_e_como_gerar(self, monkeypatch, tmp_path):
        monkeypatch.setattr(snapshot, "PASTA_CSV", tmp_path)
        with pytest.raises(snapshot.ContratoQuebrado, match="paradas_resumo.csv"):
            snapshot.ler("paradas_resumo.csv")


class TestEscrita:
    def test_escreve_json_valido_com_data_e_commit(self, tmp_path):
        caminho, _ = snapshot.escrever(tmp_path / "x" / "benchmark.json")
        lido = json.loads(caminho.read_text(encoding="utf-8"))
        assert lido["gerado_em"].endswith("Z")
        # O commit vem do git: e uma string num clone e None num ZIP baixado sem
        # .git. As duas coisas sao validas, a tela mostra "?" no segundo caso.
        assert lido["commit"] is None or (isinstance(lido["commit"], str) and lido["commit"])
        assert lido["t2"]["linhas"] and lido["t1"]["rota"]

    def test_sem_git_o_commit_e_none_e_nada_quebra(self, monkeypatch, tmp_path):
        """O cenario de quem baixa o ZIP do GitHub: nao ha .git e o snapshot ainda sai."""
        def sem_git(*args, **kwargs):
            raise FileNotFoundError("git")
        monkeypatch.setattr(snapshot.subprocess, "run", sem_git)
        caminho, _ = snapshot.escrever(tmp_path / "benchmark.json")
        lido = json.loads(caminho.read_text(encoding="utf-8"))
        assert lido["commit"] is None
        assert lido["t2"]["linhas"]

    def test_o_arquivo_versionado_bate_com_os_csvs_de_agora(self, dados):
        """O JSON commitado nao pode envelhecer em silencio: se os CSVs mudarem,
        este teste manda regenerar (python -m webdemo.snapshot)."""
        versionado = json.loads(snapshot.SAIDA.read_text(encoding="utf-8"))
        for chave in ("t1", "t2"):
            assert versionado[chave] == dados[chave], (
                "webdemo/dados/benchmark.json esta velho: rode python -m webdemo.snapshot")
