"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { BarraMotorista } from "@/components/motorista/BarraMotorista";
import { EscolhaCaminhao } from "@/components/motorista/EscolhaCaminhao";
import { PainelViagem } from "@/components/motorista/PainelViagem";
import { assumirCaminhao, buscarCaminhoes, buscarPainelMotorista, soltarCaminhao } from "@/lib/api";
import { armazemIndexedDb } from "@/lib/armazemIndexedDb";
import { novoIdLocal } from "@/lib/filaOffline";
import type { AcaoCheckin } from "@/lib/tipos";
import { useFilaOffline } from "@/lib/useFilaOffline";

const CHAVE = "rota-motorista:caminhao";
// A posse dura 60 min simulados (6 min reais); o app renova a cada minuto real.
const RENOVAR_MS = 60_000;

function lerEscolha(): number | null {
  try {
    const valor = Number(localStorage.getItem(CHAVE));
    return valor > 0 ? valor : null;
  } catch {
    return null;
  }
}

function gravarEscolha(id: number | null) {
  try {
    if (id === null) localStorage.removeItem(CHAVE);
    else localStorage.setItem(CHAVE, String(id));
  } catch {
    // Sem armazenamento (aba privada): a escolha vale só nesta visita.
  }
}

export default function Motorista() {
  const cliente = useQueryClient();
  const [armazem] = useState(() => armazemIndexedDb());
  const [caminhaoId, setCaminhaoId] = useState<number | null>(null);
  useEffect(() => setCaminhaoId(lerEscolha()), []);

  const recarregar = useCallback(() => cliente.invalidateQueries({ queryKey: ["motorista"] }), [cliente]);
  const fila = useFilaOffline(armazem, undefined, recarregar);

  const { data: caminhoes } = useQuery({
    queryKey: ["caminhoes"],
    queryFn: buscarCaminhoes,
    enabled: caminhaoId === null,
  });
  const { data: painel } = useQuery({
    queryKey: ["motorista", caminhaoId],
    queryFn: () => buscarPainelMotorista(caminhaoId!),
    enabled: caminhaoId !== null,
    refetchInterval: 10_000,
  });

  // Assume ao escolher e renova enquanto o app está aberto.
  useEffect(() => {
    if (caminhaoId === null) return;
    const renovar = () =>
      assumirCaminhao(caminhaoId)
        .then((p) => cliente.setQueryData(["motorista", caminhaoId], p))
        .catch(() => {
          // Sem rede: tenta de novo no próximo minuto.
        });
    void renovar();
    const intervalo = setInterval(renovar, RENOVAR_MS);
    return () => clearInterval(intervalo);
  }, [caminhaoId, cliente]);

  const escolher = (id: number) => {
    gravarEscolha(id);
    setCaminhaoId(id);
  };

  const trocar = () => {
    if (caminhaoId !== null) void soltarCaminhao(caminhaoId).catch(() => {});
    gravarEscolha(null);
    setCaminhaoId(null);
  };

  const checkin = (acao: AcaoCheckin) => {
    if (caminhaoId === null) return;
    void fila.enfileirar({
      id_local: novoIdLocal(),
      tipo: "checkin",
      criado_em: new Date().toISOString(),
      dados: { caminhao_id: caminhaoId, acao },
    });
  };

  const checkinsNaFila = fila.pendentes
    .filter((p) => p.tipo === "checkin" && p.dados.caminhao_id === caminhaoId)
    .map((p) => p.dados.acao as AcaoCheckin);

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col text-[15px]">
      <BarraMotorista
        placa={painel?.caminhao.placa ?? null}
        online={fila.online}
        pendentes={fila.pendentes.length}
        onTrocar={caminhaoId !== null ? trocar : undefined}
      />
      {fila.recusados.length > 0 && (
        <div role="alert" className="flex items-start gap-3 border-b border-linha px-4 py-3 text-[14px]">
          <ul className="flex-1">
            {fila.recusados.map((motivo, i) => (
              <li key={i}>Não foi aplicado: {motivo}.</li>
            ))}
          </ul>
          <button type="button" onClick={fila.dispensarRecusados} className="min-h-11 px-1 text-primaria">
            Fechar
          </button>
        </div>
      )}
      <main className="flex-1">
        {caminhaoId === null ? (
          <>
            <h1 className="px-4 pt-5 pb-3 text-[20px] font-semibold">Qual caminhão você vai dirigir?</h1>
            {caminhoes ? (
              <EscolhaCaminhao caminhoes={caminhoes} onEscolher={escolher} />
            ) : (
              <div aria-hidden className="mx-4 h-64 rounded-lg bg-fundo-sutil" />
            )}
          </>
        ) : painel ? (
          <PainelViagem painel={painel} pendentes={checkinsNaFila} onCheckin={checkin} />
        ) : (
          <div aria-hidden className="mx-4 mt-5 h-64 rounded-lg bg-fundo-sutil" />
        )}
      </main>
    </div>
  );
}
