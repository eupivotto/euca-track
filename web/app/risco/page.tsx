"use client";

import { useQuery } from "@tanstack/react-query";
import { BarraTopo } from "@/components/BarraTopo";
import { GradeRisco } from "@/components/GradeRisco";
import { buscarHistoricoRisco } from "@/lib/api";

export default function Risco() {
  const historico = useQuery({
    queryKey: ["risco", "historico", 30],
    queryFn: () => buscarHistoricoRisco(30),
    refetchInterval: 60_000,
  });

  return (
    <div className="flex min-h-dvh flex-col">
      <BarraTopo ativa="/risco" />
      <main className="flex flex-col gap-1 px-4 py-4">
        <h1 className="text-[15px] font-semibold">Risco de incêndio por área</h1>
        <p className="max-w-[70ch] text-[12.5px] text-tinta-suave">
          Fórmula de Monte Alegre nos últimos 30 dias, com a umidade das 13h e a chuva do dia de cada área
          (Open-Meteo). Hoje usa a previsão e é recalculado a cada 3 horas.
        </p>
        <div className="mt-3">
          {historico.data ? (
            <GradeRisco historico={historico.data} />
          ) : historico.isError ? (
            <p className="text-tinta-suave">Não foi possível carregar o risco. A página tenta de novo em 1 minuto.</p>
          ) : (
            <div aria-hidden className="h-40 rounded-md bg-fundo-sutil" />
          )}
        </div>
      </main>
    </div>
  );
}
