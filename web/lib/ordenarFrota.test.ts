import { describe, expect, it } from "vitest";
import { caminhao as c } from "./fabricas.test-util";
import { ordenarFrota } from "./ordenarFrota";

describe("ordenarFrota", () => {
  it("ordena carregados primeiro e desempata por placa", () => {
    const r = ordenarFrota([c("TLG2", "CARREGANDO"), c("TLG9", "EM_TRANSITO_CARREGADO"), c("TLG1", "EM_TRANSITO_CARREGADO")]);
    expect(r.map((x) => x.placa)).toEqual(["TLG1", "TLG9", "TLG2"]);
  });

  it("segue a ordem: carregado, pátio, carregando, vazio, sem estado", () => {
    const r = ordenarFrota([
      c("TLG6", null),
      c("TLG5", "EM_TRANSITO_VAZIO"),
      c("TLG4", "CARREGANDO"),
      c("TLG3", "DESCARGA"),
      c("TLG2", "FILA_PATIO"),
      c("TLG1", "EM_TRANSITO_CARREGADO"),
    ]);
    expect(r.map((x) => x.placa)).toEqual(["TLG1", "TLG2", "TLG3", "TLG4", "TLG5", "TLG6"]);
  });

  it("não altera a lista original", () => {
    const lista = [c("TLG2", "CARREGANDO"), c("TLG1", "EM_TRANSITO_CARREGADO")];
    ordenarFrota(lista);
    expect(lista[0].placa).toBe("TLG2");
  });
});
