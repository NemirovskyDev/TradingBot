export type TermKey = "candle" | "drawdown" | "sharpe" | "stop" | "buy_hold" | "backtest" | "fora_amostra";

export interface Term {
  name: string;
  short: string;
}

/** Fonte única dos termos: alimenta as dicas ao lado dos números e a tela de glossário. */
export const TERMS: Record<TermKey, Term> = {
  candle: {
    name: "Candle (vela)",
    short: "Uma barra que resume um dia: onde o preço abriu e fechou e os extremos que tocou.",
  },
  drawdown: {
    name: "Maior queda (drawdown)",
    short: "A maior queda do capital entre um pico e o ponto mais baixo seguinte. Mostra quanto doeu no pior momento.",
  },
  sharpe: {
    name: "Índice de Sharpe",
    short: "Retorno ajustado ao risco: quanto se ganhou para cada unidade de oscilação. Acima de 1 costuma ser considerado bom.",
  },
  stop: {
    name: "Stop de proteção",
    short: "Preço definido de antemão em que o bot sai da operação para limitar a perda.",
  },
  buy_hold: {
    name: "Comprar e segurar (buy and hold)",
    short: "Comprar no começo e não mexer até o fim. É a régua: o bot só vale a pena se bater isso com menos risco.",
  },
  backtest: {
    name: "Backtest",
    short: "Um ensaio com dados do passado. Mostra como a estratégia teria se comportado, mas não garante nada sobre o futuro.",
  },
  fora_amostra: {
    name: "Trecho de teste (fora da amostra)",
    short: "Parte do histórico separada para julgar a estratégia, sem ter sido usada para escolhê-la. É o que conta para o veredito.",
  },
};
