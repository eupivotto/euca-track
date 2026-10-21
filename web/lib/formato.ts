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

/** "38 min" abaixo de uma hora, "4h12" a partir dela, "—" sem valor. */
export function duracao(minutos: number | null): string {
  if (minutos === null) return "—";
  const total = Math.round(minutos);
  if (total < 60) return `${total} min`;
  return `${Math.floor(total / 60)}h${String(total % 60).padStart(2, "0")}`;
}

function partes(iso: string) {
  const lista = new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  return (tipo: string) => lista.find((p) => p.type === tipo)?.value ?? "";
}

/** "14h30", no horário de Campo Grande. */
export function horaCurta(iso: string): string {
  const valor = partes(iso);
  return `${valor("hour")}h${valor("minute")}`;
}

/** "14h", para rótulos de hora cheia. */
export function horaCheia(iso: string): string {
  return `${partes(iso)("hour")}h`;
}

/** "19/10", no horário de Campo Grande. */
export function diaCurto(iso: string): string {
  const valor = partes(iso);
  return `${valor("day")}/${valor("month")}`;
}
