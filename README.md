# TradingBot

Assistente de investimento e backtest de estratégias de swing, com um painel web que mostra, em linguagem simples, o que o bot fez em cada operação.

> **Simulação, sem envio de ordens e sem recomendação de investimento.** Esta fase só testa estratégias com dados históricos. Os dados da demo pública são sintéticos e vêm rotulados como exemplo.

## O que tem aqui

- **Backend (Python):** baixa preços (yfinance), roda três estratégias de swing com portão de risco, faz backtest sem olhar o futuro, julga a estratégia só no trecho de teste e exporta os resultados em JSON. Um analista opcional (Claude) escreve um relatório curto por ativo, sempre citando as fontes.
- **Painel (React + Vite, em `web/`):** visão geral, gráfico de candles com compras e saídas explicadas, tabela de operações, limites de risco e glossário. Site estático: lê os JSON de `web/public/data`.

## Como rodar

Backend (Python 3.11 ou mais novo):

```bash
pip install -e ".[dev]"
python -m pytest
python -m tradingbot backtest SPY --strategy sma_cross --start 2015-01-01 --end 2025-12-31
python -m tradingbot export --out web/public/data --synthetic
```

O comando `analyze` usa o Claude e precisa da variável de ambiente `ANTHROPIC_API_KEY`; sem ela, o relatório aparece como indisponível.

Painel:

```bash
cd web
npm install
npm run dev
```

Abra `http://localhost:5173/TradingBot/`. Para testes e build: `npm test` e `npm run build`.

## Configuração

Os limites de risco (risco por operação, posições abertas, perda semanal) e os custos simulados ficam em `config.toml`. São pontos de partida para calibrar, não recomendação.

## Estrutura

```
src/tradingbot/   backend (dados, estratégias, risco, backtest, avaliação, analyst, exportação, CLI)
tests/            testes do backend
web/              painel (código, testes e dados de exemplo em web/public/data)
DESIGN.md         sistema de design do painel
PRODUCT.md        contexto do produto
```
