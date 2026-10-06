"""bench.jogo_real: a medicao no jogo real tem de ser reproduzivel e fechar a conta."""
import pytest

from bench import jogo_real


def test_mesmo_sorteio_da_o_mesmo_desfecho():
    """A graca de semear por partida e poder repetir: sem isso a tabela mudava a cada rodada."""
    primeiro = jogo_real.jogar(8, 4, 96, "guloso", 3)
    assert jogo_real.jogar(8, 4, 96, "guloso", 3) == primeiro


def test_so_o_sorteio_das_batalhas_muda_entre_partidas():
    """O mapa e o mesmo nos dois sorteios; o que varia e o desfecho, nao o Grid."""
    from grid import Grid
    a = Grid(size=8, seed=4)
    b = Grid(size=8, seed=4)
    assert [[(c.terrain, c.occupied_with) for c in linha] for linha in a.grid] == \
           [[(c.terrain, c.occupied_with) for c in linha] for linha in b.grid]


def test_cada_partida_cai_em_um_motivo_conhecido():
    _, desfechos = jogo_real.medir(tamanhos=(8,), mapas_por_tamanho=3, sorteios=3)
    conhecidos = {jogo_real.VITORIA, *jogo_real.MOTIVOS}
    for nome, contagem in desfechos.items():
        assert set(contagem) <= conhecidos, (nome, set(contagem) - conhecidos)


def test_a_soma_das_colunas_fecha_as_partidas():
    mapas, desfechos = jogo_real.medir(tamanhos=(8,), mapas_por_tamanho=3, sorteios=2)
    assert mapas, "a amostra nao pode ser vazia, senao o teste passa sem medir nada"
    for nome, contagem in desfechos.items():
        assert sum(contagem.values()) == len(mapas) * 2, nome


def test_a_tabela_tem_uma_linha_por_estrategia():
    _, desfechos = jogo_real.medir(tamanhos=(8,), mapas_por_tamanho=2, sorteios=1)
    linhas = jogo_real.tabela(desfechos).splitlines()
    assert len(linhas) == 2 + len(jogo_real.ESTRATEGIAS_MEDIDAS)


def test_o_guloso_nao_desmaia_no_jogo_real_nos_mapas_pequenos():
    """O achado da secao 8 que sobrevive a batalha: o guloso falha por nao sair, nao por desmaiar."""
    _, desfechos = jogo_real.medir(tamanhos=(8,), mapas_por_tamanho=8, sorteios=5)
    assert desfechos["guloso"]["sem energia"] == 0


def test_escolher_mapas_devolve_so_mapas_que_o_bot_vence_com_o_tanque_pedido():
    mapas = jogo_real.escolher_mapas((8,), 12, 1.5)
    assert mapas, "a amostra nao pode ser vazia"
    for tamanho, seed, tanque in mapas:
        minimo, _ = jogo_real.api_greedy.menor_tanque(tamanho, seed)
        assert minimo is not None
        assert tanque == round(minimo * 1.5)
    # seeds sem solucao ficam de fora: a lista nao pode ter mais mapas que seeds pedidas
    assert len(mapas) <= 12
