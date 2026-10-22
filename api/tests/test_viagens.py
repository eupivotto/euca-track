from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.modelos import Viagem
from app.telemetria import LeituraEntrada, registrar_leituras
from tests.test_telemetria import INICIO_ROTA, MEIO_ROTA, ids  # noqa: F401  (fixture)

DEZ = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)


def enviar(sessao, caminhao_id, fazenda_id, estado, minuto, ponto=MEIO_ROTA, vel=60.0):
    lon, lat = ponto
    registrar_leituras(sessao, [LeituraEntrada(
        caminhao_id=caminhao_id, fazenda_id=fazenda_id, estado=estado, lon=lon, lat=lat,
        velocidade_kmh=vel, momento=DEZ + timedelta(minutes=minuto),
    )])


def test_viagem_com_pontos_e_eventos_em_ordem(cliente, sessao, ids):  # noqa: F811
    c, f = ids["caminhoes"][0], ids["fazenda"]
    enviar(sessao, c, f, "CARREGANDO", 0, INICIO_ROTA, vel=0)
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 10, INICIO_ROTA)
    enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 20, MEIO_ROTA)
    viagem_id = sessao.scalars(select(Viagem.id)).one()
    r = cliente.get(f"/viagens/{viagem_id}").json()
    assert r["placa"].startswith("TLG") and r["fazenda"].startswith("Área de eucalipto")
    assert r["toneladas"] == 55 and r["status"] == "EM_ANDAMENTO" and r["fim"] is None
    assert [p["momento"] for p in r["pontos"]] == sorted(p["momento"] for p in r["pontos"])
    assert [(p["lon"], p["lat"]) for p in r["pontos"]] == [INICIO_ROTA, INICIO_ROTA, MEIO_ROTA]
    assert r["pontos"][2]["velocidade_kmh"] == 60
    assert [e["estado"] for e in r["eventos"]] == ["CARREGANDO", "EM_TRANSITO_CARREGADO"]
    assert r["rota"]["type"] == "LineString" and len(r["rota"]["coordinates"]) == 2


def test_viagem_inexistente_404(cliente, semeado):
    r = cliente.get("/viagens/999999")
    assert r.status_code == 404 and r.json()["detail"] == "Viagem não encontrada"


def test_viagem_sem_pontos(cliente, sessao, ids):  # noqa: F811
    viagem = Viagem(caminhao_id=ids["caminhoes"][0], fazenda_id=ids["fazenda"], toneladas=55,
                    inicio=DEZ, status="EM_ANDAMENTO")
    sessao.add(viagem)
    sessao.flush()
    r = cliente.get(f"/viagens/{viagem.id}").json()
    assert r["pontos"] == [] and r["eventos"] == [] and r["rota"] is None


def test_lista_filtra_por_caminhao_e_ordena(cliente, sessao, ids):  # noqa: F811
    a, b = ids["caminhoes"][:2]
    f = ids["fazenda"]
    enviar(sessao, a, f, "CARREGANDO", 0, vel=0)
    enviar(sessao, a, f, "EM_TRANSITO_VAZIO", 60)
    enviar(sessao, a, f, "CARREGANDO", 90, vel=0)
    enviar(sessao, b, f, "CARREGANDO", 30, vel=0)
    todas = cliente.get("/viagens").json()
    assert [v["inicio"] for v in todas] == sorted((v["inicio"] for v in todas), reverse=True)
    assert len(todas) == 3
    so_a = cliente.get(f"/viagens?caminhao_id={a}").json()
    assert [v["status"] for v in so_a] == ["EM_ANDAMENTO", "CONCLUIDA"]
    assert set(so_a[0]) == {"id", "caminhao_id", "placa", "fazenda", "toneladas", "inicio", "fim",
                            "status"}
    assert len(cliente.get("/viagens?limite=1").json()) == 1
