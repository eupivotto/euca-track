from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter()

# Só o que o simulador precisa; nada de segredo ou conexão.
CAMPOS_SIMULACAO = (
    "seed",
    "capacidade_rodotrem_t",
    "capacidade_tritrem_t",
    "velocidade_carregado_kmh",
    "velocidade_vazio_kmh",
    "variacao_velocidade",
    "carregamento_min_min",
    "carregamento_max_min",
    "pesagem_min",
    "descarga_min_min",
    "descarga_max_min",
    "vagas_descarga",
    "intervalo_telemetria_s",
    "fator_tempo",
    "prob_evento_viagem",
)


@router.get("/simulacao/parametros")
def parametros(settings: Settings = Depends(get_settings)):
    return {campo: getattr(settings, campo) for campo in CAMPOS_SIMULACAO}
