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

  it("arrastar o cursor avisa o novo momento", () => {
    const onMudar = vi.fn();
    render(<LinhaTempo inicio={INICIO} fim={FIM} eventos={EVENTOS} cursor={Date.parse(INICIO)} onMudar={onMudar} />);
    const cursor = screen.getByRole("slider", { name: "Momento da viagem" });
    expect(cursor).toHaveAttribute("aria-valuetext", "10h00");
    fireEvent.change(cursor, { target: { value: String(Date.parse(FIM)) } });
    expect(onMudar).toHaveBeenCalledWith(Date.parse(FIM));
  });
});
