import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ListaOcorrencias } from "./ListaOcorrencias";

describe("ListaOcorrencias", () => {
  it("mostra tipo, hora, descrição e o link da foto quando há", () => {
    render(
      <ListaOcorrencias
        ocorrencias={[
          {
            id: 9, caminhao_id: 1, placa: "TLG1A23", viagem_id: 42, tipo: "PNEU", descricao: "Pneu furado",
            foto_url: "/ocorrencias/9/foto", momento: "2026-10-20T18:50:00Z",
          },
          {
            id: 10, caminhao_id: 1, placa: "TLG1A23", viagem_id: 42, tipo: "ESTRADA", descricao: "Ponte interditada",
            foto_url: null, momento: "2026-10-20T19:05:00Z",
          },
        ]}
      />,
    );
    const itens = screen.getAllByRole("listitem");
    expect(itens[0]).toHaveTextContent("Pneu");
    expect(itens[0]).toHaveTextContent("14h50");
    expect(screen.getByRole("link", { name: "Ver foto" })).toHaveAttribute("href", "/api/ocorrencias/9/foto");
    expect(itens[1]).toHaveTextContent("Problema na estrada");
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });

  it("sem ocorrências diz isso", () => {
    render(<ListaOcorrencias ocorrencias={[]} />);
    expect(screen.getByText("Nenhuma ocorrência nesta viagem.")).toBeInTheDocument();
  });
});
