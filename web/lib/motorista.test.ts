import { describe, expect, it } from "vitest";
import { acaoDoPasso, ROTULO_PASSO, TEXTO_BOTAO } from "./motorista";

describe("motorista", () => {
  it("só os passos da fazenda pedem check-in", () => {
    expect(acaoDoPasso("INICIAR_CARREGAMENTO")).toBe("INICIO_CARREGAMENTO");
    expect(acaoDoPasso("FINALIZAR_CARREGAMENTO")).toBe("FIM_CARREGAMENTO");
    for (const passo of ["INDO_PARA_FAZENDA", "AGUARDANDO_SAIDA", "INDO_PARA_FABRICA", "NA_FABRICA"] as const) {
      expect(acaoDoPasso(passo)).toBeNull();
    }
  });

  it("textos em português", () => {
    expect(TEXTO_BOTAO.INICIO_CARREGAMENTO).toBe("Iniciar carregamento");
    expect(TEXTO_BOTAO.FIM_CARREGAMENTO).toBe("Finalizar carregamento");
    expect(ROTULO_PASSO.INDO_PARA_FAZENDA).toBe("Indo para a fazenda");
  });
});
