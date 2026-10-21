import type { Conexao } from "@/lib/tipos";

export function AvisoConexao({ conexao }: { conexao: Conexao }) {
  if (conexao !== "reconectando") return null;
  return (
    <div role="status" className="border-b border-linha bg-atencao-fundo px-4 py-1.5 text-xs text-atencao">
      Reconectando… As posições podem estar desatualizadas.
    </div>
  );
}
