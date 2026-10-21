# Layouts e linguagem visual — Rota da Madeira

Data: 2026-10-20
Complementa `docs/SPEC.md` (seção 11, Telas). Mockups de referência em `.superpowers/brainstorm/1059-1792542873/content/` (`mapa-ao-vivo-v2.html`, `outras-telas.html`, `app-motorista.html`).

## 1. Intenção

O painel é uma ferramenta de trabalho para **quem acompanha a frota**: fica aberto o dia todo, e a pessoa precisa bater o olho e saber se o dia está no ritmo e o que saiu do normal. Não é vitrine de portfólio, mesmo sendo um projeto de portfólio — a credibilidade vem de parecer uma ferramenta de operação de verdade.

Pedido do autor: **moderno, clean, tema claro e sem cara de IA**.

### Objetivos
- Leitura em segundos: meta do dia e exceções visíveis sem clicar.
- Uma linguagem única entre as 6 telas do painel e o app do motorista.
- Números estáveis enquanto atualizam em tempo real (sem "dançar").

### Fora do escopo
- Tema escuro (não será feito agora).
- Personalização de layout pelo usuário (arrastar painéis, widgets).

### Anti-objetivos (o que tornaria isso um fracasso mesmo funcionando)
- Visual de template gerado por IA: grade de cards iguais com a mesma sombra, gradientes decorativos, rótulos em CAIXA ALTA espaçada acima de cada título, fundo creme com serifa, fonte monoespaçada em rótulos pequenos, seta "→" nos botões, número gigante + rótulo pequeno repetido em cards.
- Cor como única forma de distinguir estado (precisa funcionar para daltônicos).
- Painel tão "limpo" que esconde o que está errado.

## 2. Linguagem visual

### Cores (tokens)
Definir como variáveis CSS e no tema do Tailwind. Nomes em português sem acento.

| token | hex | uso |
|---|---|---|
| `superficie` | `#FFFFFF` | fundo das telas |
| `fundo-sutil` | `#F6F7F9` | áreas secundárias, item ativo em listas |
| `trilho` | `#EEF1F4` | fundo do menu em pílula, trilhos de barras de progresso |
| `linha` | `#E4E7EB` | divisórias e bordas |
| `linha-fraca` | `#F0F2F4` | divisória entre linhas de tabela |
| `tinta` | `#101418` | texto principal, fábrica no mapa, marcador "esperado" da régua |
| `tinta-suave` | `#5F6B76` | texto secundário, cabeçalhos de tabela |
| `primaria` | `#0F5C73` | azul-petróleo: progresso, caminhão carregado, item ativo, links |
| `atencao` | `#B45309` | âmbar: atraso e alertas abertos |
| `atencao-fundo` | `#FEF3E2` | fundo de linha atrasada, selo, aviso offline |
| `online` | `#2E8B57` | indicador de conexão no app |
| `chuva` | `#1D4E89` | marcador de dia com chuva |

**Classes de risco (FMA)** — preenchimento de fazendas e células; nunca usadas como cor de texto:

| classe | hex |
|---|---|
| NULO | `#9CC5A1` |
| PEQUENO | `#C9DE8E` |
| MEDIO | `#F2D06B` |
| ALTO | `#E8A33D` |
| MUITO_ALTO | `#D9534F` |

**Estados do caminhão** — distinguidos por cor **e** forma:

| estado | rótulo na tela | marcador |
|---|---|---|
| CARREGANDO | Carregando | preenchido `#9CA8B1` |
| EM_TRANSITO_CARREGADO | Carregado | preenchido `primaria` |
| FILA_PATIO | Fila do pátio | preenchido `#5A7D8C` |
| PESAGEM | Pesagem | preenchido `#5A7D8C` |
| DESCARGA | Descarga | preenchido `#5A7D8C` |
| EM_TRANSITO_VAZIO | Vazio | contorno `primaria`, miolo branco |
| (qualquer, com alerta aberto) | rótulo do alerta | preenchido `atencao` |

Foco de calor no mapa: triângulo `#C8102E` com contorno branco (forma diferente das fazendas e dos caminhões).

### Tipografia
- Família única: **Instrument Sans** (Google Fonts, via `next/font`), pesos 400, 500, 600 e 700.
- Todo número usa `font-variant-numeric: tabular-nums`.
- Escala do painel (px): 11,5 legenda · 12,5 tabela · 13 corpo · 14 subtítulo · 17 número secundário · 24 número de faixa · 34 número principal (régua da meta).
- Escala do app do motorista (px): 12 status · 14 corpo · 18 botão · 30 informação principal.
- Números grandes: peso 600, `letter-spacing` de −0,02 a −0,03em.
- Texto sempre em caixa normal (sentence case), português do Brasil, sem caixa alta em rótulos.

### Forma e profundidade
- Estrutura feita com **linhas de 1 px**, não com cards sombreados. Sem sombras, exceto o painel de detalhe do caminhão (sombra leve, porque flutua sobre o mapa).
- Raios por hierarquia: 2–3 px em barras e células, 6–8 px em controles (menu, botões do painel), 999 px em filtros em pílula, 12–14 px nos botões do app do motorista.
- Sem gradientes. Movimento só em resposta a ação (abrir painel, trocar filtro) e na posição dos caminhões; respeitar `prefers-reduced-motion`.

### Escrita
- Rótulos pelo que o usuário entende ("Fila do pátio", "Esperando", "Ver no mapa"), não pelo nome técnico do enum.
- Alertas descrevem o fato: "TLG4C17 parado há 22 min", "Foco a 2,1 km da rota da Três Irmãos".
- Vazios orientam: "Nenhum alerta aberto agora."

## 3. Estrutura comum do painel

```
┌──────────────────────────────────────────────────────────────────┐
│ Rota da Madeira  [Ao vivo|Pátio|Indicadores|Alertas|Risco|Replay] │  Dados simulados │  50 px
├──────────────────────────────────────────────────────────────────┤
│ faixa de números / filtros da tela                                │
├──────────────────────────────────────────────────────────────────┤
│ conteúdo (grade de 2 colunas separadas por linha de 1 px)         │
└──────────────────────────────────────────────────────────────────┘
```

- **Barra do topo:** nome em 700; menu segmentado em pílula (trilho `trilho`, item ativo branco com borda `linha` e peso 600); selo "Dados simulados" à direita em `atencao` sobre `atencao-fundo`. A partir da Fase 3 o selo passa a ser "Áreas de eucalipto: MapBiomas (2024). Frota e viagens: dados simulados."
- Conteúdo alinhado à esquerda; números alinhados à direita nas tabelas.
- Telas de painel ocupam a largura toda (sem coluna centralizada estreita).
- **Responsivo:** abaixo de 1024 px a grade de 2 colunas vira uma coluna (mapa em cima, tabela embaixo); abaixo de 640 px o menu rola na horizontal. O painel é pensado para desktop; no celular precisa funcionar, mas não precisa ser ótimo.

## 4. Telas do painel

### 4.1 Ao vivo (mapa) — tela principal
```
┌ topo ──────────────────────────────────────────────────────────┐
│ 2.380 t  entregues de 4.000 t      −95 t   4h12   38 min        │
│ ███████████████████████▌|░░░░░░░░░░░░░░  (| = esperado agora)    │
│ 00h      06h      12h      18h      24h                         │
├──────────────────────────────────┬─────────────────────────────┤
│ mapa                             │ Placa  Estado  Carga  ETA    │
│ fazendas por risco, rotas,       │ (com alerta primeiro,        │
│ fábrica, caminhões, focos        │  linha em atencao-fundo)     │
└──────────────────────────────────┴─────────────────────────────┘
        ~57%                                ~43%
```
- **Régua da meta** é o elemento de destaque do produto: barra `primaria` com toneladas entregues no dia; marcador vertical `tinta` na posição esperada para o horário atual (meta × fração do dia decorrida — cálculo simples, ver seção 7); escala de horas embaixo. Ao lado, três números: diferença contra o esperado, ciclo médio e espera média no pátio.
- **Mapa:** MapLibre com mapa base claro e dessaturado; atribuição do OpenStreetMap sempre visível. Fazendas como polígono preenchido pela classe de risco do dia (nas Fases 1–2, sem risco calculado: preenchimento neutro `linha`). Rotas em linha fina cinza. Fábrica em `tinta`. Legenda compacta no canto inferior esquerdo.
- **Tabela da frota:** 20 linhas, ordenada por: com alerta aberto → em trânsito por ETA → resto. Linha com alerta usa fundo `atencao-fundo`.
- **Clique no caminhão** (no mapa ou na tabela): painel de detalhe ocupa a coluna da tabela, com placa, tipo, motorista, estado, carga, ETA, fazenda de origem e alertas abertos; botão "Voltar para a frota". O caminhão fica destacado no mapa.
- **Conexão:** quando o WebSocket cai, um aviso discreto no topo ("Reconectando…") e os dados ficam marcados como desatualizados; some ao reconectar.

### 4.2 Pátio
- Faixa de números: na fila, vagas de descarga ocupadas (de 3), espera média hoje, chegando nas próximas 2 h.
- Esquerda: "Fila agora", tabela em ordem de chegada (posição, placa, chegou, esperando). A numeração aqui é legítima porque é uma ordem.
- Direita: "Chegadas previstas", linha do tempo horizontal de 2 h a partir de agora, com um traço vertical `primaria` e a placa por caminhão previsto.

### 4.3 Indicadores
- Filtro em pílulas: Hoje, 7 dias, 30 dias (mapeia para `inicio`/`fim` de `/indicadores`).
- Faixa de números: toneladas (de meta × dias), viagens, ciclo médio, fila média, % da frota em uso.
- Esquerda: barras de toneladas por hora, com linha tracejada `tinta` no ritmo necessário (meta ÷ 24).
- Direita: barra empilhada única do uso da frota agora por grupo de estado, com legenda e percentuais.

### 4.4 Alertas
- Filtros em pílulas: status (Abertos com contagem, Fechados) e tipo (Todos, Logística, Fogo).
- Tabela: hora, tipo (peso 600, `atencao` se aberto), caminhão ou fazenda, o que aconteceu, status, "Ver no mapa". Fechados em `tinta-suave`.
- "Ver no mapa" leva à tela Ao vivo com o caminhão ou a fazenda selecionados (parâmetro na URL).

### 4.5 Risco (Fase 3)
- Grade: uma linha por fazenda, uma coluna por dia dos últimos 30; célula de ~14×16 px preenchida pela classe; ponto `chuva` nas células de dia com chuva > 2,4 mm (ou seja, que reduziu a FMA); última coluna com o valor da FMA de hoje.
- Hover/foco na célula mostra data, FMA, classe, chuva e UR das 13h.
- Legenda das classes e do ponto de chuva embaixo.

### 4.6 Replay
- Cabeçalho: placa e descrição da viagem ("viagem de 19/10, Três Irmãos até a fábrica, 55 t").
- Mapa com a rota prevista tracejada e o trajeto percorrido em `primaria` até o cursor.
- Linha do tempo embaixo: trilho com cursor arrastável e os eventos da viagem (`eventos_viagem`) como pontos com nome e horário. Arrastar move o caminhão no mapa.

## 5. App do motorista (PWA)

O motorista deixa o app aberto o tempo todo, como um GPS. Cada tela responde a uma pergunta: **o que fazer agora**.

```
┌─────────────────────┐
│ 14:31      ● Online │
│ TLG2A09, rodotrem   │
│ Indo para carregar  │
│ Fazenda Três Irmãos │  ← 30 px
│ 38 km, chega ~15:10 │
│ ████████░░░░░░░░░░  │
│ ▬ ▬ ▬ ▬ ▬ ▬ (ciclo) │
│                     │
│ [ Cheguei na fazenda ] ← botão principal, muda por etapa
│ [ Registrar ocorrência ]
└─────────────────────┘
```

- Topo: hora e estado da conexão (`online` / "Sem sinal" em `atencao`).
- Informação principal grande: destino (em trânsito) ou tempo decorrido (carregando).
- Barra de progresso da viagem e as 6 etapas do ciclo como tracinhos (feitas, atual, por fazer).
- Botão principal de altura ≥ 60 px, sempre no rodapé, com a próxima ação: "Cheguei na fazenda" (check-in de início de carregamento), "Terminei de carregar" (fim). Nas etapas de pátio não há ação do motorista: o botão some e aparece o estado ("Na fila do pátio, posição 2").
- **Sem sinal:** aviso em `atencao-fundo` dizendo exatamente o que está guardado no celular e que será enviado ao reconectar. Ao reconectar: "Check-in das 15:12 enviado."
- **Ocorrência:** 6 opções grandes (Pneu, Mecânico, Estrada bloqueada, Fumaça ou fogo, Acidente, Outro), foto opcional pela câmera, "Enviar ocorrência" e "Cancelar". "Outro" abre um campo de texto curto.
- Mesmos tokens do painel; escala tipográfica própria (seção 2).

## 6. Decisões do autor
- Direção "B" (meta do dia no topo, mapa + tabela da frota) com o menu em pílula da direção "C".
- Tema claro.
- Estrutura das telas Pátio, Indicadores, Alertas, Risco e Replay como nos mockups.
- App do motorista aberto o tempo todo, uma ação principal por etapa.

## 7. Decisões tomadas por mim (Claude) — revisar
- Paleta, fonte Instrument Sans e escalas acima.
- Clique no caminhão abre painel na coluna da tabela, não balão flutuante.
- Mapa base: estilo "positron" do OpenFreeMap (gratuito, sem chave, dados OSM). Alternativa equivalente é aceitável se for clara, sem chave e com atribuição OSM.
- Posição "esperada" na régua: meta × (horas decorridas ÷ 24), linear. Se o simulador tiver horário de operação, trocar pela fração do horário de operação.
- Nas Fases 1–2 as fazendas aparecem sem cor de risco (cinza neutro) e a tela Risco não aparece no menu até a Fase 3.
- Replay aparece no menu a partir da Fase 2; na Fase 1 o menu mostra só as telas já implementadas.

## 8. Deixado para quem constrói
- Ícones (se usar, uma biblioteca de traço fino e só onde ajudam, como na câmera do app).
- Estrutura de componentes React e nomes de arquivos.
- Detalhes de animação dos caminhões entre leituras de telemetria (interpolar suavemente é desejável).
- Estados de carregamento: preferir esqueleto com a forma do conteúdo a spinners.
