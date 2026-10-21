// Espelha os formatos JSON da API (api/app/rotas_http).

export type Estado =
  | "CARREGANDO"
  | "EM_TRANSITO_CARREGADO"
  | "FILA_PATIO"
  | "PESAGEM"
  | "DESCARGA"
  | "EM_TRANSITO_VAZIO";

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
  carga_t: number;
  posicao: Posicao | null;
};

export type Indicadores = {
  inicio: string;
  fim: string;
  agora: string;
  toneladas: number;
  viagens: number;
  meta_t: number;
};

export type MensagemFrota = { tipo: "caminhao"; caminhao: Caminhao };

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
