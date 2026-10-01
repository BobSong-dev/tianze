# 04 · 许可证审计（LICENSE AUDIT）

> Phase 0 产出 · 2026-09-30。所有 License 结论均来自克隆仓库内 LICENSE 文件原文（非 README 转述）；OBE 经全库 find+grep 核查确认无任何许可证痕迹；Erfix 的日柱 bug 与许可无关但影响复用定性。
> 标签：`SAFE_TO_DEPEND`（可作依赖）· `SAFE_TO_REFERENCE`（可参考思路，重写实现）· `COPY_WITH_LICENSE`（可复制，须保留版权与许可声明）· `COPY_RESTRICTED`（受限复制）· `UNKNOWN_LICENSE`（禁止复制）。

## 1. 审计总表

| Project | License | Can depend | Can copy | Can modify | Attribution 义务 | 标签 | Notes |
|---|---|---|---|---|---|---|---|
| 6tail/lunar-python | MIT (©2020 6tail, LICENSE:1-3) | ✅ pip | ✅ | ✅ | 保留 LICENSE 与版权声明 | **SAFE_TO_DEPEND** | Tianze 历法层主依赖 |
| 6tail/lunar-javascript | MIT（npm 包，6tail/lunar 生态） | ✅ npm | ✅ | ✅ | 同上 | **SAFE_TO_DEPEND** | 生态经 git ls-remote 验证存在；作 TS/差分验证备用 |
| 6tail/lunar-java | MIT（同上） | ✅ | ✅ | ✅ | 同上 | SAFE_TO_DEPEND | 未来 Java 业务后端可复用同一口径 |
| bazi-atlas/bazi-engine | MIT (©2026 雷志锋/hawkinglei, LICENSE:3) | ✅（engine.mjs） | ✅（定表/短公式） | ✅ | 保留版权声明 | **SAFE_TO_DEPEND**（引擎本体）/ **SAFE_TO_REFERENCE**（验证架构）/ COPY_WITH_LICENSE（干支纳音藏干表、JDN 公式、五虎遁五时遁、立春表） | 定表本身多为公共领域传统内容，稳妥做法是自录 + 保留声明 |
| lymcho/open-bazi-engine | **无（全库核查零命中：无 LICENSE/COPYING/NOTICE 文件，README/源码无任何 license/copyright 字样）** | ❌ | ❌ | ❌ | — | **UNKNOWN_LICENSE** | 默认著作权保留。只能学思想（分层、类型形状、rationale、金测法），**不得复制任何 .py/.json/prompt 文本**。可联系作者请求补 MIT |
| ruanxiaoer888/bazi-engine — 代码轨 | MIT (©2026 ruanxiaoer, LICENSE) | ✅ | ✅ | ✅ | 保留声明 | **COPY_WITH_LICENSE** | engine.dist.js / tools / skill 结构可复用 |
| ruanxiaoer888/bazi-engine — 数据轨 | **CC BY-NC-SA 4.0**（LICENSE-DATA，覆盖 kb/ 全部及 UI 内嵌断语） | ✅（非商业） | ✅（非商业） | ✅ | ①署名 "bazi-engine · ruanxiaoer"；②注明修改；③**断语逐条保留 source 字段，不得删改**；④衍生数据整体以 **CC BY-NC-SA 4.0** 再发布（SA 传染） | **COPY_RESTRICTED** | Tianze 明确非商业 → 可用但义务重；README 自称内嵌防盗用水印句（扫描未定位，提取需人工排查）；作者自认 ClawHub MIT-0 展示与 NC 冲突是未决风险 |
| jiwenxu025-boop/bazi-engine | MIT (©2026 jiwenxu025-boop, LICENSE:3) | ✅ | ✅ | ✅ | 保留声明 | **SAFE_TO_DEPEND** | 治理模式（provenance/EvidenceItem/decision_policy）SAFE_TO_REFERENCE |
| Erfix404/bazi-engine | MIT (©2026 Erfan Ashouri, LICENSE:3) | ⚠️ 技术上可但**不应**（日柱 +11 天、起运退化、测试全自引用） | ✅（Meeus Ch.25 公式段） | ✅ | 保留声明 | **SAFE_TO_REFERENCE**（仅节气/黄经域）；日柱/时柱/大运域排除 | 公式 ~20 行可移植为独立 oracle；`term_crossing_jd` 一行都不要带 |
| Horace-Maxwell/Horosa | **AGPL-3.0-only**（LICENSE 全文 + CITATION.cff:13） | ❌ | ❌ | ❌ | — | **COPY_RESTRICTED**（实质：只学思想） | 主项目含 Swiss Ephemeris（AGPL）传染 + 作者自愿；Tianze 不采用 AGPL 前**禁止复制/改编任何源码**（含 9 个 bazi*.js）；其 vendored 上游另论 |
| Horosa 内 vendored 库 | lunar-javascript ^1.7.7 = MIT；kentang2017 系（太乙/金口诀/奇门等）= MIT；flatlib fork = MIT；pdf-lib/dom-align = MIT；Noto Sans CJK = OFL-1.1；d3-celestial 数据 = BSD-3；taixuanshifa/jingjue/shenyishu = **无明确 License**；Swiss Ephemeris = AGPL | — | — | — | 各依其许可 | MIT 项 **SAFE_TO_DEPEND（直接依赖原项目，绕开 Horosa）**；无 License 项禁用；THIRD_PARTY_NOTICES.md 是 vendor 合规模范 | 关键结论：Horosa 的历法底座 lunar-javascript 本身是 MIT，Tianze 可直接用 |
| 古籍原文（穷通宝鉴/子平真诠/滴天髓/三命通会/渊海子平等） | 公有领域 | ✅ | ✅ | ✅ | 建议仍标注版本源 | **SAFE_TO_DEPEND（数据）** | ruan LICENSE-DATA 亦确认古籍原文公有领域；Tianze 自建结构化数据的最优来源 |

## 2. 组合风险提示

1. **SA 传染隔离**：若 Tianze 使用 ruan 的 CC BY-NC-SA 数据，衍生知识库必须整体同许可发布。若 Tianze 希望核心数据保持最开放许可（建议如此），必须把 CC 数据放在**独立、明确标注的数据层目录**（如 `rules/derived/cc-by-nc-sa/`），与自建公有领域数据物理分离，不互相混写。
2. **AGPL 隔离**：研究 Horosa 期间的笔记（research/notes/horosa.md）只含算法描述与常数值等事实性内容，不含连续代码——这是合规边界。未来任何 Tianze 代码不得与 Horosa 源码"结构雷同的翻译/改写"。
3. **OBE 零容忍**：UNKNOWN 许可下连"抄一段改一改"都不行；本研究的 OBE 笔记全部为思想/事实级描述。
4. **Tianze 自身发布策略**（建议，见 ADR-008）：代码 MIT；数据分层——`rules/classical/`（公有领域古籍结构化，可 MIT/CC0）+ `rules/derived/`（如引入 ruan 数据则整层 CC BY-NC-SA 4.0 并在 SOURCES 声明）。每条规则携带 `source` 字段（open_source / classic / project_heuristic 三型）作为**许可义务的技术载体**。

## 3. 引用清单（docs/SOURCES.md 的种子）

- 6tail/lunar-python — https://github.com/6tail/lunar-python — MIT — Calendar/FourPillars/DaYun
- 6tail/lunar-javascript — https://github.com/6tail/lunar-javascript — MIT — 第二历法 oracle 候选
- bazi-atlas/bazi-engine — https://github.com/bazi-atlas/bazi-engine — MIT — 验证体系参照
- lymcho/open-bazi-engine — https://github.com/lymcho/open-bazi-engine — 无 License — 仅思想参照
- ruanxiaoer888/bazi-engine — https://github.com/ruanxiaoer888/bazi-engine — MIT(code)/CC BY-NC-SA 4.0(data) — KB schema 与质检参照
- jiwenxu025-boop/bazi-engine — https://github.com/jiwenxu025-boop/bazi-engine — MIT — 算法与治理参照
- Erfix404/bazi-engine — https://github.com/Erfix404/bazi-engine — MIT — 节气第二 oracle（限年/月柱域）
- Horace-Maxwell/Horosa-… — https://github.com/Horace-Maxwell/Horosa-Web-App-comprehensively-improved-Windows — AGPL-3.0 — 架构思想参照（禁复制）
- 《穷通宝鉴》《子平真诠》《滴天髓》《三命通会》《渊海子平》 — 公有领域 — 规则与调候数据原文来源
