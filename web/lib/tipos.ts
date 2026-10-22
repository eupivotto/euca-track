// Espelha os formatos JSON da API (api/app/rotas_http).

export type Estado =
  | "CARREGANDO"
  | "EM_TRANSITO_CARREGADO"
  | "FILA_PATIO"
  | "PESAGEM"
  | "DESCARGA"
  | "EM_TRANSITO_VAZIO";

export type TipoAlerta = "ATRASO" | "PARADA" | "DESVIO_ROTA" | "VELOCIDADE";

export type Posicao = {
  lon: number;
  lat: number;
  velocidade_kmh: number;
  momento: string;
};

export type Caminhao = {
  id: number;
  placa: string;
  tipo: "rodotrem" | "tritrem";
  capacidade_t: number;
  motorista: string;
  estado_atual: Estado | null;
  viagem_atual_id: number | null;
  fazenda_id: number | null;
  // Fazenda de origem da viagem atual.
  fazenda: string | null;
  carga_t: number;
  posicao: Posicao | null;
  eta: string | null;
  alertas_abertos: TipoAlerta[];
  // Caminhão com o app do motorista.
  assumido: boolean;
};

export type Alerta = {
  id: number;
  tipo: TipoAlerta;
  caminhao_id: number | null;
  placa: string | null;
  fazenda_id: number | null;
  fazenda: string | null;
  mensagem: string;
  aberto_em: string;
  fechado_em: string | null;
  status: "ABERTO" | "FECHADO";
};

export type Indicadores = {
  inicio: string;
  fim: string;
  agora: string;
  dias: number;
  toneladas: number;
  viagens: number;
  meta_t: number;
  ciclo_medio_min: number | null;
  fila_media_min: number | null;
  uso_frota: number;
  frota_por_estado: Record<Estado, number>;
  serie: { inicio: string; toneladas: number }[];
};

export type Patio = {
  agora: string;
  vagas_total: number;
  vagas_ocupadas: number;
  fila: {
    caminhao_id: number;
    placa: string;
    posicao: number;
    chegou_em: string;
    esperando_min: number;
  }[];
  espera_media_min: number | null;
  chegadas: { caminhao_id: number; placa: string; fazenda: string | null; eta: string }[];
};

export type ViagemResumo = {
  id: number;
  caminhao_id: number;
  placa: string;
  fazenda: string;
  toneladas: number;
  inicio: string;
  fim: string | null;
  status: "EM_ANDAMENTO" | "CONCLUIDA" | "INTERROMPIDA";
};

export type PontoViagem = { lon: number; lat: number; velocidade_kmh: number; momento: string };

export type ViagemDetalhe = ViagemResumo & {
  rota: { type: "LineString"; coordinates: [number, number][] } | null;
  pontos: PontoViagem[];
  eventos: { estado: Estado; momento: string }[];
};

export type Passo =
  | "INDO_PARA_FAZENDA"
  | "INICIAR_CARREGAMENTO"
  | "FINALIZAR_CARREGAMENTO"
  | "AGUARDANDO_SAIDA"
  | "INDO_PARA_FABRICA"
  | "NA_FABRICA";

export type AcaoCheckin = "INICIO_CARREGAMENTO" | "FIM_CARREGAMENTO";

export type PainelMotorista = {
  caminhao: Caminhao;
  assumido: boolean;
  assumido_ate: string | null;
  passo: Passo;
  destino: { fazenda_id: number; nome: string; distancia_km: number | null } | null;
  viagem_id: number | null;
  checkins: { acao: AcaoCheckin; momento: string }[];
  agora: string;
};

export type TipoOcorrencia = "MECANICA" | "PNEU" | "ACIDENTE" | "ESTRADA" | "OUTRO";

export type Ocorrencia = {
  id: number;
  caminhao_id: number;
  placa: string;
  viagem_id: number | null;
  tipo: TipoOcorrencia;
  descricao: string;
  // Relativa à API: passar por urlApi.
  foto_url: string | null;
  momento: string;
};

export type MensagemFrota =
  | { tipo: "caminhao"; caminhao: Caminhao }
  | { tipo: "alerta"; alerta: Alerta }
  | { tipo: "ocorrencia"; ocorrencia: Ocorrencia };

export type Conexao = "conectando" | "conectado" | "reconectando";

// GeoJSON mínimo devolvido por /fazendas e /rotas.
export type ColecaoGeo = {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    geometry: { type: string; coordinates: unknown };
    properties: Record<string, unknown>;
  }[];
};
