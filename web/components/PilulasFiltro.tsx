/** Filtro em pílulas, no mesmo estilo do menu da barra do topo. */
export function PilulasFiltro<T extends string | number>({
  rotulo,
  opcoes,
  valor,
  onMudar,
}: {
  rotulo: string;
  opcoes: { valor: T; rotulo: string }[];
  valor: T;
  onMudar: (valor: T) => void;
}) {
  return (
    <div role="group" aria-label={rotulo} className="inline-flex gap-0.5 rounded-lg bg-trilho p-[3px]">
      {opcoes.map((o) => {
        const ativa = o.valor === valor;
        return (
          <button
            key={String(o.valor)}
            type="button"
            aria-pressed={ativa}
            onClick={() => onMudar(o.valor)}
            className={
              ativa
                ? "rounded-md bg-superficie px-3 py-[5px] font-semibold whitespace-nowrap ring-1 ring-linha"
                : "rounded-md px-3 py-[5px] whitespace-nowrap text-tinta-suave hover:text-tinta"
            }
          >
            {o.rotulo}
          </button>
        );
      })}
    </div>
  );
}
