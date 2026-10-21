"use client";

import maplibregl, { type GeoJSONSource, type Map as MapaLibre } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { posicaoNoTempo } from "@/lib/replay";
import type { ViagemDetalhe } from "@/lib/tipos";

const ESTILO = "https://tiles.openfreemap.org/styles/positron";
// Cores dos tokens (o MapLibre não lê variáveis CSS).
const COR = { rota: "#a9b7c0", primaria: "#0f5c73" };

function linha(coords: [number, number][]) {
  return { type: "Feature" as const, properties: {}, geometry: { type: "LineString" as const, coordinates: coords } };
}

/** Rota prevista tracejada, trajeto percorrido até o cursor e o caminhão no ponto do cursor. */
export function MapaReplay({ viagem, cursor }: { viagem: ViagemDetalhe; cursor: number }) {
  const container = useRef<HTMLDivElement>(null);
  const mapa = useRef<MapaLibre | null>(null);
  const pronto = useRef(false);
  const cursorAtual = useRef(cursor);
  cursorAtual.current = cursor;

  const desenharCursor = (m: MapaLibre, momento: number) => {
    if (viagem.pontos.length === 0) return;
    const { lon, lat, indice } = posicaoNoTempo(viagem.pontos, momento);
    const percorrido = viagem.pontos.slice(0, indice + 1).map((p) => [p.lon, p.lat] as [number, number]);
    (m.getSource("percorrido") as GeoJSONSource).setData(linha([...percorrido, [lon, lat]]));
    (m.getSource("caminhao") as GeoJSONSource).setData({
      type: "Feature",
      properties: {},
      geometry: { type: "Point", coordinates: [lon, lat] },
    });
  };

  useEffect(() => {
    const coords = [
      ...(viagem.rota?.coordinates ?? []),
      ...viagem.pontos.map((p) => [p.lon, p.lat] as [number, number]),
    ];
    const limites = coords.reduce(
      (b, c) => b.extend(c),
      new maplibregl.LngLatBounds(coords[0] ?? [-51.76, -20.62], coords[0] ?? [-51.76, -20.62]),
    );
    const m = new maplibregl.Map({
      container: container.current!,
      style: ESTILO,
      bounds: limites,
      fitBoundsOptions: { padding: 48 },
      attributionControl: { compact: false },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      // O contêiner pode ganhar altura depois de criado o mapa: enquadra de novo com o tamanho final.
      m.resize();
      m.fitBounds(limites, { padding: 48, duration: 0 });
      const vazio = { type: "FeatureCollection" as const, features: [] };
      m.addSource("rota", { type: "geojson", data: viagem.rota ? linha(viagem.rota.coordinates) : vazio });
      m.addSource("percorrido", { type: "geojson", data: vazio });
      m.addSource("caminhao", { type: "geojson", data: vazio });
      m.addLayer({
        id: "rota",
        type: "line",
        source: "rota",
        paint: { "line-color": COR.rota, "line-width": 2, "line-dasharray": [2, 2] },
      });
      m.addLayer({
        id: "percorrido",
        type: "line",
        source: "percorrido",
        paint: { "line-color": COR.primaria, "line-width": 2.5 },
      });
      m.addLayer({
        id: "caminhao",
        type: "circle",
        source: "caminhao",
        paint: {
          "circle-radius": 7,
          "circle-color": COR.primaria,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
        },
      });
      pronto.current = true;
      desenharCursor(m, cursorAtual.current);
    });
    mapa.current = m;
    return () => {
      pronto.current = false;
      m.remove();
    };
    // O mapa é refeito só quando muda a viagem; o cursor tem efeito próprio.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viagem]);

  useEffect(() => {
    if (mapa.current && pronto.current) desenharCursor(mapa.current, cursor);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cursor]);

  return <div ref={container} className="h-full min-h-[360px] w-full bg-trilho" aria-label="Mapa da viagem" role="region" />;
}
