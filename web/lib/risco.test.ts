import { describe, expect, it } from "vitest";
import { COR_CLASSE, ROTULO_CLASSE, TIPOS_FOGO, ehAlertaFogo, imagemTriangulo } from "./risco";

describe("risco", () => {
  it("cores e rótulos das cinco classes do layout", () => {
    expect(COR_CLASSE).toEqual({
      NULO: "#9CC5A1",
      PEQUENO: "#C9DE8E",
      MEDIO: "#F2D06B",
      ALTO: "#E8A33D",
      MUITO_ALTO: "#D9534F",
    });
    expect(Object.values(ROTULO_CLASSE)).toEqual(["Nulo", "Pequeno", "Médio", "Alto", "Muito alto"]);
  });

  it("alertas de fogo são os dois de foco", () => {
    expect(TIPOS_FOGO).toEqual(["FOCO_PROXIMO_FAZENDA", "FOCO_PROXIMO_ROTA"]);
    expect(ehAlertaFogo("FOCO_PROXIMO_ROTA")).toBe(true);
    expect(ehAlertaFogo("PARADA")).toBe(false);
  });

  it("triângulo do foco: vermelho no miolo, branco na borda, transparente fora", () => {
    const img = imagemTriangulo(16);
    expect([img.width, img.height, img.data.length]).toEqual([16, 16, 16 * 16 * 4]);
    const pixel = (x: number, y: number) => Array.from(img.data.slice((y * 16 + x) * 4, (y * 16 + x) * 4 + 4));
    expect(pixel(8, 11)).toEqual([0xc8, 0x10, 0x2e, 255]);
    expect(pixel(0, 0)[3]).toBe(0);
    expect(pixel(8, 15)).toEqual([255, 255, 255, 255]);
  });
});
