from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.config import Settings
from app.focos import rumo_graus, texto_foco, vento_a_favor

FUSO = ZoneInfo("America/Campo_Grande")
ALVO = (-52.0, -20.5)


def test_rumo_para_norte_leste_e_sul():
    assert rumo_graus(ALVO, (-52.0, -20.4)) == pytest.approx(0, abs=0.5)
    assert rumo_graus(ALVO, (-51.9, -20.5)) == pytest.approx(90, abs=0.5)
    assert rumo_graus(ALVO, (-52.0, -20.6)) == pytest.approx(180, abs=0.5)
    assert rumo_graus(ALVO, (-52.1, -20.5)) == pytest.approx(270, abs=0.5)


def test_vento_vindo_do_foco_e_a_favor():
    # Foco ao norte (rumo 0°) e vento soprando de norte (0°): traz o fogo.
    assert vento_a_favor(0, 0, 45) is True


def test_vento_vindo_do_lado_oposto_e_contra():
    assert vento_a_favor(0, 180, 45) is False


def test_angulo_atravessa_o_norte():
    assert vento_a_favor(350, 20, 45) is True
    assert vento_a_favor(20, 350, 45) is True


def test_diferenca_exata_do_limite_nao_conta():
    assert vento_a_favor(45, 0, 45) is False
    assert vento_a_favor(44.9, 0, 45) is True


def test_sem_vento_nao_sabe():
    assert vento_a_favor(None, 0, 45) is None


def test_texto_com_vento_a_favor():
    detectado = datetime(2026, 10, 21, 18, 32, tzinfo=UTC)
    assert texto_foco(2140, detectado, True, FUSO) == (
        "Foco a 2,1 km, detectado às 14h32; vento das 13h sopra do foco para cá"
    )


def test_texto_com_vento_contra():
    detectado = datetime(2026, 10, 21, 18, 32, tzinfo=UTC)
    assert texto_foco(2140, detectado, False, FUSO).endswith(
        "; vento das 13h não sopra do foco para cá"
    )


def test_texto_sem_vento():
    detectado = datetime(2026, 10, 21, 3, 5, tzinfo=UTC)
    assert texto_foco(940, detectado, None, FUSO) == "Foco a 0,9 km, detectado às 23h05"


def test_parametros_dos_alertas_de_foco():
    s = Settings()
    assert s.foco_vento_angulo_max == 45 and s.foco_janela_h == 24
    assert s.foco_fazenda_km == 5 and s.foco_rota_km == 3
