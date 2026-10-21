import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LinhaTempo } from "./LinhaTempo";

const INICIO = "2026-10-20T14:00:00Z";
const FIM = "2026-10-20T16:00:00Z";
const EVENTOS = [
  { estado: "CARREGANDO" as const, momento: INICIO },
  { estado: "EM_TRANSITO_CARREGADO" as const, momento: "2026-10-20T15:00:00Z" },
];

describe("LinhaTempo", () => {
  it("mostra os eventos com nome e hora, na posição do tempo", () => {
    render(<LinhaTempo inicio={INICIO} fim={FIM} eventos={EVENTOS} cursor={Date.parse(INICIO)} onMudar={() => {}} />);
    expect(screen.getByText("Carregando")).toBeInTheDocument();
    const carregado = screen.getByRole("listitem", { name: "Carregado às 11h00" });
    expect(carregado).toHaveStyle({ left: "50%" });
  });

  it("rótulos nas pontas não saem do trilho", () => {
    const eventos = [...EVENTOS, { estado: "FILA_PATIO" as const, momento: FIM }];
    render(<LinhaTempo inicio={INICIO} fim={FIM} eventos={eventos} cursor={Date.parse(INICIO)} onMudar={() => {}} />);
    expect(screen.getByRole("listitem", { name: "Carregando às 10h00" })).toHaveClass("items-start");
    expect(screen.getByRole("listitem", { name: "Carregado às 11h00" })).toHaveClass("-translate-x-1/2");
    expect(screen.getByRole("listitem", { name: "Fila do pátio às 12h00" })).toHaveClass("items-end");
  });

  it("evento colado no anterior fica só com o ponto, sem rótulo visível", () => {
    const eventos = [
      ...EVENTOS,
      { estado: "PESAGEM" as const, momento: "2026-10-20T15:00:30Z" },
    ];
    render(<LinhaTempo inicio={INICIO} fim={FIM} eventos={eventos} cursor={Date.parse(INICIO)} onMudar={() => {}} />);
    expect(screen.getByRole("listitem", { name: "Pesagem às 11h00" })).toBeInTheDocument();
    expect(screen.queryByText("Pesagem")).not.toBeInTheDocument();
    expect(screen.getByText("Carregado")).toBeInTheDocument();
  });

  it("arrastar o cursor avisa o novo momento", () => {
    const onMudar = vi.fn();
    render(<LinhaTempo inicio={INICIO} fim={FIM} eventos={EVENTOS} cursor={Date.parse(INICIO)} onMudar={onMudar} />);
    const cursor = screen.getByRole("slider", { name: "Momento da viagem" });
    expect(cursor).toHaveAttribute("aria-valuetext", "10h00");
    fireEvent.change(cursor, { target: { value: String(Date.parse(FIM)) } });
    expect(onMudar).toHaveBeenCalledWith(Date.parse(FIM));
  });
});
