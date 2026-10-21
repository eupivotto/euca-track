import { describe, expect, it } from "vitest";
import { posicaoNoTempo } from "./replay";

const t0 = Date.parse("2026-10-20T14:00:00Z");
const min = (m: number) => new Date(t0 + m * 60_000).toISOString();
const PONTOS = [
  { lon: -51.95, lat: -20.95, velocidade_kmh: 60, momento: min(0) },
  { lon: -51.76, lat: -20.62, velocidade_kmh: 60, momento: min(10) },
  { lon: -51.76, lat: -20.62, velocidade_kmh: 0, momento: min(20) },
];

describe("posicaoNoTempo", () => {
  it("interpola entre os dois pontos em volta do momento", () => {
    const p = posicaoNoTempo(PONTOS, t0 + 5 * 60_000);
    expect(p.lon).toBeCloseTo(-51.855);
    expect(p.lat).toBeCloseTo(-20.785);
    expect(p.indice).toBe(0);
  });

  it("antes do início fica no primeiro ponto", () => {
    expect(posicaoNoTempo(PONTOS, t0 - 60_000)).toEqual({ lon: -51.95, lat: -20.95, indice: 0 });
  });

  it("depois do fim fica no último ponto", () => {
    expect(posicaoNoTempo(PONTOS, t0 + 60 * 60_000)).toEqual({ lon: -51.76, lat: -20.62, indice: 2 });
  });

  it("exatamente num ponto, o índice é o dele", () => {
    expect(posicaoNoTempo(PONTOS, t0 + 10 * 60_000)).toMatchObject({ lon: -51.76, indice: 1 });
  });
});
