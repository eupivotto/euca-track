import type {
  Alerta,
  Caminhao,
  ColecaoGeo,
  Indicadores,
  Patio,
  ViagemDetalhe,
  ViagemResumo,
} from "./tipos";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

async function buscar<T>(caminho: string): Promise<T> {
  const resposta = await fetch(`${BASE}${caminho}`);
  if (!resposta.ok) throw new Error(`A API respondeu ${resposta.status} em ${caminho}`);
  return resposta.json() as Promise<T>;
}

export const buscarCaminhoes = () => buscar<Caminhao[]>("/caminhoes");
export const buscarFazendas = () => buscar<ColecaoGeo>("/fazendas");
export const buscarRotas = () => buscar<ColecaoGeo>("/rotas");
export const buscarIndicadores = (dias = 1) => buscar<Indicadores>(`/indicadores?dias=${dias}`);
export const buscarAlertas = (status: Alerta["status"]) => buscar<Alerta[]>(`/alertas?status=${status}`);
export const buscarPatio = () => buscar<Patio>("/patio/fila");
export const buscarViagens = (caminhaoId?: number) =>
  buscar<ViagemResumo[]>(caminhaoId ? `/viagens?caminhao_id=${caminhaoId}` : "/viagens");

export async function buscarViagem(id: number): Promise<ViagemDetalhe | null> {
  const resposta = await fetch(`${BASE}/viagens/${id}`);
  if (resposta.status === 404) return null;
  if (!resposta.ok) throw new Error(`A API respondeu ${resposta.status} em /viagens/${id}`);
  return resposta.json() as Promise<ViagemDetalhe>;
}

export function urlWebSocket(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocolo}://${window.location.host}/ws/frota`;
}
