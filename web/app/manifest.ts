import type { MetadataRoute } from "next";

// Só o app do motorista é instalável; o painel continua uma página comum.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Rota da Madeira — Motorista",
    short_name: "Motorista",
    description: "Viagem, check-in de carregamento e ocorrências do motorista (dados simulados).",
    lang: "pt-BR",
    start_url: "/motorista",
    scope: "/motorista",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#0f5c73",
    icons: [
      { src: "/icone-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icone-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icone.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
