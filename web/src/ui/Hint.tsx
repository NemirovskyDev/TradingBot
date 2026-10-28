import { useEffect, useId, useState, type ReactNode } from "react";
import { TERMS, type TermKey } from "../features/glossary/terms";
import "./ui.css";

interface HintProps {
  term: TermKey;
  children: ReactNode;
}

/**
 * Termo com explicação curta. Abre por foco, toque ou mouse; fecha com Esc (mesmo aberto só pelo mouse), ao perder o foco
 * ou quando o ponteiro sai do termo e da dica. A dica faz parte da área de hover, então dá para mover o mouse até ela.
 */
export function Hint({ term, children }: HintProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const { name, short } = TERMS[term];

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <span className="hint" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className="hint-trigger"
        aria-describedby={open ? id : undefined}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen(true)}
      >
        {children}
      </button>
      {open && (
        <span role="tooltip" id={id} className="hint-tip">
          <strong>{name}</strong>
          {short}
        </span>
      )}
    </span>
  );
}
