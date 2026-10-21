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
