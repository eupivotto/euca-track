import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReguaMeta } from "./ReguaMeta";

const DIA = {
  inicio: "2026-10-20T00:00:00-04:00",
  fim: "2026-10-21T00:00:00-04:00",
  agora: "2026-10-20T14:30:00-04:00",
  viagens: 46,
  meta_t: 4000,
};

describe("ReguaMeta", () => {
  it("mostra entregue, meta e diferença contra o esperado", () => {
    render(<ReguaMeta indicadores={{ ...DIA, toneladas: 2380 }} />);
    expect(screen.getByText("2.380 t")).toBeInTheDocument();
    expect(screen.getByText("entregues de 4.000 t")).toBeInTheDocument();
    expect(screen.getByText("−37 t")).toBeInTheDocument(); // 2380 − 2416,7
    expect(screen.getByText("contra o esperado às 14h30")).toBeInTheDocument();
  });

  it("diferença positiva leva sinal de mais", () => {
    render(<ReguaMeta indicadores={{ ...DIA, toneladas: 2500 }} />);
    expect(screen.getByText("+83 t")).toBeInTheDocument();
  });

  it("barra acessível com o progresso", () => {
    render(<ReguaMeta indicadores={{ ...DIA, toneladas: 2380 }} />);
    const barra = screen.getByRole("progressbar", { name: "Toneladas entregues no dia" });
    expect(barra).toHaveAttribute("aria-valuenow", "2380");
    expect(barra).toHaveAttribute("aria-valuemax", "4000");
  });

  it("ciclo médio e espera ficam para a Fase 2", () => {
    render(<ReguaMeta indicadores={{ ...DIA, toneladas: 0 }} />);
    expect(screen.getAllByText("—")).toHaveLength(2);
  });
});
