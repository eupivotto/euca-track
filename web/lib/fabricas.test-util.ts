import type { Caminhao, Estado } from "./tipos";

// Monta um caminhão para testes.
export function caminhao(
  placa: string,
  estado: Estado | null,
  carga_t = 0,
  extra: Partial<Caminhao> = {},
): Caminhao {
  return {
    id: Number(placa.replace(/\D/g, "")) || 1,
    placa,
    tipo: "rodotrem",
    capacidade_t: 55,
    motorista: "Paulo Lima",
    estado_atual: estado,
    viagem_atual_id: null,
    fazenda_id: null,
    carga_t,
    posicao: null,
    eta: null,
    fazenda: null,
    alertas_abertos: [],
    ...extra,
  };
}
