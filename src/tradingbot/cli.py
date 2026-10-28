"""Linha de comando: `backtest TICKER` (fora da amostra, com veredito) e `analyze TICKER` (relatório do analyst)."""
import argparse
import inspect
import sys
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from tradingbot.analyst import AnalystReport, analyze
from tradingbot.config import load_config
from tradingbot.data import DataError, get_prices
from tradingbot.demo import make_synthetic_prices
from tradingbot.evaluate import Evaluation, PromotionCriteria, evaluate_detailed
from tradingbot.export import export_run, write_index
from tradingbot.strategies import STRATEGIES

DISCLAIMER = "Simulação com dados históricos. Não é recomendação de investimento."


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _backtest_text(ticker: str, strategy: str, ev: Evaluation) -> str:
    lines = [f"# Backtest {ticker} · {strategy} (trecho fora da amostra)", ""]
    if ev.strategy and ev.benchmark:
        s, b = ev.strategy.metrics, ev.benchmark.metrics
        lines += [
            f"- Retorno da estratégia: {_pct(s['total_return'])}",
            f"- Comprar e segurar: {_pct(b['total_return'])}",
            f"- Maior queda: {_pct(s['max_drawdown'])}",
            f"- Sharpe: {s['sharpe']:.2f}".replace(".", ","),
            f"- Operações: {int(s['n_trades'])}",
            f"- Sinais bloqueados pelo risco: {len(ev.strategy.blocked)}",
        ]
    lines += ["", f"Veredito: {'Passou' if ev.verdict.passed else 'Ainda não passou'}"]
    lines += [f"- {r}" for r in ev.verdict.reasons]
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def _analysis_text(rep: AnalystReport) -> str:
    if not rep.available:
        why = (
            "todas as consultas falharam (confira a chave e a conexão)."
            if rep.failed
            else "defina ANTHROPIC_API_KEY."
        )
        return f"# Análise {rep.ticker}\n\nAnalista indisponível: {why}\n\n{DISCLAIMER}"
    lines = [f"# Análise {rep.ticker}", ""]
    for section, findings in rep.sections.items():
        lines.append(f"## {section}")
        if section in rep.failed:
            lines.append("- seção indisponível (falha na consulta)")
        else:
            lines += [f"- {f.claim} (fonte: {f.source})" for f in findings] or ["- sem dados nesta seção"]
        lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _save(out: Path, ticker: str, text: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{ticker.upper()}_{date.today().isoformat()}.md"
    path.write_text(text + "\n", encoding="utf-8")
    return path


def _cmd_backtest(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(Path(args.config))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 2
    prices = get_prices(args.ticker, args.start, args.end)
    ev = evaluate_detailed(
        prices, STRATEGIES[args.strategy], PromotionCriteria(), cfg.risk, cfg.costs, cfg.initial_capital
    )
    text = _backtest_text(args.ticker.upper(), args.strategy, ev)
    print(text)
    print(f"\nRelatório salvo em {_save(Path(args.out), args.ticker, text)}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    start = (date.today() - timedelta(days=400)).isoformat()
    prices = get_prices(args.ticker, start, date.today().isoformat())
    text = _analysis_text(analyze(args.ticker.upper(), prices))
    print(text)
    print(f"\nRelatório salvo em {_save(Path(args.out), args.ticker, text)}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(Path(args.config))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out)
    prices = make_synthetic_prices()
    runs = []
    for name in sorted(STRATEGIES):
        ev = evaluate_detailed(prices, STRATEGIES[name], PromotionCriteria(), cfg.risk, cfg.costs, cfg.initial_capital)
        if ev.strategy is None or ev.benchmark is None or ev.test is None:
            print(f"Erro: histórico curto demais para exportar {name}.", file=sys.stderr)
            return 2
        defaults = {k: v.default for k, v in inspect.signature(STRATEGIES[name]).parameters.items() if k != "prices"}
        params = {"estrategia": defaults, "risco": asdict(cfg.risk), "custos": asdict(cfg.costs)}
        run_id = f"demo-{name}"
        export_run(run_id, "DEMO", name, params, ev.test, ev.strategy, ev.benchmark, ev.verdict, out, synthetic=True)
        runs.append({"id": run_id, "ticker": "DEMO", "strategy": name, "label": f"Exemplo · {name}"})
    print(f"{len(runs)} execuções de exemplo gravadas em {write_index(out, runs).parent}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tradingbot", description="Assistente de investimento e backtest (sem ordens).")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="testa uma estratégia no histórico e dá o veredito")
    bt.add_argument("ticker")
    bt.add_argument("--strategy", choices=sorted(STRATEGIES), default="sma_cross")
    bt.add_argument("--start", default="2015-01-01")
    bt.add_argument("--end", default=date.today().isoformat())
    bt.add_argument("--config", default="config.toml")
    bt.add_argument("--out", default="reports")
    bt.set_defaults(func=_cmd_backtest)

    an = sub.add_parser("analyze", help="relatório do analyst (precisa de ANTHROPIC_API_KEY)")
    an.add_argument("ticker")
    an.add_argument("--out", default="reports")
    an.set_defaults(func=_cmd_analyze)

    ex = sub.add_parser("export", help="gera os JSON de exemplo para o front")
    ex.add_argument("--synthetic", action="store_true", required=True, help="usa dados sintéticos rotulados")
    ex.add_argument("--out", default="web/public/data")
    ex.add_argument("--config", default="config.toml")
    ex.set_defaults(func=_cmd_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except DataError as exc:
        print(f"Erro nos dados: {exc}", file=sys.stderr)
        return 2
