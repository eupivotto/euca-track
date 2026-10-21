import type { Caminhao, Estado } from "./tipos";

// Fase 1: quem está trazendo madeira primeiro. A Fase 2 põe os com alerta na frente.
const PRIORIDADE: Record<Estado, number> = {
  EM_TRANSITO_CARREGADO: 0,
  FILA_PATIO: 1,
  PESAGEM: 2,
  DESCARGA: 3,
  CARREGANDO: 4,
  EM_TRANSITO_VAZIO: 5,
};

export function ordenarFrota(caminhoes: Caminhao[]): Caminhao[] {
  const prioridade = (c: Caminhao) => (c.estado_atual ? PRIORIDADE[c.estado_atual] : 6);
  return [...caminhoes].sort(
    (a, b) => prioridade(a) - prioridade(b) || a.placa.localeCompare(b.placa),
  );
}
