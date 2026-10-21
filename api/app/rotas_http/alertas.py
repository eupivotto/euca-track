from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alertas import TipoAlerta
from app.db import get_sessao
from app.modelos import Alerta
from app.vigilancia import alerta_saida

router = APIRouter()


@router.get("/alertas")
def alertas(
    status: Literal["ABERTO", "FECHADO"] | None = None,
    tipo: TipoAlerta | None = None,
    limite: int = Query(200, ge=1, le=1000),
    sessao: Session = Depends(get_sessao),
):
    consulta = select(Alerta).order_by(Alerta.aberto_em.desc(), Alerta.id.desc()).limit(limite)
    if status:
        consulta = consulta.where(Alerta.status == status)
    if tipo:
        consulta = consulta.where(Alerta.tipo == tipo)
    return [alerta_saida(a) for a in sessao.scalars(consulta)]
