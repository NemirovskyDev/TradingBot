import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/** Preferência do sistema por menos movimento; acompanha mudanças feitas com a página aberta. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => window.matchMedia(QUERY).matches);
  useEffect(() => {
    const query = window.matchMedia(QUERY);
    const sync = () => setReduced(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);
  return reduced;
}
