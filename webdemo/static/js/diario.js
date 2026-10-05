// Diario da partida: o que aconteceu, em ordem, com a conta. Portado do prototipo.
//
// Todo texto que descreve custo vem do servidor (terreno + conteudo). O diario
// so o escreve bem: nenhuma conta e refeita aqui.

const LIMITE = 40;

export function diario(lista) {
  return {
    escrever(tipo, titulo, texto) {
      const li = document.createElement("li");
      li.className = "ev " + tipo;
      li.innerHTML = `<b>${titulo}</b><span>${texto}</span>`;
      lista.prepend(li);
      while (lista.children.length > LIMITE) lista.lastChild.remove();
    },
    limpar() {
      lista.innerHTML = "";
    },
  };
}

// "3 de grama + 8 de batalha" a partir do custo que o servidor mandou. O NOME do
// terreno vem de quem chama: o servidor manda o custo, e o terreno se descobre
// pela posicao na grade que a tela ja tem.
export function conta(custo, nomeDoTerreno) {
  if (!custo) return "";
  return custo.conteudo > 0
    ? `${custo.terreno} de ${nomeDoTerreno} + ${custo.conteudo} de batalha`
    : `${custo.terreno} de ${nomeDoTerreno}`;
}

export const nomeTerreno = { concrete: "concreto", grass: "grama", water: "água" };
