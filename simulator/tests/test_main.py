from datetime import datetime, timezone

import httpx

from sim.__main__ import iniciar
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
