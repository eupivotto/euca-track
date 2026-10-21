import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChegadasPrevistas } from "./ChegadasPrevistas";
import { FilaPatio } from "./FilaPatio";

const AGORA = "2026-10-20T18:00:00Z"; // 14h00 em Campo Grande

describe("FilaPatio", () => {
  it("fila em ordem com hora de chegada e tempo de espera", () => {
    render(
      <FilaPatio
        fila={[
          { caminhao_id: 1, placa: "TLG1A23", posicao: 1, chegou_em: "2026-10-20T17:48:00Z", esperando_min: 12 },
          { caminhao_id: 2, placa: "TLG2B11", posicao: 2, chegou_em: "2026-10-20T17:57:00Z", esperando_min: 3 },
        ]}
      />,
    );
    const linhas = screen.getAllByRole("row").slice(1);
    expect(linhas[0]).toHaveTextContent(/^1TLG1A2313h4812 min$/);
    expect(linhas[1]).toHaveTextContent("TLG2B11");
  });

  it("fila vazia diz isso", () => {
    render(<FilaPatio fila={[]} />);
    expect(screen.getByText("Ninguém na fila agora.")).toBeInTheDocument();
  });
});

describe("ChegadasPrevistas", () => {
  it("chegada em 1 h fica no meio do trilho de 2 h", () => {
    render(
      <ChegadasPrevistas
        agora={AGORA}
        chegadas={[{ caminhao_id: 1, placa: "TLG1A23", fazenda: "Fazenda Cervo", eta: "2026-10-20T19:00:00Z" }]}
      />,
    );
    const marca = screen.getByRole("listitem", { name: "TLG1A23, chega às 15h00, de Fazenda Cervo" });
    expect(marca).toHaveStyle({ left: "50%" });
  });

  it("escala do trilho mostra agora, +1 h e +2 h", () => {
    render(<ChegadasPrevistas agora={AGORA} chegadas={[]} />);
    expect(screen.getByText("14h00")).toBeInTheDocument();
    expect(screen.getByText("15h00")).toBeInTheDocument();
    expect(screen.getByText("16h00")).toBeInTheDocument();
    expect(screen.getByText("Nenhum caminhão carregado chega nas próximas 2 h.")).toBeInTheDocument();
  });
});
