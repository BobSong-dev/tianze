import { describe, it, expect } from "vitest";
import { analyzeBirthInfo, getMeta, healthCheck } from "../api/tianze";

describe("API client", () => {
  it("exports analyzeBirthInfo function", () => {
    expect(typeof analyzeBirthInfo).toBe("function");
  });
  it("exports getMeta function", () => {
    expect(typeof getMeta).toBe("function");
  });
  it("exports healthCheck function", () => {
    expect(typeof healthCheck).toBe("function");
  });
});
