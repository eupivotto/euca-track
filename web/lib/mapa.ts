import type { ColecaoGeo } from "./tipos";

// Licença CC-BY-4.0 do MapBiomas: a atribuição aparece em todo mapa que mostra as áreas ou rotas saídas delas.
export const ATRIBUICAO_MAPBIOMAS = "Áreas de eucalipto © MapBiomas (CC-BY-4.0)";

export function fonteGeo<T>(data: T, attribution?: string) {
  return { type: "geojson" as const, data, ...(attribution ? { attribution } : {}) };
}

/** Canto sudoeste e nordeste de tudo na coleção; null se vazia. */
export function limitesDe(colecao: ColecaoGeo): [[number, number], [number, number]] | null {
  let oeste = Infinity;
  let sul = Infinity;
  let leste = -Infinity;
  let norte = -Infinity;
  const visitar = (c: unknown): void => {
    if (!Array.isArray(c)) return;
    if (typeof c[0] === "number") {
      const [lon, lat] = c as [number, number];
      oeste = Math.min(oeste, lon);
      leste = Math.max(leste, lon);
      sul = Math.min(sul, lat);
      norte = Math.max(norte, lat);
      return;
    }
    c.forEach(visitar);
  };
  colecao.features.forEach((f) => visitar(f.geometry.coordinates));
  return oeste === Infinity ? null : [
    [oeste, sul],
    [leste, norte],
  ];
}
