// Tela Bot: o bot joga a missao de verdade e a tela reproduz o que ele fez.
//
// O servidor roda o bot inteiro em milissegundos e empurra os eventos por SSE.
// Esta tela os guarda num buffer e os reproduz no ritmo escolhido (0,5x a 4x), o
// que da play, pausa, "um passo" e reiniciar sem rodar nada de novo. Nenhuma
// regra mora aqui: custo, desmaio, recarga e o que a estrategia decidiu chegam
// prontos. A regua cresce a cada plano (o bot so escolhe o proximo objetivo
// depois de chegar no anterior), entao nao ha total conhecido de antemao.

import { api, partidaAoVivo } from "./api.js";
import { estado } from "./estado.js";
import { criarMapa, NOME_TERRENO } from "./mapa.js";
import { criarHud } from "./hud.js";
import { diario, conta, nomeTerreno } from "./diario.js";
import { montarPresets, avisoDeViabilidade } from "./alcance.js";
import { desenharRegua, descreverRegua } from "./regua.js";

const $ = (s) => document.querySelector(s);
const PASSO_MS = 520; // um passo a 1x

export function criarTelaBot() {
  const hud = criarHud($("#b-hud"), ["energia", ["Custo", "cu"], ["Paradas", "pa"], ["Pokémon", "pk"], ["Estratégia", "es"]]);
  const lista = diario($("#b-feed"));
  const B = {
    algoritmo: "dijkstra", estrategia: "guloso", alcance: null, velocidade: 1,
    eventos: [], i: 0, timer: null, rodando: false, carregando: false, fonte: null,
    grid: null, mapa: null, alcanceDados: null,
    // estado da reproducao (reconstruido a cada evento, nunca calculado)
    energia: 0, max: 0, custo: 0, paradas: 0, pokemon: 1, marcos: [], ultimoPlano: [],
    rotaAte: 0, fim: null, erro: null,
  };

  const terreno = (r, c) => nomeTerreno[B.grid.celulas[r][c].terreno] || "terreno";

  // ---------- desenho ----------
  function painel(antes) {
    const sub = B.fim
      ? (B.fim.pokemon >= B.fim.meta ? "Missão cumprida" : `Parou: ${B.fim.motivo_parada}`)
      : `Alcance: <b>${B.max}</b> de energia por tanque`;
    hud.medidor(B.energia, B.max, sub, antes);
    hud.numero("cu", `${B.custo}`);
    hud.numero("pa", `${B.paradas}`);
    hud.numero("pk", `${B.pokemon}<small>/${estado.config.meta}</small>`);
    const e = estado.config.estrategias.find((x) => x.id === B.estrategia);
    hud.numero("es", `<span style="font-size:.7em">${B.estrategia === "nenhuma" ? "Sem parada (T1)" : (e ? e.nome : B.estrategia)}</span>`);
    B.mapa.energia(B.max ? B.energia / B.max : 0);
  }

  function regua() {
    B.reguaObj = desenharRegua($("#b-ruler"), {
      marcos: B.marcos, alcance: B.max, total: Math.max(B.custo, 1), alto: true,
    });
    B.reguaObj.mover(B.custo);
    $("#b-ruler").setAttribute("aria-label", descreverRegua(B.marcos, B.custo));
  }

  // ---------- reproducao de um evento ----------
  function aplicar(nome, d) {
    switch (nome) {
      case "inicio": {
        B.max = d.jogador.energia_max;
        B.energia = d.jogador.energia;
        B.alcanceDados = d.alcance;
        B.mapa.posicionar(d.posicao[0], d.posicao[1], { instante: true });
        const e = estado.config.estrategias.find((x) => x.id === d.estrategia);
        lista.escrever("plan", "Missão do Trabalho 1",
          `Capturar ${d.jogador.meta} Pokémon pela rota mais barata, com tanque de ${B.max}.`);
        lista.escrever("plan", "Trabalho 2: a energia tem que durar",
          d.estrategia ? `Estratégia: <b>${e ? e.nome : d.estrategia}</b>. ${e ? e.descricao : ""}` : "Sem estratégia de parada: o bot anda a rota inteira, como no Trabalho 1.");
        painel();
        break;
      }
      case "plano":
        B.ultimoPlano = d.caminho;
        B.mapa.rota(d.caminho, { somar: true });
        lista.escrever("plan", "Novo plano", `Até (${d.destino[0]}, ${d.destino[1]}): custo planejado <b>${d.custo}</b>, ${d.nos_expandidos} nós expandidos.`);
        break;
      case "paradas": {
        if (d.sem_solucao) {
          lista.escrever("faint", "Sem solução", "Nem parando em todo Centro este trecho cabe no tanque: o bot desiste da rota antes de andar.");
          break;
        }
        if (d.posicoes.length) {
          B.mapa.paradas(d.posicoes);
          lista.escrever("plan", "Paradas escolhidas",
            d.posicoes.map((p, n) => `${n + 1}. (${p[0]}, ${p[1]})`).join(" · "));
        }
        break;
      }
      case "passo": {
        const antes = B.energia;
        const [r, c] = d.posicao;
        if (d.desmaiou) {
          B.caiu = true;
          B.energia = 0;
          B.mapa.desmaiar(true);
          B.mapa.pulso(r, c, "#ef6a6a");
          const alvo = d.custo ? d.custo.total : "?";
          B.marcos.push({ c: B.custo, tipo: "desmaio" });
          B.mapa.numero(r, c, "-" + alvo, "#ef6a6a", { grande: true, lento: true, sub: `tinha ${antes}` });
          lista.escrever("faint", "Desmaiou",
            `O próximo trecho cobrava <b>${alvo}</b> e restavam <b>${antes}</b>: faltaram <b>${d.faltaram}</b>. Faltou um Centro antes.`);
          regua();
          painel(antes);
          pausar();
          break;
        }
        if (!d.valido) break;
        B.energia = d.energia_depois;
        B.custo += d.energia_gasta;
        B.mapa.posicionar(r, c, { ms: Math.min(260, 420 / B.velocidade) });
        B.mapa.trilhaAdd(r, c);
        const batalha = d.custo && d.custo.conteudo > 0;
        B.mapa.numero(r, c, "-" + d.energia_gasta, batalha ? "#f2b84b" : "#dbe3ee",
          batalha ? { grande: true, sub: conta(d.custo, terreno(r, c)) } : {});
        if (d.batalhou || d.pegou_pokebola || d.pegou_surf) B.mapa.consumir(r, c);
        if (d.jogador.pokemon > B.pokemon) {
          B.pokemon = d.jogador.pokemon;
          B.marcos.push({ c: B.custo, tipo: "captura" });
          lista.escrever("battle", `Captura ${B.pokemon - 1} de ${d.jogador.meta - 1}`,
            `Batalha com ${d.conteudo === "cpu" ? "treinador" : "Pokémon selvagem"}: <b>-${d.energia_gasta}</b> (${conta(d.custo, terreno(r, c))}). Sobram ${d.energia_depois}.`);
        } else if (d.em_centro) {
          B.marcos.push({ c: B.custo, tipo: "centro" });
        }
        regua();
        painel(antes);
        break;
      }
      case "recarga": {
        const [r, c] = d.posicao;
        const antes = B.energia;
        B.energia = d.jogador.energia;
        B.paradas += 1;
        // o passo que chegou neste Centro o tinha marcado como "passou direto"
        for (let k = B.marcos.length - 1; k >= 0; k--) {
          if (B.marcos[k].tipo === "centro") { B.marcos[k] = { ...B.marcos[k], tipo: "parada", sobrava: d.sobrava }; break; }
        }
        B.mapa.pulso(r, c, "#12b7a3");
        B.mapa.numero(r, c, "+" + d.entrou, "#12b7a3", { grande: true, sub: "recarregou" });
        lista.escrever("recharge", `Parada ${B.paradas}: recarrega`,
          `Chegou ao Centro com <b>${d.sobrava}</b> de ${d.energia_max}. Jogou fora ${d.sobrava}.`);
        regua();
        painel(antes);
        break;
      }
      case "fim": {
        B.fim = d;
        if (d.erro) { lista.escrever("faint", "Erro no bot", d.erro); break; }
        const venceu = d.pokemon >= d.meta;
        lista.escrever(venceu ? "ok" : "faint", venceu ? "Missão cumprida" : "Missão não cumprida",
          venceu
            ? `${d.pokemon} Pokémon, ${d.paradas} parada(s), ${d.energia_desperdicada} de energia desperdiçada, ${d.replanejamentos} replanejamento(s).`
            : `Capturou ${d.pokemon} de ${d.meta} (${d.motivo_parada}).`);
        if (!B.mapa) break;
        setTimeout(() => {
          if (B.fim !== d) return;
          B.mapa.faixa(venceu ? "win" : "lose", venceu ? "Missão cumprida" : "Missão não cumprida",
            venceu ? `${d.pokemon} Pokémon capturados com ${d.paradas} parada(s).` : `Capturou ${d.pokemon} de ${d.meta}: ${d.motivo_parada}.`, "Reiniciar").onclick = montar;
        }, 500);
        pausar();
        painel();
        break;
      }
    }
  }

  // ---------- controle ----------
  function atraso() { return PASSO_MS / B.velocidade; }
  function tocar() {
    if (B.rodando || B.carregando) return;
    B.rodando = true;
    $("#b-play").textContent = "⏸ Pausar";
    B.timer = setInterval(avancar, atraso());
  }
  function pausar() {
    B.rodando = false;
    clearInterval(B.timer);
    $("#b-play").textContent = B.fim ? "↻ Jogar de novo" : "▶ Jogar";
  }
  function avancar() {
    if (B.i >= B.eventos.length) {
      if (!B.fonte) pausar(); // buffer esgotado e o stream ja fechou
      return;
    }
    // eventos sem passo (plano, paradas, inicio) nao gastam tempo de tela
    let nome, dados;
    do { [nome, dados] = B.eventos[B.i++]; aplicar(nome, dados); }
    while (nome !== "passo" && nome !== "recarga" && nome !== "fim" && B.i < B.eventos.length);
    // Depois de um desmaio o bot nao anda mais: so falta o `fim`, que carrega o
    // resumo e a faixa. Consome-o agora em vez de deixa-lo preso no buffer.
    if (B.caiu && B.i < B.eventos.length && B.eventos[B.i][0] === "fim") {
      aplicar(...B.eventos[B.i++]);
    }
  }

  function montar() {
    pausar();
    if (B.fonte) B.fonte.fechar();
    B.fonte = null;
    Object.assign(B, { eventos: [], i: 0, custo: 0, paradas: 0, pokemon: 1, marcos: [], fim: null, erro: null, caiu: false, carregando: true });
    lista.limpar();
    $("#b-play").textContent = "⏳ Carregando…";
    const size = Number($("#b-size").value) || 8;
    const seed = Number($("#b-seed").value) || 0;

    api.alcance(size, seed, B.alcance ?? undefined).then((dados) => {
      B.alcanceDados = dados;
      if (B.alcance === null) B.alcance = dados.recomendado;
      $("#b-alc").max = estado.config.energia_max;
      $("#b-alc").value = B.alcance;
      $("#b-alc-v").textContent = B.alcance;
      atualizarAlcance(dados);
    }).catch(() => {});

    B.fonte = partidaAoVivo(
      { size, seed, algoritmo: B.algoritmo, estrategia: B.estrategia, energia: B.alcance ?? undefined },
      (nome, dados) => {
        if (nome === "inicio") {
          // O mapa precisa existir antes de qualquer reproducao. `inicio` e sempre o
          // primeiro evento, entao o buffer e o indice continuam sendo a unica
          // fonte da ordem: ele entra como os demais e e reproduzido ja.
          B.grid = dados;
          B.mapa = criarMapa($("#b-map"), dados, { aoDica: dicaMapa });
          B.mapa.reiniciar();
          B.custo = 0; B.paradas = 0; B.pokemon = dados.jogador.pokemon; B.marcos = [];
          B.carregando = false;
          $("#b-play").textContent = "▶ Jogar";
        }
        B.eventos.push([nome, dados]);
        if (nome === "inicio") { aplicar(...B.eventos[B.i++]); regua(); }
        if (nome === "fim") { B.fonte = null; }
      },
      (mensagem) => {
        B.carregando = false; B.fonte = null;
        lista.escrever("faint", "Conexão", mensagem);
        $("#b-play").textContent = "▶ Jogar";
      },
    );
  }

  function dicaMapa(r, c) {
    if (!B.grid) return "";
    const cel = B.grid.celulas[r][c];
    const centro = B.grid.centros.some(([cr, cc]) => cr === r && cc === c);
    return `<b>${NOME_TERRENO[cel.terreno]}</b>${centro ? "<br>Centro Pokémon" : ""}<br><small>linha ${r}, coluna ${c}</small>`;
  }

  function atualizarAlcance(dados) {
    const aviso = avisoDeViabilidade({ ...dados, escolhido: dados.escolhido || dados.niveis?.minimo });
    const el = $("#b-alc-aviso");
    el.className = "aviso-alcance " + aviso.tipo;
    el.innerHTML = aviso.html;
    montarPresets($("#b-presets"), dados, B.alcance, (valor) => { B.alcance = valor; montar(); });
  }

  // ---------- ligacao dos controles ----------
  function ligar() {
    $("#b-play").onclick = () => {
      if (B.carregando) return;
      if (B.rodando) return pausar();
      if (B.fim) return montar();
      tocar();
    };
    $("#b-reset").onclick = montar;
    $("#b-size").onchange = $("#b-seed").onchange = () => { B.alcance = null; montar(); };
    $("#b-algo").onclick = (e) => {
      const b = e.target.closest("button"); if (!b) return;
      document.querySelectorAll("#b-algo button").forEach((x) => x.classList.toggle("on", x === b));
      B.algoritmo = b.dataset.a; montar();
    };
    $("#b-speed").onclick = (e) => {
      const b = e.target.closest("button"); if (!b) return;
      document.querySelectorAll("#b-speed button").forEach((x) => x.classList.toggle("on", x === b));
      B.velocidade = Number(b.dataset.s);
      if (B.rodando) { clearInterval(B.timer); B.timer = setInterval(avancar, atraso()); }
    };
    $("#b-alc").oninput = (e) => { $("#b-alc-v").textContent = e.target.value; };
    $("#b-alc").onchange = (e) => { B.alcance = Number(e.target.value); montar(); };
  }

  function montarEstrategias() {
    const raiz = $("#b-estr");
    const todas = [...estado.config.estrategias, { id: "nenhuma", nome: "Sem parada (T1)", descricao: "" }];
    raiz.innerHTML = todas.map((e) => `<button data-e="${e.id}" class="${e.id === B.estrategia ? "on" : ""}" title="${e.descricao}">${e.nome}</button>`).join("");
    raiz.onclick = (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      raiz.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
      B.estrategia = b.dataset.e; montar();
    };
  }

  let iniciada = false;
  return {
    abrir() {
      if (!iniciada) { iniciada = true; montarEstrategias(); ligar(); }
      if (!B.grid) montar();
    },
    fechar() { pausar(); },
  };
}
