"""marcos_da_rota: a ponte entre a rota do Dijkstra e o caminhoneiro.

Os testes do guloso usam marcos montados a mao. Aqui o que se confere e que
os marcos tirados de um mapa de verdade dizem o mesmo que o grafo: o custo
acumulado no destino e o custo que o Dijkstra calculou, e os centros aparecem
onde o grid os colocou.
"""
import pytest

import grid
from graph.search import dijkstra, dijkstra_distancias
from graph.state import Estado
from greedy import marcos_da_rota, paradas, paradas_forca_bruta

ESTADO = Estado(hp_lider=100)


@pytest.fixture
def mapa():
    g = grid.Grid(size=4, seed=5, centros=0)
    for linha in g.grid:
        for celula in linha:
            celula.occupied_with = grid.LIVRE
            celula.terrain = grid.CONCRETO
    return g


class TestMapaMontadoAMao:
    def test_concreto_custa_um_por_passo(self, mapa):
        caminho = [(0, 0), (0, 1), (0, 2), (0, 3)]
        assert marcos_da_rota(caminho, mapa, ESTADO) == [
            (0, False), (1, False), (2, False), (3, False)]

    def test_centro_aparece_marcado(self, mapa):
        mapa.celula(0, 2).occupied_with = grid.CENTRO
        caminho = [(0, 0), (0, 1), (0, 2), (0, 3)]
        assert [e for _, e in marcos_da_rota(caminho, mapa, ESTADO)] == [
            False, False, True, False]

    def test_grama_soma_o_custo_da_grama(self, mapa):
        # HP 100: grama custa 3, concreto 1.
        mapa.celula(0, 1).terrain = grid.GRAMA
        caminho = [(0, 0), (0, 1), (0, 2)]
        assert [c for c, _ in marcos_da_rota(caminho, mapa, ESTADO)] == [0, 3, 4]

    def test_custo_da_origem_nao_entra(self, mapa):
        # O jogador ja esta na origem: o terreno dela nao e cobrado.
        mapa.celula(0, 0).terrain = grid.GRAMA
        assert marcos_da_rota([(0, 0), (0, 1)], mapa, ESTADO) == [
            (0, False), (1, False)]

    def test_rota_so_com_a_origem(self, mapa):
        assert marcos_da_rota([(0, 0)], mapa, ESTADO) == [(0, False)]


def _rotas_reais():
    """Uma rota por mapa: da origem ate a celula alcancavel mais cara.

    Mapas com a origem ilhada (nenhum vizinho pisavel) ficam de fora, como em
    rotas_descartes.csv do trabalho 1: a rota teria so a origem. Devolve lista,
    e nao gerador, porque o parametrize da classe reaproveita os parametros em
    cada teste.
    """
    rotas = []
    for size in (8, 15, 30):
        for seed in range(30):
            g = grid.Grid(size=size, seed=seed)
            distancias, _ = dijkstra_distancias((0, 0), g, ESTADO)
            destino = max(distancias, key=lambda p: (distancias[p], p))
            if destino != (0, 0):
                rotas.append(pytest.param(g, destino,
                                          id=f"{size}x{size}-seed{seed}"))
    return rotas


def _menor_alcance_viavel(marcos):
    """O maior trecho entre pontos de recarga consecutivos (origem, centros,
    destino): com esse tanque a rota e viavel e parar em todo centro apertado
    e obrigatorio. Abaixo dele nao ha solucao."""
    recargas = [c for i, (c, e) in enumerate(marcos)
                if i == 0 or i == len(marcos) - 1 or e]
    return max(b - a for a, b in zip(recargas, recargas[1:]))


@pytest.mark.parametrize("mapa_real, destino", _rotas_reais())
class TestMapasGerados:
    def test_custo_final_e_o_do_dijkstra(self, mapa_real, destino):
        caminho, custo, _ = dijkstra((0, 0), destino, mapa_real, ESTADO)
        marcos = marcos_da_rota(caminho, mapa_real, ESTADO)
        assert len(marcos) == len(caminho)
        assert marcos[-1][0] == custo

    def test_custo_acumulado_cresce_a_cada_passo(self, mapa_real, destino):
        caminho, _, _ = dijkstra((0, 0), destino, mapa_real, ESTADO)
        custos = [c for c, _ in marcos_da_rota(caminho, mapa_real, ESTADO)]
        assert all(b > a for a, b in zip(custos, custos[1:]))

    def test_centros_batem_com_o_grid(self, mapa_real, destino):
        caminho, _, _ = dijkstra((0, 0), destino, mapa_real, ESTADO)
        marcos = marcos_da_rota(caminho, mapa_real, ESTADO)
        centros = set(mapa_real.centros())
        assert [e for _, e in marcos] == [p in centros for p in caminho]

    def test_guloso_otimo_sobre_a_rota_real(self, mapa_real, destino):
        """O mesmo confronto com a forca bruta, agora em rota de mapa gerado.
        Testa do menor tanque viavel ate o que cobre a rota inteira, e um
        abaixo do menor, onde os dois tem que concordar que nao ha solucao."""
        caminho, custo, _ = dijkstra((0, 0), destino, mapa_real, ESTADO)
        marcos = marcos_da_rota(caminho, mapa_real, ESTADO)
        minimo = _menor_alcance_viavel(marcos)
        for alcance in sorted({minimo - 1, minimo, (minimo + custo) // 2, custo}):
            if alcance <= 0:
                continue
            guloso = paradas(marcos, alcance)
            otima = paradas_forca_bruta(marcos, alcance)
            assert (guloso is None) == (otima is None) == (alcance < minimo)
            if guloso is not None:
                assert len(guloso) == len(otima)
