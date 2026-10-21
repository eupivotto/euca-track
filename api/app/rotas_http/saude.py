from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_sessao

router = APIRouter()


@router.get("/saude")
def saude(sessao: Session = Depends(get_sessao)):
    try:
        sessao.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"api": "ok", "banco": "erro"})
    return {"api": "ok", "banco": "ok"}
