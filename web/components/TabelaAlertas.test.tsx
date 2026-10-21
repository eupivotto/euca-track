import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Alerta } from "@/lib/tipos";
import { TabelaAlertas } from "./TabelaAlertas";

const ABERTO: Alerta = {
  id: 1,
  tipo: "PARADA",
  caminhao_id: 3,
  placa: "TLG1A23",
  fazenda_id: null,
  fazenda: null,
  mensagem: "Parado há 16 min fora de fazenda ou fábrica",
  aberto_em: "2026-10-20T18:16:00Z",
  fechado_em: null,
  status: "ABERTO",
};

describe("TabelaAlertas", () => {
  it("alerta aberto mostra hora, tipo, caminhão, mensagem e link para o mapa", () => {
    render(<TabelaAlertas alertas={[ABERTO]} status="ABERTO" />);
    const linha = screen.getAllByRole("row")[1];
    expect(linha).toHaveTextContent(/14h16\s*Parada\s*TLG1A23\s*Parado há 16 min fora de fazenda ou fábrica\s*Aberto/);
    expect(screen.getByText("Parada")).toHaveClass("text-atencao");
    expect(screen.getByRole("link", { name: "Ver TLG1A23 no mapa" })).toHaveAttribute("href", "/?caminhao=3");
  });

  it("fechado mostra a hora em que fechou, sem destaque", () => {
    const fechado = { ...ABERTO, status: "FECHADO" as const, fechado_em: "2026-10-20T18:50:00Z" };
    render(<TabelaAlertas alertas={[fechado]} status="FECHADO" />);
    expect(screen.getByText("Fechado às 14h50")).toBeInTheDocument();
    expect(screen.getByText("Parada")).not.toHaveClass("text-atencao");
    expect(screen.getAllByRole("row")[1]).toHaveClass("text-tinta-suave");
  });

  it("sem alertas abertos diz isso", () => {
    render(<TabelaAlertas alertas={[]} status="ABERTO" />);
    expect(screen.getByText("Nenhum alerta aberto.")).toBeInTheDocument();
  });

  it("sem alertas fechados diz isso", () => {
    render(<TabelaAlertas alertas={[]} status="FECHADO" />);
    expect(screen.getByText("Nenhum alerta fechado.")).toBeInTheDocument();
  });
});
