import { describe, expect, it } from "vitest";
import { MARCADOR_ESTADO, ROTULO_ESTADO } from "./estados";

describe("estados do caminhão", () => {
  it("rótulos em português de quem usa", () => {
    expect(ROTULO_ESTADO.CARREGANDO).toBe("Carregando");
    expect(ROTULO_ESTADO.EM_TRANSITO_CARREGADO).toBe("Carregado");
    expect(ROTULO_ESTADO.FILA_PATIO).toBe("Fila do pátio");
    expect(ROTULO_ESTADO.PESAGEM).toBe("Pesagem");
    expect(ROTULO_ESTADO.DESCARGA).toBe("Descarga");
    expect(ROTULO_ESTADO.EM_TRANSITO_VAZIO).toBe("Vazio");
  });

  it("vazio se distingue por contorno, não só por cor", () => {
    expect(MARCADOR_ESTADO.EM_TRANSITO_VAZIO).toEqual({ cor: "#0f5c73", contorno: true });
    expect(MARCADOR_ESTADO.EM_TRANSITO_CARREGADO).toEqual({ cor: "#0f5c73", contorno: false });
  });

  it("estados de pátio compartilham a cor", () => {
    const cores = new Set(["FILA_PATIO", "PESAGEM", "DESCARGA"].map((e) => MARCADOR_ESTADO[e as "PESAGEM"].cor));
    expect(cores).toEqual(new Set(["#5a7d8c"]));
  });
});
