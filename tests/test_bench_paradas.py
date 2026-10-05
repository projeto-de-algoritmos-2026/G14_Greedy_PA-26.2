"""Testes do experimento de paradas (fase 5 do trabalho 2).

Grade pequena de proposito, como em test_bench.py: o que se garante e o
contrato (colunas, descarte registrado, invariantes do guloso), nao os numeros
da grade real.
"""
import pytest

from bench import charts, common, paradas
from greedy.estrategias import ESTRATEGIAS


@pytest.fixture(scope="module")
def grade():
    return paradas.rodar(tamanhos=(8, 15), seeds=4, destinos_por_mapa=5)


def por_rota(linhas):
    return common.agrupar(linhas, ["tamanho", "seed", "destino", "alcance", "algoritmo"])


def test_linhas_tem_as_colunas_do_csv(grade):
    linhas, descartes = grade
    assert linhas, "a grade minima precisa produzir alguma simulacao"
    assert all(set(linha) == set(paradas.CAMPOS) for linha in linhas)
    assert all(set(d) == set(paradas.CAMPOS_DESCARTE) for d in descartes)


def test_toda_rota_viavel_roda_toda_estrategia(grade):
    linhas, _ = grade
    for grupo in por_rota(linhas).values():
        # O otimo so falta quando a rota tem centros demais pra forca bruta.
        assert set(ESTRATEGIAS) - {"otimo"} <= {l["estrategia"] for l in grupo}


def test_rota_sem_recarga_vai_pros_descartes_e_nao_pras_linhas(grade):
    linhas, descartes = grade
    inviaveis = {(d["tamanho"], d["seed"], d["destino"], d["alcance"], d["algoritmo"])
                 for d in descartes if d["motivo"] == "rota sem recarga possivel"}
    assert inviaveis, "tanque curto deveria deixar alguma rota sem solucao"
    assert not inviaveis & set(por_rota(linhas))


def test_mesmo_tanque_pras_tres_rotas_do_destino(grade):
    linhas, _ = grade
    for grupo in common.agrupar(linhas, ["tamanho", "seed", "destino", "alcance"]).values():
        assert len({linha["tanque"] for linha in grupo}) == 1


def test_guloso_e_todo_centro_nunca_desmaiam_em_rota_viavel(grade):
    linhas, _ = grade
    for linha in linhas:
        if linha["estrategia"] in ("guloso", "todo_centro", "otimo"):
            assert linha["chegou"] == 1


def test_quem_chega_nunca_para_menos_que_o_guloso(grade):
    """A tese em forma de teste: parar tarde nao e parar pouco."""
    linhas, _ = grade
    for grupo in por_rota(linhas).values():
        paradas_por = {l["estrategia"]: l for l in grupo}
        minimo = paradas_por["guloso"]["paradas"]
        for linha in grupo:
            if linha["chegou"]:
                assert linha["paradas"] >= minimo
        if "otimo" in paradas_por:
            assert paradas_por["otimo"]["paradas"] == minimo


def test_tanque_nunca_e_zero():
    assert paradas.tanque(1, 0.3) == 1
    assert paradas.tanque(40, 0.5) == 20


def test_resumo_conta_execucoes_e_inviaveis(grade):
    linhas, descartes = grade
    resumo = paradas.resumir(linhas, descartes)

    assert sum(item["execucoes"] for item in resumo) == len(linhas)
    assert all(set(item) == set(paradas.CAMPOS_RESUMO) for item in resumo)
    for item in resumo:
        assert item["chegadas"] + item["desmaios"] == item["execucoes"]
        assert 0 <= item["taxa_inviavel"] < 1


def test_cruzamento_soma_os_tres_desfechos(grade):
    linhas, _ = grade
    cruzamento = paradas.cruzar(linhas)

    assert cruzamento
    for item in cruzamento:
        assert item["destinos_comparados"] == (
            item["dijkstra_menos_paradas"] + item["empates"] + item["dijkstra_mais_paradas"]
        )


def test_gerar_escreve_os_graficos_de_paradas(grade, tmp_path):
    linhas, descartes = grade
    common.escrever_csv(tmp_path / "paradas_resumo.csv", paradas.CAMPOS_RESUMO,
                        paradas.resumir(linhas, descartes))

    gerados = charts.gerar(tmp_path)

    assert [c.name for c in gerados] == [g[3] for g in charts.GRAFICOS_PARADAS]
    estrategias = (tmp_path / "paradas-estrategias.svg").read_text(encoding="utf-8")
    assert charts.CORES["guloso"] in estrategias
    assert ">otimo<" not in estrategias
