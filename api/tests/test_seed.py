import random
from pathlib import Path
import re
from collections import Counter

import pytest
from sqlalchemy import func, select

from app.config import Settings
from app.modelos import Caminhao, Fabrica, Fazenda, Motorista
from app.seed import carregar_areas, gerar_nomes, gerar_placas, semear


def test_placas_mercosul_unicas():
    placas = gerar_placas(20, random.Random(42))
    assert len(set(placas)) == 20
    assert all(re.fullmatch(r"TLG\d[A-Z]\d{2}", p) for p in placas)


def test_nomes_unicos():
    nomes = gerar_nomes(20, random.Random(1))
    assert len(set(nomes)) == 20 and all(" " in n for n in nomes)


def test_seed_reproduzivel(sessao):
    semear(sessao, Settings())
    placas = sessao.scalars(select(Caminhao.placa).order_by(Caminhao.id)).all()
    nomes = sessao.scalars(select(Motorista.nome).order_by(Motorista.id)).all()
    assert placas == gerar_placas(20, random.Random(42))
    assert len(set(nomes)) == 20


def test_seed_idempotente(sessao):
    semear(sessao, Settings())
    semear(sessao, Settings())
    assert sessao.scalar(select(func.count()).select_from(Caminhao)) == 20
    assert sessao.scalar(select(func.count()).select_from(Fazenda)) == 8
    assert sessao.scalar(select(func.count()).select_from(Fabrica)) == 1


def test_frota_12_rodotrem_8_tritrem(sessao):
    semear(sessao, Settings())
    caminhoes = sessao.scalars(select(Caminhao)).all()
    assert Counter(c.tipo for c in caminhoes) == {"rodotrem": 12, "tritrem": 8}
    assert {c.tipo: c.capacidade_t for c in caminhoes} == {"rodotrem": 55, "tritrem": 45}


def test_fazendas_sao_as_areas_do_mapbiomas(sessao):
    semear(sessao, Settings())
    nomes = sessao.scalars(select(Fazenda.nome).order_by(Fazenda.id)).all()
    assert nomes == [f"Área de eucalipto {i:02d}" for i in range(1, 9)]


def test_area_ha_bate_com_o_poligono(sessao):
    semear(sessao, Settings())
    for area_ha, medida in sessao.execute(
        select(Fazenda.area_ha, func.ST_Area(func.geography(Fazenda.geom)) / 10_000)
    ):
        assert area_ha == pytest.approx(medida, rel=0.01)


def test_centro_dentro_da_area(sessao):
    semear(sessao, Settings())
    assert all(sessao.scalars(select(func.ST_Within(Fazenda.centro, Fazenda.geom))))


def test_areas_a_ate_150_km_da_fabrica(sessao):
    semear(sessao, Settings())
    fabrica = select(Fabrica.geom).scalar_subquery()
    distancias = sessao.scalars(select(func.ST_Distance(func.geography(Fazenda.geom), func.geography(fabrica))))
    assert all(d <= 150_000 for d in distancias)


def test_sem_arquivo_de_areas_explica_como_gerar():
    with pytest.raises(FileNotFoundError, match="gerar_areas_eucalipto"):
        carregar_areas(Path("nao_existe.geojson"))
