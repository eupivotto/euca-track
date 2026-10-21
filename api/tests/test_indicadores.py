from datetime import datetime, timedelta, timezone

from app.telemetria import LeituraEntrada, registrar_leituras
from tests.test_telemetria import ids  # noqa: F401  (fixture)

CAMPO_GRANDE = timezone(timedelta(hours=-4))
CICLO = ["CARREGANDO", "EM_TRANSITO_CARREGADO", "FILA_PATIO", "PESAGEM", "DESCARGA", "EM_TRANSITO_VAZIO"]


def percorrer(sessao, caminhao_id, fazenda_id, estados, inicio):
    for i, estado in enumerate(estados):
        registrar_leituras(sessao, [LeituraEntrada(
            caminhao_id=caminhao_id, fazenda_id=fazenda_id, estado=estado,
            lon=-51.9, lat=-20.9, velocidade_kmh=0, momento=inicio + timedelta(minutes=10 * i),
        )])


def test_sem_dados(cliente):
    r = cliente.get("/indicadores").json()
    assert r["toneladas"] == 0 and r["viagens"] == 0 and r["meta_t"] == 4000
    assert set(r) == {"inicio", "fim", "agora", "toneladas", "viagens", "meta_t"}


def test_conta_so_descargas_concluidas_no_dia(cliente, sessao, ids):  # noqa: F811
    rodotrem, tritrem = ids["caminhoes"][0], ids["caminhoes"][12]
    manha = datetime(2026, 10, 20, 9, 0, tzinfo=CAMPO_GRANDE)
    percorrer(sessao, rodotrem, ids["fazenda"], CICLO, manha)        # descarregou
    percorrer(sessao, tritrem, ids["fazenda"], CICLO[:5], manha)     # ainda descarregando
    r = cliente.get("/indicadores").json()
    assert r["toneladas"] == 55 and r["viagens"] == 1


def test_dia_no_fuso_de_campo_grande(cliente, sessao, ids):  # noqa: F811
    # termina a descarga às 23:30 de Campo Grande (03:30 UTC do dia seguinte)
    inicio = datetime(2026, 10, 20, 22, 40, tzinfo=CAMPO_GRANDE)
    percorrer(sessao, ids["caminhoes"][0], ids["fazenda"], CICLO, inicio)
    r = cliente.get("/indicadores").json()
    assert datetime.fromisoformat(r["inicio"]) == datetime(2026, 10, 20, tzinfo=CAMPO_GRANDE)
    assert datetime.fromisoformat(r["agora"]) == datetime(2026, 10, 20, 23, 30, tzinfo=CAMPO_GRANDE)
    assert r["toneladas"] == 55


def test_periodo_informado_multiplica_a_meta(cliente):
    r = cliente.get("/indicadores", params={
        "inicio": "2026-10-19T00:00:00-04:00", "fim": "2026-10-21T00:00:00-04:00",
    }).json()
    assert r["meta_t"] == 8000
