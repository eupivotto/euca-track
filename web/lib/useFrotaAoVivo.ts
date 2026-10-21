"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { buscarCaminhoes, urlWebSocket } from "./api";
import type { Caminhao, Conexao, MensagemFrota } from "./tipos";

const CHAVE = ["caminhoes"];
const ESPERAS_MS = [1000, 2000, 4000, 8000, 15000];

export function esperaReconexao(tentativa: number): number {
  return ESPERAS_MS[Math.min(tentativa, ESPERAS_MS.length - 1)];
}

/** Estado da frota: carga inicial por REST e atualizações pelo WebSocket. */
export function useFrotaAoVivo(): { caminhoes: Caminhao[]; conexao: Conexao } {
  const cliente = useQueryClient();
  const { data } = useQuery({ queryKey: CHAVE, queryFn: buscarCaminhoes });
  const [conexao, setConexao] = useState<Conexao>("conectando");

  useEffect(() => {
    let ws: WebSocket;
    let tentativa = 0;
    let jaConectou = false;
    let espera: ReturnType<typeof setTimeout> | undefined;
    let encerrado = false;

    const abrir = () => {
      ws = new WebSocket(urlWebSocket());
      ws.onopen = () => {
        tentativa = 0;
        setConexao("conectado");
        // Ao voltar de uma queda, recarrega para não ficar com o que se perdeu.
        if (jaConectou) cliente.invalidateQueries({ queryKey: CHAVE });
        jaConectou = true;
      };
      ws.onmessage = (evento) => {
        const msg = JSON.parse(evento.data) as MensagemFrota;
        if (msg.tipo !== "caminhao") return;
        // Sem lista ainda: se a carga inicial falhou (API reiniciando), tenta de novo.
        if (!cliente.getQueryData(CHAVE)) {
          if (!cliente.isFetching({ queryKey: CHAVE })) cliente.invalidateQueries({ queryKey: CHAVE });
          return;
        }
        cliente.setQueryData<Caminhao[]>(CHAVE, (atual) =>
          atual?.map((c) => (c.id === msg.caminhao.id ? msg.caminhao : c)),
        );
      };
      ws.onclose = () => {
        if (encerrado) return;
        setConexao("reconectando");
        espera = setTimeout(abrir, esperaReconexao(tentativa++));
      };
    };

    abrir();
    return () => {
      encerrado = true;
      clearTimeout(espera);
      ws.close();
    };
  }, [cliente]);

  return { caminhoes: data ?? [], conexao };
}
