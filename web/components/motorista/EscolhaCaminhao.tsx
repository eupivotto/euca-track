import { ROTULO_ESTADO } from "@/lib/estados";
import type { Caminhao } from "@/lib/tipos";

/** Primeira tela do app: qual dos caminhões simulados a pessoa vai dirigir. */
export function EscolhaCaminhao({
  caminhoes,
  onEscolher,
}: {
  caminhoes: Caminhao[];
  onEscolher: (id: number) => void;
}) {
  return (
    <ul className="divide-y divide-linha border-y border-linha">
      {caminhoes.map((c) => (
        <li key={c.id}>
          <button
            type="button"
            onClick={() => onEscolher(c.id)}
            className="flex min-h-14 w-full items-center gap-3 px-4 py-3 text-left hover:bg-fundo-sutil"
          >
            <span className="flex flex-col">
              <span className="text-[16px] font-semibold">{c.placa}</span>
              <span className="text-[13px] text-tinta-suave">{c.motorista}</span>
            </span>
            <span className="ml-auto flex flex-col items-end text-[13px]">
              <span>{c.estado_atual ? ROTULO_ESTADO[c.estado_atual] : "Sem leitura"}</span>
              {c.assumido && <span className="text-atencao">Já no app</span>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
