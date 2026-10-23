import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { HistoricoRisco } from "@/lib/tipos";
import { GradeRisco } from "./GradeRisco";

const HISTORICO: HistoricoRisco = {
  datas: ["2026-10-20", "2026-10-21", "2026-10-22"],
  fazendas: [
    {
      fazenda_id: 1,
      nome: "Área de eucalipto 01",
      dias: [
        { data: "2026-10-20", fma: 1.0, classe: "NULO", chuva_mm: 0, ur_13h: 60 },
        { data: "2026-10-21", fma: 4.2, classe: "MEDIO", chuva_mm: 3.0, ur_13h: 48 },
        { data: "2026-10-22", fma: 6.3, classe: "MEDIO", chuva_mm: 2.4, ur_13h: 39 },
      ],
    },
    {
      fazenda_id: 2,
      nome: "Área de eucalipto 02",
      dias: [null, { data: "2026-10-21", fma: 21.4, classe: "MUITO_ALTO", chuva_mm: null, ur_13h: null }, null],
    },
  ],
};

describe("GradeRisco", () => {
  it("uma célula por área e dia, com o rótulo completo", () => {
    render(<GradeRisco historico={HISTORICO} />);
    expect(screen.getAllByTestId("celula-risco")).toHaveLength(6);
    expect(screen.getByLabelText("21/10: FMA 4,2, Médio, chuva 3,0 mm, UR 13h 48%")).toBeInTheDocument();
  });

  it("ponto de chuva só onde choveu mais de 2,4 mm", () => {
    render(<GradeRisco historico={HISTORICO} />);
    const chuvas = screen.getAllByTestId("ponto-chuva");
    expect(chuvas).toHaveLength(1);
    expect(chuvas[0].closest("[data-testid=celula-risco]")).toHaveAttribute(
      "aria-label",
      "21/10: FMA 4,2, Médio, chuva 3,0 mm, UR 13h 48%",
    );
  });

  it("dia sem cálculo aparece como sem dado", () => {
    render(<GradeRisco historico={HISTORICO} />);
    expect(screen.getAllByLabelText("20/10: sem dado")).toHaveLength(1);
    expect(screen.getAllByLabelText("22/10: sem dado")).toHaveLength(1);
  });

  it("dia sem chuva ou UR informadas não inventa valores", () => {
    render(<GradeRisco historico={HISTORICO} />);
    expect(screen.getByLabelText("21/10: FMA 21,4, Muito alto")).toBeInTheDocument();
  });

  it("última coluna traz a FMA de hoje", () => {
    render(<GradeRisco historico={HISTORICO} />);
    const [primeira, segunda] = screen.getAllByRole("row").slice(1);
    expect(within(primeira).getByTestId("fma-hoje")).toHaveTextContent("6,3");
    expect(within(segunda).getByTestId("fma-hoje")).toHaveTextContent("—");
  });

  it("foco na célula mostra o detalhe do dia", () => {
    render(<GradeRisco historico={HISTORICO} />);
    fireEvent.focus(screen.getByLabelText("21/10: FMA 4,2, Médio, chuva 3,0 mm, UR 13h 48%"));
    expect(screen.getByRole("status")).toHaveTextContent(
      "Área de eucalipto 01 · 21/10: FMA 4,2, Médio, chuva 3,0 mm, UR 13h 48%",
    );
  });

  it("legenda das classes e do ponto de chuva", () => {
    render(<GradeRisco historico={HISTORICO} />);
    for (const rotulo of ["Nulo", "Pequeno", "Médio", "Alto", "Muito alto", "Chuva acima de 2,4 mm"]) {
      expect(screen.getByText(rotulo)).toBeInTheDocument();
    }
  });
});
