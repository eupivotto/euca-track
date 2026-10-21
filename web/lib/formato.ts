const FUSO = "America/Campo_Grande";
const MENOS = "−";

export function toneladas(valor: number): string {
  return `${Math.round(valor).toLocaleString("pt-BR")} t`;
}

export function toneladasComSinal(valor: number): string {
  const arredondado = Math.round(valor);
  const sinal = arredondado > 0 ? "+" : arredondado < 0 ? MENOS : "";
  return `${sinal}${Math.abs(arredondado).toLocaleString("pt-BR")} t`;
}

/** "14h30", no horário de Campo Grande. */
export function horaCurta(iso: string): string {
  const partes = new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const valor = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? "";
  return `${valor("hour")}h${valor("minute")}`;
}
