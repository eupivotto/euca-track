import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { caminhao as c } from "@/lib/fabricas.test-util";
import { TabelaFrota } from "./TabelaFrota";

describe("TabelaFrota", () => {
  it("caminhão com o app do motorista leva a marca App", () => {
    render(
      <TabelaFrota
        caminhoes={[c("TLG1A23", "CARREGANDO", 0, { assumido: true }), c("TLG2B11", "CARREGANDO", 0, { id: 2 })]}
        onSelecionar={() => {}}
      />,
    );
    expect(screen.getByRole("row", { name: /TLG1A23/ })).toHaveTextContent("App");
    expect(screen.getByRole("row", { name: /TLG2B11/ })).not.toHaveTextContent("App");
  });

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

  it("mostra o ETA na hora de Campo Grande", () => {
    const comEta = c("TLG1A23", "EM_TRANSITO_CARREGADO", 55, { eta: "2026-10-20T18:50:00Z" });
    render(<TabelaFrota caminhoes={[comEta]} onSelecionar={() => {}} />);
    expect(screen.getByRole("row", { name: /TLG1A23 Carregado 55 t 14h50/ })).toBeInTheDocument();
  });

  it("linha com alerta aberto fica destacada", () => {
    const comAlerta = c("TLG1A23", "EM_TRANSITO_CARREGADO", 55, { alertas_abertos: ["ATRASO"] });
    render(<TabelaFrota caminhoes={[comAlerta, c("TLG2B11", "CARREGANDO")]} onSelecionar={() => {}} />);
    const [comDestaque, semDestaque] = screen.getAllByRole("row").slice(1);
    expect(comDestaque).toHaveClass("bg-atencao-fundo");
    expect(semDestaque).not.toHaveClass("bg-atencao-fundo");
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

