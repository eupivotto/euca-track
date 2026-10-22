"""Ocorrências registradas pelo app do motorista, com foto opcional."""
import uuid
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_sessao
from app.modelos import Caminhao, Ocorrencia
from app.operacao import agora_simulado
from app.tempo_real import difusor

router = APIRouter()


class TipoOcorrencia(StrEnum):
    MECANICA = "MECANICA"
    PNEU = "PNEU"
    ACIDENTE = "ACIDENTE"
    ESTRADA = "ESTRADA"
    OUTRO = "OUTRO"


EXTENSOES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
TIPO_POR_EXTENSAO = {ext: tipo for tipo, ext in EXTENSOES.items()}


def ocorrencia_saida(o: Ocorrencia) -> dict:
    return {
        "id": o.id,
        "caminhao_id": o.caminhao_id,
        "placa": o.caminhao.placa,
        "viagem_id": o.viagem_id,
        "tipo": o.tipo,
        "descricao": o.descricao,
        "foto_url": f"/ocorrencias/{o.id}/foto" if o.foto_url else None,
        "momento": o.momento.isoformat(),
    }


def _ler_foto(foto: UploadFile, settings: Settings) -> tuple[bytes, str]:
    """Conteúdo e extensão da foto, validando tipo e tamanho antes de gravar."""
    extensao = EXTENSOES.get(foto.content_type or "")
    if extensao is None:
        raise HTTPException(status_code=415, detail="A foto precisa ser JPEG, PNG ou WebP")
    limite = int(settings.foto_max_mb * 1024 * 1024)
    conteudo = foto.file.read(limite + 1)
    if len(conteudo) > limite:
        raise HTTPException(status_code=413, detail=f"A foto passa de {settings.foto_max_mb:g} MB")
    return conteudo, extensao


def _registrar(
    sessao: Session,
    settings: Settings,
    caminhao_id: int,
    tipo: TipoOcorrencia,
    descricao: str,
    id_local: str,
    foto: UploadFile | None,
) -> tuple[int, dict]:
    caminhao = sessao.get(Caminhao, caminhao_id)
    if caminhao is None:
        raise HTTPException(status_code=404, detail="Caminhão não encontrado")
    existente = sessao.scalar(select(Ocorrencia).where(Ocorrencia.id_local == id_local))
    if existente is not None:
        return 200, ocorrencia_saida(existente)
    nome_foto = None
    if foto is not None:
        conteudo, extensao = _ler_foto(foto, settings)
        pasta = Path(settings.pasta_fotos)
        pasta.mkdir(parents=True, exist_ok=True)
        nome_foto = f"{uuid.uuid4()}.{extensao}"
        (pasta / nome_foto).write_bytes(conteudo)
    ocorrencia = Ocorrencia(
        viagem_id=caminhao.viagem_atual_id,
        motorista_id=caminhao.motorista_id,
        caminhao_id=caminhao.id,
        tipo=tipo,
        descricao=descricao,
        foto_url=nome_foto,
        momento=agora_simulado(sessao, ZoneInfo(settings.fuso)),
        id_local=id_local,
    )
    sessao.add(ocorrencia)
    sessao.commit()
    return 201, ocorrencia_saida(ocorrencia)


@router.post("/ocorrencias")
async def registrar_ocorrencia(
    caminhao_id: int = Form(),
    tipo: TipoOcorrencia = Form(),
    descricao: str = Form(min_length=1, max_length=500),
    id_local: str = Form(min_length=1, max_length=36),
    foto: UploadFile | None = File(default=None),
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    status, saida = await run_in_threadpool(
        _registrar, sessao, settings, caminhao_id, tipo, descricao, id_local, foto
    )
    if status == 201:
        await difusor.difundir({"tipo": "ocorrencia", "ocorrencia": saida})
    return JSONResponse(saida, status_code=status)


@router.get("/ocorrencias")
def listar_ocorrencias(
    caminhao_id: int | None = None,
    viagem_id: int | None = None,
    limite: int = Query(50, ge=1, le=500),
    sessao: Session = Depends(get_sessao),
):
    consulta = select(Ocorrencia).order_by(Ocorrencia.momento.desc(), Ocorrencia.id.desc()).limit(limite)
    if caminhao_id is not None:
        consulta = consulta.where(Ocorrencia.caminhao_id == caminhao_id)
    if viagem_id is not None:
        consulta = consulta.where(Ocorrencia.viagem_id == viagem_id)
    return [ocorrencia_saida(o) for o in sessao.scalars(consulta)]


@router.get("/ocorrencias/{ocorrencia_id}/foto")
def foto_da_ocorrencia(
    ocorrencia_id: int,
    sessao: Session = Depends(get_sessao),
    settings: Settings = Depends(get_settings),
):
    ocorrencia = sessao.get(Ocorrencia, ocorrencia_id)
    caminho = Path(settings.pasta_fotos) / ocorrencia.foto_url if ocorrencia and ocorrencia.foto_url else None
    if caminho is None or not caminho.is_file():
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    return FileResponse(caminho, media_type=TIPO_POR_EXTENSAO[caminho.suffix.lstrip(".")])
