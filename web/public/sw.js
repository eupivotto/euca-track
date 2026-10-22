// Service worker do app do motorista: abre /motorista sem rede.
// Navegação: rede primeiro (nunca serve HTML antigo havendo rede), cópia em cache para o offline.
// /_next/static/: cache primeiro (nomes com hash, não mudam). /api/: nunca em cache.
const CACHE = "rota-motorista-v1";

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE).then((c) => c.add("/motorista")).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  if (pedido.method !== "GET") return;
  const url = new URL(pedido.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (pedido.mode === "navigate" && url.pathname.startsWith("/motorista")) {
    evento.respondWith(
      fetch(pedido)
        .then((resposta) => {
          const copia = resposta.clone();
          caches.open(CACHE).then((c) => c.put("/motorista", copia));
          return resposta;
        })
        .catch(() => caches.match("/motorista")),
    );
    return;
  }

  if (url.pathname.startsWith("/_next/static/") || /^\/icone/.test(url.pathname)) {
    evento.respondWith(
      caches.match(pedido).then(
        (guardada) =>
          guardada ||
          fetch(pedido).then((resposta) => {
            const copia = resposta.clone();
            caches.open(CACHE).then((c) => c.put(pedido, copia));
            return resposta;
          }),
      ),
    );
  }
});
