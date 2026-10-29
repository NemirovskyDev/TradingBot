import { useEffect, useState } from "react";

export const ROUTES = [
  { id: "carteiras", label: "Carteiras" },
  { id: "visao-geral", label: "Visão geral" },
  { id: "grafico", label: "Gráfico" },
  { id: "operacoes", label: "Operações" },
  { id: "risco", label: "Risco" },
  { id: "glossario", label: "Glossário" },
] as const;

export type RouteId = (typeof ROUTES)[number]["id"];

export interface HashRoute {
  route: RouteId;
  params: URLSearchParams;
}

function read(): HashRoute {
  const [path = "", query = ""] = window.location.hash.replace(/^#\/?/, "").split("?");
  const route = ROUTES.find((r) => r.id === path)?.id ?? "carteiras";
  return { route, params: new URLSearchParams(query) };
}

/** Rota por hash (#/grafico?trade=t2): funciona no GitHub Pages sem configuração de servidor. */
export function useHashRoute(): HashRoute {
  const [state, setState] = useState<HashRoute>(read);
  useEffect(() => {
    const onChange = () => setState(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return state;
}

export function hrefTo(route: RouteId, params?: Record<string, string>): string {
  const query = params ? `?${new URLSearchParams(params).toString()}` : "";
  return `#/${route}${query}`;
}
