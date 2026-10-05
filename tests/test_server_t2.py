"""Rotas `/api/t2/*` e estaticos do servidor, por socket de verdade.

As funcoes de `api_greedy` ja tem testes proprios. Aqui so a casca: a rota
existe, le os parametros certos, e o navegador recebe o MIME que o modulo ES
exige (`text/javascript`, que no Windows o `mimetypes` nem sempre devolve).
"""

import http.client
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from webdemo import server


@pytest.fixture(scope="module")
def base():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Manipulador)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def buscar(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.status, r.headers, r.read()


def json_de(url):
    status, _, corpo = buscar(url)
    assert status == 200
    return json.loads(corpo)


def erro_de(url):
    with pytest.raises(urllib.error.HTTPError) as e:
        buscar(url)
    return e.value.code, json.loads(e.value.read())


def eventos_sse(url):
    _, cabecalhos, corpo = buscar(url)
    assert cabecalhos["Content-Type"].startswith("text/event-stream")
    nomes = [linha[7:] for linha in corpo.decode().splitlines() if linha.startswith("event: ")]
    return nomes


class TestRotasT2:
    def test_config_lista_as_estrategias_e_os_niveis(self, base):
        dados = json_de(f"{base}/api/t2/config")
        assert {e["id"] for e in dados["estrategias"]} >= {"guloso", "todo_centro", "otimo"}
        assert dados["niveis"] == {"abaixo": 0.75, "minimo": 1.0, "folgado": 1.5}

    def test_config_expoe_os_custos_que_o_jogo_de_fato_cobra(self, base):
        """A dica da tela mostra o custo de qualquer celula; ela so pode ser honesta
        se vier de graph/cost.py e nao de uma tabela copiada no navegador."""
        c = json_de(f"{base}/api/t2/config")["custos"]
        assert c["terreno"] == {"concrete": 1, "water": 4}
        assert c["grama"] == {"base": 3, "cheio": 3, "ferido": 6}
        assert c["conteudo"] == {"pokemon": 8, "cpu": 12}

    def test_custos_da_config_batem_com_o_que_mover_cobra(self, base):
        """Nao basta a config dizer 8: o passo REAL num pokemon tem que gastar
        terreno + 8. Anda de verdade ate uma celula com pokemon e compara o gasto."""
        c = json_de(f"{base}/api/t2/config")["custos"]
        conferidos = 0
        for seed in range(30):
            novo = json_de(f"{base}/api/t2/jogo/novo?size=8&seed={seed}&energia=300")
            for direcao, viz in novo["vizinhas"].items():
                if viz["valido"] and viz["conteudo"] in c["conteudo"]:
                    sessao = json_de(f"{base}/api/t2/jogo/novo?size=8&seed={seed}&energia=300")["sessao"]
                    passo = json_de(f"{base}/api/t2/jogo/mover?sessao={sessao}&direcao={direcao}")
                    terreno = passo["custo"]["terreno"]
                    assert terreno in (c["terreno"]["concrete"], c["grama"]["cheio"])
                    assert passo["energia_gasta"] == terreno + c["conteudo"][viz["conteudo"]]
                    conferidos += 1
        assert conferidos >= 2

    def test_benchmark_serve_o_snapshot_versionado(self, base):
        dados = json_de(f"{base}/api/t2/benchmark")
        assert dados["gerado_em"] and dados["commit"]
        assert len(dados["t2"]["linhas"]) == 162 and len(dados["t1"]["rota"]) == 9

    def test_benchmark_sem_snapshot_diz_como_gerar(self, base, monkeypatch, tmp_path):
        from webdemo import api_greedy
        monkeypatch.setattr(api_greedy, "SNAPSHOT", tmp_path / "nao-existe.json")
        assert "snapshot" in json_de(f"{base}/api/t2/benchmark")["erro"]

    def test_alcance_le_size_seed_e_alcance_da_query(self, base):
        dados = json_de(f"{base}/api/t2/alcance?size=8&seed=0&alcance=150")
        assert dados["size"] == 8 and dados["seed"] == 0
        assert dados["escolhido"]["alcance"] == 150

    def test_jogo_novo_mover_e_recarregar_usam_a_mesma_sessao(self, base):
        novo = json_de(f"{base}/api/t2/jogo/novo?size=8&seed=0&energia=200")
        assert novo["jogador"]["energia"] == novo["jogador"]["energia_max"] == 200
        sessao = novo["sessao"]

        estado = json_de(f"{base}/api/t2/jogo/estado?sessao={sessao}")
        assert estado["posicao"] == novo["posicao"]

        passo = json_de(f"{base}/api/t2/jogo/mover?sessao={sessao}&direcao=d")
        assert "custo" in passo and "vizinhas" in passo

        recarga = json_de(f"{base}/api/t2/jogo/recarregar?sessao={sessao}")
        assert recarga["recarregou"] is False and recarga["motivo"]

    def test_sessao_desconhecida_e_erro_legivel_nao_excecao(self, base):
        assert "erro" in json_de(f"{base}/api/t2/jogo/estado?sessao=nao-existe")

    def test_partida_transmite_de_inicio_a_fim(self, base):
        nomes = eventos_sse(f"{base}/api/t2/partida?size=8&seed=0&energia=200&estrategia=guloso")
        assert nomes[0] == "inicio" and nomes[-1] == "fim"
        assert "plano" in nomes and "passo" in nomes

    def test_estrategia_nenhuma_pede_o_bot_do_t1_sem_paradas(self, base):
        nomes = eventos_sse(f"{base}/api/t2/partida?size=8&seed=0&energia=300&estrategia=nenhuma")
        assert nomes[-1] == "fim" and "recarga" not in nomes

    def test_comparar_devolve_as_seis_raias(self, base):
        dados = json_de(f"{base}/api/t2/comparar?size=8&seed=4&energia=64")
        assert len(dados["raias"]) == 6 and dados["alcance"] == 64
        assert dados["veredito"]["vencedoras"] and "guloso" in dados["veredito"]["vencedoras"]

    def test_comparar_algoritmo_desconhecido_da_400(self, base):
        codigo, corpo = erro_de(f"{base}/api/t2/comparar?algoritmo=inventado")
        assert codigo == 400 and "algoritmo" in corpo["erro"]

    def test_estrategia_e_algoritmo_desconhecidos_dao_400(self, base):
        codigo, corpo = erro_de(f"{base}/api/t2/partida?estrategia=inventada")
        assert codigo == 400 and "estrategia" in corpo["erro"]
        codigo, corpo = erro_de(f"{base}/api/t2/partida?algoritmo=inventado")
        assert codigo == 400 and "algoritmo" in corpo["erro"]

    def test_rota_t2_inexistente_cai_no_404_do_servidor(self, base):
        codigo, _ = erro_de(f"{base}/api/t2/nao-existe")
        assert codigo == 404

    def test_rotas_do_t1_continuam_de_pe(self, base):
        assert json_de(f"{base}/api/config")["tamanhos"]
        assert json_de(f"{base}/api/mapa?size=8&seed=42")["size"] == 8


class TestEstaticos:
    def test_javascript_sai_como_text_javascript(self, base):
        _, cabecalhos, _ = buscar(f"{base}/t1.js")
        assert cabecalhos["Content-Type"].split(";")[0] == "text/javascript"

    def test_demo_do_t1_continua_em_t1(self, base):
        status, cabecalhos, corpo = buscar(f"{base}/t1")
        assert status == 200 and cabecalhos["Content-Type"].startswith("text/html")
        assert b"/t1.js" in corpo and b"/t1.css" in corpo
        for recurso in ("/t1.js", "/t1.css"):
            assert buscar(f"{base}{recurso}")[0] == 200

    def test_pasta_static_serve_modulos_e_recusa_fuga_de_diretorio(self, base):
        _, cabecalhos, _ = buscar(f"{base}/static/t1.js")
        assert cabecalhos["Content-Type"].split(";")[0] == "text/javascript"
        # `../` cru, sem o cliente normalizar: aponta pra webdemo/server.py, que
        # EXISTE. So a checagem de ESTATICOS impede o 200.
        conexao = http.client.HTTPConnection(base.removeprefix("http://"), timeout=10)
        conexao.request("GET", "/static/../server.py")
        resposta = conexao.getresponse()
        assert resposta.status == 404
        assert b"Manipulador" not in resposta.read()
        conexao.close()
        codigo, _ = erro_de(f"{base}/static/nao-existe.js")
        assert codigo == 404
