"""Linha de comando: `backtest TICKER` (fora da amostra, com veredito) e `analyze TICKER` (relatório do analyst)."""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from tradingbot.analyst import AnalystReport, analyze
from tradingbot.catalog import DEFAULT_PATH, load_catalog, write_catalog
from tradingbot.catalog_build import build_from_network, check_expanded
from tradingbot.catalog_seed import B3, FII, US
from tradingbot.config import load_config
from tradingbot.data import DataError, get_prices
from tradingbot.demo import make_synthetic_prices
from tradingbot.evaluate import Evaluation, PromotionCriteria, evaluate_detailed
from tradingbot.export import export_run, publish, write_index
from tradingbot.export_portfolios import export_portfolios
from tradingbot.export_real import MAX_SKIPPED_FRACTION, export_real, strategy_params
from tradingbot.portfolio_data import build_price_table
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
    if args.portfolios:
        return _export_portfolios(args)
    return _export_real(args, cfg) if args.real else _export_synthetic(args, cfg)


def _export_portfolios(args: argparse.Namespace) -> int:
    """Baixa os instrumentos das carteiras, roda as metodologias e grava portfolios.json (o arquivo antigo fica se algo falhar)."""
    try:
        table = build_price_table(date.fromisoformat(args.history_start), date.fromisoformat(args.end))
        path = export_portfolios(table, Path(args.out))
    except ValueError as exc:  # datas inválidas ou sem janela comum
        print(f"Erro nas carteiras (nada foi gravado): {exc}", file=sys.stderr)
        return 2
    print(f"Carteiras gravadas em {path}")
    return 0


def _export_real(args: argparse.Namespace, cfg) -> int:
    """Um conjunto de execuções por ativo do catálogo. Não troca o que já está publicado se a fonte falhou em massa."""
    try:
        assets = load_catalog(Path(args.catalog))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro no catálogo: {exc}", file=sys.stderr)
        return 2
    if args.limit:
        assets = assets[: args.limit]
    out = Path(args.out)
    result = export_real(assets, cfg, out, args.start, args.end)
    if result.skipped:
        print(f"Ignorados ({len(result.skipped)}): " + "; ".join(result.skipped))
    if not result.runs:
        print("Erro: nenhum ativo gerou dados; nada foi gravado.", file=sys.stderr)
        return 2
    if not args.limit and len(result.skipped) > MAX_SKIPPED_FRACTION * len(assets):
        print(
            f"Erro: mais de {MAX_SKIPPED_FRACTION:.0%} dos ativos falharam (a fonte pode estar limitando as requisições); "
            "o índice e a limpeza foram pulados para não trocar o que já está publicado.",
            file=sys.stderr,
        )
        return 2
    # --limit é modo de teste: o índice fica só com esses ativos e nada é apagado
    publish(out, result.runs, prune=not args.limit)
    if args.limit:
        print(f"Aviso: modo de teste (--limit {args.limit}); o índice tem só esses ativos e nenhum arquivo antigo foi apagado.")
    print(f"{len({r['ticker'] for r in result.runs})} ativos, {len(result.runs)} execuções gravadas em {out}")
    return 0


def _export_synthetic(args: argparse.Namespace, cfg) -> int:
    out = Path(args.out)
    prices = make_synthetic_prices()
    runs = []
    for name in sorted(STRATEGIES):
        ev = evaluate_detailed(prices, STRATEGIES[name], PromotionCriteria(), cfg.risk, cfg.costs, cfg.initial_capital)
        if ev.strategy is None or ev.benchmark is None or ev.test is None:
            print(f"Erro: histórico curto demais para exportar {name}.", file=sys.stderr)
            return 2
        params = strategy_params(name, cfg)
        run_id = f"demo-{name}"
        export_run(run_id, "DEMO", name, params, ev.test, ev.strategy, ev.benchmark, ev.verdict, out, synthetic=True)
        runs.append({"id": run_id, "ticker": "DEMO", "strategy": name, "label": f"Exemplo · {name}"})
    print(f"{len(runs)} execuções de exemplo gravadas em {write_index(out, runs).parent}")
    return 0


def _cmd_catalog(args: argparse.Namespace) -> int:
    """Monta o catálogo pela rede. Só grava se as fontes responderam e o resultado é válido; o arquivo antigo fica intacto se falhar."""
    try:
        assets = build_from_network(args.sp, args.b3, args.fii)
        check_expanded(assets, {US: args.sp, B3: args.b3, FII: args.fii})
        out = write_catalog(assets, Path(args.out))
    except Exception as exc:  # noqa: BLE001 - rede, parse ou validação: o usuário precisa da mensagem, não do traceback
        print(f"Erro ao montar o catálogo (nada foi gravado): {exc}", file=sys.stderr)
        return 2
    print(f"{len(assets)} ativos gravados em {out}")
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

    ex = sub.add_parser("export", help="gera os JSON do painel (dados reais do catálogo ou sintéticos de exemplo)")
    mode = ex.add_mutually_exclusive_group(required=True)
    mode.add_argument("--real", action="store_true", help="baixa os ativos do catálogo e roda as 3 estratégias em cada um")
    mode.add_argument("--synthetic", action="store_true", help="usa dados sintéticos rotulados")
    mode.add_argument("--portfolios", action="store_true", help="roda as 7 metodologias de carteira (ARCA e outras) e grava portfolios.json")
    ex.add_argument("--out", default="web/public/data")
    ex.add_argument("--config", default="config.toml")
    ex.add_argument("--catalog", default=str(DEFAULT_PATH))
    ex.add_argument("--start", default="2010-01-01")
    ex.add_argument("--end", default=date.today().isoformat())
    ex.add_argument("--history-start", default="2004-01-01", help="início do histórico baixado para as carteiras (as regras de tendência precisam de anos de aquecimento)")
    ex.add_argument("--limit", type=int, default=0, help="só os N primeiros ativos do catálogo (para testar)")
    ex.set_defaults(func=_cmd_export)

    ca = sub.add_parser("catalog", help="monta o catálogo de ativos (seed + S&P 500, Ibovespa e FIIs; usa a rede)")
    ca.add_argument("--out", default=str(DEFAULT_PATH))
    ca.add_argument("--sp", type=int, default=60, help="quantas ações do S&P 500 acrescentar")
    ca.add_argument("--b3", type=int, default=40, help="quantas ações da B3 acrescentar")
    ca.add_argument("--fii", type=int, default=40, help="quantos FIIs acrescentar")
    ca.set_defaults(func=_cmd_catalog)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except DataError as exc:
        print(f"Erro nos dados: {exc}", file=sys.stderr)
        return 2
