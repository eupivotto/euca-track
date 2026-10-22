// @vitest-environment node
// No jsdom o Blob não sobrevive ao structuredClone do IndexedDB; no node (e no navegador) sim.
import "fake-indexeddb/auto";
import { describe, expect, it } from "vitest";
import { armazemIndexedDb } from "./armazemIndexedDb";

describe("armazemIndexedDb", () => {
  it("guarda, lista em ordem de criação e remove, inclusive a foto", async () => {
    const armazem = armazemIndexedDb("teste-armazem");
    const foto = new Blob(["png"], { type: "image/png" });
    await armazem.guardar({ id_local: "b", tipo: "ocorrencia", criado_em: "2026-10-21T10:01:00Z", dados: { caminhao_id: 1 }, foto });
    await armazem.guardar({ id_local: "a", tipo: "checkin", criado_em: "2026-10-21T10:00:00Z", dados: { caminhao_id: 1 } });
    const lista = await armazem.listar();
    expect(lista.map((p) => p.id_local)).toEqual(["a", "b"]);
    expect(lista[1].foto).toBeInstanceOf(Blob);
    await armazem.remover("a");
    expect((await armazem.listar()).map((p) => p.id_local)).toEqual(["b"]);
  });
});
