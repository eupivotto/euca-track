from datetime import datetime, timezone

import httpx

from sim.__main__ import enviar_e_controlar, iniciar
from sim.cliente import ClienteApi
from tests.test_cliente import api_falsa


def test_inicio_tenta_de_novo_quando_a_api_cai_no_meio():
    # A API cai entre aguardar_api e a montagem da simulação.
    normal = api_falsa()
    falhas = {"restantes": 1}

    def handler(req: httpx.Request):
        if req.url.path == "/simulacao/parametros" and falhas["restantes"]:
            falhas["restantes"] -= 1
            raise httpx.ConnectError("fora", request=req)
        return normal.send(normal.build_request(req.method, req.url.path))

    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://api")
    esperas = []
    simulacao = iniciar(ClienteApi(http, token="t"), lambda: datetime.now(timezone.utc), esperas.append)
    assert len(simulacao.caminhoes) == 2
    assert len(esperas) == 1


def test_resposta_da_api_controla_os_caminhoes():
    resposta = {"recebidas": 2, "assumidos": [5], "liberados": [6]}
    cliente = ClienteApi(api_falsa(resposta_telemetria=resposta), token="t")
    simulacao = iniciar(cliente, lambda: datetime.now(timezone.utc))
    enviar_e_controlar(cliente, simulacao, 0.5)
    por_id = {c.id: c for c in simulacao.caminhoes}
    assert (por_id[5].assumido, por_id[5].liberado) == (True, False)
    assert (por_id[6].assumido, por_id[6].liberado) == (False, True)


def test_enviar_sem_chaves_novas():
    # API antiga ou resposta sem controle: ninguém fica assumido.
    cliente = ClienteApi(api_falsa(), token="t")
    simulacao = iniciar(cliente, lambda: datetime.now(timezone.utc))
    simulacao.controlar({5}, set())
    enviar_e_controlar(cliente, simulacao, 0.5)
    assert not any(c.assumido or c.liberado for c in simulacao.caminhoes)


def test_falha_no_envio_mantem_o_controle_anterior():
    cliente = ClienteApi(api_falsa(status_telemetria=500), token="t")
    simulacao = iniciar(ClienteApi(api_falsa(), token="t"), lambda: datetime.now(timezone.utc))
    simulacao.controlar({5}, set())
    enviar_e_controlar(cliente, simulacao, 0.5)
    assert {c.id for c in simulacao.caminhoes if c.assumido} == {5}
