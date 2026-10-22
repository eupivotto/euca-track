# Fase 3A — Áreas reais de eucalipto (MapBiomas) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar as 8 fazendas fictícias (quadrados) por 8 áreas reais de silvicultura do MapBiomas 2024 perto de Três Lagoas, com rotas novas saindo do ponto da área mais próximo de uma estrada.

**Architecture:** Dois scripts rodados uma vez pelo desenvolvedor: `exportar_mapbiomas` lê só o recorte da região do GeoTIFF público do MapBiomas (leitura por trechos via `/vsicurl/`, sem Earth Engine) e `gerar_areas_eucalipto` vetoriza a classe 9 e grava `api/app/dados/areas_eucalipto.geojson`, que vai para o git. O seed lê esse GeoJSON; nada externo roda na subida. `gerar_rotas` passa a escolher o ponto de carregamento com o `/nearest` do OSRM sobre a borda da área.

**Tech Stack:** rasterio (novo), shapely 2, pyproj, numpy; OSRM público; IBGE (malha de MS); Next.js/MapLibre no front.

**Spec:** `docs/SPEC.md` (seções 3.1, 5, 11, 12 — Fase 3) e `docs/superpowers/specs/2026-10-20-layouts-design.md` (selo da Fase 3).

## Global Constraints

- Fonte: MapBiomas Brasil coleção 10, cobertura 2024, classe `9` = Silvicultura. Arquivo público: `https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_10/lulc/coverage/brazil_coverage_2024.tif` (EPSG:4326, pixel ~30 m, blocos 256×256). Licença CC-BY-4.0: citar "MapBiomas" no README e no mapa.
- Recorte: lat -21.6 a -19.8, lon -52.9 a -51.4, só no lado de MS (limite estadual do IBGE).
- Área mínima 500 ha; até 8 áreas; a até 150 km da fábrica; simplificação ~30 m.
- Nomes `Área de eucalipto 01` a `08`, sem proprietário ou empresa.
- Selo nas telas do painel: "Áreas de eucalipto: MapBiomas (2024). Frota e viagens: dados simulados."
- Nunca chamar OSRM, MapBiomas ou IBGE dentro de um request; parâmetros em `api/app/config.py`.
- Antes de escrever um parser de fonte externa, salvar amostra real em `api/tests/fixtures/`.
- Commits `tipo: descrição` em português; código sem acento; comentários em português.
- Medidas em metros em SIRGAS 2000 / UTM 22S (EPSG:31982).

## Review Focus

1. Área que vira MultiPolygon depois do corte por MS: guardar só a maior parte (a coluna é POLYGON) — teste na Task 1.
2. Área com buracos ou em forma de U: o `centro` precisa cair dentro dela (`representative_point`, não centroide) — teste na Task 1.
3. Menos de 8 áreas elegíveis: devolve as que houver, sem erro — teste na Task 1.
4. OSRM `/nearest` falhando em todos os pontos da borda: usa o centro e registra aviso, sem derrubar o script — teste na Task 3.
5. GeoJSON das áreas ausente na subida: o seed para com mensagem que diz como gerar — teste na Task 4.

---

### Task 1: Parâmetros e geração das áreas a partir do raster

**Files:**
- Modify: `api/pyproject.toml` (adicionar `rasterio>=1.4`, `numpy>=2`), `api/app/config.py`, `api/tests/test_config.py`
- Create: `api/app/areas.py`, `api/tests/test_areas.py`, `api/tests/fixtures/criar_raster_teste.py`, `api/tests/fixtures/raster_teste.tif`

**Interfaces:**
- Produces:
  - config: `regiao_lat_min=-21.6`, `regiao_lat_max=-19.8`, `regiao_lon_min=-52.9`, `regiao_lon_max=-51.4` (a 3B reusa para os focos), `mapbiomas_url` (URL acima), `mapbiomas_classe=9`, `areas_min_ha=500`, `areas_raio_km=150`, `areas_maximo=8`, `areas_fecho_m=60`, `areas_simplificar_m=30`.
  - `api/app/areas.py`:
    - `@dataclass AreaEucalipto(nome: str, area_ha: float, geom: Polygon, centro: Point)` (EPSG:4326)
    - `vetorizar(dados: np.ndarray, transform: Affine, classe: int) -> list[Polygon]` (4326)
    - `areas_eucalipto(pedacos: list[Polygon], limite: Polygon, fabrica: tuple[float, float], settings: Settings) -> list[AreaEucalipto]`
    - `para_geojson(areas: list[AreaEucalipto]) -> dict` (FeatureCollection; properties `nome`, `area_ha`, `centro: [lon, lat]`)

O que `areas_eucalipto` faz, em ordem: projeta para 31982; une vizinhos por fechamento (`buffer(+fecho)`, `unary_union`, `buffer(-fecho)`); corta pelo `limite`; de cada MultiPolygon fica a maior parte; simplifica (`simplificar_m`); mantém área ≥ `areas_min_ha` e distância em linha reta até a fábrica ≤ `areas_raio_km`; ordena por área decrescente; corta em `areas_maximo`; volta para 4326; nomeia `Área de eucalipto 01`… na ordem; `centro = representative_point()`.

- [ ] **Step 1: Raster de teste.** `criar_raster_teste.py` gera `raster_teste.tif` (uint8, EPSG:4326, pixel 0,003°, origem perto de -20.6/-52.0) com: 9 blocos 9×9 da classe 9 de tamanhos distintos (todos ≥ 500 ha); um bloco 3×3 da classe 9 (< 500 ha); dois blocos 5×5 da classe 9 separados por uma coluna de outra classe (juntos ≥ 500 ha, sozinhos < 500 ha); um bloco 9×9 da classe 15 (pastagem). Rodar o script e commitar o `.tif`.

- [ ] **Step 2: Testes que falham** em `test_areas.py`, lendo o fixture com rasterio e usando um `limite` sintético (retângulo que cobre o raster menos uma faixa a leste) e a fábrica no meio do raster:
  - `test_vetorizar_so_a_classe_pedida` — nenhum polígono sobre o bloco da classe 15.
  - `test_area_minima_descarta_pedaco_pequeno` — o bloco 3×3 não aparece.
  - `test_vizinhos_separados_por_um_pixel_viram_uma_area` — os dois blocos 5×5 viram uma área ≥ 500 ha.
  - `test_no_maximo_8_maiores_em_ordem` — 8 áreas, `area_ha` decrescente.
  - `test_nomes_genericos` — `["Área de eucalipto 01", …, "Área de eucalipto 08"]`.
  - `test_corte_pelo_limite_guarda_a_maior_parte` — um bloco cortado pelo limite em duas partes vira um `Polygon` só, dentro do limite.
  - `test_raio_da_fabrica` — com a fábrica longe (ex.: `areas_raio_km=1`), nenhuma área.
  - `test_menos_de_8_devolve_as_que_houver` — `areas_maximo=8` com 3 elegíveis devolve 3.
  - `test_centro_dentro_da_area_em_U` — um polígono em U passado direto: `centro.within(geom)`.
  - `test_para_geojson` — 8 features, `properties.nome` e `area_ha`, geometria `Polygon`.
  - Em `test_config.py`: os valores padrão listados acima.

- [ ] **Step 3: Rodar e ver falhar.** `docker compose build api preparo && docker compose up -d api` e `docker compose exec api pytest tests/test_areas.py tests/test_config.py -q` — Expected: FAIL por `ModuleNotFoundError: app.areas` (e os campos ausentes da config).

- [ ] **Step 4: Implementar** `areas.py` e os campos da config.

- [ ] **Step 5: Rodar.** Mesmo comando — Expected: PASS.

- [ ] **Step 6: Commit** `feat: geração das áreas de eucalipto a partir do raster do MapBiomas`.

### Task 2: Recorte do MapBiomas, limite de MS e o GeoJSON das áreas

**Files:**
- Create: `api/app/scripts/exportar_mapbiomas.py`, `api/app/scripts/gerar_areas_eucalipto.py`, `api/app/dados/limite_ms.geojson`, `api/app/dados/areas_eucalipto.geojson`, `api/tests/test_scripts_areas.py`
- Modify: `.gitignore` (`api/dados/`)

**Interfaces:**
- Consumes: `vetorizar`, `areas_eucalipto`, `para_geojson` (Task 1).
- Produces:
  - `exportar_mapbiomas.ler_recorte(origem: str, settings: Settings) -> tuple[np.ndarray, Affine, dict]` (`origem` é caminho local ou `/vsicurl/<url>`; janela `from_bounds` do recorte da config).
  - CLI `python -m app.scripts.exportar_mapbiomas [saida]` grava `api/dados/mapbiomas_2024_recorte.tif` (fora do git, ~3 MB).
  - CLI `python -m app.scripts.gerar_areas_eucalipto [raster]` grava `api/app/dados/areas_eucalipto.geojson` e imprime nome, área e distância de cada área.
  - `api/app/dados/limite_ms.geojson`: malha de MS do IBGE (`https://servicodados.ibge.gov.br/api/v3/malhas/estados/50?formato=application/vnd.geo%2Bjson&qualidade=intermediaria`), salva como veio (~11 KB).

- [ ] **Step 1: Testes que falham** em `test_scripts_areas.py`:
  - `test_ler_recorte_devolve_so_a_janela` — `ler_recorte` no `raster_teste.tif` com um recorte menor (Settings com `regiao_*` sobrescritos) devolve array com a forma da janela e `transform` cuja origem é o canto noroeste do recorte (tolerância de 1 pixel).
  - `test_limite_ms_e_um_poligono_que_contem_tres_lagoas` — o arquivo do IBGE carrega como polígono que contém (-51.70, -20.75) e não contém Castilho/SP (-51.49, -20.87).
- [ ] **Step 2: Rodar e ver falhar** — `docker compose exec api pytest tests/test_scripts_areas.py -q`. Expected: FAIL (módulo e arquivo ausentes).
- [ ] **Step 3: Implementar** os dois scripts e baixar `limite_ms.geojson`.
- [ ] **Step 4: Rodar** — Expected: PASS.
- [ ] **Step 5: Gerar os dados reais.** `docker compose exec api python -m app.scripts.exportar_mapbiomas` (Expected: recorte ~6679×5566 em menos de 1 min) e `docker compose exec api python -m app.scripts.gerar_areas_eucalipto` (Expected: 8 áreas, a maior perto de 30 mil ha, todas ≤ 150 km). Confirmar no texto da legenda da coleção 10 que 9 é "Silvicultura" e registrar a fonte no README na Task 6.
- [ ] **Step 6: Commit** `feat: scripts de recorte do MapBiomas e áreas de eucalipto geradas` (inclui os dois GeoJSON).

### Task 3: Ponto de carregamento na estrada mais próxima da área

**Files:**
- Modify: `api/app/osrm.py`, `api/app/scripts/gerar_rotas.py`, `api/tests/test_osrm.py`, `api/tests/test_gerar_rotas.py`
- Create: `api/tests/fixtures/osrm_nearest.json` (resposta real de `/nearest/v1/driving/{lon},{lat}` para um ponto de borda de uma área real)

**Interfaces:**
- Produces:
  - `osrm.ler_resposta_nearest(dados: dict) -> tuple[tuple[float, float], float]` (ponto na estrada, distância em m; `ValueError` se `code != "Ok"`).
  - `osrm.buscar_mais_proximo(cliente, settings, ponto: tuple[float, float]) -> tuple[tuple[float, float], float]`.
  - `gerar_rotas.pontos_borda(geom: Polygon, quantidade: int = 12) -> list[tuple[float, float]]` (pontos igualmente espaçados no anel externo).
  - `gerar_rotas.ponto_carregamento(cliente, settings, geom, centro, dormir) -> tuple[tuple[float, float], str | None]` — consulta `/nearest` para cada ponto da borda (1 s entre requisições), devolve o ponto de estrada com menor distância; se todas falharem, devolve o centro e um aviso.
  - `gerar_rotas` usa esse ponto como origem da rota (a linha começa nele).

- [ ] **Step 1: Salvar a amostra real** de `/nearest` em `osrm_nearest.json` (User-Agent do projeto).
- [ ] **Step 2: Testes que falham:**
  - `test_ler_resposta_nearest` contra a amostra: ponto e distância batem com o JSON.
  - `test_pontos_borda_no_anel` — 12 pontos, todos a < 1 m do anel externo de um quadrado.
  - `test_ponto_carregamento_escolhe_a_estrada_mais_perto` — cliente falso (`httpx.MockTransport`) com distâncias diferentes por ponto; escolhe a menor; `dormir` chamado entre requisições.
  - `test_ponto_carregamento_sem_osrm_usa_o_centro` — todas as respostas 500: devolve o centro e um aviso com o nome da área.
  - `test_rota_comeca_no_ponto_de_carregamento` — em `gerar_rotas` com transporte falso, a primeira coordenada da rota salva é o ponto escolhido.
- [ ] **Step 3: Rodar e ver falhar** — `docker compose exec api pytest tests/test_osrm.py tests/test_gerar_rotas.py -q`. Expected: FAIL nos testes novos.
- [ ] **Step 4: Implementar.**
- [ ] **Step 5: Rodar** — Expected: PASS (inclusive os testes antigos de `gerar_rotas`, ajustados ao `/nearest` no transporte falso).
- [ ] **Step 6: Commit** `feat: rota sai do ponto da área mais próximo de uma estrada`.

### Task 4: Seed com as áreas reais

**Files:**
- Modify: `api/app/seed.py`, `api/tests/test_seed.py` (e qualquer teste que dependa dos nomes fictícios via seed)

**Interfaces:**
- Consumes: `api/app/dados/areas_eucalipto.geojson` (Task 2).
- Produces: `seed.carregar_areas(caminho: Path = ARQUIVO_AREAS) -> list[AreaEucalipto]`; `semear` grava as fazendas a partir dele. Sai a lista `FAZENDAS` fictícia; `quadrado_fazenda` só fica se algum teste ou código ainda usar.

- [ ] **Step 1: Testes que falham:**
  - `test_fazendas_sao_as_areas_do_mapbiomas` — 8 fazendas, nomes `Área de eucalipto 01..08`, nenhuma começando com "Fazenda".
  - `test_area_ha_bate_com_o_poligono` — `area_ha` dentro de 1% da área de `ST_Area(geom::geography)/1e4`.
  - `test_centro_dentro_da_area` — `ST_Within(centro, geom)` para todas.
  - `test_areas_a_ate_150_km_da_fabrica`.
  - `test_sem_arquivo_de_areas_explica_como_gerar` — `carregar_areas(Path("nao_existe.geojson"))` levanta erro cuja mensagem cita `gerar_areas_eucalipto`.
  - Remover `test_fazendas_do_spec`.
- [ ] **Step 2: Rodar e ver falhar** — `docker compose exec api pytest tests/test_seed.py -q`. Expected: FAIL nos novos.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Suíte inteira da API** — `docker compose exec api pytest -q`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: seed usa as áreas reais de eucalipto`.

### Task 5: Painel com o selo da Fase 3 e a atribuição do MapBiomas

**Files:**
- Modify: `web/components/BarraTopo.tsx` e teste, `web/components/MapaAoVivo.tsx`, `web/components/MapaReplay.tsx`, `web/lib/` (onde as fontes do mapa forem montadas)

**Interfaces:**
- Produces: constante `ATRIBUICAO_MAPBIOMAS = "Áreas de eucalipto © MapBiomas (CC-BY-4.0)"` usada como `attribution` da fonte `fazendas` nos dois mapas.

- [ ] **Step 1: Testes que falham:**
  - `BarraTopo` mostra "Áreas de eucalipto: MapBiomas (2024). Frota e viagens: dados simulados." (o selo pode quebrar em duas linhas em tela estreita; sem `whitespace-nowrap`).
  - Teste da função que monta a fonte `fazendas` (extrair se ainda não existir) — tem `attribution` com "MapBiomas".
- [ ] **Step 2: Rodar e ver falhar** — `cd web && npx vitest run components/BarraTopo.test.tsx <teste da fonte>`. Expected: FAIL.
- [ ] **Step 3: Implementar**; o mapa ao vivo enquadra fazendas e fábrica no primeiro carregamento (`fitBounds`), já que as áreas vão até 150 km.
- [ ] **Step 4: Rodar** `npm test`, `npx tsc --noEmit`, `npm run lint` — Expected: tudo limpo.
- [ ] **Step 5: Commit** `feat: selo e atribuição do MapBiomas no painel`.

### Task 6: Banco novo, rotas reais e documentação

**Files:**
- Modify: `README.md`, `CLAUDE.md` (seção Comandos)

- [ ] **Step 1: Zerar o banco de desenvolvimento** (só dados simulados): `docker compose down`, `docker volume rm eucatrack_dados_db`, `docker compose up -d --build`. Expected: o `preparo` grava as 8 áreas e gera 8 rotas pelo OSRM, sem aviso de linha reta (ou com aviso explicado).
- [ ] **Step 2: Conferir no navegador** (largura de desktop e de celular): áreas reais no mapa, rotas saindo delas, caminhões rodando o ciclo, selo novo, atribuição MapBiomas e OpenStreetMap visíveis. Depois de ~10 min reais, nenhum alerta PARADA aberto para caminhão carregando (o ponto de carregamento fica a menos de 500 m da área).
- [ ] **Step 3: README** — fontes e atribuições (MapBiomas coleção 10, CC-BY-4.0, classe 9 com link da legenda; IBGE malha estadual), como regerar as áreas (os dois scripts) e que trocar as áreas exige zerar o banco. `CLAUDE.md` — os dois comandos novos.
- [ ] **Step 4: Suítes** — API, simulador e web. Expected: tudo verde.
- [ ] **Step 5: Commit** `docs: áreas reais de eucalipto no README`.
