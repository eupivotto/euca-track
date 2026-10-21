import { BarraTopo } from "@/components/BarraTopo";
import { TelaIndicadores } from "@/components/TelaIndicadores";

export default function Indicadores() {
  return (
    <div className="flex min-h-dvh flex-col">
      <BarraTopo ativa="/indicadores" />
      <TelaIndicadores />
    </div>
  );
}
