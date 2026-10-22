"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { type Armazem, enviarPendente, enviarPendentes, type Pendente, type Resultado } from "./filaOffline";

const INTERVALO_MS = 15_000;

type Opcoes = {
  enviar?: (p: Pendente) => Promise<Response>;
  // Depois de algum envio aceito (ex.: recarregar o painel).
  aoEnviar?: () => void;
  // Quando a rede volta, antes de enviar a fila (ex.: renovar a posse do caminhão).
  aoVoltarRede?: () => Promise<unknown>;
};

/** Fila local do app: guarda, envia na hora se der, de novo quando a rede volta e a cada 15 s. */
export function useFilaOffline(armazem: Armazem, opcoes: Opcoes = {}) {
  const [pendentes, setPendentes] = useState<Pendente[]>([]);
  const [recusados, setRecusados] = useState<Resultado["recusados"]>([]);
  const [online, setOnline] = useState(true);
  const enviando = useRef(false);
  // Pedido feito durante um envio em andamento: roda de novo ao terminar, para não esperar 15 s.
  const deNovo = useRef(false);
  // Refs: os efeitos não se reinscrevem a cada render por causa de funções novas.
  const atual = useRef({ armazem, opcoes });
  atual.current = { armazem, opcoes };

  const enviarAgora = useCallback(async () => {
    if (enviando.current) {
      deNovo.current = true;
      return;
    }
    enviando.current = true;
    try {
      do {
        deNovo.current = false;
        const { armazem, opcoes } = atual.current;
        const resultado = await enviarPendentes(armazem, opcoes.enviar ?? enviarPendente);
        if (resultado.recusados.length) setRecusados((r) => [...r, ...resultado.recusados]);
        if (resultado.enviados.length) opcoes.aoEnviar?.();
        setPendentes(await armazem.listar());
        if (resultado.parou) break;
      } while (deNovo.current);
    } finally {
      enviando.current = false;
    }
  }, []);

  /** Guarda e tenta enviar. false: não deu para guardar no celular (armazenamento cheio ou bloqueado). */
  const enfileirar = useCallback(
    async (p: Pendente): Promise<boolean> => {
      try {
        await atual.current.armazem.guardar(p);
      } catch {
        return false;
      }
      setPendentes(await atual.current.armazem.listar());
      await enviarAgora();
      return true;
    },
    [enviarAgora],
  );

  useEffect(() => {
    setOnline(navigator.onLine);
    const voltou = async () => {
      setOnline(true);
      // Sem rede por mais de 6 min a posse expira: renova antes, senão o check-in guardado volta 409.
      await atual.current.opcoes.aoVoltarRede?.().catch(() => {});
      await enviarAgora();
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
