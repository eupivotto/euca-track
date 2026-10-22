import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { caminhao } from "./fabricas.test-util";
import { esperaReconexao, useFrotaAoVivo } from "./useFrotaAoVivo";

vi.mock("./api", () => ({
  buscarCaminhoes: vi.fn(),
  urlWebSocket: () => "ws://teste/ws/frota",
}));
import { buscarCaminhoes } from "./api";

class WsFalso {
  static instancias: WsFalso[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(public url: string) {
    WsFalso.instancias.push(this);
  }
  close() {
    this.onclose?.();
  }
  abrir() {
    act(() => this.onopen?.());
  }
  receber(msg: unknown) {
    act(() => this.onmessage?.({ data: JSON.stringify(msg) }));
  }
  cair() {
    act(() => this.onclose?.());
  }
}

const ultimo = () => WsFalso.instancias[WsFalso.instancias.length - 1];

function renderizar(cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  return renderHook(() => useFrotaAoVivo(), {
    wrapper: ({ children }) => <QueryClientProvider client={cliente}>{children}</QueryClientProvider>,
  });
}

beforeEach(() => {
  WsFalso.instancias = [];
  vi.stubGlobal("WebSocket", WsFalso);
  vi.mocked(buscarCaminhoes).mockReset();
  vi.mocked(buscarCaminhoes).mockResolvedValue([caminhao("TLG1A23", "CARREGANDO", 0, { id: 1 })]);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useFrotaAoVivo", () => {
  it("espera entre tentativas cresce até 15 s", () => {
    expect([0, 1, 2, 3, 4, 5].map(esperaReconexao)).toEqual([1000, 2000, 4000, 8000, 15000, 15000]);
  });

  it("aplica mensagem do WebSocket sobre a carga inicial", async () => {
    const { result } = renderizar();
    await waitFor(() => expect(result.current.caminhoes).toHaveLength(1));
    ultimo().abrir();
    ultimo().receber({ tipo: "caminhao", caminhao: caminhao("TLG1A23", "FILA_PATIO", 55, { id: 1 }) });
    await waitFor(() => expect(result.current.caminhoes[0].estado_atual).toBe("FILA_PATIO"));
    expect(result.current.conexao).toBe("conectado");
  });

  it("ignora mensagem que chega antes da carga inicial sem quebrar", async () => {
    vi.mocked(buscarCaminhoes).mockReturnValue(new Promise(() => {}));
    const { result } = renderizar();
    ultimo().receber({ tipo: "caminhao", caminhao: caminhao("TLG1A23", "FILA_PATIO", 55, { id: 1 }) });
    expect(result.current.caminhoes).toEqual([]);
  });

  it("tenta a carga inicial de novo se ela falhou e o WebSocket está vivo", async () => {
    // A página abriu com a API reiniciando: o REST falhou, depois o WebSocket conectou.
    vi.mocked(buscarCaminhoes)
      .mockRejectedValueOnce(new Error("502"))
      .mockResolvedValue([caminhao("TLG1A23", "CARREGANDO", 0, { id: 1 })]);
    const { result } = renderizar();
    await waitFor(() => expect(buscarCaminhoes).toHaveBeenCalledTimes(1));
    await new Promise((r) => setTimeout(r, 0));
    ultimo().abrir();
    ultimo().receber({ tipo: "caminhao", caminhao: caminhao("TLG1A23", "FILA_PATIO", 55, { id: 1 }) });
    await waitFor(() => expect(result.current.caminhoes).toHaveLength(1));
  });

  it("mensagem de alerta invalida as listas de alertas e do pátio", async () => {
    const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidar = vi.spyOn(cliente, "invalidateQueries");
    const { result } = renderizar(cliente);
    await waitFor(() => expect(result.current.caminhoes).toHaveLength(1));
    ultimo().abrir();
    ultimo().receber({
      tipo: "alerta",
      alerta: {
        id: 1, tipo: "PARADA", caminhao_id: 1, placa: "TLG1A23", fazenda_id: null, fazenda: null,
        mensagem: "Parado há 16 min fora de fazenda ou fábrica", aberto_em: "2026-10-20T14:00:00Z",
        fechado_em: null, status: "ABERTO",
      },
    });
    expect(invalidar).toHaveBeenCalledWith({ queryKey: ["alertas"] });
    expect(invalidar).toHaveBeenCalledWith({ queryKey: ["patio"] });
    // A frota não muda com a mensagem de alerta.
    expect(result.current.caminhoes[0].estado_atual).toBe("CARREGANDO");
  });

  it("mensagem de ocorrência invalida a lista de ocorrências", async () => {
    const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidar = vi.spyOn(cliente, "invalidateQueries");
    const { result } = renderizar(cliente);
    await waitFor(() => expect(result.current.caminhoes).toHaveLength(1));
    ultimo().abrir();
    ultimo().receber({
      tipo: "ocorrencia",
      ocorrencia: {
        id: 9, caminhao_id: 1, placa: "TLG1A23", viagem_id: 42, tipo: "PNEU", descricao: "Pneu furado",
        foto_url: null, momento: "2026-10-20T18:50:00Z",
      },
    });
    expect(invalidar).toHaveBeenCalledWith({ queryKey: ["ocorrencias"] });
    expect(result.current.caminhoes[0].estado_atual).toBe("CARREGANDO");
  });

  it("mostra reconectando enquanto está fora e reconecta com espera crescente", async () => {
    vi.useFakeTimers();
    const { result } = renderizar();
    expect(result.current.conexao).toBe("conectando");
    const esperas = [1000, 2000, 4000, 8000, 15000, 15000];
    for (const espera of esperas) {
      const antes = WsFalso.instancias.length;
      ultimo().cair();
      expect(result.current.conexao).toBe("reconectando");
      act(() => vi.advanceTimersByTime(espera - 1));
      expect(WsFalso.instancias.length).toBe(antes);
      act(() => vi.advanceTimersByTime(1));
      expect(WsFalso.instancias.length).toBe(antes + 1);
    }
  });

  it("zera a espera depois de conectar", () => {
    vi.useFakeTimers();
    renderizar();
    ultimo().cair();
    act(() => vi.advanceTimersByTime(1000));
    ultimo().cair();
    act(() => vi.advanceTimersByTime(2000));
    ultimo().abrir();
    const antes = WsFalso.instancias.length;
    ultimo().cair();
    act(() => vi.advanceTimersByTime(1000));
    expect(WsFalso.instancias.length).toBe(antes + 1);
  });

  it("fecha o WebSocket ao desmontar, sem reconectar", () => {
    vi.useFakeTimers();
    const { unmount } = renderizar();
    unmount();
    act(() => vi.advanceTimersByTime(60_000));
    expect(WsFalso.instancias).toHaveLength(1);
  });
});
