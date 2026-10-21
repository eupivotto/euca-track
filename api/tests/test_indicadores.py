from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.modelos import Viagem
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
    assert {"inicio", "fim", "agora", "toneladas", "viagens", "meta_t", "dias", "ciclo_medio_min",
            "fila_media_min", "uso_frota", "frota_por_estado", "serie"} == set(r)


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


def test_ciclo_medio_ignora_interrompidas(cliente, sessao, ids):  # noqa: F811
    a, b = ids["caminhoes"][:2]
    manha = datetime(2026, 10, 20, 6, 0, tzinfo=CAMPO_GRANDE)
    # a: ciclo completo de 3 h (volta a carregar às 09h00)
    percorrer(sessao, a, ids["fazenda"], ["CARREGANDO"], manha)
    percorrer(sessao, a, ids["fazenda"], ["EM_TRANSITO_VAZIO"], manha + timedelta(hours=2))
    percorrer(sessao, a, ids["fazenda"], ["CARREGANDO"], manha + timedelta(hours=3))
    # b: viagem cortada por reinício depois de 1 h (descarga → carregando)
    percorrer(sessao, b, ids["fazenda"], ["CARREGANDO"], manha)
    percorrer(sessao, b, ids["fazenda"], ["DESCARGA"], manha + timedelta(minutes=30))
    percorrer(sessao, b, ids["fazenda"], ["CARREGANDO"], manha + timedelta(hours=1))
    status = {v.status for v in sessao.scalars(select(Viagem).where(Viagem.fim.is_not(None)))}
    assert status == {"CONCLUIDA", "INTERROMPIDA"}
    assert cliente.get("/indicadores").json()["ciclo_medio_min"] == 180


def test_indicadores_sem_viagens(cliente, semeado):
    r = cliente.get("/indicadores").json()
    assert r["ciclo_medio_min"] is None and r["fila_media_min"] is None
    assert len(r["serie"]) == 24 and all(b["toneladas"] == 0 for b in r["serie"])
    assert r["uso_frota"] == 0 and r["frota_por_estado"]["CARREGANDO"] == 0


def test_serie_por_hora_no_fuso(cliente, sessao, ids):  # noqa: F811
    # CICLO a partir das 09h30: EM_TRANSITO_VAZIO (entrega) às 10h20 de Campo Grande
    percorrer(sessao, ids["caminhoes"][0], ids["fazenda"], CICLO,
              datetime(2026, 10, 20, 9, 30, tzinfo=CAMPO_GRANDE))
    serie = cliente.get("/indicadores").json()["serie"]
    assert datetime.fromisoformat(serie[0]["inicio"]) == datetime(2026, 10, 20, tzinfo=CAMPO_GRANDE)
    assert [b["toneladas"] for b in serie if b["toneladas"]] == [55]
    assert serie[10]["toneladas"] == 55


def test_fila_media_no_periodo(cliente, sessao, ids):  # noqa: F811
    # CICLO de 10 em 10 min: 10 min entre FILA_PATIO e PESAGEM
    percorrer(sessao, ids["caminhoes"][0], ids["fazenda"], CICLO,
              datetime(2026, 10, 20, 9, 0, tzinfo=CAMPO_GRANDE))
    assert cliente.get("/indicadores").json()["fila_media_min"] == 10


def test_sete_dias_tem_serie_diaria_e_meta_semanal(cliente, sessao, ids):  # noqa: F811
    percorrer(sessao, ids["caminhoes"][0], ids["fazenda"], CICLO,
              datetime(2026, 10, 18, 9, 0, tzinfo=CAMPO_GRANDE))
    percorrer(sessao, ids["caminhoes"][1], ids["fazenda"], ["CARREGANDO"],
              datetime(2026, 10, 20, 9, 0, tzinfo=CAMPO_GRANDE))
    r = cliente.get("/indicadores?dias=7").json()
    assert r["dias"] == 7 and r["meta_t"] == 28000 and len(r["serie"]) == 7
    assert datetime.fromisoformat(r["inicio"]) == datetime(2026, 10, 14, tzinfo=CAMPO_GRANDE)
    assert datetime.fromisoformat(r["fim"]) == datetime(2026, 10, 21, tzinfo=CAMPO_GRANDE)
    assert [b["toneladas"] for b in r["serie"]] == [0, 0, 0, 0, 55, 0, 0]
    assert r["toneladas"] == 55


def test_uso_e_frota_por_estado(cliente, sessao, ids):  # noqa: F811
    a, b, c = ids["caminhoes"][:3]
    agora = datetime(2026, 10, 20, 9, 0, tzinfo=CAMPO_GRANDE)
    percorrer(sessao, a, ids["fazenda"], ["EM_TRANSITO_CARREGADO"], agora)
    percorrer(sessao, b, ids["fazenda"], ["EM_TRANSITO_VAZIO"], agora)
    percorrer(sessao, c, ids["fazenda"], ["FILA_PATIO"], agora)
    r = cliente.get("/indicadores").json()
    assert r["uso_frota"] == 2 / 3
    assert r["frota_por_estado"] == {"CARREGANDO": 0, "EM_TRANSITO_CARREGADO": 1, "FILA_PATIO": 1,
                                     "PESAGEM": 0, "DESCARGA": 0, "EM_TRANSITO_VAZIO": 1}


def test_periodo_sem_fuso_e_recusado(cliente):
    r = cliente.get("/indicadores?inicio=2026-10-20T00:00:00&fim=2026-10-21T00:00:00")
    assert r.status_code == 422


def test_periodo_invertido_e_recusado(cliente):
    r = cliente.get("/indicadores", params={
        "inicio": "2026-10-21T00:00:00-04:00", "fim": "2026-10-20T00:00:00-04:00",
    })
    assert r.status_code == 422


def test_dias_fora_do_limite_e_recusado(cliente):
    assert cliente.get("/indicadores?dias=31").status_code == 422
