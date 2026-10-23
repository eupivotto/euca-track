"use client";

import { useState } from "react";
import { CLASSES, COR_CHUVA, COR_CLASSE, ROTULO_CLASSE } from "@/lib/risco";
import type { DiaRisco, HistoricoRisco } from "@/lib/tipos";

// Chuva que reduziu a FMA (faixas da fórmula acima de 2,4 mm).
const CHUVA_QUE_CONTA_MM = 2.4;

const umaCasa = (valor: number) => valor.toFixed(1).replace(".", ",");

/** "2026-10-21" → "21/10". A data já é do calendário local: não passa por Date. */
const diaMes = (data: string) => `${data.slice(8, 10)}/${data.slice(5, 7)}`;

function rotuloDia(data: string, dia: DiaRisco | null) {
  if (!dia) return `${diaMes(data)}: sem dado`;
  const partes = [`FMA ${umaCasa(dia.fma)}`, ROTULO_CLASSE[dia.classe]];
  if (dia.chuva_mm !== null) partes.push(`chuva ${umaCasa(dia.chuva_mm)} mm`);
  if (dia.ur_13h !== null) partes.push(`UR 13h ${Math.round(dia.ur_13h)}%`);
  return `${diaMes(data)}: ${partes.join(", ")}`;
}

export function GradeRisco({ historico }: { historico: HistoricoRisco }) {
  const [detalhe, setDetalhe] = useState<string | null>(null);
  const { datas, fazendas } = historico;

  return (
    <div className="flex flex-col gap-3">
      <p role="status" className="min-h-[1.5em] text-[12.5px] text-tinta-suave">
        {detalhe ?? "Passe o mouse ou use Tab nas células para ver cada dia."}
      </p>
      {/* No celular a grade rola de lado dentro dela mesma; a página não. O relative prende
          os rótulos sr-only (position: absolute) dentro da rolagem. */}
      <div className="relative overflow-x-auto pb-1">
        <table className="numeros border-separate border-spacing-[2px] text-[12px]">
          <thead>
            <tr className="text-[10.5px] text-tinta-suave">
              <th scope="col" className="sticky left-0 bg-superficie pr-3 text-left font-medium">
                Área
              </th>
              {datas.map((data, i) => (
                <th key={data} scope="col" className="w-[14px] p-0 text-center font-normal">
                  {/* Um rótulo a cada semana, contando de hoje para trás. */}
                  {(datas.length - 1 - i) % 7 === 0 ? (
                    <span className="block w-[14px] overflow-visible whitespace-nowrap">{data.slice(8, 10)}</span>
                  ) : (
                    <span className="sr-only">{diaMes(data)}</span>
                  )}
                </th>
              ))}
              <th scope="col" className="pl-3 text-right font-medium">
                FMA hoje
              </th>
            </tr>
          </thead>
          <tbody>
            {fazendas.map((f) => {
              const hoje = f.dias[f.dias.length - 1];
              return (
                <tr key={f.fazenda_id}>
                  <th
                    scope="row"
                    className="sticky left-0 bg-superficie pr-3 text-left font-medium whitespace-nowrap"
                  >
                    {f.nome}
                  </th>
                  {f.dias.map((dia, i) => {
                    const rotulo = rotuloDia(datas[i], dia);
                    const mostrar = () => setDetalhe(`${f.nome} · ${rotulo}`);
                    return (
                      <td key={datas[i]} className="p-0">
                        <span
                          data-testid="celula-risco"
                          role="img"
                          tabIndex={0}
                          aria-label={rotulo}
                          title={rotulo}
                          onMouseEnter={mostrar}
                          onFocus={mostrar}
                          className="relative block h-4 w-[14px] rounded-[2px]"
                          style={{ background: dia ? COR_CLASSE[dia.classe] : "var(--color-trilho)" }}
                        >
                          {dia?.chuva_mm != null && dia.chuva_mm > CHUVA_QUE_CONTA_MM && (
                            <i
                              data-testid="ponto-chuva"
                              aria-hidden
                              className="absolute top-1/2 left-1/2 size-[5px] -translate-x-1/2 -translate-y-1/2 rounded-full ring-1 ring-white"
                              style={{ background: COR_CHUVA }}
                            />
                          )}
                        </span>
                      </td>
                    );
                  })}
                  <td data-testid="fma-hoje" className="pl-3 text-right font-semibold">
                    {hoje ? umaCasa(hoje.fma) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px]">
        {CLASSES.map((c) => (
          <span key={c} className="inline-flex items-center gap-1.5">
            <i aria-hidden className="inline-block h-3 w-[10px] rounded-[2px]" style={{ background: COR_CLASSE[c] }} />
            {ROTULO_CLASSE[c]}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <i aria-hidden className="inline-block size-[5px] rounded-full" style={{ background: COR_CHUVA }} />
          Chuva acima de 2,4 mm
        </span>
        <span className="inline-flex items-center gap-1.5">
          <i aria-hidden className="inline-block h-3 w-[10px] rounded-[2px] bg-trilho" />
          Sem dado
        </span>
      </div>
    </div>
  );
}
