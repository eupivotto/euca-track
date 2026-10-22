"""App do motorista: painel da viagem, posse do caminhão e check-in de carregamento."""
from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.modelos import Caminhao, Checkin, Rota
from app.motorista import Acao, assumido, erro_checkin, passo_atual
from app.operacao import agora_simulado
from app.rotas_http.frota import montar_caminhao_saida
from app.tempo_real import difusor

router = APIRouter(prefix="/motorista")


class CorpoCaminhao(BaseModel):
    caminhao_id: int


class CorpoCheckin(BaseModel):
    caminhao_id: int
    acao: Acao
    # Gerado no celular; repetir o mesmo envio devolve o check-in já gravado.
    id_local: str = Field(min_length=1, max_length=36)


def _caminhao(sessao: Session, caminhao_id: int) -> Caminhao:
    caminhao = sessao.get(Caminhao, caminhao_id)
    if caminhao is None:
        raise HTTPException(status_code=404, detail="Caminhão não encontrado")
    return caminhao


def _checkins(sessao: Session, caminhao: Caminhao) -> list[Checkin]:
    if caminhao.viagem_atual_id is None:
        return []
    return list(
        sessao.scalars(
            select(Checkin)
            .where(Checkin.viagem_id == caminhao.viagem_atual_id)
            .order_by(Checkin.momento, Checkin.id)
        )
    )


def checkin_saida(c: Checkin) -> dict:
    return {"id": c.id, "acao": c.acao, "momento": c.momento.isoformat(), "viagem_id": c.viagem_id}


def montar_painel(sessao: Session, caminhao: Caminhao, settings: Settings) -> dict:
    agora = agora_simulado(sessao, ZoneInfo(settings.fuso))
    checkins = _checkins(sessao, caminhao)
    destino = None
    if caminhao.fazenda_destino is not None:
        distancia = sessao.scalar(
            select(Rota.distancia_km).where(Rota.fazenda_id == caminhao.fazenda_destino_id)
        )
        destino = {
            "fazenda_id": caminhao.fazenda_destino_id,
            "nome": caminhao.fazenda_destino.nome,
            "distancia_km": distancia,
        }
    return {
        "caminhao": montar_caminhao_saida(sessao, caminhao, agora),
        "assumido": assumido(caminhao.assumido_ate, agora),
        "assumido_ate": caminhao.assumido_ate.isoformat() if caminhao.assumido_ate else None,
        "passo": passo_atual(caminhao.estado_atual, {Acao(c.acao) for c in checkins}),
        "destino": destino,
        "viagem_id": caminhao.viagem_atual_id,
        "checkins": [{"acao": c.acao, "momento": c.momento.isoformat()} for c in checkins],
        "agora": agora.isoformat(),
    }


def _mensagem_caminhao(painel: dict) -> dict:
    return {"tipo": "caminhao", "caminhao": painel["caminhao"]}


@router.get("/caminhoes/{caminhao_id}")
def painel(
    caminhao_id: int,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    return montar_painel(sessao, _caminhao(sessao, caminhao_id), settings)


def _assumir(sessao: Session, caminhao_id: int, settings: Settings) -> dict:
    caminhao = _caminhao(sessao, caminhao_id)
    agora = agora_simulado(sessao, ZoneInfo(settings.fuso))
    caminhao.assumido_ate = agora + timedelta(minutes=settings.motorista_assumir_min)
    sessao.commit()
    return montar_painel(sessao, caminhao, settings)


def _soltar(sessao: Session, caminhao_id: int, settings: Settings) -> dict:
    caminhao = _caminhao(sessao, caminhao_id)
    caminhao.assumido_ate = None
    sessao.commit()
    return montar_painel(sessao, caminhao, settings)


@router.post("/assumir")
async def assumir(
    corpo: CorpoCaminhao,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    """Assume o caminhão ou renova a posse (o app chama a cada minuto)."""
    resultado = await run_in_threadpool(_assumir, sessao, corpo.caminhao_id, settings)
    await difusor.difundir(_mensagem_caminhao(resultado))
    return resultado


@router.post("/soltar")
async def soltar(
    corpo: CorpoCaminhao,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    resultado = await run_in_threadpool(_soltar, sessao, corpo.caminhao_id, settings)
    await difusor.difundir(_mensagem_caminhao(resultado))
    return resultado


def _checkin(sessao: Session, corpo: CorpoCheckin, settings: Settings) -> tuple[int, dict, dict]:
    """Devolve (status HTTP, check-in, painel)."""
    caminhao = _caminhao(sessao, corpo.caminhao_id)
    existente = sessao.scalar(select(Checkin).where(Checkin.id_local == corpo.id_local))
    if existente is not None:
        return 200, checkin_saida(existente), montar_painel(sessao, caminhao, settings)
    agora = agora_simulado(sessao, ZoneInfo(settings.fuso))
    feitas = {Acao(c.acao) for c in _checkins(sessao, caminhao)}
    erro = erro_checkin(
        caminhao.estado_atual, assumido(caminhao.assumido_ate, agora), feitas, corpo.acao
    )
    if erro:
        raise HTTPException(status_code=409, detail=erro)
    novo = Checkin(
        viagem_id=caminhao.viagem_atual_id,
        caminhao_id=caminhao.id,
        acao=corpo.acao,
        momento=agora,
        id_local=corpo.id_local,
    )
    sessao.add(novo)
    sessao.commit()
    return 201, checkin_saida(novo), montar_painel(sessao, caminhao, settings)


@router.post("/checkin")
async def fazer_checkin(
    corpo: CorpoCheckin,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    status, saida, resultado = await run_in_threadpool(_checkin, sessao, corpo, settings)
    if status == 201:
        await difusor.difundir(_mensagem_caminhao(resultado))
    return JSONResponse(saida, status_code=status)
