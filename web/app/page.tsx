"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AvisoConexao } from "@/components/AvisoConexao";
import { BarraTopo } from "@/components/BarraTopo";
import { DetalheCaminhao } from "@/components/DetalheCaminhao";
import { PilulasFiltro } from "@/components/PilulasFiltro";
import { ReguaMeta } from "@/components/ReguaMeta";
import { TabelaFrota } from "@/components/TabelaFrota";
import { buscarFazendas, buscarFocos, buscarIndicadores, buscarOcorrencias, buscarRotas } from "@/lib/api";
import { useFrotaAoVivo } from "@/lib/useFrotaAoVivo";

// O MapLibre depende do navegador (WebGL).
const MapaAoVivo = dynamic(() => import("@/components/MapaAoVivo").then((m) => m.MapaAoVivo), {
  ssr: false,
  loading: () => <div className="h-full min-h-[360px] bg-trilho" />,
});

// "Ver no mapa" da tela de alertas abre com ?caminhao=<id> selecionado ou ?fazenda=<id> enquadrada.
export default function Pagina() {
  return (
    <Suspense>
      <AoVivo />
    </Suspense>
  );
}

function AoVivo() {
  const parametros = useSearchParams();
  const { caminhoes, conexao } = useFrotaAoVivo();
  // Risco e focos vêm das rotinas (outro processo, sem WebSocket): relidos a cada minuto.
  const fazendas = useQuery({ queryKey: ["fazendas"], queryFn: buscarFazendas, refetchInterval: 60_000 });
  const [horasFocos, setHorasFocos] = useState<24 | 48>(24);
  const focos = useQuery({
    queryKey: ["focos", horasFocos],
    queryFn: () => buscarFocos(horasFocos),
    refetchInterval: 60_000,
  });
  const rotas = useQuery({ queryKey: ["rotas"], queryFn: buscarRotas, staleTime: Infinity });
  const indicadores = useQuery({
    queryKey: ["indicadores", 1],
    queryFn: () => buscarIndicadores(1),
    refetchInterval: 30_000,
  });
  const [selecionadoId, setSelecionadoId] = useState<number | null>(
    () => Number(parametros.get("caminhao")) || null,
  );
  const selecionado = caminhoes.find((c) => c.id === selecionadoId);
  const viagemSelecionada = selecionado?.viagem_atual_id ?? null;
  const ocorrencias = useQuery({
    queryKey: ["ocorrencias", viagemSelecionada],
    queryFn: () => buscarOcorrencias({ viagemId: viagemSelecionada! }),
    enabled: viagemSelecionada !== null,
  });

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <BarraTopo ativa="/" />
      <AvisoConexao conexao={conexao} />
      {indicadores.data ? (
        <ReguaMeta indicadores={indicadores.data} />
      ) : (
        <div className="h-[104px] border-b border-linha" aria-hidden />
      )}
      <main className="grid flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[1.35fr_1fr]">
        <div className="relative h-[60vh] lg:h-auto">
          <MapaAoVivo
            fazendas={fazendas.data}
            rotas={rotas.data}
            focos={focos.data}
            caminhoes={caminhoes}
            selecionadoId={selecionadoId}
            onSelecionar={setSelecionadoId}
            fazendaFoco={Number(parametros.get("fazenda")) || null}
          />
          <div className="absolute top-3 left-3 text-[12px]">
            <PilulasFiltro
              rotulo="Focos de calor"
              opcoes={[
                { valor: 24 as const, rotulo: "Focos 24 h" },
                { valor: 48 as const, rotulo: "48 h" },
              ]}
              valor={horasFocos}
              onMudar={setHorasFocos}
            />
          </div>
        </div>
        <aside className="border-t border-linha lg:overflow-y-auto lg:border-t-0 lg:border-l">
          {selecionado ? (
            <DetalheCaminhao
              caminhao={selecionado}
              ocorrencias={ocorrencias.data}
              onVoltar={() => setSelecionadoId(null)}
            />
          ) : (
            <TabelaFrota caminhoes={caminhoes} onSelecionar={setSelecionadoId} />
          )}
        </aside>
      </main>
    </div>
  );
}
