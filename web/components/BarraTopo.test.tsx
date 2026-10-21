import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BarraTopo } from "./BarraTopo";

describe("BarraTopo", () => {
  it("mostra o selo de dados simulados", () => {
    render(<BarraTopo ativa="/" />);
    expect(screen.getByText("Dados simulados")).toBeInTheDocument();
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

describe("BarraTopo na Fase 2", () => {
  it("menu mostra as telas da fase 2 e marca a atual", () => {
    render(<BarraTopo ativa="/patio" />);
    const nomes = screen.getAllByRole("link").map((l) => l.textContent);
    expect(nomes).toEqual(["Ao vivo", "Pátio", "Indicadores", "Alertas", "Replay"]);
    expect(screen.getByRole("link", { name: "Pátio" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Ao vivo" })).not.toHaveAttribute("aria-current");
  });
});
