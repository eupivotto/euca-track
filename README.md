# Rota da Madeira

Painel de operações florestais em tempo real: caminhões levando madeira das fazendas até a fábrica, acompanhados ao vivo no mapa, com a meta do dia no topo.

Projeto de portfólio. Frota, motoristas, viagens e fazendas são **dados simulados**; nenhum dado é de empresa real. A especificação completa está em `docs/SPEC.md`.

## Subir

Precisa de Docker.

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
docker compose exec api python -m app.scripts.gerar_rotas
```

Depois abra http://localhost/. O simulador espera as rotas existirem e começa sozinho.

O script de rotas consulta o servidor público do OSRM uma vez por fazenda; se ele não responder, usa uma linha reta como aproximação e avisa.

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
