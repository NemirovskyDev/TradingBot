// matchMedia controlável nos testes. Por padrão o movimento reduzido fica LIGADO: os testes de tela veem
// os valores finais na hora; os testes de animação ligam o movimento com setReducedMotion(false).
let reduced = true;
const listeners = new Set<EventListenerOrEventListenerObject>();

export function setReducedMotion(value: boolean): void {
  reduced = value;
  listeners.forEach((l) => (typeof l === "function" ? l(new Event("change")) : l.handleEvent(new Event("change"))));
}

export function installMatchMedia(): void {
  window.matchMedia = (query: string) =>
    ({
      get matches() {
        return query.includes("prefers-reduced-motion") ? reduced : false;
      },
      media: query,
      onchange: null,
      addEventListener: (_: string, cb: EventListenerOrEventListenerObject) => listeners.add(cb),
      removeEventListener: (_: string, cb: EventListenerOrEventListenerObject) => listeners.delete(cb),
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
