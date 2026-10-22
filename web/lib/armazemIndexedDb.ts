import type { Armazem, Pendente } from "./filaOffline";

const LOJA = "pendentes";

function abrir(nome: string): Promise<IDBDatabase> {
  return new Promise((resolver, rejeitar) => {
    const pedido = indexedDB.open(nome, 1);
    pedido.onupgradeneeded = () => pedido.result.createObjectStore(LOJA, { keyPath: "id_local" });
    pedido.onsuccess = () => resolver(pedido.result);
    pedido.onerror = () => rejeitar(pedido.error);
  });
}

async function operar<T>(
  nome: string,
  modo: IDBTransactionMode,
  fazer: (loja: IDBObjectStore) => IDBRequest,
): Promise<T> {
  const banco = await abrir(nome);
  return new Promise<T>((resolver, rejeitar) => {
    const transacao = banco.transaction(LOJA, modo);
    const pedido = fazer(transacao.objectStore(LOJA));
    transacao.oncomplete = () => {
      banco.close();
      resolver(pedido.result as T);
    };
    transacao.onerror = () => {
      banco.close();
      rejeitar(transacao.error);
    };
  });
}

/** Fila do app no IndexedDB do celular: sobrevive a fechar a página e guarda a foto (Blob). */
export function armazemIndexedDb(nome = "rota-motorista"): Armazem {
  return {
    listar: async () => {
      const itens = await operar<Pendente[]>(nome, "readonly", (loja) => loja.getAll());
      return itens.sort((a, b) => a.criado_em.localeCompare(b.criado_em));
    },
    guardar: async (p) => {
      await operar(nome, "readwrite", (loja) => loja.put(p));
    },
    remover: async (id_local) => {
      await operar(nome, "readwrite", (loja) => loja.delete(id_local));
    },
  };
}
