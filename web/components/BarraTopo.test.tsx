import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BarraTopo } from "./BarraTopo";

describe("BarraTopo", () => {
  it("mostra o selo da Fase 3: áreas do MapBiomas, frota simulada", () => {
    render(<BarraTopo ativa="/" />);
    const selo = screen.getByText("Áreas de eucalipto: MapBiomas (2024). Frota e viagens: dados simulados.");
    // Em tela estreita o selo quebra em duas linhas em vez de empurrar o menu.
    expect(selo).not.toHaveClass("whitespace-nowrap");
  });

  it("marca a tela ativa", () => {
    render(<BarraTopo ativa="/" />);
    expect(screen.getByRole("link", { name: "Ao vivo" })).toHaveAttribute("aria-current", "page");
  });

  it("mostra o nome do produto", () => {
    render(<BarraTopo ativa="/" />);
    expect(screen.getByText("Rota da Madeira")).toBeInTheDocument();
  });
});

describe("BarraTopo na Fase 3", () => {
  it("menu mostra as telas, com Risco antes de Replay, e marca a atual", () => {
    render(<BarraTopo ativa="/patio" />);
    const nomes = screen.getAllByRole("link").map((l) => l.textContent);
    expect(nomes).toEqual(["Ao vivo", "Pátio", "Indicadores", "Alertas", "Risco", "Replay"]);
    expect(screen.getByRole("link", { name: "Pátio" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Ao vivo" })).not.toHaveAttribute("aria-current");
  });
});
