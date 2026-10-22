"""Configuração única do projeto: parâmetros de simulação e limites.

Valores padrão conforme docs/SPEC.md (seção 4); cada campo pode ser
sobrescrito por variável de ambiente com o mesmo nome em maiúsculas.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rota:rota@db:5432/rota"
    token_telemetria: str = "dev-token"
    fuso: str = "America/Campo_Grande"

    # Simulação (SPEC seção 4)
    seed: int = 42
    capacidade_rodotrem_t: float = 55
    capacidade_tritrem_t: float = 45
    velocidade_carregado_kmh: float = 60
    velocidade_vazio_kmh: float = 70
    variacao_velocidade: float = 0.15
    carregamento_min_min: float = 40
    carregamento_max_min: float = 60
    pesagem_min: float = 5
    descarga_min_min: float = 25
    descarga_max_min: float = 35
    vagas_descarga: int = 3
    intervalo_telemetria_s: float = 30
    fator_tempo: float = 10
    meta_diaria_t: float = 4000
    prob_evento_viagem: float = 0.05
    parada_min_min: float = 20  # duração da parada não prevista (padrão do plano da Fase 2)
    parada_max_min: float = 40

    # Alertas de logística e ETA (SPEC seção 6)
    alerta_atraso_tolerancia: float = 0.20
    # Carência no início do trecho: com poucas leituras (saída ainda devagar) o ETA estoura.
    alerta_atraso_carencia_min: float = 10
    alerta_parada_velocidade_kmh: float = 5
    alerta_parada_min: float = 15
    alerta_raio_local_m: float = 500
    alerta_desvio_m: float = 500
    alerta_desvio_leituras: int = 2
    alerta_velocidade_max_kmh: float = 80
    eta_leituras: int = 10
    eta_velocidade_min_kmh: float = 20

    # App do motorista: posse do caminhão (min simulados, renovada pelo app) e fotos
    motorista_assumir_min: float = 60
    pasta_fotos: str = "/dados/fotos"
    foto_max_mb: float = 10

    # Rotas (SPEC seção 5)
    osrm_url: str = "https://router.project-osrm.org"
    fator_linha_reta: float = 1.3
    user_agent: str = "rota-da-madeira/0.1 (+https://github.com/eupivotto/euca-track)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
