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
    const { result } = renderHook(() => useFilaOffline(armazem, enviar, aoEnviar));
    await act(() => result.current.enfileirar(novo("a")));
    await waitFor(() => expect(result.current.pendentes).toEqual([]));
    expect(enviar).toHaveBeenCalledTimes(1);
    expect(aoEnviar).toHaveBeenCalled();
  });

  it("sem rede o item fica pendente e sai quando a conexão volta", async () => {
    const enviar = vi.fn().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValue(new Response("{}", { status: 201 }));
    const armazem = armazemEmMemoria();
    const { result } = renderHook(() => useFilaOffline(armazem, enviar));
    await act(() => result.current.enfileirar(novo("a")));
    await waitFor(() => expect(result.current.pendentes.map((p) => p.id_local)).toEqual(["a"]));
    await act(async () => {
      window.dispatchEvent(new Event("online"));
    });
    await waitFor(() => expect(result.current.pendentes).toEqual([]));
  });

  it("recusado aparece com o motivo até ser dispensado", async () => {
    const enviar = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Assuma o caminhão antes do check-in" }), { status: 409 }),
    );
    const armazem = armazemEmMemoria();
    const { result } = renderHook(() => useFilaOffline(armazem, enviar));
    await act(() => result.current.enfileirar(novo("a")));
    await waitFor(() => expect(result.current.recusados).toEqual(["Assuma o caminhão antes do check-in"]));
    act(() => result.current.dispensarRecusados());
    expect(result.current.recusados).toEqual([]);
  });
});
