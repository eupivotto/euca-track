"use client";

import { useEffect } from "react";

/**
 * Registra o service worker. Navegadores só permitem em HTTPS ou localhost:
 * pelo IP da rede local (http) o app funciona, mas não abre sem rede nem instala.
 */
export function RegistroSw() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!window.isSecureContext || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/motorista" }).catch(() => {
      // Sem service worker o app segue funcionando com rede.
    });
  }, []);
  return null;
}
