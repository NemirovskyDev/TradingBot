import { TERMS } from "./terms";
import "./glossary.css";

const SORTED = Object.values(TERMS).sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));

export function GlossaryScreen() {
  return (
    <section className="panel glossary" aria-labelledby="glossary-title">
      <h2 id="glossary-title">Termos do painel</h2>
      <p className="panel-sub">Os termos que aparecem no painel, em linguagem simples.</p>
      <dl>
        {SORTED.map((t) => (
          <div key={t.name}>
            <dt>{t.name}</dt>
            <dd>{t.short}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
