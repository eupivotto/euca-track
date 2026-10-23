from contextlib import nullcontext
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import func, select

from app.config import Settings
from app.modelos import Alerta, Fazenda, FocoCalor
from app.rotinas import rodar_clima, rodar_focos
from tests.conftest import FIXTURES

AMOSTRA = (FIXTURES / "focos_diario_br_amostra.csv").read_bytes()
# Os focos da amostra são de 21/10 às 17:32 UTC.
DEPOIS_DA_AMOSTRA = datetime(2026, 10, 21, 20, 0, tzinfo=UTC)


def _quebrado():
    def handler(request):
        raise httpx.ConnectError("fora do ar", request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _fabrica(sessao):
    return lambda: nullcontext(sessao)


def test_rodar_focos_nao_sobe_excecao(semeado, settings, capsys, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("banco caiu")

    monkeypatch.setattr("app.rotinas.importar_focos", explode)
    rodar_focos(_fabrica(semeado), settings, _quebrado(), DEPOIS_DA_AMOSTRA)
    assert "banco caiu" in capsys.readouterr().out


def test_rodar_focos_com_fonte_fora_do_ar_avisa(semeado, settings, capsys):
    rodar_focos(_fabrica(semeado), settings, _quebrado(), DEPOIS_DA_AMOSTRA)
    assert "não baixados" in capsys.readouterr().out


def test_rodar_clima_com_fonte_fora_do_ar_avisa(semeado, settings, capsys, monkeypatch):
    monkeypatch.setattr("app.clima.PAUSA_S", 0)
    rodar_clima(_fabrica(semeado), settings, _quebrado(), date(2026, 10, 23))
    saida = capsys.readouterr().out
    assert "clima não atualizado" in saida and "Área de eucalipto 01" in saida


def test_rodar_clima_nao_sobe_excecao(semeado, settings, capsys, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("erro inesperado")

    monkeypatch.setattr("app.rotinas.importar_clima", explode)
    rodar_clima(_fabrica(semeado), settings, _quebrado(), date(2026, 10, 23))
    assert "erro inesperado" in capsys.readouterr().out


def test_rodar_focos_grava_e_abre_alerta_de_fazenda(semeado):
    # O foco mais perto da amostra fica a ~6,2 km da Área de eucalipto 04.
    settings = Settings(foco_fazenda_km=7)
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=AMOSTRA)))
    rodar_focos(_fabrica(semeado), settings, cliente, DEPOIS_DA_AMOSTRA)
    assert semeado.scalar(select(func.count()).select_from(FocoCalor)) == 5
    [alerta] = semeado.scalars(select(Alerta).where(Alerta.tipo == "FOCO_PROXIMO_FAZENDA")).all()
    assert semeado.get(Fazenda, alerta.fazenda_id).nome == "Área de eucalipto 04"
    assert alerta.mensagem.startswith("Foco a 6,2 km, detectado às 13h32")
