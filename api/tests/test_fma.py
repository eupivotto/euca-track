from datetime import date, timedelta

import pytest

from app.config import Settings
from app.fma import ClasseRisco, DiaClima, classificar, fma_do_dia, serie_fma

# H = 50% dá parcela 100/50 = 2,0; FMA de ontem = 10.


@pytest.mark.parametrize(
    ("chuva", "esperado"),
    [
        (0, 12.0), (2.4, 12.0),
        (2.5, 9.0), (4.9, 9.0),
        (5.0, 6.0), (9.9, 6.0),
        (10.0, 4.0), (12.9, 4.0),
        (13.0, 0.0),
    ],
)
def test_cada_faixa_de_chuva(chuva, esperado):
    assert fma_do_dia(10, 50, chuva) == pytest.approx(esperado)


@pytest.mark.parametrize(
    ("chuva", "esperado"),
    [(2.45, 9.0), (2.44, 12.0), (12.95, 0.0), (4.95, 6.0)],
)
def test_chuva_arredondada_a_uma_casa_antes_da_faixa(chuva, esperado):
    assert fma_do_dia(10, 50, chuva) == pytest.approx(esperado)


def _dias(*valores):
    inicio = date(2026, 10, 1)
    return [DiaClima(inicio + timedelta(days=i), ur, chuva) for i, (ur, chuva) in enumerate(valores)]


def test_serie_zera_e_recomeca_no_dia_seguinte():
    saida = serie_fma(_dias((50, 0), (50, 20), (50, 0)), Settings())
    assert [round(fma, 1) for _, fma, _ in saida] == [2.0, 0.0, 2.0]
    assert [d for d, _, _ in saida] == [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)]


@pytest.mark.parametrize("ur_ruim", [None, 0])
def test_dia_sem_umidade_fica_fora_e_nao_mexe_no_acumulado(ur_ruim):
    saida = serie_fma(_dias((50, 0), (ur_ruim, 0), (50, 0)), Settings())
    assert [d for d, _, _ in saida] == [date(2026, 10, 1), date(2026, 10, 3)]
    assert [round(fma, 1) for _, fma, _ in saida] == [2.0, 4.0]


def test_dia_sem_chuva_informada_fica_fora():
    saida = serie_fma(_dias((50, 0), (50, None), (50, 0)), Settings())
    assert [round(fma, 1) for _, fma, _ in saida] == [2.0, 4.0]


def test_serie_ordena_por_data_e_classifica():
    dias = list(reversed(_dias((25, 0), (25, 0))))  # parcela 4,0
    saida = serie_fma(dias, Settings())
    assert [(round(f, 1), c) for _, f, c in saida] == [
        (4.0, ClasseRisco.MEDIO), (8.0, ClasseRisco.MEDIO),
    ]


@pytest.mark.parametrize(
    ("fma", "classe"),
    [
        (0, ClasseRisco.NULO), (1.0, ClasseRisco.NULO), (1.04, ClasseRisco.NULO),
        (1.05, ClasseRisco.PEQUENO), (1.1, ClasseRisco.PEQUENO), (3.0, ClasseRisco.PEQUENO),
        (3.1, ClasseRisco.MEDIO), (8.0, ClasseRisco.MEDIO),
        (8.1, ClasseRisco.ALTO), (20.0, ClasseRisco.ALTO),
        (20.1, ClasseRisco.MUITO_ALTO), (35, ClasseRisco.MUITO_ALTO),
    ],
)
def test_classes_nos_limites(fma, classe):
    assert classificar(fma, Settings()) is classe


def test_limites_das_classes_vem_da_config():
    assert classificar(1.5, Settings(fma_limite_nulo=2.0)) is ClasseRisco.NULO
