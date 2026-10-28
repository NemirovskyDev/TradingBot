import { Component, type ErrorInfo, type ReactNode } from "react";
import "./ui.css";

interface Props {
  children: ReactNode;
  onReset?: () => void;
}

interface State {
  failed: boolean;
}

/** Rede de segurança: um erro ao desenhar uma tela vira uma mensagem com "Tentar de novo", nunca uma tela em branco. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Erro ao desenhar a tela:", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" className="state state-error">
        <p className="state-title">Não foi possível desenhar esta tela</p>
        <p>Algo inesperado aconteceu ao montar os gráficos ou as tabelas. Os dados podem estar em um formato que o painel não conhece.</p>
        <button
          type="button"
          className="button"
          onClick={() => {
            this.setState({ failed: false });
            this.props.onReset?.();
          }}
        >
          Tentar de novo
        </button>
      </div>
    );
  }
}
