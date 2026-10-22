import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { caminhao } from "@/lib/fabricas.test-util";
import { EscolhaCaminhao } from "./EscolhaCaminhao";

describe("EscolhaCaminhao", () => {
  it("lista placa, motorista e estado e avisa a escolha", async () => {
    const onEscolher = vi.fn();
    render(
      <EscolhaCaminhao
        caminhoes={[caminhao("TLG1A23", "EM_TRANSITO_VAZIO", 0, { id: 3 }), caminhao("TLG2B11", "CARREGANDO", 0, { id: 4 })]}
        onEscolher={onEscolher}
      />,
    );
    const botao = screen.getByRole("button", { name: /TLG1A23/ });
    expect(botao).toHaveTextContent("Paulo Lima");
    expect(botao).toHaveTextContent("Vazio");
    await userEvent.click(botao);
    expect(onEscolher).toHaveBeenCalledWith(3);
  });

  it("caminhão já com o app aparece marcado", () => {
    render(
      <EscolhaCaminhao caminhoes={[caminhao("TLG1A23", "CARREGANDO", 0, { assumido: true })]} onEscolher={() => {}} />,
    );
    expect(screen.getByRole("button", { name: /TLG1A23/ })).toHaveTextContent("Já no app");
  });
});
