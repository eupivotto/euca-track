"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { type Armazem, enviarPendente, enviarPendentes, type Pendente } from "./filaOffline";

const INTERVALO_MS = 15_000;

/**
 * Fila local do app: guarda, envia na hora se der, de novo quando a rede volta
 * e a cada 15 s. aoEnviar roda depois de algum envio aceito (ex.: recarregar o painel).
 */
export function useFilaOffline(
  armazem: Armazem,
  enviar: (p: Pendente) => Promise<Response> = enviarPendente,
  aoEnviar?: () => void,
) {
  const [pendentes, setPendentes] = useState<Pendente[]>([]);
  const [recusados, setRecusados] = useState<string[]>([]);
  const [online, setOnline] = useState(true);
  const enviando = useRef(false);
  // Refs: os efeitos não se reinscrevem a cada render por causa de funções novas.
  const atual = useRef({ armazem, enviar, aoEnviar });
  atual.current = { armazem, enviar, aoEnviar };

  // Pedido feito durante um envio em andamento: roda de novo ao terminar, para não esperar 15 s.
  const deNovo = useRef(false);

  const enviarAgora = useCallback(async () => {
    if (enviando.current) {
      deNovo.current = true;
      return;
    }
    enviando.current = true;
    try {
      do {
        deNovo.current = false;
        const { armazem, enviar, aoEnviar } = atual.current;
        const resultado = await enviarPendentes(armazem, enviar);
        if (resultado.recusados.length) setRecusados((r) => [...r, ...resultado.recusados.map((x) => x.motivo)]);
        if (resultado.enviados.length) aoEnviar?.();
        setPendentes(await armazem.listar());
        if (resultado.parou) break;
      } while (deNovo.current);
    } finally {
      enviando.current = false;
    }
  }, []);

  const enfileirar = useCallback(
    async (p: Pendente) => {
      await atual.current.armazem.guardar(p);
      setPendentes(await atual.current.armazem.listar());
      await enviarAgora();
    },
    [enviarAgora],
  );

  useEffect(() => {
    setOnline(navigator.onLine);
    const voltou = () => {
      setOnline(true);
      void enviarAgora();
    };
    const caiu = () => setOnline(false);
    window.addEventListener("online", voltou);
    window.addEventListener("offline", caiu);
    const intervalo = setInterval(() => void enviarAgora(), INTERVALO_MS);
    // O que ficou guardado de uma visita anterior sai assim que a página abre.
    void enviarAgora();
    return () => {
      window.removeEventListener("online", voltou);
      window.removeEventListener("offline", caiu);
      clearInterval(intervalo);
    };
  }, [enviarAgora]);

  const dispensarRecusados = useCallback(() => setRecusados([]), []);

  return { pendentes, recusados, online, enfileirar, enviarAgora, dispensarRecusados };
}
