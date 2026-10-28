// Único ponto de import da biblioteca `motion`: todas as animações do painel nascem aqui.
// Regras: movimento reduzido liga tudo no valor final; se a animação não rodar, um temporizador de
// segurança devolve o conteúdo visível e o número no valor final.
import { animate } from "motion";
import { useLayoutEffect, useRef, type ReactNode, type RefObject } from "react";
import { useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

export { useReducedMotion };

const EASE_OUT: [number, number, number, number] = [0.16, 1, 0.3, 1]; // saída exponencial
const SAFETY_MS = 300;

interface Stoppable {
  stop: () => void;
  finished?: Promise<unknown>;
}

/** Roda a animação e garante `done` ao terminar, ao ser cancelada ou, no pior caso, pelo temporizador de segurança. */
function runWithSafety(start: () => Stoppable, done: () => void, totalMs: number): () => void {
  const controls = start();
  const timer = window.setTimeout(() => {
    controls.stop(); // animação que não terminou no prazo: para e deixa o estado final
    done();
  }, totalMs + SAFETY_MS);
  controls.finished?.then(done, done);
  return () => {
    window.clearTimeout(timer);
    controls.stop();
    done();
  };
}

interface CountUpProps {
  value: number;
  format: (n: number) => string;
  duration?: number;
}

/** Número que sobe de 0 até o valor. Termina sempre no valor final, mesmo que a animação trave. */
export function CountUp({ value, format, duration = 0.9 }: CountUpProps) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(value);

  useLayoutEffect(() => {
    if (reduced) {
      setShown(value);
      return;
    }
    setShown(0);
    return runWithSafety(
      () => animate(0, value, { duration, ease: EASE_OUT, onUpdate: setShown }),
      () => setShown(value),
      duration * 1000,
    );
  }, [value, duration, reduced]);

  return <span>{format(shown)}</span>;
}

interface RevealProps {
  children: ReactNode;
  delay?: number;
  className?: string;
}

/** Entrada curta (sobe 14 px e aparece). Começa escondido só enquanto a animação roda. */
export function Reveal({ children, delay = 0, className }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || reduced) return;
    el.style.opacity = "0";
    const clear = () => {
      el.style.opacity = "";
      el.style.transform = "";
    };
    return runWithSafety(
      () => animate(el, { opacity: [0, 1], transform: ["translateY(14px)", "translateY(0px)"] }, { duration: 0.5, delay, ease: EASE_OUT }),
      clear,
      (0.5 + delay) * 1000,
    );
  }, [delay, reduced]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

/** O gráfico se desenha da esquerda para a direita quando `key` muda (nova execução). */
export function useDrawIn(ref: RefObject<HTMLElement | null>, key: unknown): void {
  const reduced = useReducedMotion();

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || reduced) return;
    el.style.clipPath = "inset(0 100% 0 0)";
    const clear = () => {
      el.style.clipPath = "";
    };
    return runWithSafety(
      () => animate(el, { clipPath: ["inset(0 100% 0 0)", "inset(0 0% 0 0)"] }, { duration: 1.1, ease: EASE_OUT }),
      clear,
      1100,
    );
    // `key` identifica o conjunto de dados mostrado; trocar de dados redesenha o gráfico
  }, [ref, reduced, key]);
}
