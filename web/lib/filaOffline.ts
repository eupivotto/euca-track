import { urlApi } from "./api";

// Check-ins e ocorrências passam sempre por esta fila: com rede saem na hora, sem rede esperam.
export type Pendente = {
  // Gerado no celular; a API não duplica um envio repetido com o mesmo id_local.
  id_local: string;
  tipo: "checkin" | "ocorrencia";
  criado_em: string;
  dados: Record<string, string | number>;
  foto?: Blob;
};

export interface Armazem {
  listar(): Promise<Pendente[]>;
  guardar(p: Pendente): Promise<void>;
  remover(id_local: string): Promise<void>;
}

export type Resultado = {
  enviados: string[];
  recusados: { id_local: string; motivo: string }[];
  // true: faltou rede ou o servidor falhou; o resto continua na fila.
  parou: boolean;
};

export function armazemEmMemoria(): Armazem {
  const itens = new Map<string, Pendente>();
  return {
    listar: async () => [...itens.values()].sort((a, b) => a.criado_em.localeCompare(b.criado_em)),
    guardar: async (p) => void itens.set(p.id_local, p),
    remover: async (id) => void itens.delete(id),
  };
}

async function motivo(resposta: Response): Promise<string> {
  try {
    const corpo = await resposta.json();
    if (typeof corpo?.detail === "string") return corpo.detail;
  } catch {
    // Corpo sem JSON: fica a mensagem genérica.
  }
  return `A API recusou o envio (${resposta.status})`;
}

/** Envia em ordem de criação. Para no primeiro erro de rede ou 5xx; 4xx sai da fila com o motivo. */
export async function enviarPendentes(
  armazem: Armazem,
  enviar: (p: Pendente) => Promise<Response>,
): Promise<Resultado> {
  const resultado: Resultado = { enviados: [], recusados: [], parou: false };
  for (const p of await armazem.listar()) {
    let resposta: Response;
    try {
      resposta = await enviar(p);
    } catch {
      resultado.parou = true;
      break;
    }
    if (resposta.status >= 500) {
      resultado.parou = true;
      break;
    }
    if (resposta.ok) resultado.enviados.push(p.id_local);
    else resultado.recusados.push({ id_local: p.id_local, motivo: await motivo(resposta) });
    await armazem.remover(p.id_local);
  }
  return resultado;
}

export function enviarPendente(p: Pendente): Promise<Response> {
  if (p.tipo === "checkin") {
    return fetch(urlApi("/motorista/checkin"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...p.dados, id_local: p.id_local }),
    });
  }
  const corpo = new FormData();
  for (const [chave, valor] of Object.entries(p.dados)) corpo.set(chave, String(valor));
  corpo.set("id_local", p.id_local);
  if (p.foto) corpo.set("foto", p.foto, "foto");
  return fetch(urlApi("/ocorrencias"), { method: "POST", body: corpo });
}
