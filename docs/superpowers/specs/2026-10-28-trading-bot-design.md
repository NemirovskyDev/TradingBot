# TradingBot: design da fase 1 (assistente + backtest)

Data: 2026-10-28. Status: rascunho para revisão do Bernardo.

## 1. Objetivo
Um assistente em Python, de linha de comando, que ajuda a investir (análise de ativos e da lista de acompanhamento) e testa estratégias de swing no histórico antes de qualquer ordem. O objetivo de longo prazo é operar para ganhar capital, mas só depois de a estratégia passar nos critérios da seção 6.

## 2. Decisões já tomadas
- Fase 1: assistente + backtest. Paper trading é a fase 2; dinheiro real é a fase 3 e depende de outra corretora.
- Horizonte: swing (dias a semanas), dados diários.
- Alpaca: só conta paper, se o cadastro permitir. O cadastro de conta real foi bloqueado (sem país de residência fiscal listado). A Alpaca opera ações, ETFs e algumas criptos dos EUA, não a B3.
- Universo inicial: ações e ETFs dos EUA. O yfinance também cobre a B3, então ativos brasileiros entram só na parte do assistente.
- O LLM explica e filtra. Quem decide e executa é código determinístico.

## 3. Fora do escopo da fase 1
Envio de ordens, day trade, opções, dinheiro real, qualquer decisão automática de compra.

## 4. Arquitetura
| Módulo | Função | Depende de |
|---|---|---|
| `data` | Baixa e guarda em cache preços diários (yfinance) e fundamentos básicos. Única parte que conhece a fonte. | yfinance |
| `strategies` | Regras determinísticas (cruzamento de médias, momentum, reversão por RSI). Recebe preços, devolve sinais de compra, venda ou nada. | `data` |
| `backtest` | Roda uma estratégia no histórico com custos e slippage. Devolve retorno, drawdown máximo, Sharpe e número de trades; compara com buy and hold. | `data`, `strategies` |
| `risk` | Portão de risco determinístico entre sinal e ordem (seção 5). | config |
| `analyst` | Subagentes do Claude (técnica, fundamentos, sentimento, risco de notícia) com saída estruturada. Cita a fonte de cada afirmação. Não decide ordens. | `data` |
| `broker` | Interface vazia na fase 1: "enviar ordem" e "ler posições". Na fase 2 ganha a implementação paper da Alpaca. | n/a |

Fluxo: `data` → `strategies` → `backtest` → relatório. O `analyst` roda em paralelo e se junta ao relatório.

## 5. Portão de risco
Código sem LLM, que vence qualquer opinião do `analyst`. Valores iniciais, todos em arquivo de configuração:
- Risco por trade: no máximo 1% do capital; `qtd = (capital × 1%) / (entrada − stop)`.
- Stop obrigatório: sinal sem stop é rejeitado.
- Limites globais: teto de posições abertas, por ativo e por setor; perda máxima na semana pausa o bot.
- Fase 2: toda ordem exige confirmação explícita do Bernardo. Afrouxar isso é decisão dele, depois da validação.

Os subagentes do `analyst` mostram os motivos, não uma nota mágica.

## 6. Testes e critério para passar ao paper trading
Como testar:
- Backtest com custos e slippage, sem look-ahead.
- Treino e teste separados, mais walk-forward. Estado na fase 1 (2026-10-28): o veredito usa só o corte simples (30% mais recentes como teste); `walk_forward_windows` existe e tem teste, mas ainda não entra no veredito. Passa a valer quando calibrarmos o critério (por exemplo, exigir que a maioria das janelas passe).
- Poucos parâmetros, para evitar overfitting.
- Testes unitários em `risk` e `backtest`, porque um bug neles gera lucro falso.

Uma estratégia só avança se, no período fora da amostra:
- bater o buy and hold ajustado ao risco;
- tiver drawdown máximo aceitável para o Bernardo;
- tiver trades suficientes para ter significância estatística;
- continuar positiva quando o custo dobra.

Falhar é um resultado válido: a estratégia é descartada. Os números acima são pontos de partida a calibrar, não recomendação de investimento.

## 7. Referências (só como ideia, nada instalado)
- `jakeschincariol/day-trader-skill`: portão de risco antes da ordem e simulação em dados passados. É de day trade e tem tom de marketing.
- `zubair-trabzada/ai-trading-claude`: divisão em subagentes. A nota 0-100 não tem validação, então não é adotada.
Ambos usam instalação por script ou clone; se algum dia forem testados, ler `SKILL.md` e `install.sh` antes.

## 8. Pontos em aberto
- Cadastro na Alpaca paper: ainda não testado.
- Corretora para a fase 3 (Interactive Brokers foi citada de memória e precisa de conferência).
- Fonte de notícias e fundamentos do `analyst`.
- Limites numéricos da seção 5 e do critério da seção 6, a calibrar com o Bernardo.
