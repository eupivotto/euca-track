import json
from datetime import datetime, timezone

import httpx

from sim.cliente import ClienteApi
from tests.test_simulacao import PARAMETROS_PADRAO

FAZENDAS = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[-51.96, -20.96]]]},
         "properties": {"id": 1, "tipo": "fazenda", "nome": "Fazenda Santa Luzia", "area_ha": 3200}},
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[-52.06, -20.46]]]},
         "properties": {"id": 2, "tipo": "fazenda", "nome": "Fazenda Boa Vista", "area_ha": 2800}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-51.76, -20.62]},
         "properties": {"id": 1, "tipo": "fabrica", "nome": "Fábrica"}},
    ],
}
ROTAS = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature",
         "geometry": {"type": "LineString", "coordinates": [[-51.95, -20.95], [-51.76, -20.62]]},
         "properties": {"id": 10, "fazenda_id": 1, "distancia_km": 65.3, "duracao_prevista_min": 79}},
    ],
}
CAMINHOES = [{"id": 5, "capacidade_t": 55}, {"id": 6, "capacidade_t": 45}]
# Última leitura gravada, no fuso da operação (como GET /indicadores devolve).
ULTIMO_MOMENTO = "2026-10-21T14:02:49-04:00"


def api_falsa(vistos=None, status_telemetria=200, resposta_telemetria=None):
    def handler(req: httpx.Request):
        if vistos is not None:
            vistos.append(req)
        caminho = req.url.path
        if caminho == "/simulacao/parametros":
            return httpx.Response(200, json=PARAMETROS_PADRAO)
        if caminho == "/fazendas":
            return httpx.Response(200, json=FAZENDAS)
        if caminho == "/rotas":
            return httpx.Response(200, json=ROTAS)
        if caminho == "/caminhoes":
            return httpx.Response(200, json=CAMINHOES)
        if caminho == "/indicadores":
            return httpx.Response(200, json={"agora": ULTIMO_MOMENTO, "toneladas": 0})
        if caminho == "/telemetria":
            return httpx.Response(status_telemetria, json=resposta_telemetria or {"recebidas": 0})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://api")


def test_parametros():
    assert ClienteApi(api_falsa(), token="t").parametros().vagas_descarga == 3


def test_fazendas_juntam_rota_e_area():
    fs = ClienteApi(api_falsa(), token="t").fazendas()
    assert len(fs) == 1
    assert fs[0].id == 1 and fs[0].area_ha == 3200
    assert fs[0].coords_rota[0] == (-51.95, -20.95)


def test_fazenda_sem_rota_fica_de_fora():
    ids = [f.id for f in ClienteApi(api_falsa(), token="t").fazendas()]
    assert 2 not in ids


def test_caminhoes():
    assert ClienteApi(api_falsa(), token="t").caminhoes() == [(5, 55), (6, 45)]


def test_envio_manda_token_e_lote():
    vistos = []
    cli = ClienteApi(api_falsa(vistos), token="t")
    assert cli.enviar([{"caminhao_id": 1}]) == {"recebidas": 0}
    assert vistos[0].headers["x-token"] == "t"
    assert json.loads(vistos[0].content) == [{"caminhao_id": 1}]


def test_envio_com_api_fora_nao_levanta():
    def cai(req):
        raise httpx.ConnectError("fora", request=req)

    cli = ClienteApi(httpx.Client(transport=httpx.MockTransport(cai), base_url="http://api"), token="t")
    assert cli.enviar([]) is None


def test_envio_com_erro_http_devolve_none():
    assert ClienteApi(api_falsa(status_telemetria=500), token="t").enviar([]) is None


def test_enviar_devolve_a_resposta():
    resposta = {"recebidas": 1, "assumidos": [5], "liberados": [6]}
    cli = ClienteApi(api_falsa(resposta_telemetria=resposta), token="t")
    assert cli.enviar([{"caminhao_id": 5}]) == resposta


def test_relogio_continua_da_ultima_leitura_quando_ela_esta_a_frente():
    # Simulador reiniciado: o relógio simulado já passou da hora real.
    agora_real = datetime(2026, 10, 21, 16, 0, tzinfo=timezone.utc)
    inicio = ClienteApi(api_falsa(), token="t").relogio_inicial(agora_real)
    assert inicio == datetime(2026, 10, 21, 18, 2, 49, tzinfo=timezone.utc)


def test_relogio_usa_hora_real_quando_ela_esta_a_frente():
    agora_real = datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc)
    assert ClienteApi(api_falsa(), token="t").relogio_inicial(agora_real) == agora_real
