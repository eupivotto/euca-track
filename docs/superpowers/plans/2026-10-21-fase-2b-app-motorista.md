# Fase 2B — App do motorista (PWA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** App do motorista em `/motorista` (PWA): a pessoa assume um dos 20 caminhões simulados, vê a próxima viagem, faz o check-in de início e fim de carregamento (que comanda a saída do caminhão no simulador) e registra ocorrências com foto, com fila local quando estiver offline.

**Architecture:** A API guarda quem está "assumido" (`caminhoes.assumido_ate`, renovado pelo app a cada minuto) e os check-ins da viagem. Na resposta de `POST /telemetria` ela devolve `assumidos` (o simulador congela o carregamento deles) e `liberados` (caminhões em `CARREGANDO` com check-in de fim: o simulador os faz sair). O app manda check-ins e ocorrências sempre por uma fila local em IndexedDB, com `id_local` (UUID) para a API não duplicar um envio repetido. O painel mostra a marca "App" no caminhão e as ocorrências da viagem no detalhe.

**Tech Stack:** FastAPI + python-multipart, SQLAlchemy 2, Alembic, pytest; simulador Python + httpx; Next.js 15 (App Router, `app/manifest.ts`), TanStack Query 5, IndexedDB, Vitest + Testing Library + fake-indexeddb.

**Spec:** `docs/SPEC.md` (seções 9, 10 e 11.7; Fase 2). Decisão da pessoa dona do projeto: o app assume um caminhão; o simulador continua movendo-o pela rota, mas só o tira do carregamento quando o app faz o check-in de fim.

## Global Constraints

- TDD: teste antes da regra; rodar os testes ao fim de cada passo.
- Código, tabelas e variáveis em português sem acento; comentários e README em português.
- Toda tela com dados simulados exibe o selo "Dados simulados" (inclusive `/motorista`).
- Configuração em `api/app/config.py` (pydantic-settings), sobrescrita por variável de ambiente.
- Nenhuma chamada a OSRM/Open-Meteo/INPE dentro de request.
- Commits pequenos em português, `tipo: descrição`, com o trailer da sessão.
- Tabelas do SPEC: `ocorrencias (viagem_id, motorista_id, tipo, descricao, foto_url, momento)`; rotas `POST /motorista/checkin` e `POST /ocorrencias` (multipart).
- Momentos gravados pela API (check-in, ocorrência, assumir) usam o relógio simulado (`operacao.agora_simulado`), não o relógio do celular.
- Visual: o mesmo sistema do painel (tokens de `web/app/globals.css`, Instrument Sans, tema claro, "sem cara de IA"); o app é pensado para 390 px de largura, alvos de toque de pelo menos 44 px.

## Decisões deste plano (a pessoa revisa)

- **Assumir expira:** `assumido_ate = agora_simulado + motorista_assumir_min` (padrão 60 min simulados = 6 min reais). O app renova a cada 60 s reais enquanto está aberto. Fechou o app, o simulador retoma o caminhão em até 6 min reais.
- **Check-in exige caminhão assumido.** `INICIO_CARREGAMENTO` só em `CARREGANDO` e uma vez por viagem; `FIM_CARREGAMENTO` só depois do início, uma vez por viagem. Fora disso: 409 com mensagem em português.
- **Liberação não depende de estar assumido:** se o check-in de fim foi feito, o caminhão sai mesmo que a posse tenha expirado logo depois.
- **Dois celulares podem assumir o mesmo caminhão** (não há login); vale a última ação. Projeto de demonstração.
- **Momento do que veio da fila offline** é o da chegada na API (relógio simulado). O app não tenta converter o horário do celular para o tempo simulado.
- **Foto:** JPEG, PNG ou WebP, até `foto_max_mb` = 10 MB; gravada em `pasta_fotos` (volume Docker `fotos`). Sem compressão no navegador.
- **Service worker só em contexto seguro** (HTTPS ou `localhost`). Pelo IP da rede local (`http://192.168.0.111/`) o celular não registra o service worker: a fila offline funciona com a página aberta, mas abrir o app sem rede e instalar como app só funcionam com HTTPS (Fase 4, ou `tailscale serve`).
- **"Próxima viagem":** fazenda de destino da última leitura (`caminhoes.fazenda_destino_id`, nova coluna), já que no trecho vazio a `viagem_atual` ainda é a anterior.

## Review Focus

1. Resposta do envio perdida e reenviada pela fila: a API devolve o mesmo registro (200) pelo `id_local`, sem duplicar check-in nem ocorrência.
2. A posse expirou enquanto o celular estava offline: o check-in pendente volta 409, sai da fila e o app mostra por quê, em vez de tentar para sempre.
3. Foto grande demais ou de tipo errado: 413/415 com mensagem clara, e o Nginx não corta antes (limite do corpo acima de 10 MB).
4. Simulador falando com uma API que responde sem `assumidos`/`liberados` (ou com erro): segue como hoje, sem quebrar.
5. Caminhão liberado num lote e o simulador ainda com o carregamento "congelado": sai no passo seguinte, uma vez só, e a viagem seguinte começa sem o check-in da anterior.

---

### Task 1: Migração, modelos e configuração

**Files:**
- Create: `api/alembic/versions/0003_motorista.py`
- Modify: `api/app/modelos.py`, `api/app/config.py`, `api/app/telemetria.py`
- Test: `api/tests/test_migracao.py`, `api/tests/test_config.py`, `api/tests/test_telemetria.py`

**Interfaces:**
- Produces:
  - Tabela `checkins` (`id`, `criado_em`, `viagem_id` FK, `caminhao_id` FK, `acao` String(30), `momento`, `id_local` String(36) unique) e modelo `Checkin`.
  - Tabela `ocorrencias` (`id`, `criado_em`, `viagem_id` FK nullable, `motorista_id` FK, `caminhao_id` FK, `tipo` String(20), `descricao` String(500), `foto_url` String(200) nullable, `momento`, `id_local` String(36) unique) e modelo `Ocorrencia`. `caminhao_id` não está no SPEC: entra para listar por caminhão sem viagem.
  - `caminhoes.assumido_ate` (timestamptz nullable) e `caminhoes.fazenda_destino_id` (FK fazendas, nullable); relação `Caminhao.fazenda_destino`.
  - Settings: `motorista_assumir_min: float = 60`, `pasta_fotos: str = "/dados/fotos"`, `foto_max_mb: float = 10`.
  - `registrar_leituras` grava `caminhao.fazenda_destino_id = leitura.fazenda_id` em toda leitura.

- [ ] **Step 1: Testes que falham**
  - `test_migracao_cria_checkins_e_ocorrencias`: colunas acima existem; `id_local` tem restrição única nas duas tabelas; `caminhoes` tem `assumido_ate` e `fazenda_destino_id`.
  - `test_config.py`: padrões `motorista_assumir_min == 60`, `pasta_fotos == "/dados/fotos"`, `foto_max_mb == 10`.
  - `test_leitura_grava_fazenda_de_destino`: leitura `EM_TRANSITO_VAZIO` com `outra_fazenda` → `caminhao.fazenda_destino_id == ids["outra_fazenda"]` enquanto `viagem_atual.fazenda_id` continua a anterior.
- [ ] **Step 2:** `docker compose exec api pytest tests/test_migracao.py tests/test_config.py tests/test_telemetria.py -q` → FAIL (colunas e campos inexistentes).
- [ ] **Step 3:** Migração 0003 (com `downgrade`), modelos, settings e a linha em `registrar_leituras`.
- [ ] **Step 4:** Mesmo comando → PASS; depois `docker compose exec api pytest -q` → tudo verde.
- [ ] **Step 5:** `git commit -m "feat: tabelas de check-in e ocorrências e posse do caminhão pelo app"`

### Task 2: Regras do motorista (puras)

**Files:**
- Create: `api/app/motorista.py`
- Test: `api/tests/test_motorista.py`

**Interfaces:**
- Produces:
  - `class Acao(StrEnum)`: `INICIO_CARREGAMENTO`, `FIM_CARREGAMENTO`.
  - `class Passo(StrEnum)`: `INDO_PARA_FAZENDA`, `INICIAR_CARREGAMENTO`, `FINALIZAR_CARREGAMENTO`, `AGUARDANDO_SAIDA`, `INDO_PARA_FABRICA`, `NA_FABRICA`.
  - `erro_checkin(estado: str | None, assumido: bool, feitas: set[Acao], acao: Acao) -> str | None` — `None` se pode; senão a mensagem do 409.
  - `passo_atual(estado: str | None, feitas: set[Acao]) -> Passo`.

- [ ] **Step 1: Testes que falham** (cada um com a mensagem exata):
  - não assumido → `"Assuma o caminhão antes do check-in"`.
  - `INICIO_CARREGAMENTO` fora de `CARREGANDO` → `"O caminhão não está na fazenda"`.
  - `INICIO` repetido → `"O carregamento já foi iniciado"`.
  - `FIM` sem início → `"Inicie o carregamento antes de finalizar"`.
  - `FIM` repetido → `"O carregamento já foi finalizado"`.
  - caminhos válidos → `None`.
  - `passo_atual`: `EM_TRANSITO_VAZIO` → `INDO_PARA_FAZENDA`; `CARREGANDO` sem nada → `INICIAR_CARREGAMENTO`; com início → `FINALIZAR_CARREGAMENTO`; com fim → `AGUARDANDO_SAIDA`; `EM_TRANSITO_CARREGADO` → `INDO_PARA_FABRICA`; `FILA_PATIO`/`PESAGEM`/`DESCARGA` → `NA_FABRICA`; `None` → `INDO_PARA_FAZENDA`.
- [ ] **Step 2:** `docker compose exec api pytest tests/test_motorista.py -q` → FAIL (módulo não existe).
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Mesmo comando → PASS.
- [ ] **Step 5:** `git commit -m "feat: regras de check-in e passo do motorista"`

### Task 3: Rotas `/motorista` (painel, assumir, soltar, check-in)

**Files:**
- Create: `api/app/rotas_http/motorista.py`
- Modify: `api/app/main.py`, `api/app/rotas_http/frota.py` (`montar_caminhao_saida` ganha `assumido`)
- Test: `api/tests/test_rotas_motorista.py`

**Interfaces:**
- Consumes: Task 1 (modelos, settings), Task 2 (`erro_checkin`, `passo_atual`), `operacao.agora_simulado`, `tempo_real.difusor`, `frota.montar_caminhao_saida`.
- Produces:
  - `GET /motorista/caminhoes/{id}` → `PainelMotorista`: `{caminhao: <saída de /caminhoes>, assumido: bool, assumido_ate: str|null, passo: Passo, destino: {fazenda_id, nome, distancia_km}|null, viagem_id: int|null, checkins: [{acao, momento}], agora: str}`. 404 `"Caminhão não encontrado"`.
  - `POST /motorista/assumir` `{caminhao_id}` → `PainelMotorista`; define `assumido_ate`; difunde `{"tipo":"caminhao",...}`.
  - `POST /motorista/soltar` `{caminhao_id}` → `PainelMotorista`; limpa `assumido_ate`; difunde.
  - `POST /motorista/checkin` `{caminhao_id, acao, id_local}` → 201 `{id, acao, momento, viagem_id}`; mesmo `id_local` de novo → 200 com o mesmo registro; regra violada → 409 `{"detail": <mensagem da Task 2>}`; difunde o caminhão.
  - `montar_caminhao_saida(...)["assumido"]: bool` (`assumido_ate > agora_simulado`).
  - Helper `assumido(caminhao, agora) -> bool` em `app/motorista.py`.

- [ ] **Step 1: Testes que falham**
  - `test_painel_de_caminhao_inexistente_404`.
  - `test_assumir_define_posse_pelo_relogio_simulado`: com uma leitura em `INICIO` (10h00 UTC), `assumido_ate == INICIO + 60 min` e `/caminhoes` mostra `assumido: true`.
  - `test_posse_expira`: leitura nova em `INICIO + 61 min` → `assumido: false`.
  - `test_soltar_devolve_ao_simulador`.
  - `test_checkin_inicio_e_fim_na_fazenda`: leitura `CARREGANDO`, assumir, `INICIO` 201, `FIM` 201; o painel mostra `passo == "AGUARDANDO_SAIDA"` e os dois check-ins.
  - `test_checkin_repetido_pelo_id_local_nao_duplica` (Review Focus 1): mesmo corpo duas vezes → 201 e 200, um registro só.
  - `test_checkin_sem_posse_409` (Review Focus 2) com `detail == "Assuma o caminhão antes do check-in"`.
  - `test_destino_e_a_fazenda_da_ultima_leitura`: leitura `EM_TRANSITO_VAZIO` para `outra_fazenda` → `destino.fazenda_id == ids["outra_fazenda"]` e `passo == "INDO_PARA_FAZENDA"`.
  - `test_checkin_difunde_o_caminhao`: WebSocket recebe `{"tipo":"caminhao"}` com `assumido: true`. Usar o padrão de `test_websocket_recebe_alerta` (conectar antes do POST).
- [ ] **Step 2:** `docker compose exec api pytest tests/test_rotas_motorista.py -q` → FAIL (404 nas rotas).
- [ ] **Step 3:** Implementar. Rotas `async` com o trabalho de banco em `run_in_threadpool`, como `POST /telemetria`.
- [ ] **Step 4:** Mesmo comando → PASS; suíte inteira verde.
- [ ] **Step 5:** `git commit -m "feat: rotas do motorista para assumir caminhão e fazer check-in"`

### Task 4: Telemetria devolve assumidos e liberados

**Files:**
- Modify: `api/app/rotas_http/frota.py`, `api/app/motorista.py`
- Test: `api/tests/test_rotas_motorista.py`

**Interfaces:**
- Produces: `POST /telemetria` → `{"recebidas": n, "assumidos": [ids], "liberados": [ids]}`, calculados depois de gravar o lote.
  - `assumidos`: `assumido_ate > maior momento do lote`.
  - `liberados`: `estado_atual == CARREGANDO` e há `Checkin(FIM_CARREGAMENTO)` para `viagem_atual_id`, com ou sem posse.
  - Função `controle_simulador(sessao, agora) -> tuple[list[int], list[int]]`.

- [ ] **Step 1: Testes que falham**
  - `test_telemetria_devolve_assumidos`.
  - `test_telemetria_libera_quem_finalizou_o_carregamento`.
  - `test_viagem_seguinte_nao_herda_a_liberacao` (Review Focus 5): depois de `EM_TRANSITO_CARREGADO`… `EM_TRANSITO_VAZIO` e `CARREGANDO` de novo (viagem nova), o caminhão não está em `liberados`.
- [ ] **Step 2:** `docker compose exec api pytest tests/test_rotas_motorista.py -q` → FAIL (`KeyError`/chaves ausentes).
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** PASS; suíte inteira verde (testes antigos que conferem `{"recebidas": n}` exatamente passam a conferir só essa chave).
- [ ] **Step 5:** `git commit -m "feat: telemetria informa ao simulador quem está com o app"`

### Task 5: Ocorrências com foto

**Files:**
- Create: `api/app/rotas_http/ocorrencias.py`
- Modify: `api/pyproject.toml` (`python-multipart>=0.0.9`), `api/app/main.py`, `infra/nginx/default.conf` (`client_max_body_size 12m;` em `/api/`), `docker-compose.yml` (volume `fotos:/dados/fotos` na `api`)
- Test: `api/tests/test_ocorrencias.py`

**Interfaces:**
- Produces:
  - `TIPOS_OCORRENCIA = {"MECANICA": "Problema mecânico", "PNEU": "Pneu", "ACIDENTE": "Acidente", "ESTRADA": "Problema na estrada", "OUTRO": "Outro"}`.
  - `POST /ocorrencias` multipart: `caminhao_id`, `tipo`, `descricao` (até 500), `id_local`, `foto` opcional → 201 `OcorrenciaSaida`; `id_local` repetido → 200 com a mesma; tipo inválido → 422; foto de outro tipo → 415 `"A foto precisa ser JPEG, PNG ou WebP"`; acima do limite → 413 `"A foto passa de 10 MB"`; caminhão inexistente → 404. `viagem_id` e `motorista_id` vêm do caminhão; `momento` do relógio simulado. Difunde `{"tipo":"ocorrencia","ocorrencia": OcorrenciaSaida}`.
  - `OcorrenciaSaida = {id, caminhao_id, placa, viagem_id, tipo, descricao, foto_url: str|null, momento}`, com `foto_url = "/ocorrencias/{id}/foto"` (relativa à API).
  - `GET /ocorrencias?caminhao_id=&viagem_id=&limite=50` → mais recentes primeiro.
  - `GET /ocorrencias/{id}/foto` → o arquivo com o `media_type` gravado; 404 se não houver.
  - A foto vai para `settings.pasta_fotos/<uuid>.<ext>`; a coluna `foto_url` guarda só o nome do arquivo.
- Nos testes, sobrescrever `get_settings` com `pasta_fotos=tmp_path` via `app.dependency_overrides`.

- [ ] **Step 1: Testes que falham**: criação com foto (arquivo existe e GET da foto devolve os mesmos bytes); sem foto; `id_local` repetido (Review Focus 1); 415; 413 (com `foto_max_mb=0.001`); listagem filtrada por caminhão; WebSocket recebe `ocorrencia`.
- [ ] **Step 2:** Rebuild da imagem (`docker compose build api && docker compose up -d api`), depois `docker compose exec api pytest tests/test_ocorrencias.py -q` → FAIL (404).
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** PASS; suíte inteira verde; `docker compose up -d nginx` e `docker compose restart nginx`; `curl -F` de uma imagem de 2 MB via `http://localhost/api/ocorrencias` → 201 (Review Focus 3).
- [ ] **Step 5:** `git commit -m "feat: ocorrências com foto"`

### Task 6: Simulador obedece ao app

**Files:**
- Modify: `simulator/sim/simulacao.py`, `simulator/sim/cliente.py`, `simulator/sim/__main__.py`
- Test: `simulator/tests/test_simulacao.py`, `simulator/tests/test_cliente.py`

**Interfaces:**
- Consumes: resposta da Task 4.
- Produces:
  - `CaminhaoSim.assumido: bool = False`, `CaminhaoSim.liberado: bool = False`.
  - `Simulacao.controlar(assumidos: set[int], liberados: set[int]) -> None` — atribui os dois flags de cada caminhão.
  - Em `_avancar`, para `CARREGANDO`: `liberado` → sai já (`_entrar(EM_TRANSITO_CARREGADO)`) e zera o flag; senão, `assumido` → não desconta o tempo; senão, como hoje.
  - `ClienteApi.enviar(leituras) -> dict | None` (`None` em falha); `__main__` chama `controlar(set(r.get("assumidos", [])), set(r.get("liberados", [])))` quando há resposta.

- [ ] **Step 1: Testes que falham**
  - `test_assumido_nao_termina_o_carregamento_sozinho`: assumido, avançar 200 min → continua `CARREGANDO`.
  - `test_liberado_sai_no_passo_seguinte_uma_vez`: depois de `controlar(set(), {id})`, o próximo `passo` mostra `EM_TRANSITO_CARREGADO`; a viagem seguinte, de novo em `CARREGANDO`, não sai antes do tempo.
  - `test_solto_volta_a_contar_o_tempo`.
  - `test_enviar_devolve_a_resposta` e `test_enviar_sem_chaves_novas` (Review Focus 4: resposta `{"recebidas": 2}` → `controlar(set(), set())`, sem erro).
- [ ] **Step 2:** `docker compose exec simulator pytest -q` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** PASS (os testes antigos de `enviar` que esperam `True`/`False` passam a esperar dict/`None`).
- [ ] **Step 5:** `git commit -m "feat: simulador segura o carregamento do caminhão assumido pelo app"`

### Task 7: Fila offline e cliente do motorista (web/lib)

**Files:**
- Create: `web/lib/motorista.ts`, `web/lib/filaOffline.ts`, `web/lib/armazemIndexedDb.ts`
- Modify: `web/lib/tipos.ts`, `web/lib/api.ts`, `web/package.json` (dev: `fake-indexeddb`)
- Test: `web/lib/motorista.test.ts`, `web/lib/filaOffline.test.ts`, `web/lib/armazemIndexedDb.test.ts`

**Interfaces:**
- Produces:
  - Tipos `Passo`, `AcaoCheckin`, `PainelMotorista`, `TipoOcorrencia`, `Ocorrencia`; `Caminhao.assumido: boolean`; `MensagemFrota` ganha `{tipo:"ocorrencia"; ocorrencia: Ocorrencia}`.
  - `api.ts`: `buscarPainelMotorista(id)`, `assumirCaminhao(id)`, `soltarCaminhao(id)`, `buscarOcorrencias({caminhaoId?, viagemId?})`, `urlApi(caminho)`.
  - `motorista.ts`: `ROTULO_PASSO: Record<Passo, string>` ("Indo para a fazenda", "Cheguei na fazenda", …), `ROTULO_OCORRENCIA`, `acaoDoPasso(passo) -> AcaoCheckin | null`, `TEXTO_BOTAO: Record<AcaoCheckin,string>` = `{INICIO_CARREGAMENTO: "Iniciar carregamento", FIM_CARREGAMENTO: "Finalizar carregamento"}`.
  - `filaOffline.ts`:
    - `type Pendente = { id_local: string; tipo: "checkin" | "ocorrencia"; criado_em: string; dados: Record<string, string | number>; foto?: Blob }`.
    - `interface Armazem { listar(): Promise<Pendente[]>; guardar(p: Pendente): Promise<void>; remover(id_local: string): Promise<void> }`.
    - `armazemEmMemoria(): Armazem` (testes).
    - `type Resultado = { enviados: string[]; recusados: { id_local: string; motivo: string }[]; parou: boolean }`.
    - `enviarPendentes(armazem, enviar: (p) => Promise<Response>) -> Promise<Resultado>`: em ordem de `criado_em`; 2xx remove; 4xx remove e anota o `detail` como motivo (Review Focus 2); 5xx ou falha de rede para e mantém o resto (`parou: true`).
    - `enviarPendente(p): Promise<Response>`: check-in vira JSON; ocorrência vira `FormData` com a foto.
  - `armazemIndexedDb(nome = "rota-motorista"): Armazem`.

- [ ] **Step 1: Testes que falham**: `acaoDoPasso`; fila mantém a ordem; 409 sai da fila com o motivo; erro de rede para sem perder nada; 5xx para; `enviarPendente` monta `FormData` com a foto; o armazém IndexedDB (com `import "fake-indexeddb/auto"`) guarda, lista em ordem e remove, inclusive `Blob`.
- [ ] **Step 2:** `cd web && npx vitest run lib/motorista.test.ts lib/filaOffline.test.ts lib/armazemIndexedDb.test.ts` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** PASS; `npm test`, `npx tsc --noEmit` e `npm run lint` limpos.
- [ ] **Step 5:** `git commit -m "feat: fila offline e cliente do app do motorista"`

### Task 8: Tela do motorista — escolha, viagem e check-in

**Files:**
- Create: `web/app/motorista/page.tsx`, `web/components/motorista/EscolhaCaminhao.tsx`, `web/components/motorista/PainelViagem.tsx`, `web/components/motorista/BarraMotorista.tsx`, `web/lib/useFilaOffline.ts`
- Test: `web/components/motorista/EscolhaCaminhao.test.tsx`, `web/components/motorista/PainelViagem.test.tsx`, `web/components/motorista/BarraMotorista.test.tsx`

**Interfaces:**
- Consumes: Task 7.
- Produces:
  - `EscolhaCaminhao({ caminhoes, onEscolher })`: lista (placa, motorista, estado), botões de 44 px ou mais.
  - `PainelViagem({ painel, pendentes, onCheckin })`: destino (fazenda e km), estado, ETA; um botão grande com o texto de `TEXTO_BOTAO` só quando `acaoDoPasso` não for nulo; com um check-in daquela ação na fila, o botão vira "Enviando quando houver rede" e fica desabilitado.
  - `BarraMotorista({ placa, online, pendentes, onTrocar })`: placa, selo "Dados simulados", "Sem rede · N pendentes" ou "N pendentes", e "Trocar de caminhão".
  - `useFilaOffline()`: `{ pendentes, recusados, enfileirar(p), enviarAgora() }`; tenta enviar ao enfileirar, no evento `online` e a cada 15 s; recusados aparecem como aviso fechável.
  - A página guarda o caminhão escolhido em `localStorage` (`rota-motorista:caminhao`, em try/catch), chama `assumirCaminhao` ao escolher e a cada 60 s, consulta o painel a cada 10 s, e `soltarCaminhao` em "Trocar de caminhão".

- [ ] **Step 1: Testes que falham**:
  - Escolher chama `onEscolher(id)`.
  - Passo `INICIAR_CARREGAMENTO` mostra "Iniciar carregamento", e o clique chama `onCheckin("INICIO_CARREGAMENTO")`.
  - `INDO_PARA_FABRICA` não mostra botão de check-in.
  - Pendente da mesma ação desabilita o botão.
  - A barra mostra "Sem rede · 2 pendentes" offline e o selo "Dados simulados".
- [ ] **Step 2:** `cd web && npx vitest run components/motorista` → FAIL.
- [ ] **Step 3:** Implementar. Layout próprio, sem `BarraTopo` do painel.
- [ ] **Step 4:** PASS; tsc e lint limpos; no navegador a 390 px (`http://localhost/motorista`), assumir um caminhão e ver a marca no painel.
- [ ] **Step 5:** `git commit -m "feat: tela do motorista com viagem e check-in"`

### Task 9: Ocorrência com foto no app

**Files:**
- Create: `web/components/motorista/FormOcorrencia.tsx`
- Modify: `web/app/motorista/page.tsx`
- Test: `web/components/motorista/FormOcorrencia.test.tsx`

**Interfaces:**
- Produces: `FormOcorrencia({ onEnviar, onCancelar })` com tipo (pílulas, uma obrigatória), descrição (obrigatória, até 500, com contador), foto (`<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment">` com prévia e "Remover foto"), e "Registrar ocorrência". Recusa no cliente uma foto acima de 10 MB com "A foto passa de 10 MB". `onEnviar({tipo, descricao, foto?})`. A página põe na fila com `crypto.randomUUID()` e confirma "Ocorrência registrada" ou "Ocorrência guardada; será enviada quando houver rede".

- [ ] **Step 1: Testes que falham**: botão desabilitado sem tipo ou descrição; envio com foto passa o `File`; foto grande mostra o erro e não envia; o contador chega a 500 e para.
- [ ] **Step 2:** `cd web && npx vitest run components/motorista/FormOcorrencia.test.tsx` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** PASS; no navegador, registrar uma ocorrência com foto e abrir `GET /api/ocorrencias/{id}/foto`.
- [ ] **Step 5:** `git commit -m "feat: registro de ocorrência com foto no app do motorista"`

### Task 10: PWA — manifest, ícones e service worker

**Files:**
- Create: `web/app/manifest.ts`, `web/public/icone.svg`, `web/public/icone-192.png`, `web/public/icone-512.png`, `web/public/sw.js`, `web/components/motorista/RegistroSw.tsx`
- Modify: `web/app/motorista/page.tsx` (ou `web/app/motorista/layout.tsx` com `metadata` próprio: `themeColor`, `appleWebApp`), `web/next.config.ts` (headers de `/sw.js`: `Cache-Control: no-cache`)
- Test: `web/app/manifest.test.ts`

**Interfaces:**
- Produces: manifest com `name: "Rota da Madeira — Motorista"`, `short_name: "Motorista"`, `start_url: "/motorista"`, `scope: "/motorista"`, `display: "standalone"`, cores dos tokens e ícones de 192 e 512 px. Os PNG são gerados uma vez a partir do SVG (com `sharp`, que vem com o Next, ou com o Playwright) e commitados. O `sw.js` usa a rede primeiro para a navegação de `/motorista`, com cópia em cache para abrir offline, e o cache primeiro para `/_next/static/`. Não guarda nada de `/api/`. Ele nunca serve HTML antigo quando há rede. O registro acontece só com `isSecureContext` e em produção.
- Ruling previsto: o service worker não tem teste automático (jsdom não roda service worker); a verificação é manual em `http://localhost` (contexto seguro): carregar `/motorista`, desligar a rede no Playwright (`context.setOffline(true)`) e recarregar.

- [ ] **Step 1: Teste que falha**: `manifest()` devolve `start_url` `/motorista`, `display` `standalone` e ícones 192/512.
- [ ] **Step 2:** `cd web && npx vitest run app/manifest.test.ts` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** PASS; `docker compose build web && docker compose up -d web && docker compose restart nginx`; verificação offline manual descrita acima.
- [ ] **Step 5:** `git commit -m "feat: app do motorista instalável e abrindo sem rede"`

### Task 11: Painel mostra o app e as ocorrências

**Files:**
- Modify: `web/components/TabelaFrota.tsx`, `web/components/DetalheCaminhao.tsx`, `web/lib/useFrotaAoVivo.ts`
- Create: `web/components/ListaOcorrencias.tsx`
- Test: `web/components/TabelaFrota.test.tsx`, `web/components/DetalheCaminhao.test.tsx`, `web/components/ListaOcorrencias.test.tsx`, `web/lib/useFrotaAoVivo.test.tsx`

**Interfaces:**
- Consumes: Task 7 (tipos, `buscarOcorrencias`, `urlApi`).
- Produces:
  - Marca "App" ao lado da placa (texto, não só cor) quando `assumido`.
  - `ListaOcorrencias({ ocorrencias })`: tipo, hora, descrição e link "Ver foto" (`urlApi(foto_url)`, em nova aba); vazia → "Nenhuma ocorrência nesta viagem.".
  - O detalhe busca `["ocorrencias", viagem_atual_id]`.
  - A mensagem `ocorrencia` do WebSocket invalida `["ocorrencias"]`.

- [ ] **Step 1: Testes que falham**: marca "App"; lista com foto e sem foto; lista vazia; invalidação.
- [ ] **Step 2:** `cd web && npx vitest run components lib/useFrotaAoVivo.test.tsx` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** PASS; `npm test`, tsc e lint limpos.
- [ ] **Step 5:** `git commit -m "feat: painel mostra caminhão no app e ocorrências da viagem"`

### Task 12: README e verificação ponta a ponta

**Files:**
- Modify: `README.md` (seção "App do motorista": endereço, fluxo, limite do HTTPS para instalar e abrir offline), `CLAUDE.md` (comandos, se mudarem)

- [ ] **Step 1:** `docker compose up -d --build` e `docker compose restart nginx`.
- [ ] **Step 2:** No Playwright a 390 px: abrir `/motorista`, assumir um caminhão vazio, esperar chegar à fazenda, iniciar e finalizar o carregamento, ver o caminhão sair no painel (`/`) com a marca "App", registrar uma ocorrência com foto e vê-la no detalhe do painel.
- [ ] **Step 3:** Offline: com a rede desligada, fazer um check-in e uma ocorrência (ficam pendentes); religar a rede e ver as duas enviadas uma vez só.
- [ ] **Step 4:** Suítes completas: `docker compose exec api pytest -q`, `docker compose exec simulator pytest -q`, `cd web && npm test`, tsc, lint.
- [ ] **Step 5:** `git commit -m "docs: app do motorista no README"`
