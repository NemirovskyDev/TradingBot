---
name: TradingBot
description: Painel escuro e didático de backtests (carteiras e estratégias) com dados reais, com o acabamento do padrão da categoria.
colors:
  ground: "#0b1118"
  surface: "#121a23"
  raised: "#1c2733"
  line: "#243241"
  line-strong: "#5b6e83"
  ink: "#e8eef4"
  ink-soft: "#9fb0c0"
  action: "#7cb2ff"
  action-hover: "#a3c8ff"
  action-ink: "#08111c"
  action-wash: "#132641"
  gain: "#3ddc97"
  gain-wash: "#0f2a20"
  loss: "#ff7b7b"
  loss-wash: "#2d1619"
  loss-line: "#6b2d31"
  alert: "#f5a524"
  benchmark: "#8fa1b3"
  ref-cdi: "#8fa1b3"
  ref-ibov: "#f5a524"
  ref-sp: "#c9a7ff"
typography:
  display:
    fontFamily: "Hanken Grotesk Variable, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "2rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Hanken Grotesk Variable, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Hanken Grotesk Variable, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 650
    lineHeight: 1.3
  body:
    fontFamily: "Hanken Grotesk Variable, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tabular-nums"
  label:
    fontFamily: "Hanken Grotesk Variable, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 560
    lineHeight: 1.5
rounded:
  sm: "4px"
  md: "8px"
  pill: "999px"
spacing:
  "1": "0.25rem"
  "2": "0.5rem"
  "3": "0.75rem"
  "4": "1rem"
  "5": "1.5rem"
  "6": "2rem"
  "7": "3rem"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 1rem"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  nav-item:
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 0.75rem"
  nav-item-active:
    backgroundColor: "{colors.action-wash}"
    textColor: "{colors.action}"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "1.5rem"
  badge:
    backgroundColor: "{colors.action-wash}"
    textColor: "{colors.action}"
    rounded: "{rounded.pill}"
    padding: "2px 0.75rem"
  select:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 0.75rem"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "40px"
    padding: "0 1rem"
  chip-selected:
    backgroundColor: "{colors.action-wash}"
    textColor: "{colors.action}"
  goal-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.md}"
    padding: "1rem"
  goal-card-selected:
    backgroundColor: "{colors.action-wash}"
    textColor: "{colors.action}"
  button-quiet:
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "40px"
    padding: "0 1rem"
  profile-warning:
    backgroundColor: "{colors.loss-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0.75rem 1rem"
  hint-tip:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0.75rem 1rem"
  simulation-banner:
    backgroundColor: "{colors.action-wash}"
    textColor: "{colors.ink}"
    padding: "0.5rem 1rem"
---

# Design System: TradingBot

## Overview

**Creative North Star: "The Night Ledger"**

Um painel escuro, grafite azulado (tema escolhido pelo Bernardo em 2026-10-28, único, sem alternância), que faz o que a categoria espera (régua TradingView, Robinhood, Stripe, Linear) e se diferencia pela clareza didática e pelo acabamento: cada número e cada marcador se explicam em uma frase. Não há fantasia visual. A confiança vem de hierarquia limpa, números tabulares, contraste verificado e honestidade sobre ser uma simulação.

A densidade é média. Uma sans de trabalho, um azul de ação, verde e vermelho só para resultado, âmbar só para alerta. Superfícies grafite sobre um fundo mais escuro, separadas por linhas finas; sombra suave só nos painéis. Todo texto passa AA (conferido em `contrast.test.ts`).

**Key Characteristics:**
- Claro, uma única sans autohospedada (Hanken Grotesk Variable via @fontsource-variable), algarismos tabulares no corpo inteiro.
- Raio de 8px em tudo que é caixa; 4px só no anel de foco; pílula só no selo.
- Painéis planos com borda e sombra suave; faixa de métricas é um painel com divisórias, não quatro cartões.
- Movimento curto e sempre com saída de segurança; com movimento reduzido tudo aparece pronto.
- Todo texto passa AA, travado por `web/src/contrast.test.ts`.

## Colors

Grafite azulado com um azul claro de ação; verde e vermelho reservados a resultado.

### Primary
- **Azul de Ação** (action): botão primário, item de navegação ativo, links de linha, anel de foco, linha de capital, linha de entrada, operação selecionada. Hover do botão em `action-hover`; o texto do botão usa `action-ink` (escuro).
- **Lavado de Ação** (action-wash): fundo do aviso de simulação, do selo, do item ativo e da seleção de texto.

### Secondary
- **Verde Ganho** (gain) e **Lavado de Ganho** (gain-wash): resultado positivo, vela de alta, marcador de compra, ícone de veredito aprovado.
- **Vermelho Perda** (loss) e **Lavado de Perda** (loss-wash): resultado negativo, vela de baixa, marcador de saída com prejuízo, linha de stop.

### Tertiary
- **Âmbar Alerta** (alert): veredito não aprovado (ícone). Só texto/ícone sobre as superfícies escuras. O mesmo valor também é a cor da linha do Ibovespa nos gráficos de carteiras (`ref-ibov`); lá é identidade de série, não alerta.

### Neutral
- **Fundo Grafite** (ground): fundo da página, hover de linha, faixa do filtro.
- **Superfície** (surface): painéis, navegação, campos. **Elevada** (raised): tooltip de glossário, link de pular ao conteúdo, selo de referência.
- **Linha** (line): todas as bordas e divisórias de 1px.
- **Tinta** (ink): texto principal.
- **Tinta Suave** (ink-soft): rótulos, textos secundários, navegação inativa.
- **Linha forte** (line-strong, 3:1 sobre a superfície): borda de controles, rolagem, pausa tracejada. **Benchmark** (benchmark, 3:1): linha de referência do gráfico por ativo. **Linha de perda** (loss-line): borda de erro.

### Referências dos gráficos de carteiras
- **Cinza-azul CDI** (ref-cdi, mesmo valor de `benchmark`): CDI, tracejada.
- **Âmbar Ibovespa** (ref-ibov): Ibovespa, pontilhada.
- **Lilás S&P** (ref-sp): S&P 500, tracejada longa.
- A carteira escolhida é sempre a linha azul de ação, sólida e mais grossa (3, contra 2 das referências).

### Named Rules
**The Result-Only Color Rule.** Verde e vermelho significam resultado financeiro e nada mais; ação e navegação usam o azul.
**The Never-Alone Rule.** Cor nunca é o único sinal: vela de alta é vazada e de baixa é cheia, compra é seta para cima abaixo da barra e saída é seta para baixo acima, cada referência tem formato de linha próprio (tracejada, pontilhada, tracejada longa), resultados trazem sinal e palavra.

## Typography

**Display Font:** Hanken Grotesk Variable (com system-ui, -apple-system, Segoe UI, sans-serif)
**Body Font:** a mesma
**Label/Mono Font:** nenhuma; sem display face, sem monospace

**Character:** Uma sans neutra e legível que carrega o painel inteiro; hierarquia por tamanho e peso, não por troca de família. Números tabulares evitam que colunas pulem.

### Hierarchy
- **Display** (650, 2rem, 1.2): token `--text-2xl` existe; não há uso encontrado nos componentes.
- **Headline** (650, 1.5rem, 1.2, -0.015em): título da execução (h1) e valor das métricas.
- **Title** (650, 1.125rem, 1.3): títulos de painel (h2), marca, detalhe da operação (h3), valores de limites de risco.
- **Body** (400, 0.9375rem, 1.5): texto corrente; textos longos limitados a 46rem no glossário.
- **Label** (560-600, 0.8125rem): rótulos de métrica, cabeçalhos de tabela, legendas, notas, aviso de simulação. Sem caixa alta, sem kicker.

### Named Rules
**The One Family Rule.** Uma família só; peso (400, 560, 600, 650, 700 na marca) e tamanho fazem a hierarquia.

## Layout

Navegação lateral fixa de 232px à esquerda; conteúdo em coluna com `main` de até 1240px, padding 2rem. Faixa de aviso de simulação no topo, fora do shell. Visão geral: faixa de métricas de 4 colunas, depois grade 2fr/1fr (curva de capital e veredito). Tela de gráfico: 2fr / mínimo 18rem. Ritmo vertical em `--space-5` (1.5rem) entre blocos, `--space-3`/`--space-4` dentro.

Responsivo: abaixo de 1024px as grades viram uma coluna. Abaixo de 768px a navegação vira barra inferior fixa de 5 itens (ícone sobre rótulo, 52px, respeita safe-area), a marca some, as métricas viram 2x2 e as tabelas viram cartões.

Alvos de toque: 40px (botões, selects, nav), 44px (itens de lista de operações), 36px (filtro segmentado).

## Elevation & Depth

Híbrido discreto: profundidade vem de borda de 1px mais fundo um pouco mais claro sobre o fundo escuro; uma sombra suave e difusa só nos painéis e no tooltip.

### Shadow Vocabulary
- **Painel** (`box-shadow: 0 1px 2px rgb(0 0 0 / 0.45), 0 6px 18px rgb(0 0 0 / 0.35)`): painéis, painel de perfil e tooltip de glossário (`--shadow`).
- **Segmento ativo** (`box-shadow: 0 1px 2px rgb(0 0 0 / 0.5)`): botão selecionado do filtro de operações.

### Named Rules
**The No-Nested-Card Rule.** Um painel nunca contém outro painel com borda e sombra; subdivisão usa divisórias de 1px (faixa de métricas, notas, fatos da operação).

## Shapes

Raio pequeno e uniforme: 8px (`--radius`) para painéis, botões, campos, itens de lista e cartões móveis; 6px para o botão interno do filtro; 4px no anel de foco e em código inline; pílula (999px) no selo "exemplo" e nos chips de carteira. Bordas 1px em `--line`; borda tracejada em `line-strong` só no aviso de "selecione uma operação". Foco: contorno de 2px em azul de ação, offset 2px.

## Components

### Buttons
- **Shape:** raio 8px, altura mínima 40px, padding 0 1rem, peso 600.
- **Primary:** fundo azul de ação, texto escuro (`action-ink`); hover `action-hover` em 120ms ease-out (AA testado).
- **Controles ocultos:** botões de ordenar, de dica e de filtro são sem fundo; filtro segmentado marca o ativo com fundo elevado e sombra de segmento.

### Shell e navegação
Barra lateral em `surface` com borda direita; itens de 40px, texto tinta suave, peso 560; hover com fundo `ground`; página atual (`aria-current="page"`) com lavado de ação e texto azul. Seis rotas por hash: Carteiras (primeira e padrão), Visão geral, Gráfico, Operações, Risco, Glossário. Link "pular para o conteúdo" visível ao receber foco. No celular, barra inferior.

### Cabeçalho da execução e seletor
h1 em headline (ticker sem sufixos técnicos, mais a estratégia) com selo pílula "exemplo" quando os dados são sintéticos; abaixo, o nome do ativo e a categoria, e a sub-linha do trecho de teste em tinta suave. Dois seletores nativos lado a lado, "Ativo" (agrupado por categoria com optgroup) e "Estratégia" (só as do ativo), com borda `--line`, altura 40px e rótulo acima; ocupam a linha toda e quebram em telas estreitas, sem passar da largura.

### Faixa de métricas
Um painel sem padding com quatro itens divididos por linha de 1px; rótulo (label, tinta suave), valor (headline) em verde ou vermelho conforme sinal, detalhe com comparação ao buy and hold. O valor usa contagem animada.

### Painéis e veredito
Painel: superfície, borda, 8px, padding 1.5rem, sombra de painel. Veredito: título com ícone (verde aprovado, âmbar não aprovado), razões em lista, nota final separada por linha.

### Tabela ordenável
Cabeçalhos em botão com marca de ordenação, linhas com divisória e hover `ground`; na tela Carteiras as linhas são clicáveis (hover e selecionada em lavado de ação, nome como botão `aria-pressed`), colunas numéricas à direita. No celular o cabeçalho some, cada linha vira cartão com rótulo (`data-label`) antes do valor e um select de ordenação aparece.

### Detalhe da operação
Painel lateral: título, lista "por quê" com rótulo/valor, fatos em 2 colunas sob divisória; lista de operações com botões de 44px, selecionado com borda azul e lavado de ação (`aria-pressed`). Resultado em verde/vermelho/cinza com palavra junto.

### Dica de glossário
Termo com sublinhado pontilhado; tooltip elevado (`raised`, texto `ink`, 18rem, 8px) abaixo do termo.

### Estados
Vazio/erro/carregando em caixa com borda (erro com borda `loss-line`) ou variante plana; carregando com spinner de 18px (800ms, parado com movimento reduzido); texto com título em 650 e detalhe em label.

### Gráficos
Curva de capital em azul de ação contra benchmark tracejado (`benchmark`), legenda com amostras de linha. O gráfico de carteiras está em Carteiras. Velas: alta vazada (preenchimento da cor da superfície, borda e pavio verdes), baixa cheia vermelha. Marcadores: seta para cima abaixo da barra (compra), seta para baixo acima (saída); só o selecionado leva texto e tamanho maior. Linhas tracejadas de Entrada (azul) e Stop (vermelho) para a operação selecionada. Grade só horizontal em `--line`, sem borda de escala, rótulos 12px tinta suave, locale pt-BR, roda do mouse não escala. Cada gráfico tem tabela de dados equivalente em `<details>` e legenda OHLC ao passar o cursor.

### Aviso de simulação
Faixa fina no topo de toda tela (`role="note"`, lavado de ação, centralizada): "Simulação com dados históricos, sem envio de ordens. Não é recomendação de investimento." O rodapé credita Yahoo Finance (via yfinance), diz que os dados não são em tempo real e credita o TradingView.

### Movimento
Biblioteca `motion` importada só em `web/src/motion/index.tsx`. Easing de saída exponencial (0.16, 1, 0.3, 1). Revelação: sobe 14px e aparece em 500ms, com atraso por bloco. Contagem das métricas: 900ms. Gráfico se desenha da esquerda para a direita em 1100ms (clip-path). Marcador selecionado pulsa uma vez (tamanho 3 por 260ms, depois 2). Transições de estado: 120ms ease-out. Segurança: todo efeito tem temporizador de duração + 300ms que para a animação e fixa o estado final (conteúdo visível, número final). Com `prefers-reduced-motion: reduce` os hooks pulam a animação, o CSS zera animações e transições globalmente e o spinner para.

## Do's and Don'ts

### Do:
- **Do** usar apenas tokens de `web/src/tokens.css` para cor, espaço, raio, sombra e tamanho de texto; qualquer par texto/fundo novo entra em `contrast.test.ts` com mínimo 4.5:1.
- **Do** dar a cada marcador, valor e termo uma explicação em uma frase em português do Brasil.
- **Do** manter o aviso de simulação e o selo "exemplo" (dados sintéticos) em toda tela.
- **Do** combinar cor com forma, posição, palavra ou sinal para resultado e direção.
- **Do** dar a toda animação o temporizador de segurança e o ramo de movimento reduzido.
- **Do** manter alvos de toque de pelo menos 40px.

### Don't:
- **Don't** aninhar painéis com borda e sombra; use divisórias.
- **Don't** usar verde ou vermelho fora de resultado financeiro.
- **Don't** introduzir uma segunda família, display face ou monospace decorativa.
- **Don't** usar texto em cinza mais escuro que `ink-soft` sobre os fundos escuros.
- **Don't** esconder conteúdo atrás de animação sem a saída de segurança.
- **Don't** apresentar o painel como recomendação de investimento.

### Carteiras
Tela inicial (`#/carteiras`, `Carteiras` em primeiro na navegação). Comparativo ordenável (11 carteiras e 3 referências, selo "Referência"), seletor em chips de rádio (borda `line-strong`, selecionado em lavado de ação) (`fieldset`, foco visível), painel de detalhe com frase de leitura, métricas, gráfico, composição, regra e tabela ano a ano. O gráfico das carteiras usa escala logarítmica (com nota ao lado) e distingue as referências pela cor própria (`ref-cdi`, `ref-ibov`, `ref-sp`) e pelo formato da linha (tracejada, pontilhada, tracejada longa), não só pela cor; a legenda repete cada amostra; a carteira escolhida é a linha azul sólida e grossa. A tabela comparativa rola dentro do painel em telas médias e vira cartões no celular. A navegação do celular tem 6 colunas.

### Escolha de objetivo
No topo da tela Carteiras, um `fieldset` "Qual é o seu objetivo?" com 4 cartões de rádio (nome e frase; raio 8px, borda `line-strong`, hover com borda de ação), em grade `auto-fit` de no mínimo 13rem. O escolhido ganha borda e lavado de ação e o nome em azul; foco visível no cartão. Abaixo, um painel com o que esperar, a frase de leitura do exemplo, o aviso (fundo `loss-wash`, `role="note"`), botão discreto (`button-quiet`: sem fundo, borda `line-strong`) para ver o exemplo em detalhe, link para as estratégias por ativo (só no perfil de swing) e as metodologias parecidas como links de texto com os números da janela comum. Escolher um perfil também seleciona a carteira dele no detalhe. Os chips de carteira ficam em dois grupos: metodologias clássicas e exemplos por objetivo.

### Janela de comparação
Acima da tabela, dois rádios nativos em linha (alvo de 40px): "Mesmo período para todas" (padrão, justo) e "Histórico completo de cada uma", que acrescenta a coluna "Desde" e um aviso de que períodos diferentes não se comparam de forma justa. O gráfico da carteira escolhida começa na data dela e reescala as referências para começarem juntas em 100.
