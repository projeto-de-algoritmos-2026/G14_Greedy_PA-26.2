"""Servidor da demo. Biblioteca padrao, nenhuma dependencia nova.

    python -m webdemo

Casca fina: cada rota chama uma funcao de `webdemo/api.py` ou de
`webdemo/benchmark.py` e devolve o resultado como JSON. Nao ha regra de jogo
nem algoritmo aqui.

Streaming e SSE (`text/event-stream`), que a `http.server` sustenta sem
biblioteca: e uma resposta que nunca fecha, com um bloco de texto por evento, e
o navegador le com `EventSource`. Vale pra partida do bot e pro benchmark, os
dois casos em que o interesse esta em ver acontecer, nao em receber pronto.
"""

import argparse
import json
import mimetypes
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bench.common import ALGORITMOS, SEEDS, TAMANHOS

from greedy.estrategias import ESTRATEGIAS

from . import api, api_greedy
from .benchmark import eventos_benchmark

ESTATICOS = Path(__file__).resolve().parent / "static"

# `mimetypes` consulta o sistema, e no Windows (o README usa PowerShell) um .js
# pode sair como text/plain, que o navegador RECUSA como modulo ES. Fixar aqui.
TIPOS = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}

# Valor de `estrategia` que pede o bot do T1: anda a rota inteira sem parar.
SEM_ESTRATEGIA = "nenhuma"


def _primeiro(consulta, chave, padrao=None):
    valores = consulta.get(chave)
    return valores[0] if valores else padrao


def _lista(consulta, chave):
    bruto = _primeiro(consulta, chave, "")
    return [item for item in bruto.split(",") if item]


def _posicao(texto, padrao=(0, 0)):
    """Aceita destino no formato `linha-coluna`, que e como a URL o carrega."""
    try:
        linha, coluna = texto.split("-")
        return int(linha), int(coluna)
    except (AttributeError, ValueError):
        return padrao


class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "G14Demo/1.0"

    def log_message(self, formato, *args):
        """Silencia o log por requisicao: numa apresentacao o terminal fica
        visivel, e uma enxurrada de GET nao ajuda ninguem."""

    # ---------------- utilidades de resposta ----------------

    def _json(self, dados, status=200):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _abrir_stream(self):
        """Abre a resposta que nao fecha.

        `Connection: close` de proposito, apesar de HTTP/1.1: um corpo sem
        Content-Length so termina quando o socket fecha, e anunciar keep-alive
        aqui deixaria cliente e servidor discordando sobre onde a resposta
        acaba.
        """
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()

    def _evento(self, nome, dados):
        bloco = f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
        self.wfile.write(bloco.encode("utf-8"))
        self.wfile.flush()

    def _transmitir(self, gerador):
        """Despeja um gerador de (evento, dados) na conexao ate acabar.

        Fechar a aba no meio derruba o socket; isso e uso normal da demo, nao
        erro, entao a excecao morre aqui em vez de sujar o terminal.
        """
        self._abrir_stream()
        try:
            for nome, dados in gerador:
                self._evento(nome, dados)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _estatico(self, nome):
        caminho = (ESTATICOS / nome).resolve()
        if not caminho.is_file() or ESTATICOS not in caminho.parents:
            self._json({"erro": "nao encontrado"}, status=404)
            return
        corpo = caminho.read_bytes()
        tipo = (TIPOS.get(caminho.suffix.lower())
                or mimetypes.guess_type(caminho.name)[0]
                or "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    # ---------------- rotas ----------------

    def _rota_t2(self, rota, consulta):
        """Rotas do trabalho 2 (`/api/t2/*`). Devolve False se nao for uma delas.

        Casca fina sobre `webdemo/api_greedy.py`, no mesmo estilo do T1: parametros
        em query string, movimento do jogo por GET como em `/api/jogo/mover`.
        """
        size = api.limitar(_primeiro(consulta, "size"), 3, api.MAX_TAMANHO, 15)
        seed = api.limitar(_primeiro(consulta, "seed"), 0, api.MAX_SEED, 42)
        sessao = _primeiro(consulta, "sessao", "")

        if rota == "/api/t2/config":
            self._json(api_greedy.config())
        elif rota == "/api/t2/benchmark":
            self._json(api_greedy.benchmark())
        elif rota == "/api/t2/alcance":
            self._json(api_greedy.dados_alcance(size, seed, _primeiro(consulta, "alcance")))
        elif rota == "/api/t2/jogo/novo":
            self._json(api_greedy.criar_jogo(size, seed, _primeiro(consulta, "energia")))
        elif rota == "/api/t2/jogo/estado":
            self._json(api_greedy.estado_jogo(sessao))
        elif rota == "/api/t2/jogo/mover":
            self._json(api_greedy.mover_jogo(sessao, _primeiro(consulta, "direcao", "")))
        elif rota == "/api/t2/jogo/recarregar":
            self._json(api_greedy.recarregar_jogo(sessao))
        elif rota == "/api/t2/comparar":
            algoritmo = _primeiro(consulta, "algoritmo", "dijkstra")
            if algoritmo not in ALGORITMOS:
                self._json({"erro": f"algoritmo desconhecido: {algoritmo}"}, 400)
            else:
                try:
                    self._json(api_greedy.comparar(size, seed, _primeiro(consulta, "energia"), algoritmo))
                except RuntimeError as erro:
                    self._json({"erro": str(erro)}, 503)
        elif rota == "/api/t2/partida":
            algoritmo = _primeiro(consulta, "algoritmo", "dijkstra")
            estrategia = _primeiro(consulta, "estrategia", api_greedy.ESTRATEGIA_PADRAO)
            if estrategia == SEM_ESTRATEGIA:
                estrategia = None
            if algoritmo not in ALGORITMOS:
                self._json({"erro": f"algoritmo desconhecido: {algoritmo}"}, 400)
            elif estrategia is not None and estrategia not in ESTRATEGIAS:
                self._json({"erro": f"estrategia desconhecida: {estrategia}"}, 400)
            else:
                self._transmitir(api_greedy.eventos_partida(
                    size, seed, algoritmo, _primeiro(consulta, "energia"), estrategia))
        else:
            return False
        return True

    def do_GET(self):
        endereco = urlparse(self.path)
        rota = endereco.path
        consulta = parse_qs(endereco.query)

        if rota in ("/", "/index.html"):
            return self._estatico("index.html")
        # A demo do Trabalho 1, intacta, para comparar e como rede de seguranca.
        if rota in ("/t1", "/t1.html"):
            return self._estatico("t1.html")
        if rota in ("/t1.js", "/t1.css"):
            return self._estatico(rota.lstrip("/"))
        if rota.startswith("/static/"):
            return self._estatico(rota[len("/static/"):])
        if rota.startswith("/api/t2/") and self._rota_t2(rota, consulta):
            return

        if rota == "/api/config":
            return self._json({
                "algoritmos": list(ALGORITMOS),
                "tamanhos": list(TAMANHOS),
                "seeds": SEEDS,
            })

        size = api.limitar(_primeiro(consulta, "size"), 3, api.MAX_TAMANHO, 15)
        seed = api.limitar(_primeiro(consulta, "seed"), 0, api.MAX_SEED, 42)
        hp = api.limitar(_primeiro(consulta, "hp"), 0, 100, 100)
        surf = _primeiro(consulta, "surf", "0") in ("1", "true", "True")

        if rota == "/api/mapa":
            return self._json(api.dados_mapa(size, seed, hp, surf))

        if rota == "/api/seed-com-surf":
            de = api.limitar(_primeiro(consulta, "de"), 0, api.MAX_SEED, 0)
            return self._json(api.procurar_seed_com_surf(size, de))

        if rota == "/api/objetivos":
            limite = api.limitar(_primeiro(consulta, "limite"), 1, 6, 3)
            return self._json(api.dados_objetivos(size, seed, hp, surf, limite))

        if rota == "/api/rota":
            destino = _posicao(_primeiro(consulta, "destino"))
            algoritmos = _lista(consulta, "algoritmo") or None
            return self._json(api.dados_rota(size, seed, destino, algoritmos, hp, surf))

        if rota == "/api/partida":
            algoritmo = _primeiro(consulta, "algoritmo", "dijkstra")
            if algoritmo not in ALGORITMOS:
                return self._json({"erro": f"algoritmo desconhecido: {algoritmo}"}, 400)
            return self._transmitir(api.eventos_partida(size, seed, algoritmo))

        if rota == "/api/benchmark":
            tamanhos = [int(t) for t in _lista(consulta, "tamanhos")] or list(TAMANHOS)
            seeds = api.limitar(_primeiro(consulta, "seeds"), 1, 200, SEEDS)
            repeticoes = api.limitar(_primeiro(consulta, "repeticoes"), 1, 200, 25)
            experimento = _primeiro(consulta, "experimento", "ambos")
            if experimento not in ("rotas", "partidas", "ambos"):
                return self._json({"erro": f"experimento desconhecido: {experimento}"}, 400)
            return self._transmitir(eventos_benchmark(
                tamanhos=tamanhos, seeds=seeds, repeticoes=repeticoes,
                experimento=experimento,
            ))

        if rota == "/api/jogo/novo":
            return self._json(api.criar_jogo(size, seed))

        if rota == "/api/jogo/mover":
            sessao = _primeiro(consulta, "sessao", "")
            direcao = (_primeiro(consulta, "direcao", "") or "").upper()
            return self._json(api.mover_jogo(sessao, direcao))

        self._json({"erro": "rota desconhecida"}, status=404)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Demo web do G14")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--sem-navegador", action="store_true")
    args = parser.parse_args(argv)

    endereco = f"http://localhost:{args.porta}/"
    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), Manipulador)
    print(f"Demo do G14 em {endereco}   (ctrl+c encerra)")
    if not args.sem_navegador:
        webbrowser.open(endereco)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrado")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
