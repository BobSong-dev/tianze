import { ELEMENT_ORDER, elementCn, normalizeElement } from "./vocab";
import type { ElementCountsData } from "../types/tianze";

export function elementRows(counts?: ElementCountsData | null) {
  const entries = Object.entries(counts?.elements ?? {}).map(([key, value]) =>
    [normalizeElement(key), value] as const);
  const byElement = new Map(entries);
  return ELEMENT_ORDER.flatMap(key => {
    const value = byElement.get(key);
    if (!value || !Number.isFinite(value.visible) || !Number.isFinite(value.hidden)) return [];
    return [{ key, cn: elementCn(key), ...value, total: value.visible + value.hidden }];
  });
}

export function summarizeElements(rows: ReturnType<typeof elementRows>) {
  if (rows.length !== ELEMENT_ORDER.length) return null;
  const totals = rows.map(row => row.total);
  const max = Math.max(...totals);
  const min = Math.min(...totals);
  const names = (total: number) => rows.filter(row => row.total === total).map(row => row.cn).join("、");
  return max === min ? `五行显干与藏干计数相同，各 ${max} 处。`
    : `按显干与藏干合计，${names(max)}最多（${max} 处），${names(min)}最少（${min} 处）。`;
}
