"""
Created on Mon Feb 8
A Pokemon clone for the terminal.
@author: Andrew Alagna

Ponto de entrada. As regras vivem em game.py, o mapa em grid.py, as entidades
em models.py e a conversa com o jogador em ui.py.
"""
import argparse

from rich import print

from bot.runner import jogar_com_bot
from greedy.estrategias import ESTRATEGIAS
from ui import playing_game, starting_player_info


def parse_args():
    p = argparse.ArgumentParser(description="Pokemon Py")
    p.add_argument("--size", type=int, default=8, help="lado do mapa quadrado")
    p.add_argument("--seed", type=int, default=None, help="semente do mapa, para reproduzir uma partida")
    modos = p.add_mutually_exclusive_group()
    modos.add_argument("--bot", action="store_true", help="joga automaticamente")
    modos.add_argument("--human", action="store_true", help="joga com comandos no terminal")
    p.add_argument("--visual", action="store_true", help="mostra o mapa a cada passo do bot")
    p.add_argument("--energia", type=int, default=None,
                   help="tamanho do tanque de energia; sem ele a partida nao usa energia")
    p.add_argument("--estrategia", choices=ESTRATEGIAS, default=None,
                   help="onde o bot para pra recarregar (exige --bot e --energia)")
    args = p.parse_args()
    if args.energia is not None and args.energia <= 0:
        p.error("--energia deve ser positiva")
    if args.estrategia is not None and not (args.bot and args.energia):
        p.error("--estrategia exige --bot e --energia")
    return args


if __name__ == "__main__":
    args = parse_args()
    player = starting_player_info()
    if args.energia is not None:
        player.energia = player.energia_max = args.energia
    print(f"Hello {player.name}, get ready to play Pokemon Py!")
    if args.bot:
        resultado = jogar_com_bot(
            player, size=args.size, seed=args.seed, visual=args.visual,
            estrategia=ESTRATEGIAS.get(args.estrategia),
        )
        print(
            f"Bot finished: {len(resultado.objetivos_visitados)} objectives, "
            f"{len(resultado.movimentos)} steps ({resultado.motivo_parada})."
        )
        if args.estrategia:
            print(
                f"Strategy {args.estrategia}: {resultado.paradas} stops, "
                f"{resultado.energia_desperdicada} energy wasted."
            )
    else:
        playing_game(player, size=args.size, seed=args.seed)
