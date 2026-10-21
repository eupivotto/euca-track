import { act, render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { caminhao } from "@/lib/fabricas.test-util";
import type { ColecaoGeo } from "@/lib/tipos";

// MapLibre falso: guarda um setData espiado por fonte e dispara o "load" na mão.
const fontes: Record<string, { setData: ReturnType<typeof vi.fn> }> = {};
let aoCarregar: (() => void) | undefined;
let pendentes: Record<string, (() => void)[]> = {};

vi.mock("maplibre-gl", () => {
  class MapaFalso {
    on(evento: string, ...args: unknown[]) {
      if (evento === "load") aoCarregar = args[0] as () => void;
    }
    once(evento: string, fn: () => void) {
      (pendentes[evento] ??= []).push(fn);
    }
    fire(evento: string) {
      const fns = pendentes[evento] ?? [];
      pendentes[evento] = [];
      fns.forEach((fn) => fn());
    }
    addControl() {}
    addLayer() {}
    addSource(id: string) {
      fontes[id] = { setData: vi.fn() };
    }
    getSource(id: string) {
      return fontes[id];
    }
    getCanvas() {
      return { style: {} };
    }
    remove() {}
  }
  return { default: { Map: MapaFalso, NavigationControl: class {} } };
});

import { MapaAoVivo } from "./MapaAoVivo";

const vazia: ColecaoGeo = { type: "FeatureCollection", features: [] };

describe("MapaAoVivo", () => {
  beforeEach(() => {
    for (const id of Object.keys(fontes)) delete fontes[id];
    pendentes = {};
  });

  it("atualizar caminhões não reenvia fazendas nem rotas", () => {
    const props = { fazendas: vazia, rotas: vazia, selecionadoId: null, onSelecionar: () => {} };
    const { rerender } = render(<MapaAoVivo {...props} caminhoes={[]} />);
    act(() => aoCarregar?.());
    rerender(<MapaAoVivo {...props} caminhoes={[caminhao("TLG1A23", "CARREGANDO", 0, { id: 1 })]} />);
    rerender(<MapaAoVivo {...props} caminhoes={[caminhao("TLG1A23", "FILA_PATIO", 55, { id: 1 })]} />);
    // Uma vez quando o mapa carrega; depois só os caminhões mudam.
    expect(fontes.fazendas.setData).toHaveBeenCalledTimes(1);
    expect(fontes.rotas.setData).toHaveBeenCalledTimes(1);
    expect(fontes.caminhoes.setData).toHaveBeenCalledTimes(3);
  });
});
