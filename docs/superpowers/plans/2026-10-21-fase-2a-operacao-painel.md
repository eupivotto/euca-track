# Fase 2A — Operação no painel: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao painel as telas de operação da Fase 2 — alertas de logística com ETA, pátio, indicadores e replay — sobre a base da Fase 1. O app do motorista (PWA) fica no plano 2B.

**Architecture:** A cada leitura de telemetria a API atualiza o trecho do caminhão (início, chegada prevista, ETA), monta a situação dele e passa por regras puras de alerta; o que abriu ou fechou é gravado em `alertas` e difundido no WebSocket junto com o caminhão. Pátio, indicadores e replay são leituras do banco servidas por endpoints novos. O simulador ganha velocidade por trecho e a parada não prevista, para que os alertas aconteçam na demonstração.

**Tech Stack:** o mesmo da Fase 1 (FastAPI, SQLAlchemy 2, GeoAlchemy2, Shapely 2, Alembic, pytest; Next.js 15, React 19, Tailwind 4, MapLibre GL 5, TanStack Query 5, Vitest).

**Spec:** `docs/SPEC.md` (seções 4, 6, 9, 10, 11, 12 — Fase 2) e `docs/superpowers/specs/2026-10-20-layouts-design.md` (seções 4.1 a 4.4 e 4.6).

## Global Constraints

- TDD: teste antes da implementação para toda regra de negócio (ETA, cada alerta, não repetição); rodar os testes ao fim de cada passo.
- Código, tabelas e variáveis em português sem acento; comentários em português.
- Commits pequenos em português, formato `tipo: descrição`, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` e `Claude-Session: https://claude.ai/code/session_01B1xyRLKx7XXVRhia1kxXGX`.
- Limites de alerta e parâmetros novos de simulação ficam em `api/app/config.py`, com os padrões da seção 6 do SPEC e sobrescrita por variável de ambiente. O simulador lê os seus pela API (`/simulacao/parametros`).
- SRID 4326 para armazenar; distâncias em metros por projeção local (equiretangular em torno do ponto) — erro < 1% nas distâncias de até alguns km que os alertas usam.
- Toda tela nova tem a barra do topo com o selo "Dados simulados"; mapas com atribuição do OpenStreetMap.
- O ciclo médio ignora viagens `INTERROMPIDA` (decisão da Fase 1).
- Front segue os tokens, a tipografia e os anti-objetivos do documento de layouts; estados de carregamento com esqueleto, não spinner.

## Review Focus

1. **Parado onde é normal parar:** caminhão com velocidade 0 em `CARREGANDO`, `FILA_PATIO`, `PESAGEM` ou `DESCARGA`, ou em trânsito a menos de 500 m de fazenda ou fábrica, não gera PARADA. Teste em Task 4 (`test_parada_no_patio_nao_alerta`, `test_parada_perto_da_fabrica_nao_alerta`).
2. **Alerta aberto quando o trecho acaba:** caminhão com ATRASO aberto chega ao pátio; o alerta fecha e não reabre na próxima viagem por causa do trecho anterior. Teste em Task 5 (`test_alerta_fecha_ao_sair_do_transito`).
3. **Fazenda sem rota no banco:** leitura em trânsito para fazenda sem rota não quebra o lote; ETA fica nulo e DESVIO/ATRASO não são avaliados. Teste em Task 3 (`test_trecho_sem_rota_fica_sem_eta`).
4. **Período sem viagens:** indicadores e pátio devolvem `null` para médias e listas vazias, não 0 nem erro. Teste em Task 7 (`test_espera_media_sem_dados_e_nula`) e Task 8 (`test_indicadores_sem_viagens`).
5. **Velocidade da primeira leitura do trecho:** a média do ETA usa só leituras do trecho atual; as leituras paradas do carregamento não puxam a média para baixo nem disparam ATRASO falso logo na saída. Teste em Task 3 (`test_eta_ignora_leituras_de_antes_do_trecho`).

## Decisões deste plano (não estão no SPEC)

- **Trecho:** cada perna em trânsito (`EM_TRANSITO_CARREGADO`, fazenda → fábrica; `EM_TRANSITO_VAZIO`, fábrica → fazenda de destino) é um trecho. A rota em uso é a da `leitura.fazenda_id` (no vazio, é a fazenda de destino), percorrida ao contrário no vazio.
- **Previsto do trecho:** `eta_prevista = início do trecho + distancia_km da rota ÷ velocidade média configurada` (60 km/h carregado, 70 km/h vazio). Não usa a duração do OSRM, que é de carro e faria todo caminhão parecer atrasado ou adiantado. No trecho carregado, o mesmo valor vai para `viagens.eta_prevista`.
- **ATRASO:** `(eta_atual − início do trecho) > 1,2 × (eta_prevista − início do trecho)`.
- **Média do ETA:** últimas 10 leituras **do trecho atual** (`momento ≥ inicio_trecho`), mínimo de 20 km/h.
- **Fechamento de alertas** (o SPEC só diz que não repete enquanto aberto): um alerta fecha quando a condição deixa de valer na leitura seguinte, ou quando o caminhão sai do trânsito. VELOCIDADE e PARADA também. Um índice único parcial `(tipo, caminhao_id) WHERE status = 'ABERTO'` garante a não repetição no banco.
- **PARADA** só é avaliada em trânsito, e "fora de fazenda, fábrica ou pátio" é: a mais de 500 m de todo polígono de fazenda e do ponto da fábrica (o pátio fica na fábrica).
- **FOCO_PROXIMO_ROTA** fica para a Fase 3 (depende dos focos). A coluna `alertas.foco_id` já entra, sem FK; a FK vem com `focos_calor`. O filtro "Fogo" da tela Alertas só aparece na Fase 3.
- **Colunas novas em `caminhoes`:** `inicio_trecho`, `eta_prevista`, `eta_atual` (o painel lê o ETA sem recalcular).
- **Índice `posicoes(momento)`** entra na migração (minor da Fase 1; `/indicadores` e o "agora" dependem dele).
- **Simulador:** a variação de ±15% passa a ser sorteada **uma vez por trecho**, não por leitura. Com 70 km/h ±15% sorteado por leitura, quase todo trecho vazio passaria de 80 km/h em alguma leitura e o alerta VELOCIDADE viraria ruído; por trecho, só ~2% dos trechos vazios passam do limite. A parada não prevista (5% por viagem) acontece num ponto sorteado entre 20% e 80% do trecho carregado e dura de 20 a 40 min (padrões meus, configuráveis).
- **DESVIO_ROTA** não acontece na simulação (o caminhão segue a rota); a regra é coberta só por teste.
- **`/indicadores?dias=N`** (1 a 30) como alternativa a `inicio`/`fim`: `inicio` = 00h de hoje − (N − 1) dias, `fim` = 00h de amanhã, no fuso configurado. `inicio`/`fim` passam a exigir fuso (422 sem fuso ou com `fim ≤ inicio`).
- **Uso da frota:** fração dos caminhões com estado que não estão em `FILA_PATIO` (esperando não é uso).
- **Série de toneladas:** por hora quando o período tem 1 dia; por dia quando tem mais.
- **`GET /viagens`** (lista das últimas viagens, para escolher o replay) entra além do `GET /viagens/{id}` do SPEC.
- **Fase 2 dividida:** este plano é o painel (2A). O app do motorista em PWA, `POST /motorista/checkin` e `POST /ocorrencias` ficam no plano 2B, que depende de como o app convive com o simulador.

## Estrutura de arquivos

```
api/alembic/versions/0002_fase2.py   alertas, colunas de trecho, índice de posicoes(momento)
api/app/config.py                    limites de alerta (SPEC 6) e parâmetros de parada
api/app/geo.py                       em_metros, progresso_na_linha, distancia_m
api/app/eta.py                       velocidade_media, calcular_eta
api/app/alertas.py                   TipoAlerta, Situacao, alertas_ativos (regras puras)
api/app/vigilancia.py                montar_situacao, atualizar_alertas, alerta_saida (banco)
api/app/telemetria.py                trecho + ETA + alertas por leitura; LoteAplicado
api/app/operacao.py                  espera_media_fila_min, ciclo_medio_min
api/app/rotas_http/alertas.py        GET /alertas
api/app/rotas_http/patio.py          GET /patio/fila
api/app/rotas_http/viagens.py        GET /viagens, GET /viagens/{id}
simulator/sim/simulacao.py           velocidade por trecho, parada não prevista
web/lib/telas.ts, tipos.ts, api.ts, formato.ts, ordenarFrota.ts, useFrotaAoVivo.ts
web/lib/replay.ts                    posicaoNoTempo
web/components/BarraTopo.tsx         menu com as telas novas
web/components/FaixaNumeros.tsx      faixa de números das telas (pátio, indicadores)
web/components/PilulasFiltro.tsx     filtro em pílulas (indicadores, alertas)
web/components/MapaReplay.tsx
web/app/patio/page.tsx, indicadores/page.tsx, alertas/page.tsx, replay/page.tsx
```

---

### Task 1: Migração da Fase 2 e configuração

**Files:**
- Create: `api/alembic/versions/0002_fase2.py`
- Modify: `api/app/modelos.py`, `api/app/config.py`, `api/app/rotas_http/simulacao.py`
- Test: `api/tests/test_migracao.py`, `api/tests/test_config.py`

**Interfaces:**
- Produces:
  - Modelo `Alerta(ComId, Base)`, tabela `alertas`: `tipo: str(30)`, `caminhao_id: int | None` (FK caminhoes), `fazenda_id: int | None` (FK fazendas), `foco_id: int | None` (sem FK), `mensagem: str(200)`, `aberto_em: datetime`, `fechado_em: datetime | None`, `status: str(10)` (`"ABERTO"`/`"FECHADO"`); relação `caminhao`. Índice único parcial `ux_alertas_aberto` em `(tipo, caminhao_id)` com `status = 'ABERTO'`; índice `ix_alertas_aberto_em`.
  - `Caminhao.inicio_trecho`, `Caminhao.eta_prevista`, `Caminhao.eta_atual`: `datetime | None`.
  - Índice `ix_posicoes_momento` em `posicoes(momento)`.
  - `Settings`: `alerta_atraso_tolerancia = 0.20`, `alerta_parada_velocidade_kmh = 5`, `alerta_parada_min = 15`, `alerta_raio_local_m = 500`, `alerta_desvio_m = 500`, `alerta_desvio_leituras = 2`, `alerta_velocidade_max_kmh = 80`, `eta_leituras = 10`, `eta_velocidade_min_kmh = 20`, `parada_min_min = 20`, `parada_max_min = 40`.
  - `CAMPOS_SIMULACAO` ganha `parada_min_min` e `parada_max_min`.

- [ ] **Step 1: Escrever os testes**

```python
def test_migracao_cria_alertas_e_colunas_de_trecho(sessao):
    insp = inspect(sessao.connection())
    assert {"tipo", "caminhao_id", "fazenda_id", "foco_id", "mensagem", "aberto_em",
            "fechado_em", "status"} <= {c["name"] for c in insp.get_columns("alertas")}
    assert {"inicio_trecho", "eta_prevista", "eta_atual"} <= {c["name"] for c in insp.get_columns("caminhoes")}
    assert "ix_posicoes_momento" in {i["name"] for i in insp.get_indexes("posicoes")}

def test_um_alerta_aberto_por_tipo_e_caminhao(sessao, semeado):
    # dois ABERTO iguais violam o índice parcial; um ABERTO + um FECHADO é permitido
    ...
    with pytest.raises(IntegrityError): sessao.flush()

def test_limites_de_alerta_do_spec(settings):
    assert settings.alerta_velocidade_max_kmh == 80 and settings.alerta_parada_min == 15
    assert settings.alerta_desvio_m == 500 and settings.alerta_atraso_tolerancia == 0.20
    assert settings.eta_leituras == 10 and settings.eta_velocidade_min_kmh == 20

def test_parametros_da_simulacao_incluem_parada(cliente):
    r = cliente.get("/simulacao/parametros").json()
    assert r["parada_min_min"] == 20 and r["parada_max_min"] == 40
```

- [ ] **Step 2:** `docker compose exec api pytest tests/test_migracao.py tests/test_config.py -q` → FAIL (tabela `alertas` não existe).
- [ ] **Step 3:** Implementar a migração `0002_fase2` (`down_revision = "0001_fase1"`, com `downgrade`), os modelos e a config.
- [ ] **Step 4:** Rodar de novo → PASS; rodar a suíte inteira da API → PASS.
- [ ] **Step 5: Commit** `feat: tabela de alertas, colunas de trecho e limites da fase 2`

---

### Task 2: Geometria em metros

**Files:**
- Modify: `api/app/geo.py`
- Test: `api/tests/test_geo.py`

**Interfaces:**
- Produces (todas recebem geometrias Shapely em lon/lat):
  - `em_metros(geom: BaseGeometry, lat_ref: float) -> BaseGeometry` — projeção equiretangular local (x = lon × 111 320 × cos(lat_ref), y = lat × 110 574).
  - `progresso_na_linha(linha: LineString, ponto: Point) -> tuple[float, float]` — (fração de 0 a 1 do ponto projetado ao longo da linha, distância em metros do ponto à linha), ambos calculados em metros com `lat_ref = ponto.y`.
  - `distancia_m(geom: BaseGeometry, ponto: Point) -> float` — 0 dentro de polígono.

- [ ] **Step 1: Escrever os testes**

```python
LINHA = LineString([(-51.95, -20.95), (-51.76, -20.62)])

def test_ponto_no_meio_da_linha():
    fracao, dist = progresso_na_linha(LINHA, Point(-51.855, -20.785))
    assert fracao == pytest.approx(0.5, abs=0.01) and dist < 5

def test_distancia_de_um_km_ao_norte():
    p = Point(-51.95, -20.95 + 1000 / 110_574)  # 1 km ao norte da ponta inicial
    assert distancia_m(Point(-51.95, -20.95), p) == pytest.approx(1000, rel=0.01)

def test_distancia_bate_com_haversine():
    a, b = (-51.95, -20.95), (-51.90, -20.93)
    assert distancia_m(Point(a), Point(b)) == pytest.approx(distancia_km(a, b) * 1000, rel=0.01)

def test_dentro_do_poligono_e_zero():
    fazenda = Polygon(quadrado_fazenda(-20.95, -51.95, 3200))
    assert distancia_m(fazenda, Point(-51.95, -20.95)) == 0
```

- [ ] **Step 2:** `docker compose exec api pytest tests/test_geo.py -q` → FAIL (`ImportError`).
- [ ] **Step 3:** Implementar com `shapely.ops.transform`.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5: Commit** `feat: distâncias em metros e progresso ao longo da rota`

---

### Task 3: ETA e trecho na telemetria

**Files:**
- Create: `api/app/eta.py`
- Modify: `api/app/telemetria.py`, `api/app/rotas_http/frota.py`
- Test: `api/tests/test_eta.py`, `api/tests/test_telemetria.py`

**Interfaces:**
- Consumes: `progresso_na_linha` (Task 2); colunas de trecho (Task 1).
- Produces:
  - `velocidade_media(velocidades: list[float], minimo_kmh: float) -> float` — média, nunca abaixo do mínimo; lista vazia → mínimo.
  - `calcular_eta(agora: datetime, restante_km: float, velocidades: list[float], minimo_kmh: float) -> datetime`.
  - Em `registrar_leituras`, depois de gravar a posição de cada leitura (as rotas do lote são carregadas uma vez, `fazenda_id → (LineString, distancia_km)`):
    - Entrou num estado de trânsito (ou está em trânsito com `inicio_trecho` nulo): `inicio_trecho = momento`; `eta_prevista = momento + distancia_km ÷ velocidade configurada do estado`; no carregado, também `viagem.eta_prevista`.
    - Em trânsito: `restante_km = (1 − fração) × distancia_km` no carregado e `fração × distancia_km` no vazio; velocidades = últimas `eta_leituras` posições do caminhão com `momento ≥ inicio_trecho` (inclui a atual); `eta_atual = calcular_eta(...)`.
    - Fora de trânsito: as três colunas voltam a nulo.
    - Sem rota para a fazenda: `eta_prevista` e `eta_atual` ficam nulos; nada quebra.
  - `CaminhaoSaida` (GET `/caminhoes` e WebSocket) ganha `eta: str | None` (ISO de `eta_atual`) e `fazenda: str | None` (nome da fazenda da viagem atual — a de origem).

- [ ] **Step 1: Escrever os testes**

```python
# test_eta.py
AGORA = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)

def test_eta_pela_media_das_leituras():
    assert calcular_eta(AGORA, 50, [40, 60], 20) == AGORA + timedelta(hours=1)

def test_eta_usa_velocidade_minima():
    assert calcular_eta(AGORA, 50, [0, 0, 10], 20) == AGORA + timedelta(hours=2.5)

def test_media_sem_leituras_e_o_minimo():
    assert velocidade_media([], 20) == 20

def test_chegou_eta_e_agora():
    assert calcular_eta(AGORA, 0, [60], 20) == AGORA

# test_telemetria.py — rota da fixture semeado_com_rota: 54,2 km
def test_entrar_em_transito_define_trecho_e_previsto(sessao, ids):
    c, f = ids["caminhoes"][0], ids["fazenda"]
    registrar_leituras(sessao, [leitura(c, f, "CARREGANDO", 0)])
    registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", 10, ponto=INICIO_ROTA, vel=60)])
    cam = sessao.get(Caminhao, c)
    assert cam.inicio_trecho == INICIO + timedelta(minutes=10)
    assert cam.eta_prevista == cam.inicio_trecho + timedelta(minutes=54.2)  # 54,2 km a 60 km/h
    assert cam.viagem_atual.eta_prevista == cam.eta_prevista

def test_eta_atual_pela_distancia_restante(sessao, ids):
    # na metade da rota a 54,2 km/h de média → 30 min para chegar
    ...
    assert cam.eta_atual == momento + timedelta(minutes=30)

def test_eta_ignora_leituras_de_antes_do_trecho(sessao, ids):
    # 5 leituras a 0 km/h em CARREGANDO, depois 1 em trânsito a 60: média = 60, não 10
    ...

def test_sair_do_transito_limpa_o_trecho(sessao, ids): ...

def test_trecho_sem_rota_fica_sem_eta(sessao, ids):
    # remove a rota da fazenda e envia leitura em trânsito: sem erro, eta nulo
    ...

def test_vazio_usa_a_rota_ao_contrario(sessao, ids):
    # vazio perto da fábrica (fim da linha) → restante ≈ distância inteira
    ...

def test_caminhao_saida_tem_eta_e_fazenda(cliente, sessao, ids):
    ...
    assert saida["eta"] is not None and saida["fazenda"].startswith("Fazenda")
```

O helper `leitura_em(c, f, estado, minuto, ponto, vel)` monta a leitura com posição e velocidade dadas; `INICIO_ROTA = (-51.95, -20.95)`.

- [ ] **Step 2:** `docker compose exec api pytest tests/test_eta.py tests/test_telemetria.py -q` → FAIL.
- [ ] **Step 3:** Implementar `eta.py` e o trecho em `telemetria.py`; acrescentar `eta` e `fazenda` em `montar_caminhao_saida`.
- [ ] **Step 4:** Rodar → PASS; suíte inteira da API → PASS.
- [ ] **Step 5: Commit** `feat: ETA por trecho a partir das últimas leituras`

---

### Task 4: Regras de alerta (puras)

**Files:**
- Create: `api/app/alertas.py`
- Test: `api/tests/test_alertas.py`

**Interfaces:**
- Produces:
  - `class TipoAlerta(StrEnum)`: `ATRASO`, `PARADA`, `DESVIO_ROTA`, `VELOCIDADE`.
  - `@dataclass Situacao`: `estado: Estado`, `velocidade_kmh: float`, `momento: datetime`, `parado_desde: datetime | None` (primeira leitura da sequência atual abaixo do limite de parada; `None` se a atual está acima), `distancia_local_m: float` (até a fazenda ou fábrica mais próxima), `fora_da_rota_seguidas: int` (leituras seguidas do trecho, terminando na atual, a mais de `alerta_desvio_m` da rota; 0 sem rota), `inicio_trecho`, `eta_prevista`, `eta_atual: datetime | None`.
  - `alertas_ativos(s: Situacao, settings: Settings) -> set[TipoAlerta]`:
    - VELOCIDADE: `velocidade_kmh > alerta_velocidade_max_kmh`.
    - PARADA: em trânsito, `parado_desde` definido, `momento − parado_desde > alerta_parada_min` e `distancia_local_m > alerta_raio_local_m`.
    - DESVIO_ROTA: em trânsito e `fora_da_rota_seguidas ≥ alerta_desvio_leituras`.
    - ATRASO: em trânsito, os três horários definidos e `(eta_atual − inicio_trecho) > (1 + alerta_atraso_tolerancia) × (eta_prevista − inicio_trecho)`.

- [ ] **Step 1: Escrever os testes** (helper `situacao(**mudancas)` parte de um caminhão carregado a 60 km/h, no meio da rota, sem atraso)

```python
def test_sem_alerta_em_situacao_normal(settings):
    assert alertas_ativos(situacao(), settings) == set()

def test_velocidade_acima_de_80(settings):
    assert TipoAlerta.VELOCIDADE in alertas_ativos(situacao(velocidade_kmh=80.5), settings)
    assert TipoAlerta.VELOCIDADE not in alertas_ativos(situacao(velocidade_kmh=80), settings)

def test_parada_depois_de_15_min_fora_de_local(settings):
    s = situacao(velocidade_kmh=0, parado_desde=MOMENTO - timedelta(minutes=16), distancia_local_m=2000)
    assert TipoAlerta.PARADA in alertas_ativos(s, settings)

def test_parada_de_15_min_ainda_nao_alerta(settings):
    s = situacao(velocidade_kmh=0, parado_desde=MOMENTO - timedelta(minutes=15), distancia_local_m=2000)
    assert TipoAlerta.PARADA not in alertas_ativos(s, settings)

def test_parada_perto_da_fabrica_nao_alerta(settings):
    s = situacao(velocidade_kmh=0, parado_desde=MOMENTO - timedelta(minutes=40), distancia_local_m=400)
    assert alertas_ativos(s, settings) == set()

def test_parada_no_patio_nao_alerta(settings):
    s = situacao(estado=Estado.FILA_PATIO, velocidade_kmh=0,
                 parado_desde=MOMENTO - timedelta(hours=1), distancia_local_m=2000)
    assert alertas_ativos(s, settings) == set()

def test_desvio_so_na_segunda_leitura_fora(settings):
    assert TipoAlerta.DESVIO_ROTA not in alertas_ativos(situacao(fora_da_rota_seguidas=1), settings)
    assert TipoAlerta.DESVIO_ROTA in alertas_ativos(situacao(fora_da_rota_seguidas=2), settings)

def test_atraso_acima_de_20_por_cento(settings):
    # previsto 60 min de trecho; ETA atual dá 73 min → alerta; 72 min → não
    ...

def test_sem_previsto_nao_avalia_atraso(settings):
    assert alertas_ativos(situacao(eta_prevista=None, eta_atual=None), settings) == set()
```

- [ ] **Step 2:** `docker compose exec api pytest tests/test_alertas.py -q` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5: Commit** `feat: regras de alerta de logística`

---

### Task 5: Alertas no banco, na telemetria, no WebSocket e em `GET /alertas`

**Files:**
- Create: `api/app/vigilancia.py`, `api/app/rotas_http/alertas.py`
- Modify: `api/app/telemetria.py`, `api/app/rotas_http/frota.py`, `api/app/main.py`
- Test: `api/tests/test_vigilancia.py`, `api/tests/test_telemetria.py`

**Interfaces:**
- Consumes: `alertas_ativos`, `Situacao` (Task 4); `distancia_m`, `progresso_na_linha` (Task 2); trecho (Task 3).
- Produces:
  - `montar_situacao(sessao, caminhao, leitura, rota: LineString | None, locais: list[BaseGeometry], settings) -> Situacao` — chamada depois de gravar a posição; `locais` = polígonos das fazendas + ponto da fábrica, carregados uma vez por lote.
  - `atualizar_alertas(sessao, caminhao, ativos: set[TipoAlerta], situacao: Situacao) -> list[Alerta]` — abre os ativos que não estão abertos (`aberto_em = momento`, mensagem do tipo) e fecha os abertos que não estão ativos (`fechado_em = momento`, `status = "FECHADO"`); devolve os que mudaram.
  - Mensagens (em português, curtas): VELOCIDADE `"83 km/h"`; PARADA `"Parado há 16 min fora de fazenda ou fábrica"`; DESVIO_ROTA `"A 740 m da rota"`; ATRASO `"Chegada prevista às 14h50, 35 min depois do previsto"` (hora no fuso configurado).
  - `registrar_leituras` passa a devolver `LoteAplicado(caminhoes: list[int], alertas: list[int])` (ids, sem repetição, na ordem).
  - `alerta_saida(alerta) -> dict`: `{id, tipo, caminhao_id, placa, fazenda_id, fazenda, mensagem, aberto_em, fechado_em, status}`.
  - `POST /telemetria`, depois do commit: difunde os caminhões (como hoje) e depois `{"tipo": "alerta", "alerta": AlertaSaida}` para cada alerta que mudou.
  - `CaminhaoSaida` ganha `alertas_abertos: list[str]` (tipos, ordem alfabética).
  - `GET /alertas?status=ABERTO|FECHADO&tipo=&limite=200` → `list[AlertaSaida]`, mais recentes primeiro.

- [ ] **Step 1: Escrever os testes**

```python
def test_alerta_abre_uma_vez_enquanto_aberto(sessao, ids):
    for m in range(3):  # três leituras seguidas a 85 km/h
        registrar_leituras(sessao, [leitura_em(c, f, "EM_TRANSITO_CARREGADO", m, vel=85)])
    assert contar_alertas(sessao, "VELOCIDADE") == 1

def test_alerta_fecha_quando_a_condicao_passa(sessao, ids):
    # 85 km/h, depois 70 → FECHADO com fechado_em = momento da segunda
    ...

def test_alerta_reabre_depois_de_fechado(sessao, ids):
    # 85, 70, 85 → dois alertas: um FECHADO e um ABERTO
    ...

def test_alerta_fecha_ao_sair_do_transito(sessao, ids):
    # ATRASO aberto em trânsito; leitura em FILA_PATIO fecha
    ...

def test_parada_pela_sequencia_de_leituras(sessao, ids):
    # em trânsito a 2 km do fim da rota: 60 km/h, depois 0 km/h por 33 leituras de 30 s
    # → PARADA abre só quando passa de 15 min parado
    ...

def test_desvio_com_duas_leituras_fora_da_rota(sessao, ids):
    # duas leituras a ~1 km da linha → DESVIO_ROTA; uma só → nada
    ...

def test_lote_devolve_alertas_que_mudaram(sessao, ids): ...

def test_websocket_recebe_alerta(cliente, ids):
    with cliente.websocket_connect("/ws/frota") as ws:
        cliente.post("/telemetria", json=[leitura_json_em(c, f, "EM_TRANSITO_CARREGADO", 0, vel=85)], headers=CABECALHO)
        mensagens = [ws.receive_json(), ws.receive_json()]
    assert [m["tipo"] for m in mensagens] == ["caminhao", "alerta"]
    assert mensagens[0]["caminhao"]["alertas_abertos"] == ["VELOCIDADE"]
    assert mensagens[1]["alerta"]["mensagem"] == "85 km/h"

def test_get_alertas_filtra_por_status_e_tipo(cliente, ids): ...
```

- [ ] **Step 2:** `docker compose exec api pytest tests/test_vigilancia.py tests/test_telemetria.py -q` → FAIL.
- [ ] **Step 3:** Implementar; ajustar `_aplicar_lote` em `frota.py` ao `LoteAplicado`.
- [ ] **Step 4:** Rodar → PASS; suíte inteira da API → PASS.
- [ ] **Step 5: Commit** `feat: alertas de logística na telemetria, no WebSocket e em /alertas`

---

### Task 6: Simulador — velocidade por trecho e parada não prevista

**Files:**
- Modify: `simulator/sim/simulacao.py`
- Test: `simulator/tests/test_simulacao.py`

**Interfaces:**
- Consumes: `parada_min_min`, `parada_max_min` em `/simulacao/parametros` (Task 1).
- Produces:
  - `Parametros` ganha `parada_min_min: float`, `parada_max_min: float`.
  - `CaminhaoSim` ganha `fator_velocidade: float = 1`, `parada_km: float | None = None`, `parada_restante_min: float = 0`.
  - Ao entrar em qualquer trânsito: `fator_velocidade = rng.uniform(1 − variacao, 1 + variacao)`. Ao entrar em `EM_TRANSITO_CARREGADO`: com probabilidade `prob_evento_viagem`, `parada_km = rng.uniform(0.2, 0.8) × comprimento da rota` e `parada_restante_min = rng.uniform(parada_min_min, parada_max_min)`; senão `parada_km = None`.
  - Em trânsito: velocidade = base × fator (constante no trecho). Ao alcançar `parada_km` com `parada_restante_min > 0`, fica parado (velocidade 0, `km` não avança) até zerar `parada_restante_min`; depois segue.

- [ ] **Step 1: Escrever os testes**

```python
def test_velocidade_constante_dentro_do_trecho(): ...
def test_velocidade_por_trecho_dentro_da_variacao():
    # 200 trechos: toda velocidade em [60 × 0,85, 60 × 1,15] e [70 × 0,85, 70 × 1,15]
    ...
def test_parada_nao_prevista_segura_o_caminhao():
    # prob_evento_viagem = 1, parada 20–20 min: no trecho carregado aparecem 40 leituras
    # seguidas (30 s cada) com velocidade 0 e a mesma posição, depois volta a andar
    ...
def test_sem_evento_nao_para_no_transito():
    # prob_evento_viagem = 0: nenhuma leitura em trânsito com velocidade 0
    ...
def test_mesma_semente_mesma_sequencia(): ...  # já existe: deve continuar passando
```

`PARAMETROS_PADRAO` dos testes ganha `"parada_min_min": 20, "parada_max_min": 40`; `api_falsa` em `test_cliente.py` também.

- [ ] **Step 2:** `docker compose exec simulator pytest -q` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5: Commit** `feat: simulador com velocidade por trecho e parada não prevista`

---

### Task 7: `GET /patio/fila`

**Files:**
- Create: `api/app/operacao.py`, `api/app/rotas_http/patio.py`
- Modify: `api/app/main.py`, `api/app/rotas_http/indicadores.py` (extrair o cálculo do "agora" para `operacao.agora_simulado(sessao, fuso)`)
- Test: `api/tests/test_patio.py`

**Interfaces:**
- Produces:
  - `agora_simulado(sessao, fuso: ZoneInfo) -> datetime` — `max(posicoes.momento)` ou o horário real, no fuso.
  - `espera_media_fila_min(sessao, inicio, fim) -> float | None` — média de (momento de `PESAGEM` − momento de `FILA_PATIO`) na mesma viagem, para `PESAGEM` em `[inicio, fim)`.
  - `GET /patio/fila` → `{agora, vagas_total, vagas_ocupadas, fila: [{caminhao_id, placa, posicao, chegou_em, esperando_min}], espera_media_min, chegadas: [{caminhao_id, placa, fazenda, eta}]}`.
    - `vagas_ocupadas` = caminhões em `PESAGEM` ou `DESCARGA`.
    - `fila` = caminhões em `FILA_PATIO`, por `chegou_em` (momento do evento `FILA_PATIO` da viagem atual), `posicao` a partir de 1, `esperando_min = agora − chegou_em`.
    - `espera_media_min` = `espera_media_fila_min` de hoje (00h no fuso até `agora`).
    - `chegadas` = caminhões em `EM_TRANSITO_CARREGADO` com `eta_atual` em `[agora, agora + 2 h]`, por `eta`.

- [ ] **Step 1: Escrever os testes**

```python
def test_fila_em_ordem_de_chegada(cliente, sessao, ids):
    # caminhão B entra na fila às 10h05, A às 10h10 → B posição 1, A posição 2
    ...

def test_vagas_ocupadas_contam_pesagem_e_descarga(cliente, sessao, ids): ...

def test_espera_media_de_hoje(cliente, sessao, ids):
    # duas viagens: 10 e 20 min entre FILA_PATIO e PESAGEM → 15
    ...

def test_espera_media_sem_dados_e_nula(cliente, semeado):
    assert cliente.get("/patio/fila").json()["espera_media_min"] is None

def test_chegadas_nas_proximas_duas_horas(cliente, sessao, ids):
    # ETA em 30 min entra; ETA em 3 h não entra; vazio não entra
    ...
```

- [ ] **Step 2–4:** FAIL → implementar → PASS (suíte inteira da API).
- [ ] **Step 5: Commit** `feat: fila do pátio e chegadas previstas`

---

### Task 8: `GET /indicadores` completo

**Files:**
- Modify: `api/app/rotas_http/indicadores.py`, `api/app/operacao.py`
- Test: `api/tests/test_indicadores.py`

**Interfaces:**
- Consumes: `agora_simulado`, `espera_media_fila_min` (Task 7).
- Produces:
  - Parâmetros: `inicio`, `fim` (`AwareDatetime`, opcionais; 422 se `fim ≤ inicio`) **ou** `dias: int` (1 a 30, padrão 1).
  - Resposta, além dos campos da Fase 1: `dias: float`, `ciclo_medio_min: float | None` (média de `fim − inicio` das viagens `CONCLUIDA` com `fim` no período), `fila_media_min: float | None`, `uso_frota: float` (0 a 1, agora), `frota_por_estado: dict[str, int]` (agora, os 6 estados, zeros incluídos), `serie: [{inicio, toneladas}]` (por hora se o período tem 1 dia, por dia se tem mais; cobre o período inteiro, baldes vazios com 0).
  - `ciclo_medio_min(sessao, inicio, fim) -> float | None` em `operacao.py`.

- [ ] **Step 1: Escrever os testes**

```python
def test_ciclo_medio_ignora_interrompidas(cliente, sessao, ids):
    # uma CONCLUIDA de 3 h e uma INTERROMPIDA de 1 h → 180
    ...

def test_indicadores_sem_viagens(cliente, semeado):
    r = cliente.get("/indicadores").json()
    assert r["ciclo_medio_min"] is None and r["fila_media_min"] is None
    assert len(r["serie"]) == 24 and all(b["toneladas"] == 0 for b in r["serie"])

def test_serie_por_hora_no_fuso(cliente, sessao, ids):
    # entrega às 10h20 de Campo Grande cai no balde das 10h
    ...

def test_sete_dias_tem_serie_diaria_e_meta_semanal(cliente, semeado):
    r = cliente.get("/indicadores?dias=7").json()
    assert len(r["serie"]) == 7 and r["meta_t"] == 28000

def test_uso_e_frota_por_estado(cliente, sessao, ids):
    # 2 caminhões em trânsito e 1 na fila → uso 2/3
    ...

def test_periodo_sem_fuso_e_recusado(cliente):
    assert cliente.get("/indicadores?inicio=2026-10-20T00:00:00&fim=2026-10-21T00:00:00").status_code == 422

def test_periodo_invertido_e_recusado(cliente): ...
```

- [ ] **Step 2–4:** FAIL → implementar → PASS (suíte inteira da API, inclusive os testes da Fase 1 em `test_indicadores.py`).
- [ ] **Step 5: Commit** `feat: indicadores completos com ciclo, fila, uso da frota e série`

---

### Task 9: Viagens para o replay

**Files:**
- Create: `api/app/rotas_http/viagens.py`
- Modify: `api/app/main.py`
- Test: `api/tests/test_viagens.py`

**Interfaces:**
- Produces:
  - `GET /viagens?caminhao_id=&limite=20` → `[{id, caminhao_id, placa, fazenda, toneladas, inicio, fim, status}]`, mais recentes primeiro (`limite` de 1 a 100).
  - `GET /viagens/{id}` → `{id, caminhao_id, placa, fazenda, toneladas, inicio, fim, status, rota: GeoJSON LineString | None, pontos: [{lon, lat, velocidade_kmh, momento}], eventos: [{estado, momento}]}`, pontos e eventos em ordem de tempo. 404 com `"Viagem não encontrada"`.

- [ ] **Step 1: Escrever os testes**

```python
def test_viagem_com_pontos_e_eventos_em_ordem(cliente, sessao, ids): ...
def test_viagem_inexistente_404(cliente, semeado):
    assert cliente.get("/viagens/999999").status_code == 404
def test_viagem_sem_pontos(cliente, sessao, ids):  # lista vazia, não erro
    ...
def test_lista_filtra_por_caminhao_e_ordena(cliente, sessao, ids): ...
```

- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat: viagens com trajeto e eventos para o replay`

---

### Task 10: Front — base da Fase 2 e tela Ao vivo completa

**Files:**
- Create: `web/components/PilulasFiltro.tsx`, `web/components/FaixaNumeros.tsx`
- Modify: `web/lib/telas.ts`, `web/lib/tipos.ts`, `web/lib/api.ts`, `web/lib/formato.ts`, `web/lib/estados.ts`, `web/lib/ordenarFrota.ts`, `web/lib/useFrotaAoVivo.ts`, `web/lib/fabricas.test-util.ts`, `web/components/TabelaFrota.tsx`, `web/components/DetalheCaminhao.tsx`, `web/components/ReguaMeta.tsx`, `web/app/page.tsx`
- Test: `web/lib/ordenarFrota.test.ts`, `web/lib/formato.test.ts`, `web/lib/useFrotaAoVivo.test.tsx`, `web/components/TabelaFrota.test.tsx`, `web/components/ReguaMeta.test.tsx`, `web/components/BarraTopo.test.tsx`, `web/components/DetalheCaminhao.test.tsx`

**Interfaces:**
- Consumes: formatos das Tasks 3, 5, 7, 8 e 9.
- Produces:
  - `TELAS`: Ao vivo `/`, Pátio `/patio`, Indicadores `/indicadores`, Alertas `/alertas`, Replay `/replay`.
  - Tipos: `Caminhao` + `eta: string | null`, `fazenda: string | null`, `alertas_abertos: TipoAlerta[]`; `TipoAlerta`; `Alerta`; `Patio`; `Indicadores` completo; `ViagemResumo`; `ViagemDetalhe`; `MensagemFrota` = caminhão | `{tipo: "alerta", alerta: Alerta}`.
  - `api.ts`: `buscarIndicadores(dias = 1)`, `buscarAlertas(status)`, `buscarPatio()`, `buscarViagens(caminhaoId?)`, `buscarViagem(id)`.
  - `formato.ts`: `duracao(min: number | null): string` → `"38 min"` abaixo de 60, `"4h12"` a partir de 60, `"—"` para nulo.
  - `ROTULO_ALERTA: Record<TipoAlerta, string>`: Atraso, Parada, Desvio de rota, Velocidade.
  - `ordenarFrota`: com alerta aberto primeiro → em trânsito por ETA crescente → resto pela prioridade da Fase 1; placa desempata.
  - `useFrotaAoVivo`: mensagem `alerta` invalida as consultas `["alertas"]` e `["patio"]`; mensagem `caminhao` como hoje.
  - `TabelaFrota`: colunas Placa, Estado, Carga, ETA (`horaCurta` ou `"—"`); linha com alerta em `bg-atencao-fundo`.
  - `DetalheCaminhao`: acrescenta Fazenda de origem, ETA, alertas abertos (rótulo) e o link "Ver viagem no replay" → `/replay?viagem=<viagem_atual_id>`.
  - `ReguaMeta`: ciclo médio e espera no pátio vêm de `ciclo_medio_min` e `fila_media_min` via `duracao`.
  - `page.tsx`: `?caminhao=<id>` na URL abre a tela com o caminhão selecionado (`useSearchParams` dentro de `<Suspense>`).
  - `<PilulasFiltro opcoes={{valor, rotulo}[]} valor onMudar rotulo />` — grupo de botões com `aria-pressed`, no estilo do menu.
  - `<FaixaNumeros itens={{valor, rotulo}[]} />` — a faixa de números das telas.

- [ ] **Step 1: Escrever os testes**

```ts
it("alerta primeiro, depois em trânsito por ETA", () => {
  const lista = ordenarFrota([
    caminhao("TLG1A01", "EM_TRANSITO_CARREGADO", 55, { eta: "2026-10-20T15:00:00-04:00" }),
    caminhao("TLG1A02", "EM_TRANSITO_VAZIO", 0, { eta: "2026-10-20T14:00:00-04:00" }),
    caminhao("TLG1A03", "CARREGANDO", 0, { alertas_abertos: ["PARADA"] }),
  ]);
  expect(lista.map((c) => c.placa)).toEqual(["TLG1A03", "TLG1A02", "TLG1A01"]);
});

it("duração curta e longa", () => {
  expect(duracao(38)).toBe("38 min");
  expect(duracao(252)).toBe("4h12");
  expect(duracao(null)).toBe("—");
});

it("linha com alerta fica destacada e mostra o ETA", () => { ... });
it("detalhe mostra fazenda de origem, alertas e link do replay", () => { ... });
it("régua mostra ciclo médio e espera no pátio", () => { ... });
it("mensagem de alerta invalida a lista de alertas", () => { ... });
it("menu mostra as telas da fase 2 e marca a atual", () => { ... });
```

- [ ] **Step 2:** `cd web && npm test` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `npm test`, `npx tsc --noEmit`, `npm run lint` → tudo limpo.
- [ ] **Step 5: Commit** `feat: ao vivo com ETA, alertas na frota e menu da fase 2`

---

### Task 11: Front — tela Pátio

**Files:**
- Create: `web/app/patio/page.tsx`, `web/components/FilaPatio.tsx`, `web/components/ChegadasPrevistas.tsx`
- Test: `web/components/FilaPatio.test.tsx`, `web/components/ChegadasPrevistas.test.tsx`

**Interfaces:**
- Consumes: `buscarPatio`, `FaixaNumeros`, `duracao`, `horaCurta` (Task 10).
- Produces (layout 4.2): faixa com "na fila", "vagas ocupadas" (`"2 de 3"`), "espera média hoje", "chegando em 2 h"; esquerda "Fila agora" (posição, placa, chegou, esperando); direita "Chegadas previstas" — trilho de 2 h a partir de `agora`, um traço `primaria` por caminhão na posição `(eta − agora) / 2 h` com a placa. Recarrega a cada 30 s e quando chega alerta (Task 10). Fila vazia: "Ninguém na fila agora."

- [ ] **Step 1: Escrever os testes**

```ts
it("fila em ordem com tempo de espera", () => { ... "1", "TLG1A23", "14h02", "12 min" ... });
it("fila vazia diz isso", () => { ... "Ninguém na fila agora." ... });
it("chegada a 1 h fica no meio do trilho", () => {
  // style left: 50%
});
```

- [ ] **Step 2–4:** FAIL → implementar → PASS; `tsc` e `lint` limpos.
- [ ] **Step 5: Commit** `feat: tela do pátio com fila e chegadas previstas`

---

### Task 12: Front — tela Indicadores

Antes de escrever o gráfico, carregar a skill `dataviz`.

**Files:**
- Create: `web/app/indicadores/page.tsx`, `web/components/BarrasToneladas.tsx`, `web/components/UsoFrota.tsx`
- Test: `web/components/BarrasToneladas.test.tsx`, `web/components/UsoFrota.test.tsx`

**Interfaces:**
- Consumes: `buscarIndicadores(dias)`, `PilulasFiltro`, `FaixaNumeros`, `duracao` (Task 10).
- Produces (layout 4.3): pílulas Hoje / 7 dias / 30 dias (`dias` = 1, 7, 30); faixa com toneladas "de X t", viagens, ciclo médio, fila média, uso da frota em %; esquerda: barras de toneladas por balde da `serie` (SVG ou divs, sem biblioteca), com linha tracejada `tinta` no ritmo necessário (`meta_t ÷ número de baldes`); direita: uma barra empilhada de `frota_por_estado` em quatro grupos (Carregado, Vazio, Carregando, No pátio — este soma fila, pesagem e descarga), com legenda e percentuais. Recarrega a cada 60 s.

- [ ] **Step 1: Escrever os testes**

```ts
it("uma barra por balde, com rótulo acessível", () => { ... "10h: 110 t" ... });
it("linha do ritmo na altura de meta ÷ baldes", () => { ... });
it("uso da frota agrupa os estados do pátio", () => { ... "No pátio 25%" ... });
it("trocar o filtro pede outro período", async () => { ... buscarIndicadores chamado com 7 ... });
```

- [ ] **Step 2–4:** FAIL → implementar → PASS; `tsc` e `lint` limpos.
- [ ] **Step 5: Commit** `feat: tela de indicadores`

---

### Task 13: Front — tela Alertas

**Files:**
- Create: `web/app/alertas/page.tsx`, `web/components/TabelaAlertas.tsx`
- Test: `web/components/TabelaAlertas.test.tsx`

**Interfaces:**
- Consumes: `buscarAlertas`, `PilulasFiltro`, `ROTULO_ALERTA` (Task 10).
- Produces (layout 4.4): pílulas de status "Abertos (n)" e "Fechados"; tabela com hora (`horaCurta(aberto_em)`), tipo (peso 600, `atencao` se aberto), caminhão, o que aconteceu (`mensagem`), status ("Aberto" ou "Fechado às 14h50"), link "Ver no mapa" → `/?caminhao=<id>`. Fechados em `tinta-suave`. Sem o filtro Logística/Fogo nesta fase. Lista vazia: "Nenhum alerta aberto." / "Nenhum alerta fechado."

- [ ] **Step 1: Escrever os testes**

```ts
it("alerta aberto mostra tipo, mensagem e link para o mapa", () => { ... href "/?caminhao=3" ... });
it("fechado mostra a hora em que fechou", () => { ... });
it("sem alertas abertos diz isso", () => { ... });
```

- [ ] **Step 2–4:** FAIL → implementar → PASS; `tsc` e `lint` limpos.
- [ ] **Step 5: Commit** `feat: tela de alertas`

---

### Task 14: Front — tela Replay

**Files:**
- Create: `web/lib/replay.ts`, `web/components/MapaReplay.tsx`, `web/components/LinhaTempo.tsx`, `web/app/replay/page.tsx`
- Test: `web/lib/replay.test.ts`, `web/components/LinhaTempo.test.tsx`

**Interfaces:**
- Consumes: `buscarViagens`, `buscarViagem` (Task 10).
- Produces (layout 4.6):
  - `posicaoNoTempo(pontos: PontoViagem[], momento: number): {lon, lat, indice}` — interpola linearmente entre os dois pontos em volta de `momento` (ms); antes do primeiro → primeiro; depois do último → último. `indice` = último ponto já passado (para cortar o trajeto percorrido).
  - `/replay?viagem=<id>`: cabeçalho "viagem de 19/10, Fazenda Três Irmãos até a fábrica, 55 t" e a placa; sem `viagem`, uma lista das últimas viagens (`buscarViagens`) para escolher. Viagem não encontrada: "Viagem não encontrada." com link para a lista.
  - `<MapaReplay rota pontos cursor />`: rota tracejada cinza, trajeto percorrido em `primaria` até o cursor, o caminhão no ponto do cursor; atribuição OSM.
  - `<LinhaTempo inicio fim eventos cursor onMudar />`: `<input type="range">` acessível sobre o trilho, eventos como pontos com rótulo do estado (`ROTULO_ESTADO`) e hora.

- [ ] **Step 1: Escrever os testes**

```ts
it("interpola entre dois pontos", () => {
  expect(posicaoNoTempo(pontos, metade)).toMatchObject({ lon: -51.855, lat: -20.785, indice: 0 });
});
it("antes do início fica no primeiro ponto, depois do fim no último", () => { ... });
it("linha do tempo mostra os eventos e move o cursor", async () => { ... onMudar chamado ... });
```

O `MapaReplay` não tem teste unitário (WebGL); é verificado na Task 15.

- [ ] **Step 2–4:** FAIL → implementar → PASS; `tsc` e `lint` limpos.
- [ ] **Step 5: Commit** `feat: tela de replay da viagem`

---

### Task 15: Verificação ponta a ponta e documentação

**Files:**
- Modify: `README.md` (telas da Fase 2, alertas e como forçar um pela variável de ambiente), `CLAUDE.md` (Comandos, se algum mudar)

- [ ] **Step 1:** `docker compose up -d --build` (aplica a migração 0002 pelo serviço `preparo`); todas as suítes passam: `docker compose exec api pytest`, `docker compose exec simulator pytest`, `cd web && npm test`, `npx tsc --noEmit`, `npm run lint`.
- [ ] **Step 2:** Para ver alertas sem esperar, subir o simulador uma vez com `PROB_EVENTO_VIAGEM=1` no serviço `api` (o simulador lê da API) e conferir no navegador (Playwright) que aparecem PARADA e ATRASO na tela Alertas e destacados na tabela da frota; voltar ao padrão depois.
- [ ] **Step 3:** Navegar por todas as telas em `http://localhost/`: Pátio (fila e chegadas mudam com o tempo), Indicadores (os três filtros), Alertas ("Ver no mapa" abre o caminhão selecionado), Replay (arrastar o cursor move o caminhão). Sem erros no console. Screenshot de cada tela, também em 390 px de largura.
- [ ] **Step 4:** Commit `docs: telas e alertas da fase 2 no README`

---

## Critérios de pronto da Fase 2 (SPEC seção 12) cobertos por este plano

| critério | task |
|---|---|
| Pátio | 7, 11 |
| Indicadores | 8, 10, 12 |
| Alertas de logística (seção 6) | 1, 2, 4, 5, 6, 10, 13 |
| Replay | 9, 14 |
| Testes de cada regra de alerta, inclusive a não repetição | 4, 5 |
| Testes do ETA | 3 |
| App do motorista em PWA com modo offline | plano 2B |
