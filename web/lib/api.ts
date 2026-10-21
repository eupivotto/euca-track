import type { Caminhao, ColecaoGeo, Indicadores } from "./tipos";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

async function buscar<T>(caminho: string): Promise<T> {
  const resposta = await fetch(`${BASE}${caminho}`);
  if (!resposta.ok) throw new Error(`A API respondeu ${resposta.status} em ${caminho}`);
  return resposta.json() as Promise<T>;
}

export const buscarCaminhoes = () => buscar<Caminhao[]>("/caminhoes");
export const buscarFazendas = () => buscar<ColecaoGeo>("/fazendas");
export const buscarRotas = () => buscar<ColecaoGeo>("/rotas");
export const buscarIndicadores = () => buscar<Indicadores>("/indicadores");

export function urlWebSocket(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocolo}://${window.location.host}/ws/frota`;
}
