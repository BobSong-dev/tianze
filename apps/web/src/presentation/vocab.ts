/**
 * Tianze · 受控状态词汇表（前端展示层）
 *
 * 纪律：本文件**只做 code → 中文标签的映射**，不新增、不推断、不改写后端语义。
 * 每个状态的原码都通过 <StatusBadge> 的 title 悬停保留，便于核对。
 * 后端返回未收录的 code 时，原样显示 code 本身（不猜测含义）。
 */

export interface StatusMeta {
  /** 中文受控词（原码在 title 中保留） */
  label: string;
  /** 语义分组，用于配色；不代表优先级或确定性升级 */
  tone: string;
  /** 该状态的边界说明（来自既有术语表，措辞不改） */
  hint?: string;
}

export const STATUS_MAP: Record<string, StatusMeta> = {
  // 候选与确定性阶梯
  CANDIDATE: { label: '候选', tone: 'candidate', hint: '满足部分结构条件，需进一步复核，不是结论。' },
  LIKELY: { label: '倾向支持', tone: 'likely', hint: '支持证据占优，仍非确定性结论。' },
  DISPUTED: { label: '两说并存', tone: 'disputed', hint: '方法或流派存在分歧，两说并列，不裁决。' },
  BLOCKED: { label: '阻断', tone: 'blocked', hint: '存在明确阻断条件，该结构不成立。' },
  UNRESOLVED: { label: '待定', tone: 'unresolved', hint: '证据不足，无法判定。' },
  ESTABLISHED: { label: '已确立', tone: 'established', hint: '结构事实层：条件已由引擎核实成立。' },
  EXPERIMENTAL: { label: '实验性', tone: 'experimental', hint: '岁运参与该计算存在流派分歧，仅作参考。' },
  SUPPORTED: { label: '受支持', tone: 'supported', hint: '在当前上下文中有支撑依据。' },

  // 证据在场性
  PRESENT: { label: '在场', tone: 'supported' },
  MISSING: { label: '缺', tone: 'unresolved' },

  // 一致性（多方法/多体系）
  AGREED: { label: '各方法一致', tone: 'supported' },
  PARTIAL: { label: '部分一致', tone: 'disputed' },
  DISAGREED: { label: '存在分歧', tone: 'disputed' },
  CONFLICT: { label: '多体系冲突', tone: 'disputed' },
  HIGH: { label: '多体系一致', tone: 'supported' },

  // 严重度
  FATAL: { label: '严重', tone: 'blocked' },
  WARNING: { label: '警告', tone: 'disputed' },
  INFO: { label: '提示', tone: 'unresolved' },
};

/** 证据来源层级（VIEW） */
export const VIEW_MAP: Record<string, string> = {
  CLASSICAL_EXPLICIT: '古籍明言',
  CLASSICAL_IMPLICIT: '古籍隐含',
  PROJECT_REFERENCE: '项目参考',
  ENGINEERING_HEURISTIC: '工程启发',
  TIANZE_NORMALIZATION: '天泽结构归一',
};

/** 溯源层级（provenanceLevels） */
export const PROVENANCE_MAP: Record<string, string> = {
  CLASSICAL_EXPLICIT: '古籍明言',
  CLASSICAL_IMPLICIT: '古籍隐含',
  PROJECT_REFERENCE: '项目参考',
  ENGINEERING_HEURISTIC: '工程启发',
  TIANZE_NORMALIZATION: '天泽结构归一',
};

/** Temporal Delta 变化种类 */
export const DELTA_KIND_MAP: Record<string, string> = {
  added: '新出现',
  removed: '消失',
  strengthened: '增强',
  weakened: '减弱',
  status_changed: '状态改变',
  blocked: '被阻断',
  unblocked: '解除 / 到位',
  disagreement_changed: '一致性变化',
};

/** 回放层级 */
export const LAYER_MAP: Record<string, string> = {
  natal: '原局',
  luck: '大运',
  annual: '流年',
  monthly: '流月',
  daily: '流日',
};

/** 五行 / 阴阳 */
export const ELEMENT_CN: Record<string, string> = {
  WOOD: '木', FIRE: '火', EARTH: '土', METAL: '金', WATER: '水',
};

export const YINYANG_CN: Record<string, string> = { YIN: '阴', YANG: '阳' };

export const ELEMENT_VAR: Record<string, string> = {
  WOOD: 'var(--wx-wood)', FIRE: 'var(--wx-fire)', EARTH: 'var(--wx-earth)',
  METAL: 'var(--wx-metal)', WATER: 'var(--wx-water)',
};

export const ELEMENT_BG_VAR: Record<string, string> = {
  WOOD: 'var(--wx-wood-bg)', FIRE: 'var(--wx-fire-bg)', EARTH: 'var(--wx-earth-bg)',
  METAL: 'var(--wx-metal-bg)', WATER: 'var(--wx-water-bg)',
};

/**
 * 五行键归一化。
 * 引擎在不同位置给出的大小写并不一致（`elementCounts.elements` 用小写
 * `wood`，`pillar.stemElement` 用大写 `WOOD`），前端统一归一为**大写**后再查表。
 * 这是**键名归一**，不是语义映射：无法识别的键原样返回并落到兜底样式。
 */
export const ELEMENT_ORDER = ['WOOD', 'FIRE', 'EARTH', 'METAL', 'WATER'] as const;

export function normalizeElement(el?: string | null): string {
  return (el ?? '').toUpperCase();
}

/** 五行/阴阳的展示名（兼容大小写，未知值原样返回） */
export function elementCn(el?: string | null): string {
  const k = normalizeElement(el);
  return ELEMENT_CN[k] ?? el ?? '';
}

export function yinYangCn(v?: string | null): string {
  const k = normalizeElement(v);
  return YINYANG_CN[k] ?? v ?? '';
}

export function elementVar(el?: string | null): string {
  return ELEMENT_VAR[normalizeElement(el)] ?? 'var(--bronze-600)';
}

export const SEASON_CN: Record<string, string> = {
  spring: '春', summer: '夏', autumn: '秋', winter: '冬',
};

/** 季节展示名（兼容大小写，未知值原样返回） */
export function seasonCn(v?: string | null): string {
  const k = (v ?? '').toLowerCase();
  return SEASON_CN[k] ?? v ?? '';
}

/** 结构强度分析器（analyzerId → 展示名 + 原码） */
export const ANALYZER_MAP: Record<string, { cn: string; method: string }> = {
  dimensional_v1: { cn: '得令 · 得地 · 得势', method: 'dimension' },
  'weighted-v1': { cn: '加权计分', method: 'weighted' },
  'fuyi-v1': { cn: '扶抑取用', method: 'fuyi' },
};

/** 柱位 */
export const POSITION_CN: Record<string, string> = {
  year: '年柱', month: '月柱', day: '日柱', hour: '时柱',
};

/** 关系类型 → 图形语义分组（仅决定线条配色，不改变关系含义） */
export function relationTone(kind: string): 'harmony' | 'clash' | 'punish' | 'plain' {
  const k = (kind || '').toUpperCase();
  if (k.includes('COMBINATION') || k.includes('HARMONY') || k.includes('HE')) return 'harmony';
  if (k.includes('CLASH') || k.includes('CHONG') || k.includes('BREAK') || k.includes('PO')) return 'clash';
  if (k.includes('PUNISH') || k.includes('XING') || k.includes('HARM') || k.includes('HAI')) return 'punish';
  return 'plain';
}

export function codeCn(map: Record<string, string>, code?: string | null): string {
  if (!code) return '';
  return map[code] ?? code;
}

/** 状态元数据：未知 code 原样透传，tone 回落 neutral */
export function statusMeta(code?: string | null): StatusMeta {
  if (!code) return { label: '', tone: 'unresolved' };
  return STATUS_MAP[code] ?? { label: code, tone: 'unresolved' };
}
