from datetime import datetime, timedelta, timezone

from app.eta import calcular_eta, velocidade_media

AGORA = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)


def test_eta_pela_media_das_leituras():
    assert calcular_eta(AGORA, 50, [40, 60], 20) == AGORA + timedelta(hours=1)


def test_eta_usa_velocidade_minima():
    assert calcular_eta(AGORA, 50, [0, 0, 10], 20) == AGORA + timedelta(hours=2.5)


def test_media_sem_leituras_e_o_minimo():
    assert velocidade_media([], 20) == 20


def test_chegou_eta_e_agora():
    assert calcular_eta(AGORA, 0, [60], 20) == AGORA
