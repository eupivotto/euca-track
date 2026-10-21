import { describe, expect, it } from "vitest";
import { esperadoAgora, fracao } from "./regua";

const INICIO = "2026-10-20T00:00:00-04:00";

describe("régua da meta", () => {
  it("esperado é proporcional ao horário do dia", () => {
    expect(esperadoAgora(4000, INICIO, "2026-10-20T12:00:00-04:00")).toBe(2000);
    expect(esperadoAgora(4000, INICIO, "2026-10-20T00:00:00-04:00")).toBe(0);
  });

  it("esperado não passa da meta nem fica negativo", () => {
    expect(esperadoAgora(4000, INICIO, "2026-10-21T03:00:00-04:00")).toBe(4000);
    expect(esperadoAgora(4000, INICIO, "2026-10-19T23:00:00-04:00")).toBe(0);
  });

  it("fração limitada entre 0 e 1", () => {
    expect(fracao(2380, 4000)).toBeCloseTo(0.595);
    expect(fracao(5000, 4000)).toBe(1);
    expect(fracao(10, 0)).toBe(0);
  });
});
