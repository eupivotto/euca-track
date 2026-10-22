import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { armazemEmMemoria, type Pendente } from "./filaOffline";
import { useFilaOffline } from "./useFilaOffline";

const novo = (id_local: string): Pendente => ({
  id_local,
  tipo: "checkin",
  criado_em: new Date().toISOString(),
  dados: { caminhao_id: 1, acao: "INICIO_CARREGAMENTO" },
});

describe("useFilaOffline", () => {
  it("enfileirar tenta enviar na hora", async () => {
    const enviar = vi.fn().mockResolvedValue(new Response("{}", { status: 201 }));
    const aoEnviar = vi.fn();
    const armazem = armazemEmMemoria();
    const { result } = renderHook(() => useFilaOffline(armazem, { enviar, aoEnviar }));
    let guardou: boolean | undefined;
    await act(async () => {
      guardou = await result.current.enfileirar(novo("a"));
    });
    expect(guardou).toBe(true);
    await waitFor(() => expect(result.current.pendentes).toEqual([]));
    expect(enviar).toHaveBeenCalledTimes(1);
    expect(aoEnviar).toHaveBeenCalled();
  });

  it("sem rede o item fica pendente e sai quando a conexão volta", async () => {
    const enviar = vi.fn().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValue(new Response("{}", { status: 201 }));
    const armazem = armazemEmMemoria();
    const { result } = renderHook(() => useFilaOffline(armazem, { enviar }));
    await act(() => result.current.enfileirar(novo("a")));
    await waitFor(() => expect(result.current.pendentes.map((p) => p.id_local)).toEqual(["a"]));
    await act(async () => {
      window.dispatchEvent(new Event("online"));
    });
    await waitFor(() => expect(result.current.pendentes).toEqual([]));
  });

  it("ao voltar a rede, renova a posse antes de enviar a fila", async () => {
    const ordem: string[] = [];
    const enviar = vi.fn(async () => {
      ordem.push("enviar");
      return new Response("{}", { status: 201 });
    });
    const aoVoltarRede = vi.fn(async () => {
      ordem.push("renovar");
    });
    const armazem = armazemEmMemoria();
    await armazem.guardar(novo("a"));
    renderHook(() => useFilaOffline(armazem, { enviar, aoVoltarRede }));
    // Ao abrir, a fila envia o que estava guardado; depois chega um item novo e a rede volta.
    await waitFor(() => expect(enviar).toHaveBeenCalledTimes(1));
    ordem.length = 0;
    await armazem.guardar(novo("b"));
    await act(async () => {
      window.dispatchEvent(new Event("online"));
    });
    await waitFor(() => expect(ordem).toEqual(["renovar", "enviar"]));
  });

  it("recusado aparece com o motivo até ser dispensado", async () => {
    const enviar = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "O carregamento já foi iniciado" }), { status: 409 }),
    );
    const armazem = armazemEmMemoria();
    const { result } = renderHook(() => useFilaOffline(armazem, { enviar }));
    await act(() => result.current.enfileirar(novo("a")));
    await waitFor(() => expect(result.current.recusados).toEqual([{ id_local: "a", motivo: "O carregamento já foi iniciado" }]));
    act(() => result.current.dispensarRecusados());
    expect(result.current.recusados).toEqual([]);
  });

  it("falha ao guardar no celular devolve false e não envia nada", async () => {
    const enviar = vi.fn();
    const armazem = { ...armazemEmMemoria(), guardar: vi.fn().mockRejectedValue(new Error("QuotaExceededError")) };
    const { result } = renderHook(() => useFilaOffline(armazem, { enviar }));
    let guardou: boolean | undefined;
    await act(async () => {
      guardou = await result.current.enfileirar(novo("a"));
    });
    expect(guardou).toBe(false);
    expect(result.current.pendentes).toEqual([]);
  });
});
