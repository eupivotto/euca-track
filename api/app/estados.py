from enum import StrEnum


class Estado(StrEnum):
    """Estados do ciclo da viagem (SPEC seção 4)."""

    CARREGANDO = "CARREGANDO"
    EM_TRANSITO_CARREGADO = "EM_TRANSITO_CARREGADO"
    FILA_PATIO = "FILA_PATIO"
    PESAGEM = "PESAGEM"
    DESCARGA = "DESCARGA"
    EM_TRANSITO_VAZIO = "EM_TRANSITO_VAZIO"


# Estados em que o caminhão está com a madeira a bordo.
ESTADOS_CARREGADO = {
    Estado.EM_TRANSITO_CARREGADO,
    Estado.FILA_PATIO,
    Estado.PESAGEM,
    Estado.DESCARGA,
}
