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

/** Texto depois de registrar: muda sozinho de "guardada" para "registrada" quando a fila envia. */
export function confirmacaoOcorrencia(idLocal: string, pendentes: string[]): string {
  return pendentes.includes(idLocal)
    ? "Ocorrência guardada; será enviada quando houver rede."
    : "Ocorrência registrada.";
}

/**
 * Check-ins que seguram o botão: os da fila e o último enviado enquanto o painel ainda
 * mostra o passo de quando foi feito (sem isso, o botão antigo volta até o painel recarregar).
 * Recusado pela API, o enviado deixa de segurar.
 */
export function acoesEmEspera(
  naFila: AcaoCheckin[],
  enviada: { id_local: string; acao: AcaoCheckin; passo: Passo } | null,
  passo: Passo,
  recusados: string[],
): AcaoCheckin[] {
  const esperando = enviada && enviada.passo === passo && !recusados.includes(enviada.id_local);
  return esperando ? [...new Set([...naFila, enviada.acao])] : naFila;
}
