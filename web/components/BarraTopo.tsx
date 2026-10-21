import Link from "next/link";
import { TELAS } from "@/lib/telas";

export function BarraTopo({ ativa }: { ativa: string }) {
  return (
    <header className="flex h-[50px] shrink-0 items-center gap-4 border-b border-linha px-4">
      <span className="text-[15px] font-bold tracking-[-0.01em]">Rota da Madeira</span>
      <nav aria-label="Telas" className="flex gap-0.5 overflow-x-auto rounded-lg bg-trilho p-[3px]">
        {TELAS.map((tela) => {
          const atual = tela.href === ativa;
          return (
            <Link
              key={tela.href}
              href={tela.href}
              aria-current={atual ? "page" : undefined}
              className={
                atual
                  ? "rounded-md bg-superficie px-3 py-[5px] font-semibold whitespace-nowrap ring-1 ring-linha"
                  : "rounded-md px-3 py-[5px] whitespace-nowrap text-tinta-suave hover:text-tinta"
              }
            >
              {tela.rotulo}
            </Link>
          );
        })}
      </nav>
      <span className="ml-auto rounded bg-atencao-fundo px-2 py-[3px] text-xs whitespace-nowrap text-atencao">
        Dados simulados
      </span>
    </header>
  );
}
