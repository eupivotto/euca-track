"""Dados de referência fictícios (SPEC seções 3 e 4).

Uso: python -m app.seed
"""
import random
import string

from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.geo import quadrado_fazenda
from app.modelos import Caminhao, Fabrica, Fazenda, Motorista

FABRICA = ("Fábrica Modelo Três Lagoas", -20.6200, -51.7600)

FAZENDAS = [
    ("Fazenda Santa Luzia", -20.9500, -51.9500, 3200),
    ("Fazenda Boa Vista", -20.4500, -52.0500, 2800),
    ("Fazenda Três Irmãos", -21.1000, -52.3000, 4100),
    ("Fazenda Água Limpa", -20.3000, -51.8500, 2500),
    ("Fazenda Cervo", -20.8000, -52.4000, 3600),
    ("Fazenda São Bento", -21.2500, -51.9000, 3000),
    ("Fazenda Morada do Sol", -20.5500, -52.5500, 4400),
    ("Fazenda Ribeirão", -20.1500, -52.2500, 2700),
]

TOTAL_CAMINHOES = 20
TOTAL_RODOTREM = 12

PRENOMES = [
    "Antônio", "Carlos", "Edson", "Fábio", "Gilberto", "Hélio", "Ivan", "Jair",
    "Luciano", "Márcio", "Nilton", "Osmar", "Paulo", "Reinaldo", "Sérgio",
    "Valdir", "Wagner", "Adriana", "Cláudia", "Rosana",
]
SOBRENOMES = [
    "Almeida", "Barbosa", "Cardoso", "Dias", "Ferreira", "Gomes", "Lima",
    "Martins", "Nogueira", "Oliveira", "Pereira", "Ribeiro", "Santos", "Teixeira",
]


def gerar_placas(n: int, rng: random.Random) -> list[str]:
    """Placas no padrão Mercosul LLLNLNN com prefixo TLG, sem repetição."""
    placas: list[str] = []
    while len(placas) < n:
        placa = (
            f"TLG{rng.randrange(10)}{rng.choice(string.ascii_uppercase)}"
            f"{rng.randrange(100):02d}"
        )
        if placa not in placas:
            placas.append(placa)
    return placas


def gerar_nomes(n: int, rng: random.Random) -> list[str]:
    nomes: list[str] = []
    while len(nomes) < n:
        nome = f"{rng.choice(PRENOMES)} {rng.choice(SOBRENOMES)}"
        if nome not in nomes:
            nomes.append(nome)
    return nomes


def semear(sessao: Session, settings: Settings) -> None:
    """Grava fábrica, fazendas, motoristas e caminhões. Não faz nada se já houver dados."""
    if sessao.scalar(select(Fabrica.id).limit(1)) is not None:
        return

    nome, lat, lon = FABRICA
    sessao.add(Fabrica(nome=nome, geom=from_shape(Point(lon, lat), srid=4326)))

    for nome, lat, lon, area in FAZENDAS:
        sessao.add(
            Fazenda(
                nome=nome,
                area_ha=area,
                centro=from_shape(Point(lon, lat), srid=4326),
                geom=from_shape(Polygon(quadrado_fazenda(lat, lon, area)), srid=4326),
            )
        )

    # Placas primeiro: a ordem dos sorteios faz parte da reprodutibilidade.
    rng = random.Random(settings.seed)
    placas = gerar_placas(TOTAL_CAMINHOES, rng)
    nomes = gerar_nomes(TOTAL_CAMINHOES, rng)

    for i, (placa, nome) in enumerate(zip(placas, nomes)):
        motorista = Motorista(nome=nome)
        sessao.add(motorista)
        rodotrem = i < TOTAL_RODOTREM
        sessao.add(
            Caminhao(
                placa=placa,
                tipo="rodotrem" if rodotrem else "tritrem",
                capacidade_t=settings.capacidade_rodotrem_t if rodotrem else settings.capacidade_tritrem_t,
                motorista=motorista,
            )
        )
    sessao.flush()


if __name__ == "__main__":
    from app.db import SessionLocal

    with SessionLocal() as s:
        semear(s, get_settings())
        s.commit()
    print("Seed concluído.")
