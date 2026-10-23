import type {
  Alerta,
  Caminhao,
  ColecaoGeo,
  HistoricoRisco,
  Indicadores,
  Ocorrencia,
  PainelMotorista,
  Patio,
  ViagemDetalhe,
  ViagemResumo,
} from "./tipos";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

/** Endereço completo de um caminho da API (ex.: foto_url de uma ocorrência). */
export const urlApi = (caminho: string) => `${BASE}${caminho}`;

async function buscar<T>(caminho: string): Promise<T> {
  const resposta = await fetch(`${BASE}${caminho}`);
  if (!resposta.ok) throw new Error(`A API respondeu ${resposta.status} em ${caminho}`);
  return resposta.json() as Promise<T>;
}

export const buscarCaminhoes = () => buscar<Caminhao[]>("/caminhoes");
export const buscarFazendas = () => buscar<ColecaoGeo>("/fazendas");
export const buscarRotas = () => buscar<ColecaoGeo>("/rotas");
export const buscarFocos = (horas: number) => buscar<ColecaoGeo>(`/focos?horas=${horas}`);
export const buscarHistoricoRisco = (dias = 30) => buscar<HistoricoRisco>(`/risco/historico?dias=${dias}`);
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

export const buscarPainelMotorista = (caminhaoId: number) =>
  buscar<PainelMotorista>(`/motorista/caminhoes/${caminhaoId}`);

async function postar<T>(caminho: string, corpo: unknown): Promise<T> {
  const resposta = await fetch(`${BASE}${caminho}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  if (!resposta.ok) throw new Error(`A API respondeu ${resposta.status} em ${caminho}`);
  return resposta.json() as Promise<T>;
}

export const assumirCaminhao = (caminhaoId: number) =>
  postar<PainelMotorista>("/motorista/assumir", { caminhao_id: caminhaoId });
export const soltarCaminhao = (caminhaoId: number) =>
  postar<PainelMotorista>("/motorista/soltar", { caminhao_id: caminhaoId });

export function buscarOcorrencias({ caminhaoId, viagemId }: { caminhaoId?: number; viagemId?: number }) {
  const filtros = new URLSearchParams();
  if (caminhaoId) filtros.set("caminhao_id", String(caminhaoId));
  if (viagemId) filtros.set("viagem_id", String(viagemId));
  return buscar<Ocorrencia[]>(`/ocorrencias?${filtros}`);
}

export function urlWebSocket(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocolo}://${window.location.host}/ws/frota`;
}
