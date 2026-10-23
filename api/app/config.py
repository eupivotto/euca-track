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

    # Região do projeto (SPEC 3.1 e 8): recorte das áreas de eucalipto e dos focos
    regiao_lat_min: float = -21.6
    regiao_lat_max: float = -19.8
    regiao_lon_min: float = -52.9
    regiao_lon_max: float = -51.4

    # Áreas reais de eucalipto (SPEC 3.1): MapBiomas coleção 10, classe 9 = Silvicultura
    mapbiomas_url: str = (
        "https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/"
        "collection_10/lulc/coverage/brazil_coverage_2024.tif"
    )
    mapbiomas_classe: int = 9
    areas_min_ha: float = 500
    areas_raio_km: float = 150
    areas_maximo: int = 8
    areas_fecho_m: float = 60  # une talhões separados por aceiros e estradas internas
    areas_simplificar_m: float = 30

    # Risco de incêndio (SPEC seção 7): limite superior de cada classe da FMA
    fma_limite_nulo: float = 1.0
    fma_limite_pequeno: float = 3.0
    fma_limite_medio: float = 8.0
    fma_limite_alto: float = 20.0
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_historico_url: str = "https://archive-api.open-meteo.com/v1/archive"
    clima_backfill_dias: int = 60

    # Alertas de foco (SPEC seção 8): janela pelo relógio real, vento das 13h
    foco_janela_h: float = 24
    foco_fazenda_km: float = 5
    foco_rota_km: float = 3
    foco_vento_angulo_max: float = 45
    inpe_focos_url: str = (
        "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/"
        "focos_diario_br_{data}.csv"
    )

    # Rotas (SPEC seção 5)
    osrm_url: str = "https://router.project-osrm.org"
    fator_linha_reta: float = 1.3
    user_agent: str = "rota-da-madeira/0.1 (+https://github.com/eupivotto/euca-track)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
