import { urlApi } from "@/lib/api";
import { horaCurta } from "@/lib/formato";
import { ROTULO_OCORRENCIA } from "@/lib/motorista";
import type { Ocorrencia } from "@/lib/tipos";

/** Ocorrências registradas pelo app do motorista, mais recentes primeiro (ordem da API). */
export function ListaOcorrencias({ ocorrencias }: { ocorrencias: Ocorrencia[] }) {
  if (ocorrencias.length === 0) return <p className="text-tinta-suave">Nenhuma ocorrência nesta viagem.</p>;
  return (
    <ul className="text-[13px]">
      {ocorrencias.map((o) => (
        <li key={o.id} className="border-b border-linha-fraca py-2">
          <div className="flex justify-between gap-4">
            <span className="font-medium">{ROTULO_OCORRENCIA[o.tipo]}</span>
            <span className="numeros text-tinta-suave">{horaCurta(o.momento)}</span>
          </div>
          <p className="mt-0.5">{o.descricao}</p>
          {o.foto_url && (
            <a
              href={urlApi(o.foto_url)}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-primaria hover:underline"
            >
              Ver foto
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
