"use client";

import { useQuery } from "@tanstack/react-query";
import { BarraTopo } from "@/components/BarraTopo";
import { ChegadasPrevistas } from "@/components/ChegadasPrevistas";
import { FaixaNumeros } from "@/components/FaixaNumeros";
import { FilaPatio } from "@/components/FilaPatio";
import { buscarPatio } from "@/lib/api";
import { duracao } from "@/lib/formato";
import { useFrotaAoVivo } from "@/lib/useFrotaAoVivo";

export default function Patio() {
  // O WebSocket da frota invalida o pátio quando abre ou fecha alerta; o resto vem do intervalo.
  useFrotaAoVivo();
  const { data: patio } = useQuery({ queryKey: ["patio"], queryFn: buscarPatio, refetchInterval: 30_000 });

  return (
    <div className="flex min-h-dvh flex-col">
      <BarraTopo ativa="/patio" />
      {patio ? (
        <>
          <FaixaNumeros
            itens={[
              { valor: String(patio.fila.length), rotulo: "na fila" },
              { valor: `${patio.vagas_ocupadas} de ${patio.vagas_total}`, rotulo: "vagas de descarga ocupadas" },
              { valor: duracao(patio.espera_media_min), rotulo: "espera média hoje" },
              { valor: String(patio.chegadas.length), rotulo: "chegando nas próximas 2 h" },
            ]}
          />
          <main className="grid flex-1 grid-cols-1 lg:grid-cols-2">
            <FilaPatio fila={patio.fila} />
            <div className="border-t border-linha lg:border-t-0 lg:border-l">
              <ChegadasPrevistas agora={patio.agora} chegadas={patio.chegadas} />
            </div>
          </main>
        </>
      ) : (
        <div aria-hidden className="h-[74px] border-b border-linha bg-fundo-sutil" />
      )}
    </div>
  );
}
