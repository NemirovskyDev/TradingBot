import type { ReactNode } from "react";
import type { RouteId } from "./routes";

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

const ICONS: Record<RouteId, ReactNode> = {
  "visao-geral": (
    <>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </>
  ),
  grafico: (
    <>
      <rect x="5" y="7" width="4" height="9" rx="1" />
      <path d="M7 4v3M7 16v4" />
      <rect x="15" y="5" width="4" height="8" rx="1" />
      <path d="M17 3v2M17 13v5" />
    </>
  ),
  operacoes: (
    <>
      <path d="M9 6h12M9 12h12M9 18h12" />
      <path d="M4 6h.01M4 12h.01M4 18h.01" />
    </>
  ),
  risco: <path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6l8-3z" />,
  glossario: (
    <>
      <path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5z" />
      <path d="M8 7h7" />
    </>
  ),
};

export function NavIcon({ route }: { route: RouteId }) {
  return <Icon>{ICONS[route]}</Icon>;
}
