# Tianze 来源声明（SOURCES）

> 许可义务的技术载体。任何从上游借来的表/公式/思想都在此登记；每条规则的机器可查出处见 `SourceReference`（`type: classic / open_source / project_heuristic / tianze_original`）。

## 直接依赖（DEPEND）

| 项目 | 用途 | License | 仓库 |
|---|---|---|---|
| lunar-python 1.4.8 | 历法/节气/四柱/藏干/纳音/十二长生/旬空/胎元/大运底座 | MIT (©2020 6tail) | https://github.com/6tail/lunar-python |
| pydantic | 数据契约 | MIT | https://github.com/pydantic/pydantic |

注：差分对拍时以 `npm install --no-save` 为 research/upstream/bazi-atlas 安装
lunar-javascript@1.7.7（MIT）至其 node_modules——不改上游任何被跟踪文件，
该目录本就不入库。

## 参考项目（研究期克隆于 `research/upstream/`，均只读）

| 项目 | 借鉴内容 | License | 本仓库对应文档 |
|---|---|---|---|
| bazi-atlas/bazi-engine | 验证体系（对拍/盖章/守恒律/守卫 fixture/R 约定模式）；双轨道时间；DST 处理的问题定义；weighted/fuyi/取格默认参数出处；**跨引擎差分对拍实跑对象**（tools/atlas_differential.mjs 仅调用其公开入口 computeBazi，5 命例四柱一致） | MIT | docs/research/07-BORROWING-MATRIX.md |
| jiwenxu025-boop/bazi-engine | 边界警告、EvidenceItem 概念、provenance 分级、反例测试模式 | MIT | 同上 |
| ruanxiaoer888/bazi-engine | 规则 schema 与质检方法论（**其 CC BY-NC-SA 数据本仓库未使用**） | 代码 MIT / 数据 CC BY-NC-SA 4.0 | 同上 |
| lymcho/open-bazi-engine | 架构思想（分层/Interaction 形状/rationale）——**无 License，未复制任何代码或表** | UNKNOWN | docs/research/04-LICENSE-AUDIT.md |
| Erfix404/bazi-engine | Meeus Ch.25 黄经公式思路（tests/crosscheck 自写重实现，仅限年/月柱域；其日柱代码有 +11 天 bug，未参考） | MIT | 同上 |
| Horace-Maxwell/Horosa-… | 多流派解释器/事实-视角分离/诚实元数据等**思想**（AGPL，未复制任何源码） | AGPL-3.0 | 同上 |

## 数据来源

| 数据 | 来源 | 许可 |
|---|---|---|
| **调候规则 182 条（knowledge/rules/tiaohou/）** | 用户提供的徐乐吾八字知识库（_知识库.zip，穷通宝鉴评注逐月规则，PDF 页码定位）——古籍原文层为公有领域，徐注层注明出处；raw/ 不入库（ADR-026） | 引用范围：结构化规则+短引文+页码 |
| 调候交叉参考 | ruan shigan-lun（DATA_CROSSCHECK）、SOP 附表B（现代汇编，仅参考） | — |

| 数据 | 来源 | 许可 |
|---|---|---|
| 藏干表/十神关系/纳音/十二长生/合冲刑害破/三合三会 | 传统命理公共内容（通行子平口径），逐值与 lunar-python 表对账 | 公有领域内容；对账代码 MIT |
| 中国夏令时窗口表（1986-1991） | 国务院夏时制通告（多源一致；与 bazi-atlas 同源口径） | 公共事实，标记 needs-verification |
| （未来）调候 120 组 | 《穷通宝鉴》原文自录 | 公有领域原文 + Tianze 结构化 |

## M8 特殊格局规则来源

| 规则 | 来源 | 级别 |
|---|---|---|
| 从格反条件（有根不从） | jiwenxu yongshen.py | PROJECT_REFERENCE |
| 从格/专旺阈值 | Horosa baziGejuYongShen | PROJECT_REFERENCE |
| 专旺五格划分 | ruan build_ui | PROJECT_REFERENCE |
| 候选阈值/状态映射 | Tianze | ENGINEERING_HEURISTIC |
| 化气框架 | jiwenxu HUA_QI_CONDITIONS（概念） | PROJECT_REFERENCE |
| 通关元素图 | Tianze 五行生克图 | ENGINEERING_HEURISTIC |

## 古籍（规则层引用目标）

《子平真诠》《穷通宝鉴》《滴天髓》《三命通会》《渊海子平》——公有领域；Tianze 引用时标注书名与篇名，不逐字搬运现代校注本。
