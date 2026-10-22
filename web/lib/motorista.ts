import type { AcaoCheckin, PainelMotorista, Passo, TipoOcorrencia } from "./tipos";

export const ROTULO_PASSO: Record<Passo, string> = {
  INDO_PARA_FAZENDA: "Indo para a fazenda",
  INICIAR_CARREGAMENTO: "Na fazenda",
  FINALIZAR_CARREGAMENTO: "Carregando",
  AGUARDANDO_SAIDA: "Carregamento finalizado, saindo",
  INDO_PARA_FABRICA: "Indo para a fábrica",
  NA_FABRICA: "Na fábrica",
};

export const TEXTO_BOTAO: Record<AcaoCheckin, string> = {
  INICIO_CARREGAMENTO: "Iniciar carregamento",
  FIM_CARREGAMENTO: "Finalizar carregamento",
};

export const ROTULO_OCORRENCIA: Record<TipoOcorrencia, string> = {
  MECANICA: "Problema mecânico",
  PNEU: "Pneu",
  ACIDENTE: "Acidente",
  ESTRADA: "Problema na estrada",
  OUTRO: "Outro",
};

/** O check-in que o passo pede, ou null quando não há nada a fazer no app. */
export function acaoDoPasso(passo: Passo): AcaoCheckin | null {
  if (passo === "INICIAR_CARREGAMENTO") return "INICIO_CARREGAMENTO";
  if (passo === "FINALIZAR_CARREGAMENTO") return "FIM_CARREGAMENTO";
  return null;
}

// Último painel de cada caminhão no celular: na fazenda sem sinal, o app reabre com o botão de check-in.
const chavePainel = (caminhaoId: number) => `rota-motorista:painel:${caminhaoId}`;

export function guardarPainel(caminhaoId: number, painel: PainelMotorista): void {
  try {
    localStorage.setItem(chavePainel(caminhaoId), JSON.stringify(painel));
  } catch {
    // Sem armazenamento: o app só não abre o painel sem rede.
  }
}

export function lerPainelGuardado(caminhaoId: number): PainelMotorista | undefined {
  try {
    const texto = localStorage.getItem(chavePainel(caminhaoId));
    return texto ? (JSON.parse(texto) as PainelMotorista) : undefined;
  } catch {
    return undefined;
  }
}
