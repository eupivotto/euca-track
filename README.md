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
