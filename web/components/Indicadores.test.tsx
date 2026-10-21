import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Indicadores } from "@/lib/tipos";
import { BarrasToneladas } from "./BarrasToneladas";
import { TelaIndicadores } from "./TelaIndicadores";
import { UsoFrota } from "./UsoFrota";

vi.mock("@/lib/api", () => ({ buscarIndicadores: vi.fn() }));
import { buscarIndicadores } from "@/lib/api";

const hora = (h: number) => `2026-10-20T${String(h).padStart(2, "0")}:00:00-04:00`;
const SERIE_DIA = Array.from({ length: 24 }, (_, h) => ({ inicio: hora(h), toneladas: h === 10 ? 110 : 0 }));

const INDICADORES: Indicadores = {
  inicio: hora(0),
  fim: "2026-10-21T00:00:00-04:00",
  agora: hora(14),
  dias: 1,
  toneladas: 2380,
  viagens: 46,
  meta_t: 4000,
  ciclo_medio_min: 252,
  fila_media_min: 38,
  uso_frota: 0.8,
  frota_por_estado: {
    CARREGANDO: 4,
    EM_TRANSITO_CARREGADO: 6,
    FILA_PATIO: 3,
    PESAGEM: 1,
    DESCARGA: 1,
    EM_TRANSITO_VAZIO: 5,
  },
  serie: SERIE_DIA,
};

describe("BarrasToneladas", () => {
  it("uma barra por balde, com rótulo acessível", () => {
    render(<BarrasToneladas serie={SERIE_DIA} meta_t={4000} />);
    const barras = screen.getAllByRole("img");
    expect(barras).toHaveLength(24);
    expect(screen.getByRole("img", { name: "10h: 110 t" })).toBeInTheDocument();
  });

  it("linha do ritmo na altura de meta ÷ baldes", () => {
    // Ritmo de 166,7 t/h; o eixo vai até o maior entre a barra mais alta e o ritmo, com folga de 15%.
    render(<BarrasToneladas serie={SERIE_DIA} meta_t={4000} />);
    const ritmo = screen.getByText("ritmo necessário: 167 t por hora");
    expect(ritmo.parentElement).toHaveStyle({ bottom: `${100 / 1.15}%` });
  });

  it("série diária rotula pelo dia e fala em ritmo por dia", () => {
    const semana = Array.from({ length: 7 }, (_, d) => ({
      inicio: `2026-10-${14 + d}T00:00:00-04:00`,
      toneladas: 3000,
    }));
    render(<BarrasToneladas serie={semana} meta_t={28000} />);
    expect(screen.getByRole("img", { name: "14/10: 3.000 t" })).toBeInTheDocument();
    expect(screen.getByText("ritmo necessário: 4.000 t por dia")).toBeInTheDocument();
  });
});

describe("UsoFrota", () => {
  it("agrupa os estados do pátio e mostra percentuais", () => {
    render(<UsoFrota frota={INDICADORES.frota_por_estado} />);
    expect(screen.getByText("No pátio")).toBeInTheDocument();
    expect(screen.getByLabelText("No pátio: 5 caminhões, 25%")).toBeInTheDocument();
    expect(screen.getByLabelText("Carregado: 6 caminhões, 30%")).toBeInTheDocument();
  });
});

describe("TelaIndicadores", () => {
  beforeEach(() => {
    vi.mocked(buscarIndicadores).mockReset();
    vi.mocked(buscarIndicadores).mockResolvedValue(INDICADORES);
  });

  it("mostra a faixa de números do período", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TelaIndicadores />
      </QueryClientProvider>,
    );
    expect(await screen.findByText("2.380 t")).toBeInTheDocument();
    expect(screen.getByText("de 4.000 t")).toBeInTheDocument();
    expect(screen.getByText("4h12")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  it("trocar o filtro pede outro período", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <TelaIndicadores />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(buscarIndicadores).toHaveBeenCalledWith(1));
    await userEvent.click(screen.getByRole("button", { name: "7 dias" }));
    await waitFor(() => expect(buscarIndicadores).toHaveBeenCalledWith(7));
    expect(screen.getByRole("button", { name: "7 dias" })).toHaveAttribute("aria-pressed", "true");
  });
});
