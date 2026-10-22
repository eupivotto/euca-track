import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { caminhao } from "@/lib/fabricas.test-util";
import type { PainelMotorista, Passo } from "@/lib/tipos";
import { PainelViagem } from "./PainelViagem";

function painel(passo: Passo, extra: Partial<PainelMotorista> = {}): PainelMotorista {
  return {
    caminhao: caminhao("TLG1A23", "CARREGANDO", 0, { eta: "2026-10-21T18:30:00Z" }),
    assumido: true,
    assumido_ate: "2026-10-21T19:00:00Z",
    passo,
    destino: { fazenda_id: 5, nome: "Fazenda Cervo", distancia_km: 48.3 },
    viagem_id: 10,
    checkins: [],
    agora: "2026-10-21T18:00:00Z",
    ...extra,
  };
}

describe("PainelViagem", () => {
  it("na fazenda, o botão inicia o carregamento", async () => {
    const onCheckin = vi.fn();
    render(<PainelViagem painel={painel("INICIAR_CARREGAMENTO")} pendentes={[]} onCheckin={onCheckin} />);
    expect(screen.getByText("Fazenda Cervo")).toBeInTheDocument();
    expect(screen.getByText("48 km")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Iniciar carregamento" }));
    expect(onCheckin).toHaveBeenCalledWith("INICIO_CARREGAMENTO");
  });

  it("indo para a fábrica não tem check-in e mostra a chegada prevista", () => {
    render(
      <PainelViagem
        painel={painel("INDO_PARA_FABRICA", {
          caminhao: caminhao("TLG1A23", "EM_TRANSITO_CARREGADO", 55, { eta: "2026-10-21T18:30:00Z" }),
        })}
        pendentes={[]}
        onCheckin={() => {}}
      />,
    );
    expect(screen.getByText("Indo para a fábrica")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("Chegada prevista às 14h30")).toBeInTheDocument();
  });

  it("check-in na fila desabilita o botão até haver rede", () => {
    render(
      <PainelViagem painel={painel("FINALIZAR_CARREGAMENTO")} pendentes={["FIM_CARREGAMENTO"]} onCheckin={() => {}} />,
    );
    const botao = screen.getByRole("button", { name: "Enviando quando houver rede" });
    expect(botao).toBeDisabled();
  });

  it("sem posse avisa que o simulador retomou o caminhão", () => {
    render(<PainelViagem painel={painel("INICIAR_CARREGAMENTO", { assumido: false })} pendentes={[]} onCheckin={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("O simulador retomou este caminhão");
  });
});
