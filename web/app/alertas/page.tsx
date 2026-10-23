"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { BarraTopo } from "@/components/BarraTopo";
import { PilulasFiltro } from "@/components/PilulasFiltro";
import { type GrupoAlerta, TabelaAlertas, doGrupo } from "@/components/TabelaAlertas";
import { buscarAlertas } from "@/lib/api";
import type { Alerta } from "@/lib/tipos";
import { useFrotaAoVivo } from "@/lib/useFrotaAoVivo";

export default function Alertas() {
  // O WebSocket da frota invalida as listas quando um alerta de logística abre ou fecha;
  // os de foco perto da área vêm das rotinas e chegam pela releitura a cada minuto.
  useFrotaAoVivo();
  const [status, setStatus] = useState<Alerta["status"]>("ABERTO");
  const [grupo, setGrupo] = useState<GrupoAlerta>("TODOS");
  const abertos = useQuery({
    queryKey: ["alertas", "ABERTO"],
    queryFn: () => buscarAlertas("ABERTO"),
    refetchInterval: 60_000,
  });
  const fechados = useQuery({
    queryKey: ["alertas", "FECHADO"],
    queryFn: () => buscarAlertas("FECHADO"),
    enabled: status === "FECHADO",
    refetchInterval: 60_000,
  });
  const abertosNoGrupo = abertos.data?.filter((a) => doGrupo(a, grupo)).length;
  const lista = status === "ABERTO" ? abertos.data : fechados.data;

  return (
    <div className="flex min-h-dvh flex-col">
      <BarraTopo ativa="/alertas" />
      <div className="flex flex-wrap gap-2 border-b border-linha px-4 py-2.5">
        <PilulasFiltro
          rotulo="Status"
          opcoes={[
            { valor: "ABERTO" as const, rotulo: `Abertos (${abertosNoGrupo ?? "…"})` },
            { valor: "FECHADO" as const, rotulo: "Fechados" },
          ]}
          valor={status}
          onMudar={setStatus}
        />
        <PilulasFiltro
          rotulo="Tipo"
          opcoes={[
            { valor: "TODOS" as const, rotulo: "Todos" },
            { valor: "LOGISTICA" as const, rotulo: "Logística" },
            { valor: "FOGO" as const, rotulo: "Fogo" },
          ]}
          valor={grupo}
          onMudar={setGrupo}
        />
      </div>
      <main className="flex-1 overflow-x-auto">
        {lista ? (
          <TabelaAlertas alertas={lista} status={status} grupo={grupo} />
        ) : (
          <div aria-hidden className="m-4 h-24 rounded-md bg-fundo-sutil" />
        )}
      </main>
    </div>
  );
}
