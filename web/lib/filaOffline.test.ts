import { describe, expect, it, vi } from "vitest";
import { armazemEmMemoria, enviarPendente, enviarPendentes, type Pendente } from "./filaOffline";

function pendente(id_local: string, criado_em: string, extra: Partial<Pendente> = {}): Pendente {
  return {
    id_local,
    tipo: "checkin",
    criado_em,
    dados: { caminhao_id: 1, acao: "INICIO_CARREGAMENTO" },
    ...extra,
  };
}

const resposta = (status: number, corpo: unknown = {}) =>
  new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } });

describe("enviarPendentes", () => {
  it("envia na ordem em que foram criados e tira da fila", async () => {
    const armazem = armazemEmMemoria();
    await armazem.guardar(pendente("b", "2026-10-21T10:01:00Z"));
    await armazem.guardar(pendente("a", "2026-10-21T10:00:00Z"));
    const ordem: string[] = [];
    const r = await enviarPendentes(armazem, async (p) => {
      ordem.push(p.id_local);
      return resposta(201);
    });
    expect(ordem).toEqual(["a", "b"]);
    expect(r).toEqual({ enviados: ["a", "b"], recusados: [], parou: false });
    expect(await armazem.listar()).toEqual([]);
  });

  it("recusado pela API (409) sai da fila com o motivo", async () => {
    const armazem = armazemEmMemoria();
    await armazem.guardar(pendente("a", "2026-10-21T10:00:00Z"));
    await armazem.guardar(pendente("b", "2026-10-21T10:01:00Z"));
    const r = await enviarPendentes(armazem, async (p) =>
      p.id_local === "a" ? resposta(409, { detail: "Assuma o caminhão antes do check-in" }) : resposta(201),
    );
    expect(r.recusados).toEqual([{ id_local: "a", motivo: "Assuma o caminhão antes do check-in" }]);
    expect(r.enviados).toEqual(["b"]);
    expect(await armazem.listar()).toEqual([]);
  });

  it("sem rede para e não perde nada", async () => {
    const armazem = armazemEmMemoria();
    await armazem.guardar(pendente("a", "2026-10-21T10:00:00Z"));
    await armazem.guardar(pendente("b", "2026-10-21T10:01:00Z"));
    const enviar = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const r = await enviarPendentes(armazem, enviar);
    expect(r).toEqual({ enviados: [], recusados: [], parou: true });
    expect(enviar).toHaveBeenCalledTimes(1);
    expect((await armazem.listar()).map((p) => p.id_local)).toEqual(["a", "b"]);
  });

  it("erro do servidor (5xx) também para e mantém", async () => {
    const armazem = armazemEmMemoria();
    await armazem.guardar(pendente("a", "2026-10-21T10:00:00Z"));
    const r = await enviarPendentes(armazem, async () => resposta(502));
    expect(r.parou).toBe(true);
    expect(await armazem.listar()).toHaveLength(1);
  });
});

describe("enviarPendente", () => {
  it("check-in vai como JSON com o id_local", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(resposta(201));
    await enviarPendente(pendente("a", "2026-10-21T10:00:00Z"));
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/motorista/checkin");
    expect(JSON.parse(init!.body as string)).toEqual({
      caminhao_id: 1,
      acao: "INICIO_CARREGAMENTO",
      id_local: "a",
    });
    fetch.mockRestore();
  });

  it("ocorrência vai como formulário com a foto", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(resposta(201));
    const foto = new Blob(["png"], { type: "image/png" });
    await enviarPendente({
      id_local: "o1",
      tipo: "ocorrencia",
      criado_em: "2026-10-21T10:00:00Z",
      dados: { caminhao_id: 1, tipo: "PNEU", descricao: "Pneu furado" },
      foto,
    });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("/api/ocorrencias");
    const corpo = init!.body as FormData;
    expect(corpo.get("id_local")).toBe("o1");
    expect(corpo.get("tipo")).toBe("PNEU");
    expect(corpo.get("foto")).toBeInstanceOf(Blob);
    fetch.mockRestore();
  });
});
