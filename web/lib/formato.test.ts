import { describe, expect, it } from "vitest";
import { duracao, horaCurta } from "./formato";

describe("formato", () => {
  it("duração curta em minutos e longa em horas", () => {
    expect(duracao(38)).toBe("38 min");
    expect(duracao(59.6)).toBe("1h00");
    expect(duracao(252)).toBe("4h12");
    expect(duracao(null)).toBe("—");
  });

  it("hora curta no horário de Campo Grande", () => {
    expect(horaCurta("2026-10-20T18:30:00Z")).toBe("14h30");
  });
});
