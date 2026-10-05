// Tela Benchmark, em tres paginas: Trabalho 1, Trabalho 2 e Juntos.
//
// So desenha o snapshot (webdemo/dados/benchmark.json), que vem dos CSVs
// consolidados de bench/out. NENHUM numero e calculado ou estimado aqui, e cada
// bloco diz de onde veio. O protótipo tinha numeros ilustrativos no T2 e
// "paradas estimadas" em Juntos; o dado real contraria as duas coisas, e a tela
// mostra o que foi medido.

import { estado } from "./estado.js";

const $ = (s) => document.querySelector(s);

const ALGS = [["dfs", "DFS", "#f07178"], ["bfs", "BFS", "#4fd1b0"], ["dijkstra", "Dijkstra", "#8fb0ff"]];
const ESTR = [
  ["todo_centro", "Todo centro", "#8a97a8"],
  ["limiar_50", "Limiar 50%", "#e7c66b"],
  ["limiar_25", "Limiar 25%", "#efb86a"],
  ["limiar_10", "Limiar 10%", "#ef9a6a"],
  ["guloso", "Guloso", "#12b7a3"],
  ["otimo", "Ótimo (ref.)", "#cfd8e3"],
];
const NOME_ALCANCE = { curto: "Curto (30% da rota)", medio: "Médio (50%)", longo: "Longo (75%)" };

const fmt = (v, d = 1) => Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v) => `${fmt(v * 100, 0)}%`;

export function criarTelaBenchmark() {
  const Q = { pagina: "t1", size: 15, alcance: "medio" };

  const procedencia = (b) => `medido em ${b.commit || "?"}, ${String(b.gerado_em || "").slice(0, 10)}`;

  // Cartao de metrica: barras horizontais; "melhor" so quando a metrica distingue.
  // `excluir`: estrategias que falham e nao entram no destaque de "melhor".
  function cartao(titulo, nota, linhas, melhor, casas = 1, excluir = []) {
    const max = Math.max(...linhas.map((l) => l.v), 1e-9);
    const candidatos = linhas.filter((l) => !excluir.includes(l.k)).map((l) => l.v);
    const alvo = !melhor || !candidatos.length ? null : melhor === "min" ? Math.min(...candidatos) : Math.max(...candidatos);
    const barras = linhas.map((l) => {
      const ganhou = alvo !== null && l.v === alvo && !excluir.includes(l.k);
      return `<div class="bar${ganhou ? " best" : ""}"><span class="nm" title="${l.nome}">${l.nome}</span><span class="track"><i class="fill" data-w="${(l.v / max * 100).toFixed(1)}" style="background:${l.cor}"></i></span><span class="val">${l.texto ?? fmt(l.v, casas)}${ganhou ? "<em>melhor</em>" : ""}</span></div>`;
    }).join("");
    return `<div class="metric"><div class="mt">${titulo}${nota ? `<small>${nota}</small>` : ""}</div>${barras}</div>`;
  }

  const t1 = (b) => Object.fromEntries(b.t1.rota.map((r) => [`${r.algoritmo}-${r.tamanho}`, r]));
  const t1p = (b) => Object.fromEntries(b.t1.partida.map((r) => [`${r.algoritmo}-${r.tamanho}`, r]));

  function paginaT1(b) {
    const rota = t1(b);
    const part = t1p(b);
    const linhas = (tab, campo) => ALGS.map(([k, nome, cor]) => ({ k, nome, cor, v: tab[`${k}-${Q.size}`][campo] }));
    const rotas = [
      ["Custo médio", "menor paga menos", "custo_medio", "min"],
      ["Passos médios", "", "passos_medio", "min"],
      ["Nós expandidos", "esforço, não tempo", "nos_expandidos_medio", "min"],
    ].map(([t, n, c, m]) => cartao(t, n, linhas(rota, c), m)).join("");
    const partidas = [
      ["Objetivos", "mais é melhor", "objetivos_medio", "max"],
      ["Passos", "ler junto com objetivos", "passos_medio", null],
      ["Batalhas", "não distingue", "batalhas_medio", null],
      ["HP perdido", "não distingue", "hp_perdido_medio", null],
    ].map(([t, n, c, m]) => cartao(t, n, linhas(part, c), m)).join("");
    const bfs = rota[`bfs-${Q.size}`];
    const dij = rota[`dijkstra-${Q.size}`];
    return `<div class="bn-group"><h3>Rota pura <span class="prov real">real · ${procedencia(b)} · ${b.t1.filtro_rota}</span></h3><div class="bn-row c3">${rotas}</div></div>
      <div class="bn-group"><h3>Partida completa <span class="prov real">real · ${procedencia(b)}</span></h3><div class="bn-row c4">${partidas}</div></div>
      <div class="tese-bn">Em ${Q.size}×${Q.size}: o BFS anda <b>${fmt(bfs.passos_medio)}</b> passos e paga <b>${fmt(bfs.custo_medio)}</b>; o Dijkstra anda <b>${fmt(dij.passos_medio)}</b> e paga <b>${fmt(dij.custo_medio)}</b>. <b>Menos passos não é menor custo.</b></div>`;
  }

  function linhasT2(b) {
    // o snapshot traz uma linha por (tamanho, alcance, algoritmo, estrategia); a
    // pagina mostra o Dijkstra, a rota do Trabalho 1 que o guloso recebe
    return b.t2.linhas.filter((l) => l.tamanho === Q.size && l.alcance === Q.alcance && l.algoritmo === "dijkstra");
  }

  function paginaT2(b) {
    const dados = Object.fromEntries(linhasT2(b).map((l) => [l.estrategia, l]));
    const lin = (campo, conv = (x) => x) => ESTR.filter(([k]) => dados[k]).map(([k, nome, cor]) => ({ k, nome, cor, v: conv(dados[k][campo]) }));
    const falham = ESTR.map(([k]) => k).filter((k) => dados[k] && dados[k].taxa_desmaio > 0.05);
    const alguma = dados.guloso;
    const inviaveis = alguma ? alguma.taxa_inviavel : 0;
    const execs = alguma ? alguma.execucoes : 0;
    const cards = [
      cartao("Paradas médias", "menos é melhor (quem desmaia não conta)", lin("paradas_medio"), "min", 2, falham),
      cartao("Desmaios", "% das rotas", lin("taxa_desmaio", (x) => x * 100).map((l) => ({ ...l, texto: pct(l.v / 100) })), "min", 0),
      cartao("Energia desperdiçada", "ao recarregar (quem desmaia não conta)", lin("energia_desperdicada_medio"), "min", 1, falham),
    ].join("");
    return `<div class="bn-group"><h3>Guloso e rivais <span class="prov real">real · ${procedencia(b)} · ${NOME_ALCANCE[Q.alcance]}</span></h3><div class="bn-row c3">${cards}</div></div>
      <div class="tese-bn">Grade herdada do T1: tamanhos 8, 15 e 30, 30 seeds, alcance em 3 níveis. A rota vem do Dijkstra do T1 e o <b>guloso só escolhe onde parar</b>. Em ${Q.size}×${Q.size} com alcance ${Q.alcance}, <b>${pct(inviaveis)}</b> das rotas sequer têm solução (foram descartadas; as médias contam as ${execs} que têm). Quem desmaia (${falham.map((k) => ESTR.find((e) => e[0] === k)[1]).join(", ") || "ninguém"}) não entra no "melhor". Guloso e ótimo têm as mesmas paradas em todos os pares medidos.</div>`;
  }

  function paginaJuntos(b) {
    const linhas = b.t2.cruzamento.filter((c) => c.tamanho === Q.size);
    const rota = t1(b);
    const custos = cartao("Custo médio da rota", "Trabalho 1 · real", ALGS.map(([k, nome, cor]) => ({ k, nome, cor, v: rota[`${k}-${Q.size}`].custo_medio })), "min", 1);
    const corpo = ["curto", "medio", "longo"].map((a) => {
      const c = linhas.find((x) => x.alcance === a);
      if (!c) return "";
      const destaque = a === Q.alcance ? ' style="background:rgba(18,183,163,.07)"' : "";
      return `<tr${destaque}><td>${NOME_ALCANCE[a]}</td><td>${c.destinos_comparados}</td><td class="g">${c.dijkstra_menos_paradas}</td><td>${c.empates}</td><td class="x">${c.dijkstra_mais_paradas}</td></tr>`;
    }).join("");
    const tabela = `<div class="metric"><div class="mt">Paradas do guloso: Dijkstra contra DFS e BFS<small>Trabalho 2 · real · mesmos destinos</small></div>
      <table class="mtx"><thead><tr><th>Alcance</th><th>Destinos</th><th>Dijkstra menos</th><th>Empate</th><th>Dijkstra mais</th></tr></thead><tbody>${corpo}</tbody></table></div>`;
    const total = linhas.reduce((s, c) => s + c.destinos_comparados, 0);
    const menos = linhas.reduce((s, c) => s + c.dijkstra_menos_paradas, 0);
    const mais = linhas.reduce((s, c) => s + c.dijkstra_mais_paradas, 0);
    const porTamanho = ["8", "15", "30"].map((t) => {
      const cs = b.t2.cruzamento.filter((c) => c.tamanho === Number(t));
      return `${t}×${t}: ${cs.reduce((s, c) => s + c.dijkstra_menos_paradas, 0)} de ${cs.reduce((s, c) => s + c.destinos_comparados, 0)}`;
    }).join("; ");
    return `<div class="bn-group"><h3>Do T1 ao T2 <span class="prov real">custos reais</span> <span class="prov real">paradas medidas · ${procedencia(b)}</span></h3><div class="bn-row c2">${custos}${tabela}</div></div>
      <div class="tese-bn">A rota mais barata do T1 <b>pode</b> precisar de menos paradas no T2, mas o medido é modesto: em ${Q.size}×${Q.size}, o Dijkstra precisou de menos paradas em <b>${menos}</b> de ${total} destinos, empatou no resto e <b>${mais === 0 ? "nunca precisou de mais" : `precisou de mais em ${mais}`}</b>. Destinos em que o Dijkstra precisou de menos paradas, por mapa: ${porTamanho}. Três tamanhos não provam uma tendência; é o que a grade mediu.</div>`;
  }

  const SUB = {
    t1: "<b>Trabalho 1 · Grafos.</b> DFS, BFS e Dijkstra. Médias de 30 seeds por tamanho, HP cheio e sem Surf.",
    t2: "<b>Trabalho 2 · Guloso.</b> Seis regras de parada sobre a rota do Dijkstra, medidas em 7.109 simulações.",
    ac: "<b>Juntos.</b> A rota do primeiro trabalho vira entrada do segundo: o que muda quando o caminho é mais barato?",
  };

  function desenhar() {
    const b = estado.benchmark;
    const corpo = $("#bn-body");
    if (!b || b.erro) {
      corpo.innerHTML = `<div class="erro-tela"><b>Sem dados do benchmark.</b><br>${b ? b.erro : "snapshot não carregado"}<br><small>Rode <code>python -m webdemo.snapshot</code> e recarregue.</small></div>`;
      return;
    }
    document.querySelectorAll("#bn-page button").forEach((x) => x.classList.toggle("on", x.dataset.p === Q.pagina));
    document.querySelectorAll("#bn-size button").forEach((x) => x.classList.toggle("on", Number(x.dataset.s) === Q.size));
    document.querySelectorAll("#bn-alc button").forEach((x) => x.classList.toggle("on", x.dataset.a === Q.alcance));
    $("#bn-alc-wrap").style.display = Q.pagina === "t2" ? "" : "none";
    $("#bn-sub").innerHTML = SUB[Q.pagina];
    corpo.innerHTML = { t1: paginaT1, t2: paginaT2, ac: paginaJuntos }[Q.pagina](b);
    requestAnimationFrame(() => requestAnimationFrame(() => corpo.querySelectorAll(".fill").forEach((f) => { f.style.width = f.dataset.w + "%"; })));
  }

  let ligada = false;
  return {
    abrir() {
      if (!ligada) {
        ligada = true;
        $("#bn-page").onclick = (e) => { const x = e.target.closest("button"); if (x) { Q.pagina = x.dataset.p; desenhar(); } };
        $("#bn-size").onclick = (e) => { const x = e.target.closest("button"); if (x) { Q.size = Number(x.dataset.s); desenhar(); } };
        $("#bn-alc").onclick = (e) => { const x = e.target.closest("button"); if (x) { Q.alcance = x.dataset.a; desenhar(); } };
      }
      desenhar();
    },
  };
}
