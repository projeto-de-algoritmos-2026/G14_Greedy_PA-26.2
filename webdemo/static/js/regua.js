// Regua da missao (custo acumulado). Portada do prototipo (buildRuler), mas o que
// ela desenha e a LINHA DO TEMPO REAL do bot, nao marcos estimados.
//
// Entrada: `marcos` = [{c, tipo}], tipo em `centro` (passou direto), `parada`
// (recarregou, com `sobrava`), `captura` e `desmaio`. `c` e o custo acumulado.
// A regua e a mesma no Bot (cresce ao vivo) e nas raias do Comparar (pronta).

const W = 1000;
const MARGEM = 24;
const UTIL = 952;

const esc = (texto) => String(texto).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function desenharRegua(svg, { marcos, alcance, total, alto = false, chegou = null }) {
  const H = alto ? 118 : 84;
  const ay = alto ? 48 : 34;
  const fim = Math.max(total, ...marcos.map((m) => m.c), 1);
  const X = (c) => MARGEM + (c / fim) * UTIL;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);

  let s = `<line x1="${X(0)}" x2="${X(fim)}" y1="${ay}" y2="${ay}" stroke="#2a3645" stroke-width="6" stroke-linecap="round"/>`;

  // trechos entre recargas: verde = energia usada no tanque; a faixa ambar embaixo
  // e o que ainda havia no tanque quando o bot parou (jogado fora)
  const paradas = marcos.filter((m) => m.tipo === "parada");
  const desmaio = marcos.find((m) => m.tipo === "desmaio");
  const pontos = [0, ...paradas.map((p) => p.c)];
  const ultimoFim = desmaio ? desmaio.c : fim;
  pontos.forEach((inicio, k) => {
    const ultimo = k === pontos.length - 1;
    const termino = ultimo ? ultimoFim : pontos[k + 1];
    const cor = ultimo && desmaio ? "#ef6a6a" : "#12b7a3";
    s += `<rect x="${X(inicio)}" y="${ay - 3}" width="${Math.max(0, X(termino) - X(inicio))}" height="6" rx="3" fill="${cor}"/>`;
    if (!ultimo) {
      const sobra = paradas[k].sobrava || 0;
      if (sobra > 0) {
        s += `<rect x="${X(termino)}" y="${ay + 12 + (k % 2) * 8}" width="${Math.max(2, X(termino + sobra) - X(termino))}" height="5" rx="2.5" fill="#f2b84b" opacity=".6"><title>Parou com ${sobra} de ${alcance} no tanque</title></rect>`;
      }
    }
  });

  // marcos: Centro ignorado (cinza), parada numerada (verde), captura (losango ambar)
  let nParada = 0;
  let nCaptura = 0;
  marcos.forEach((m) => {
    const x = X(m.c);
    if (m.tipo === "centro") {
      s += `<rect x="${x - 2}" y="${ay - 8}" width="4" height="16" rx="1" fill="#3a4658"><title>Passou direto por um Centro (custo ${m.c})</title></rect>`;
    } else if (m.tipo === "parada") {
      nParada += 1;
      s += `<rect x="${x - 4}" y="${ay - 15}" width="8" height="30" rx="2" fill="#12b7a3"><title>Parada ${nParada}: custo ${m.c}</title></rect><text x="${x}" y="${ay - 21}" text-anchor="middle" font-size="16" font-weight="800" fill="#12b7a3" font-family="monospace">${nParada}</text>`;
    } else if (m.tipo === "captura") {
      nCaptura += 1;
      s += `<path d="M${x} ${ay - 11} L${x + 8} ${ay} L${x} ${ay + 11} L${x - 8} ${ay} Z" fill="#f2b84b" stroke="#2b1d00" stroke-width="2"><title>Captura ${nCaptura}: custo ${m.c}</title></path><text x="${x}" y="${ay + 4.5}" text-anchor="middle" font-size="12" font-weight="800" fill="#2b1d00" font-family="monospace">${nCaptura}</text>`;
    }
    if (alto && (m.tipo === "parada" || m.tipo === "captura")) {
      s += `<text x="${x}" y="${ay + 44}" text-anchor="middle" font-size="15" fill="#8a97a8" font-family="monospace">${m.c}</text>`;
    }
  });

  s += `<circle cx="${X(0)}" cy="${ay}" r="5" fill="#fff"/>`;
  if (alto) {
    s += `<text x="${X(0)}" y="${ay + 44}" text-anchor="middle" font-size="15" fill="#8a97a8" font-family="monospace">0</text>`;
    if (!desmaio) s += `<text x="${X(fim)}" y="${ay + 44}" text-anchor="middle" font-size="15" fill="#8a97a8" font-family="monospace">${fim}</text>`;
  }
  if (desmaio) {
    s += `<g transform="translate(${X(desmaio.c)},${ay})"><circle r="12" fill="#1a0f12" stroke="#ef6a6a" stroke-width="2.4"/><path d="M-5 -5L5 5M5 -5L-5 5" stroke="#ef6a6a" stroke-width="2.8" stroke-linecap="round"/><title>Desmaiou no custo ${desmaio.c}</title></g>`;
  } else if (chegou) {
    s += `<text x="${X(fim) + 2}" y="${ay + 5}" font-size="16" fill="#12b7a3">⚑</text>`;
  }
  s += `<circle class="runner" cx="${X(0)}" cy="${ay}" r="8" fill="#fff" stroke="#12b7a3" stroke-width="3"/>`;
  svg.innerHTML = s;

  const corredor = svg.querySelector(".runner");
  return {
    X,
    // o corredor nunca passa de onde o bot realmente chegou
    mover(custo) {
      corredor.setAttribute("cx", X(Math.min(custo, ultimoFim)));
    },
  };
}

// Descricao textual (acessibilidade): a regua e um desenho, isto e o que ela diz.
export function descreverRegua(marcos, total) {
  const paradas = marcos.filter((m) => m.tipo === "parada").length;
  const capturas = marcos.filter((m) => m.tipo === "captura").length;
  const desmaio = marcos.find((m) => m.tipo === "desmaio");
  return `Custo até ${total}. ${capturas} captura(s), ${paradas} parada(s)${desmaio ? `, desmaiou no custo ${desmaio.c}` : ""}.`;
}

export { esc };
