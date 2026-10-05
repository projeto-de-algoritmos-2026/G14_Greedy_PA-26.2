// Gaveta de legenda. Os custos vem da config do servidor (graph/cost.py), nunca
// de uma tabela copiada aqui: se a regra mudar, a legenda muda junto.

import { icone } from "./icones.js";

export function montarLegenda(gaveta, botao, config) {
  const c = config.custos;
  const grama = c.grama.cheio === c.grama.ferido ? `${c.grama.cheio}` : `${c.grama.cheio} a ${c.grama.ferido}`;
  const linha = (desenho, nome, detalhe, custo) =>
    `<div class="lg">${desenho}<div class="t">${nome}<span class="d">${detalhe}</span></div><div class="c">${custo}</div></div>`;
  const amostra = (cor) => `<div class="sw" style="background:${cor}"></div>`;

  gaveta.innerHTML = `
    <h2>Legenda</h2><p style="color:var(--muted);margin:0">Também aparece ao passar o mouse em cada célula.</p>
    <h4>Terreno · custo de entrar</h4>
    ${linha(amostra("#5b6470"), "Concreto", "referência", c.terreno.concrete)}
    ${linha(amostra("#2d7643"), "Grama", "sobe conforme o HP do líder cai", grama)}
    ${linha(amostra("#1e4e86"), "Água", "a aresta só existe com Surf", c.terreno.water)}
    <h4>Conteúdo da célula</h4>
    ${linha(icone("pokemon"), "Pokémon selvagem", "batalha forçada", "+" + c.conteudo.pokemon)}
    ${linha(icone("cpu"), "Treinador", "batalha, prêmio maior", "+" + c.conteudo.cpu)}
    ${linha(icone("pokebola"), "Pokébola", "item, sem penalidade", "+0")}
    ${linha(icone("surf"), "Item Surf", "permite atravessar água", "+0")}
    ${linha(icone("bloqueio"), "Bloqueio", "a aresta não existe", "n/a")}
    ${linha(icone("centro"), "Centro Pokémon", "entrar não recarrega; recarregar é decisão da estratégia", "+0")}
    <h4>Marcações</h4>
    <div class="lg"><div class="sw" style="background:transparent;border:2px solid #12b7a3;border-radius:50%"></div><div class="t">Anel de energia<span class="d">em volta do treinador: verde, âmbar, vermelho</span></div><div></div></div>
    <div class="lg"><div class="sw" style="background:#8fb0ff;height:5px;margin:10px 0"></div><div class="t">Rota do bot<span class="d">o trecho até o próximo objetivo</span></div><div></div></div>
    <div class="lg"><div class="sw" style="background:#12b7a3;border-radius:50%;width:18px;height:18px;margin:4px"></div><div class="t">Número de parada<span class="d">ordem das recargas que a estratégia escolheu</span></div><div></div></div>`;

  const alternar = () => {
    const aberta = !gaveta.classList.contains("open");
    gaveta.classList.toggle("open", aberta);
    botao.classList.toggle("on", aberta);
  };
  botao.addEventListener("click", alternar);
}
