"""Algoritmos gulosos do trabalho 2 (modulo Algoritmos Ambiciosos).

O caminhoneiro trabalha SOBRE a rota que o Dijkstra ja escolheu: ele nao
escolhe caminho, escolhe onde parar pra recarregar. Ver greedy/caminhoneiro.py.
"""
from .caminhoneiro import marcos_da_rota, paradas
from .estrategias import ESTRATEGIAS
from .forca_bruta import paradas_forca_bruta, viavel
from .viabilidade import alcance_minimo, trecho_critico, viabilidade

__all__ = ["ESTRATEGIAS", "alcance_minimo", "marcos_da_rota", "paradas",
           "paradas_forca_bruta", "trecho_critico", "viabilidade", "viavel"]
