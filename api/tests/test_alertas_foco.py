import math
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy import select

from app.alertas import Situacao, TipoAlerta, alertas_ativos
from app.estados import Estado
from app.focos import FocoPerto, atualizar_alertas_fazenda
from app.modelos import Alerta, ClimaDiario, Fazenda, FocoCalor
from app.telemetria import registrar_leituras
from tests.test_telemetria import INICIO, MEIO_ROTA, ids, leitura_em  # noqa: F401

AGORA_REAL = datetime.now(UTC).replace(microsecond=0)
HOJE_LOCAL = AGORA_REAL.astimezone(ZoneInfo("America/Campo_Grande")).date()


def _situacao(estado, foco=None):
    return Situacao(
        estado=estado, velocidade_kmh=60, momento=INICIO, parado_desde=None,
        distancia_local_m=5000, fora_da_rota_seguidas=0, inicio_trecho=None,
        eta_prevista=None, eta_atual=None, foco_rota=foco,
    )


def test_foco_na_rota_so_vale_em_transito(settings):
    foco = FocoPerto(1, 2000, AGORA_REAL, None)
    assert TipoAlerta.FOCO_PROXIMO_ROTA in alertas_ativos(_situacao(Estado.EM_TRANSITO_CARREGADO, foco), settings)
    assert TipoAlerta.FOCO_PROXIMO_ROTA in alertas_ativos(_situacao(Estado.EM_TRANSITO_VAZIO, foco), settings)
    assert TipoAlerta.FOCO_PROXIMO_ROTA not in alertas_ativos(_situacao(Estado.CARREGANDO, foco), settings)
    assert TipoAlerta.FOCO_PROXIMO_ROTA not in alertas_ativos(_situacao(Estado.EM_TRANSITO_CARREGADO), settings)


def _ao_lado_da_rota(km):
    # A rota de teste vai de (-51.95, -20.95) a (-51.76, -20.62); anda `km` na perpendicular.
    lat = MEIO_ROTA[1]
    m_lon, m_lat = 111_320 * math.cos(math.radians(lat)), 110_600
    dx, dy = 0.19 * m_lon, 0.33 * m_lat
    norma = math.hypot(dx, dy)
    ux, uy = dy / norma, -dx / norma
    return (MEIO_ROTA[0] + ux * km * 1000 / m_lon, MEIO_ROTA[1] + uy * km * 1000 / m_lat)


def _foco(sessao, ponto, horas_atras=1.0, chave=None):
    foco = FocoCalor(
        geom=from_shape(Point(*ponto), srid=4326), satelite="NOAA-20",
        detectado_em=AGORA_REAL - timedelta(hours=horas_atras), municipio="TRÊS LAGOAS",
        chave=chave or f"{ponto}|{horas_atras}",
    )
    sessao.add(foco)
    sessao.flush()
    return foco


def _enviar(sessao, c, f, estado, minuto):
    registrar_leituras(sessao, [leitura_em(c, f, estado, minuto)], agora_real=AGORA_REAL)


def _alertas(sessao, tipo):
    return sessao.scalars(select(Alerta).where(Alerta.tipo == tipo).order_by(Alerta.id)).all()


def test_foco_perto_da_rota_abre_alerta(sessao, ids):
    foco = _foco(sessao, _ao_lado_da_rota(2))
    c, f = ids["caminhoes"][0], ids["fazenda"]
    _enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    [alerta] = _alertas(sessao, "FOCO_PROXIMO_ROTA")
    assert alerta.status == "ABERTO" and alerta.caminhao_id == c and alerta.foco_id == foco.id
    assert alerta.mensagem.startswith("Foco a 2,0 km da rota da ")
    # Relógio simulado no alerta, como os de logística.
    assert alerta.aberto_em == INICIO


def test_foco_longe_da_rota_nao_abre(sessao, ids):
    _foco(sessao, _ao_lado_da_rota(4))
    _enviar(sessao, ids["caminhoes"][0], ids["fazenda"], "EM_TRANSITO_CARREGADO", 0)
    assert _alertas(sessao, "FOCO_PROXIMO_ROTA") == []


def test_foco_antigo_nao_abre(sessao, ids):
    _foco(sessao, _ao_lado_da_rota(1), horas_atras=30)
    _enviar(sessao, ids["caminhoes"][0], ids["fazenda"], "EM_TRANSITO_CARREGADO", 0)
    assert _alertas(sessao, "FOCO_PROXIMO_ROTA") == []


def test_foco_na_rota_nao_repete_e_fecha_ao_sair_do_transito(sessao, ids):
    _foco(sessao, _ao_lado_da_rota(2))
    c, f = ids["caminhoes"][0], ids["fazenda"]
    for m in range(3):
        _enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", m)
    assert [a.status for a in _alertas(sessao, "FOCO_PROXIMO_ROTA")] == ["ABERTO"]
    _enviar(sessao, c, f, "FILA_PATIO", 3)
    [alerta] = _alertas(sessao, "FOCO_PROXIMO_ROTA")
    assert alerta.status == "FECHADO" and alerta.fechado_em == INICIO + timedelta(minutes=3)


def _fazenda(sessao):
    return sessao.scalars(select(Fazenda).order_by(Fazenda.id)).first()


def _a_oeste_da_fazenda(fazenda, km):
    poligono = to_shape(fazenda.geom)
    lon, lat = min(poligono.exterior.coords, key=lambda p: p[0])
    return (lon - km * 1000 / (111_320 * math.cos(math.radians(lat))), lat)


def _alertas_da_fazenda(sessao, fazenda_id):
    return sessao.scalars(
        select(Alerta).where(Alerta.tipo == "FOCO_PROXIMO_FAZENDA", Alerta.fazenda_id == fazenda_id)
        .order_by(Alerta.id)
    ).all()


def test_foco_perto_da_fazenda_abre_um_alerta(semeado, settings):
    fazenda = _fazenda(semeado)
    foco = _foco(semeado, _a_oeste_da_fazenda(fazenda, 3))
    atualizar_alertas_fazenda(semeado, settings, AGORA_REAL, INICIO)
    [alerta] = _alertas_da_fazenda(semeado, fazenda.id)
    assert alerta.status == "ABERTO" and alerta.foco_id == foco.id and alerta.caminhao_id is None
    assert alerta.mensagem.startswith("Foco a 3,0 km, detectado às ")
    assert alerta.aberto_em == INICIO


def test_segundo_foco_perto_nao_abre_outro(semeado, settings):
    fazenda = _fazenda(semeado)
    _foco(semeado, _a_oeste_da_fazenda(fazenda, 3))
    atualizar_alertas_fazenda(semeado, settings, AGORA_REAL, INICIO)
    _foco(semeado, _a_oeste_da_fazenda(fazenda, 2))
    atualizar_alertas_fazenda(semeado, settings, AGORA_REAL, INICIO + timedelta(minutes=30))
    assert [a.status for a in _alertas_da_fazenda(semeado, fazenda.id)] == ["ABERTO"]


def test_sem_foco_na_janela_fecha(semeado, settings):
    fazenda = _fazenda(semeado)
    _foco(semeado, _a_oeste_da_fazenda(fazenda, 3), horas_atras=23)
    atualizar_alertas_fazenda(semeado, settings, AGORA_REAL, INICIO)
    depois = INICIO + timedelta(hours=2)
    atualizar_alertas_fazenda(semeado, settings, AGORA_REAL + timedelta(hours=2), depois)
    [alerta] = _alertas_da_fazenda(semeado, fazenda.id)
    assert alerta.status == "FECHADO" and alerta.fechado_em == depois


def test_foco_a_6_km_da_fazenda_nao_abre(semeado, settings):
    fazenda = _fazenda(semeado)
    _foco(semeado, _a_oeste_da_fazenda(fazenda, 6))
    atualizar_alertas_fazenda(semeado, settings, AGORA_REAL, INICIO)
    assert _alertas_da_fazenda(semeado, fazenda.id) == []


def test_mensagem_com_vento_vindo_do_foco(semeado, settings):
    fazenda = _fazenda(semeado)
    _foco(semeado, _a_oeste_da_fazenda(fazenda, 3))
    # Vento de oeste (270°) e foco a oeste: o vento traz o fogo.
    semeado.add(ClimaDiario(fazenda_id=fazenda.id, data=HOJE_LOCAL, ur_13h=30, chuva_mm=0,
                            vento_kmh=12, vento_dir=270))
    semeado.flush()
    atualizar_alertas_fazenda(semeado, settings, AGORA_REAL, INICIO)
    [alerta] = _alertas_da_fazenda(semeado, fazenda.id)
    assert alerta.mensagem.endswith("; vento das 13h sopra do foco para cá")


def test_foco_na_rota_nao_reabre_na_volta_para_o_mesmo_foco(sessao, ids):
    _foco(sessao, _ao_lado_da_rota(2))
    c, f = ids["caminhoes"][0], ids["fazenda"]
    _enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    _enviar(sessao, c, f, "FILA_PATIO", 1)
    _enviar(sessao, c, f, "EM_TRANSITO_VAZIO", 2)
    assert [a.status for a in _alertas(sessao, "FOCO_PROXIMO_ROTA")] == ["FECHADO"]


def test_foco_novo_na_rota_abre_de_novo(sessao, ids):
    _foco(sessao, _ao_lado_da_rota(2), chave="primeiro")
    c, f = ids["caminhoes"][0], ids["fazenda"]
    _enviar(sessao, c, f, "EM_TRANSITO_CARREGADO", 0)
    _enviar(sessao, c, f, "FILA_PATIO", 1)
    _foco(sessao, _ao_lado_da_rota(1), chave="segundo")
    _enviar(sessao, c, f, "EM_TRANSITO_VAZIO", 2)
    assert [a.status for a in _alertas(sessao, "FOCO_PROXIMO_ROTA")] == ["FECHADO", "ABERTO"]
