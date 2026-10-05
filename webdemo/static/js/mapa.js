// Mapa em SVG. Portado do prototipo aprovado (buildMap), com duas diferencas de
// fundo: o grid vem da API (tamanho e conteudo variaveis, nao um 10x10 fixo) e
// nenhuma regra mora aqui. O mapa so DESENHA o que o servidor mandou e ANIMA
// os efeitos (numero que pula da celula, pulso, trilha, desmaio).

import { ICON } from "./icones.js";

const NS = "http://www.w3.org/2000/svg";
const S = 48; // lado da celula no sistema de coordenadas do SVG

export const NOME_TERRENO = { concrete: "Concreto", grass: "Grama", water: "Água" };
export const NOME_CONTEUDO = {
  pokemon: "Pokémon selvagem", cpu: "Treinador", pokebola: "Pokébola",
  bloqueio: "Bloqueio", centro: "Centro Pokémon", surf: "Item Surf",
};

const PADRAO = { concrete: "pc", grass: "pg", water: "pw" };
let serie = 0; // ids de pattern unicos quando ha mais de um mapa na pagina

const $ = (seletor, raiz) => raiz.querySelector(seletor);

// A dica que o mapa mostra ao passar o mouse e montada por quem usa o mapa
// (`aoDica`): so a tela sabe o que o servidor diz sobre o custo da celula.
export function criarMapa(hospedeiro, grid, { selo = false, aoDica = null } = {}) {
  const id = ++serie;
  const n = grid.size;
  const cx = (c) => c * S + S / 2;
  const cy = (r) => r * S + S / 2;
  const centros = new Set((grid.centros || []).map(([r, c]) => `${r},${c}`));

  let celulas = "";
  let conteudos = "";
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      const cel = grid.celulas[r][c];
      const terreno = PADRAO[cel.terreno] || "pc";
      celulas += `<rect x="${c * S}" y="${r * S}" width="${S}" height="${S}" fill="url(#${terreno}${id})" stroke="#0b0f14" stroke-opacity=".35"/>`;
      const chave = `${r},${c}`;
      const conteudo = centros.has(chave) ? "centro" : cel.conteudo;
      if (conteudo === "centro") {
        const seloR = selo
          ? `<g transform="translate(15,15)"><circle r="8.5" fill="#12b7a3" stroke="#04231f" stroke-width="2"/><text y="3.8" text-anchor="middle" font-size="11" font-weight="800" fill="#04231f" font-family="monospace">R</text></g>`
          : "";
        conteudos += `<g class="content" data-k="${chave}" transform="translate(${cx(c)},${cy(r)})"><circle class="centro-pulso" r="21" fill="none" stroke="#12b7a3" stroke-width="2"/>${ICON.centro()}${seloR}</g>`;
      } else if (ICON[conteudo]) {
        conteudos += `<g class="content" data-k="${chave}" transform="translate(${cx(c)},${cy(r)})">${ICON[conteudo]()}</g>`;
      }
    }
  }

  hospedeiro.innerHTML = `<svg viewBox="0 0 ${n * S} ${n * S}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Mapa ${n} por ${n}">
    <defs>
      <pattern id="pc${id}" width="16" height="16" patternUnits="userSpaceOnUse"><rect width="16" height="16" fill="#5b6470"/><circle cx="3" cy="4" r=".9" fill="#6d7784"/><circle cx="11" cy="10" r=".9" fill="#4d5560"/><circle cx="7" cy="14" r=".8" fill="#6d7784"/></pattern>
      <pattern id="pg${id}" width="12" height="12" patternUnits="userSpaceOnUse"><rect width="12" height="12" fill="#2d7643"/><path d="M2 10l1-4M6 11l0-5M10 10l-1-4" stroke="#3f9a5a" stroke-width="1.3" stroke-linecap="round" fill="none"/></pattern>
      <pattern id="pw${id}" width="24" height="12" patternUnits="userSpaceOnUse"><rect width="24" height="12" fill="#1e4e86"/><path d="M0 6q3-3 6 0t6 0 6 0 6 0" fill="none" stroke="#3f7bbf" stroke-width="1.2" opacity=".75"/><animateTransform attributeName="patternTransform" type="translate" from="0 0" to="24 0" dur="3.5s" repeatCount="indefinite"/></pattern>
    </defs>
    <g>${celulas}</g>
    <g data-l="conts">${conteudos}</g>
    <polyline data-l="route" fill="none" stroke="#8fb0ff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>
    <polyline data-l="trail" fill="none" stroke="#12b7a3" stroke-width="3" stroke-linecap="round" stroke-dasharray="1 7" opacity=".9"/>
    <g data-l="objs"></g>
    <g data-l="stops"></g>
    <g data-l="pulses"></g>
    <rect class="hoverbox" width="${S}" height="${S}" x="-99" y="-99" rx="3"/>
    <g class="player" data-l="player"><g class="body">
      <circle r="23" fill="#12b7a3" opacity=".16"/>
      <circle class="ring" r="19" fill="none" stroke="#12b7a3" stroke-width="4" stroke-linecap="round" transform="rotate(-90)" stroke-dasharray="119.4 119.4"/>
      <circle r="13" fill="#12b7a3" stroke="#fff" stroke-width="2"/>
      <circle cx="-4" cy="-2" r="1.7" fill="#04231f"/><circle cx="4" cy="-2" r="1.7" fill="#04231f"/><path d="M-4 3 q4 3 8 0" stroke="#04231f" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    </g></g>
    <g data-l="floats"></g>
  </svg><div class="banner" data-l="banner"></div><div class="prompt" data-l="prompt"></div>`;

  const svg = $("svg", hospedeiro);
  const camada = (nome) => $(`[data-l=${nome}]`, hospedeiro);
  const jogador = camada("player");
  const anel = $(".ring", hospedeiro);
  const destaque = $(".hoverbox", hospedeiro);
  const dica = document.getElementById("tip");
  const trilha = [];

  const mostrarDica = (evento, html) => {
    if (!dica) return;
    dica.innerHTML = html;
    dica.style.left = Math.min(evento.clientX + 14, innerWidth - 250) + "px";
    dica.style.top = evento.clientY + 14 + "px";
    dica.classList.add("on");
  };
  const esconderDica = () => dica && dica.classList.remove("on");

  svg.addEventListener("mousemove", (evento) => {
    const ponto = svg.createSVGPoint();
    ponto.x = evento.clientX;
    ponto.y = evento.clientY;
    const p = ponto.matrixTransform(svg.getScreenCTM().inverse());
    const c = Math.floor(p.x / S);
    const r = Math.floor(p.y / S);
    if (r < 0 || c < 0 || r >= n || c >= n) return esconderDica();
    destaque.setAttribute("x", c * S);
    destaque.setAttribute("y", r * S);
    const html = aoDica ? aoDica(r, c) : "";
    if (html) mostrarDica(evento, html);
    else esconderDica();
  });
  svg.addEventListener("mouseleave", () => {
    esconderDica();
    destaque.setAttribute("x", -99);
  });

  const marcar = (camadaNome, lista, lado, cor, texto) => {
    camada(camadaNome).innerHTML = lista
      .map(([r, c], i) => `<g transform="translate(${cx(c) + lado},${cy(r) - 15})"><circle r="9" fill="${cor}" stroke="${texto === "amber" ? "#2b1d00" : "#04231f"}" stroke-width="2"/><text y="4" text-anchor="middle" font-size="11" font-weight="800" fill="${texto === "amber" ? "#2b1d00" : "#04231f"}" font-family="monospace">${i + 1}</text></g>`)
      .join("");
  };

  const acoes = {
    size: n,

    // numero que pula da celula: o custo da entrada. opcoes: {grande, lento, sub}
    numero(r, c, texto, cor, o = {}) {
      const g = camada("floats");
      const t = document.createElementNS(NS, "text");
      const desce = r < 2; // perto do topo o numero desce, senao sairia do mapa
      t.setAttribute("x", cx(c));
      t.setAttribute("y", cy(r) + (desce ? 8 : -4));
      t.setAttribute("fill", cor);
      t.setAttribute("font-size", o.grande ? 30 : 20);
      t.setAttribute("class", "float" + (o.lento ? " lento" : ""));
      t.style.setProperty("--s", desce ? 1 : -1);
      t.style.setProperty("--dy", (desce ? "" : "-") + (o.grande ? "58px" : "40px"));
      t.textContent = texto;
      g.appendChild(t);
      setTimeout(() => t.remove(), o.lento ? 2400 : 1300);
      if (o.sub) {
        const s = document.createElementNS(NS, "text");
        s.setAttribute("x", cx(c));
        s.setAttribute("y", cy(r) + (desce ? 30 : 14));
        s.setAttribute("fill", "#fff");
        s.setAttribute("font-size", 11);
        s.setAttribute("class", "float lento");
        s.style.setProperty("--s", desce ? 1 : -1);
        s.style.setProperty("--dy", desce ? "30px" : "-30px");
        s.textContent = o.sub;
        g.appendChild(s);
        setTimeout(() => s.remove(), 2400);
      }
    },

    aviso(html, tipo) {
      const p = camada("prompt");
      if (!html) {
        p.className = "prompt";
        return;
      }
      p.innerHTML = html;
      p.className = "prompt on" + (tipo ? " " + tipo : "");
    },

    posicionar(r, c, { instante = false, ms = 0 } = {}) {
      if (ms) jogador.style.transitionDuration = ms + "ms";
      if (instante) jogador.style.transition = "none";
      jogador.style.transform = `translate(${cx(c)}px,${cy(r)}px)`;
      if (instante) {
        jogador.getBoundingClientRect(); // forca o layout antes de religar a transicao
        jogador.style.transition = "";
      }
    },

    energia(fracao) {
      anel.style.strokeDasharray = `${Math.max(0, fracao) * 119.4} 119.4`;
      anel.style.stroke = fracao <= 0.25 ? "#ef6a6a" : fracao <= 0.5 ? "#f2b84b" : "#12b7a3";
    },

    pulso(r, c, cor) {
      const el = document.createElementNS(NS, "circle");
      el.setAttribute("cx", cx(c));
      el.setAttribute("cy", cy(r));
      el.setAttribute("r", 16);
      el.setAttribute("fill", "none");
      el.setAttribute("stroke", cor);
      el.setAttribute("stroke-width", 3);
      el.setAttribute("class", "burst");
      camada("pulses").appendChild(el);
      setTimeout(() => el.remove(), 1000);
    },

    desmaiar(ligado) {
      jogador.classList.toggle("faint", ligado);
      if (ligado) anel.style.stroke = "#ef6a6a";
    },

    // o conteudo some depois de vencido/pego; o Centro nunca some
    consumir(r, c) {
      const g = $(`[data-k="${r},${c}"]`, hospedeiro);
      if (g && !g.querySelector(".centro-pulso")) g.style.opacity = 0;
    },

    trilhaAdd(r, c) {
      trilha.push(`${cx(c)},${cy(r)}`);
      camada("trail").setAttribute("points", trilha.join(" "));
    },
    trilhaLimpar() {
      trilha.length = 0;
      camada("trail").setAttribute("points", "");
    },

    // desenha a rota sem apagar o que ja foi desenhado: o bot planeja de novo a
    // cada objetivo, e a rota de cada trecho se soma a dos anteriores
    rota(caminho, { somar = false } = {}) {
      const el = camada("route");
      const pontos = caminho.map(([r, c]) => [cx(c), cy(r)]);
      const atuais = somar && el.getAttribute("points") ? el.getAttribute("points") + " " : "";
      el.setAttribute("points", atuais + pontos.map((p) => p.join(",")).join(" "));
      el.style.strokeDasharray = "";
      el.style.strokeDashoffset = "";
    },
    rotaLimpar() {
      camada("route").setAttribute("points", "");
      camada("stops").innerHTML = "";
      camada("objs").innerHTML = "";
    },

    objetivos: (lista) => marcar("objs", lista, -15, "#f2b84b", "amber"),
    paradas: (lista) => marcar("stops", lista, 15, "#12b7a3", "jade"),

    faixa(tipo, titulo, texto, botao) {
      const b = camada("banner");
      b.className = "banner on " + tipo;
      b.innerHTML = `<h2>${titulo}</h2><p>${texto}</p>${botao ? `<button class="btn primary">${botao}</button>` : ""}`;
      return $("button", b);
    },
    faixaEsconder() {
      camada("banner").className = "banner";
    },

    reiniciar() {
      acoes.trilhaLimpar();
      acoes.desmaiar(false);
      acoes.faixaEsconder();
      acoes.aviso(null);
      acoes.rotaLimpar();
      camada("floats").innerHTML = "";
      camada("pulses").innerHTML = "";
      hospedeiro.querySelectorAll(".content").forEach((g) => (g.style.opacity = 1));
    },
  };

  acoes.posicionar(grid.posicao ? grid.posicao[0] : 0, grid.posicao ? grid.posicao[1] : 0, { instante: true });
  acoes.energia(1);
  return acoes;
}
