"""Fórmula de Monte Alegre (Soares, 1972) e classes de risco (SPEC seção 7)."""
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.config import Settings


class ClasseRisco(StrEnum):
    NULO = "NULO"
    PEQUENO = "PEQUENO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"
    MUITO_ALTO = "MUITO_ALTO"


@dataclass
class DiaClima:
    data: date
    ur_13h: float | None
    chuva_mm: float | None


def _uma_casa(valor: float) -> float:
    # str() evita que 2,45 vire 2,4499999… antes do arredondamento meio para cima.
    return float(Decimal(str(valor)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def fma_do_dia(fma_ontem: float, ur_13h: float, chuva_mm: float) -> float:
    parcela = 100 / ur_13h
    chuva = _uma_casa(chuva_mm)
    if chuva <= 2.4:
        return fma_ontem + parcela
    if chuva <= 4.9:
        return fma_ontem * 0.7 + parcela
    if chuva <= 9.9:
        return fma_ontem * 0.4 + parcela
    if chuva <= 12.9:
        return fma_ontem * 0.2 + parcela
    return 0.0


def classificar(fma: float, settings: Settings) -> ClasseRisco:
    valor = _uma_casa(fma)
    if valor <= settings.fma_limite_nulo:
        return ClasseRisco.NULO
    if valor <= settings.fma_limite_pequeno:
        return ClasseRisco.PEQUENO
    if valor <= settings.fma_limite_medio:
        return ClasseRisco.MEDIO
    if valor <= settings.fma_limite_alto:
        return ClasseRisco.ALTO
    return ClasseRisco.MUITO_ALTO


def serie_fma(dias: list[DiaClima], settings: Settings) -> list[tuple[date, float, ClasseRisco]]:
    """FMA acumulada em ordem de data, partindo de zero.

    Dia sem UR válida ou sem chuva (lacuna do modelo) fica fora da saída e o
    dia seguinte soma sobre o último dia válido.
    """
    saida = []
    acumulado = 0.0
    for dia in sorted(dias, key=lambda d: d.data):
        if dia.ur_13h is None or dia.ur_13h <= 0 or dia.chuva_mm is None:
            continue
        acumulado = fma_do_dia(acumulado, dia.ur_13h, dia.chuva_mm)
        saida.append((dia.data, acumulado, classificar(acumulado, settings)))
    return saida
