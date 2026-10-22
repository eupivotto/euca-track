# Fase 3B — Risco de incêndio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calcular a Fórmula de Monte Alegre por área com clima real do Open-Meteo, importar focos de calor reais do INPE, abrir alertas de foco perto das áreas e das rotas, e mostrar risco e focos no mapa e na tela Risco.

**Architecture:** Um serviço novo no compose, `rotinas` (mesma imagem da API, `python -m app.rotinas`, APScheduler), é o único que fala com Open-Meteo e INPE: grava `clima_diario`, recalcula `risco_diario`, grava `focos_calor` e abre/fecha os alertas de foco perto de fazenda. O alerta de foco perto da rota nasce no caminho da telemetria (vigilância), como os alertas de logística, e por isso sai no WebSocket. A API só lê do banco. O front consulta focos, risco e alertas com atualização periódica.

**Tech Stack:** APScheduler 3, httpx, PostGIS, FastAPI; Next.js, TanStack Query, MapLibre.

**Spec:** `docs/SPEC.md` (seções 6, 7, 8, 9, 10, 11, 12 — Fase 3) e `docs/superpowers/specs/2026-10-20-layouts-design.md` (cores das classes, foco como triângulo `#C8102E`, tela 4.5 Risco, alertas com filtro Logística/Fogo).

## Global Constraints

- FMA (SPEC 7): `parcela = 100 / H` (H = UR das 13h, America/Campo_Grande). Chuva ≤ 2,4: `ontem + parcela`; 2,5–4,9: `ontem × 0,7 + parcela`; 5,0–9,9: `ontem × 0,4 + parcela`; 10,0–12,9: `ontem × 0,2 + parcela`; > 12,9: `0` (recomeça no dia seguinte). Chuva arredondada a uma casa (meio para cima) antes de escolher a faixa.
- Classes: NULO 0,0–1,0; PEQUENO 1,1–3,0; MEDIO 3,1–8,0; ALTO 8,1–20,0; MUITO_ALTO > 20,0 — limites configuráveis. A FMA é arredondada a uma casa (meio para cima) antes de classificar.
- Clima: Open-Meteo por coordenada (`centro`) da fazenda; horárias `relative_humidity_2m`, `precipitation`, `wind_speed_10m`, `wind_direction_10m`; timezone `America/Campo_Grande`. Backfill de 60 dias pela API de histórico (`archive-api.open-meteo.com/v1/archive`, vai até ontem) na primeira execução.
- Focos: arquivo diário do INPE `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_AAAAMMDD.csv` (colunas `id,lat,lon,data_hora_gmt,satelite,municipio,estado,…`; hora em UTC; atualizado ao longo do dia). Recorte lat −21,6 a −19,8, lon −52,9 a −51,4 (`regiao_*` da config). Sem duplicar: chave (lat, lon, data e hora, satélite). Rotina a cada 30 min.
- Alertas de foco: `FOCO_PROXIMO_FAZENDA` (foco das últimas 24 h a menos de 5 km do polígono) e `FOCO_PROXIMO_ROTA` (foco das últimas 24 h a menos de 3 km da rota de uma viagem em andamento). Mensagem com distância, horário da detecção e se o vento das 13h sopra do foco para a fazenda (diferença de ângulo < 45°). Mesmo tipo e mesmo caminhão (ou fazenda) não repete enquanto aberto.
- Nunca chamar Open-Meteo ou INPE dentro de um request; amostras reais em `api/tests/fixtures/` antes dos parsers; parâmetros em `api/app/config.py`.
- Cores das classes (layout): NULO `#9CC5A1`, PEQUENO `#C9DE8E`, MEDIO `#F2D06B`, ALTO `#E8A33D`, MUITO_ALTO `#D9534F`, nunca como cor de texto; ponto de chuva `#1D4E89`; foco: triângulo `#C8102E` com contorno branco.
- Commits `tipo: descrição` em português; código sem acento.

## Decisões de desenho (para o revisor)

- **Dois relógios.** Focos e clima são reais; a frota roda no relógio simulado, que se adianta 10× (já está horas à frente do real). Janelas de focos ("últimas 24 h") usam o relógio **real**. `aberto_em` de todo alerta usa o relógio **simulado** (`agora_simulado`), para a lista de alertas continuar em ordem; o horário real da detecção vai na mensagem.
- **Risco "de hoje"** é a data real em America/Campo_Grande.
- **Rotina de clima a cada 3 h**, não 1×/dia: a linha de hoje vem da previsão e melhora ao longo do dia; são 8 requisições.
- **Focos:** baixa o arquivo de hoje (UTC) a cada 30 min; nas 2 primeiras horas do dia UTC baixa também o de ontem (fecha o dia); na primeira execução, ontem e hoje. Chave de unicidade numa coluna `chave` texto (`lat|lon|AAAA-MM-DDTHH:MM|satelite`), porque igualdade de geometria no índice não é confiável.
- **Vento no alerta de rota:** vento das 13h da fazenda da viagem, comparado ao rumo do ponto da rota mais perto do foco até o foco.
- **"Viagem em andamento"** para o alerta de rota: caminhão em trânsito (carregado ou vazio) na rota.
- **Sem WebSocket a partir das rotinas** (outro processo): focos, risco e alertas são relidos a cada 60 s no front.

## Review Focus

1. Open-Meteo devolve `null` na UR das 13h ou na chuva de um dia (lacuna do modelo): o dia fica sem FMA e a série continua do último dia válido, sem `ZeroDivisionError` — teste na Task 1 e na Task 3.
2. UR das 13h igual a 0 (dado ruim): não divide por zero; trata como dia sem dado — teste na Task 1.
3. CSV do INPE vazio (só cabeçalho), com linha quebrada ou com BOM: importa o resto e não derruba a rotina — teste na Task 4.
4. Uma fonte externa fora do ar: a rotina registra e tenta na próxima vez, sem matar o processo do agendador — teste na Task 6.
5. Ângulo do vento perto de 0°/360° (ex.: vento 350°, rumo 20°): diferença de 30°, conta como a favor — teste na Task 2.

---

### Task 1: FMA e classes (regra pura)

**Files:** Create `api/app/fma.py`, `api/tests/test_fma.py`; Modify `api/app/config.py`, `api/tests/test_config.py`

**Interfaces — Produces:**
- config: `fma_limite_nulo=1.0`, `fma_limite_pequeno=3.0`, `fma_limite_medio=8.0`, `fma_limite_alto=20.0`.
- `class ClasseRisco(StrEnum)`: NULO, PEQUENO, MEDIO, ALTO, MUITO_ALTO.
- `@dataclass DiaClima(data: date, ur_13h: float | None, chuva_mm: float | None)`
- `fma_do_dia(fma_ontem: float, ur_13h: float, chuva_mm: float) -> float`
- `classificar(fma: float, settings: Settings) -> ClasseRisco`
- `serie_fma(dias: list[DiaClima], settings) -> list[tuple[date, float, ClasseRisco]]` — em ordem de data, primeiro dia com `fma_ontem = 0`; dia sem UR, com UR ≤ 0 ou sem chuva fica fora da saída e não mexe no acumulado.

- [ ] **Step 1: Testes que falham** (`test_fma.py`), com H = 50 (parcela 2,0) e FMA de ontem = 10:
  - chuva 0 → 12,0; 2,4 → 12,0; 2,5 → 9,0; 4,9 → 9,0; 5,0 → 6,0; 9,9 → 6,0; 10,0 → 4,0; 12,9 → 4,0; 13,0 → 0.
  - arredondamento da chuva: 2,45 → faixa 2,5–4,9 (9,0); 2,44 → faixa ≤ 2,4 (12,0); 12,95 → zera.
  - série: `[(d1, 50, 0), (d2, 50, 20), (d3, 50, 0)]` → 2,0; 0,0; 2,0 (zera e recomeça no dia seguinte).
  - série com um dia `ur_13h=None` no meio: o dia some da saída e o seguinte soma sobre o anterior válido; `ur_13h=0` idem.
  - classes nos limites: 0 e 1,0 → NULO; 1,1 e 3,0 → PEQUENO; 3,1 e 8,0 → MEDIO; 8,1 e 20,0 → ALTO; 20,1 → MUITO_ALTO; 1,04 → NULO; 1,05 → PEQUENO.
  - limites vindos da config: com `fma_limite_nulo=2.0`, 1,5 → NULO.
  - config: os quatro limites padrão.
- [ ] **Step 2:** `docker compose exec api pytest tests/test_fma.py tests/test_config.py -q` — Expected: FAIL (módulo ausente).
- [ ] **Step 3:** Implementar (arredondamento com `Decimal` e `ROUND_HALF_UP`).
- [ ] **Step 4:** mesmo comando — Expected: PASS.
- [ ] **Step 5:** Commit `feat: fórmula de Monte Alegre e classes de risco`.

### Task 2: Vento a favor e distância de foco (regra pura)

**Files:** Create `api/app/focos.py` (parte pura), `api/tests/test_focos_regras.py`

**Interfaces — Produces:**
- `rumo_graus(de: tuple[float, float], para: tuple[float, float]) -> float` — azimute 0–360 (0 = norte, 90 = leste), pontos (lon, lat).
- `vento_a_favor(vento_dir: float | None, rumo_alvo_para_foco: float, angulo_max: float) -> bool | None` — `vento_dir` é a direção de onde o vento vem (meteorológica); a favor quando a menor diferença angular entre `vento_dir` e o rumo do alvo até o foco é < `angulo_max`; `None` sem dado de vento.
- `texto_foco(distancia_m: float, detectado_em: datetime, a_favor: bool | None, fuso: ZoneInfo) -> str` — ex.: `"Foco a 2,1 km, detectado às 14h32; vento das 13h sopra do foco para cá"` / `"…; vento das 13h não sopra do foco para cá"` / sem vento: só distância e horário.

- [ ] **Step 1: Testes que falham:** rumo para norte ≈ 0, leste ≈ 90, sul ≈ 180; foco ao norte com vento de 0° → a favor; foco ao sul com vento de 0° → contra; vento 350° e rumo 20° → a favor (30°); diferença exatamente 45° → contra; `vento_dir=None` → `None`; `texto_foco` com 2140 m → "2,1 km" e hora local "14h32" (detecção 18:32 UTC).
- [ ] **Step 2:** `docker compose exec api pytest tests/test_focos_regras.py -q` — Expected: FAIL.
- [ ] **Step 3:** Implementar; config `foco_vento_angulo_max=45`, `foco_fazenda_km=5`, `foco_rota_km=3`, `foco_janela_h=24`.
- [ ] **Step 4:** Expected: PASS. **Step 5:** Commit `feat: vento a favor e texto do alerta de foco`.

### Task 3: Tabelas e importação do clima (Open-Meteo)

**Files:** Create `api/alembic/versions/0004_risco.py`, `api/app/clima.py`, `api/tests/test_clima.py`, `api/tests/fixtures/open_meteo_forecast.json`, `api/tests/fixtures/open_meteo_archive.json`; Modify `api/app/modelos.py`, `api/app/config.py`, `api/tests/test_migracao.py`

**Interfaces — Produces:**
- Tabelas: `clima_diario(fazenda_id, data, ur_13h, chuva_mm, vento_kmh, vento_dir)` único (fazenda_id, data); `risco_diario(fazenda_id, data, fma, classe)` único (fazenda_id, data); `focos_calor(geom POINT 4326, satelite, detectado_em timestamptz, municipio, chave único)`, índice em `detectado_em` e GIST em `geom`. Modelos `ClimaDiario`, `RiscoDiario`, `FocoCalor`.
- config: `open_meteo_url="https://api.open-meteo.com/v1/forecast"`, `open_meteo_historico_url="https://archive-api.open-meteo.com/v1/archive"`, `clima_backfill_dias=60`.
- `ler_open_meteo(dados: dict) -> list[ClimaDia]` — `ClimaDia(data, ur_13h, chuva_mm, vento_kmh, vento_dir)`: UR, vento e direção da hora `T13:00`; chuva = soma das horas do dia (`None` se todas nulas).
- `buscar_clima(cliente, settings, lon, lat, inicio: date, fim: date, historico: bool) -> list[ClimaDia]`.
- `importar_clima(sessao, settings, cliente, hoje: date) -> list[str]` — para cada fazenda: sem nenhuma linha → histórico de `hoje − 60` até ontem; sempre → previsão com `past_days=3`, `forecast_days=1`; grava com upsert; depois recalcula `risco_diario` da fazenda com `serie_fma` sobre toda a série (apaga e regrava). Erro de uma fazenda vira aviso, as outras seguem. 1 s entre requisições.

- [ ] **Step 1: Amostras reais:** salvar a resposta da previsão (`past_days=3&forecast_days=1`) e do histórico (5 dias) para o centro da Área de eucalipto 01, com as 4 variáveis horárias e o timezone.
- [ ] **Step 2: Testes que falham:**
  - `test_ler_open_meteo_previsao` / `_historico` contra as amostras: um `ClimaDia` por data; UR das 13h igual ao valor da hora `T13:00` do JSON; chuva igual à soma do dia.
  - `test_dia_com_valores_nulos` — JSON com UR das 13h `null` → `ur_13h=None`.
  - `test_importar_faz_backfill_so_na_primeira_vez` — transporte falso: primeira execução chama `/archive` 8 vezes e `/forecast` 8 vezes; segunda, só `/forecast`.
  - `test_importar_grava_clima_e_risco` — depois de importar, `risco_diario` tem uma linha por dia com UR e chuva, com a FMA de `serie_fma`.
  - `test_upsert_nao_duplica` — importar duas vezes a mesma data mantém uma linha, com o valor novo.
  - `test_falha_de_uma_fazenda_vira_aviso` — 500 para uma coordenada: aviso com o nome; as outras gravadas.
  - migração: as três tabelas existem.
- [ ] **Step 3:** `docker compose exec api pytest tests/test_clima.py tests/test_migracao.py -q` — Expected: FAIL.
- [ ] **Step 4:** Implementar (migração, modelos, `clima.py`). **Step 5:** Expected: PASS.
- [ ] **Step 6:** Commit `feat: clima diário do Open-Meteo e recálculo da FMA`.

### Task 4: Importação dos focos do INPE

**Files:** Modify `api/app/focos.py`; Create `api/tests/test_focos_importar.py`, `api/tests/fixtures/focos_diario_br_amostra.csv`; Modify `api/app/config.py`

**Interfaces — Produces:**
- config: `inpe_focos_url="https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_{data}.csv"`.
- `@dataclass FocoLido(lat, lon, detectado_em: datetime (UTC), satelite, municipio)`; `ler_csv_focos(texto: str, settings) -> list[FocoLido]` — só dentro do recorte; ignora linhas quebradas; tolera BOM.
- `chave_foco(f: FocoLido) -> str`.
- `arquivos_do_momento(agora_utc: datetime, primeira_vez: bool) -> list[date]` — hoje; e ontem se `primeira_vez` ou hora UTC < 2.
- `importar_focos(sessao, settings, cliente, agora_utc) -> tuple[int, list[str]]` — baixa, lê, grava com `ON CONFLICT (chave) DO NOTHING`; devolve quantos entraram e avisos (404 do arquivo de hoje logo após a virada não é erro: aviso).

- [ ] **Step 1: Amostra real:** do arquivo diário real, guardar cabeçalho + todas as linhas dentro do recorte + ~20 de fora (inclusive MS fora do recorte), com acentos preservados.
- [ ] **Step 2: Testes que falham:** só focos do recorte; `detectado_em` em UTC (`2026-10-21 17:32:00` → 17:32Z); município com acento; CSV só com cabeçalho → `[]`; linha com coluna faltando ignorada; BOM no início tolerado; `arquivos_do_momento` (01:00Z → ontem e hoje; 05:00Z → só hoje; primeira vez → ontem e hoje); importar duas vezes a mesma amostra não duplica; 404 vira aviso.
- [ ] **Step 3:** `docker compose exec api pytest tests/test_focos_importar.py -q` — Expected: FAIL. **Step 4:** Implementar. **Step 5:** PASS.
- [ ] **Step 6:** Commit `feat: importação dos focos de calor do INPE`.

### Task 5: Alertas de foco

**Files:** Modify `api/app/alertas.py`, `api/app/vigilancia.py`, `api/app/focos.py`; Create `api/tests/test_alertas_foco.py`

**Interfaces — Produces:**
- `TipoAlerta.FOCO_PROXIMO_FAZENDA`, `TipoAlerta.FOCO_PROXIMO_ROTA`.
- `Situacao.foco_rota: FocoPerto | None = None` com `@dataclass FocoPerto(foco_id, distancia_m, detectado_em, a_favor: bool | None)`; `alertas_ativos` liga `FOCO_PROXIMO_ROTA` só em trânsito com `foco_rota`; `mensagem` usa `texto_foco` + `" da rota da {fazenda}"`.
- `foco_perto_da_rota(sessao, rota_geom, fazenda_id, agora_real, settings) -> FocoPerto | None` — foco mais perto entre os das últimas `foco_janela_h` horas a menos de `foco_rota_km` (PostGIS `geography`); vento = `clima_diario` de hoje (real) da fazenda.
- `montar_situacao` preenche `foco_rota`; o `foco_id` vai para o alerta aberto.
- `atualizar_alertas_fazenda(sessao, settings, agora_real, agora_sim) -> list[Alerta]` — por fazenda, foco mais perto do polígono nas últimas 24 h a menos de 5 km: abre `FOCO_PROXIMO_FAZENDA` se não houver aberto para a fazenda; fecha quando não houver mais; mensagem `texto_foco` com vento da fazenda; `aberto_em`/`fechado_em` = `agora_sim`.

- [ ] **Step 1: Testes que falham:** regra pura (em trânsito com foco → ativo; carregando com foco → não); no banco: foco a 2 km da rota em uso abre `FOCO_PROXIMO_ROTA` com "2,0 km" e `foco_id`; foco a 4 km não abre; foco de 30 h atrás não abre; não repete enquanto aberto; fecha ao sair do trânsito; fazenda: foco a 3 km do polígono abre um alerta com `fazenda_id`; segundo foco perto não abre outro; sem focos na janela fecha; mensagem com vento a favor quando o `clima_diario` de hoje tem vento vindo do foco.
- [ ] **Step 2:** `docker compose exec api pytest tests/test_alertas_foco.py tests/test_alertas.py tests/test_vigilancia.py -q` — Expected: FAIL nos novos. **Step 3:** Implementar. **Step 4:** PASS (antigos inclusive).
- [ ] **Step 5:** Commit `feat: alertas de foco perto da fazenda e da rota`.

### Task 6: Serviço de rotinas

**Files:** Create `api/app/rotinas.py`, `api/tests/test_rotinas.py`; Modify `api/pyproject.toml` (`apscheduler>=3.10,<4`), `docker-compose.yml`, `api/app/config.py`

**Interfaces — Produces:**
- config: `rotina_clima_h=3`, `rotina_focos_min=30`.
- `rodar_clima(fabrica_sessao, settings, cliente, hoje)` e `rodar_focos(fabrica_sessao, settings, cliente, agora_utc)` — abrem sessão, chamam o importador (e `atualizar_alertas_fazenda` depois dos focos), fazem commit, imprimem avisos com `flush=True`; **qualquer exceção é capturada e impressa**, nunca sobe.
- `python -m app.rotinas`: roda as duas na partida e agenda (`BlockingScheduler`, `max_instances=1`, `coalesce=True`).
- Compose: serviço `rotinas` (imagem da API, `restart: unless-stopped`, depende de `preparo` concluído).

- [ ] **Step 1: Testes que falham:** `rodar_focos` com transporte que levanta erro não levanta e imprime aviso; `rodar_clima` idem; `rodar_focos` com a amostra grava focos e abre alerta de fazenda quando há foco perto.
- [ ] **Step 2:** `docker compose exec api pytest tests/test_rotinas.py -q` — FAIL. **Step 3:** Implementar. **Step 4:** PASS.
- [ ] **Step 5:** Subir: `docker compose up -d --build rotinas` e `docker compose logs rotinas` — Expected: backfill de 60 dias para 8 áreas e focos importados, sem traceback.
- [ ] **Step 6:** Commit `feat: serviço de rotinas para clima e focos`.

### Task 7: API de focos e risco

**Files:** Create `api/app/rotas_http/risco.py`, `api/tests/test_rotas_risco.py`; Modify `api/app/rotas_http/mapa.py`, `api/app/rotas_http/alertas.py` (filtro por tipo aceita os novos), `api/app/main.py`

**Interfaces — Produces:**
- `GET /focos?horas=24` (1–72) → GeoJSON de pontos com `id`, `detectado_em`, `satelite`, `municipio`; janela pelo relógio real.
- `GET /risco/fazendas?data=AAAA-MM-DD` (padrão: hoje real) → `[{fazenda_id, nome, data, fma, classe}]` (sem linha: `fma` e `classe` `null`).
- `GET /risco/historico?dias=30` (1–90) → `{"datas": [...], "fazendas": [{fazenda_id, nome, dias: [{data, fma, classe, chuva_mm, ur_13h} | null]}]}` alinhado às datas.
- `GET /fazendas`: cada fazenda ganha `classe` e `fma` de hoje (ou do último dia disponível até hoje).

- [ ] **Step 1: Testes que falham:** janela de 24 h exclui foco de 30 h; `horas=0` → 422; risco de uma data sem cálculo → `null`; histórico alinhado com buracos `null`; `/fazendas` com `classe`.
- [ ] **Step 2–4:** RED, implementar, GREEN (`docker compose exec api pytest tests/test_rotas_risco.py -q`).
- [ ] **Step 5:** Commit `feat: rotas de focos e risco`.

### Task 8: Mapa com risco e focos, filtro Fogo nos alertas

**Files:** Modify `web/lib/tipos.ts`, `web/lib/api.ts`, `web/components/MapaAoVivo.tsx` (+ teste), `web/app/page.tsx`, `web/app/alertas/page.tsx`, `web/components/TabelaAlertas.tsx` (+ teste); Create `web/lib/risco.ts` (+ teste)

**Interfaces — Produces:**
- `COR_CLASSE: Record<ClasseRisco, string>`, `ROTULO_CLASSE` ("Nulo", "Pequeno", "Médio", "Alto", "Muito alto"), `TIPOS_FOGO = ["FOCO_PROXIMO_FAZENDA", "FOCO_PROXIMO_ROTA"]`, `ehAlertaFogo(tipo)`.
- Mapa: preenchimento das áreas por `classe` (sem classe: neutro); camada de focos com triângulo `#C8102E` de contorno branco; pílulas 24 h / 48 h; legenda com classes e foco; clique na área mostra nome, FMA e classe.
- Alertas: pílulas de tipo Todos / Logística / Fogo; "Ver no mapa" de alerta de fazenda leva a `/?fazenda=<id>`, que enquadra a área.
- Consultas de focos, fazendas e alertas com `refetchInterval: 60_000`.

- [ ] **Step 1: Testes que falham:** `risco.test.ts` (cores e rótulos das 5 classes, `ehAlertaFogo`); `TabelaAlertas` com filtro Fogo mostra só os de foco e Logística esconde-os; alerta de fazenda tem link `/?fazenda=3`; legenda do mapa lista as 5 classes e "Foco de calor".
- [ ] **Step 2–4:** RED, implementar, GREEN (`cd web && npm test`, `npx tsc --noEmit`, `npm run lint`).
- [ ] **Step 5:** Commit `feat: risco e focos no mapa e filtro de fogo nos alertas`.

### Task 9: Tela Risco

**Files:** Create `web/app/risco/page.tsx`, `web/components/GradeRisco.tsx` (+ teste); Modify `web/lib/telas.ts`, `web/lib/api.ts`, `web/components/BarraTopo.test.tsx`

**Interfaces — Produces:** Grade como no layout 4.5: uma linha por área, uma coluna por dia dos últimos 30, célula ~14×16 px pela cor da classe, ponto `#1D4E89` em dia com chuva > 2,4 mm, última coluna com a FMA de hoje; foco/hover na célula mostra data, FMA, classe, chuva e UR das 13h; legenda das classes e do ponto de chuva; dia sem dado em cinza claro. Rolagem horizontal dentro da grade no celular (a página não rola de lado). Menu: Ao vivo, Pátio, Indicadores, Alertas, Risco, Replay.

- [ ] **Step 1: Testes que falham:** grade com 2 áreas × 3 dias mostra 6 células com `aria-label` "21/10: FMA 4,2, Médio, chuva 3,0 mm, UR 13h 48%"; ponto de chuva só onde chuva > 2,4; dia `null` com rótulo "sem dado"; última coluna com a FMA de hoje; menu inclui Risco antes de Replay.
- [ ] **Step 2–4:** RED, implementar, GREEN.
- [ ] **Step 5:** Commit `feat: tela de risco com a FMA dos últimos 30 dias`.

### Task 10: Conferência, documentação

**Files:** Modify `README.md`, `CLAUDE.md`

- [ ] **Step 1:** `docker compose up -d --build`; conferir no navegador (desktop e celular): áreas coloridas pelo risco, focos reais na região (se houver no dia), tela Risco com 60 dias de histórico (30 visíveis), filtro Fogo. Se não houver foco real perto de nenhuma área, inserir um foco de teste no banco de desenvolvimento perto de uma área e de uma rota, conferir os dois alertas e apagá-lo.
- [ ] **Step 2:** README: fontes (Open-Meteo, INPE Programa Queimadas, Soares 1972 / IPEF), serviço `rotinas`, os dois relógios. CLAUDE.md: comando para rodar as rotinas uma vez.
- [ ] **Step 3:** Suítes da API, simulador e web — Expected: verdes.
- [ ] **Step 4:** Commit `docs: risco de incêndio no README`.
