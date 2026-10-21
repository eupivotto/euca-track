import { toneladas } from "@/lib/formato";
import type { Caminhao } from "@/lib/tipos";
import { MarcaEstado } from "./TabelaFrota";

function Linha({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-linha-fraca py-2">
      <dt className="text-tinta-suave">{rotulo}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  );
}

export function DetalheCaminhao({ caminhao, onVoltar }: { caminhao: Caminhao; onVoltar: () => void }) {
  return (
    <div className="numeros p-4">
      <button
        type="button"
        onClick={onVoltar}
        className="mb-3 rounded-md px-2 py-1 -ml-2 text-primaria hover:bg-fundo-sutil"
      >
        Voltar para a frota
      </button>
      <h2 className="text-[24px] leading-tight font-semibold tracking-[-0.02em]">{caminhao.placa}</h2>
      <p className="mb-3 text-tinta-suave capitalize">{caminhao.tipo}</p>
      <dl className="text-[13px]">
        <Linha rotulo="Motorista">{caminhao.motorista}</Linha>
        <Linha rotulo="Estado">
          <MarcaEstado caminhao={caminhao} />
        </Linha>
        <Linha rotulo="Carga">
          {caminhao.carga_t > 0 ? toneladas(caminhao.carga_t) : "—"}
        </Linha>
        <Linha rotulo="Capacidade">{toneladas(caminhao.capacidade_t)}</Linha>
        <Linha rotulo="Velocidade">
          {caminhao.posicao ? `${Math.round(caminhao.posicao.velocidade_kmh)} km/h` : "—"}
        </Linha>
      </dl>
    </div>
  );
}
