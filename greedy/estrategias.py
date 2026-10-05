"""Estrategias de parada que o bot e o benchmark comparam com o guloso.

Todas tem a mesma assinatura do caminhoneiro:

    estrategia(marcos, alcance, energia_inicial=None) -> indices | None

e devolvem os indices (em `marcos`) dos centros onde parar, na ordem da
rota. So o guloso e o otimo sabem quando a rota nao tem solucao e devolvem
None. As rivais nao sabem: decidem as paradas pela regra delas e quem
descobre o desmaio e a execucao.

As rivais existem pra mostrar a tese do trabalho, de que parar tarde nao e
parar pouco:

- todo_centro para em todos os centros da rota. Nunca desmaia se a rota
  tiver solucao, mas para demais.
- limiar(pct) e a regra que um jogador humano usaria: passa direto pelo
  centro enquanto a energia esta acima de pct% do tanque. Com limiar alto
  para demais; com limiar baixo desmaia entre dois centros.
"""
from .caminhoneiro import paradas
from .forca_bruta import candidatos, paradas_forca_bruta

# Acima disso a forca bruta (2^k) deixa de ser referencia pratica.
MAX_CENTROS_OTIMO = 20


def guloso(marcos, alcance, energia_inicial=None):
    """O caminhoneiro: para no centro mais distante que o tanque alcanca."""
    return paradas(marcos, alcance, energia_inicial)


def todo_centro(marcos, alcance, energia_inicial=None):
    """Para em todo centro da rota, fora a origem e o destino."""
    return candidatos(marcos)


def limiar(pct):
    """Estrategia que para no centro quando a energia esta em pct% ou menos.

    A conta e feita em inteiros (energia * 100 <= pct * alcance) pra que o
    limite exato, como 5 de 20 em 25%, nao dependa de arredondamento.
    """
    if not 0 < pct < 100:
        raise ValueError("pct deve estar entre 0 e 100")

    def estrategia(marcos, alcance, energia_inicial=None):
        energia = alcance if energia_inicial is None else energia_inicial
        escolhidas = []
        for i in range(1, len(marcos) - 1):
            energia -= marcos[i][0] - marcos[i - 1][0]
            if energia < 0:
                # Desmaiaria antes daqui. As paradas seguintes nao acontecem,
                # e quem registra o desmaio e a execucao.
                break
            if marcos[i][1] and energia * 100 <= pct * alcance:
                escolhidas.append(i)
                energia = alcance
        return escolhidas

    estrategia.__name__ = f"limiar_{pct}"
    estrategia.__doc__ = f"Para no centro com energia em {pct}% do tanque ou menos."
    return estrategia


def otimo(marcos, alcance, energia_inicial=None):
    """Referencia por forca bruta. So em rotas com poucos centros."""
    if len(candidatos(marcos)) > MAX_CENTROS_OTIMO:
        raise ValueError(
            f"otimo por forca bruta so ate {MAX_CENTROS_OTIMO} centros na rota")
    return paradas_forca_bruta(marcos, alcance, energia_inicial)


ESTRATEGIAS = {
    "guloso": guloso,
    "todo_centro": todo_centro,
    "limiar_10": limiar(10),
    "limiar_25": limiar(25),
    "limiar_50": limiar(50),
    "otimo": otimo,
}
