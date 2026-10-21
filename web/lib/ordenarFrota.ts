import type { Caminhao, Estado } from "./tipos";

// Sem alerta e sem ETA: quem está trazendo madeira primeiro.
const PRIORIDADE: Record<Estado, number> = {
  EM_TRANSITO_CARREGADO: 0,
  FILA_PATIO: 1,
  PESAGEM: 2,
  DESCARGA: 3,
  CARREGANDO: 4,
  EM_TRANSITO_VAZIO: 5,
};

/** Com alerta aberto → em trânsito por ETA → resto; a placa desempata. */
export function ordenarFrota(caminhoes: Caminhao[]): Caminhao[] {
  const grupo = (c: Caminhao) => (c.alertas_abertos.length > 0 ? 0 : c.eta ? 1 : 2);
  const prioridade = (c: Caminhao) => (c.estado_atual ? PRIORIDADE[c.estado_atual] : 6);
  const eta = (c: Caminhao) => (c.eta ? Date.parse(c.eta) : 0);
  return [...caminhoes].sort(
    (a, b) =>
      grupo(a) - grupo(b) ||
      (grupo(a) === 1 ? eta(a) - eta(b) : prioridade(a) - prioridade(b)) ||
      a.placa.localeCompare(b.placa),
  );
}
