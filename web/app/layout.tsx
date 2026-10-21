import type { Metadata } from "next";
import { Instrument_Sans } from "next/font/google";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";
import { Providers } from "./providers";

const instrument = Instrument_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--fonte-instrument",
});

export const metadata: Metadata = {
  title: "Rota da Madeira",
  description: "Painel de operações florestais: logística de madeira e risco de incêndio.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={instrument.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
