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

describe("ordenarFrota na Fase 2", () => {
  it("alerta primeiro, depois em trânsito por ETA, depois o resto", () => {
    const lista = ordenarFrota([
      c("TLG1A04", "FILA_PATIO", 55),
      c("TLG1A01", "EM_TRANSITO_CARREGADO", 55, { eta: "2026-10-20T15:00:00-04:00" }),
      c("TLG1A02", "EM_TRANSITO_VAZIO", 0, { eta: "2026-10-20T14:00:00-04:00" }),
      c("TLG1A03", "CARREGANDO", 0, { alertas_abertos: ["PARADA"] }),
    ]);
    expect(lista.map((x) => x.placa)).toEqual(["TLG1A03", "TLG1A02", "TLG1A01", "TLG1A04"]);
  });
});
