const DIA_MS = 24 * 60 * 60 * 1000;

export function fracao(valor: number, total: number): number {
  if (total <= 0) return 0;
  return Math.min(1, Math.max(0, valor / total));
}

/** Quanto já deveria ter chegado até agora, supondo ritmo constante no dia. */
export function esperadoAgora(meta_t: number, inicio: string, agora: string): number {
  const decorrido = Date.parse(agora) - Date.parse(inicio);
  return meta_t * fracao(decorrido, DIA_MS);
}
