import type { ReactNode } from "react";
import { NavIcon } from "./icons";
import { hrefTo, ROUTES, type RouteId } from "./routes";
import "./ui.css";

interface ShellProps {
  route: RouteId;
  children: ReactNode;
}

/** Navegação lateral no desktop e barra inferior no celular (um só <nav>, reposicionado por CSS). */
export function Shell({ route, children }: ShellProps) {
  return (
    <div className="shell">
      {/* sem mexer no hash: ele é a rota (#/grafico?trade=t2), e "#conteudo" derrubaria a tela atual */}
      <a
        className="skip-link"
        href="#conteudo"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("conteudo")?.focus();
        }}
      >
        Ir para o conteúdo
      </a>
      <nav className="nav" aria-label="Seções do painel">
        <p className="brand">TradingBot</p>
        <ul>
          {ROUTES.map((r) => (
            <li key={r.id}>
              <a href={hrefTo(r.id)} aria-current={r.id === route ? "page" : undefined}>
                <NavIcon route={r.id} />
                <span>{r.label}</span>
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <div className="content">
        <main id="conteudo" tabIndex={-1}>
          {children}
        </main>
        <footer className="credits">
          <p>
            Os preços históricos vêm do Yahoo Finance (via yfinance), só para fins educacionais: não são em tempo real e podem ter atrasos e erros.
            Execuções marcadas como "Exemplo" usam dados sintéticos. Listas de ativos: Wikipedia e brapi.
          </p>
          <p>
            Gráficos com Lightweight Charts™ da{" "}
            <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">
              TradingView
            </a>
            .
          </p>
        </footer>
      </div>
    </div>
  );
}
