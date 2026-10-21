"use client";

import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { BarraTopo } from "@/components/BarraTopo";
import { LinhaTempo } from "@/components/LinhaTempo";
import { buscarViagem, buscarViagens } from "@/lib/api";
import { diaCurto, horaCurta, toneladas } from "@/lib/formato";
import type { ViagemDetalhe } from "@/lib/tipos";

// O MapLibre depende do navegador (WebGL).
const MapaReplay = dynamic(() => import("@/components/MapaReplay").then((m) => m.MapaReplay), {
  ssr: false,
  loading: () => <div className="h-full min-h-[360px] bg-trilho" />,
});

const STATUS = { EM_ANDAMENTO: "em andamento", CONCLUIDA: "entregue", INTERROMPIDA: "interrompida" };

export default function Pagina() {
  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <BarraTopo ativa="/replay" />
      <Suspense>
        <Replay />
      </Suspense>
    </div>
  );
}

function Replay() {
  const id = Number(useSearchParams().get("viagem")) || null;
  return id ? <ReplayViagem id={id} /> : <EscolherViagem />;
}

function EscolherViagem() {
  const { data: viagens } = useQuery({ queryKey: ["viagens"], queryFn: () => buscarViagens() });
  return (
    <main className="px-4 py-3.5">
      <h1 className="pb-2 text-[15px] font-semibold">Escolha uma viagem para rever</h1>
      {!viagens ? (
        <div aria-hidden className="h-24 rounded-md bg-fundo-sutil" />
      ) : viagens.length === 0 ? (
        <p className="text-tinta-suave">Ainda não há viagens registradas.</p>
      ) : (
        <ul className="numeros max-w-2xl text-[13px]">
          {viagens.map((v) => (
            <li key={v.id} className="border-b border-linha-fraca">
              <Link href={`/replay?viagem=${v.id}`} className="flex gap-4 px-1 py-2 hover:bg-fundo-sutil">
                <span className="w-[72px] font-medium">{v.placa}</span>
                <span className="flex-1">{v.fazenda}</span>
                <span className="text-tinta-suave">
                  {diaCurto(v.inicio)}, {horaCurta(v.inicio)}, {STATUS[v.status]}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function ReplayViagem({ id }: { id: number }) {
  const { data: viagem, isPending } = useQuery({ queryKey: ["viagem", id], queryFn: () => buscarViagem(id) });
  if (isPending) return <div aria-hidden className="m-4 h-24 rounded-md bg-fundo-sutil" />;
  if (!viagem) {
    return (
      <main className="px-4 py-3.5">
        <p>Viagem não encontrada.</p>
        <Link href="/replay" className="text-primaria">
          Ver as últimas viagens
        </Link>
      </main>
    );
  }
  return <Reprodutor key={viagem.id} viagem={viagem} />;
}

function Reprodutor({ viagem }: { viagem: ViagemDetalhe }) {
  const ultimo = viagem.pontos.at(-1)?.momento;
  const fim = viagem.fim ?? ultimo ?? viagem.inicio;
  const [cursor, setCursor] = useState(() => Date.parse(viagem.inicio));

  return (
    <>
      <header className="border-b border-linha px-4 py-3">
        <h1 className="text-[20px] leading-tight font-semibold tracking-[-0.02em]">{viagem.placa}</h1>
        <p className="text-tinta-suave">
          Viagem de {diaCurto(viagem.inicio)}, {viagem.fazenda} até a fábrica, {toneladas(viagem.toneladas)}
          {viagem.status !== "CONCLUIDA" && ` (${STATUS[viagem.status]})`}
        </p>
      </header>
      <main className="flex flex-1 flex-col lg:min-h-0">
        <div className="h-[55vh] lg:h-auto lg:flex-1">
          {viagem.pontos.length === 0 ? (
            <p className="px-4 py-3.5 text-tinta-suave">Esta viagem ainda não tem posições registradas.</p>
          ) : (
            <MapaReplay viagem={viagem} cursor={cursor} />
          )}
        </div>
        <div className="border-t border-linha">
          <LinhaTempo inicio={viagem.inicio} fim={fim} eventos={viagem.eventos} cursor={cursor} onMudar={setCursor} />
        </div>
      </main>
    </>
  );
}
