"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { BarraMotorista } from "@/components/motorista/BarraMotorista";
import { EscolhaCaminhao } from "@/components/motorista/EscolhaCaminhao";
import { FormOcorrencia, type NovaOcorrencia } from "@/components/motorista/FormOcorrencia";
import { PainelViagem } from "@/components/motorista/PainelViagem";
import { assumirCaminhao, buscarCaminhoes, buscarPainelMotorista, soltarCaminhao } from "@/lib/api";
import { armazemIndexedDb } from "@/lib/armazemIndexedDb";
import { novoIdLocal } from "@/lib/filaOffline";
import { acoesEmEspera, confirmacaoOcorrencia, guardarPainel, lerPainelGuardado } from "@/lib/motorista";
import type { AcaoCheckin, Passo } from "@/lib/tipos";
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
  const [registrando, setRegistrando] = useState(false);
  // id_local da última ocorrência registrada, para a confirmação acompanhar a fila.
  const [confirmacao, setConfirmacao] = useState<string | null>(null);
  // Último check-in feito e o passo de quando foi feito: segura o botão até o painel mudar.
  const [enviada, setEnviada] = useState<{ id_local: string; acao: AcaoCheckin; passo: Passo } | null>(null);
  const [erroGuardar, setErroGuardar] = useState(false);
  useEffect(() => setCaminhaoId(lerEscolha()), []);

  const recarregar = useCallback(() => cliente.invalidateQueries({ queryKey: ["motorista"] }), [cliente]);
  // Assume o caminhão ou renova a posse; sem rede, falha e tenta de novo na próxima vez.
  const renovar = useCallback(async () => {
    if (caminhaoId === null) return;
    const novo = await assumirCaminhao(caminhaoId);
    cliente.setQueryData(["motorista", caminhaoId], novo);
  }, [caminhaoId, cliente]);
  const fila = useFilaOffline(armazem, { aoEnviar: recarregar, aoVoltarRede: renovar });

  const { data: caminhoes } = useQuery({
    queryKey: ["caminhoes"],
    queryFn: buscarCaminhoes,
    enabled: caminhaoId === null,
  });
  const { data: painel } = useQuery({
    queryKey: ["motorista", caminhaoId],
    queryFn: async () => {
      const novo = await buscarPainelMotorista(caminhaoId!);
      guardarPainel(caminhaoId!, novo);
      return novo;
    },
    enabled: caminhaoId !== null,
    refetchInterval: 10_000,
    // Sem rede, abre com o último painel visto (a busca tenta de novo a cada 10 s).
    initialData: () => (caminhaoId !== null ? lerPainelGuardado(caminhaoId) : undefined),
    initialDataUpdatedAt: 0,
  });

  // Assume ao escolher e renova enquanto o app está aberto.
  useEffect(() => {
    if (caminhaoId === null) return;
    const tentar = () => renovar().catch(() => {});
    void tentar();
    const intervalo = setInterval(tentar, RENOVAR_MS);
    return () => clearInterval(intervalo);
  }, [caminhaoId, renovar]);

  const escolher = (id: number) => {
    gravarEscolha(id);
    setCaminhaoId(id);
  };

  const trocar = () => {
    if (caminhaoId !== null) void soltarCaminhao(caminhaoId).catch(() => {});
    gravarEscolha(null);
    setCaminhaoId(null);
  };

  const checkin = async (acao: AcaoCheckin) => {
    if (caminhaoId === null || !painel) return;
    const id_local = novoIdLocal();
    setEnviada({ id_local, acao, passo: painel.passo });
    const guardou = await fila.enfileirar({
      id_local,
      tipo: "checkin",
      criado_em: new Date().toISOString(),
      dados: { caminhao_id: caminhaoId, acao },
    });
    if (!guardou) {
      setEnviada(null);
      setErroGuardar(true);
    }
  };

  const registrarOcorrencia = async ({ tipo, descricao, foto }: NovaOcorrencia): Promise<boolean> => {
    if (caminhaoId === null) return false;
    const id_local = novoIdLocal();
    const guardou = await fila.enfileirar({
      id_local,
      tipo: "ocorrencia",
      criado_em: new Date().toISOString(),
      dados: { caminhao_id: caminhaoId, tipo, descricao },
      foto,
    });
    // O formulário só fecha com a ocorrência guardada; senão ele avisa e mantém o que foi escrito.
    if (!guardou) return false;
    setRegistrando(false);
    // Depois da primeira tentativa de envio, para não piscar "registrada" antes de guardar.
    setConfirmacao(id_local);
    return true;
  };

  const checkinsNaFila = fila.pendentes
    .filter((p) => p.tipo === "checkin" && p.dados.caminhao_id === caminhaoId)
    .map((p) => p.dados.acao as AcaoCheckin);
  const emEspera = painel ? acoesEmEspera(
        checkinsNaFila,
        enviada,
        painel.passo,
        fila.recusados.map((r) => r.id_local),
      ) : checkinsNaFila;

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col text-[15px]">
      <BarraMotorista
        placa={painel?.caminhao.placa ?? null}
        online={fila.online}
        pendentes={fila.pendentes.length}
        onTrocar={caminhaoId !== null ? trocar : undefined}
      />
      {erroGuardar && (
        <div role="alert" className="flex items-start gap-3 border-b border-linha px-4 py-3 text-[14px]">
          <p className="flex-1">Não foi possível guardar o check-in no celular. Tente de novo.</p>
          <button type="button" onClick={() => setErroGuardar(false)} className="min-h-11 px-1 text-primaria">
            Fechar
          </button>
        </div>
      )}
      {fila.recusados.length > 0 && (
        <div role="alert" className="flex items-start gap-3 border-b border-linha px-4 py-3 text-[14px]">
          <ul className="flex-1">
            {fila.recusados.map(({ id_local, motivo }) => (
              <li key={id_local}>Não foi aplicado. {motivo}.</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => {
              // Sem isto, o check-in recusado voltaria a segurar o botão ao sair da lista.
              setEnviada(null);
              fila.dispensarRecusados();
            }}
            className="min-h-11 px-1 text-primaria"
          >
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
        ) : registrando ? (
          <FormOcorrencia onEnviar={registrarOcorrencia} onCancelar={() => setRegistrando(false)} />
        ) : painel ? (
          <>
            {confirmacao && (
              <p role="status" className="mx-4 mt-4 rounded-md bg-fundo-sutil px-3 py-2 text-[14px]">
                {confirmacaoOcorrencia(
                  confirmacao,
                  fila.pendentes.map((p) => p.id_local),
                )}
              </p>
            )}
            <PainelViagem
              painel={painel}
              pendentes={emEspera}
              online={fila.online}
              onCheckin={(acao) => void checkin(acao)}
            />
            <div className="border-t border-linha px-4 py-5">
              <button
                type="button"
                onClick={() => {
                  setConfirmacao(null);
                  setRegistrando(true);
                }}
                className="h-12 w-full rounded-lg border border-linha text-[15px] font-medium"
              >
                Registrar ocorrência
              </button>
            </div>
          </>
        ) : (
          <div aria-hidden className="mx-4 mt-5 h-64 rounded-lg bg-fundo-sutil" />
        )}
      </main>
    </div>
  );
}
