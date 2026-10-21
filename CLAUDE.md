# Rota da Madeira

Painel de operações florestais em tempo real: logística de madeira (fazendas → fábrica) e risco de incêndio por fazenda. Projeto de portfólio com dados públicos e dados simulados. Especificação completa em `docs/SPEC.md` — leia antes de qualquer tarefa.

## Regras do projeto

- **TDD first.** Para toda regra de negócio (ciclo da viagem, alertas, FMA, ETA), escreva o teste antes da implementação. Rode os testes ao fim de cada passo.
- **Trabalhe por fase.** Siga as fases do `docs/SPEC.md` na ordem. Ao terminar uma fase, pare, resuma o que foi feito e espere aprovação antes de começar a próxima.
- **Nada de dados reais de empresa.** Frota, motoristas e viagens são fictícios. As fazendas começam fictícias e, na Fase 3, viram áreas reais de eucalipto do MapBiomas, sempre com nomes genéricos e sem indicar proprietário ou empresa. Toda tela com dados simulados exibe o selo "Dados simulados".
- **Fontes externas:** nunca chame OSRM, Open-Meteo ou INPE dentro de um request do usuário. Busque em rotinas agendadas ou scripts, salve no banco e sirva do banco.
- **Antes de escrever um importador externo,** baixe uma amostra real, salve em `tests/fixtures/` e escreva o parser contra essa amostra. Não suponha formato de arquivo.
- **Configuração em um lugar só:** parâmetros de simulação e limites de alerta ficam em `api/app/config.py` (pydantic-settings), com valores padrão do SPEC e sobrescrita por variável de ambiente.
- **Commits pequenos** com mensagem em português, no formato `tipo: descrição` (feat, fix, test, docs, chore, refactor).
- **Idioma:** código, nomes de tabelas e de variáveis em português sem acento (ex.: `fazendas`, `risco_diario`), comentários e README em português.

## Stack

- `api/` — Python 3.12, FastAPI, SQLAlchemy 2 + GeoAlchemy2, Alembic, pydantic-settings, APScheduler, pytest
- `simulator/` — Python 3.12, httpx, pytest
- `web/` — Next.js (App Router) + TypeScript, Tailwind, MapLibre GL, TanStack Query, Vitest + Testing Library
- Banco — PostgreSQL com PostGIS (imagem `postgis/postgis`)
- Infra — Docker Compose, Nginx, GitHub Actions

## Comandos (manter atualizados conforme o projeto evolui)

- Subir tudo: `docker compose up -d --build`
- Testes da API: `docker compose exec api pytest`
- Testes do simulador: `docker compose exec simulator pytest`
- Testes do front: `cd web && npm test`
- Migrações: `docker compose exec api alembic upgrade head`
- Seed: `docker compose exec api python -m app.seed`
