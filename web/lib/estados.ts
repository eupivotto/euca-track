import type { Estado } from "./tipos";

// Rótulos pelo que quem acompanha a frota entende, não pelo nome do enum.
export const ROTULO_ESTADO: Record<Estado, string> = {
  CARREGANDO: "Carregando",
  EM_TRANSITO_CARREGADO: "Carregado",
  FILA_PATIO: "Fila do pátio",
  PESAGEM: "Pesagem",
  DESCARGA: "Descarga",
  EM_TRANSITO_VAZIO: "Vazio",
};

// Cor e forma de cada estado: o vazio usa contorno para não depender só de cor.
// Hex direto porque o MapLibre não lê variáveis CSS.
const PRIMARIA = "#0f5c73";
const PATIO = "#5a7d8c";

export const MARCADOR_ESTADO: Record<Estado, { cor: string; contorno: boolean }> = {
  CARREGANDO: { cor: "#9ca8b1", contorno: false },
  EM_TRANSITO_CARREGADO: { cor: PRIMARIA, contorno: false },
  FILA_PATIO: { cor: PATIO, contorno: false },
  PESAGEM: { cor: PATIO, contorno: false },
  DESCARGA: { cor: PATIO, contorno: false },
  EM_TRANSITO_VAZIO: { cor: PRIMARIA, contorno: true },
};
