from enum import StrEnum


class Estado(StrEnum):
    """Estados do ciclo da viagem (SPEC seção 4). Mesmos valores da API."""

    CARREGANDO = "CARREGANDO"
    EM_TRANSITO_CARREGADO = "EM_TRANSITO_CARREGADO"
    FILA_PATIO = "FILA_PATIO"
    PESAGEM = "PESAGEM"
    DESCARGA = "DESCARGA"
    EM_TRANSITO_VAZIO = "EM_TRANSITO_VAZIO"


CICLO = list(Estado)


def proximo_estado(estado: Estado) -> Estado:
    return CICLO[(CICLO.index(estado) + 1) % len(CICLO)]
