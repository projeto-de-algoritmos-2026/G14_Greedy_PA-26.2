// HUD: o medidor de energia e os cartoes de numeros. Portado do prototipo.
//
// O medidor deixa uma faixa vermelha do que foi perdido no ultimo passo e
// encolhe, pra o jogador VER o custo e nao so ler o numero.

const $ = (seletor, raiz) => raiz.querySelector(seletor);

// cartoes: "energia" (medidor), "energia+recarga" (medidor com o botao R) ou
// [rotulo, chave] para um numero simples
export function criarHud(raiz, cartoes) {
  raiz.innerHTML = cartoes
    .map((c) => {
      if (c === "energia" || c === "energia+recarga") {
        const botao = c === "energia+recarga"
          ? `<button class="recarga" data-k="rb" disabled title="Só funciona em cima de um Centro Pokémon"><kbd>R</kbd> Recarregar</button>`
          : "";
        return `<div class="card"><div class="lbl lbl-row"><span>Energia</span>${botao}</div><div class="gauge" data-k="g"><i class="loss"></i><i class="fill"></i><span class="val"></span></div><div class="sub" data-k="gsub"></div></div>`;
      }
      return `<div class="card"><div class="lbl">${c[0]}</div><div class="num" data-k="${c[1]}"></div></div>`;
    })
    .join("");
  const botaoRecarga = $("[data-k=rb]", raiz);

  return {
    // `antes`: a energia anterior. Se perdeu energia, uma faixa vermelha fica onde estava e encolhe.
    medidor(energia, maximo, sub, antes) {
      const g = $("[data-k=g]", raiz);
      const fracao = maximo > 0 ? energia / maximo : 0;
      const perda = $(".loss", g);
      g.className = "gauge" + (fracao <= 0.25 ? " low" : fracao <= 0.5 ? " mid" : "");
      g.style.setProperty("--seg", 100 / maximo + "%");
      perda.style.transition = "none";
      perda.style.width = ((antes !== undefined && antes > energia ? antes : energia) / maximo) * 100 + "%";
      perda.getBoundingClientRect(); // forca o layout antes de religar a transicao
      perda.style.transition = "";
      perda.style.width = fracao * 100 + "%";
      $(".fill", g).style.width = fracao * 100 + "%";
      $(".val", g).textContent = `${energia} / ${maximo}`;
      $("[data-k=gsub]", raiz).innerHTML = sub || "";
    },
    numero(chave, html) {
      $(`[data-k=${chave}]`, raiz).innerHTML = html;
    },
    recarga(ligada) {
      if (!botaoRecarga) return;
      botaoRecarga.disabled = !ligada;
      botaoRecarga.classList.toggle("pronto", ligada);
    },
    aoRecarregar(fn) {
      if (botaoRecarga) botaoRecarga.onclick = fn;
    },
  };
}
