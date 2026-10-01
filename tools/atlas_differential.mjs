// bazi-atlas 差分对拍桥（M5 Differential Testing）。
// 用途：实际运行 research/upstream/bazi-atlas/engine.mjs（MIT），对若干公共命例
// 输出四柱 JSON，与 Tianze 主引擎对拍。不复制其代码，仅调用其公开入口。
// 用法：node tools/atlas_differential.mjs
// 输出：JSON 数组 [{name, birth, atlasPillars}]
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..");
const atlasPath = path.join(repoRoot, "research", "upstream", "bazi-atlas", "engine.mjs");

const require = createRequire(import.meta.url);
const { pathToFileURL } = await import("node:url");
const atlas = await import(pathToFileURL(atlasPath).href);

const CASES = [
  { name: "plan_example_2003", birth: { year: 2003, month: 8, day: 18, hour: 14, minute: 30, tzOffsetHours: 8, sect: 2 } },
  { name: "basic_1986", birth: { year: 1986, month: 4, day: 21, hour: 10, minute: 0, tzOffsetHours: 8, sect: 2 } },
  { name: "female_1983", birth: { year: 1983, month: 2, day: 15, hour: 20, minute: 0, tzOffsetHours: 8, sect: 2 } },
  { name: "late_zi_1986_sect2", birth: { year: 1986, month: 4, day: 21, hour: 23, minute: 30, tzOffsetHours: 8, sect: 2 } },
  { name: "lichun_2024_after", birth: { year: 2024, month: 2, day: 4, hour: 18, minute: 0, tzOffsetHours: 8, sect: 2 } },
];

const out = [];
for (const c of CASES) {
  const r = atlas.computeBazi(c.birth);
  out.push({
    name: c.name,
    birth: c.birth,
    atlasPillars: {
      year: r.pillars.year.ganzhi,
      month: r.pillars.month.ganzhi,
      day: r.pillars.day.ganzhi,
      hour: r.pillars.time ? r.pillars.time.ganzhi : null,
    },
  });
}
console.log(JSON.stringify(out, null, 2));
