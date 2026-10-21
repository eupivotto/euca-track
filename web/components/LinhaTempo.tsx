import { ROTULO_ESTADO } from "@/lib/estados";
import { horaCurta } from "@/lib/formato";
import type { ViagemDetalhe } from "@/lib/tipos";

/** Trilho com cursor arrastável e os eventos da viagem como pontos com nome e hora. */
export function LinhaTempo({
  inicio,
  fim,
  eventos,
  cursor,
  onMudar,
}: {
  inicio: string;
  fim: string;
  eventos: ViagemDetalhe["eventos"];
  cursor: number;
  onMudar: (momento: number) => void;
}) {
  const [t0, t1] = [Date.parse(inicio), Date.parse(fim)];
  const posicao = (iso: string) => `${((Date.parse(iso) - t0) / Math.max(1, t1 - t0)) * 100}%`;

  return (
    <div className="numeros px-4 pt-3 pb-4">
      <input
        type="range"
        aria-label="Momento da viagem"
        aria-valuetext={horaCurta(new Date(cursor).toISOString())}
        min={t0}
        max={t1}
        step={30_000}
        value={cursor}
        onChange={(e) => onMudar(Number(e.target.value))}
        className="w-full accent-primaria"
      />
      <ol className="relative mt-1 h-12">
        {eventos.map((e, i) => (
          <li
            key={`${e.estado}-${e.momento}`}
            aria-label={`${ROTULO_ESTADO[e.estado]} às ${horaCurta(e.momento)}`}
            className="absolute top-0 flex -translate-x-1/2 flex-col items-center text-[11px] whitespace-nowrap"
            style={{ left: posicao(e.momento) }}
          >
            <i aria-hidden className="size-2 rounded-full bg-tinta" />
            {/* Eventos próximos alternam a altura do rótulo. */}
            <span aria-hidden className={i % 2 ? "mt-4" : "mt-0.5"}>
              {ROTULO_ESTADO[e.estado]}
            </span>
            <span aria-hidden className="text-tinta-suave">
              {horaCurta(e.momento)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
