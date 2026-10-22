import httpx
from geoalchemy2.shape import to_shape
import pytest
from shapely.geometry import Point
from sqlalchemy import func, select

from app.geo import distancia_km
from app.modelos import Fazenda, Rota
from shapely.geometry import box

from app.scripts.gerar_rotas import PONTOS_BORDA, gerar_rotas, ponto_carregamento, pontos_borda
from app.seed import semear
from tests.test_osrm import AMOSTRA, AMOSTRA_NEAREST




def cliente_que_responde(status: int, texto: str = "") -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, text=texto)))


def osrm_ok(pedidos: list | None = None) -> httpx.Client:
    """OSRM falso: /nearest devolve a amostra real, /route a rota de amostra."""

    def handler(req):
        if pedidos is not None:
            pedidos.append(req)
        return httpx.Response(200, text=AMOSTRA_NEAREST if "/nearest/" in req.url.path else AMOSTRA)

    return httpx.Client(transport=httpx.MockTransport(handler))


def nearest_com_distancias(distancias: list[float]) -> httpx.Client:
    """Cada ponto da borda recebe uma estrada em (lon + 0.01, lat) com a distância da lista, em ordem."""
    fila = iter(distancias)

    def handler(req):
        lon, lat = map(float, req.url.path.rsplit("/", 1)[1].split(","))
        corpo = {"code": "Ok", "waypoints": [{"location": [lon + 0.01, lat], "distance": next(fila)}]}
        return httpx.Response(200, json=corpo)

    return httpx.Client(transport=httpx.MockTransport(handler))


QUADRADO = box(-52.0, -20.6, -51.9, -20.5)
CENTRO = (-51.95, -20.55)


def test_pontos_borda_no_anel():
    pontos = pontos_borda(QUADRADO, 12)
    assert len(pontos) == 12
    assert all(QUADRADO.exterior.distance(Point(p)) < 1e-9 for p in pontos)


def test_ponto_carregamento_escolhe_a_estrada_mais_perto(settings):
    distancias = [900.0, 400.0, 120.0, 800.0] + [1000.0] * 8
    pausas = []
    ponto, aviso = ponto_carregamento(nearest_com_distancias(distancias), settings, QUADRADO, CENTRO, pausas.append, "Área X")
    terceiro = pontos_borda(QUADRADO, 12)[2]
    assert ponto == pytest.approx((terceiro[0] + 0.01, terceiro[1]))
    assert aviso is None
    assert pausas == [1.0] * 12  # uma pausa antes de cada requisição


def test_ponto_carregamento_sem_osrm_usa_o_centro(settings):
    ponto, aviso = ponto_carregamento(cliente_que_responde(500), settings, QUADRADO, CENTRO, lambda s: None, "Área X")
    assert ponto == CENTRO
    assert "Área X" in aviso


def test_usa_linha_reta_quando_osrm_falha(sessao, settings):
    semear(sessao, settings)
    avisos = gerar_rotas(sessao, settings, cliente_que_responde(503), dormir=lambda s: None)
    rotas = sessao.scalars(select(Rota)).all()
    # cada área avisa duas vezes: carregamento no centro e rota em linha reta
    assert len(rotas) == 8 and len(avisos) == 16
    primeira = sessao.scalars(select(Fazenda).order_by(Fazenda.id)).first()
    centro = to_shape(primeira.centro)
    rota = next(r for r in rotas if r.fazenda_id == primeira.id)
    # sem /nearest a rota sai do centro da área
    assert rota.distancia_km == pytest.approx(distancia_km((centro.x, centro.y), (-51.76, -20.62)) * 1.3, rel=0.01)
    assert all(primeira.nome in a for a in avisos[:2])


def test_conexao_recusada_tambem_cai_no_fallback(sessao, settings):
    semear(sessao, settings)

    def recusa(req):
        raise httpx.ConnectError("recusada", request=req)

    cliente = httpx.Client(transport=httpx.MockTransport(recusa))
    assert len(gerar_rotas(sessao, settings, cliente, dormir=lambda s: None)) == 16


def test_uma_requisicao_por_vez_com_1s(sessao, settings):
    semear(sessao, settings)
    pausas = []
    avisos = gerar_rotas(sessao, settings, osrm_ok(), dormir=pausas.append)
    assert avisos == []
    # 8 áreas × (12 pontos da borda + 1 rota), com 1 s entre requisições
    assert pausas == [1.0] * (8 * (PONTOS_BORDA + 1) - 1)


def test_idempotente(sessao, settings):
    semear(sessao, settings)
    gerar_rotas(sessao, settings, cliente_que_responde(503), dormir=lambda s: None)
    gerar_rotas(sessao, settings, osrm_ok(), dormir=lambda s: None)
    assert sessao.scalar(select(func.count()).select_from(Rota)) == 8
    # a segunda execução substituiu as linhas retas pela rota do OSRM
    assert sessao.scalar(select(func.min(func.ST_NPoints(Rota.geom)))) > 2


def test_somente_faltantes_nao_consulta_quem_ja_tem_rota(sessao, settings):
    # Usado na subida do compose: reiniciar não pode bater no OSRM de novo.
    semear(sessao, settings)
    gerar_rotas(sessao, settings, osrm_ok(), dormir=lambda s: None)
    pedidos = []
    gerar_rotas(sessao, settings, osrm_ok(pedidos), dormir=lambda s: None, somente_faltantes=True)
    assert pedidos == []


def test_rota_sai_do_ponto_de_carregamento(sessao, settings):
    semear(sessao, settings)
    pedidos = []
    gerar_rotas(sessao, settings, osrm_ok(pedidos), dormir=lambda s: None)
    rotas = [r for r in pedidos if "/route/" in r.url.path]
    assert len(rotas) == 8
    # origem é a estrada da amostra de /nearest, não o centro da área
    assert all(r.url.path.split("/")[-1].startswith("-51.725739,-20.407791;") for r in rotas)


def test_osrm_travado_nao_segura_a_subida(sessao, settings):
    # Servidor que trava (timeout): depois da primeira falha no /nearest, nenhuma área consulta de novo.
    semear(sessao, settings)
    pedidos = []

    def trava(req):
        pedidos.append(req.url.path)
        raise httpx.ReadTimeout("travou", request=req)

    gerar_rotas(sessao, settings, httpx.Client(transport=httpx.MockTransport(trava)), dormir=lambda s: None)
    assert sum("/nearest/" in p for p in pedidos) == 1
    assert sum("/route/" in p for p in pedidos) == 8


def test_estrada_inexistente_num_ponto_nao_desliga_o_osrm(settings):
    # NoSegment num ponto é resposta válida: os outros pontos continuam sendo consultados.
    respostas = iter([{"code": "NoSegment", "waypoints": []}] + [{"code": "Ok", "waypoints": [{"location": [-51.9, -20.5], "distance": 50.0}]}] * 11)
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=next(respostas))))
    ponto, aviso = ponto_carregamento(cliente, settings, QUADRADO, CENTRO, lambda s: None, "Área X")
    assert ponto == (-51.9, -20.5) and aviso is None
