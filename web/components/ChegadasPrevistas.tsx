import { horaCurta } from "@/lib/formato";
import type { Patio } from "@/lib/tipos";

const JANELA_MS = 2 * 60 * 60 * 1000;
const HORA_MS = 60 * 60 * 1000;

/** Linha do tempo das próximas 2 h: um traço por caminhão carregado previsto. */
export function ChegadasPrevistas({ agora, chegadas }: { agora: string; chegadas: Patio["chegadas"] }) {
  const inicio = Date.parse(agora);
  const posicao = (eta: string) =>
    Math.min(100, Math.max(0, ((Date.parse(eta) - inicio) / JANELA_MS) * 100));
  const escala = [0, 1, 2].map((h) => new Date(inicio + h * HORA_MS).toISOString());

  return (
    <section aria-labelledby="titulo-chegadas" className="px-4 pt-3.5 pb-4">
      <h2 id="titulo-chegadas" className="pb-2 text-[15px] font-semibold">
        Chegadas previstas
      </h2>
      {chegadas.length === 0 && (
        <p className="pb-3 text-tinta-suave">Nenhum caminhão carregado chega nas próximas 2 h.</p>
      )}
      <ol className="relative mt-2 h-[150px] border-b border-linha">
        {chegadas.map((c, i) => (
          <li
            key={c.caminhao_id}
            aria-label={`${c.placa}, chega às ${horaCurta(c.eta)}${c.fazenda ? `, de ${c.fazenda}` : ""}`}
            className="absolute bottom-0 flex flex-col items-start"
            style={{ left: `${posicao(c.eta)}%` }}
          >
            {/* Alturas alternadas para placas próximas não se sobreporem. */}
            <span className="numeros -translate-x-1/2 pb-1 text-[11.5px] font-medium whitespace-nowrap">
              {c.placa}
            </span>
            <span aria-hidden className="w-0.5 bg-primaria" style={{ height: 28 + (i % 4) * 26 }} />
          </li>
        ))}
      </ol>
      <div className="numeros mt-1.5 flex justify-between text-[11px] text-tinta-suave">
        {escala.map((m) => (
          <span key={m}>{horaCurta(m)}</span>
        ))}
      </div>
    </section>
  );
}
