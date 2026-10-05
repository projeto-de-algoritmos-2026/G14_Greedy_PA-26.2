// Estado compartilhado entre as telas e a navegacao por abas.
//
// O estado guarda so o que vem do servidor (a config e o snapshot) e a aba
// aberta. Nada de regra do jogo: quem sabe o que custa um passo e o servidor.

export const estado = {
  config: null,     // /api/t2/config
  benchmark: null,  // /api/t2/benchmark (snapshot)
  aba: null,
};

const ABAS = ["jogo", "bot", "comparar", "bench"];
const telas = {}; // nome -> { abrir(), fechar?() }

export function registrar(nome, tela) {
  telas[nome] = tela;
}

export function abaDaUrl() {
  const dica = location.hash.slice(1);
  return ABAS.includes(dica) ? dica : "jogo";
}

export function abrir(nome) {
  if (!ABAS.includes(nome)) nome = "jogo";
  const anterior = estado.aba;
  if (anterior && anterior !== nome && telas[anterior] && telas[anterior].fechar) {
    telas[anterior].fechar();
  }
  estado.aba = nome;
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("on", s.id === "tab-" + nome));
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("on", b.dataset.tab === nome));
  history.replaceState(null, "", "#" + nome);
  if (telas[nome] && telas[nome].abrir) telas[nome].abrir();
}

export function iniciarAbas() {
  document.getElementById("tabs").addEventListener("click", (e) => {
    const botao = e.target.closest(".tab-btn");
    if (botao) abrir(botao.dataset.tab);
  });
  addEventListener("hashchange", () => {
    if (abaDaUrl() !== estado.aba) abrir(abaDaUrl());
  });
}
