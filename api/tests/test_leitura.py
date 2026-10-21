from collections import Counter

import pytest


def test_fazendas_geojson(cliente, semeado):
    fc = cliente.get("/fazendas").json()
    assert fc["type"] == "FeatureCollection"
    tipos = Counter(f["properties"]["tipo"] for f in fc["features"])
    assert tipos == {"fazenda": 8, "fabrica": 1}
    fab = next(f for f in fc["features"] if f["properties"]["tipo"] == "fabrica")
    assert fab["geometry"]["type"] == "Point"
    assert fab["geometry"]["coordinates"] == pytest.approx([-51.76, -20.62])
    faz = next(f for f in fc["features"] if f["properties"]["tipo"] == "fazenda")
    assert faz["geometry"]["type"] == "Polygon"
    assert set(faz["properties"]) == {"id", "tipo", "nome", "area_ha"}


def test_rotas_geojson(cliente, semeado_com_rota):
    fc = cliente.get("/rotas").json()
    assert len(fc["features"]) == 8
    f = fc["features"][0]
    assert f["geometry"]["type"] == "LineString"
    assert f["geometry"]["coordinates"][0] == pytest.approx([-51.95, -20.95])
    assert set(f["properties"]) == {"id", "fazenda_id", "distancia_km", "duracao_prevista_min"}


def test_caminhoes_sem_telemetria(cliente, semeado):
    cs = cliente.get("/caminhoes").json()
    assert len(cs) == 20
    assert [c["id"] for c in cs] == sorted(c["id"] for c in cs)
    primeiro = cs[0]
    assert primeiro["posicao"] is None and primeiro["estado_atual"] is None
    assert primeiro["carga_t"] == 0 and primeiro["fazenda_id"] is None
    assert primeiro["tipo"] == "rodotrem" and primeiro["capacidade_t"] == 55
    assert " " in primeiro["motorista"]


def test_parametros_para_o_simulador(cliente):
    p = cliente.get("/simulacao/parametros").json()
    assert p["vagas_descarga"] == 3 and p["fator_tempo"] == 10 and p["seed"] == 42
    assert p["carregamento_min_min"] == 40 and p["descarga_max_min"] == 35
    assert "token_telemetria" not in p and "database_url" not in p
