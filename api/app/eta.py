"""ETA: distância restante na rota ÷ velocidade média das últimas leituras (SPEC seção 6)."""
from datetime import datetime, timedelta


def velocidade_media(velocidades: list[float], minimo_kmh: float) -> float:
    """Média das leituras, nunca abaixo do mínimo (para o ETA não estourar)."""
    if not velocidades:
        return minimo_kmh
    return max(minimo_kmh, sum(velocidades) / len(velocidades))


def calcular_eta(
    agora: datetime, restante_km: float, velocidades: list[float], minimo_kmh: float
) -> datetime:
    horas = restante_km / velocidade_media(velocidades, minimo_kmh)
    return agora + timedelta(hours=horas)
