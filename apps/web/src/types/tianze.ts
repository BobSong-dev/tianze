// ---- Tianze API Types (hand-maintained, aligned with SDK SimplifiedResult) ----

export interface PillarData {
  stem: string;
  branch: string;
  stemElement: string;
  stemYinYang: string;
  branchElement: string;
  branchYinYang: string;
  hiddenStems: { stem: string; role: string; element: string; yinYang: string; tenGod: string }[];
  tenGod: string | null;
  naYin: string;
  changSheng: string | null;
  xunKong: string | null;
  position: string;
}

export interface RelationData {
  kind: string;
  label: string;
  members: string[];
  positions: string[];
  adjacency: string | null;
  monthInvolved: boolean;
  transformCandidate: string | null;
  subType: string | null;
  note: string | null;
  conventionId: string;
}

export interface RootData {
  stem: string; branch: string; hiddenStem: string;
  rootType: string; depth: string; position: string;
  isMonthRoot: boolean; isDayMaster: boolean; statement: string;
}

export interface VisibilityData {
  hiddenStem: string; visibleStem: string; position: string;
  sourceBranch: string; sourceRole: string; sourcePosition: string;
  distance: number; monthRelated: boolean; dayMasterRelated: boolean; statement: string;
}

export interface MonthCommandData {
  monthBranch: string; season: string; element: string; yinYang: string;
  mainQi: { stem: string; role: string; transparent: boolean } | null;
  hiddenStemPriority: { stem: string; role: string; transparent: boolean }[];
  dayMaster: string;
  relationToDayMaster: { state: string; inCommand: boolean; rule: string };
  evidence: string[];
}

export interface ElementCountsData {
  elements: Record<string, { visible: number; hidden: number }>;
  stems: Record<string, number>;
  branches: Record<string, number>;
  hiddenStems: Record<string, number>;
  missing: string[];
}

export interface StrengthMethodResult {
  analyzerId: string; name: string;
  verdict: string | null; score: number | null;
  params: Record<string, unknown> | null;
  contributions: { factor: string; effect: string; value: number; reason: string }[] | null;
  provenance: { level: string; project: string | null; concept: string; note: string | null }[] | null;
  confidence: string | null;
  strengthEvidence: {
    deLing: { result: boolean; reason: string[] };
    deDi: { result: boolean; reason: string[] };
    deShi: { result: boolean; reason: string[] };
  } | null;
  supportEvidence: string[] | null;
  drainEvidence: string[] | null;
  evidence: string[];
  note: string | null;
}

export interface StrengthReport {
  methods: StrengthMethodResult[];
  agreement: string | null;
  note: string;
}

export interface PatternCandidate {
  name: string; category: string; monthBranch: string; sourceStem: string;
  tenGod: string; via: string; evidence: string[];
  provenance: { level: string; project: string | null; concept: string; note: string | null }[];
}

export interface PatternEvaluation {
  candidate: PatternCandidate;
  supports: PatternFactor[];
  damages: PatternFactor[];
  rescues: PatternFactor[];
  conflicts: PatternFactor[];
  status: string;
  note: string | null;
}

export interface PatternFactor {
  kind: string; ruleId: string; name: string; detail: string;
  provenance: { level: string; project: string | null; concept: string; note: string | null };
  related: string[];
}

export interface PatternAnalysis {
  candidates: PatternCandidate[];
  primaryIndex: number | null;
  evaluation: PatternEvaluation | null;
  note: string | null;
}

export interface TiaoHouRecommendation {
  targetStem: string; element: string; priority: string;
  present: boolean; positions: string[];
  ruleIds: string[];
  provenance: { level: string; project: string | null; concept: string; note: string | null }[];
  quality: string | null;
  quote: string | null;
  source: { book: string; chapter: string | null; pages: number[]; sourceKind: string; commentator: string | null } | null;
}

export interface TiaoHouResult {
  dayMaster: string; monthBranch: string; resolved: boolean;
  recommendations: TiaoHouRecommendation[];
  evidence: string[]; conflicts: string[];
  conditions: Record<string, unknown>[]; exceptions: Record<string, unknown>[];
  ruleIds: string[]; note: string | null;
}

export interface AdvancedAnalysis {
  specialPattern: {
    cong: { type: string; school: string; status: string; prerequisites: string[];
            supports: { kind: string; ruleId: string; text: string }[];
            blockers: { kind: string; ruleId: string; text: string }[];
            conflicts: { kind: string; ruleId: string; text: string }[];
            schoolVariants: Record<string, string>;
            provenance: { level: string; concept: string }[];
          }[];
    zhuanwang: { type: string; status: string; supports: unknown[]; blockers: unknown[]; schoolVariants: Record<string, string> }[];
    transformation: { stemPair: string[]; targetElement: string; status: string;
                      seasonSupport: boolean | null; obstructions: string[] }[];
  };
  bingYao: { problems: { type: string; target: string; evidence: string[] }[];
             medicines: { problem: string; kind: string; target: string; evidence: string[] }[] };
  tongGuan: { conflictPairs: { conflict: { from: string; to: string }; evidence: string[] }[];
              bridges: { conflict: { from: string; to: string }; bridge: string; present: boolean; evidence: string[] }[] };
}

export interface AnalyzeResponse {
  meta: { engineVersion: string; engineStage: string; analysisSchemaVersion: string;
          knowledgeSchemaVersion: string; caseSchemaVersion: string; lunarPythonVersion: string };
  pillars: { year: PillarData; month: PillarData; day: PillarData; hour?: PillarData };
  dayMaster: { stem: string; element: string; yinYang: string };
  relations: RelationData[];
  roots: RootData[];
  visibility: VisibilityData[];
  monthCommand: MonthCommandData | null;
  elementCounts: ElementCountsData | null;
  strength: StrengthReport | null;
  pattern: PatternAnalysis | null;
  tiaohou: TiaoHouResult | null;
  advancedAnalysis: AdvancedAnalysis | null;
  specialPoints: { taiYuan: string; mingGong: string | null; shenGong: string | null } | null;
  luck: unknown;
  conventions: Record<string, string>;
  warnings: string[];
  fallbacks: string[];
  missingCapabilities: string[];
}

export interface MetaResponse {
  engineVersion: string; apiVersion: string; analysisSchemaVersion: string;
  knowledgeSchemaVersion: string; caseSchemaVersion: string;
  supportedStrengthMethods: string[]; supportedAnalysisModules: string[]; supportedConventions: string[];
}

export interface ApiError {
  error: { code: string; message: string; details: Record<string, unknown> };
}
