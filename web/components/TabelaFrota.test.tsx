import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { caminhao as c } from "@/lib/fabricas.test-util";
import { DetalheCaminhao } from "./DetalheCaminhao";
import { TabelaFrota } from "./TabelaFrota";

describe("TabelaFrota", () => {
  it("mostra placa, estado legível e carga", () => {
    render(<TabelaFrota caminhoes={[c("TLG1A23", "FILA_PATIO", 55)]} onSelecionar={() => {}} />);
    expect(screen.getByRole("row", { name: /TLG1A23 Fila do pátio 55 t/ })).toBeInTheDocument();
  });

  it("sem carga mostra travessão", () => {
    render(<TabelaFrota caminhoes={[c("TLG2B11", "EM_TRANSITO_VAZIO", 0)]} onSelecionar={() => {}} />);
    expect(screen.getByRole("row", { name: /TLG2B11 Vazio —/ })).toBeInTheDocument();
  });

  it("ordena com carregados primeiro", () => {
    render(
      <TabelaFrota
        caminhoes={[c("TLG2B11", "CARREGANDO"), c("TLG1A23", "EM_TRANSITO_CARREGADO", 55)]}
        onSelecionar={() => {}}
      />,
    );
    const linhas = screen.getAllByRole("row").slice(1);
    expect(linhas[0]).toHaveTextContent("TLG1A23");
  });

  it("clique na linha seleciona o caminhão", async () => {
    const onSelecionar = vi.fn();
    render(<TabelaFrota caminhoes={[c("TLG1A23", "FILA_PATIO", 55, { id: 7 })]} onSelecionar={onSelecionar} />);
    await userEvent.click(screen.getByText("TLG1A23"));
    expect(onSelecionar).toHaveBeenCalledWith(7);
  });

  it("Enter na linha também seleciona", async () => {
    const onSelecionar = vi.fn();
    render(<TabelaFrota caminhoes={[c("TLG1A23", "FILA_PATIO", 55, { id: 7 })]} onSelecionar={onSelecionar} />);
    screen.getAllByRole("row")[1].focus();
    await userEvent.keyboard("{Enter}");
    expect(onSelecionar).toHaveBeenCalledWith(7);
  });
});

describe("DetalheCaminhao", () => {
  it("mostra os dados e volta para a frota", async () => {
    const onVoltar = vi.fn();
    render(<DetalheCaminhao caminhao={c("TLG1A23", "DESCARGA", 55)} onVoltar={onVoltar} />);
    expect(screen.getByRole("heading", { name: "TLG1A23" })).toBeInTheDocument();
    expect(screen.getByText("Paulo Lima")).toBeInTheDocument();
    expect(screen.getByText("Descarga")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Voltar para a frota" }));
    expect(onVoltar).toHaveBeenCalled();
  });
});
