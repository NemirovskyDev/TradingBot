import type { PortfolioData, Run, RunIndex } from "./types";
import { DataError, parseIndex, parsePortfolios, parseRun, SAFE_ID } from "./validate";

type FetchFn = typeof fetch;

async function getJson(path: string, fetchFn: FetchFn): Promise<unknown> {
  let res: Response;
  try {
    res = await fetchFn(`${import.meta.env.BASE_URL}${path}`);
  } catch {
    throw new DataError("Não foi possível carregar os dados. Verifique a conexão e tente de novo.");
  }
  if (!res.ok) throw new DataError(`Não foi possível carregar os dados (erro ${res.status}).`);
  try {
    return await res.json();
  } catch {
    throw new DataError("O arquivo de dados não é um JSON válido.");
  }
}

export async function loadIndex(fetchFn: FetchFn = fetch): Promise<RunIndex> {
  return parseIndex(await getJson("data/index.json", fetchFn));
}

export async function loadRun(id: string, fetchFn: FetchFn = fetch): Promise<Run> {
  // o id vira parte do caminho do arquivo: só aceita o formato que o backend gera
  if (!SAFE_ID.test(id)) throw new DataError("Identificador de execução inválido.");
  return parseRun(await getJson(`data/runs/${id}.json`, fetchFn));
}

export async function loadPortfolios(fetchFn: FetchFn = fetch): Promise<PortfolioData> {
  return parsePortfolios(await getJson("data/portfolios.json", fetchFn));
}
