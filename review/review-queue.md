# Tianze Review Queue

- total items: 424
- stats: {'ocrRisk': 163, 'machineCurated': 216, 'sensitiveClaims': 38, 'ruleConflicts': 7}

## 分区

### ocrRiskRules（163）

- {"id": "DTZ-04", "book": "DTZ", "title": "阳干从气不从势，阴干从势无情义"}
- {"id": "DTZ-05", "book": "DTZ", "title": "阳干虽弱不从势——韩复榘（绝处逢生）、虞洽卿（不能从煞）、施再邨（气绝不从）"}
- {"id": "DTZ-06", "book": "DTZ", "title": "伍庭芳（己土从木）与许世英（乙木反不能从）之辨"}
- {"id": "DTZ-07", "book": "DTZ", "title": "甲木参天，脱胎要火——春不容金，秋不容土；火炽乘龙，水汤骑虎"}
- {"id": "DTZ-08", "book": "DTZ", "title": "乙木虽柔，封羊解牛——怀丁抱丙，跨凤乘猴；虚湿之地骑马亦忧；藤萝系甲可春可秋"}
- {"id": "DTZ-09", "book": "DTZ", "title": "支神只以冲为重，刑与穿兮动不动——三刑逢冲为祸甚烈"}
- {"id": "DTZ-11", "book": "DTZ", "title": "旺者冲衰衰者拔，衰神冲旺旺者发（旺衰以全局气势言）"}
- {"id": "DTZ-13", "book": "DTZ", "title": "土居中央寄于四隅——寅申巳亥同藏戊土，午藏己土；亥子之土名存实亡"}
- …（其余 155 条见 JSON）

### machineCuratedRules（216）

- {"id": "EV-CAR-01", "domain": "event", "label": "官星透岁运+官杀主题增强", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出事件
- {"id": "EV-CAR-02", "domain": "event", "label": "官印相生（印化官杀）", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出事件断言
- {"id": "EV-CAR-03", "domain": "event", "label": "伤官见官（岁运伤官克官）", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出事件
- {"id": "EV-WEA-01", "domain": "event", "label": "财星透岁运+财主题增强", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出事件断
- {"id": "EV-WEA-02", "domain": "event", "label": "刃头财/比劫夺财（因财启争）", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出
- {"id": "EV-WEA-03", "domain": "event", "label": "财库逢冲（两说并存）", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出事件断言
- {"id": "EV-REL-01", "domain": "event", "label": "夫妻宫（日支）逢岁运六合", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出事件
- {"id": "EV-REL-02", "domain": "event", "label": "夫妻宫逢冲/夫星逢冲", "method": "ai_curation", "note": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；升级需真人对照扫描件；效果只输出主题方向，不输出事件断言
- …（其余 208 条见 JSON）

### sensitiveClaims（38）

- {"caseId": "CASE-QBTM-丁-37", "text": "位至招商局督办；庚午年遭暗杀；原书生辰标注「光绪十三年闰四月初十日辰时」。", "keywords": ["杀"]}
- {"caseId": "CASE-QBTM-丁-44", "text": "名垂青史；行巳运尽节而死。", "keywords": ["死"]}
- {"caseId": "CASE-QBTM-丁-67", "text": "位居北洋总督；贵为总统；丙辰年卒，年五十八；原书生辰标注「咸丰九年八月廿日未时」。", "keywords": ["卒"]}
- {"caseId": "CASE-QBTM-丁-83", "text": "原书断大富，入午运即死。", "keywords": ["死"]}
- {"caseId": "CASE-QBTM-丁-93", "text": "原书载「甲运大发，午运败家丧家，未运死」。", "keywords": ["死"]}
- {"caseId": "CASE-QBTM-丁-103", "text": "原书断「无庚虽富而夭」。", "keywords": ["夭"]}
- {"caseId": "CASE-QBTM-戊-03", "text": "癸运夭折", "keywords": ["夭"]}
- {"caseId": "CASE-QBTM-戊-26", "text": "位至总长；戊运己卯年元旦被刺殒命", "keywords": ["刺"]}
- …（其余 30 条见 JSON）

### ruleConflicts（7）

- {"source": "event", "rules": ["EV-CAR-01", "EV-CAR-03"], "resolution": "specific-over-general", "note": "无救应条件时回落 keep-both：DTZ-39「可见/不可见」之辨需察财印有无"}
- {"source": "event", "rules": ["EV-WEA-01", "EV-WEA-02"], "resolution": "specific-over-general", "note": "无强度条件时回落 keep-both：SS-R10「须察其配合，非可一例以推」"}
- {"source": "event", "rules": ["EV-REL-02", "EV-REL-03"], "resolution": "keep-both", "note": "MLD-18：配偶星临岁运（support）与夫妻宫逢冲（oppose）可同时成立；原文并注明「离婚非不可避免事」，方向相反只表示主题
- {"source": "event", "rules": ["EV-CON-01", "EV-WEA-02"], "resolution": "no-adjudication", "note": "special_pattern 视角（从格顺势/破格两说）与 traditional 视角（比劫夺财）方向相反时属流派差异
- {"source": "tiaohou", "rules": ["QBT-甲-07", "QBT-甲-06"], "resolution": "specific-over-general", "note": "QBT-甲-06（五六月合论）与 QBT-甲-07（六月专论）覆盖重叠：specific-over-gener
- {"source": "tiaohou", "rules": ["QBT-甲-07", "QBT-甲-06"], "resolution": "specific-over-general", "note": "QBT-甲-06（五六月合论）与 QBT-甲-07（六月专论）覆盖重叠：specific-over-gener
- {"source": "tiaohou", "rules": ["QBT-己-10"], "resolution": "specific-over-general", "note": "标题'以丙为主要'与正文'先透癸次透丙'两说并存：从正文"}

### unresolved（2）

- {"kind": "tiaohou_coverage", "detail": "调候 120 格全覆盖（0 UNRESOLVED）——若未来知识库扩展出现缺口会在此登记"}
- {"kind": "event_unresolved_rate", "detail": "Event 主题 UNRESOLVED 率（探针）：{'multi_view_agree': 0.0, 'multi_view_conflict': 0.0, 'shensha_only': 0.0, 'unknown_hour'

