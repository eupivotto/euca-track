"use client";

import maplibregl, { type GeoJSONSource, type Map as MapaLibre } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { MARCADOR_ESTADO } from "@/lib/estados";
import type { Caminhao, ColecaoGeo } from "@/lib/tipos";

const ESTILO = "https://tiles.openfreemap.org/styles/positron";
const CENTRO: [number, number] = [-52.1, -20.72];

// Cores dos tokens (o MapLibre não lê variáveis CSS).
const COR = { linha: "#e4e7eb", rota: "#a9b7c0", tinta: "#101418", contornoFazenda: "#c4cbd2" };

function caminhoesGeo(caminhoes: Caminhao[], selecionadoId: number | null) {
  return {
    type: "FeatureCollection" as const,
    features: caminhoes
      .filter((c) => c.posicao && c.estado_atual)
      .map((c) => {
        const { cor, contorno } = MARCADOR_ESTADO[c.estado_atual!];
        return {
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [c.posicao!.lon, c.posicao!.lat] },
          properties: { id: c.id, cor, contorno, selecionado: c.id === selecionadoId },
        };
      }),
  };
}

export function MapaAoVivo({
  fazendas,
  rotas,
  caminhoes,
  selecionadoId,
  onSelecionar,
}: {
  fazendas: ColecaoGeo | undefined;
  rotas: ColecaoGeo | undefined;
  caminhoes: Caminhao[];
  selecionadoId: number | null;
  onSelecionar: (id: number) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapa = useRef<MapaLibre | null>(null);
  const pronto = useRef(false);
  const aoSelecionar = useRef(onSelecionar);
  aoSelecionar.current = onSelecionar;

  useEffect(() => {
    const m = new maplibregl.Map({
      container: container.current!,
      style: ESTILO,
      center: CENTRO,
      zoom: 8,
      attributionControl: { compact: false },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      const vazio = { type: "FeatureCollection" as const, features: [] };
      m.addSource("fazendas", { type: "geojson", data: vazio });
      m.addSource("rotas", { type: "geojson", data: vazio });
      m.addSource("caminhoes", { type: "geojson", data: vazio });

      // Fases 1–2: fazendas em cinza neutro; a cor de risco chega na Fase 3.
      m.addLayer({
        id: "fazendas",
        type: "fill",
        source: "fazendas",
        filter: ["==", ["get", "tipo"], "fazenda"],
        paint: { "fill-color": COR.linha, "fill-opacity": 0.9 },
      });
      m.addLayer({
        id: "fazendas-borda",
        type: "line",
        source: "fazendas",
        filter: ["==", ["get", "tipo"], "fazenda"],
        paint: { "line-color": COR.contornoFazenda, "line-width": 1 },
      });
      m.addLayer({
        id: "rotas",
        type: "line",
        source: "rotas",
        paint: { "line-color": COR.rota, "line-width": 1.4 },
      });
      m.addLayer({
        id: "fabrica",
        type: "circle",
        source: "fazendas",
        filter: ["==", ["get", "tipo"], "fabrica"],
        paint: {
          "circle-radius": 6,
          "circle-color": COR.tinta,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5,
        },
      });
      m.addLayer({
        id: "caminhoes",
        type: "circle",
        source: "caminhoes",
        paint: {
          "circle-radius": ["case", ["get", "selecionado"], 7, 4.5],
          "circle-color": ["case", ["get", "contorno"], "#ffffff", ["get", "cor"]],
          "circle-stroke-color": ["case", ["get", "contorno"], ["get", "cor"], "#ffffff"],
          "circle-stroke-width": ["case", ["get", "contorno"], 1.8, 1.2],
        },
      });
      m.on("click", "caminhoes", (e) => {
        const id = e.features?.[0]?.properties?.id;
        if (typeof id === "number") aoSelecionar.current(id);
      });
      m.on("mouseenter", "caminhoes", () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", "caminhoes", () => (m.getCanvas().style.cursor = ""));
      pronto.current = true;
      m.fire("dados-prontos");
    });
    mapa.current = m;
    return () => {
      pronto.current = false;
      m.remove();
    };
  }, []);

  // Cada fonte é atualizada quando seus dados mudam, depois do mapa carregar.
  useEffect(() => {
    const m = mapa.current;
    if (!m) return;
    const aplicar = () => {
      if (fazendas) (m.getSource("fazendas") as GeoJSONSource).setData(fazendas as never);
      if (rotas) (m.getSource("rotas") as GeoJSONSource).setData(rotas as never);
      (m.getSource("caminhoes") as GeoJSONSource).setData(caminhoesGeo(caminhoes, selecionadoId));
    };
    if (pronto.current) aplicar();
    else m.once("dados-prontos", aplicar);
  }, [fazendas, rotas, caminhoes, selecionadoId]);

  return (
    <div className="relative h-full min-h-[360px] bg-trilho">
      {/* O CSS do MapLibre fixa position: relative em .maplibregl-map, então o tamanho vem de h-full. */}
      <div ref={container} className="h-full w-full" aria-label="Mapa da frota" role="region" />
      <Legenda />
    </div>
  );
}

function Legenda() {
  const itens = [
    { rotulo: "Carregado", estilo: { background: MARCADOR_ESTADO.EM_TRANSITO_CARREGADO.cor } },
    { rotulo: "Vazio", estilo: { boxShadow: `inset 0 0 0 1.5px ${MARCADOR_ESTADO.EM_TRANSITO_VAZIO.cor}` } },
    { rotulo: "Carregando", estilo: { background: MARCADOR_ESTADO.CARREGANDO.cor } },
    { rotulo: "No pátio", estilo: { background: MARCADOR_ESTADO.FILA_PATIO.cor } },
    { rotulo: "Fábrica", estilo: { background: COR.tinta } },
  ];
  return (
    <div className="absolute bottom-3 left-3 flex flex-wrap gap-3 rounded-lg border border-linha bg-superficie px-2.5 py-2 text-[11.5px]">
      {itens.map((i) => (
        <span key={i.rotulo} className="inline-flex items-center gap-1.5">
          <i aria-hidden className="inline-block size-2 rounded-full" style={i.estilo} />
          {i.rotulo}
        </span>
      ))}
    </div>
  );
}
