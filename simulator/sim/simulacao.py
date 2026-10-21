"""Simulação da frota: ciclo de cada caminhão, fila do pátio e relógio simulado."""
import random
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta

from sim.estados import Estado, proximo_estado
from sim.rota import Ponto, comprimento_km, ponto_na_linha

ESTADOS_PATIO = {Estado.FILA_PATIO, Estado.PESAGEM, Estado.DESCARGA}
EM_TRANSITO = {Estado.EM_TRANSITO_CARREGADO, Estado.EM_TRANSITO_VAZIO}


@dataclass
class Parametros:
    """Mesmos nomes de GET /simulacao/parametros da API."""

    seed: int
    capacidade_rodotrem_t: float
    capacidade_tritrem_t: float
    velocidade_carregado_kmh: float
    velocidade_vazio_kmh: float
    variacao_velocidade: float
    carregamento_min_min: float
    carregamento_max_min: float
    pesagem_min: float
    descarga_min_min: float
    descarga_max_min: float
    vagas_descarga: int
    intervalo_telemetria_s: float
    fator_tempo: float
    prob_evento_viagem: float
    parada_min_min: float
    parada_max_min: float

    @classmethod
    def de_json(cls, dados: dict) -> "Parametros":
        return cls(**{f.name: dados[f.name] for f in fields(cls)})


@dataclass
class FazendaSim:
    id: int
    area_ha: float
    coords_rota: list[Ponto]  # sentido fazenda -> fábrica
    comprimento_km: float = field(init=False)

    def __post_init__(self) -> None:
        self.comprimento_km = comprimento_km(self.coords_rota)


@dataclass
class CaminhaoSim:
    id: int
    capacidade_t: float
    estado: Estado
    fazenda_id: int
    km: float = 0
    minutos_restantes: float = 0
    velocidade_kmh: float = 0
    # Sorteado uma vez por trecho (±variação), para a velocidade não oscilar a cada leitura.
    fator_velocidade: float = 1
    # Parada não prevista no trecho carregado: onde (km) e quanto tempo falta.
    parada_km: float | None = None
    parada_restante_min: float = 0


class Simulacao:
    def __init__(
        self,
        parametros: Parametros,
        fazendas: list[FazendaSim],
        caminhoes: list[tuple[int, float]],
        inicio: datetime,
    ) -> None:
        if not fazendas:
            raise ValueError("A simulação precisa de pelo menos uma fazenda com rota")
        self.p = parametros
        self.rng = random.Random(parametros.seed)
        self.fazendas = {f.id: f for f in sorted(fazendas, key=lambda f: f.id)}
        self.agora = inicio
        self.fila: list[int] = []
        ids_fazendas = list(self.fazendas)
        self.caminhoes = [
            CaminhaoSim(
                id=id_,
                capacidade_t=capacidade,
                estado=Estado.CARREGANDO,
                fazenda_id=self.rng.choice(ids_fazendas),
                minutos_restantes=self._duracao_carregamento(),
            )
            for id_, capacidade in sorted(caminhoes)
        ]

    def _duracao_carregamento(self) -> float:
        return self.rng.uniform(self.p.carregamento_min_min, self.p.carregamento_max_min)

    def sortear_fazenda(self) -> int:
        """Destino da viagem vazia, com peso pela área da fazenda."""
        ids = list(self.fazendas)
        return self.rng.choices(ids, weights=[self.fazendas[i].area_ha for i in ids])[0]

    def _velocidade_base(self, estado: Estado) -> float:
        if estado == Estado.EM_TRANSITO_CARREGADO:
            return self.p.velocidade_carregado_kmh
        return self.p.velocidade_vazio_kmh

    def _comecar_trecho(self, c: CaminhaoSim) -> None:
        variacao = self.p.variacao_velocidade
        c.fator_velocidade = self.rng.uniform(1 - variacao, 1 + variacao)
        c.km = 0
        c.parada_km = None
        if c.estado == Estado.EM_TRANSITO_CARREGADO and self.rng.random() < self.p.prob_evento_viagem:
            comprimento = self.fazendas[c.fazenda_id].comprimento_km
            c.parada_km = self.rng.uniform(0.2, 0.8) * comprimento
            c.parada_restante_min = self.rng.uniform(self.p.parada_min_min, self.p.parada_max_min)
        # Saindo agora: a leitura de partida já tem a velocidade do trecho.
        c.velocidade_kmh = self._velocidade_base(c.estado) * c.fator_velocidade

    def _entrar(self, c: CaminhaoSim, estado: Estado) -> None:
        c.estado = estado
        c.velocidade_kmh = 0
        if estado == Estado.CARREGANDO:
            c.minutos_restantes = self._duracao_carregamento()
        elif estado == Estado.EM_TRANSITO_CARREGADO:
            self._comecar_trecho(c)
        elif estado == Estado.FILA_PATIO:
            self.fila.append(c.id)
        elif estado == Estado.PESAGEM:
            c.minutos_restantes = self.p.pesagem_min
        elif estado == Estado.DESCARGA:
            c.minutos_restantes = self.rng.uniform(self.p.descarga_min_min, self.p.descarga_max_min)
        elif estado == Estado.EM_TRANSITO_VAZIO:
            c.fazenda_id = self.sortear_fazenda()
            self._comecar_trecho(c)

    def _avancar(self, c: CaminhaoSim, minutos: float) -> None:
        if c.estado in EM_TRANSITO:
            if c.parada_km is not None and c.km >= c.parada_km:
                c.velocidade_kmh = 0
                c.parada_restante_min -= minutos
                if c.parada_restante_min <= 0:
                    c.parada_km = None
                return
            c.velocidade_kmh = self._velocidade_base(c.estado) * c.fator_velocidade
            c.km += c.velocidade_kmh * minutos / 60
            if c.km >= self.fazendas[c.fazenda_id].comprimento_km:
                self._entrar(c, proximo_estado(c.estado))
        elif c.estado != Estado.FILA_PATIO:
            c.minutos_restantes -= minutos
            if c.minutos_restantes <= 0:
                self._entrar(c, proximo_estado(c.estado))

    def _liberar_fila(self, aguardando: list[int]) -> None:
        """Leva para a pesagem quem já estava na fila antes deste passo, se houver vaga."""
        ocupadas = sum(c.estado in (Estado.PESAGEM, Estado.DESCARGA) for c in self.caminhoes)
        por_id = {c.id: c for c in self.caminhoes}
        for id_ in aguardando:
            if ocupadas >= self.p.vagas_descarga:
                break
            self.fila.remove(id_)
            self._entrar(por_id[id_], Estado.PESAGEM)
            ocupadas += 1

    def _posicao(self, c: CaminhaoSim) -> Ponto:
        rota = self.fazendas[c.fazenda_id].coords_rota
        if c.estado == Estado.CARREGANDO:
            return rota[0]
        if c.estado in ESTADOS_PATIO:
            return rota[-1]
        if c.estado == Estado.EM_TRANSITO_CARREGADO:
            return ponto_na_linha(rota, c.km)
        return ponto_na_linha(rota[::-1], c.km)

    def passo(self, minutos: float) -> list[dict]:
        """Avança o relógio simulado e devolve uma leitura por caminhão."""
        self.agora += timedelta(minutes=minutos)
        # Quem chega ao pátio aparece pelo menos uma leitura na fila.
        aguardando = list(self.fila)
        for c in self.caminhoes:
            self._avancar(c, minutos)
        self._liberar_fila(aguardando)
        leituras = []
        for c in self.caminhoes:
            lon, lat = self._posicao(c)
            leituras.append(
                {
                    "caminhao_id": c.id,
                    "fazenda_id": c.fazenda_id,
                    "estado": c.estado.value,
                    "lon": lon,
                    "lat": lat,
                    "velocidade_kmh": round(c.velocidade_kmh, 1),
                    "momento": self.agora.isoformat(),
                }
            )
        return leituras
