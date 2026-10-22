import type { Metadata, Viewport } from "next";
import { RegistroSw } from "@/components/motorista/RegistroSw";

export const metadata: Metadata = {
  title: "App do motorista",
  description: "Viagem, check-in de carregamento e ocorrências do motorista (dados simulados).",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icone.svg", apple: "/icone-192.png" },
  appleWebApp: { capable: true, title: "Motorista", statusBarStyle: "default" },
};

export const viewport: Viewport = { themeColor: "#0f5c73" };

export default function LayoutMotorista({ children }: { children: React.ReactNode }) {
  return (
    <>
      <RegistroSw />
      {children}
    </>
  );
}
