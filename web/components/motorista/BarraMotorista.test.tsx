import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BarraMotorista } from "./BarraMotorista";

describe("BarraMotorista", () => {
  it("offline mostra quantos envios estão guardados", () => {
    render(<BarraMotorista placa="TLG1A23" online={false} pendentes={2} onTrocar={() => {}} />);
    expect(screen.getByText("Dados simulados")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Sem rede. 2 envios guardados");
  });

  it("offline sem nada guardado explica o que acontece", () => {
    render(<BarraMotorista placa="TLG1A23" online={false} pendentes={0} onTrocar={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Sem rede. O que você registrar fica guardado e sai quando a conexão voltar.",
    );
  });

  it("online sem pendências não mostra aviso", () => {
    render(<BarraMotorista placa="TLG1A23" online pendentes={0} onTrocar={() => {}} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("online com pendência diz que está enviando", () => {
    render(<BarraMotorista placa="TLG1A23" online pendentes={1} onTrocar={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("Enviando 1 envio guardado");
  });

  it("trocar de caminhão", async () => {
    const onTrocar = vi.fn();
    render(<BarraMotorista placa="TLG1A23" online pendentes={0} onTrocar={onTrocar} />);
    await userEvent.click(screen.getByRole("button", { name: "Trocar de caminhão" }));
    expect(onTrocar).toHaveBeenCalled();
  });
});
