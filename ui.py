"""Camada de interacao com o jogador humano.

Tudo que le do teclado e escreve na tela durante a exploracao mora aqui. O
game.py nao sabe que existe terminal, e e isso que permite o bot da fase 5
jogar a mesma partida sem ninguem digitando.
"""
import random

from rich import print

from game import DIRECOES, mover, partida_encerrada, recarregar
from grid import Grid
from models import Player, Pokemon

PROMPT_DIRECAO = "Do you want to go W (up), A (left), S (down), or D (right)? "
PROMPT_ERRO = "You cannot move there. Try again, Enter W/A/S/D to move in a different direction: "
TECLA_RECARGA = "R"


def passo_do_jogador(grid, player):
    """Pede direcoes ate uma valer, aplica e devolve o Movimento.

    No original, a resposta dada ao prompt de erro era descartada: o laco
    voltava ao prompt do topo e sobrescrevia a direcao antes de usa-la. Aqui a
    resposta ao prompt de erro e a proxima tentativa de verdade.

    Com energia ligada, R recarrega com game.recarregar, a mesma acao que o
    bot usa. Recarregar nao e passo: o jogador continua no mesmo lugar e o
    prompt volta. Desmaiar devolve o Movimento invalido, porque nenhuma
    direcao vai valer depois disso.
    """
    grid.print_grid()
    prompt = _prompt_direcao(player)
    while True:
        direcao = input(prompt)
        if player.usa_energia and direcao.strip().upper() == TECLA_RECARGA:
            entrou = recarregar(grid, player)
            if entrou:
                print(f"You rested at the Pokemon Center: +{entrou} energy.", "[green]")
            else:
                print("Nothing to recharge here.")
            prompt = _prompt_direcao(player)
            continue
        movimento = mover(grid, player, direcao)
        if movimento.desmaiou:
            print("You ran out of energy and fainted!", "[red]")
            return movimento
        if movimento.valido:
            if movimento.pegou_pokebola:
                print("Sweet, you found a pokeball!!", "[red]")
            if movimento.pegou_surf:
                print("You learned Surf! You can cross water now.", "[cyan]")
            if movimento.em_centro and player.usa_energia:
                print(f"You are at a Pokemon Center. Enter {TECLA_RECARGA} to recharge.", "[green]")
            return movimento
        prompt = PROMPT_ERRO


def _prompt_direcao(player):
    if not player.usa_energia:
        return PROMPT_DIRECAO
    return (f"Energy {player.energia}/{player.energia_max}. Do you want to go W (up), "
            f"A (left), S (down), D (right), or {TECLA_RECARGA} to recharge? ")


def starting_player_info():
    player_name = input("Hello there! What is your name?: ")
    gender = input("What is your gender?: ")
    nature = input("How would you describe your nature?: ")
    starter_pokemon = input("Which pokemon do you want to start with? P - Pikachu, C - Charmander, or S - Squirtle?: ")
    starter_pokemon = choose_starter_pokemon(starter_pokemon)
    return Player(player_name, gender, nature, [starter_pokemon], {'potion': 3, 'pokeball': 3}, 10000)


def choose_starter_pokemon(starter_pokemon):
    while not starter_pokemon or starter_pokemon[0].upper() not in ('P', 'C', 'S'):
        starter_pokemon = input("Please enter the first letter P (Pikachu) , C (Charmander), or S (Squirtle) to choose "
                                "your starter pokemon")
    name = input('What do you want to name your pokemon?: ')
    inicial = starter_pokemon[0].upper()
    if inicial == 'P':
        return Pokemon(name, random.choice(["Male", "Female"]), "Pikachu", 'Electric', {'Shock': 40, 'Tail Whip': 25})
    elif inicial == 'C':
        return Pokemon(name, random.choice(["Male", "Female"]), "Charmander", 'Fire', {'Flamethrower': 40, 'Claw': 25})
    else:
        return Pokemon(name, random.choice(["Male", "Female"]), "Squirtle", 'Water', {'Hydropump': 40, 'Tackle': 25})


def playing_game(player, size=8, seed=None):
    grid = Grid(size=size, seed=seed)
    while not partida_encerrada(player):
        passo_do_jogador(grid, player)
    if len(player.pokemon_list) >= 4:
        print(f"Game over! You captured 4 pokemon {player.poke_list_names()}. Thanks for playing!", ":smile:")
    elif player.desmaiado:
        print("Game over! You fainted on the way. Thanks for playing!", ":smile:")
    else:
        print("Game over! You lost all of your pokemon. Thanks for playing!", ":smile:")
