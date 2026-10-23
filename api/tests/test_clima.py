import copy
import json
from datetime import date

import httpx
import pytest
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select

from app.clima import ClimaDia, importar_clima, ler_open_meteo
from app.fma import DiaClima, serie_fma
from app.modelos import ClimaDiario, Fazenda, RiscoDiario
from tests.conftest import FIXTURES

PREVISAO = json.loads((FIXTURES / "open_meteo_forecast.json").read_text(encoding="utf-8"))
HISTORICO = json.loads((FIXTURES / "open_meteo_archive.json").read_text(encoding="utf-8"))
HOJE = date(2026, 10, 23)


def _valor_13h(dados, dia, variavel):
    horas = dados["hourly"]
    return horas[variavel][horas["time"].index(f"{dia}T13:00")]


def _chuva_do_dia(dados, dia):
    horas = dados["hourly"]
    return sum(v for t, v in zip(horas["time"], horas["precipitation"]) if t.startswith(dia))


@pytest.mark.parametrize("dados", [PREVISAO, HISTORICO], ids=["previsao", "historico"])
def test_ler_open_meteo(dados):
    dias = ler_open_meteo(dados)
    datas = sorted({t[:10] for t in dados["hourly"]["time"]})
    assert [d.data.isoformat() for d in dias] == datas
    for d in dias:
        dia = d.data.isoformat()
        assert d.ur_13h == _valor_13h(dados, dia, "relative_humidity_2m")
        assert d.vento_kmh == _valor_13h(dados, dia, "wind_speed_10m")
        assert d.vento_dir == _valor_13h(dados, dia, "wind_direction_10m")
        assert d.chuva_mm == pytest.approx(_chuva_do_dia(dados, dia))


def test_dia_com_valores_nulos():
    dados = copy.deepcopy(PREVISAO)
    horas = dados["hourly"]
    i = horas["time"].index("2026-10-22T13:00")
    horas["relative_humidity_2m"][i] = None
    for j, t in enumerate(horas["time"]):
        if t.startswith("2026-10-21"):
            horas["precipitation"][j] = None
    dias = {d.data.isoformat(): d for d in ler_open_meteo(dados)}
    assert dias["2026-10-22"].ur_13h is None
    assert dias["2026-10-21"].chuva_mm is None
    assert isinstance(dias["2026-10-23"], ClimaDia)


class OpenMeteoFalso:
    def __init__(self, previsao=PREVISAO, falhar_latitude=None):
        self.previsao = previsao
        self.falhar_latitude = falhar_latitude
        self.chamadas: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.chamadas.append(request.url.path)
        if self.falhar_latitude and request.url.params["latitude"] == self.falhar_latitude:
            return httpx.Response(500, text="erro")
        dados = HISTORICO if request.url.path.endswith("/archive") else self.previsao
        return httpx.Response(200, json=dados)

    def cliente(self):
        return httpx.Client(transport=httpx.MockTransport(self))


def _importar(sessao, settings, falso):
    return importar_clima(sessao, settings, falso.cliente(), HOJE, dormir=lambda s: None)


def test_importar_faz_backfill_so_na_primeira_vez(semeado, settings):
    falso = OpenMeteoFalso()
    assert _importar(semeado, settings, falso) == []
    assert falso.chamadas.count("/v1/archive") == 8
    assert falso.chamadas.count("/v1/forecast") == 8

    falso = OpenMeteoFalso()
    _importar(semeado, settings, falso)
    assert falso.chamadas == ["/v1/forecast"] * 8


def test_backfill_pede_60_dias_ate_ontem(semeado, settings):
    pedidos = []

    def handler(request):
        pedidos.append(request.url.params)
        dados = HISTORICO if request.url.path.endswith("/archive") else PREVISAO
        return httpx.Response(200, json=dados)

    importar_clima(semeado, settings, httpx.Client(transport=httpx.MockTransport(handler)), HOJE,
                   dormir=lambda s: None)
    historico = pedidos[0]
    assert (historico["start_date"], historico["end_date"]) == ("2026-08-24", "2026-10-22")
    assert historico["timezone"] == "America/Campo_Grande"
    previsao = pedidos[1]
    assert (previsao["past_days"], previsao["forecast_days"]) == ("3", "1")


def test_importar_grava_clima_e_risco(semeado, settings):
    _importar(semeado, settings, OpenMeteoFalso())
    fazenda_id = semeado.scalars(select(Fazenda.id).order_by(Fazenda.id)).first()
    clima = semeado.scalars(
        select(ClimaDiario).where(ClimaDiario.fazenda_id == fazenda_id).order_by(ClimaDiario.data)
    ).all()
    assert [c.data.isoformat() for c in clima] == [f"2026-10-{d}" for d in range(17, 24)]
    esperado = serie_fma([DiaClima(c.data, c.ur_13h, c.chuva_mm) for c in clima], settings)
    risco = semeado.scalars(
        select(RiscoDiario).where(RiscoDiario.fazenda_id == fazenda_id).order_by(RiscoDiario.data)
    ).all()
    assert [(r.data, r.fma, r.classe) for r in risco] == [
        (d, pytest.approx(f), str(c)) for d, f, c in esperado
    ]


def test_upsert_nao_duplica(semeado, settings):
    _importar(semeado, settings, OpenMeteoFalso())
    nova = copy.deepcopy(PREVISAO)
    i = nova["hourly"]["time"].index("2026-10-23T13:00")
    nova["hourly"]["relative_humidity_2m"][i] = 77
    _importar(semeado, settings, OpenMeteoFalso(previsao=nova))
    linhas = semeado.scalars(select(ClimaDiario).where(ClimaDiario.data == HOJE)).all()
    assert len(linhas) == 8 and {c.ur_13h for c in linhas} == {77}
    total = semeado.scalar(select(func.count()).select_from(RiscoDiario).where(RiscoDiario.data == HOJE))
    assert total == 8


def test_falha_de_uma_fazenda_vira_aviso(semeado, settings):
    primeira = semeado.scalars(select(Fazenda).order_by(Fazenda.id)).first()
    latitude = str(round(to_shape(primeira.centro).y, 4))
    avisos = _importar(semeado, settings, OpenMeteoFalso(falhar_latitude=latitude))
    assert len(avisos) == 1 and primeira.nome in avisos[0]
    com_clima = semeado.scalar(select(func.count(func.distinct(ClimaDiario.fazenda_id))))
    assert com_clima == 7


def test_lacuna_depois_de_dias_parado_e_preenchida(semeado, settings):
    pedidos = []

    def handler(request):
        pedidos.append((request.url.path, dict(request.url.params)))
        dados = HISTORICO if request.url.path.endswith("/archive") else PREVISAO
        return httpx.Response(200, json=dados)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    importar_clima(semeado, settings, cliente, HOJE, dormir=lambda s: None)
    pedidos.clear()
    # Painel desligado: a última linha gravada é de 23/10 e "hoje" agora é 02/11.
    importar_clima(semeado, settings, cliente, date(2026, 11, 2), dormir=lambda s: None)
    historicos = [p for caminho, p in pedidos if caminho == "/v1/archive"]
    assert len(historicos) == 8
    assert (historicos[0]["start_date"], historicos[0]["end_date"]) == ("2026-10-24", "2026-11-01")


def test_sem_lacuna_nao_pede_historico(semeado, settings):
    falso = OpenMeteoFalso()
    _importar(semeado, settings, falso)
    falso = OpenMeteoFalso()
    importar_clima(semeado, settings, falso.cliente(), date(2026, 10, 26), dormir=lambda s: None)
    assert falso.chamadas == ["/v1/forecast"] * 8
