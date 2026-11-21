import { expect, it } from "vitest";
import { elementRows, summarizeElements } from "../presentation/elementCounts";
import type { ElementCountsData } from "../types/tianze";

it("keeps zero counts, ties and incomplete counts distinct", () => {
  const elements = Object.fromEntries(["wood", "fire", "earth", "metal", "water"].map(key =>
    [key, { visible: 0, hidden: 0 }]));
  const counts: ElementCountsData = { elements, stems: {}, branches: {}, hiddenStems: {}, missing: [] };
  const summary = () => summarizeElements(elementRows(counts));
  expect(summary()).toContain("各 0 处");
  elements.wood.hidden = 2;
  elements.fire.visible = 2;
  expect(summary()).toBe("按显干与藏干合计，木、火最多（2 处），土、金、水最少（0 处）。");
  delete elements.metal;
  expect(summary()).toBeNull();
});
