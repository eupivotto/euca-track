import { horaCurta } from "@/lib/formato";
import { acaoDoPasso, ROTULO_PASSO, TEXTO_BOTAO } from "@/lib/motorista";
import type { AcaoCheckin, PainelMotorista } from "@/lib/tipos";

/** A viagem do ponto de vista do motorista: para onde vai, quando chega e o check-in da vez. */
export function PainelViagem({
  painel,
  pendentes,
  online,
  onCheckin,
}: {
  painel: PainelMotorista;
  // Check-ins na fila ou a caminho: o botão fica parado até o painel mudar de passo.
  pendentes: AcaoCheckin[];
  online: boolean;
  onCheckin: (acao: AcaoCheckin) => void;
}) {
  const { caminhao, destino, passo } = painel;
  const acao = acaoDoPasso(passo);
  const naFila = acao !== null && pendentes.includes(acao);
  const indoParaFabrica = passo === "INDO_PARA_FABRICA";

  return (
    <section aria-label="Viagem" className="px-4 pt-5 pb-6">
      {!painel.assumido && (
        <p role="status" className="mb-4 rounded-md bg-atencao-fundo px-3 py-2 text-[14px] text-atencao">
          O caminhão ainda não está com o app; ele será assumido em instantes.
        </p>
      )}
      <h1 className="text-[24px] leading-tight font-semibold tracking-[-0.01em]">{ROTULO_PASSO[passo]}</h1>

      <dl className="numeros mt-5 grid grid-cols-2 gap-x-4 gap-y-3 text-[15px]">
        <div className="col-span-2">
          <dt className="text-[13px] text-tinta-suave">{indoParaFabrica ? "Carga de" : "Fazenda"}</dt>
          <dd className="font-medium">{(indoParaFabrica ? caminhao.fazenda : destino?.nome) ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-[13px] text-tinta-suave">Distância da rota</dt>
          <dd>{destino?.distancia_km != null ? `${Math.round(destino.distancia_km)} km` : "—"}</dd>
        </div>
        <div>
          <dt className="text-[13px] text-tinta-suave">Carga</dt>
          <dd>{caminhao.carga_t > 0 ? `${caminhao.carga_t} t` : "Vazio"}</dd>
        </div>
      </dl>

      {caminhao.eta && (
        <p className="numeros mt-4 text-[15px]">
          {indoParaFabrica ? "Chegada prevista" : "Chegada à fazenda prevista"} às {horaCurta(caminhao.eta)}
        </p>
      )}

      {acao && painel.assumido && (
        <button
          type="button"
          disabled={naFila}
          onClick={() => onCheckin(acao)}
          className="mt-6 h-14 w-full rounded-lg bg-primaria text-[16px] font-semibold text-white disabled:bg-trilho disabled:text-tinta-suave"
        >
          {naFila ? (online ? "Enviando…" : "Enviando quando houver rede") : TEXTO_BOTAO[acao]}
        </button>
      )}
    </section>
  );
}
