import { describe, expect, it } from "vitest";
import manifest from "./manifest";

describe("manifest", () => {
  it("abre o app do motorista como app instalado", () => {
    const m = manifest();
    expect(m.start_url).toBe("/motorista");
    expect(m.scope).toBe("/motorista");
    expect(m.display).toBe("standalone");
    expect(m.icons?.map((i) => i.sizes)).toEqual(expect.arrayContaining(["192x192", "512x512"]));
  });
});
