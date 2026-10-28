import { formatDate, formatPercent, formatPrice, formatQty } from "../../data/format";
import { outcome, resultClass } from "../../data/outcome";
import type { Trade } from "../../data/types";
import { Hint } from "../../ui/Hint";

/** Explica uma operação em frases simples e mostra os números dela. */
export function TradeDetail({ trade }: { trade: Trade }) {
  const o = outcome(trade.pnl_pct);
  return (
    <section className="panel trade-detail" aria-labelledby="trade-detail-title">
      <h3 id="trade-detail-title">Compra em {formatDate(trade.entry_date)}</h3>
      <dl className="why-list">
        <div>
          <dt>Por que comprou</dt>
          <dd>{trade.reason_entry}</dd>
        </div>
        <div>
          <dt>Por que saiu, em {formatDate(trade.exit_date)}</dt>
          <dd>{trade.reason_exit}</dd>
        </div>
      </dl>
      <dl className="facts">
        <div>
          <dt>Preço de entrada</dt>
          <dd>{formatPrice(trade.entry_price)}</dd>
        </div>
        <div>
          <dt>Preço de saída</dt>
          <dd>{formatPrice(trade.exit_price)}</dd>
        </div>
        <div>
          <dt>Quantidade</dt>
          <dd>{formatQty(trade.qty)}</dd>
        </div>
        <div>
          <dt>
            <Hint term="stop">Stop de proteção</Hint>
          </dt>
          <dd>{formatPrice(trade.stop)}</dd>
        </div>
        <div>
          <dt>Resultado</dt>
          <dd>
            <span className={resultClass[o.kind]}>{formatPercent(trade.pnl_pct)}</span> <span className="result-word">({o.word})</span>
          </dd>
        </div>
      </dl>
    </section>
  );
}
