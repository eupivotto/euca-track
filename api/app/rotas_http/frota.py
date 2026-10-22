from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.estados import ESTADOS_CARREGADO
from app.modelos import Alerta, Caminhao, Posicao
from app.motorista import assumido
from app.operacao import agora_simulado
from app.telemetria import CaminhaoDesconhecido, LeituraEntrada, registrar_leituras
from app.tempo_real import difusor
from app.vigilancia import alerta_saida

router = APIRouter()


def montar_caminhao_saida(
    sessao: Session, caminhao: Caminhao, agora: datetime | None = None
) -> dict:
    """Estado atual de um caminhão, no formato de GET /caminhoes e do WebSocket."""
    if agora is None:
        agora = agora_simulado(sessao, ZoneInfo(get_settings().fuso))
    ultima = sessao.scalars(
        select(Posicao)
        .where(Posicao.caminhao_id == caminhao.id)
        .order_by(Posicao.momento.desc(), Posicao.id.desc())
        .limit(1)
    ).first()
    posicao = None
    if ultima is not None:
        ponto = to_shape(ultima.geom)
        posicao = {
            "lon": ponto.x,
            "lat": ponto.y,
            "velocidade_kmh": ultima.velocidade_kmh,
            "momento": ultima.momento.isoformat(),
        }
    carregado = caminhao.estado_atual in ESTADOS_CARREGADO
    return {
        "id": caminhao.id,
        "placa": caminhao.placa,
        "tipo": caminhao.tipo,
        "capacidade_t": caminhao.capacidade_t,
        "motorista": caminhao.motorista.nome,
        "estado_atual": caminhao.estado_atual,
        "viagem_atual_id": caminhao.viagem_atual_id,
        "fazenda_id": caminhao.viagem_atual.fazenda_id if caminhao.viagem_atual else None,
        # Fazenda de origem da viagem atual (no vazio, a carga dela já foi entregue).
        "fazenda": caminhao.viagem_atual.fazenda.nome if caminhao.viagem_atual else None,
        "carga_t": caminhao.capacidade_t if carregado else 0,
        "posicao": posicao,
        "eta": caminhao.eta_atual.isoformat() if caminhao.eta_atual else None,
        "assumido": assumido(caminhao.assumido_ate, agora),
        "alertas_abertos": sorted(
            sessao.scalars(
                select(Alerta.tipo).where(
                    Alerta.caminhao_id == caminhao.id, Alerta.status == "ABERTO"
                )
            )
        ),
    }


@router.get("/caminhoes")
def caminhoes(sessao: Session = Depends(get_sessao), settings: Settings = Depends(get_settings)):
    agora = agora_simulado(sessao, ZoneInfo(settings.fuso))
    return [
        montar_caminhao_saida(sessao, c, agora)
        for c in sessao.scalars(select(Caminhao).order_by(Caminhao.id))
    ]


def _aplicar_lote(sessao: Session, leituras: list[LeituraEntrada]) -> list[dict]:
    """Grava o lote e devolve as mensagens do WebSocket: caminhões, depois alertas."""
    try:
        lote = registrar_leituras(sessao, leituras)
    except CaminhaoDesconhecido as erro:
        # registrar_leituras valida o lote antes de gravar: não há o que desfazer.
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    sessao.commit()
    agora = agora_simulado(sessao, ZoneInfo(get_settings().fuso))
    return [
        {"tipo": "caminhao", "caminhao": montar_caminhao_saida(sessao, sessao.get(Caminhao, i), agora)}
        for i in lote.caminhoes
    ] + [{"tipo": "alerta", "alerta": alerta_saida(sessao.get(Alerta, i))} for i in lote.alertas]


@router.post("/telemetria")
async def telemetria(
    leituras: list[LeituraEntrada],
    x_token: str | None = Header(default=None),
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    if x_token != settings.token_telemetria:
        raise HTTPException(status_code=401, detail="Token de telemetria inválido")
    mensagens = await run_in_threadpool(_aplicar_lote, sessao, leituras)
    for mensagem in mensagens:
        await difusor.difundir(mensagem)
    return {"recebidas": len(leituras)}


@router.websocket("/ws/frota")
async def ws_frota(ws: WebSocket):
    await difusor.conectar(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        difusor.desconectar(ws)
