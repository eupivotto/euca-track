import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // O service worker é sempre buscado de novo, para uma versão nova chegar ao celular.
  async headers() {
    return [{ source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache" }] }];
  },
};

export default nextConfig;
