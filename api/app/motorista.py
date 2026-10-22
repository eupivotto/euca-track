"""Regras do app do motorista: check-in de carregamento e o passo em que a viagem está."""
from datetime import datetime
from enum import StrEnum

from app.estados import Estado


class Acao(StrEnum):
    INICIO_CARREGAMENTO = "INICIO_CARREGAMENTO"
    FIM_CARREGAMENTO = "FIM_CARREGAMENTO"


class Passo(StrEnum):
    """O que o motorista tem a fazer agora, do ponto de vista do app."""

    INDO_PARA_FAZENDA = "INDO_PARA_FAZENDA"
    INICIAR_CARREGAMENTO = "INICIAR_CARREGAMENTO"
    FINALIZAR_CARREGAMENTO = "FINALIZAR_CARREGAMENTO"
    AGUARDANDO_SAIDA = "AGUARDANDO_SAIDA"
    INDO_PARA_FABRICA = "INDO_PARA_FABRICA"
    NA_FABRICA = "NA_FABRICA"


def erro_checkin(estado: str | None, assumido: bool, feitas: set[Acao], acao: Acao) -> str | None:
    """None se o check-in pode ser feito; senão, o motivo (vira o 409 da API)."""
    if not assumido:
        return "Assuma o caminhão antes do check-in"
    if estado != Estado.CARREGANDO:
        return "O caminhão não está na fazenda"
    if acao == Acao.INICIO_CARREGAMENTO:
        return "O carregamento já foi iniciado" if acao in feitas else None
    if Acao.INICIO_CARREGAMENTO not in feitas:
        return "Inicie o carregamento antes de finalizar"
    return "O carregamento já foi finalizado" if acao in feitas else None


def passo_atual(estado: str | None, feitas: set[Acao]) -> Passo:
    if estado == Estado.CARREGANDO:
        if Acao.FIM_CARREGAMENTO in feitas:
            return Passo.AGUARDANDO_SAIDA
        if Acao.INICIO_CARREGAMENTO in feitas:
            return Passo.FINALIZAR_CARREGAMENTO
        return Passo.INICIAR_CARREGAMENTO
    if estado == Estado.EM_TRANSITO_CARREGADO:
        return Passo.INDO_PARA_FABRICA
    if estado in (Estado.FILA_PATIO, Estado.PESAGEM, Estado.DESCARGA):
        return Passo.NA_FABRICA
    return Passo.INDO_PARA_FAZENDA


def assumido(assumido_ate: datetime | None, agora: datetime) -> bool:
    """O caminhão está com o app até assumido_ate (relógio simulado)."""
    return assumido_ate is not None and assumido_ate > agora
