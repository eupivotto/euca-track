import { describe, expect, it } from "vitest";
import { caminhao } from "./fabricas.test-util";
import {
  acaoDoPasso,
  acoesEmEspera,
  confirmacaoOcorrencia,
  guardarPainel,
  lerPainelGuardado,
  ROTULO_PASSO,
  TEXTO_BOTAO,
} from "./motorista";
import type { PainelMotorista } from "./tipos";

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

describe("painel guardado", () => {
  const painel: PainelMotorista = {
    caminhao: caminhao("TLG1A23", "CARREGANDO"),
    assumido: true,
    assumido_ate: null,
    passo: "INICIAR_CARREGAMENTO",
    destino: null,
    viagem_id: 1,
    checkins: [],
    agora: "2026-10-21T18:00:00Z",
  };

  it("guarda o último painel de cada caminhão para abrir sem rede", () => {
    guardarPainel(7, painel);
    expect(lerPainelGuardado(7)).toEqual(painel);
    expect(lerPainelGuardado(8)).toBeUndefined();
  });

  it("armazenamento indisponível não quebra", () => {
    const original = Storage.prototype.getItem;
    Storage.prototype.getItem = () => {
      throw new Error("bloqueado");
    };
    try {
      expect(lerPainelGuardado(7)).toBeUndefined();
    } finally {
      Storage.prototype.getItem = original;
    }
  });
});

describe("confirmacaoOcorrencia", () => {
  it("guardada enquanto está na fila, registrada quando sai", () => {
    expect(confirmacaoOcorrencia("o1", ["o1"])).toBe("Ocorrência guardada; será enviada quando houver rede.");
    expect(confirmacaoOcorrencia("o1", [])).toBe("Ocorrência registrada.");
  });
});

describe("acoesEmEspera", () => {
  it("check-in enviado segura o botão até o passo mudar", () => {
    const enviada = { id_local: "c1", acao: "INICIO_CARREGAMENTO" as const, passo: "INICIAR_CARREGAMENTO" as const };
    // Saiu da fila, mas o painel ainda não recarregou: continua esperando.
    expect(acoesEmEspera([], enviada, "INICIAR_CARREGAMENTO", [])).toEqual(["INICIO_CARREGAMENTO"]);
    // O painel mudou de passo: libera o próximo botão.
    expect(acoesEmEspera([], enviada, "FINALIZAR_CARREGAMENTO", [])).toEqual([]);
  });

  it("check-in recusado pela API libera o botão", () => {
    const enviada = { id_local: "c1", acao: "INICIO_CARREGAMENTO" as const, passo: "INICIAR_CARREGAMENTO" as const };
    expect(acoesEmEspera([], enviada, "INICIAR_CARREGAMENTO", ["c1"])).toEqual([]);
  });

  it("o que está na fila também espera", () => {
    expect(acoesEmEspera(["FIM_CARREGAMENTO"], null, "FINALIZAR_CARREGAMENTO", [])).toEqual(["FIM_CARREGAMENTO"]);
  });
});
