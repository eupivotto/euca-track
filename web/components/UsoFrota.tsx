import { MARCADOR_ESTADO } from "@/lib/estados";
import type { Estado, Indicadores } from "@/lib/tipos";

// Mesmas cores do mapa. Ordem escolhida para o carregado não encostar no pátio
// (os dois azuis ficam difíceis de separar lado a lado); o vazio é contorno, como no mapa.
const GRUPOS: { rotulo: string; estados: Estado[]; estilo: React.CSSProperties }[] = [
  { rotulo: "Carregado", estados: ["EM_TRANSITO_CARREGADO"], estilo: { background: MARCADOR_ESTADO.EM_TRANSITO_CARREGADO.cor } },
  { rotulo: "Carregando", estados: ["CARREGANDO"], estilo: { background: MARCADOR_ESTADO.CARREGANDO.cor } },
  { rotulo: "No pátio", estados: ["FILA_PATIO", "PESAGEM", "DESCARGA"], estilo: { background: MARCADOR_ESTADO.FILA_PATIO.cor } },
  {
    rotulo: "Vazio",
    estados: ["EM_TRANSITO_VAZIO"],
    estilo: { boxShadow: `inset 0 0 0 1.5px ${MARCADOR_ESTADO.EM_TRANSITO_VAZIO.cor}` },
  },
];

/** Uso da frota agora: uma barra empilhada por grupo de estado, com legenda e percentuais. */
export function UsoFrota({ frota }: { frota: Indicadores["frota_por_estado"] }) {
  const grupos = GRUPOS.map((g) => ({ ...g, n: g.estados.reduce((s, e) => s + frota[e], 0) }));
  const total = grupos.reduce((s, g) => s + g.n, 0);
  const pct = (n: number) => (total ? Math.round((n / total) * 100) : 0);

  return (
    <figure className="numeros">
      <div className="flex h-7 gap-[2px]">
        {grupos
          .filter((g) => g.n > 0)
          .map((g) => (
            <div
              key={g.rotulo}
              aria-hidden
              title={`${g.rotulo}: ${g.n} caminhões, ${pct(g.n)}%`}
              className="rounded-[4px]"
              style={{ ...g.estilo, flexGrow: g.n }}
            />
          ))}
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12.5px]">
        {grupos.map((g) => (
          <li
            key={g.rotulo}
            aria-label={`${g.rotulo}: ${g.n} caminhões, ${pct(g.n)}%`}
            className="flex items-center gap-1.5"
          >
            <i aria-hidden className="inline-block size-2.5 rounded-[2px]" style={g.estilo} />
            <span>{g.rotulo}</span>
            <span className="ml-auto text-tinta-suave">
              {pct(g.n)}% ({g.n})
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
