"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { buscarIndicadores } from "@/lib/api";
import { duracao, toneladas } from "@/lib/formato";
import { BarrasToneladas } from "./BarrasToneladas";
import { FaixaNumeros } from "./FaixaNumeros";
import { PilulasFiltro } from "./PilulasFiltro";
import { UsoFrota } from "./UsoFrota";

const PERIODOS = [
  { valor: 1, rotulo: "Hoje" },
  { valor: 7, rotulo: "7 dias" },
  { valor: 30, rotulo: "30 dias" },
];

export function TelaIndicadores() {
  const [dias, setDias] = useState(1);
  const { data: ind } = useQuery({
    queryKey: ["indicadores", dias],
    queryFn: () => buscarIndicadores(dias),
    refetchInterval: 60_000,
  });

  return (
    <>
      <div className="border-b border-linha px-4 py-2.5">
        <PilulasFiltro rotulo="Período" opcoes={PERIODOS} valor={dias} onMudar={setDias} />
      </div>
      {ind ? (
        <>
          <FaixaNumeros
            itens={[
              { valor: toneladas(ind.toneladas), rotulo: `de ${toneladas(ind.meta_t)}` },
              { valor: ind.viagens.toLocaleString("pt-BR"), rotulo: "viagens entregues" },
              { valor: duracao(ind.ciclo_medio_min), rotulo: "ciclo médio" },
              { valor: duracao(ind.fila_media_min), rotulo: "fila média" },
              { valor: `${Math.round(ind.uso_frota * 100)}%`, rotulo: "da frota em uso agora" },
            ]}
          />
          <main className="grid flex-1 grid-cols-1 lg:grid-cols-[1.6fr_1fr]">
            <section aria-labelledby="titulo-toneladas" className="px-4 pt-3.5 pb-5">
              <h2 id="titulo-toneladas" className="pb-3 text-[15px] font-semibold">
                Toneladas entregues por {dias === 1 ? "hora" : "dia"}
              </h2>
              <BarrasToneladas serie={ind.serie} meta_t={ind.meta_t} />
            </section>
            <section
              aria-labelledby="titulo-uso"
              className="border-t border-linha px-4 pt-3.5 pb-5 lg:border-t-0 lg:border-l"
            >
              <h2 id="titulo-uso" className="pb-3 text-[15px] font-semibold">
                Uso da frota agora
              </h2>
              <UsoFrota frota={ind.frota_por_estado} />
            </section>
          </main>
        </>
      ) : (
        <div aria-hidden className="h-[74px] border-b border-linha bg-fundo-sutil" />
      )}
    </>
  );
}
