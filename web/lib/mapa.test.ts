import { describe, expect, it } from "vitest";
import { ATRIBUICAO_MAPBIOMAS, fonteGeo, limitesDe } from "./mapa";
import type { ColecaoGeo } from "./tipos";

const colecao = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { tipo: "fazenda" },
      geometry: { type: "Polygon", coordinates: [[[-52.5, -21.0], [-52.0, -21.0], [-52.0, -20.5], [-52.5, -21.0]]] },
    },
    { type: "Feature", properties: { tipo: "fabrica" }, geometry: { type: "Point", coordinates: [-51.76, -20.62] } },
  ],
} as unknown as ColecaoGeo;

describe("mapa", () => {
  it("fonte das áreas leva a atribuição do MapBiomas", () => {
    const fonte = fonteGeo(colecao, ATRIBUICAO_MAPBIOMAS);
    expect(fonte).toEqual({ type: "geojson", data: colecao, attribution: ATRIBUICAO_MAPBIOMAS });
    expect(ATRIBUICAO_MAPBIOMAS).toContain("MapBiomas");
  });

  it("limites cobrem polígonos e pontos", () => {
    expect(limitesDe(colecao)).toEqual([
      [-52.5, -21.0],
      [-51.76, -20.5],
    ]);
  });

  it("coleção vazia não tem limites", () => {
    expect(limitesDe({ type: "FeatureCollection", features: [] } as unknown as ColecaoGeo)).toBeNull();
  });
});
