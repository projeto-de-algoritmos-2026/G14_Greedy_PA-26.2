// Tela Jogo: o humano anda pelo mapa gastando energia.
//
// Nenhuma conta mora aqui. O servidor devolve, para cada passo, quanto custou
// (terreno + conteudo), se o treinador desmaiou e quanto faltou; para cada
// vizinha, quanto custaria entrar SEM dar o passo. A tela escolhe o texto e a
// animacao.

import { api } from "./api.js";
import { estado } from "./estado.js";
import { criarMapa, NOME_TERRENO, NOME_CONTEUDO } from "./mapa.js";
import { criarHud } from "./hud.js";
import { diario, conta, nomeTerreno } from "./diario.js";
import { montarPresets, avisoDeViabilidade } from "./alcance.js";

const $ = (s) => document.querySelector(s);

const TECLAS = {
  w: "W", arrowup: "W", s: "S", arrowdown: "S", a: "A", arrowleft: "A", d: "D", arrowright: "D",
};
const DELTA = { W: [-1, 0], S: [1, 0], A: [0, -1], D: [0, 1] };

export function criarTelaJogo() {
  const hud = criarHud($("#j-hud"), ["energia+recarga", ["HP do líder", "hp"], ["Pokémon", "pk"], ["Pokébolas", "pb"], ["Surf", "sf"]]);
  const lista = diario($("#j-feed"));
  let mapa = null;
  let partida = null; // { sessao, grid, pos, jogador, vizinhas, encerrada }

  const terrenoDe = (r, c) => nomeTerreno[partida.grid.celulas[r][c].terreno] || "terreno";
  const noCentro = () => partida.grid.centros.some(([r, c]) => r === partida.pos[0] && c === partida.pos[1]);
  const distanciaAoCentro = () =>
    Math.min(...partida.grid.centros.map(([r, c]) => Math.abs(r - partida.pos[0]) + Math.abs(c - partida.pos[1])));

  function desenhar(antes) {
    const j = partida.jogador;
    const sub = partida.encerrada
      ? j.motivo || j.situacao
      : `Centro mais perto: <b>${distanciaAoCentro()} passo(s)</b> em linha reta`;
    hud.medidor(j.energia, j.energia_max, sub, antes);
    hud.numero("hp", `${j.hp_lider}`);
    hud.numero("pk", `${j.pokemon}<small>/${j.meta}</small>`);
    hud.numero("pb", `${j.pokebolas}`);
    hud.numero("sf", `<small>${j.surf ? "sim" : "não"}</small>`);
    mapa.energia(j.energia / j.energia_max);
    const podeRecarregar = !partida.encerrada && noCentro() && j.energia < j.energia_max;
    hud.recarga(podeRecarregar);

    if (partida.encerrada) mapa.aviso(null);
    else if (noCentro()) {
      mapa.aviso(j.energia < j.energia_max
        ? `<kbd>R</kbd> Recarregar aqui <span>+${j.energia_max - j.energia} de energia</span>`
        : `Tanque cheio <span>siga em frente</span>`, j.energia < j.energia_max ? "" : "neutro");
    } else if (j.energia / j.energia_max <= 0.5) {
      mapa.aviso(`Energia baixa <span>Centro a ${distanciaAoCentro()} passo(s): chegue nele e aperte <kbd>R</kbd></span>`, "aviso");
    } else mapa.aviso(null);
  }

  // A dica so vale para as 4 vizinhas: e o que o servidor sabe responder sem o passo.
  function dica(r, c) {
    if (!partida) return "";
    const cel = partida.grid.celulas[r][c];
    const centro = partida.grid.centros.some(([cr, cc]) => cr === r && cc === c);
    const conteudo = centro ? "centro" : cel.conteudo;
    let html = `<b>${NOME_TERRENO[cel.terreno]}</b>`;
    if (NOME_CONTEUDO[conteudo] && conteudo !== "livre" && conteudo !== "visitado") html += `<br>${NOME_CONTEUDO[conteudo]}`;
    html += `<br><small>linha ${r}, coluna ${c}</small>`;
    if (partida.encerrada) return html;
    const direcao = Object.entries(partida.vizinhas).find(([, v]) => v.posicao[0] === r && v.posicao[1] === c);
    if (!direcao) return html;
    const v = direcao[1];
    if (!v.valido) return html + `<br><small>${v.motivo}</small>`;
    const detalhe = v.custo.conteudo > 0 ? ` (${v.custo.terreno} + ${v.custo.conteudo} de batalha)` : "";
    return v.desmaia
      ? html + `<br><b style="color:#ef6a6a">Entrar agora: desmaia.</b> Custa ${v.custo.total}${detalhe} e você tem ${partida.jogador.energia}.`
      : html + `<br>Entrar agora: <b style="color:#f2b84b">-${v.custo.total}</b>${detalhe}, sobram ${v.sobram}.`;
  }

  async function novo() {
    const size = Number($("#j-size").value) || 8;
    const seed = Number($("#j-seed").value) || 0;
    const energia = $("#j-energia").value ? Number($("#j-energia").value) : undefined;
    let dados;
    try {
      dados = await api.jogoNovo(size, seed, energia);
    } catch (erro) {
      lista.limpar();
      lista.escrever("faint", "Não consegui começar", erro.message);
      return;
    }
    partida = {
      sessao: dados.sessao, grid: dados, pos: dados.posicao, jogador: dados.jogador,
      vizinhas: dados.vizinhas, encerrada: false, alcance: dados.alcance,
    };
    mapa = criarMapa($("#j-map"), dados, { selo: true, aoDica: dica });
    mapa.posicionar(dados.posicao[0], dados.posicao[1], { instante: true });
    $("#j-energia").value = dados.jogador.energia_max;
    lista.limpar();
    desenhar();

    const alc = dados.alcance;
    const aviso = avisoDeViabilidade(alc);
    lista.escrever("plan", "Partida nova",
      `Capture ${dados.jogador.meta} Pokémon. Energia máxima ${dados.jogador.energia_max}. Há ${dados.centros.length} Centros (selo <b>R</b>): entrar neles <b>não recarrega sozinho</b>, aperte <kbd>R</kbd> em cima.`);
    if (aviso.html) lista.escrever(aviso.tipo === "ok" ? "ok" : "plan", "Alcance", aviso.html);
    montarPresets($("#j-presets"), alc, dados.jogador.energia_max, (valor) => {
      $("#j-energia").value = valor;
      novo();
    });
    $("#j-energia-dica").textContent = alc.menor_tanque != null ? `(mínimo verificado: ${alc.menor_tanque})` : "";
  }

  async function mover(direcao) {
    if (!partida || partida.encerrada || partida.ocupada) return;
    partida.ocupada = true;
    try {
      const antes = partida.jogador.energia;
      const r = await api.jogoMover(partida.sessao, direcao);
      if (r.erro) return lista.escrever("faint", "Partida", r.erro);
      // O desmaio chega com `valido: false` (o passo nao aconteceu), entao ele TEM
      // que ser tratado antes do "movimento invalido", senao vira "bloqueio".
      if (!r.valido && !r.desmaiou) {
        const texto = { "agua sem surf": "Sem Surf a aresta não existe.", "celula inacessivel": "Não dá para passar por aqui.", "fora do mapa": "Fim do mapa." }[r.motivo] || r.motivo;
        if (r.motivo !== "fora do mapa") lista.escrever("", r.motivo === "agua sem surf" ? "Água" : "Bloqueio", texto);
        return;
      }
      const [linha, coluna] = r.posicao;
      const terreno = r.celula ? nomeTerreno[r.celula.terreno] : terrenoDe(linha, coluna);
      partida.vizinhas = r.vizinhas;
      partida.jogador = r.jogador;

      if (r.desmaiou) {
        // o passo nao aconteceu: a posicao do jogador continua a mesma
        const [dl, dc] = DELTA[direcao];
        const alvo = [partida.pos[0] + dl, partida.pos[1] + dc];
        partida.encerrada = true;
        mapa.desmaiar(true);
        mapa.pulso(alvo[0], alvo[1], "#ef6a6a");
        const custo = r.custo ? r.custo.total : "?";
        mapa.numero(alvo[0], alvo[1], "-" + custo, "#ef6a6a", { grande: true, lento: true, sub: `você tinha ${antes}` });
        desenhar(antes);
        const porque = r.custo && r.custo.conteudo > 0
          ? `A batalha cobrou <b>${custo}</b> de energia (${conta(r.custo, nomeTerreno[partida.grid.celulas[alvo[0]][alvo[1]].terreno])}).`
          : `O terreno cobra <b>${custo}</b>.`;
        lista.escrever("faint", "Desmaiou", `${porque} Você entrou com <b>${antes}</b>: faltaram <b>${r.faltaram}</b>.`);
        setTimeout(() => {
          const b = mapa.faixa("lose", "Desmaiou",
            `${porque.replace(/<\/?b>/g, "")} Você entrou com ${antes}: faltaram ${r.faltaram}.<br><br>Dica: recarregue num Centro (<kbd>R</kbd>) antes de entrar em batalha.`, "Nova partida");
          b.onclick = novo;
        }, 700);
        return;
      }

      partida.pos = [linha, coluna];
      mapa.posicionar(linha, coluna);
      mapa.trilhaAdd(linha, coluna);
      const batalha = r.custo && r.custo.conteudo > 0;
      mapa.numero(linha, coluna, "-" + r.energia_gasta, batalha ? "#f2b84b" : "#dbe3ee",
        batalha ? { grande: true, sub: conta(r.custo, terreno) } : {});
      if (r.batalhou || r.pegou_pokebola || r.pegou_surf) mapa.consumir(linha, coluna);

      const sobram = r.energia_depois;
      if (r.batalhou) {
        const tipo = r.conteudo === "cpu" ? "Venceu um treinador" : "Capturou um Pokémon";
        lista.escrever("battle", tipo, `Batalha forçada: <b>-${r.energia_gasta}</b> de energia (${conta(r.custo, terreno)}) e -${r.hp_perdido} de HP. Sobram ${sobram}.`);
      } else if (r.pegou_pokebola) lista.escrever("ok", "Pokébola", `Mais uma no bolso. -${r.energia_gasta} de energia (só o terreno).`);
      else if (r.pegou_surf) lista.escrever("ok", "Surf", `Agora dá para atravessar água. -${r.energia_gasta} de energia.`);
      else if (r.em_centro) lista.escrever("recharge", "Centro Pokémon", `Entrar não recarrega. Aperte <kbd>R</kbd> para encher o tanque (restam ${sobram}).`);
      else lista.escrever("", terreno[0].toUpperCase() + terreno.slice(1), `-${r.energia_gasta} de energia.`);

      const fim = partida.jogador;
      if (fim.situacao === "vitoria") {
        partida.encerrada = true;
        lista.escrever("ok", "Vitória", `${fim.meta} Pokémon capturados.`);
        desenhar(antes);
        setTimeout(() => { mapa.faixa("win", "Vitória", `${fim.meta} Pokémon capturados.`, "Jogar de novo").onclick = novo; }, 500);
        return;
      }
      if (fim.situacao === "derrota") {
        partida.encerrada = true;
        desenhar(antes);
        lista.escrever("faint", "Derrota", fim.motivo || "O time caiu.");
        setTimeout(() => { mapa.faixa("lose", "Derrota", fim.motivo || "O time caiu em batalha.", "Nova partida").onclick = novo; }, 500);
        return;
      }
      desenhar(antes);
    } finally {
      if (partida) partida.ocupada = false;
    }
  }

  async function recarregar() {
    if (!partida || partida.encerrada) return;
    const r = await api.jogoRecarregar(partida.sessao);
    if (r.erro) return lista.escrever("faint", "Partida", r.erro);
    partida.vizinhas = r.vizinhas;
    partida.jogador = r.jogador;
    if (!r.recarregou) {
      const texto = r.motivo === "sem centro aqui"
        ? ["Sem Centro aqui", "Recarregar só funciona em cima de um Centro Pokémon (ícone verde com o selo R)."]
        : ["Tanque cheio", "Nada a recarregar."];
      return lista.escrever("", texto[0], texto[1]);
    }
    const [linha, coluna] = partida.pos;
    mapa.pulso(linha, coluna, "#12b7a3");
    mapa.numero(linha, coluna, "+" + r.entrou, "#12b7a3", { grande: true, sub: "recarregou" });
    desenhar(r.sobrava);
    lista.escrever("recharge", "Recarregou", `+${r.entrou} de energia. Sobravam ${r.sobrava} de ${partida.jogador.energia_max}: jogou fora ${r.sobrava}.`);
  }

  hud.aoRecarregar(recarregar);
  $("#j-novo").onclick = novo;
  $("#j-energia").addEventListener("change", novo);

  function teclado(e) {
    if (estado.aba !== "jogo" || /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    const k = e.key.toLowerCase();
    if (TECLAS[k]) { e.preventDefault(); mover(TECLAS[k]); }
    else if (k === "r") recarregar();
  }
  document.addEventListener("keydown", teclado);

  return {
    abrir() { if (!partida) return novo(); },
    novo,
  };
}
