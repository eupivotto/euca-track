import { diaCurto, horaCheia, toneladas } from "@/lib/formato";
import type { Indicadores } from "@/lib/tipos";

/**
 * Toneladas entregues por balde (hora ou dia), com a linha tracejada do ritmo
 * necessário para bater a meta (meta ÷ número de baldes). Uma série só: sem legenda.
 */
export function BarrasToneladas({ serie, meta_t }: { serie: Indicadores["serie"]; meta_t: number }) {
  if (serie.length === 0) return null;
  const porHora = serie.length > 1 && Date.parse(serie[1].inicio) - Date.parse(serie[0].inicio) <= 3_600_000;
  const rotulo = porHora ? horaCheia : diaCurto;
  const ritmo = meta_t / serie.length;
  const topo = Math.max(ritmo, ...serie.map((b) => b.toneladas)) * 1.15;
  const altura = (t: number) => `${(t / topo) * 100}%`;
  // Rótulos do eixo: a cada 6 h no dia, a cada 5 dias no mês, todos na semana.
  const passoRotulo = porHora ? 6 : serie.length > 10 ? 5 : 1;

  return (
    <figure className="numeros">
      <div className="relative h-[240px] border-b border-linha">
        <div className="absolute inset-0 flex items-end gap-[2px]">
          {serie.map((b) => (
            <div key={b.inicio} className="group relative flex h-full flex-1 items-end">
              <div
                role="img"
                tabIndex={0}
                aria-label={`${rotulo(b.inicio)}: ${toneladas(b.toneladas)}`}
                className="w-full rounded-t-[4px] bg-primaria outline-offset-1"
                style={{ height: b.toneladas > 0 ? altura(b.toneladas) : 0 }}
              />
              <span
                aria-hidden
                className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 rounded border border-linha bg-superficie px-1.5 py-0.5 text-[11.5px] whitespace-nowrap group-focus-within:block group-hover:block"
              >
                {rotulo(b.inicio)}: {toneladas(b.toneladas)}
              </span>
            </div>
          ))}
        </div>
        <div className="pointer-events-none absolute inset-x-0 border-t border-dashed border-tinta" style={{ bottom: altura(ritmo) }}>
          <span className="absolute right-0 bottom-0.5 bg-superficie/90 px-1 text-[11px] text-tinta-suave">
            ritmo necessário: {toneladas(ritmo)} por {porHora ? "hora" : "dia"}
          </span>
        </div>
      </div>
      <div className="mt-1.5 flex gap-[2px] text-[11px] text-tinta-suave" aria-hidden>
        {serie.map((b, i) => (
          <span key={b.inicio} className="flex-1 overflow-visible whitespace-nowrap">
            {i % passoRotulo === 0 ? rotulo(b.inicio) : ""}
          </span>
        ))}
      </div>
    </figure>
  );
}
