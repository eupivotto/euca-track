import { ROTULO_ESTADO } from "@/lib/estados";
import { horaCurta } from "@/lib/formato";
import type { ViagemDetalhe } from "@/lib/tipos";

// Fração do trilho abaixo da qual dois rótulos se sobrepõem.
const DISTANCIA_MINIMA = 0.08;

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
  const fracao = (iso: string) => (Date.parse(iso) - t0) / Math.max(1, t1 - t0);
  const posicao = (iso: string) => `${fracao(iso) * 100}%`;
  // Nas pontas o rótulo encosta para dentro, para não sair do trilho.
  const alinhamento = (iso: string) =>
    fracao(iso) < 0.08 ? "items-start" : fracao(iso) > 0.92 ? "-translate-x-full items-end" : "-translate-x-1/2 items-center";
  // Evento colado no último rotulado fica só com o ponto (nome e hora no title e no aria-label).
  let ultimoRotulado = -Infinity;
  const comRotulo = eventos.map((e) => {
    const mostrar = fracao(e.momento) - ultimoRotulado >= DISTANCIA_MINIMA;
    if (mostrar) ultimoRotulado = fracao(e.momento);
    return mostrar;
  });

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
      <ol className="relative mt-1 h-10">
        {eventos.map((e, i) => {
          const rotulo = `${ROTULO_ESTADO[e.estado]} às ${horaCurta(e.momento)}`;
          return (
            <li
              key={`${e.estado}-${e.momento}`}
              aria-label={rotulo}
              title={rotulo}
              className={`absolute top-0 flex flex-col text-[11px] whitespace-nowrap ${alinhamento(e.momento)}`}
              style={{ left: posicao(e.momento) }}
            >
              <i aria-hidden className="size-2 rounded-full bg-tinta" />
              {comRotulo[i] && (
                <>
                  <span aria-hidden className="mt-0.5">
                    {ROTULO_ESTADO[e.estado]}
                  </span>
                  <span aria-hidden className="text-tinta-suave">
                    {horaCurta(e.momento)}
                  </span>
                </>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
