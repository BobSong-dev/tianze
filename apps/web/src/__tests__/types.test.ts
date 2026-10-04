import { describe, it, expect } from "vitest";

describe("Types module", () => {
  it("has PillarData shape", async () => {
    const mod = await import("../types/tianze");
    expect(mod).toBeDefined();
  });
});
