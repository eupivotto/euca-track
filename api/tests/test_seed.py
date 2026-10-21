import random
import re
from collections import Counter

from sqlalchemy import func, select

from app.config import Settings
from app.modelos import Caminhao, Fabrica, Fazenda, Motorista
from app.seed import gerar_nomes, gerar_placas, semear


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


def test_fazendas_do_spec(sessao):
    semear(sessao, Settings())
    santa_luzia = sessao.scalar(select(Fazenda).where(Fazenda.nome == "Fazenda Santa Luzia"))
    assert santa_luzia.area_ha == 3200
    lon, lat = sessao.execute(
        select(func.ST_X(Fazenda.centro), func.ST_Y(Fazenda.centro)).where(Fazenda.id == santa_luzia.id)
    ).one()
    assert (lon, lat) == (-51.95, -20.95)
