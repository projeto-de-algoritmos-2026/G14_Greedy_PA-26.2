"""O mapa do jogo: a celula (GridSquare) e a matriz (Grid)."""
import random

from rich import print

# Conteudo possivel de uma celula.
INACESSIVEL = 0
LIVRE = 1
POKEMON = 2
POKEBOLA = 3
CPU = 4
SURF = 5
# CENTRO entrou no trabalho 2: e onde a energia recarrega. Diferente dos
# outros conteudos, nao some quando pisado (e um predio, nao um item), entao
# o mesmo centro serve pra varias paradas.
CENTRO = 6
VISITADO = -1

EMOJI = {
    INACESSIVEL: "\U0001F6B7",
    LIVRE: "\U0001F334",
    POKEMON: "\U0001F994",
    POKEBOLA: "\U000026D4",
    CPU: "\U0001F94A",
    SURF: "\U0001F3C4",
    CENTRO: "\U0001F3E5",
    VISITADO: "\U00002705",
}

EMOJI_JOGADOR = "\U0001FAE1"

# Terreno. O jogo ja sorteava esse campo e nunca o lia; a fase 2 passa a
# usa-lo como peso do grafo (graph/cost.py) e, no caso da agua, como o que
# decide se a aresta existe (graph/adapter.py).
GRAMA = 'grass'
AGUA = 'water'
CONCRETO = 'concrete'
TERRENOS = [GRAMA, AGUA, CONCRETO]

# Fracao das celulas que vira Centro Pokemon. Com 8x8 da 5 centros, com 30x30
# da 72. Calibrada no benchmark da fase 5: com 4% a maioria das rotas do 8x8 e
# do 15x15 nao passava por centro nenhum, e sem centro na rota toda estrategia
# de parada empata.
DENSIDADE_CENTRO = 0.08


class GridSquare:
    # SURF entrou na fase 2: e o item que concede a habilidade de atravessar
    # agua. Ele tinha que ser item de mapa (decisao do Lucas) justamente pra
    # que o grafo mude de forma durante a partida, e nao so de peso.
    OPCOES = [INACESSIVEL, LIVRE, POKEMON, POKEBOLA, CPU, SURF]
    DISTRIBUICAO = [.02, .58, .13, .05, .10, .02]

    def __init__(self, rng=None):
        """rng permite reproduzir um mapa: veja Grid(size, seed)."""
        rng = rng or random
        self.terrain = rng.choice(TERRENOS)
        self.occupied_with = rng.choices(self.OPCOES, self.DISTRIBUICAO)[0]

    @property
    def acessivel(self):
        """Se o CONTEUDO da celula permite entrar. Nao olha terreno."""
        return self.occupied_with != INACESSIVEL

    @property
    def e_agua(self):
        return self.terrain == AGUA

    def pisavel(self, surf=False):
        """A unica definicao de passabilidade do projeto.

        mover() (game.py) e vizinhos() (graph/adapter.py) chamam este metodo.
        Se cada um tivesse a sua propria regra, o bot planejaria rota que o
        jogo recusa, ou desistiria de rota que o jogo aceita.
        """
        return self.acessivel and (surf or not self.e_agua)

    def __repr__(self):
        return EMOJI.get(self.occupied_with, "")


class Grid:
    def __init__(self, size=8, seed=None, centros=None):
        """size e seed sao o que torna o benchmark da fase 6 reproduzivel.

        O RNG e proprio do Grid: dois mapas com a mesma seed sao iguais mesmo
        que outra parte do programa sorteie coisas entre a criacao dos dois.
        """
        self.size = size
        self.seed = seed
        self.rng = random.Random(seed)
        self.grid = [[GridSquare(self.rng) for _ in range(size)] for _ in range(size)]
        # A posicao de partida precisa ser pisavel, e o jogador NAO mora dentro
        # da matriz: a posicao dele vive so em row_pos/col_pos. Desde a fase 2
        # o terreno tambem e forcado: agua na origem prenderia o jogador no
        # canto, porque ele comeca sem surf.
        self.grid[0][0].occupied_with = LIVRE
        self.grid[0][0].terrain = CONCRETO
        self.row_pos, self.col_pos = 0, 0
        self._tirar_surf_da_agua()
        self._espalhar_centros(centros)

    def _espalhar_centros(self, quantidade=None):
        """Transforma celulas LIVRE em CENTRO depois que o mapa ja existe.

        O sorteio acontece DEPOIS de todas as celulas, com o mesmo RNG. Por
        isso o mapa de uma seed continua identico ao do trabalho 1 em tudo que
        nao e centro: o benchmark antigo segue reproduzivel e a comparacao
        entre os dois trabalhos usa os mesmos mapas.

        So entra celula LIVRE, fora da origem e fora da agua. LIVRE porque um
        centro em cima de pokemon ou CPU somaria batalha a parada; fora da agua
        pra que centro nao seja premio exclusivo de quem tem surf, o mesmo
        cuidado que _tirar_surf_da_agua tem com o item de surf. Com isso o custo
        de entrar num centro e so o do terreno, igual ao de uma celula livre, e
        as rotas do trabalho 1 nao mudam.
        """
        candidatas = [
            (r, c)
            for r, linha in enumerate(self.grid)
            for c, celula in enumerate(linha)
            if (r, c) != (0, 0)
            and celula.occupied_with == LIVRE
            and celula.terrain != AGUA
        ]
        if quantidade is None:
            quantidade = max(1, round(self.size * self.size * DENSIDADE_CENTRO))
        quantidade = min(quantidade, len(candidatas))
        for r, c in self.rng.sample(candidatas, quantidade):
            self.grid[r][c].occupied_with = CENTRO

    def centros(self):
        """Posicoes de todos os centros, em ordem de linha."""
        return [
            (r, c)
            for r, linha in enumerate(self.grid)
            for c, celula in enumerate(linha)
            if celula.occupied_with == CENTRO
        ]

    def _tirar_surf_da_agua(self):
        """O item de Surf nao nasce em celula de agua.

        Sem isso o item que CONCEDE a travessia da agua pode nascer dentro da
        agua, e ai ele exige Surf pra ser alcancado: e inatingivel por
        construcao, nao por topologia do mapa. Isso nao e o mesmo fenomeno que
        a fase 2 documentou (item que cai num componente separado da origem),
        e uma contradicao da propria geracao.

        A correcao troca o TERRENO da celula, nao a posicao do item: mover o
        item mudaria a distribuicao de conteudo do mapa, e o que esta errado
        aqui e o par (conteudo, terreno), nao onde o item caiu.
        """
        for linha in self.grid:
            for celula in linha:
                if celula.occupied_with == SURF and celula.terrain == AGUA:
                    celula.terrain = CONCRETO

    @property
    def posicao(self):
        return self.row_pos, self.col_pos

    def dentro(self, row, col):
        return 0 <= row < self.size and 0 <= col < self.size

    def celula(self, row, col):
        return self.grid[row][col]

    def desenhar(self):
        """Devolve o mapa como texto, com o jogador desenhado na posicao dele."""
        linhas = []
        for r, linha in enumerate(self.grid):
            simbolos = []
            for c, celula in enumerate(linha):
                if (r, c) == self.posicao:
                    simbolos.append(EMOJI_JOGADOR)
                else:
                    simbolos.append(str(celula))
            linhas.append(" ".join(simbolos))
        return "\n".join(linhas)

    def print_grid(self):
        print(self.desenhar())
