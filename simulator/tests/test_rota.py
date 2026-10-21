import pytest

from sim.rota import comprimento_km, ponto_na_linha

LINHA = [(-52.0, -21.0), (-52.0, -20.9), (-51.9, -20.9)]


def test_comprimento_soma_os_segmentos():
    # 0,1° de latitude ~ 11,1 km; 0,1° de longitude a -20,9° ~ 10,4 km
    assert comprimento_km(LINHA) == pytest.approx(11.12 + 10.39, abs=0.1)


def test_inicio_meio_e_fim():
    total = comprimento_km(LINHA)
    assert ponto_na_linha(LINHA, 0) == LINHA[0]
    assert ponto_na_linha(LINHA, total) == pytest.approx(LINHA[-1])
    meio_primeiro = ponto_na_linha(LINHA, comprimento_km(LINHA[:2]) / 2)
    assert meio_primeiro == pytest.approx((-52.0, -20.95), abs=1e-4)


def test_ponto_no_segundo_segmento():
    km = comprimento_km(LINHA[:2]) + comprimento_km(LINHA[1:]) / 2
    assert ponto_na_linha(LINHA, km) == pytest.approx((-51.95, -20.9), abs=1e-4)


def test_fora_da_linha_fica_nas_pontas():
    assert ponto_na_linha(LINHA, -5) == LINHA[0]
    assert ponto_na_linha(LINHA, 10_000) == pytest.approx(LINHA[-1])


def test_segmento_de_comprimento_zero():
    linha = [(-52.0, -21.0), (-52.0, -21.0), (-51.9, -21.0)]
    assert ponto_na_linha(linha, 1) == pytest.approx((-51.9904, -21.0), abs=1e-3)
