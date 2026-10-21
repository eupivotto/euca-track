# Fase 1 — Base e mapa ao vivo: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Subir com um comando a API, o banco PostGIS, o simulador da frota, o front e o Nginx, com os 20 caminhões fictícios percorrendo o ciclo e aparecendo em movimento na tela "Ao vivo".

**Architecture:** O simulador é um processo único que mantém o estado dos 20 caminhões e do pátio, avança o relógio simulado e manda telemetria em lote para a API. A API grava posições, abre e fecha viagens conforme o estado muda, e repassa cada leitura por WebSocket. O front carrega o estado inicial por REST e depois só aplica as mensagens do WebSocket, com reconexão automática.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, GeoAlchemy2, Shapely 2, Alembic, pydantic-settings, psycopg 3, httpx, pytest; Next.js 15 (App Router), React 19, TypeScript, Tailwind 4, MapLibre GL 5, TanStack Query 5, Vitest + Testing Library; PostgreSQL 16 + PostGIS 3.4 (`postgis/postgis:16-3.4`); Docker Compose; Nginx.

**Spec:** `docs/SPEC.md` (seções 3, 4, 5, 9, 10, 11, 12 — Fase 1) e `docs/superpowers/specs/2026-10-20-layouts-design.md` (linguagem visual e tela Ao vivo).

## Global Constraints

- TDD: teste antes da implementação para toda regra de negócio; rodar os testes ao fim de cada passo.
- Código, tabelas e variáveis em português sem acento; comentários em português.
- Commits pequenos em português, formato `tipo: descrição` (feat, fix, test, docs, chore, refactor), terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Parâmetros de simulação ficam em `api/app/config.py` (pydantic-settings), com os padrões da seção 4 do SPEC e sobrescrita por variável de ambiente. O simulador não tem cópia própria: busca os parâmetros na API.
- Nunca chamar OSRM dentro de request do usuário: só no script `gerar_rotas.py`, com resultado salvo no banco.
- Antes de escrever o parser do OSRM, baixar uma resposta real para `api/tests/fixtures/`.
- SRID 4326 para armazenar.
- Toda tela com dados simulados exibe o selo "Dados simulados"; mapa com atribuição do OpenStreetMap.
- `SEED=42` para tudo que é sorteado (placas, nomes, fazenda inicial, sorteios do simulador).
- Front segue os tokens, a tipografia e a lista de anti-objetivos do documento de layouts.

## Review Focus

1. **Simulador reiniciado no meio do dia:** a API já tem viagem aberta para o caminhão; a primeira leitura nova não pode duplicar viagem nem quebrar. Teste em Task 6 (`test_reinicio_mesmo_estado_nao_duplica_viagem`).
2. **Cliente de WebSocket que caiu durante o envio:** a telemetria continua sendo aceita e a conexão morta é descartada. Teste em Task 6 (`test_broadcast_descarta_conexao_morta`).
3. **Telemetria inválida:** token errado → 401; caminhão inexistente → 422 sem gravar nada do lote. Teste em Task 6.
4. **API fora do ar quando o simulador envia:** o simulador registra o erro e segue no próximo passo, sem morrer. Teste em Task 10 (`test_envio_com_api_fora_nao_levanta`).
5. **Pátio lotado:** o 4º caminhão espera em `FILA_PATIO` até abrir vaga, na ordem de chegada. Teste em Task 9 (`test_quarto_caminhao_espera_na_fila`).

## Decisões deste plano (não estão no SPEC)

- Endpoints extras: `GET /rotas` (o mapa e o simulador precisam das linhas) e `GET /simulacao/parametros` (para o simulador ler a config da API).
- `POST /telemetria` recebe uma **lista** de leituras (um lote por passo do simulador).
- `GET /indicadores` já existe na Fase 1, mas só com `toneladas`, `viagens`, `meta_t` e `agora`, para alimentar a régua da meta. A Fase 2 completa os outros campos.
- "Agora" do painel é o relógio simulado: `max(posicoes.momento)`, ou o horário real se ainda não houver posição.
- Viagem começa quando o caminhão entra em `CARREGANDO` e termina quando ele entra em `CARREGANDO` de novo; `toneladas` = capacidade do caminhão. Entregue = viagem com evento `EM_TRANSITO_VAZIO` no período.
- Pátio: a vaga de descarga (3) é tomada ao sair da fila para a pesagem; o caminhão ocupa a vaga em `PESAGEM` e `DESCARGA`.
- Parada não prevista (5%) fica para a Fase 2, junto com o alerta PARADA; o parâmetro já entra na config.
- Testes da API rodam contra o banco `rota_teste` no mesmo container PostGIS.

## Estrutura de arquivos

```
docker-compose.yml
infra/db/init.sql                    cria rota_teste e extensão postgis
infra/nginx/default.conf
api/Dockerfile, api/pyproject.toml, api/alembic.ini
api/alembic/env.py, api/alembic/versions/0001_fase1.py
api/app/config.py                    Settings (pydantic-settings)
api/app/db.py                        engine, SessionLocal, get_sessao
api/app/modelos.py                   modelos SQLAlchemy da Fase 1
api/app/estados.py                   Estado (StrEnum), ESTADOS_CARREGADO
api/app/geo.py                       quadrado_fazenda, distancia_km, linha_reta
api/app/seed.py                      dados das seções 3 e 4
api/app/osrm.py                      RotaCalculada, ler_resposta_osrm, buscar_rota
api/app/scripts/gerar_rotas.py
api/app/tempo_real.py                Difusor (WebSocket)
api/app/telemetria.py                registrar_leituras
api/app/rotas_http/                  saude.py, mapa.py, frota.py, indicadores.py, simulacao.py
api/app/main.py
api/tests/conftest.py, api/tests/fixtures/osrm_faz01.json
simulator/Dockerfile, simulator/pyproject.toml
simulator/sim/estados.py             Estado, proximo_estado
simulator/sim/rota.py                comprimento_km, ponto_na_linha
simulator/sim/simulacao.py           Parametros, Simulacao
simulator/sim/cliente.py             ClienteApi
simulator/sim/__main__.py
web/                                 Next.js (ver Tasks 11–13)
```

---

### Task 1: Compose mínimo, config e `/saude`

**Files:**
- Create: `docker-compose.yml` (serviços `db` e `api` por enquanto), `infra/db/init.sql`, `api/Dockerfile`, `api/pyproject.toml`, `api/app/__init__.py`, `api/app/config.py`, `api/app/db.py`, `api/app/main.py`, `api/app/rotas_http/__init__.py`, `api/app/rotas_http/saude.py`
- Test: `api/tests/conftest.py`, `api/tests/test_config.py`, `api/tests/test_saude.py`

**Interfaces:**
- Produces: `from app.config import Settings, get_settings` (com `@lru_cache`); `from app.db import engine, SessionLocal, get_sessao` (dependência FastAPI que gera `Session`); `app.main:app`; fixture pytest `cliente` (TestClient) e `sessao` (Session no banco de teste, com rollback por teste).

Campos de `Settings` (nome → padrão), todos sobrescritos por variável de ambiente de mesmo nome em maiúsculas:
`database_url="postgresql+psycopg://rota:rota@db:5432/rota"`, `token_telemetria="dev-token"`, `seed=42`, `capacidade_rodotrem_t=55`, `capacidade_tritrem_t=45`, `velocidade_carregado_kmh=60`, `velocidade_vazio_kmh=70`, `variacao_velocidade=0.15`, `carregamento_min_min=40`, `carregamento_max_min=60`, `pesagem_min=5`, `descarga_min_min=25`, `descarga_max_min=35`, `vagas_descarga=3`, `intervalo_telemetria_s=30`, `fator_tempo=10`, `meta_diaria_t=4000`, `prob_evento_viagem=0.05`, `osrm_url="https://router.project-osrm.org"`, `fator_linha_reta=1.3`, `user_agent="rota-da-madeira/0.1 (+https://github.com/eupivotto/euca-track)"`, `fuso="America/Campo_Grande"`.

- [ ] **Step 1: Escrever `infra/db/init.sql`** criando o banco `rota_teste` e `CREATE EXTENSION IF NOT EXISTS postgis` em `rota` e em `rota_teste`. Montar em `/docker-entrypoint-initdb.d/` no serviço `db` (`postgis/postgis:16-3.4`, usuário/senha `rota`, healthcheck `pg_isready`). O serviço `api` monta `./api:/app`, depende do `db` saudável e roda `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- [ ] **Step 2: Escrever os testes**

```python
# test_config.py
def test_padroes_do_spec():
    s = Settings()
    assert (s.capacidade_rodotrem_t, s.capacidade_tritrem_t) == (55, 45)
    assert (s.velocidade_carregado_kmh, s.velocidade_vazio_kmh) == (60, 70)
    assert s.vagas_descarga == 3 and s.fator_tempo == 10 and s.meta_diaria_t == 4000
    assert s.seed == 42

def test_sobrescrita_por_ambiente(monkeypatch):
    monkeypatch.setenv("META_DIARIA_T", "5000")
    assert Settings().meta_diaria_t == 5000

# test_saude.py
def test_saude_com_banco(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200
    assert r.json() == {"api": "ok", "banco": "ok"}
```

`conftest.py`: aponta `DATABASE_URL` para `.../rota_teste` antes de importar o app; no início da sessão roda `alembic upgrade head` no banco de teste (até a Task 2 existir, nada a migrar); fixture `sessao` com conexão + transação revertida ao fim; `cliente` sobrescreve `get_sessao` para usar essa sessão.

- [ ] **Step 3:** `docker compose up -d --build db api` e `docker compose exec api pytest` → FAIL (módulos inexistentes).
- [ ] **Step 4: Implementar** `Settings`, `db.py` e `GET /saude` (executa `SELECT 1`; se falhar, responde 503 com `{"api": "ok", "banco": "erro"}`).
- [ ] **Step 5:** `docker compose exec api pytest` → 3 passed.
- [ ] **Step 6: Commit** `chore: compose com banco PostGIS e API com /saude`

---

### Task 2: Modelos e migração da Fase 1

**Files:**
- Create: `api/app/estados.py`, `api/app/modelos.py`, `api/alembic.ini`, `api/alembic/env.py`, `api/alembic/versions/0001_fase1.py`
- Test: `api/tests/test_migracao.py`

**Interfaces:**
- Produces: `Estado(StrEnum)` com `CARREGANDO, EM_TRANSITO_CARREGADO, FILA_PATIO, PESAGEM, DESCARGA, EM_TRANSITO_VAZIO`; `ESTADOS_CARREGADO = {EM_TRANSITO_CARREGADO, FILA_PATIO, PESAGEM, DESCARGA}`. Modelos (classes em PascalCase singular, `__tablename__` como no SPEC): `Fabrica(nome, geom POINT)`, `Fazenda(nome, area_ha, centro POINT, geom POLYGON)`, `Motorista(nome)`, `Caminhao(placa unique, tipo, capacidade_t, motorista_id, estado_atual nullable, viagem_atual_id nullable)`, `Rota(fazenda_id unique, geom LINESTRING, distancia_km, duracao_prevista_min)`, `Viagem(caminhao_id, fazenda_id, rota_id nullable, toneladas, inicio, fim nullable, eta_prevista nullable, status)`, `EventoViagem(viagem_id, estado, momento)`, `Posicao(caminhao_id, viagem_id nullable, geom POINT, velocidade_kmh, momento)`. Todos com `id` e `criado_em` (default `now()`). Geometrias `Geometry(..., srid=4326)`. Momentos `timestamptz`. Índice `ix_posicoes_caminhao_momento (caminhao_id, momento)`. `Viagem.status` ∈ `"EM_ANDAMENTO" | "CONCLUIDA"`.

- [ ] **Step 1: Escrever o teste**

```python
def test_tabelas_da_fase_1_existem(sessao):
    nomes = set(inspect(sessao.bind).get_table_names())
    assert {"fabrica", "fazendas", "motoristas", "caminhoes", "rotas",
            "viagens", "eventos_viagem", "posicoes"} <= nomes

def test_geometrias_em_4326(sessao):
    srid = sessao.execute(text("SELECT Find_SRID('public','fazendas','geom')")).scalar()
    assert srid == 4326

def test_indice_de_posicoes(sessao):
    idx = {i["name"] for i in inspect(sessao.bind).get_indexes("posicoes")}
    assert "ix_posicoes_caminhao_momento" in idx
```

- [ ] **Step 2:** `docker compose exec api pytest tests/test_migracao.py` → FAIL.
- [ ] **Step 3: Implementar** modelos e a migração `0001_fase1` escrita à mão (autogenerate do GeoAlchemy2 costuma duplicar índices espaciais; conferir). `env.py` lê a URL de `get_settings().database_url`.
- [ ] **Step 4:** `docker compose exec api alembic upgrade head` e `docker compose exec api pytest` → tudo passa.
- [ ] **Step 5: Commit** `feat: modelos e migração da fase 1`

---

### Task 3: Geometria das fazendas e seed reproduzível

**Files:**
- Create: `api/app/geo.py`, `api/app/seed.py`
- Test: `api/tests/test_geo.py`, `api/tests/test_seed.py`

**Interfaces:**
- Produces: `quadrado_fazenda(lat: float, lon: float, area_ha: float) -> list[tuple[float, float]]` (anel fechado de 5 pontos `(lon, lat)`); `distancia_km(a: tuple[float,float], b: tuple[float,float]) -> float` (haversine, entrada `(lon, lat)`); `gerar_placas(n: int, rng: random.Random) -> list[str]`; `gerar_nomes(n: int, rng: random.Random) -> list[str]`; `semear(sessao: Session, settings: Settings) -> None` (idempotente); `python -m app.seed` chama `semear` e faz commit.

Dados: fábrica e as 8 fazendas exatamente como na seção 3 do SPEC. 20 caminhões: os 12 primeiros `rodotrem` (55 t) e os 8 seguintes `tritrem` (45 t), capacidades lidas da config. Placas no padrão Mercosul `LLLNLNN` com prefixo `TLG` (ex.: `TLG1A23`), únicas. Nomes: combinação sorteada de listas fixas de nomes e sobrenomes comuns no Brasil, únicos. Caminhão *i* recebe o motorista *i*. `rng = random.Random(settings.seed)`.

- [ ] **Step 1: Escrever os testes**

```python
def test_quadrado_tem_a_area_informada():
    anel = quadrado_fazenda(-20.95, -51.95, 3200)
    area_m2 = shapely.ops.transform(para_utm_22s, Polygon(anel)).area  # pyproj EPSG:4326 -> EPSG:31982
    assert area_m2 / 10_000 == pytest.approx(3200, rel=0.01)
    assert anel[0] == anel[-1] and len(anel) == 5

def test_quadrado_centrado_no_ponto():
    c = Polygon(quadrado_fazenda(-20.95, -51.95, 3200)).centroid
    assert (c.x, c.y) == pytest.approx((-51.95, -20.95), abs=1e-6)

def test_distancia_conhecida():
    # fábrica -> Santa Luzia, em linha reta
    assert distancia_km((-51.76, -20.62), (-51.95, -20.95)) == pytest.approx(41.7, abs=0.5)

def test_placas_mercosul_unicas():
    placas = gerar_placas(20, random.Random(42))
    assert len(set(placas)) == 20
    assert all(re.fullmatch(r"TLG\d[A-Z]\d{2}", p) for p in placas)

def test_seed_reproduzivel(sessao):
    semear(sessao, Settings())
    primeira = sessao.scalars(select(Caminhao.placa).order_by(Caminhao.id)).all()
    nomes = sessao.scalars(select(Motorista.nome).order_by(Motorista.id)).all()
    assert primeira == gerar_placas(20, random.Random(42))
    assert len(set(nomes)) == 20

def test_seed_idempotente(sessao):
    semear(sessao, Settings()); semear(sessao, Settings())
    assert sessao.scalar(select(func.count()).select_from(Caminhao)) == 20
    assert sessao.scalar(select(func.count()).select_from(Fazenda)) == 8

def test_frota_12_rodotrem_8_tritrem(sessao):
    semear(sessao, Settings())
    tipos = Counter(sessao.scalars(select(Caminhao.tipo)).all())
    assert tipos == {"rodotrem": 12, "tritrem": 8}
```

Atenção: `gerar_placas` e `gerar_nomes` usam o mesmo `rng` em sequência dentro de `semear` (placas primeiro). O teste de reprodutibilidade compara só as placas com um `Random(42)` novo, então o sorteio das placas tem que vir primeiro.

- [ ] **Step 2:** `docker compose exec api pytest tests/test_geo.py tests/test_seed.py` → FAIL.
- [ ] **Step 3: Implementar** `geo.py` (meio lado em graus: `dlat = s/2/111_320`, `dlon = s/2/(111_320*cos(lat))`, com `s = sqrt(area_ha*10_000)`) e `seed.py` (sai cedo se já houver fábrica).
- [ ] **Step 4:** testes → PASS; rodar `docker compose exec api python -m app.seed` no banco de desenvolvimento.
- [ ] **Step 5: Commit** `feat: seed de fábrica, fazendas e frota com semente fixa`

---

### Task 4: Rotas pelo OSRM com fallback em linha reta

**Files:**
- Create: `api/tests/fixtures/osrm_faz01.json`, `api/app/osrm.py`, `api/app/scripts/__init__.py`, `api/app/scripts/gerar_rotas.py`
- Modify: `api/app/geo.py` (adicionar `linha_reta`)
- Test: `api/tests/test_osrm.py`, `api/tests/test_gerar_rotas.py`

**Interfaces:**
- Consumes: `distancia_km`, `Settings`, modelos `Fazenda`, `Fabrica`, `Rota`.
- Produces: `@dataclass RotaCalculada(coords: list[tuple[float,float]], distancia_km: float, duracao_min: float)`; `ler_resposta_osrm(dados: dict) -> RotaCalculada` (levanta `ValueError` se `code != "Ok"` ou sem rotas); `buscar_rota(cliente: httpx.Client, settings, origem, destino) -> RotaCalculada`; `linha_reta(origem, destino, fator: float, velocidade_kmh: float) -> RotaCalculada` (2 pontos, distância × fator, duração = distância ÷ velocidade × 60); `gerar_rotas(sessao, settings, cliente: httpx.Client, dormir=time.sleep) -> list[str]` (devolve os avisos). Geometria sempre no sentido fazenda → fábrica.

- [ ] **Step 1: Baixar a amostra real** (uma requisição só):

```bash
curl -A "rota-da-madeira/0.1 (+https://github.com/eupivotto/euca-track)" \
  "https://router.project-osrm.org/route/v1/driving/-51.95,-20.95;-51.76,-20.62?overview=full&geometries=geojson" \
  -o api/tests/fixtures/osrm_faz01.json
```

Abrir o arquivo e conferir os campos `code`, `routes[0].geometry.coordinates`, `routes[0].distance` (m), `routes[0].duration` (s). Se o formato for diferente disso, ajustar o parser ao arquivo, não o contrário. Se o servidor recusar, registrar no plano e no README como subir um OSRM próprio (seção 5 do SPEC) e seguir só com o fallback.

- [ ] **Step 2: Escrever os testes**

```python
def test_parser_contra_amostra_real():
    dados = json.loads((FIXTURES / "osrm_faz01.json").read_text())
    r = ler_resposta_osrm(dados)
    assert r.distancia_km == pytest.approx(dados["routes"][0]["distance"] / 1000)
    assert r.duracao_min == pytest.approx(dados["routes"][0]["duration"] / 60)
    assert len(r.coords) > 2
    assert r.coords[0] == pytest.approx((-51.95, -20.95), abs=0.05)

def test_parser_recusa_code_diferente_de_ok():
    with pytest.raises(ValueError):
        ler_resposta_osrm({"code": "NoRoute", "routes": []})

def test_buscar_rota_manda_user_agent(settings):
    vistos = []
    def handler(req):
        vistos.append(req); return httpx.Response(200, json=json.loads(AMOSTRA))
    buscar_rota(httpx.Client(transport=httpx.MockTransport(handler)), settings, (-51.95, -20.95), (-51.76, -20.62))
    assert vistos[0].headers["user-agent"] == settings.user_agent
    assert "overview=full" in str(vistos[0].url) and "geometries=geojson" in str(vistos[0].url)

def test_gerar_rotas_usa_linha_reta_quando_osrm_falha(sessao, settings):
    semear(sessao, settings)
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    avisos = gerar_rotas(sessao, settings, cliente, dormir=lambda s: None)
    rotas = sessao.scalars(select(Rota)).all()
    assert len(rotas) == 8 and len(avisos) == 8
    santa_luzia = next(r for r in rotas if r.fazenda_id == id_da("Fazenda Santa Luzia"))
    assert santa_luzia.distancia_km == pytest.approx(41.7 * 1.3, abs=0.7)

def test_gerar_rotas_uma_requisicao_por_vez_com_1s(sessao, settings):
    semear(sessao, settings)
    pausas = []
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=json.loads(AMOSTRA))))
    gerar_rotas(sessao, settings, cliente, dormir=pausas.append)
    assert pausas == [1.0] * 7  # entre 8 requisições

def test_gerar_rotas_idempotente(sessao, settings):
    # rodar duas vezes substitui, não duplica
    ...
    assert sessao.scalar(select(func.count()).select_from(Rota)) == 8
```

- [ ] **Step 3:** `docker compose exec api pytest tests/test_osrm.py tests/test_gerar_rotas.py` → FAIL.
- [ ] **Step 4: Implementar.** Qualquer `httpx.HTTPError`, status ≠ 200 ou `ValueError` do parser vira fallback com aviso `"Rota de <fazenda> em linha reta: <motivo>"`, impresso pelo `__main__`. Timeout do cliente: 20 s. `python -m app.scripts.gerar_rotas` cria o `httpx.Client` com o User-Agent e faz commit.
- [ ] **Step 5:** testes → PASS. Rodar `docker compose exec api python -m app.scripts.gerar_rotas` no banco de desenvolvimento e conferir 8 rotas.
- [ ] **Step 6: Commit** `feat: geração de rotas pelo OSRM com fallback em linha reta`

---

### Task 5: Endpoints de leitura

**Files:**
- Create: `api/app/rotas_http/mapa.py`, `api/app/rotas_http/frota.py`, `api/app/rotas_http/simulacao.py`
- Modify: `api/app/main.py`
- Test: `api/tests/test_leitura.py`

**Interfaces:**
- Consumes: modelos, `semear`, `ESTADOS_CARREGADO`.
- Produces (JSON exato):
  - `GET /fazendas` → `FeatureCollection`; fazendas com geometria `Polygon` e `properties {id, tipo: "fazenda", nome, area_ha}`; fábrica com `Point` e `properties {id, tipo: "fabrica", nome}`.
  - `GET /rotas` → `FeatureCollection` de `LineString` (fazenda → fábrica), `properties {id, fazenda_id, distancia_km, duracao_prevista_min}`.
  - `GET /caminhoes` → lista ordenada por `id` de `CaminhaoSaida {id, placa, tipo, capacidade_t, motorista, estado_atual: str|None, viagem_atual_id: int|None, fazenda_id: int|None, carga_t: float, posicao: {lon, lat, velocidade_kmh, momento}|None}`. `carga_t = capacidade_t` se `estado_atual ∈ ESTADOS_CARREGADO`, senão `0`. `fazenda_id` vem da viagem atual. `posicao` = última leitura do caminhão.
  - `GET /simulacao/parametros` → os campos de simulação da `Settings` (`seed`, capacidades, velocidades, `variacao_velocidade`, tempos de carregamento/pesagem/descarga, `vagas_descarga`, `intervalo_telemetria_s`, `fator_tempo`, `prob_evento_viagem`).
  - Função `montar_caminhao_saida(sessao, caminhao: Caminhao) -> dict`, reutilizada pela Task 6.

- [ ] **Step 1: Escrever os testes** (com `semear` e uma rota inserida à mão)

```python
def test_fazendas_geojson(cliente, semeado):
    fc = cliente.get("/fazendas").json()
    tipos = Counter(f["properties"]["tipo"] for f in fc["features"])
    assert tipos == {"fazenda": 8, "fabrica": 1}
    fab = next(f for f in fc["features"] if f["properties"]["tipo"] == "fabrica")
    assert fab["geometry"]["coordinates"] == pytest.approx([-51.76, -20.62])

def test_rotas_geojson(cliente, semeado_com_rota):
    f = cliente.get("/rotas").json()["features"][0]
    assert f["geometry"]["type"] == "LineString"
    assert set(f["properties"]) == {"id", "fazenda_id", "distancia_km", "duracao_prevista_min"}

def test_caminhoes_sem_telemetria(cliente, semeado):
    cs = cliente.get("/caminhoes").json()
    assert len(cs) == 20
    assert cs[0]["posicao"] is None and cs[0]["estado_atual"] is None and cs[0]["carga_t"] == 0

def test_parametros_para_o_simulador(cliente):
    p = cliente.get("/simulacao/parametros").json()
    assert p["vagas_descarga"] == 3 and p["fator_tempo"] == 10 and p["seed"] == 42
    assert "token_telemetria" not in p and "database_url" not in p
```

- [ ] **Step 2:** rodar → FAIL. **Step 3:** implementar (geometrias com `geoalchemy2.shape.to_shape` + `shapely.geometry.mapping`). **Step 4:** rodar → PASS.
- [ ] **Step 5: Commit** `feat: endpoints de fazendas, rotas, caminhões e parâmetros`

---

### Task 6: Telemetria, viagens e WebSocket

**Files:**
- Create: `api/app/tempo_real.py`, `api/app/telemetria.py`
- Modify: `api/app/rotas_http/frota.py` (POST `/telemetria`, WS `/ws/frota`)
- Test: `api/tests/test_telemetria.py`, `api/tests/test_tempo_real.py`

**Interfaces:**
- Consumes: `montar_caminhao_saida`, `Estado`, modelos.
- Produces:
  - `LeituraEntrada(BaseModel) {caminhao_id: int, fazenda_id: int, estado: Estado, lon: float, lat: float, velocidade_kmh: float, momento: datetime (com fuso)}`.
  - `registrar_leituras(sessao, leituras: list[LeituraEntrada]) -> list[int]` — devolve os ids dos caminhões atualizados; levanta `CaminhaoDesconhecido(caminhao_id)` antes de gravar qualquer coisa se algum id não existir.
  - `POST /telemetria` com header `X-Token`; corpo `list[LeituraEntrada]`; resposta `{"recebidas": n}`. Token errado → 401; `CaminhaoDesconhecido` → 422. Depois do commit, difunde `{"tipo": "caminhao", "caminhao": <CaminhaoSaida>}` para cada caminhão do lote.
  - `class Difusor` com `async conectar(ws)`, `desconectar(ws)`, `async difundir(mensagem: dict)`; instância única `difusor` em `tempo_real.py`. `WS /ws/frota` aceita, registra e fica lendo até desconectar.

Regras de `registrar_leituras`, por leitura, em ordem:
1. Grava `Posicao` (com `viagem_id` atual).
2. Se `estado == CARREGANDO` e (caminhão sem viagem atual **ou** `estado_atual != CARREGANDO`): fecha a viagem atual se houver (`fim = momento`, `status = "CONCLUIDA"`), cria nova `Viagem(fazenda_id, rota_id da fazenda, toneladas = capacidade_t, inicio = momento, status = "EM_ANDAMENTO")`, aponta `viagem_atual_id`.
3. Se o caminhão não tem viagem atual e o estado não é `CARREGANDO` (primeira leitura no meio do ciclo): cria a viagem do mesmo jeito, com `inicio = momento`.
4. Se `estado != estado_atual`: grava `EventoViagem(viagem_atual, estado, momento)` e atualiza `estado_atual`.

- [ ] **Step 1: Escrever os testes**

```python
def leitura(c, estado, minuto, fazenda=1): ...  # helper monta LeituraEntrada

def test_ciclo_completo_gera_viagem_e_eventos(sessao, semeado):
    estados = ["CARREGANDO", "EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM", "DESCARGA", "EM_TRANSITO_VAZIO", "CARREGANDO"]
    for i, e in enumerate(estados):
        registrar_leituras(sessao, [leitura(1, e, i * 10)])
    viagens = sessao.scalars(select(Viagem).order_by(Viagem.id)).all()
    assert [v.status for v in viagens] == ["CONCLUIDA", "EM_ANDAMENTO"]
    assert viagens[0].toneladas == 55
    assert len(viagens[0].eventos) == 6

def test_leituras_repetidas_nao_geram_eventos(sessao, semeado):
    for m in range(3):
        registrar_leituras(sessao, [leitura(1, "EM_TRANSITO_CARREGADO", m)])
    assert sessao.scalar(select(func.count()).select_from(EventoViagem)) == 1
    assert sessao.scalar(select(func.count()).select_from(Posicao)) == 3

def test_reinicio_mesmo_estado_nao_duplica_viagem(sessao, semeado):
    registrar_leituras(sessao, [leitura(1, "CARREGANDO", 0)])
    registrar_leituras(sessao, [leitura(1, "CARREGANDO", 1)])  # simulador reiniciado
    assert sessao.scalar(select(func.count()).select_from(Viagem)) == 1

def test_primeira_leitura_no_meio_do_ciclo_abre_viagem(sessao, semeado):
    registrar_leituras(sessao, [leitura(1, "FILA_PATIO", 0)])
    c = sessao.get(Caminhao, 1)
    assert c.viagem_atual_id is not None and c.estado_atual == "FILA_PATIO"

def test_token_errado_401(cliente, semeado):
    r = cliente.post("/telemetria", json=[], headers={"X-Token": "x"})
    assert r.status_code == 401

def test_caminhao_desconhecido_422_sem_gravar(cliente, semeado):
    corpo = [leitura_json(1, "CARREGANDO", 0), leitura_json(999, "CARREGANDO", 0)]
    r = cliente.post("/telemetria", json=corpo, headers={"X-Token": "dev-token"})
    assert r.status_code == 422
    assert cliente.get("/caminhoes").json()[0]["posicao"] is None

def test_websocket_recebe_caminhao(cliente, semeado):
    with cliente.websocket_connect("/ws/frota") as ws:
        cliente.post("/telemetria", json=[leitura_json(1, "CARREGANDO", 0)], headers={"X-Token": "dev-token"})
        msg = ws.receive_json()
    assert msg["tipo"] == "caminhao" and msg["caminhao"]["placa"].startswith("TLG")
    assert msg["caminhao"]["posicao"]["velocidade_kmh"] == 0

# test_tempo_real.py
async def test_broadcast_descarta_conexao_morta():
    viva, morta = WsFalso(), WsFalso(falha=True)
    d = Difusor(); await d.conectar(viva); await d.conectar(morta)
    await d.difundir({"tipo": "caminhao"})
    assert viva.recebidas == [{"tipo": "caminhao"}]
    assert morta not in d.conexoes
```

- [ ] **Step 2:** rodar → FAIL. **Step 3:** implementar. **Step 4:** rodar → PASS.
- [ ] **Step 5: Commit** `feat: recebimento de telemetria, ciclo de viagens e WebSocket da frota`

---

### Task 7: `GET /indicadores` mínimo (régua da meta)

**Files:**
- Create: `api/app/rotas_http/indicadores.py`
- Test: `api/tests/test_indicadores.py`

**Interfaces:**
- Produces: `GET /indicadores?inicio=&fim=` (ISO 8601, opcionais) → `{inicio, fim, agora, toneladas: float, viagens: int, meta_t: float}`. `agora = max(posicoes.momento)` ou `now()`. Sem parâmetros: `inicio` = 00:00 do dia de `agora` no fuso `America/Campo_Grande`, `fim` = `inicio + 1 dia`. `toneladas`/`viagens` = soma/contagem das viagens com evento `EM_TRANSITO_VAZIO` em `[inicio, fim)`. `meta_t = meta_diaria_t × dias do período`.

- [ ] **Step 1: Escrever os testes**

```python
def test_sem_dados(cliente):
    r = cliente.get("/indicadores").json()
    assert r["toneladas"] == 0 and r["viagens"] == 0 and r["meta_t"] == 4000

def test_conta_so_descargas_concluidas_no_dia(cliente, sessao, semeado):
    # caminhão 1 (55 t) completa uma descarga às 10h; caminhão 13 (45 t) ainda está em DESCARGA
    ...
    r = cliente.get("/indicadores").json()
    assert r["toneladas"] == 55 and r["viagens"] == 1

def test_dia_no_fuso_de_campo_grande(cliente, sessao, semeado):
    # descarga às 23:30 de Campo Grande (03:30 UTC do dia seguinte) conta no dia local
    ...
```

- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat: indicador de toneladas do dia para a régua da meta`

---

### Task 8: Simulador — máquina de estados e posição na rota

**Files:**
- Create: `simulator/pyproject.toml`, `simulator/Dockerfile`, `simulator/sim/__init__.py`, `simulator/sim/estados.py`, `simulator/sim/rota.py`
- Modify: `docker-compose.yml` (serviço `simulator`, monta `./simulator:/app`, comando provisório `sleep infinity` até a Task 10)
- Test: `simulator/tests/test_estados.py`, `simulator/tests/test_rota.py`

**Interfaces:**
- Produces: `Estado(StrEnum)` com os mesmos 6 valores da API; `proximo_estado(estado: Estado) -> Estado`; `comprimento_km(coords: list[tuple[float,float]]) -> float`; `ponto_na_linha(coords, km: float) -> tuple[float, float]` (limita a `[0, comprimento]`).

- [ ] **Step 1: Escrever os testes**

```python
def test_ciclo_na_ordem_do_spec():
    e, vistos = Estado.CARREGANDO, []
    for _ in range(6):
        vistos.append(e); e = proximo_estado(e)
    assert vistos == ["CARREGANDO", "EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM", "DESCARGA", "EM_TRANSITO_VAZIO"]
    assert e == Estado.CARREGANDO

LINHA = [(-52.0, -21.0), (-52.0, -20.9), (-51.9, -20.9)]

def test_inicio_meio_e_fim():
    total = comprimento_km(LINHA)
    assert ponto_na_linha(LINHA, 0) == LINHA[0]
    assert ponto_na_linha(LINHA, total) == pytest.approx(LINHA[-1])
    meio_primeiro = ponto_na_linha(LINHA, comprimento_km(LINHA[:2]) / 2)
    assert meio_primeiro == pytest.approx((-52.0, -20.95), abs=1e-4)

def test_fora_da_linha_fica_nas_pontas():
    assert ponto_na_linha(LINHA, -5) == LINHA[0]
    assert ponto_na_linha(LINHA, 10_000) == pytest.approx(LINHA[-1])

def test_segmento_de_comprimento_zero():
    assert ponto_na_linha([(-52, -21), (-52, -21), (-51.9, -21)], 1) is not None
```

- [ ] **Step 2:** `docker compose up -d --build simulator` e `docker compose exec simulator pytest` → FAIL. **Step 3:** implementar (haversine próprio; interpolação linear dentro do segmento). **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat: simulador com máquina de estados do ciclo e interpolação na rota`

---

### Task 9: Simulador — frota, pátio e relógio simulado

**Files:**
- Create: `simulator/sim/simulacao.py`
- Test: `simulator/tests/test_simulacao.py`

**Interfaces:**
- Consumes: `Estado`, `proximo_estado`, `comprimento_km`, `ponto_na_linha`.
- Produces:
  - `@dataclass Parametros` com os mesmos nomes de `GET /simulacao/parametros`; `Parametros.de_json(d: dict) -> Parametros` (ignora chaves extras).
  - `@dataclass FazendaSim(id: int, area_ha: float, coords_rota: list[tuple[float,float]])` (rota fazenda → fábrica).
  - `@dataclass CaminhaoSim(id: int, capacidade_t: float, estado: Estado, fazenda_id: int, km: float = 0, minutos_restantes: float = 0, velocidade_kmh: float = 0)`.
  - `Simulacao(parametros, fazendas: list[FazendaSim], caminhoes: list[tuple[int, float]], inicio: datetime)`; atributos `agora`, `caminhoes: list[CaminhaoSim]`, `fila: list[int]`; método `passo(minutos: float) -> list[dict]` devolvendo uma leitura por caminhão no formato de `LeituraEntrada` (`momento` em ISO 8601).

Regras:
- `rng = random.Random(parametros.seed)`. Início: para cada caminhão em ordem de id, `fazenda_id = rng.choice(ids das fazendas ordenados)`, estado `CARREGANDO`, `minutos_restantes = rng.uniform(carregamento_min_min, carregamento_max_min)`.
- Por passo: `agora += minutos`; para cada caminhão em ordem de id:
  - `CARREGANDO`, `PESAGEM`, `DESCARGA`: desconta `minutos_restantes`; ao zerar, avança. Durações: pesagem = `pesagem_min`, descarga = `uniform(descarga_min_min, descarga_max_min)`.
  - Em trânsito: `velocidade_kmh = base × rng.uniform(1 − variacao, 1 + variacao)` (base carregado 60, vazio 70); `km += velocidade × minutos / 60`; ao passar do comprimento, chega. Carregado chega → `FILA_PATIO` e entra no fim de `fila`. Vazio chega → `CARREGANDO`.
  - Ao entrar em `EM_TRANSITO_VAZIO`: sorteia a próxima fazenda com `rng.choices(ids, weights=áreas)`, `km = 0`.
  - Depois de processar todos, enquanto `len(em PESAGEM ou DESCARGA) < vagas_descarga` e `fila` não vazia: o primeiro da fila vai para `PESAGEM`.
- Posição: `CARREGANDO` no primeiro ponto da rota da fazenda; estados de pátio no último ponto (fábrica); carregado em `ponto_na_linha(coords, km)`; vazio na rota invertida. Velocidade 0 fora do trânsito.

- [ ] **Step 1: Escrever os testes** (fixture com 2 fazendas de rota curta em linha reta e parâmetros padrão)

```python
def test_mesma_semente_mesma_simulacao():
    a, b = nova_sim(), nova_sim()
    for _ in range(200):
        assert a.passo(0.5) == b.passo(0.5)

def test_todos_comecam_carregando_em_fazenda_sorteada():
    s = nova_sim()
    assert {c.estado for c in s.caminhoes} == {Estado.CARREGANDO}
    assert [c.fazenda_id for c in s.caminhoes] == [c.fazenda_id for c in nova_sim().caminhoes]

def test_caminhao_percorre_o_ciclo_completo():
    s = nova_sim(caminhoes=[(1, 55)])
    vistos = []
    for _ in range(2000):
        e = s.passo(0.5)[0]["estado"]
        if not vistos or vistos[-1] != e: vistos.append(e)
    assert vistos[:7] == ["CARREGANDO", "EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM", "DESCARGA", "EM_TRANSITO_VAZIO", "CARREGANDO"]

def test_quarto_caminhao_espera_na_fila():
    s = nova_sim(caminhoes=[(i, 55) for i in range(1, 5)])
    for i, c in enumerate(s.caminhoes):  # todos chegam juntos, em ordem de id
        c.estado, c.km = Estado.EM_TRANSITO_CARREGADO, 10_000
    s.passo(0.5)
    estados = {c.id: c.estado for c in s.caminhoes}
    assert [estados[i] for i in (1, 2, 3)] == [Estado.PESAGEM] * 3
    assert estados[4] == Estado.FILA_PATIO and s.fila == [4]

def test_velocidade_dentro_da_variacao():
    s = nova_sim(caminhoes=[(1, 55)])
    s.caminhoes[0].estado = Estado.EM_TRANSITO_CARREGADO
    v = s.passo(0.5)[0]["velocidade_kmh"]
    assert 60 * 0.85 <= v <= 60 * 1.15

def test_vazio_escolhe_fazenda_pela_area():
    # duas fazendas com áreas 1 e 9; em 1000 sorteios, ~90% vão para a maior
    ...
    assert 0.85 < proporcao_maior < 0.95

def test_relogio_avanca():
    s = nova_sim(); t0 = s.agora
    s.passo(0.5)
    assert s.agora - t0 == timedelta(seconds=30)
```

- [ ] **Step 2–4:** FAIL → implementar → PASS (`docker compose exec simulator pytest`).
- [ ] **Step 5: Commit** `feat: simulação da frota com pátio e relógio simulado`

---

### Task 10: Simulador — cliente da API e laço principal

**Files:**
- Create: `simulator/sim/cliente.py`, `simulator/sim/__main__.py`
- Modify: `docker-compose.yml` (comando `python -m sim`, envs `API_URL=http://api:8000`, `TOKEN_TELEMETRIA`, `depends_on: api`)
- Test: `simulator/tests/test_cliente.py`

**Interfaces:**
- Consumes: `Parametros`, `FazendaSim`, `Simulacao`, endpoints das Tasks 5 e 6.
- Produces: `ClienteApi(http: httpx.Client, token: str)` com `parametros() -> Parametros`, `fazendas() -> list[FazendaSim]` (junta `GET /fazendas` e `GET /rotas` por `fazenda_id`; fazendas sem rota ficam de fora), `caminhoes() -> list[tuple[int, float]]`, `enviar(leituras: list[dict]) -> bool` (True se 200; qualquer erro → registra no log e devolve False, nunca levanta).
- `__main__`: espera a API responder `/saude` e haver pelo menos uma rota (tenta a cada 5 s, avisando no log "Sem rotas no banco: rode python -m app.scripts.gerar_rotas"); cria `Simulacao(inicio=agora real)`; a cada `intervalo_telemetria_s / fator_tempo` s reais (3 s), chama `passo(intervalo_telemetria_s / 60)` e `enviar`.

- [ ] **Step 1: Escrever os testes** (com `httpx.MockTransport`)

```python
def test_fazendas_juntam_rota_e_area(): ...
    assert fs[0].area_ha == 3200 and fs[0].coords_rota[0] == (-51.95, -20.95)

def test_fazenda_sem_rota_fica_de_fora(): ...

def test_envio_manda_token():
    vistos = []
    cli = ClienteApi(cliente_mock(vistos, status=200), token="t")
    assert cli.enviar([{"caminhao_id": 1}]) is True
    assert vistos[0].headers["x-token"] == "t"

def test_envio_com_api_fora_nao_levanta():
    def cai(req): raise httpx.ConnectError("fora", request=req)
    cli = ClienteApi(httpx.Client(transport=httpx.MockTransport(cai), base_url="http://api"), token="t")
    assert cli.enviar([]) is False

def test_envio_com_erro_http_devolve_false(): ...  # 500 → False
```

- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5:** Verificação manual: `docker compose up -d --build`, `docker compose exec api python -m app.scripts.gerar_rotas` (se ainda não rodou), `docker compose logs -f simulator` sem erros por 1 min, e `curl localhost:8000/caminhoes` mostra os 20 com `posicao` e estados variados.
- [ ] **Step 6: Commit** `feat: laço do simulador enviando telemetria para a API`

---

### Task 11: Front — projeto, tokens e barra do topo

**Files:**
- Create: `web/` (Next.js 15 App Router, TS, Tailwind 4, `output: "standalone"`), `web/Dockerfile`, `web/vitest.config.ts`, `web/vitest.setup.ts`, `web/app/globals.css`, `web/app/layout.tsx`, `web/app/providers.tsx`, `web/components/BarraTopo.tsx`
- Modify: `docker-compose.yml` (serviço `web`, porta 3000, `NEXT_PUBLIC_API_URL=/api`)
- Test: `web/components/BarraTopo.test.tsx`

**Interfaces:**
- Produces: tokens do documento de layouts (seção 2) como variáveis CSS e no `@theme` do Tailwind, com os mesmos nomes (`--color-superficie`, `--color-primaria`, `--color-risco-nulo`… `--color-estado-carregando`…); fonte Instrument Sans via `next/font/google` na variável `--font-sans`; classe utilitária `.numeros { font-variant-numeric: tabular-nums }`. `<BarraTopo ativa: string />` com os itens `[{rotulo: "Ao vivo", href: "/"}]` na Fase 1 (lista em `web/lib/telas.ts`, para a Fase 2 só acrescentar). `<Providers>` com `QueryClientProvider`.

- [ ] **Step 1: Escrever os testes**

```tsx
it("mostra o selo de dados simulados", () => {
  render(<BarraTopo ativa="/" />);
  expect(screen.getByText("Dados simulados")).toBeInTheDocument();
});
it("marca a tela ativa", () => {
  render(<BarraTopo ativa="/" />);
  expect(screen.getByRole("link", { name: "Ao vivo" })).toHaveAttribute("aria-current", "page");
});
```

- [ ] **Step 2:** `cd web && npm test` → FAIL. **Step 3:** implementar conforme a seção 3 do documento de layouts (barra de 50 px, menu segmentado em pílula, selo em `atencao` sobre `atencao-fundo`). **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat: projeto web com tokens visuais e barra do topo`

---

### Task 12: Front — dados ao vivo e reconexão

**Files:**
- Create: `web/lib/tipos.ts`, `web/lib/api.ts`, `web/lib/estados.ts`, `web/lib/ordenarFrota.ts`, `web/lib/useFrotaAoVivo.ts`
- Test: `web/lib/estados.test.ts`, `web/lib/ordenarFrota.test.ts`, `web/lib/useFrotaAoVivo.test.ts`

**Interfaces:**
- Consumes: JSON das Tasks 5, 6 e 7.
- Produces:
  - `tipos.ts`: `Estado`, `Caminhao` (espelha `CaminhaoSaida`), `Indicadores`, `MensagemFrota = { tipo: "caminhao"; caminhao: Caminhao }`.
  - `api.ts`: `buscarCaminhoes()`, `buscarFazendas()`, `buscarRotas()`, `buscarIndicadores()`; base `process.env.NEXT_PUBLIC_API_URL ?? "/api"`; `urlWebSocket()` → `${ws|wss}://${location.host}/ws/frota` (ou `NEXT_PUBLIC_WS_URL`).
  - `estados.ts`: `ROTULO_ESTADO: Record<Estado, string>` e `MARCADOR_ESTADO: Record<Estado, { cor: string; contorno: boolean }>` com os valores da tabela "Estados do caminhão" do documento de layouts.
  - `ordenarFrota(cs: Caminhao[]): Caminhao[]` — na Fase 1: em trânsito carregado primeiro, depois pátio, carregando e vazio; empate por placa. (A Fase 2 põe os com alerta na frente.)
  - `useFrotaAoVivo(): { caminhoes: Caminhao[]; conexao: "conectando" | "conectado" | "reconectando" }` — carga inicial com TanStack Query (`buscarCaminhoes`), aplica cada `MensagemFrota` substituindo por `id`; reconecta com espera 1, 2, 4, 8 e 15 s (teto 15), zerando ao conectar.

- [ ] **Step 1: Escrever os testes**

```ts
it("rótulos em português de quem usa", () => {
  expect(ROTULO_ESTADO.FILA_PATIO).toBe("Fila do pátio");
  expect(ROTULO_ESTADO.EM_TRANSITO_VAZIO).toBe("Vazio");
  expect(MARCADOR_ESTADO.EM_TRANSITO_VAZIO.contorno).toBe(true);
});

it("ordena carregados primeiro e desempata por placa", () => {
  const r = ordenarFrota([c("TLG2", "CARREGANDO"), c("TLG9", "EM_TRANSITO_CARREGADO"), c("TLG1", "EM_TRANSITO_CARREGADO")]);
  expect(r.map((x) => x.placa)).toEqual(["TLG1", "TLG9", "TLG2"]);
});

// useFrotaAoVivo.test.ts — WebSocket falso global + fake timers
it("aplica mensagem do WebSocket sobre a carga inicial", async () => { ... });
it("reconecta com espera crescente até 15 s", async () => {
  // fecha a conexão 6 vezes; espera entre tentativas: 1000, 2000, 4000, 8000, 15000, 15000
});
it("mostra reconectando enquanto está fora", async () => { ... expect(result.current.conexao).toBe("reconectando") });
it("ignora mensagem de caminhão que chega antes da carga inicial sem quebrar", async () => { ... });
```

- [ ] **Step 2–4:** FAIL → implementar → PASS (`cd web && npm test`).
- [ ] **Step 5: Commit** `feat: dados da frota ao vivo com reconexão automática`

---

### Task 13: Front — tela Ao vivo

**Files:**
- Create: `web/lib/regua.ts`, `web/components/ReguaMeta.tsx`, `web/components/MapaAoVivo.tsx`, `web/components/TabelaFrota.tsx`, `web/components/DetalheCaminhao.tsx`, `web/components/AvisoConexao.tsx`, `web/app/page.tsx`
- Test: `web/lib/regua.test.ts`, `web/components/ReguaMeta.test.tsx`, `web/components/TabelaFrota.test.tsx`

**Interfaces:**
- Consumes: Tasks 11 e 12.
- Produces:
  - `esperadoAgora(meta_t: number, inicio: string, agora: string): number` = `meta_t × min(1, max(0, (agora − inicio) / 24 h))`; `fracao(valor, total)` limitada a `[0, 1]`.
  - `<ReguaMeta indicadores={Indicadores} />`: número principal "2.380 t", texto "entregues de 4.000 t", barra `primaria`, marcador `tinta` em `esperadoAgora`, diferença com sinal ("−95 t") rotulada "contra o esperado às HHhMM", escala 00h/06h/12h/18h/24h. Ciclo médio e espera no pátio aparecem como "—" na Fase 1. Números formatados em `pt-BR`.
  - `<MapaAoVivo fazendas rotas caminhoes selecionadoId onSelecionar />`: MapLibre com estilo `https://tiles.openfreemap.org/styles/positron`, centro na fábrica, fazendas em cinza neutro (`linha`) sem risco nesta fase, rotas em linha fina, fábrica em `tinta`, caminhões como camada `circle` com cor e contorno de `MARCADOR_ESTADO`; atribuição OSM visível; legenda compacta no canto inferior esquerdo.
  - `<TabelaFrota caminhoes onSelecionar />`: colunas Placa, Estado, Carga (sem coluna ETA na Fase 1); Carga "55 t" ou "—".
  - `<DetalheCaminhao caminhao onVoltar />`: placa, tipo, motorista, estado, carga e botão "Voltar para a frota", ocupando a coluna da tabela.
  - `<AvisoConexao conexao />`: "Reconectando…" discreto no topo quando `conexao === "reconectando"`.
  - `page.tsx`: layout da seção 4.1 do documento (régua no topo; grade ~57/43 de mapa e tabela; uma coluna abaixo de 1024 px). `indicadores` recarrega a cada 30 s.

- [ ] **Step 1: Escrever os testes**

```ts
it("esperado é proporcional ao horário do dia", () => {
  expect(esperadoAgora(4000, "2026-10-20T00:00:00-04:00", "2026-10-20T12:00:00-04:00")).toBe(2000);
  expect(esperadoAgora(4000, "2026-10-20T00:00:00-04:00", "2026-10-21T03:00:00-04:00")).toBe(4000);
});

it("régua mostra entregue, meta e diferença", () => {
  render(<ReguaMeta indicadores={{ toneladas: 2380, meta_t: 4000, viagens: 46,
    inicio: "2026-10-20T00:00:00-04:00", fim: "2026-10-21T00:00:00-04:00", agora: "2026-10-20T14:30:00-04:00" }} />);
  expect(screen.getByText("2.380 t")).toBeInTheDocument();
  expect(screen.getByText("entregues de 4.000 t")).toBeInTheDocument();
  expect(screen.getByText("−37 t")).toBeInTheDocument(); // 2380 − 2416,7
});

it("tabela mostra placa, estado legível e carga", () => {
  render(<TabelaFrota caminhoes={[c("TLG1A23", "FILA_PATIO", 55)]} onSelecionar={() => {}} />);
  expect(screen.getByRole("row", { name: /TLG1A23 Fila do pátio 55 t/ })).toBeInTheDocument();
});

it("clique na linha seleciona o caminhão", async () => { ... expect(onSelecionar).toHaveBeenCalledWith(1) });
```

O `MapaAoVivo` não tem teste unitário (MapLibre depende de WebGL); é verificado na Task 14.

- [ ] **Step 2–4:** FAIL → implementar → PASS.
- [ ] **Step 5: Commit** `feat: tela ao vivo com régua da meta, mapa e tabela da frota`

---

### Task 14: Nginx, um comando para subir tudo e verificação ponta a ponta

**Files:**
- Create: `infra/nginx/default.conf`
- Modify: `docker-compose.yml` (serviço `nginx` na porta 80: `/` → `web:3000`, `/api/` → `api:8000/` sem o prefixo, `/ws/` → `api:8000/ws/` com `Upgrade`/`Connection` e `proxy_read_timeout 1h`); `CLAUDE.md` (seção Comandos: acrescentar `docker compose exec api python -m app.scripts.gerar_rotas`)
- Create: `README.md` mínimo (como rodar, em português; o README completo é da Fase 4)

**Interfaces:**
- Consumes: todos os serviços.

- [ ] **Step 1:** Subir do zero: `docker compose down -v && docker compose up -d --build`, depois `docker compose exec api alembic upgrade head`, `docker compose exec api python -m app.seed`, `docker compose exec api python -m app.scripts.gerar_rotas`.
- [ ] **Step 2:** Rodar todas as suítes: `docker compose exec api pytest`, `docker compose exec simulator pytest`, `cd web && npm test` → todas passam.
- [ ] **Step 3:** Abrir `http://localhost/` no navegador (Playwright): os 20 caminhões aparecem e se movem; a régua mostra toneladas subindo ao longo do tempo; o selo "Dados simulados" e a atribuição do OSM estão visíveis; clicar num caminhão abre o detalhe. Tirar screenshot e comparar com `mapa-ao-vivo-v2.html`.
- [ ] **Step 4:** Reconexão: `docker compose restart api`; a tela mostra "Reconectando…" e volta sozinha a atualizar sem recarregar a página.
- [ ] **Step 5: Commit** `chore: nginx e subida completa com um comando`

---

## Critérios de pronto da Fase 1 (SPEC seção 12)

| critério | task |
|---|---|
| Compose com api, simulator, web, db e nginx sobe com um comando | 1, 8, 10, 11, 14 |
| Migrações e seed das seções 3 e 4 | 1, 2, 3 |
| Rotas geradas e salvas (seção 5) | 4 |
| Simulador percorre o ciclo completo e envia telemetria | 8, 9, 10 |
| Mapa ao vivo com 20 caminhões via WebSocket, com reconexão | 6, 12, 13, 14 |
| Testes: máquina de estados, interpolação, seed reproduzível | 3, 8, 9 |
