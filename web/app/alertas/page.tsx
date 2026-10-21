"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { BarraTopo } from "@/components/BarraTopo";
import { PilulasFiltro } from "@/components/PilulasFiltro";
import { TabelaAlertas } from "@/components/TabelaAlertas";
import { buscarAlertas } from "@/lib/api";
import type { Alerta } from "@/lib/tipos";
import { useFrotaAoVivo } from "@/lib/useFrotaAoVivo";

export default function Alertas() {
  // O WebSocket da frota invalida as listas quando um alerta abre ou fecha.
  useFrotaAoVivo();
  const [status, setStatus] = useState<Alerta["status"]>("ABERTO");
  const abertos = useQuery({ queryKey: ["alertas", "ABERTO"], queryFn: () => buscarAlertas("ABERTO") });
  const fechados = useQuery({
    queryKey: ["alertas", "FECHADO"],
    queryFn: () => buscarAlertas("FECHADO"),
    enabled: status === "FECHADO",
  });
  const lista = status === "ABERTO" ? abertos.data : fechados.data;

  return (
    <div className="flex min-h-dvh flex-col">
      <BarraTopo ativa="/alertas" />
      {/* O filtro Logística/Fogo entra na Fase 3, com os alertas de foco. */}
      <div className="border-b border-linha px-4 py-2.5">
        <PilulasFiltro
          rotulo="Status"
          opcoes={[
            { valor: "ABERTO" as const, rotulo: `Abertos (${abertos.data?.length ?? "…"})` },
            { valor: "FECHADO" as const, rotulo: "Fechados" },
          ]}
          valor={status}
          onMudar={setStatus}
        />
      </div>
      <main className="flex-1 overflow-x-auto">
        {lista ? (
          <TabelaAlertas alertas={lista} status={status} />
        ) : (
          <div aria-hidden className="m-4 h-24 rounded-md bg-fundo-sutil" />
        )}
      </main>
    </div>
  );
}
