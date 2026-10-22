import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { caminhao as c } from "@/lib/fabricas.test-util";
import { DetalheCaminhao } from "./DetalheCaminhao";

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

  it("mostra fazenda de origem, ETA, alertas e o link do replay", () => {
    const comTudo = c("TLG1A23", "EM_TRANSITO_CARREGADO", 55, {
      fazenda: "Fazenda Três Irmãos",
      eta: "2026-10-20T18:50:00Z",
      alertas_abertos: ["ATRASO", "PARADA"],
      viagem_atual_id: 42,
    });
    render(<DetalheCaminhao caminhao={comTudo} onVoltar={() => {}} />);
    expect(screen.getByText("Fazenda Três Irmãos")).toBeInTheDocument();
    expect(screen.getByText("14h50")).toBeInTheDocument();
    expect(screen.getByText("Atraso, Parada")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver viagem no replay" })).toHaveAttribute(
      "href",
      "/replay?viagem=42",
    );
  });

  it("sem viagem não oferece o replay", () => {
    render(<DetalheCaminhao caminhao={c("TLG1A23", null)} onVoltar={() => {}} />);
    expect(screen.queryByRole("link", { name: "Ver viagem no replay" })).not.toBeInTheDocument();
    expect(screen.getByText("Nenhum")).toBeInTheDocument();
  });

  it("caminhão no app mostra isso e lista as ocorrências da viagem", () => {
    render(
      <DetalheCaminhao
        caminhao={c("TLG1A23", "EM_TRANSITO_CARREGADO", 55, { assumido: true, viagem_atual_id: 42 })}
        ocorrencias={[
          {
            id: 9, caminhao_id: 1, placa: "TLG1A23", viagem_id: 42, tipo: "PNEU",
            descricao: "Pneu furado", foto_url: "/ocorrencias/9/foto", momento: "2026-10-20T18:50:00Z",
          },
        ]}
        onVoltar={() => {}}
      />,
    );
    expect(screen.getByText("Com o app do motorista")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ocorrências da viagem" })).toBeInTheDocument();
    expect(screen.getByText("Pneu furado")).toBeInTheDocument();
  });
});
