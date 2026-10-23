import type { ClasseRisco, TipoAlerta } from "./tipos";

// Cores das classes do layout: preenchimento de áreas e células, nunca texto.
export const COR_CLASSE: Record<ClasseRisco, string> = {
  NULO: "#9CC5A1",
  PEQUENO: "#C9DE8E",
  MEDIO: "#F2D06B",
  ALTO: "#E8A33D",
  MUITO_ALTO: "#D9534F",
};

export const ROTULO_CLASSE: Record<ClasseRisco, string> = {
  NULO: "Nulo",
  PEQUENO: "Pequeno",
  MEDIO: "Médio",
  ALTO: "Alto",
  MUITO_ALTO: "Muito alto",
};

export const CLASSES = Object.keys(COR_CLASSE) as ClasseRisco[];

export const COR_FOCO = "#C8102E";
export const COR_CHUVA = "#1D4E89";

export const TIPOS_FOGO: TipoAlerta[] = ["FOCO_PROXIMO_FAZENDA", "FOCO_PROXIMO_ROTA"];

export const ehAlertaFogo = (tipo: TipoAlerta) => TIPOS_FOGO.includes(tipo);

/** Ícone do foco para o MapLibre: triângulo vermelho com contorno branco, em RGBA. */
export function imagemTriangulo(tamanho: number, borda = 1.5) {
  const data = new Uint8Array(tamanho * tamanho * 4);
  const vertices: [number, number][] = [
    [tamanho / 2, 0],
    [tamanho, tamanho],
    [0, tamanho],
  ];
  // Distância com sinal do ponto à aresta a→b; positiva do lado de dentro (sentido horário na tela).
  const aresta = ([ax, ay]: [number, number], [bx, by]: [number, number], x: number, y: number) =>
    ((bx - ax) * (y - ay) - (by - ay) * (x - ax)) / Math.hypot(bx - ax, by - ay);
  for (let y = 0; y < tamanho; y++) {
    for (let x = 0; x < tamanho; x++) {
      const px = x + 0.5;
      const py = y + 0.5;
      const d = Math.min(...vertices.map((v, i) => aresta(v, vertices[(i + 1) % 3], px, py)));
      if (d < 0) continue;
      const [r, g, b] = d < borda ? [255, 255, 255] : [0xc8, 0x10, 0x2e];
      data.set([r, g, b, 255], (y * tamanho + x) * 4);
    }
  }
  return { width: tamanho, height: tamanho, data };
}
