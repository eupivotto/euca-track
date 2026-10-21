import type { PontoViagem } from "./tipos";

/**
 * Onde o caminhão estava em `momento` (ms): interpola entre as duas leituras em volta.
 * `indice` é a última leitura já passada, para cortar o trajeto percorrido.
 */
export function posicaoNoTempo(
  pontos: PontoViagem[],
  momento: number,
): { lon: number; lat: number; indice: number } {
  const tempos = pontos.map((p) => Date.parse(p.momento));
  if (momento <= tempos[0]) return { lon: pontos[0].lon, lat: pontos[0].lat, indice: 0 };
  const ultimo = pontos.length - 1;
  if (momento >= tempos[ultimo]) return { lon: pontos[ultimo].lon, lat: pontos[ultimo].lat, indice: ultimo };

  let i = 0;
  while (tempos[i + 1] <= momento) i++;
  const [a, b] = [pontos[i], pontos[i + 1]];
  const t = (momento - tempos[i]) / (tempos[i + 1] - tempos[i]);
  return { lon: a.lon + (b.lon - a.lon) * t, lat: a.lat + (b.lat - a.lat) * t, indice: i };
}
