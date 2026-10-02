"""Algoritmos gulosos do trabalho 2 (modulo Algoritmos Ambiciosos).

O caminhoneiro trabalha SOBRE a rota que o Dijkstra ja escolheu: ele nao
escolhe caminho, escolhe onde parar pra recarregar. Ver greedy/caminhoneiro.py.
"""
from .caminhoneiro import marcos_da_rota, paradas
from .forca_bruta import paradas_forca_bruta, viavel

__all__ = ["marcos_da_rota", "paradas", "paradas_forca_bruta", "viavel"]
