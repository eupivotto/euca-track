"use client";

import { useEffect, useState } from "react";
import { ROTULO_OCORRENCIA } from "@/lib/motorista";
import type { TipoOcorrencia } from "@/lib/tipos";

// Mesmo limite da API (foto_max_mb): recusa aqui para não guardar na fila algo que voltaria 413.
const FOTO_MAX_MB = 10;
const DESCRICAO_MAX = 500;

export type NovaOcorrencia = { tipo: TipoOcorrencia; descricao: string; foto: File | undefined };

export function FormOcorrencia({
  onEnviar,
  onCancelar,
}: {
  onEnviar: (o: NovaOcorrencia) => void;
  onCancelar: () => void;
}) {
  const [tipo, setTipo] = useState<TipoOcorrencia | null>(null);
  const [descricao, setDescricao] = useState("");
  const [foto, setFoto] = useState<File | undefined>();
  const [erroFoto, setErroFoto] = useState<string | null>(null);
  const [previa, setPrevia] = useState<string | null>(null);

  useEffect(() => {
    if (!foto || typeof URL.createObjectURL !== "function") return;
    const url = URL.createObjectURL(foto);
    setPrevia(url);
    return () => {
      URL.revokeObjectURL(url);
      setPrevia(null);
    };
  }, [foto]);

  const escolherFoto = (arquivo: File | undefined) => {
    setErroFoto(null);
    if (arquivo && arquivo.size > FOTO_MAX_MB * 1024 * 1024) {
      setErroFoto(`A foto passa de ${FOTO_MAX_MB} MB. Escolha outra ou tire de novo.`);
      setFoto(undefined);
      return;
    }
    setFoto(arquivo);
  };

  const pronto = tipo !== null && descricao.trim().length > 0;

  return (
    <form
      aria-label="Registrar ocorrência"
      className="flex flex-col gap-5 px-4 pt-5 pb-8"
      onSubmit={(e) => {
        e.preventDefault();
        if (pronto) onEnviar({ tipo, descricao: descricao.trim(), foto });
      }}
    >
      <h1 className="text-[20px] font-semibold">Nova ocorrência</h1>

      <fieldset>
        <legend className="mb-2 text-[13px] text-tinta-suave">Tipo</legend>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(ROTULO_OCORRENCIA) as TipoOcorrencia[]).map((t) => (
            <label
              key={t}
              className="flex min-h-11 cursor-pointer items-center rounded-full border border-linha px-4 has-checked:border-primaria has-checked:bg-primaria has-checked:text-white has-focus-visible:outline-2 has-focus-visible:outline-primaria"
            >
              <input
                type="radio"
                name="tipo"
                value={t}
                checked={tipo === t}
                onChange={() => setTipo(t)}
                className="sr-only"
              />
              {ROTULO_OCORRENCIA[t]}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="descricao" className="text-[13px] text-tinta-suave">
          O que aconteceu
        </label>
        <textarea
          id="descricao"
          rows={4}
          maxLength={DESCRICAO_MAX}
          value={descricao}
          onChange={(e) => setDescricao(e.target.value.slice(0, DESCRICAO_MAX))}
          className="rounded-lg border border-linha px-3 py-2 text-[15px]"
        />
        <span className="numeros self-end text-[12px] text-tinta-suave">
          {descricao.length}/{DESCRICAO_MAX}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {foto ? (
          <div className="flex items-center gap-3">
            {previa && (
              // eslint-disable-next-line @next/next/no-img-element -- prévia local (blob:), sem otimização
              <img src={previa} alt="Prévia da foto" className="size-20 rounded-md object-cover" />
            )}
            <span className="flex-1 truncate text-[14px]">{foto.name}</span>
            <button type="button" onClick={() => setFoto(undefined)} className="min-h-11 px-1 text-primaria">
              Remover foto
            </button>
          </div>
        ) : (
          <label className="flex min-h-12 cursor-pointer items-center justify-center rounded-lg border border-dashed border-linha text-[15px] text-primaria has-focus-visible:outline-2 has-focus-visible:outline-primaria">
            Tirar ou escolher foto
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              onChange={(e) => escolherFoto(e.target.files?.[0])}
              className="sr-only"
            />
          </label>
        )}
        {erroFoto && (
          <p role="alert" className="text-[14px] text-atencao">
            {erroFoto}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <button
          type="submit"
          disabled={!pronto}
          className="h-14 rounded-lg bg-primaria text-[16px] font-semibold text-white disabled:bg-trilho disabled:text-tinta-suave"
        >
          Registrar ocorrência
        </button>
        <button type="button" onClick={onCancelar} className="min-h-11 text-[15px] text-tinta-suave">
          Cancelar
        </button>
      </div>
    </form>
  );
}
