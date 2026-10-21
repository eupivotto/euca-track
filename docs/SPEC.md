# Rota da Madeira — Especificação

## 1. Objetivo

Painel web que mostra, em tempo real:

1. Caminhões levando madeira de fazendas de eucalipto até uma fábrica de celulose em Três Lagoas/MS, com fila de pátio, indicadores e alertas.
2. O perigo de incêndio de cada fazenda (Fórmula de Monte Alegre) e os focos de calor detectados pelo INPE perto das fazendas e das rotas.

Todos os dados operacionais são simulados. Dados de clima, focos e estradas são públicos.

## 2. Estrutura do repositório

```
rota-da-madeira/
  CLAUDE.md
  docker-compose.yml
  .github/workflows/ci.yml
  docs/SPEC.md
  api/            FastAPI, modelos, rotinas, regras, testes
  simulator/      simulador da frota, testes
  web/            Next.js: painel + app do motorista (PWA)
  infra/nginx/    configuração do Nginx
```

## 3. Dados de referência (seed)

Coordenadas fictícias, todas no lado sul-mato-grossense do rio Paraná. Nomes inventados.

### Fábrica

| id | nome | lat | lon |
|---|---|---|---|
| fab-01 | Fábrica Modelo Três Lagoas | -20.6200 | -51.7600 |

### Fazendas

| id | nome | lat | lon | area_ha |
|---|---|---|---|---|
| faz-01 | Fazenda Santa Luzia | -20.9500 | -51.9500 | 3200 |
| faz-02 | Fazenda Boa Vista | -20.4500 | -52.0500 | 2800 |
| faz-03 | Fazenda Três Irmãos | -21.1000 | -52.3000 | 4100 |
| faz-04 | Fazenda Água Limpa | -20.3000 | -51.8500 | 2500 |
| faz-05 | Fazenda Cervo | -20.8000 | -52.4000 | 3600 |
| faz-06 | Fazenda São Bento | -21.2500 | -51.9000 | 3000 |
| faz-07 | Fazenda Morada do Sol | -20.5500 | -52.5500 | 4400 |
| faz-08 | Fazenda Ribeirão | -20.1500 | -52.2500 | 2700 |

Cada fazenda vira um polígono simples (quadrado com a área informada, centrado no ponto) para os cálculos de distância. Essas fazendas fictícias servem às Fases 1 e 2; na Fase 3 elas são substituídas por áreas reais de eucalipto (seção 3.1).

### 3.1 Áreas reais de eucalipto (MapBiomas) — Fase 3

Objetivo: trocar os quadrados fictícios por polígonos de plantações florestais que existem de verdade na região, para que o risco de incêndio seja calculado sobre áreas reais.

- **Fonte:** MapBiomas Brasil, cobertura e uso da terra, asset do Earth Engine `projects/mapbiomas-public/assets/brazil/lulc/v1` (banda `classification`, 30 m, anos 1985 a 2024, propriedade `ano`). Licença CC-BY-4.0: citar "MapBiomas" no README e no mapa.
- **Classe:** `9` = Plantação florestal (Silvicultura). Confirmar o código na legenda da coleção usada antes de filtrar.
- **Ano:** o mais recente disponível (2024).
- **Recorte:** retângulo lat -21.6 a -19.8, lon -52.9 a -51.4, só no lado de MS.
- **Exportação:** script `api/app/scripts/exportar_mapbiomas.py` usando a API Python do Earth Engine (conta gratuita para uso não comercial). Alternativa sem Earth Engine: baixar o GeoTIFF da coleção pela plataforma do MapBiomas e processar localmente com rasterio.
- **Processamento** (`api/app/scripts/gerar_areas_eucalipto.py`):
  1. Filtrar pixels da classe 9 no recorte
  2. Vetorizar (rasterio.features.shapes ou gdal_polygonize)
  3. Unir polígonos vizinhos e simplificar a geometria (tolerância de ~30 m)
  4. Manter só áreas com 500 ha ou mais
  5. Escolher as 8 maiores áreas a até 150 km da fábrica, por distância em estrada quando houver rota
  6. Salvar em `fazendas` com nomes genéricos (`Área de eucalipto 01` a `08`), sem indicar proprietário ou empresa
- **Rotas:** depois da troca, rodar de novo `gerar_rotas.py` usando o ponto da área mais próximo de uma estrada como ponto de carregamento.
- **Testes:** com um raster pequeno em `api/tests/fixtures/`, testar filtro de classe, área mínima, limite de 8 áreas e nomes genéricos.
- **Selo na tela:** "Áreas de eucalipto: MapBiomas (2024). Frota e viagens: dados simulados."

### Frota

- 20 caminhões fictícios, placas no padrão Mercosul geradas pelo seed (ex.: `TLG1A23`), 12 do tipo `rodotrem` e 8 `tritrem`
- 20 motoristas com nomes fictícios
- Cada caminhão começa em uma fazenda sorteada com semente fixa (`SEED=42`), para a simulação ser reproduzível

## 4. Parâmetros da simulação (padrões, todos configuráveis)

| parâmetro | padrão |
|---|---|
| capacidade rodotrem (t) | 55 |
| capacidade tritrem (t) | 45 |
| velocidade média carregado (km/h) | 60 |
| velocidade média vazio (km/h) | 70 |
| variação de velocidade | ±15% |
| carregamento na fazenda (min) | 40 a 60 |
| pesagem na balança (min) | 5 |
| descarga (min) | 25 a 35 |
| capacidade de descarga simultânea no pátio | 3 caminhões |
| intervalo de envio de telemetria (s, tempo simulado) | 30 |
| fator de aceleração do tempo | 10 (1 min real = 10 min simulados) |
| meta diária de madeira (t) | 4000 |
| probabilidade de evento por viagem (parada não prevista) | 5% |

Ciclo de cada viagem (estados): `CARREGANDO → EM_TRANSITO_CARREGADO → FILA_PATIO → PESAGEM → DESCARGA → EM_TRANSITO_VAZIO → CARREGANDO`.

A fazenda de destino de cada viagem vazia é sorteada com peso pela área da fazenda.

## 5. Rotas

- Calcular uma vez, por script (`api/app/scripts/gerar_rotas.py`), a rota de cada fazenda até a fábrica usando OSRM (`/route/v1/driving/`, `overview=full`, `geometries=geojson`).
- Salvar na tabela `rotas`: linha (LINESTRING), distância (km) e duração prevista (min).
- Respeitar a política do servidor de demonstração: User-Agent identificando o projeto, uma requisição por vez, 1 s entre requisições. Se o servidor recusar, documentar como subir um OSRM próprio em Docker.
- Se uma rota não puder ser calculada, usar linha reta com fator 1,3 de distância e registrar aviso.

## 6. Alertas de logística (padrões configuráveis)

| alerta | regra |
|---|---|
| ATRASO | ETA atual maior que o previsto em mais de 20% |
| PARADA | velocidade < 5 km/h por mais de 15 min fora de fazenda, fábrica ou pátio (raio de 500 m) |
| DESVIO_ROTA | posição a mais de 500 m da linha da rota em uso, por 2 leituras seguidas |
| VELOCIDADE | velocidade acima de 80 km/h |
| FOCO_PROXIMO_ROTA | foco de calor das últimas 24 h a menos de 3 km da rota de uma viagem em andamento |

Um alerta do mesmo tipo para o mesmo caminhão não se repete enquanto estiver aberto.

ETA: distância restante na rota ÷ velocidade média das últimas 10 leituras (mínimo de 20 km/h para não estourar).

## 7. Risco de incêndio — Fórmula de Monte Alegre (FMA)

Fonte: Soares (1972), conforme descrito em Scientia Forestalis nº 87 (IPEF).

Cálculo diário por fazenda:

```
H = umidade relativa do ar às 13h (%), horário America/Campo_Grande
chuva = precipitação total do dia (mm)
parcela = 100 / H

se chuva <= 2.4:          FMA_hoje = FMA_ontem + parcela
se 2.5 <= chuva <= 4.9:   FMA_hoje = FMA_ontem * 0.7 + parcela
se 5.0 <= chuva <= 9.9:   FMA_hoje = FMA_ontem * 0.4 + parcela
se 10.0 <= chuva <= 12.9: FMA_hoje = FMA_ontem * 0.2 + parcela
se chuva > 12.9:          FMA_hoje = 0 (recomeça no dia seguinte)
```

Classes (padrão original, faixas configuráveis):

| classe | FMA |
|---|---|
| NULO | 0,0 a 1,0 |
| PEQUENO | 1,1 a 3,0 |
| MEDIO | 3,1 a 8,0 |
| ALTO | 8,1 a 20,0 |
| MUITO_ALTO | acima de 20,0 |

Testes obrigatórios: uma série de dias cobrindo cada faixa de chuva, o zeramento acima de 12,9 mm e cada classe, incluindo os limites exatos (1,0 / 1,1; 3,0 / 3,1; 8,0 / 8,1; 20,0 / 20,1). Para precipitação com uma casa decimal entre faixas (ex.: 2,45), arredondar para uma casa antes de classificar.

Clima: Open-Meteo, por coordenada da fazenda. Variáveis horárias `relative_humidity_2m`, `precipitation`, `wind_speed_10m`, `wind_direction_10m`, timezone `America/Campo_Grande`. Uma rotina diária grava em `clima_diario` (UR das 13h, chuva do dia, vento das 13h) e recalcula `risco_diario`. Backfill dos últimos 60 dias pela API de histórico na primeira execução.

## 8. Focos de calor (INPE)

- Fonte: Programa Queimadas do INPE, portal de dados abertos (seção "Dados para download").
- Antes de implementar, baixar um arquivo real, salvar em `api/tests/fixtures/` e escrever o parser contra ele (confirmar formato, colunas e frequência).
- Filtrar a região: retângulo lat -21.6 a -19.8, lon -52.9 a -51.4.
- Gravar em `focos_calor` sem duplicar (chave: lat, lon, data e hora, satélite).
- Rotina a cada 30 min. Alertas: `FOCO_PROXIMO_FAZENDA` (foco a menos de 5 km do polígono de uma fazenda) e `FOCO_PROXIMO_ROTA` (seção 6).
- Para cada alerta de foco, informar distância, horário da detecção e se o vento das 13h sopra do foco em direção à fazenda (diferença de ângulo menor que 45°).

## 9. Banco de dados

Tabelas (todas com `id`, `criado_em`):

- `fabrica` (nome, geom POINT)
- `fazendas` (nome, area_ha, centro POINT, geom POLYGON)
- `caminhoes` (placa, tipo, capacidade_t, motorista_id, estado_atual, viagem_atual_id)
- `motoristas` (nome)
- `rotas` (fazenda_id, geom LINESTRING, distancia_km, duracao_prevista_min)
- `viagens` (caminhao_id, fazenda_id, rota_id, toneladas, inicio, fim, eta_prevista, status)
- `eventos_viagem` (viagem_id, estado, momento)
- `posicoes` (caminhao_id, viagem_id, geom POINT, velocidade_kmh, momento) — índice por caminhão e momento
- `ocorrencias` (viagem_id, motorista_id, tipo, descricao, foto_url, momento)
- `focos_calor` (geom POINT, satelite, detectado_em, municipio)
- `clima_diario` (fazenda_id, data, ur_13h, chuva_mm, vento_kmh, vento_dir)
- `risco_diario` (fazenda_id, data, fma, classe)
- `alertas` (tipo, caminhao_id, fazenda_id, foco_id, mensagem, aberto_em, fechado_em, status)

SRID 4326 para armazenar; usar `geography` ou transformar para 31982/31983 (SIRGAS 2000 / UTM) quando calcular distâncias em metros.

## 10. API

| método e rota | descrição |
|---|---|
| GET /saude | status da API e do banco |
| GET /fazendas | fazendas e fábrica em GeoJSON |
| GET /caminhoes | estado atual de cada caminhão |
| WS /ws/frota | posições, mudanças de estado e alertas em tempo real |
| POST /telemetria | recebe posições do simulador (token simples em header) |
| GET /viagens/{id} | trajeto (GeoJSON) e eventos, para o replay |
| GET /patio/fila | fila atual e chegadas previstas nas próximas 2 h |
| GET /indicadores?inicio=&fim= | ciclo médio, viagens, toneladas, uso da frota, tempo de fila |
| POST /motorista/checkin | início/fim de carregamento |
| POST /ocorrencias | registro com foto (multipart) |
| GET /focos?horas=24 | focos recentes na região |
| GET /risco/fazendas?data= | FMA e classe por fazenda |
| GET /alertas?tipo=&status= | alertas abertos e fechados |

## 11. Telas

1. **Mapa ao vivo** — fazendas coloridas pela classe de risco do dia, fábrica, rotas, caminhões coloridos pelo estado, focos das últimas 24/48 h. Clique no caminhão mostra placa, estado, carga e ETA.
2. **Pátio** — fila atual, tempo de espera por caminhão, chegadas previstas nas próximas 2 h.
3. **Indicadores** — ciclo médio, viagens e toneladas do dia contra a meta, tempo médio de fila, uso da frota.
4. **Alertas** — lista filtrável, com link para o caminhão ou a fazenda no mapa.
5. **Risco** — FMA por fazenda nos últimos 30 dias, com dias de chuva marcados.
6. **Replay** — trajeto de uma viagem com linha do tempo de eventos.
7. **App do motorista (PWA)** — próxima viagem, check-in, ocorrência com foto, fila local quando estiver offline e envio ao reconectar.

Todas as telas: selo "Dados simulados" e atribuição do OpenStreetMap no mapa. A partir da Fase 3, também a atribuição do MapBiomas.

## 12. Fases e critérios de pronto

### Fase 1 — Base e mapa ao vivo
- Docker Compose com api, simulator, web, db (PostGIS) e nginx sobe com um comando
- Migrações e seed das seções 3 e 4
- Rotas geradas e salvas (seção 5)
- Simulador percorre o ciclo completo e envia telemetria
- Mapa ao vivo mostrando os 20 caminhões em movimento via WebSocket, com reconexão automática
- Testes: máquina de estados do ciclo, interpolação da posição na rota, seed reproduzível

### Fase 2 — Operação
- Pátio, indicadores, alertas de logística (seção 6) e replay
- App do motorista em PWA com modo offline
- Testes de cada regra de alerta, inclusive a não repetição de alerta aberto, e do ETA

### Fase 3 — Risco de incêndio
- Troca das fazendas fictícias pelas áreas reais de eucalipto do MapBiomas e novas rotas (seção 3.1)
- Importação de clima (com backfill) e de focos (seção 8)
- Cálculo da FMA com os testes obrigatórios da seção 7
- Camadas de risco e focos no mapa, tela de risco, alertas de foco
- Testes do parser de focos contra a amostra real em fixtures

### Fase 4 — Publicação
- CI no GitHub Actions rodando todos os testes
- Deploy em VPS com Nginx e HTTPS
- README com arquitetura, fontes de dados e atribuições, decisões técnicas, como rodar e um GIF ou vídeo da demonstração
