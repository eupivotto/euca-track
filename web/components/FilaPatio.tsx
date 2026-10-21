import { duracao, horaCurta } from "@/lib/formato";
import type { Patio } from "@/lib/tipos";

/** "Fila agora": em ordem de chegada, então a numeração é a posição real. */
export function FilaPatio({ fila }: { fila: Patio["fila"] }) {
  return (
    <section aria-labelledby="titulo-fila">
      <h2 id="titulo-fila" className="px-4 pt-3.5 pb-2 text-[15px] font-semibold">
        Fila agora
      </h2>
      {fila.length === 0 ? (
        <p className="px-4 pb-4 text-tinta-suave">Ninguém na fila agora.</p>
      ) : (
        <table className="numeros w-full border-collapse text-[12.5px]">
          <thead>
            <tr className="text-left text-[11.5px] text-tinta-suave">
              <th className="border-b border-linha px-4 py-2 font-medium">Posição</th>
              <th className="border-b border-linha px-3 py-2 font-medium">Placa</th>
              <th className="border-b border-linha px-3 py-2 text-right font-medium">Chegou</th>
              <th className="border-b border-linha px-4 py-2 text-right font-medium">Esperando</th>
            </tr>
          </thead>
          <tbody>
            {fila.map((f) => (
              <tr key={f.caminhao_id}>
                <td className="border-b border-linha-fraca px-4 py-[7px]">{f.posicao}</td>
                <td className="border-b border-linha-fraca px-3 py-[7px] font-medium">{f.placa}</td>
                <td className="border-b border-linha-fraca px-3 py-[7px] text-right">{horaCurta(f.chegou_em)}</td>
                <td className="border-b border-linha-fraca px-4 py-[7px] text-right">{duracao(f.esperando_min)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
