import { MARCADOR_ESTADO, ROTULO_ESTADO } from "@/lib/estados";
import { horaCurta, toneladas } from "@/lib/formato";
import { ordenarFrota } from "@/lib/ordenarFrota";
import type { Caminhao } from "@/lib/tipos";

export function MarcaEstado({ caminhao }: { caminhao: Caminhao }) {
  if (!caminhao.estado_atual) return <span className="text-tinta-suave">Sem sinal</span>;
  const { cor, contorno } = MARCADOR_ESTADO[caminhao.estado_atual];
  return (
    <span className="inline-flex items-center gap-1.5">
      <i
        aria-hidden
        className="inline-block size-[7px] rounded-[2px]"
        style={contorno ? { boxShadow: `inset 0 0 0 1.5px ${cor}` } : { background: cor }}
      />
      {ROTULO_ESTADO[caminhao.estado_atual]}
    </span>
  );
}

export function TabelaFrota({
  caminhoes,
  onSelecionar,
}: {
  caminhoes: Caminhao[];
  onSelecionar: (id: number) => void;
}) {
  return (
    <table className="numeros w-full border-collapse text-[12.5px]">
      <thead>
        <tr className="text-left text-[11.5px] text-tinta-suave">
          <th className="border-b border-linha px-3 py-2 font-medium">Placa</th>
          <th className="border-b border-linha px-3 py-2 font-medium">Estado</th>
          <th className="border-b border-linha px-3 py-2 text-right font-medium">Carga</th>
          <th className="border-b border-linha px-3 py-2 text-right font-medium">ETA</th>
        </tr>
      </thead>
      <tbody>
        {ordenarFrota(caminhoes).map((c) => (
          <tr
            key={c.id}
            tabIndex={0}
            onClick={() => onSelecionar(c.id)}
            onKeyDown={(e) => e.key === "Enter" && onSelecionar(c.id)}
            className={
              c.alertas_abertos.length > 0
                ? "cursor-pointer bg-atencao-fundo hover:bg-atencao-fundo/70"
                : "cursor-pointer hover:bg-fundo-sutil focus-visible:bg-fundo-sutil"
            }
          >
            <td className="border-b border-linha-fraca px-3 py-[7px] font-medium whitespace-nowrap">
              {c.placa}
              {c.assumido && (
                <span
                  title="Com o app do motorista"
                  className="ml-1.5 rounded border border-primaria px-1 text-[10.5px] font-semibold text-primaria"
                >
                  App
                </span>
              )}
            </td>
            <td className="border-b border-linha-fraca px-3 py-[7px]">
              <MarcaEstado caminhao={c} />
            </td>
            <td className="border-b border-linha-fraca px-3 py-[7px] text-right">
              {c.carga_t > 0 ? toneladas(c.carga_t) : "—"}
            </td>
            <td className="border-b border-linha-fraca px-3 py-[7px] text-right">
              {c.eta ? horaCurta(c.eta) : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
