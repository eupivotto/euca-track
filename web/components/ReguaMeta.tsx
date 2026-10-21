import { horaCurta, toneladas, toneladasComSinal } from "@/lib/formato";
import { esperadoAgora, fracao } from "@/lib/regua";
import type { Indicadores } from "@/lib/tipos";

const ESCALA = ["00h", "06h", "12h", "18h", "24h"];

function Numero({ valor, rotulo }: { valor: string; rotulo: string }) {
  return (
    <div className="text-xs text-tinta-suave">
      <b className="block text-[17px] font-semibold text-tinta">{valor}</b>
      {rotulo}
    </div>
  );
}

export function ReguaMeta({ indicadores }: { indicadores: Indicadores }) {
  const { toneladas: entregue, meta_t, inicio, agora } = indicadores;
  const esperado = esperadoAgora(meta_t, inicio, agora);

  return (
    <section aria-label="Meta do dia" className="numeros border-b border-linha px-4 pt-3.5 pb-4">
      <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-2">
        <span className="text-[34px] leading-none font-semibold tracking-[-0.03em]">{toneladas(entregue)}</span>
        <span className="text-sm text-tinta-suave">entregues de {toneladas(meta_t)}</span>
        <div className="ml-auto flex gap-7">
          <Numero valor={toneladasComSinal(entregue - esperado)} rotulo={`contra o esperado às ${horaCurta(agora)}`} />
          <Numero valor="—" rotulo="ciclo médio" />
          <Numero valor="—" rotulo="espera no pátio" />
        </div>
      </div>
      <div
        role="progressbar"
        aria-label="Toneladas entregues no dia"
        aria-valuemin={0}
        aria-valuemax={meta_t}
        aria-valuenow={Math.round(entregue)}
        className="relative mt-2.5 h-3 rounded-[3px] bg-trilho"
      >
        <div
          className="absolute inset-y-0 left-0 rounded-[3px] bg-primaria transition-[width] duration-700"
          style={{ width: `${fracao(entregue, meta_t) * 100}%` }}
        />
        <div
          title={`Esperado agora: ${toneladas(esperado)}`}
          className="absolute -top-[5px] -bottom-[5px] w-0.5 bg-tinta"
          style={{ left: `${fracao(esperado, meta_t) * 100}%` }}
        />
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-tinta-suave">
        {ESCALA.map((h) => (
          <span key={h}>{h}</span>
        ))}
      </div>
    </section>
  );
}
