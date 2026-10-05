// Presets de alcance e o aviso de viabilidade. Usado pelo Jogo e pelo Bot.
//
// O servidor responde, por simulacao da missao inteira, se um tanque cumpre a
// missao (`viavel`). A tela so mostra essa resposta, com honestidade sobre o que
// ela garante: `viavel` e sempre verdade (vem de uma simulacao), mas "menor
// tanque" e o menor que a BUSCA achou. A vitoria nao e monotona no tanque
// (medido: 8x8 seed 3 vence com 46, a busca acha 122), por isso o rotulo e
// "minimo verificado" e nao "minimo".

export const ROTULO = {
  abaixo: "Abaixo do mínimo",
  minimo: "Mínimo verificado",
  folgado: "Folgado",
};

const DICA = {
  abaixo: "Um tanque menor que o mínimo verificado: costuma não cumprir a missão.",
  minimo: "O menor tanque que a simulação verificou que cumpre a missão. Pode existir um menor, por sorte de batalha.",
  folgado: "Mais tanque que o mínimo verificado: sobra energia para o bot parar menos.",
};

// Monta os botoes dos presets. `aoEscolher(alcance)` recebe o tanque.
export function montarPresets(raiz, dados, atual, aoEscolher) {
  const niveis = dados.niveis || {};
  const nomes = Object.keys(niveis);
  if (!nomes.length) {
    raiz.innerHTML = "";
    return;
  }
  raiz.innerHTML = nomes
    .map((nome) => {
      const n = niveis[nome];
      const classe = (n.alcance === atual ? " on" : "") + (n.viavel ? " ok" : " nao");
      return `<button class="preset${classe}" data-n="${nome}" title="${DICA[nome] || ""}"><span>${ROTULO[nome] || nome}</span><b>${n.alcance}</b></button>`;
    })
    .join("");
  raiz.querySelectorAll("button").forEach((b) => {
    b.onclick = () => aoEscolher(niveis[b.dataset.n].alcance);
  });
}

// O texto que diz se o tanque escolhido cumpre a missao, e o que faltou se nao.
export function avisoDeViabilidade(dados) {
  if (dados.menor_tanque === null || dados.menor_tanque === undefined) {
    return {
      tipo: "sem",
      html: `<b>Este mapa não tem solução.</b> Nem com o tanque cheio a missão termina (${dados.motivo_sem_solucao || "o Trabalho 1 também não vence"}): a energia não é o que impede.`,
    };
  }
  const e = dados.escolhido;
  if (!e) return { tipo: "neutro", html: "" };
  if (e.viavel) {
    const folga = e.folga > 0 ? `, sobram ${e.folga} sobre o mínimo verificado (${dados.menor_tanque})` : " (é o mínimo verificado)";
    return { tipo: "ok", html: `<b>Com ${e.alcance} a missão é possível</b>${folga}.` };
  }
  const falta = e.folga < 0 ? ` Faltam ${-e.folga} para o mínimo verificado (${dados.menor_tanque}).` : "";
  return {
    tipo: "nao",
    html: `<b>Com ${e.alcance} o bot não cumpre a missão</b> (${e.motivo || "sem energia"}; capturou ${e.pokemon} de ${e.meta}).${falta}`,
  };
}
