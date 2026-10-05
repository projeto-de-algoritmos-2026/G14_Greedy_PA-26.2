// Ponto de entrada. Carrega a config e o snapshot do servidor, monta as telas e
// abre a aba da URL. Se o servidor nao responder, a pagina diz, em vez de
// ficar em branco.

import { api } from "./api.js";
import { estado, registrar, iniciarAbas, abrir, abaDaUrl } from "./estado.js";
import { montarLegenda } from "./legenda.js";
import { criarTelaJogo } from "./jogo.js";
import { criarTelaBot } from "./bot.js";
import { criarTelaComparar } from "./comparar.js";
import { criarTelaBenchmark } from "./benchmark.js";

async function iniciar() {
  try {
    estado.config = await api.config();
  } catch (erro) {
    document.querySelector("main").innerHTML =
      `<div class="erro-tela"><b>Não consegui falar com o servidor.</b><br>${erro.message}<br><small>Rode <code>python -m webdemo</code> e recarregue a página.</small></div>`;
    return;
  }
  // o snapshot e opcional: sem ele so a aba Benchmark fica sem dados
  try {
    estado.benchmark = await api.benchmark();
  } catch {
    estado.benchmark = { erro: "sem snapshot do benchmark" };
  }

  const meta = estado.config.meta;
  document.querySelectorAll("[data-meta]").forEach((el) => (el.textContent = `${meta} Pokémon`));
  montarLegenda(document.getElementById("dr-legenda"), document.getElementById("btn-legenda"), estado.config);

  registrar("jogo", criarTelaJogo());
  registrar("bot", criarTelaBot());
  registrar("comparar", criarTelaComparar());
  registrar("bench", criarTelaBenchmark());
  iniciarAbas();
  abrir(abaDaUrl());
}

iniciar();
