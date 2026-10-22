import json

import httpx
import pytest

from app.geo import linha_reta
from app.osrm import buscar_mais_proximo, buscar_rota, ler_resposta_nearest, ler_resposta_osrm
from tests.conftest import FIXTURES

AMOSTRA = (FIXTURES / "osrm_faz01.json").read_text()
AMOSTRA_NEAREST = (FIXTURES / "osrm_nearest.json").read_text()


def test_parser_contra_amostra_real():
    dados = json.loads(AMOSTRA)
    r = ler_resposta_osrm(dados)
    assert r.distancia_km == pytest.approx(dados["routes"][0]["distance"] / 1000)
    assert r.duracao_min == pytest.approx(dados["routes"][0]["duration"] / 60)
    assert len(r.coords) > 2
    assert r.coords[0] == pytest.approx((-51.95, -20.95), abs=0.05)


def test_parser_recusa_code_diferente_de_ok():
    with pytest.raises(ValueError):
        ler_resposta_osrm({"code": "NoRoute", "routes": []})


def test_parser_recusa_sem_rotas():
    with pytest.raises(ValueError):
        ler_resposta_osrm({"code": "Ok", "routes": []})


def test_buscar_rota_manda_user_agent(settings):
    vistos = []

    def handler(req):
        vistos.append(req)
        return httpx.Response(200, text=AMOSTRA)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    buscar_rota(cliente, settings, (-51.95, -20.95), (-51.76, -20.62))
    url = str(vistos[0].url)
    assert vistos[0].headers["user-agent"] == settings.user_agent
    assert "/route/v1/driving/-51.95,-20.95;-51.76,-20.62" in url
    assert "overview=full" in url and "geometries=geojson" in url


def test_linha_reta_com_fator():
    r = linha_reta((-51.95, -20.95), (-51.76, -20.62), fator=1.3, velocidade_kmh=60)
    assert r.coords == [(-51.95, -20.95), (-51.76, -20.62)]
    assert r.distancia_km == pytest.approx(41.7 * 1.3, abs=0.7)
    assert r.duracao_min == pytest.approx(r.distancia_km / 60 * 60)


def test_nearest_contra_amostra_real():
    ponto, distancia = ler_resposta_nearest(json.loads(AMOSTRA_NEAREST))
    assert ponto == pytest.approx((-51.725739, -20.407791))
    assert distancia == pytest.approx(209.8171357)


def test_nearest_recusa_code_diferente_de_ok():
    with pytest.raises(ValueError):
        ler_resposta_nearest({"code": "NoSegment", "waypoints": []})


def test_buscar_mais_proximo_pede_o_ponto_com_user_agent(settings):
    vistos = []

    def handler(req):
        vistos.append(req)
        return httpx.Response(200, text=AMOSTRA_NEAREST)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    buscar_mais_proximo(cliente, settings, (-51.72753, -20.40693))
    assert vistos[0].url.path == "/nearest/v1/driving/-51.72753,-20.40693"
    assert vistos[0].headers["User-Agent"] == settings.user_agent
