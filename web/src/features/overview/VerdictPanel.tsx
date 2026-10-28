import type { Verdict } from "../../data/types";

/** Veredito do critério de promoção em linguagem simples, com ícone e texto além da cor. */
export function VerdictPanel({ verdict }: { verdict: Verdict }) {
  const { passed, reasons } = verdict;
  return (
    <section className={`panel verdict ${passed ? "verdict-pass" : "verdict-fail"}`} aria-labelledby="verdict-title">
      <h2 id="verdict-title" className="verdict-title">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          {passed ? <path d="M5 12.5l4.5 4.5L19 7.5" /> : <path d="M6 12h12" />}
        </svg>
        <span>
          Veredito: <strong>{passed ? "Passou" : "Ainda não passou"}</strong>
        </span>
      </h2>
      {passed ? (
        <p>A estratégia cumpriu todos os critérios no trecho de teste.</p>
      ) : (
        <>
          <p>No trecho de teste, a estratégia ainda não cumpriu o que é preciso para seguir para o paper trading:</p>
          <ul>
            {reasons.map((r, i) => (
              <li key={`${i}-${r}`}>{r}</li>
            ))}
          </ul>
        </>
      )}
      <p className="verdict-note">O veredito vale só para o trecho de teste e não é recomendação de investimento.</p>
    </section>
  );
}
