from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select

from app.modelos import ClimaDiario, Fazenda, FocoCalor, RiscoDiario

AGORA = datetime.now(UTC)
HOJE = AGORA.astimezone(ZoneInfo("America/Campo_Grande")).date()


def _foco(sessao, horas_atras, chave):
    sessao.add(FocoCalor(
        geom=from_shape(Point(-51.8, -20.7), srid=4326), satelite="NOAA-20",
        detectado_em=AGORA - timedelta(hours=horas_atras), municipio="TRÊS LAGOAS", chave=chave,
    ))
    sessao.flush()


def _fazendas(sessao):
    return sessao.scalars(select(Fazenda).order_by(Fazenda.id)).all()


def test_focos_da_janela(cliente, sessao):
    _foco(sessao, 2, "a")
    _foco(sessao, 30, "b")
    r = cliente.get("/focos").json()
    assert r["type"] == "FeatureCollection" and len(r["features"]) == 1
    props = r["features"][0]["properties"]
    assert {"id", "detectado_em", "satelite", "municipio"} <= props.keys()
    assert props["municipio"] == "TRÊS LAGOAS"
    assert r["features"][0]["geometry"]["type"] == "Point"
    assert len(cliente.get("/focos?horas=48").json()["features"]) == 2


def test_focos_horas_fora_do_limite(cliente):
    assert cliente.get("/focos?horas=0").status_code == 422
    assert cliente.get("/focos?horas=73").status_code == 422


def test_risco_das_fazendas_no_dia(cliente, semeado):
    primeira, segunda = _fazendas(semeado)[:2]
    semeado.add(RiscoDiario(fazenda_id=primeira.id, data=HOJE, fma=4.2, classe="MEDIO"))
    semeado.flush()
    r = {l["fazenda_id"]: l for l in cliente.get("/risco/fazendas").json()}
    assert len(r) == 8
    assert r[primeira.id] == {"fazenda_id": primeira.id, "nome": primeira.nome, "data": HOJE.isoformat(),
                              "fma": 4.2, "classe": "MEDIO"}
    assert (r[segunda.id]["fma"], r[segunda.id]["classe"]) == (None, None)


def test_risco_de_data_sem_calculo(cliente, semeado):
    r = cliente.get("/risco/fazendas?data=2020-01-01").json()
    assert all(l["fma"] is None and l["classe"] is None for l in r)


def test_historico_alinhado_com_buracos(cliente, semeado):
    fazenda = _fazendas(semeado)[0]
    ontem = HOJE - timedelta(days=1)
    semeado.add_all([
        RiscoDiario(fazenda_id=fazenda.id, data=HOJE, fma=6.0, classe="MEDIO"),
        ClimaDiario(fazenda_id=fazenda.id, data=HOJE, ur_13h=40, chuva_mm=3.0),
    ])
    semeado.flush()
    r = cliente.get("/risco/historico?dias=3").json()
    assert r["datas"] == [(HOJE - timedelta(days=d)).isoformat() for d in (2, 1, 0)]
    linha = next(f for f in r["fazendas"] if f["fazenda_id"] == fazenda.id)
    assert linha["nome"] == fazenda.nome
    assert linha["dias"][:2] == [None, None]
    assert linha["dias"][2] == {"data": HOJE.isoformat(), "fma": 6.0, "classe": "MEDIO",
                                "chuva_mm": 3.0, "ur_13h": 40}
    assert ontem.isoformat() in r["datas"]
    assert cliente.get("/risco/historico?dias=0").status_code == 422
    assert cliente.get("/risco/historico?dias=91").status_code == 422


def test_fazendas_trazem_classe_de_hoje_ou_do_ultimo_dia(cliente, semeado):
    primeira, segunda = _fazendas(semeado)[:2]
    semeado.add_all([
        RiscoDiario(fazenda_id=primeira.id, data=HOJE - timedelta(days=1), fma=2.0, classe="PEQUENO"),
        RiscoDiario(fazenda_id=primeira.id, data=HOJE, fma=9.0, classe="ALTO"),
        RiscoDiario(fazenda_id=segunda.id, data=HOJE - timedelta(days=2), fma=1.5, classe="PEQUENO"),
        # Um dia futuro (previsão) não vale como "hoje".
        RiscoDiario(fazenda_id=segunda.id, data=HOJE + timedelta(days=1), fma=25, classe="MUITO_ALTO"),
    ])
    semeado.flush()
    props = {f["properties"]["id"]: f["properties"]
             for f in cliente.get("/fazendas").json()["features"] if f["properties"]["tipo"] == "fazenda"}
    assert (props[primeira.id]["classe"], props[primeira.id]["fma"]) == ("ALTO", 9.0)
    assert props[segunda.id]["classe"] == "PEQUENO"
    terceira = _fazendas(semeado)[2]
    assert (props[terceira.id]["classe"], props[terceira.id]["fma"]) == (None, None)


def test_filtro_de_alertas_aceita_tipos_de_foco(cliente):
    assert cliente.get("/alertas?tipo=FOCO_PROXIMO_FAZENDA").status_code == 200
    assert cliente.get("/alertas?tipo=FOCO_PROXIMO_ROTA").status_code == 200
