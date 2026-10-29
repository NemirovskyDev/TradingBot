import type { DataError } from "../data/validate";
import "./ui.css";

export function Loading() {
  return (
    <div role="status" className="state state-loading">
      <span className="spinner" aria-hidden="true" />
      Carregando dados…
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: DataError; onRetry: () => void }) {
  return (
    <div role="alert" className="state state-error">
      <p className="state-title">Não foi possível mostrar os dados</p>
      <p>Os arquivos de dados não puderam ser lidos. Tente de novo ou escolha outra execução.</p>
      <p className="state-detail">Detalhe técnico: {error.message}</p>
      <p className="state-detail">
        Se o problema continuar, gere os dados de novo com <code>python -m tradingbot export --real</code>.
      </p>
      <button type="button" className="button" onClick={onRetry}>
        Tentar de novo
      </button>
    </div>
  );
}

/** `flat` tira a borda e o fundo quando o estado vive dentro de um painel (cartão dentro de cartão é erro). */
export function EmptyState({ title, hint, flat = false }: { title: string; hint: string; flat?: boolean }) {
  return (
    <div className={flat ? "state state-empty state-flat" : "state state-empty"}>
      <p className="state-title">{title}</p>
      <p>{hint}</p>
    </div>
  );
}
