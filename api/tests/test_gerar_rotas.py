import httpx
import pytest
from sqlalchemy import func, select

from app.modelos import Fazenda, Rota
from app.scripts.gerar_rotas import gerar_rotas
from app.seed import semear
from tests.test_osrm import AMOSTRA


def cliente_que_responde(status: int, texto: str = "") -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, text=texto)))


def test_usa_linha_reta_quando_osrm_falha(sessao, settings):
    semear(sessao, settings)
    avisos = gerar_rotas(sessao, settings, cliente_que_responde(503), dormir=lambda s: None)
    rotas = sessao.scalars(select(Rota)).all()
    assert len(rotas) == 8 and len(avisos) == 8
    santa_luzia = sessao.scalar(select(Fazenda.id).where(Fazenda.nome == "Fazenda Santa Luzia"))
    rota = next(r for r in rotas if r.fazenda_id == santa_luzia)
    assert rota.distancia_km == pytest.approx(41.7 * 1.3, abs=0.7)
    assert "Fazenda Santa Luzia" in avisos[0]


def test_conexao_recusada_tambem_cai_no_fallback(sessao, settings):
    semear(sessao, settings)

    def recusa(req):
        raise httpx.ConnectError("recusada", request=req)

    cliente = httpx.Client(transport=httpx.MockTransport(recusa))
    assert len(gerar_rotas(sessao, settings, cliente, dormir=lambda s: None)) == 8


def test_uma_requisicao_por_vez_com_1s(sessao, settings):
    semear(sessao, settings)
    pausas = []
    avisos = gerar_rotas(sessao, settings, cliente_que_responde(200, AMOSTRA), dormir=pausas.append)
    assert avisos == []
    assert pausas == [1.0] * 7  # entre 8 requisições


def test_idempotente(sessao, settings):
    semear(sessao, settings)
    gerar_rotas(sessao, settings, cliente_que_responde(503), dormir=lambda s: None)
    gerar_rotas(sessao, settings, cliente_que_responde(200, AMOSTRA), dormir=lambda s: None)
    assert sessao.scalar(select(func.count()).select_from(Rota)) == 8
    # a segunda execução substituiu as linhas retas pela rota do OSRM
    assert sessao.scalar(select(func.min(func.ST_NPoints(Rota.geom)))) > 2


def test_somente_faltantes_nao_consulta_quem_ja_tem_rota(sessao, settings):
    # Usado na subida do compose: reiniciar não pode bater no OSRM de novo.
    semear(sessao, settings)
    gerar_rotas(sessao, settings, cliente_que_responde(200, AMOSTRA), dormir=lambda s: None)
    pedidos = []

    def conta(req):
        pedidos.append(req)
        return httpx.Response(200, text=AMOSTRA)

    cliente = httpx.Client(transport=httpx.MockTransport(conta))
    gerar_rotas(sessao, settings, cliente, dormir=lambda s: None, somente_faltantes=True)
    assert pedidos == []
