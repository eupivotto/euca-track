from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.alertas import Situacao, TipoAlerta, alertas_ativos
from app.estados import Estado

MOMENTO = datetime(2026, 10, 20, 10, 30, tzinfo=timezone.utc)
INICIO = MOMENTO - timedelta(minutes=30)

# Carregado a 60 km/h no meio da rota, no horário: trecho previsto de 60 min.
NORMAL = Situacao(
    estado=Estado.EM_TRANSITO_CARREGADO,
    velocidade_kmh=60,
    momento=MOMENTO,
    parado_desde=None,
    distancia_local_m=20_000,
    fora_da_rota_seguidas=0,
    inicio_trecho=INICIO,
    eta_prevista=INICIO + timedelta(minutes=60),
    eta_atual=INICIO + timedelta(minutes=60),
)


def situacao(**mudancas):
    return replace(NORMAL, **mudancas)


def test_sem_alerta_em_situacao_normal(settings):
    assert alertas_ativos(situacao(), settings) == set()


def test_velocidade_acima_de_80(settings):
    assert TipoAlerta.VELOCIDADE in alertas_ativos(situacao(velocidade_kmh=80.5), settings)
    assert TipoAlerta.VELOCIDADE not in alertas_ativos(situacao(velocidade_kmh=80), settings)


def test_parada_depois_de_15_min_fora_de_local(settings):
    s = situacao(velocidade_kmh=0, parado_desde=MOMENTO - timedelta(minutes=16))
    assert TipoAlerta.PARADA in alertas_ativos(s, settings)


def test_parada_de_15_min_ainda_nao_alerta(settings):
    s = situacao(velocidade_kmh=0, parado_desde=MOMENTO - timedelta(minutes=15))
    assert TipoAlerta.PARADA not in alertas_ativos(s, settings)


def test_parada_perto_da_fabrica_nao_alerta(settings):
    s = situacao(velocidade_kmh=0, parado_desde=MOMENTO - timedelta(minutes=40),
                 distancia_local_m=400)
    assert TipoAlerta.PARADA not in alertas_ativos(s, settings)


def test_parada_no_patio_nao_alerta(settings):
    s = situacao(estado=Estado.FILA_PATIO, velocidade_kmh=0,
                 parado_desde=MOMENTO - timedelta(hours=1))
    assert alertas_ativos(s, settings) == set()


def test_desvio_so_na_segunda_leitura_fora(settings):
    assert TipoAlerta.DESVIO_ROTA not in alertas_ativos(situacao(fora_da_rota_seguidas=1), settings)
    assert TipoAlerta.DESVIO_ROTA in alertas_ativos(situacao(fora_da_rota_seguidas=2), settings)


def test_desvio_fora_do_transito_nao_alerta(settings):
    s = situacao(estado=Estado.CARREGANDO, velocidade_kmh=0, fora_da_rota_seguidas=5)
    assert alertas_ativos(s, settings) == set()


def test_atraso_acima_de_20_por_cento(settings):
    # Trecho previsto de 60 min: ETA atual dando 73 min alerta; 72 min (exatamente 20%) não.
    assert TipoAlerta.ATRASO in alertas_ativos(
        situacao(eta_atual=INICIO + timedelta(minutes=73)), settings
    )
    assert TipoAlerta.ATRASO not in alertas_ativos(
        situacao(eta_atual=INICIO + timedelta(minutes=72)), settings
    )


def test_sem_previsto_nao_avalia_atraso(settings):
    assert alertas_ativos(situacao(eta_prevista=None, eta_atual=None), settings) == set()


def test_varios_alertas_ao_mesmo_tempo(settings):
    s = situacao(velocidade_kmh=85, fora_da_rota_seguidas=3)
    assert alertas_ativos(s, settings) == {TipoAlerta.VELOCIDADE, TipoAlerta.DESVIO_ROTA}


def test_atraso_espera_a_carencia_do_inicio_do_trecho(settings):
    # 5 min de trecho com ETA estourado: ainda dentro da carência, não alerta.
    s = situacao(momento=INICIO + timedelta(minutes=5), eta_atual=INICIO + timedelta(minutes=180))
    assert TipoAlerta.ATRASO not in alertas_ativos(s, settings)
    s = situacao(momento=INICIO + timedelta(minutes=10), eta_atual=INICIO + timedelta(minutes=180))
    assert TipoAlerta.ATRASO in alertas_ativos(s, settings)
