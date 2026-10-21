/** Faixa de números no topo das telas (pátio, indicadores). */
export function FaixaNumeros({ itens }: { itens: { valor: string; rotulo: string }[] }) {
  return (
    <dl className="numeros flex flex-wrap gap-x-9 gap-y-3 border-b border-linha px-4 py-3.5">
      {itens.map((i) => (
        <div key={i.rotulo} className="flex flex-col-reverse">
          <dt className="text-xs text-tinta-suave">{i.rotulo}</dt>
          <dd className="text-[22px] leading-tight font-semibold tracking-[-0.02em]">{i.valor}</dd>
        </div>
      ))}
    </dl>
  );
}
