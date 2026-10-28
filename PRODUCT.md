# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
React + Vite (escolha do Bernardo, 2026-10-28). Sai como site estático, sem backend; lê arquivos JSON exportados pelo backtest em Python.

## Users
Dois públicos com o mesmo peso: (1) pessoas leigas em finanças, que nunca viram um gráfico de candles e precisam entender o que o bot faz; (2) recrutadores e desenvolvedores que avaliam a qualidade técnica do projeto no GitHub e no portfólio do Bernardo.

## Product Purpose
Painel que mostra, de forma visual e explicada, o que o TradingBot faz: o gráfico do ativo, as compras e vendas (simuladas na fase 1), a curva do capital contra "comprar e segurar", as métricas e o veredito do critério de promoção. Serve também de vitrine do projeto. Sucesso: um leigo entende em minutos o que aconteceu em cada trade, e um dev reconhece o cuidado técnico.

## Positioning
Um painel de trading que explica cada decisão em linguagem simples e é honesto sobre os limites (simulação, sem recomendação de investimento), em vez de prometer lucro.

## Operating Context
Demo estática pública (GitHub Pages) lendo JSON pré-gerado pelo backtest. Na fase 2 (paper trading) o mesmo painel poderá ler posições da conta paper, só em modo local. O backend Python e a spec estão em `docs/superpowers/`.

## Capabilities and Constraints
- Fase 1 não envia ordens: "comprando/vendendo" significa trades simulados do backtest.
- Sem backend e sem chaves no repositório; o painel público nunca conecta a conta real.
- Aviso visível de "simulação, não é recomendação de investimento".
- Cada trade tem uma frase de explicação; métricas têm glossário rápido.
- Dados de exemplo ainda não existem (o backtest não foi implementado).

## Brand Commitments
- Repositório próprio no GitHub com demo publicada; o Portfólio do Bernardo aponta para ele (integração direta pode vir depois).
- O Bernardo quer animações como diferencial (regra de 2026-10-28), sem limite de "poucas".
- Todo código do front passa pela pipeline de qualidade do CLAUDE.md.
- Direção visual (2026-10-28): o Bernardo escolheu o padrão da categoria, um painel de trading limpo, executado com todo o capricho e sem humor nem fantasia. Régua de qualidade: TradingView (gráficos), Robinhood (simplicidade para leigos), Stripe Dashboard (clareza de tabelas e métricas) e Linear (acabamento e animações sutis). O Box Score e as demais direções sorteadas foram recusadas; duas ideias podem ser reaproveitadas se ele quiser: jogada nova destacada até ser vista e hachura para sinal bloqueado pelo risco.
- Cores de texto precisam passar WCAG AA: usar verde `#13734a`, vermelho `#b3261e` e laranja `#c2410c` ou mais escuros sobre fundo claro (o detector reprovou tons mais claros).

## Evidence on Hand
Nenhuma. Não existem resultados de backtest, números de desempenho, depoimentos nem usuários. Nada disso pode ser inventado na interface; os dados de demo devem ser rotulados como exemplo.

## Product Principles
1. Explicar antes de impressionar: cada gráfico e número tem uma leitura em linguagem simples.
2. Honestidade sobre simulação: nunca sugerir lucro garantido nem dinheiro real.
3. Demo reproduzível: tudo na tela vem de JSON gerado pelo backtest, nada hardcoded.
4. Impressionar sem esconder: o capricho técnico e visual aparece, mas nunca à custa da clareza.

## Accessibility & Inclusion
Respeitar `prefers-reduced-motion`, não esconder conteúdo atrás de animação, contraste adequado nos gráficos e informação que não dependa só de cor (compra/venda também por forma e texto). Textos em português do Brasil.
