// Cliente da API. E a unica porta do front para o servidor: nenhuma tela faz
// fetch nem abre EventSource por conta propria, entao o contrato /api/t2/* vive
// num lugar so e a tela nunca precisa saber de URL.
//
// Nenhuma regra do jogo mora aqui ou em qualquer modulo do front: custo, desmaio,
// recarga e viabilidade do alcance vem prontos do servidor.

const BASE = "/api/t2";

function consulta(parametros) {
  const limpos = Object.entries(parametros).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return limpos.length ? "?" + new URLSearchParams(limpos).toString() : "";
}

async function pegar(caminho, parametros = {}) {
  const resposta = await fetch(BASE + caminho + consulta(parametros));
  let corpo = null;
  try {
    corpo = await resposta.json();
  } catch {
    // corpo nao e JSON: cai no erro de status abaixo
  }
  if (!resposta.ok) {
    throw new Error((corpo && corpo.erro) || `${caminho}: HTTP ${resposta.status}`);
  }
  return corpo;
}

export const api = {
  config: () => pegar("/config"),
  benchmark: () => pegar("/benchmark"),
  alcance: (size, seed, alcance) => pegar("/alcance", { size, seed, alcance }),
  comparar: (size, seed, energia, algoritmo) => pegar("/comparar", { size, seed, energia, algoritmo }),

  jogoNovo: (size, seed, energia) => pegar("/jogo/novo", { size, seed, energia }),
  jogoEstado: (sessao) => pegar("/jogo/estado", { sessao }),
  jogoMover: (sessao, direcao) => pegar("/jogo/mover", { sessao, direcao }),
  jogoRecarregar: (sessao) => pegar("/jogo/recarregar", { sessao }),
};

// Partida do bot ao vivo (SSE). Devolve um objeto com `fechar()`.
//
// Os eventos chegam na ordem em que o bot os produz, nao em replay: `inicio`,
// e por plano `plano`, `paradas`, varios `passo` e, se a estrategia mandou
// parar, uma `recarga`; por fim `fim`. `aoEvento(nome, dados)` recebe todos.
// Erro de rede ou do servidor vira `aoErro(mensagem)` e fecha a conexao: o
// EventSource reconectaria sozinho e repetiria a partida do zero.
export function partidaAoVivo({ size, seed, algoritmo, estrategia, energia }, aoEvento, aoErro) {
  const url = `${BASE}/partida` + consulta({ size, seed, algoritmo, estrategia, energia });
  const fonte = new EventSource(url);
  let encerrada = false;

  const fechar = () => {
    encerrada = true;
    fonte.close();
  };

  for (const nome of ["inicio", "plano", "paradas", "passo", "recarga", "fim"]) {
    fonte.addEventListener(nome, (evento) => {
      if (encerrada) return;
      aoEvento(nome, JSON.parse(evento.data));
      if (nome === "fim") fechar();
    });
  }
  fonte.onerror = () => {
    if (encerrada) return;
    fechar();
    if (aoErro) aoErro("a conexao com o servidor caiu no meio da partida");
  };
  return { fechar };
}
