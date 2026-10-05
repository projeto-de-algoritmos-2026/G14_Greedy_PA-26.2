// Icones do mapa. Os desenhos vem do prototipo aprovado (prototipo-interface-fase-6.html);
// a chave e a que a API devolve em `conteudo` (api.CONTEUDO), nao a letra do prototipo.
// `surf` nao existia no prototipo: e um item de mapa (ganha-se o Surf pegando-o).
const DESENHOS = {
  P: () => `<ellipse rx="12" ry="10" fill="#f6d365"/><polygon points="-9,-6 -6,-17 -2,-8" fill="#f6d365"/><polygon points="9,-6 6,-17 2,-8" fill="#f6d365"/><circle cx="-4" cy="-1" r="1.9" fill="#222"/><circle cx="4" cy="-1" r="1.9" fill="#222"/><circle cx="-7.5" cy="4" r="2.2" fill="#f28b82"/><circle cx="7.5" cy="4" r="2.2" fill="#f28b82"/>`,
  T: () => `<rect x="-7" y="-2" width="14" height="15" rx="4" fill="#e0524d"/><circle cy="-8" r="5.5" fill="#f0b89a"/><path d="M-6 -9 a6 6 0 0 1 12 0 z" fill="#2b3a55"/>`,
  B: () => `<circle r="9" fill="#fff"/><path d="M-9 0 a9 9 0 0 1 18 0 z" fill="#e5484d"/><line x1="-9" x2="9" stroke="#222" stroke-width="1.6"/><circle r="3.2" fill="#fff" stroke="#222" stroke-width="1.6"/>`,
  "#": () => `<polygon points="-14,10 -11,-7 -1,-14 11,-9 14,10" fill="#262c35" stroke="#3b4656" stroke-width="1.5"/><polygon points="-1,-14 11,-9 4,-3" fill="#3a4454"/>`,
  C: () => `<rect x="-13" y="-11" width="26" height="23" rx="4" fill="#e8f6f3"/><rect x="-13" y="-11" width="26" height="7" rx="3" fill="#12b7a3"/><rect x="-2" y="-1" width="4" height="12" fill="#12b7a3"/><rect x="-6" y="3" width="12" height="4" fill="#12b7a3"/>`,
  flag: () => `<line x1="-6" y1="12" x2="-6" y2="-13" stroke="#fff" stroke-width="2"/><path d="M-6 -13 L11 -6 L-6 1 Z" fill="#12b7a3"/>`,
};

// chave da API -> desenho
const DA_API = {
  pokemon: "P", cpu: "T", pokebola: "B", bloqueio: "#", centro: "C", surf: "S", flag: "flag",
};

DESENHOS.S = () => `<path d="M-13 6 q6-12 13-2 q7-10 13 2 z" fill="#3f7bbf"/><path d="M-11 9 h22" stroke="#9cc3ee" stroke-width="2" stroke-linecap="round"/>`;

export const ICON = Object.fromEntries(
  Object.entries(DA_API).map(([chave, letra]) => [chave, DESENHOS[letra]]),
);

export const icone = (chave, tamanho = 28) =>
  `<svg viewBox="-16 -16 32 32" width="${tamanho}" height="${tamanho}">${ICON[chave]()}</svg>`;
