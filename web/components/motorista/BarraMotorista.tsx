function envios(n: number): string {
  return n === 1 ? "1 envio guardado" : `${n} envios guardados`;
}

/** Topo do app: caminhão em uso, selo, troca de caminhão e o estado da fila offline. */
export function BarraMotorista({
  placa,
  online,
  pendentes,
  onTrocar,
}: {
  placa: string | null;
  online: boolean;
  pendentes: number;
  onTrocar?: () => void;
}) {
  const aviso = !online
    ? `Sem rede. ${envios(pendentes)}; saem quando a conexão voltar.`
    : pendentes > 0
      ? `Enviando ${envios(pendentes)}…`
      : null;
  return (
    <header className="sticky top-0 z-10 border-b border-linha bg-superficie">
      <div className="flex h-14 items-center gap-3 px-4">
        <span className="text-[16px] font-bold tracking-[-0.01em]">{placa ?? "Rota da Madeira"}</span>
        <span className="rounded bg-atencao-fundo px-2 py-[3px] text-xs whitespace-nowrap text-atencao">
          Dados simulados
        </span>
        {onTrocar && (
          <button
            type="button"
            onClick={onTrocar}
            className="ml-auto min-h-11 px-1 text-[14px] text-primaria underline-offset-2 hover:underline"
          >
            Trocar de caminhão
          </button>
        )}
      </div>
      {aviso && (
        <div role="status" className="border-t border-linha bg-atencao-fundo px-4 py-2 text-[13px] text-atencao">
          {aviso}
        </div>
      )}
    </header>
  );
}
