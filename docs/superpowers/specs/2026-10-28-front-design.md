# TradingBot Front: design do painel (fase 1)

Data: 2026-10-28. Status: rascunho para revisão do Bernardo. Contexto de produto: `PRODUCT.md`. Backend: `2026-10-28-trading-bot-design.md`.

## 1. Objetivo
Painel web que mostra, de forma visual e explicada, o que o TradingBot fez: gráfico do ativo, compras e vendas simuladas, curva do capital contra "comprar e segurar", métricas e o veredito do critério de promoção. Serve a dois públicos com o mesmo peso: leigos em finanças (precisam entender cada trade) e recrutadores e devs (avaliam a qualidade do projeto no GitHub e no portfólio).

## 2. Decisões já tomadas
- Modo da superfície: **Operate** (painel de trabalho). Construído em código, sem comp de imagem.
- Direção visual: **padrão da categoria**, executado com todo o capricho, sem fantasia. Régua de qualidade: TradingView (gráficos), Robinhood (simplicidade para leigos), Stripe Dashboard (tabelas e métricas), Linear (acabamento e animações sutis).
- Stack: React + Vite + TypeScript, site estático, sem backend.
- Hospedagem: pasta `web/` no repositório `NemirovskyDev/TradingBot`, demo no GitHub Pages; o Portfólio só aponta para ela.
- Animações são parte do diferencial (regra de 2026-10-28), com a trava de acessibilidade `prefers-reduced-motion`.
- Todo código passa pela pipeline de qualidade do CLAUDE.md (camadas 2 a 11).

## 3. Fora do escopo
Envio de ordens, login, conta real, dados ao vivo, backend próprio, edição de estratégias pela interface. Na fase 2 o mesmo painel poderá ler posições da conta paper, só em modo local.

## 4. Telas
Navegação lateral fixa; padrões de navegação e controles são os conhecidos (links, abas, tabelas ordenáveis, selects).
1. **Visão geral:** cartões de métricas (retorno da estratégia, retorno de comprar e segurar, maior queda, nº de operações), veredito de promoção em linguagem simples com os motivos, e a curva de capital contra o benchmark.
2. **Gráfico:** candles do ativo com marcadores de compra e saída; clicar em um marcador abre um painel com a explicação do trade ("comprou porque a média curta cruzou a longa para cima").
3. **Operações:** tabela ordenável (data, ação, preço, quantidade, resultado, motivo), com filtro por resultado; linha ligada ao marcador no gráfico.
4. **Risco:** limites configurados (risco por trade, teto de posições, perda semanal) e lista de sinais bloqueados pelo portão de risco, cada um com o motivo.
5. **Glossário:** termos usados (candle, drawdown, Sharpe, stop, buy and hold) em frases curtas; os termos também aparecem como dicas ao lado dos números.

Seletor de execução (ativo + estratégia) no topo, alimentado por `index.json`. Aviso fixo: "Simulação com dados de exemplo. Não é recomendação de investimento."

## 5. Contrato de dados (backend → front)
O backtest exporta arquivos JSON versionados; o front só lê, nada é hardcoded.
- `public/data/index.json`: `{ schema: 1, runs: [{ id, ticker, strategy, label }] }`.
- `public/data/runs/{id}.json`:
  - `meta`: `{ ticker, strategy, params, start, end, initial_capital, generated_at, synthetic: boolean }`
  - `prices`: `[{ date, open, high, low, close, volume }]`
  - `equity`: `[{ date, strategy, buy_hold }]`
  - `trades`: `[{ id, entry_date, entry_price, exit_date, exit_price, qty, stop, pnl_pct, reason_entry, reason_exit }]`
  - `blocked`: `[{ date, ticker, reason }]`
  - `metrics`: `{ total_return, benchmark_return, max_drawdown, sharpe, n_trades }`
  - `verdict`: `{ passed: boolean, reasons: string[] }`
- Datas em `AAAA-MM-DD`; retornos e drawdown como frações (0,124 = 12,4%).
- O front valida cada arquivo ao carregar (schema) e mostra erro claro se faltar campo ou a versão for diferente.
- **Mudança no plano do backend:** adicionar uma tarefa `export_json(result, verdict, path)` que gera esses arquivos; as frases `reason_entry` e `reason_exit` vêm das estratégias (cada sinal carrega um motivo em português).

## 6. Arquitetura do front
- `web/src/data/`: carrega e valida JSON (`loadIndex`, `loadRun`), tipos TypeScript derivados do contrato.
- `web/src/charts/`: gráficos com **Lightweight Charts** (TradingView, Apache-2.0, exige aviso de atribuição): candles com marcadores, curva de capital.
- `web/src/features/{overview,chart,trades,risk,glossary}/`: uma pasta por tela.
- `web/src/ui/`: componentes de base (cartão de métrica, tabela ordenável, dica de glossário, aviso de simulação).
- `web/src/motion/`: animações compartilhadas com a biblioteca `motion`, em um único lugar.
- Roteamento por hash (funciona no GitHub Pages sem configuração de servidor); `base` do Vite igual ao nome do repositório.

## 7. Estados
Carregando (esqueleto), erro de dados (mensagem e botão de tentar de novo), execução sem trades (explica por quê), tabela filtrada vazia, arquivo com versão incompatível, execução marcada `synthetic` (selo "exemplo" visível).

## 8. Animações
Entrada e transição de telas, contagem progressiva dos números, o gráfico desenhando-se ao carregar, marcadores aparecendo em sequência, linha da tabela destacada ao selecionar o trade. Tudo em um módulo só, com a trava: com `prefers-reduced-motion` as animações viram troca instantânea e nenhum conteúdo fica escondido atrás de animação.

## 9. Acessibilidade e responsividade
- Contraste AA: texto usa verde `#13734a`, vermelho `#b3261e` e laranja `#c2410c` ou mais escuros sobre fundo claro.
- Compra e saída nunca dependem só de cor: forma do marcador e texto também.
- Cada gráfico tem alternativa em tabela; navegação completa por teclado; foco visível; rótulos para leitores de tela.
- Layout de 390 px a 1600 px; no celular a navegação vira barra inferior e o gráfico ocupa a largura toda.
- Português do Brasil.

## 10. Testes e critérios de pronto
- Vitest + Testing Library: carregamento e validação do JSON (campos faltando, versão errada), ordenação e filtro da tabela, estados de erro e vazio, formatação de números em pt-BR.
- Verificação de acessibilidade automatizada (axe) por tela.
- Build do Vite sem erros, tipagem estrita, lint.
- Pronto quando: um leigo consegue dizer, em poucos minutos, por que o bot comprou e vendeu em um trade qualquer; o painel funciona em 390 px e em 1440 px; nenhum dado vem de fora dos JSON; o aviso de simulação está visível em todas as telas.

## 11. Pontos em aberto
- Dados da demo: usar série sintética (rotulada) ou dados reais do yfinance. Redistribuir dados do Yahoo publicamente pode ter restrição de termos; recomendo sintéticos até conferirmos.
- Fonte tipográfica e tokens finais: definidos na construção (Impeccable) e registrados em `DESIGN.md`; evitar as fontes que o detector marca como genéricas.
- Deploy no GitHub Pages por GitHub Actions: só configurar com o OK do Bernardo.
- Integração direta ao Portfólio: depois da demo pública.
