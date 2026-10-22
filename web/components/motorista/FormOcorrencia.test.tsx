import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FormOcorrencia } from "./FormOcorrencia";

function foto(tamanho: number, tipo = "image/jpeg") {
  return new File([new Uint8Array(tamanho)], "foto.jpg", { type: tipo });
}

describe("FormOcorrencia", () => {
  it("só envia com tipo e descrição", async () => {
    const onEnviar = vi.fn().mockResolvedValue(true);
    render(<FormOcorrencia onEnviar={onEnviar} onCancelar={() => {}} />);
    const enviar = screen.getByRole("button", { name: "Registrar ocorrência" });
    expect(enviar).toBeDisabled();
    await userEvent.click(screen.getByRole("radio", { name: "Pneu" }));
    expect(enviar).toBeDisabled();
    await userEvent.type(screen.getByLabelText("O que aconteceu"), "Pneu furado no km 30");
    expect(enviar).toBeEnabled();
    await userEvent.click(enviar);
    expect(onEnviar).toHaveBeenCalledWith({ tipo: "PNEU", descricao: "Pneu furado no km 30", foto: undefined });
  });

  it("envia a foto escolhida", async () => {
    const onEnviar = vi.fn().mockResolvedValue(true);
    render(<FormOcorrencia onEnviar={onEnviar} onCancelar={() => {}} />);
    await userEvent.click(screen.getByRole("radio", { name: "Problema mecânico" }));
    await userEvent.type(screen.getByLabelText("O que aconteceu"), "Freio");
    const arquivo = foto(1000);
    await userEvent.upload(screen.getByLabelText("Tirar ou escolher foto"), arquivo);
    expect(screen.getByRole("button", { name: "Remover foto" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Registrar ocorrência" }));
    expect(onEnviar).toHaveBeenCalledWith({ tipo: "MECANICA", descricao: "Freio", foto: arquivo });
  });

  it("se não der para guardar no celular, avisa e mantém o que foi escrito", async () => {
    const onEnviar = vi.fn().mockResolvedValue(false);
    render(<FormOcorrencia onEnviar={onEnviar} onCancelar={() => {}} />);
    await userEvent.click(screen.getByRole("radio", { name: "Pneu" }));
    await userEvent.type(screen.getByLabelText("O que aconteceu"), "Pneu furado");
    await userEvent.click(screen.getByRole("button", { name: "Registrar ocorrência" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível guardar no celular");
    expect(screen.getByLabelText("O que aconteceu")).toHaveValue("Pneu furado");
  });

  it("foto acima de 10 MB é recusada antes de enviar", async () => {
    const onEnviar = vi.fn().mockResolvedValue(true);
    render(<FormOcorrencia onEnviar={onEnviar} onCancelar={() => {}} />);
    await userEvent.upload(screen.getByLabelText("Tirar ou escolher foto"), foto(10 * 1024 * 1024 + 1));
    expect(screen.getByRole("alert")).toHaveTextContent("A foto passa de 10 MB");
    expect(screen.queryByRole("button", { name: "Remover foto" })).not.toBeInTheDocument();
  });

  it("descrição para em 500 caracteres e mostra o contador", async () => {
    render(<FormOcorrencia onEnviar={async () => true} onCancelar={() => {}} />);
    const campo = screen.getByLabelText("O que aconteceu");
    await userEvent.click(campo);
    await userEvent.paste("a".repeat(520));
    expect(campo).toHaveValue("a".repeat(500));
    expect(screen.getByText("500/500")).toBeInTheDocument();
  });
});
