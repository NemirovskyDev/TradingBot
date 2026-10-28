const MINUS = "−"; // sinal de menos tipográfico, não o hífen

function decimal(digits: number): Intl.NumberFormat {
  return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** 0,124 vira "12,4%"; negativos usam o sinal de menos e nunca aparece "−0,0%". */
export function formatPercent(fraction: number, digits = 1): string {
  const pct = fraction * 100;
  const shown = Number(Math.abs(pct).toFixed(digits));
  const sign = pct < 0 && shown !== 0 ? MINUS : "";
  return `${sign}${decimal(digits).format(shown)}%`;
}

/** Número simples em pt-BR com o mesmo sinal de menos tipográfico (e sem "−0,00"). */
export function formatNumber(n: number, digits = 2): string {
  const shown = Number(Math.abs(n).toFixed(digits));
  return `${n < 0 && shown !== 0 ? MINUS : ""}${decimal(digits).format(shown)}`;
}

export function formatPrice(n: number): string {
  return formatNumber(n, 2);
}

/** Quantidade: inteiro sem casas, fracionado com duas. */
export function formatQty(n: number): string {
  return formatNumber(n, Number.isInteger(n) ? 0 : 2);
}

/** "2025-09-12" vira "12/09/2025" sem passar por Date, para não sofrer deslocamento de fuso. */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
