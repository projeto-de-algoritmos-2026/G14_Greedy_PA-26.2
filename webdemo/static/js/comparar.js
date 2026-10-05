// Tela Comparar: as seis estrategias jogando a MESMA missao, lado a lado.
//
// Decisao do Lucas: cada raia e uma execucao real do bot (nao a rota planejada
// concatenada). O servidor devolve, por raia, o desfecho e a linha do tempo; a
// tela so desenha. O veredito tambem vem do servidor.
//
// A "corrida" e uma animacao do corredor sobre a regua de cada raia: ele anda
// ate onde aquele bot realmente chegou (ou cai onde desmaiou). Nada e simulado.

import { api } from "./api.js";
import { estado } from "./estado.js";
import { desenharRegua, descreverRegua } from "./regua.js";
import { montarPresets } from "./alcance.js";

const $ = (s) => document.querySelector(s);
const DURACAO_MS = 7000;

export function criarTelaComparar() {
  const C = { alcance: null, raf: null, raias: [], carregando: 0, dados: null };

  function cartao(r) {
    if (!r.disponivel) {
      return `<div class="lane" data-id="${r.estrategia}"><div><div class="nome">${r.nome}</div><div class="desc">${r.descricao}</div></div>
        <svg role="img" aria-label="indisponível"></svg>
        <div class="res"><span class="badge na">Indisponível</span><div class="desc" style="grid-column:1/-1">${r.motivo_indisponivel}</div></div></div>`;
    }
    const selo = r.venceu
      ? `<span class="badge ok">Chega</span>`
      : `<span class="badge bad">${r.motivo === "sem energia" ? `Desmaia no custo ${r.desmaio_em}` : r.motivo}</span>`;
    return `<div class="lane" data-id="${r.estrategia}"><div><div class="nome">${r.nome}</div><div class="desc">${r.descricao}</div></div>
      <svg role="img"></svg>
      <div class="res">${selo}
        <div class="stat"><div class="k">Paradas</div><div class="v">${r.paradas}</div></div>
        <div class="stat"><div class="k">Desperdício</div><div class="v">${r.energia_desperdicada}</div></div>
        <div class="stat"><div class="k">Pokémon</div><div class="v">${r.pokemon}/${r.meta}</div></div></div></div>`;
  }

  function veredito(d) {
    const v = d.veredito;
    const nome = (id) => (d.raias.find((r) => r.estrategia === id) || {}).nome || id;
    const el = $("#c-verdict");
    if (v.menos_paradas === null) {
      el.innerHTML = `<p class="tese">Nenhuma estratégia cumpre a missão com alcance ${d.alcance}. Aumente o tanque.</p>`;
      return;
    }
    const falharam = v.falharam.length
      ? ` ${v.falharam.length} estratégia(s) <b style="color:var(--red)">não cumprem a missão</b>: ${v.falharam.map(nome).join(", ")}.` : "";
    const nao = v.indisponiveis.length ? ` ${v.indisponiveis.map(nome).join(", ")}: indisponível nesta rota.` : "";
    const empate = v.vencedoras.length > 1 ? "empatam" : "vence";
    el.innerHTML = `<div class="stat"><div class="k">Menos paradas que cumprem</div><div class="v"><b>${v.menos_paradas}</b></div></div>
      <p class="tese">${v.vencedoras.map(nome).join(", ")} ${empate} com ${v.menos_paradas} parada(s).${falharam}${nao}
      O limiar humano ("paro quando a energia fica baixa") ou para demais ou desmaia; o guloso só para quando precisa.
      <small>Cada raia é uma execução real do bot, com a mesma semente e o mesmo tanque.</small></p>`;
  }

  function montarRaias(d) {
    $("#c-lanes").innerHTML = d.raias.map(cartao).join("");
    // Comparar e por o mesmo custo no mesmo lugar: todas as reguas dividem UM eixo,
    // o da raia que mais andou. Com eixos proprios, quem desmaia em 116 parecia
    // ter andado tanto quanto quem terminou em 192.
    const eixo = Math.max(...d.raias.filter((r) => r.disponivel).map((r) => r.custo_total), 1);
    C.raias = d.raias.map((r) => {
      const el = document.querySelector(`.lane[data-id="${r.estrategia}"]`);
      if (!r.disponivel) return { r, el, regua: null, fim: 0 };
      const svg = el.querySelector("svg");
      const regua = desenharRegua(svg, { marcos: r.linha, alcance: d.alcance, total: eixo, chegou: r.venceu });
      svg.setAttribute("aria-label", `${r.nome}: ${descreverRegua(r.linha, r.custo_total)}`);
      return { r, el, regua, fim: r.venceu ? r.custo_total : (r.desmaio_em ?? r.custo_total) };
    });
    veredito(d);
    $("#c-go").textContent = "▶ Largar corrida";
  }

  function correr() {
    if (C.raf) cancelAnimationFrame(C.raf);
    if (!C.dados) return;
    C.raias.forEach((x) => { x.el.classList.remove("win"); if (x.regua) x.regua.mover(0); });
    const t0 = performance.now();
    $("#c-go").textContent = "↻ Reiniciar";
    const reduzido = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const maior = Math.max(...C.raias.map((x) => x.r.custo_total || 0), 1);
    (function quadro(agora) {
      const p = reduzido ? 1 : Math.min(1, (agora - t0) / DURACAO_MS);
      C.raias.forEach((x) => {
        if (x.regua) x.regua.mover(Math.min(p * maior, x.fim));
      });
      if (p < 1) { C.raf = requestAnimationFrame(quadro); return; }
      const vencem = new Set(C.dados.veredito.vencedoras);
      C.raias.forEach((x) => { if (vencem.has(x.r.estrategia)) x.el.classList.add("win"); });
    })(t0);
  }

  async function carregar() {
    const ticket = ++C.carregando;
    if (C.raf) cancelAnimationFrame(C.raf);
    $("#c-lanes").classList.add("calculando");
    $("#c-go").disabled = true;
    $("#c-verdict").innerHTML = `<p class="tese">Calculando: o bot joga a missão inteira seis vezes (pode levar alguns segundos em mapas grandes).</p>`;
    const size = Number($("#c-size").value) || 8;
    const seed = Number($("#c-seed").value) || 0;
    try {
      const dados = await api.comparar(size, seed, C.alcance ?? undefined);
      if (ticket !== C.carregando) return; // chegou uma resposta mais nova no meio
      C.dados = dados;
      if (C.alcance === null) C.alcance = dados.alcance;
      $("#c-alc").value = dados.alcance;
      $("#c-alc-v").textContent = dados.alcance;
      montarRaias(dados);
      api.alcance(size, seed, dados.alcance).then((a) => {
        montarPresets($("#c-presets"), a, dados.alcance, (valor) => { C.alcance = valor; carregar(); });
      }).catch(() => {});
    } catch (erro) {
      if (ticket !== C.carregando) return;
      $("#c-verdict").innerHTML = `<p class="tese"><b style="color:var(--red)">Não consegui comparar:</b> ${erro.message}</p>`;
    } finally {
      if (ticket === C.carregando) {
        $("#c-lanes").classList.remove("calculando");
        $("#c-go").disabled = false;
      }
    }
  }

  let ligada = false;
  return {
    abrir() {
      if (!ligada) {
        ligada = true;
        $("#c-go").onclick = () => { if (C.dados) correr(); };
        $("#c-size").onchange = $("#c-seed").onchange = () => { C.alcance = null; C.dados = null; carregar(); };
        $("#c-alc").oninput = (e) => { $("#c-alc-v").textContent = e.target.value; };
        $("#c-alc").onchange = (e) => { C.alcance = Number(e.target.value); carregar(); };
      }
      if (!C.dados) carregar();
    },
    fechar() { if (C.raf) cancelAnimationFrame(C.raf); },
  };
}
