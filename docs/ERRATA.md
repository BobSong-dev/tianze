# Tianze 勘误与上游缺陷清单（ERRATA）

> bazi-atlas 把 methodology/corrections 放站外的教训：本文件是**仓内一等文档**。发现上游缺陷或本仓库错误，在此登记；修复后保留条目并注明状态。

## 上游缺陷（影响 Tianze 使用方式）

| # | 对象 | 缺陷 | Tianze 对策 | 状态 |
|---|---|---|---|---|
| ERRATA-01 | lunar-python | sect=2 时时柱日干仍按次日日干五鼠遁（Lunar.py:177），源码无注释 | 固化为 R1 补充口径 + fixture 锁定（late_zi_sect1/2 成对） | OPEN（口径已采纳，出处待向 6tail 求证） |
| ERRATA-02 | lunar-python | `getYun()` 对 23 点出生归亥时（bazi-atlas 发现的公开分歧） | 大运相关测试避开 23 点档；后续引入独立起运计算 | OPEN |
| ERRATA-03 | lunar-python | 宜忌/日神煞数据为无出处 hex 串 | 不使用该部分 | CLOSED（规避） |
| ERRATA-04 | jiwenxu 藏干表 | 丑支中气/余气作 辛/癸（与通行 癸/辛 相反，作者注"修正记录"） | Tianze 取通行序（R8），与 lunar/Atlas 一致；分歧记录 | CLOSED（选型） |
| ERRATA-05 | 本仓库 | 中国 DST 窗口表（R12）待逐条核对国务院通告原文 | fixture 避开 DST 边界分钟级；表标 needs-verification | OPEN |
| ERRATA-06 | Erfix404 引擎 | 日柱锚点 `_DAY_ANCHOR_JDN=2433180` 实为 1949-09-20（+11 天）；`term_crossing_jd` 恒返 ±40 天 | 其代码一概不参考；crosscheck 日柱锚点用 `2433191`（三锚点实算验证） | CLOSED（规避） |
| ERRATA-07 | lunar-python | 节气表 key 拼音/中文混用（DA_XUE/冬至/DONG_ZHI…） | 适配层做名称归一化（`_normalize_jieqi_name`） | CLOSED |

## 本仓库错误记录

（暂无——发现即登记，修复必留守卫 fixture。）
