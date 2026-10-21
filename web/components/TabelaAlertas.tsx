import Link from "next/link";
import { ROTULO_ALERTA } from "@/lib/estados";
import { horaCurta } from "@/lib/formato";
import type { Alerta } from "@/lib/tipos";

export function TabelaAlertas({ alertas, status }: { alertas: Alerta[]; status: Alerta["status"] }) {
  if (alertas.length === 0) {
    return (
      <p className="px-4 py-4 text-tinta-suave">
        {status === "ABERTO" ? "Nenhum alerta aberto." : "Nenhum alerta fechado."}
      </p>
    );
  }
  return (
    <table className="numeros w-full border-collapse text-[12.5px]">
      <thead>
        <tr className="text-left text-[11.5px] text-tinta-suave">
          <th className="border-b border-linha px-4 py-2 font-medium">Hora</th>
          <th className="border-b border-linha px-3 py-2 font-medium">Tipo</th>
          <th className="border-b border-linha px-3 py-2 font-medium">Caminhão</th>
          <th className="border-b border-linha px-3 py-2 font-medium">O que aconteceu</th>
          <th className="border-b border-linha px-3 py-2 font-medium">Status</th>
          <th className="border-b border-linha px-4 py-2 font-medium">
            <span className="sr-only">Mapa</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {alertas.map((a) => {
          const aberto = a.status === "ABERTO";
          return (
            <tr key={a.id} className={aberto ? undefined : "text-tinta-suave"}>
              <td className="border-b border-linha-fraca px-4 py-[7px]">{horaCurta(a.aberto_em)}</td>
              <td className="border-b border-linha-fraca px-3 py-[7px]">
                <span className={aberto ? "font-semibold text-atencao" : "font-semibold"}>
                  {ROTULO_ALERTA[a.tipo]}
                </span>
              </td>
              <td className="border-b border-linha-fraca px-3 py-[7px] font-medium">{a.placa ?? a.fazenda}</td>
              <td className="border-b border-linha-fraca px-3 py-[7px]">{a.mensagem}</td>
              <td className="border-b border-linha-fraca px-3 py-[7px] whitespace-nowrap">
                {aberto ? "Aberto" : `Fechado às ${horaCurta(a.fechado_em!)}`}
              </td>
              <td className="border-b border-linha-fraca px-4 py-[7px] text-right whitespace-nowrap">
                {a.caminhao_id !== null && (
                  <Link
                    href={`/?caminhao=${a.caminhao_id}`}
                    aria-label={`Ver ${a.placa} no mapa`}
                    className="rounded-md px-2 py-1 text-primaria hover:bg-fundo-sutil"
                  >
                    Ver no mapa
                  </Link>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
