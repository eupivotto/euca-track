import Link from "next/link";
import { TELAS } from "@/lib/telas";

export function BarraTopo({ ativa }: { ativa: string }) {
  return (
    <header className="flex min-h-[50px] shrink-0 flex-wrap items-center gap-x-4 gap-y-1.5 border-b border-linha px-4 py-2 sm:flex-nowrap sm:py-0">
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
      {/* No celular o selo desce para uma linha própria, embaixo do menu. */}
      <span className="w-full rounded bg-atencao-fundo px-2 py-[3px] text-xs leading-tight text-atencao sm:ml-auto sm:w-auto sm:max-w-[24rem]">
        Áreas de eucalipto: MapBiomas (2024). Frota e viagens: dados simulados.
      </span>
    </header>
  );
}
