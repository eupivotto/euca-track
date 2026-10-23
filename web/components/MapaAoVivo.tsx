"use client";

import maplibregl, { type GeoJSONSource, type Map as MapaLibre } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { MARCADOR_ESTADO } from "@/lib/estados";
import { ATRIBUICAO_MAPBIOMAS, fonteGeo, limitesDe } from "@/lib/mapa";
import { CLASSES, COR_CLASSE, COR_FOCO, ROTULO_CLASSE, imagemTriangulo } from "@/lib/risco";
import type { Caminhao, ClasseRisco, ColecaoGeo } from "@/lib/tipos";

const ESTILO = "https://tiles.openfreemap.org/styles/positron";
const CENTRO: [number, number] = [-52.1, -20.72];

// Cores dos tokens (o MapLibre não lê variáveis CSS).
const COR = { linha: "#e4e7eb", rota: "#a9b7c0", tinta: "#101418", contornoFazenda: "#c4cbd2" };

// Preenchimento pela classe de risco do dia; sem cálculo ainda, cinza neutro.
const PREENCHIMENTO_RISCO = [
  "match",
  ["get", "classe"],
  ...CLASSES.flatMap((c) => [c, COR_CLASSE[c]]),
  COR.linha,
] as unknown as string;

const escapar = (texto: string) =>
  texto.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

function textoArea(propriedades: Record<string, unknown>) {
  const nome = escapar(String(propriedades.nome ?? ""));
  const classe = propriedades.classe as ClasseRisco | null | undefined;
  const fma = typeof propriedades.fma === "number" ? propriedades.fma.toFixed(1).replace(".", ",") : null;
  const risco = classe && fma ? `FMA ${fma}, risco ${ROTULO_CLASSE[classe].toLowerCase()}` : "Risco ainda não calculado";
  return `<strong>${nome}</strong><br>${risco}`;
}

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
  focos,
  caminhoes,
  selecionadoId,
  onSelecionar,
  fazendaFoco = null,
}: {
  fazendas: ColecaoGeo | undefined;
  rotas: ColecaoGeo | undefined;
  focos?: ColecaoGeo;
  caminhoes: Caminhao[];
  // Vindo de "Ver no mapa" de um alerta de área: enquadra só ela na primeira carga.
  fazendaFoco?: number | null;
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
      m.addSource("fazendas", fonteGeo(vazio, ATRIBUICAO_MAPBIOMAS));
      m.addSource("rotas", { type: "geojson", data: vazio });
      m.addSource("caminhoes", { type: "geojson", data: vazio });
      m.addSource("focos", { type: "geojson", data: vazio, attribution: "Focos de calor: INPE" });
      if (!m.hasImage("foco")) m.addImage("foco", imagemTriangulo(28), { pixelRatio: 2 });

      m.addLayer({
        id: "fazendas",
        type: "fill",
        source: "fazendas",
        filter: ["==", ["get", "tipo"], "fazenda"],
        paint: { "fill-color": PREENCHIMENTO_RISCO, "fill-opacity": 0.85 },
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
        id: "focos",
        type: "symbol",
        source: "focos",
        layout: { "icon-image": "foco", "icon-allow-overlap": true },
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
      m.on("click", "fazendas", (e) => {
        const propriedades = e.features?.[0]?.properties;
        if (propriedades) new maplibregl.Popup().setLngLat(e.lngLat).setHTML(textoArea(propriedades)).addTo(m);
      });
      for (const camada of ["caminhoes", "fazendas"]) {
        m.on("mouseenter", camada, () => (m.getCanvas().style.cursor = "pointer"));
        m.on("mouseleave", camada, () => (m.getCanvas().style.cursor = ""));
      }
      pronto.current = true;
      m.fire("dados-prontos");
    });
    mapa.current = m;
    return () => {
      pronto.current = false;
      m.remove();
    };
  }, []);

  // Uma fonte por efeito: a frota muda a cada 3 s, fazendas e rotas quase nunca.
  const quandoPronto = (aplicar: (m: MapaLibre) => void) => {
    const m = mapa.current;
    if (!m) return;
    if (pronto.current) aplicar(m);
    else m.once("dados-prontos", () => aplicar(m));
  };

  // As áreas vão até 150 km da fábrica: na primeira carga, enquadra todas.
  const enquadrado = useRef(false);
  useEffect(() => {
    if (!fazendas) return;
    quandoPronto((m) => {
      (m.getSource("fazendas") as GeoJSONSource).setData(fazendas as never);
      if (enquadrado.current) return;
      const alvo = fazendas.features.filter((f) => f.properties.tipo === "fazenda" && f.properties.id === fazendaFoco);
      const limites = limitesDe(alvo.length ? { ...fazendas, features: alvo } : fazendas);
      if (limites) {
        enquadrado.current = true;
        m.fitBounds(limites, { padding: 32, duration: 0 });
      }
    });
    // fazendaFoco só vale na primeira carga.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fazendas]);

  useEffect(() => {
    if (focos) quandoPronto((m) => (m.getSource("focos") as GeoJSONSource).setData(focos as never));
  }, [focos]);

  useEffect(() => {
    if (rotas) quandoPronto((m) => (m.getSource("rotas") as GeoJSONSource).setData(rotas as never));
  }, [rotas]);

  useEffect(() => {
    quandoPronto((m) =>
      (m.getSource("caminhoes") as GeoJSONSource).setData(caminhoesGeo(caminhoes, selecionadoId)),
    );
  }, [caminhoes, selecionadoId]);

  return (
    <div className="relative h-full min-h-[360px] bg-trilho">
      {/* O CSS do MapLibre fixa position: relative em .maplibregl-map, então o tamanho vem de h-full. */}
      <div ref={container} className="h-full w-full" aria-label="Mapa da frota" role="region" />
      <Legenda />
    </div>
  );
}

function Legenda() {
  const frota = [
    { rotulo: "Carregado", estilo: { background: MARCADOR_ESTADO.EM_TRANSITO_CARREGADO.cor } },
    { rotulo: "Vazio", estilo: { boxShadow: `inset 0 0 0 1.5px ${MARCADOR_ESTADO.EM_TRANSITO_VAZIO.cor}` } },
    { rotulo: "Carregando", estilo: { background: MARCADOR_ESTADO.CARREGANDO.cor } },
    { rotulo: "No pátio", estilo: { background: MARCADOR_ESTADO.FILA_PATIO.cor } },
    { rotulo: "Fábrica", estilo: { background: COR.tinta } },
  ];
  // No celular a atribuição ocupa duas linhas: a legenda sobe para não ficar embaixo dela.
  return (
    <div className="absolute right-3 bottom-12 left-3 flex flex-col gap-1.5 rounded-lg border border-linha bg-superficie px-2.5 py-2 text-[11.5px] sm:right-auto sm:bottom-3">
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {frota.map((i) => (
          <span key={i.rotulo} className="inline-flex items-center gap-1.5">
            <i aria-hidden className="inline-block size-2 rounded-full" style={i.estilo} />
            {i.rotulo}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-tinta-suave">Risco de incêndio</span>
        {CLASSES.map((c) => (
          <span key={c} className="inline-flex items-center gap-1.5">
            <i aria-hidden className="inline-block h-2 w-3 rounded-[2px]" style={{ background: COR_CLASSE[c] }} />
            {ROTULO_CLASSE[c]}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <svg aria-hidden width="10" height="9" viewBox="0 0 10 9">
            <path d="M5 0.8 L9.3 8.3 L0.7 8.3 Z" fill={COR_FOCO} stroke="#ffffff" strokeWidth="1" />
          </svg>
          Foco de calor
        </span>
      </div>
    </div>
  );
}
