from datetime import datetime, timedelta, timezone

from app.telemetria import LeituraEntrada, registrar_leituras
from tests.test_telemetria import FIM_ROTA, INICIO_ROTA, MEIO_ROTA, ids  # noqa: F401  (fixture)

CAMPO_GRANDE = timezone(timedelta(hours=-4))
DEZ = datetime(2026, 10, 20, 10, 0, tzinfo=CAMPO_GRANDE)


def enviar(sessao, caminhao_id, fazenda_id, estado, momento, ponto=FIM_ROTA, vel=0.0):
    lon, lat = ponto
    registrar_leituras(sessao, [LeituraEntrada(
        caminhao_id=caminhao_id, fazenda_id=fazenda_id, estado=estado,
        lon=lon, lat=lat, velocidade_kmh=vel, momento=momento,
    )])


def test_fila_em_ordem_de_chegada(cliente, sessao, ids):  # noqa: F811
    a, b = ids["caminhoes"][:2]
    f = ids["fazenda"]
    enviar(sessao, b, f, "FILA_PATIO", DEZ + timedelta(minutes=5))
    enviar(sessao, a, f, "FILA_PATIO", DEZ + timedelta(minutes=10))
    enviar(sessao, b, f, "FILA_PATIO", DEZ + timedelta(minutes=12))  # continua na fila
    fila = cliente.get("/patio/fila").json()["fila"]
    assert [(x["caminhao_id"], x["posicao"]) for x in fila] == [(b, 1), (a, 2)]
    assert [x["esperando_min"] for x in fila] == [7, 2]
    assert datetime.fromisoformat(fila[0]["chegou_em"]) == DEZ + timedelta(minutes=5)
    assert fila[0]["placa"].startswith("TLG")


def test_vagas_ocupadas_contam_pesagem_e_descarga(cliente, sessao, ids):  # noqa: F811
    a, b, c = ids["caminhoes"][:3]
    f = ids["fazenda"]
    enviar(sessao, a, f, "PESAGEM", DEZ)
    enviar(sessao, b, f, "DESCARGA", DEZ)
    enviar(sessao, c, f, "FILA_PATIO", DEZ)
    r = cliente.get("/patio/fila").json()
    assert (r["vagas_ocupadas"], r["vagas_total"]) == (2, 3)
    assert len(r["fila"]) == 1


def test_espera_media_de_hoje(cliente, sessao, ids):  # noqa: F811
    a, b = ids["caminhoes"][:2]
    f = ids["fazenda"]
    enviar(sessao, a, f, "FILA_PATIO", DEZ)
    enviar(sessao, a, f, "PESAGEM", DEZ + timedelta(minutes=10))
    enviar(sessao, b, f, "FILA_PATIO", DEZ)
    enviar(sessao, b, f, "PESAGEM", DEZ + timedelta(minutes=20))
    assert cliente.get("/patio/fila").json()["espera_media_min"] == 15


def test_espera_media_ignora_ontem(cliente, sessao, ids):  # noqa: F811
    a = ids["caminhoes"][0]
    f = ids["fazenda"]
    ontem = DEZ - timedelta(days=1)
    enviar(sessao, a, f, "FILA_PATIO", ontem)
    enviar(sessao, a, f, "PESAGEM", ontem + timedelta(minutes=40))
    enviar(sessao, a, f, "CARREGANDO", DEZ, INICIO_ROTA)
    assert cliente.get("/patio/fila").json()["espera_media_min"] is None


def test_espera_media_sem_dados_e_nula(cliente, semeado):
    r = cliente.get("/patio/fila").json()
    assert r["espera_media_min"] is None and r["fila"] == [] and r["chegadas"] == []


def test_chegadas_nas_proximas_duas_horas(cliente, sessao, ids):  # noqa: F811
    perto, longe, vazio = ids["caminhoes"][:3]
    f = ids["fazenda"]
    # Metade da rota a 54,2 km/h: chega em 30 min.
    enviar(sessao, perto, f, "EM_TRANSITO_CARREGADO", DEZ, MEIO_ROTA, vel=54.2)
    # Início da rota a 10 km/h (mínimo de 20): 163 min, fora das 2 h.
    enviar(sessao, longe, f, "EM_TRANSITO_CARREGADO", DEZ, INICIO_ROTA, vel=10)
    enviar(sessao, vazio, f, "EM_TRANSITO_VAZIO", DEZ, MEIO_ROTA, vel=70)
    chegadas = cliente.get("/patio/fila").json()["chegadas"]
    assert [c["caminhao_id"] for c in chegadas] == [perto]
    eta = datetime.fromisoformat(chegadas[0]["eta"])
    assert abs((eta - (DEZ + timedelta(minutes=30))).total_seconds()) < 60
    assert chegadas[0]["fazenda"].startswith("Fazenda")
