"""Executa uma escolha de paradas sobre os marcos, sem mapa e sem jogo.

E a conta que separa as estrategias: dadas as paradas, o treinador chega ou
desmaia? Quantas vezes parou de fato? Quanta energia ainda tinha no tanque
quando recarregou? A ultima e o desperdicio: parar cedo demais joga fora
energia que levaria mais longe, e e por isso que parar tarde nao e parar
pouco nem parar mal.

O modelo e o mesmo do jogo: cada passo gasta o custo de entrar no marco
seguinte, sem energia pra pagar o passo o treinador desmaia onde esta, e
parar num centro enche o tanque.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Simulacao:
    chegou: bool
    paradas: int
    # Indice do ultimo marco alcancado antes de desmaiar. None quando chegou.
    desmaio_em: int | None
    # Soma do que restava no tanque a cada recarga.
    energia_desperdicada: int
    # Custo percorrido ate chegar ou desmaiar.
    energia_gasta: int
    # O que sobrou no tanque no ultimo marco alcancado.
    energia_final: int


def simular(marcos, alcance, escolhidas, energia_inicial=None):
    """Anda pelos marcos parando em `escolhidas` e conta o que aconteceu.

    Paradas depois do ponto de desmaio nao acontecem e nao entram na conta.
    `escolhidas` precisa ter so centros, fora da origem e do destino: e o
    contrato das estrategias, e uma parada fora dele e erro de quem chamou.
    """
    if alcance <= 0:
        raise ValueError("alcance deve ser positivo")
    if not marcos:
        raise ValueError("marcos vazio: a rota precisa ter ao menos a origem")
    destino_idx = len(marcos) - 1
    for i in escolhidas:
        if not (0 < i < destino_idx) or not marcos[i][1]:
            raise ValueError(f"parada {i} nao e centro entre origem e destino")

    energia = alcance if energia_inicial is None else energia_inicial
    paradas_em = set(escolhidas)
    feitas = 0
    desperdicio = 0

    for i in range(1, len(marcos)):
        passo = marcos[i][0] - marcos[i - 1][0]
        if passo > energia:
            return Simulacao(False, feitas, i - 1, desperdicio,
                             marcos[i - 1][0] - marcos[0][0], energia)
        energia -= passo
        if i in paradas_em:
            desperdicio += energia
            energia = alcance
            feitas += 1

    return Simulacao(True, feitas, None, desperdicio,
                     marcos[destino_idx][0] - marcos[0][0], energia)
