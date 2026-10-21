# Rota da Madeira

Painel de operações florestais em tempo real: caminhões levando madeira das fazendas até a fábrica, acompanhados ao vivo no mapa, com a meta do dia no topo.

Projeto de portfólio. Frota, motoristas, viagens e fazendas são **dados simulados**; nenhum dado é de empresa real. A especificação completa está em `docs/SPEC.md`.

## Subir

Precisa de Docker.

```bash
docker compose up -d --build
```

Depois abra http://localhost/. Na subida, o serviço `preparo` aplica as migrações, cria os dados simulados e calcula as rotas que faltarem; a API só começa depois dele, e o simulador começa sozinho em seguida.

As rotas vêm do servidor público do OSRM, uma consulta por fazenda, só na primeira subida. Se ele não responder, cada rota vira uma linha reta aproximada (com aviso em `docker compose logs preparo`). Para recalcular todas: `docker compose exec api python -m app.scripts.gerar_rotas`.

## Telas

- **Ao vivo** — meta do dia, mapa e tabela da frota. Caminhões com alerta aberto vêm primeiro na tabela, destacados; os em trânsito mostram a chegada prevista (ETA).
- **Pátio** — fila atual em ordem de chegada, vagas de descarga ocupadas e caminhões carregados que chegam nas próximas 2 h.
- **Indicadores** — toneladas, viagens, ciclo médio, fila média e uso da frota, para hoje, 7 ou 30 dias.
- **Alertas** — abertos e fechados, com "Ver no mapa" para o caminhão.
- **Replay** — o trajeto de uma viagem com a linha do tempo dos eventos.

## Alertas de logística

A API avalia cada leitura de telemetria e abre um alerta por tipo e caminhão, que fecha sozinho quando a condição passa:

- **Atraso** — o ETA atual passa da chegada prevista do trecho em mais de 20%.
- **Parada** — abaixo de 5 km/h por mais de 15 min na estrada, a mais de 500 m de fazenda ou fábrica.
- **Desvio de rota** — duas leituras seguidas a mais de 500 m da rota.
- **Velocidade** — acima de 80 km/h.

Os limites ficam em `api/app/config.py`. O simulador faz uma parada não prevista em 5% das viagens; para ver alertas sem esperar, suba com todas as viagens parando e depois volte ao normal:

```bash
PROB_EVENTO_VIAGEM=1 docker compose up -d
docker compose up -d
```

## Testes

```bash
docker compose exec api pytest
docker compose exec simulator pytest
cd web && npm test
```

## Estrutura

- `api/` — FastAPI, PostGIS, telemetria e WebSocket da frota
- `simulator/` — simula os 20 caminhões e envia telemetria para a API
- `web/` — Next.js com MapLibre (mapa base OpenFreeMap, dados © OpenStreetMap)
- `infra/` — Nginx e inicialização do banco
