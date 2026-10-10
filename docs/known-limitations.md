# Tianze 已知限制（v0.4.0）

按处理方式分三类（详见发布判定报告）。

## EXTERNAL_BLOCKED（需外部条件，不影响受限发布）

| 项 | 缺失条件 | 影响 |
|---|---|---|
| raw OCR 原文核对 | 知识库 zip 未入库（556/556 sourceFile 缺失，路径/页码可回溯） | 引文经 MACHINE_CURATED 归一化，原文逐字核对未做（source_coverage status=BLOCKED） |
| 子邀巳（ZP-11） | OCR 残缺（取印为用口径）+ 泛化 ~27% | 不落地引擎；保留引文注册表 |
| 争合条件化变体（见辰化合/破干从化） | 需辰/破干条件引文核验 | 注记保留，不判定 |
| 命例流年层回放 | 年锚多解（60 年周期，4 例 ×10 候选） | 只回放 natal→大运两层 |
| 真实 Provider AI 评测 | 无 API Key | mock 评测全绿；真实成绩不伪造 |
| 三平台 CI 实跑 / GitHub Release / push | 远端权限 | 配置就绪（CI 矩阵 yml），未执行不称已验证 |
| 跨浏览器打印实测 | 需真实浏览器环境 | Chromium E2E 已过；Safari/Firefox NOT_TESTED |

## PARTIAL（功能可用，边界已知）

- 真太阳时：支持 clock/true_solar/mean_solar；精度依赖用户提供经度。
- 空亡作用位置：表+差分已落地，仅消费于贵人三要件（泛化待引文）。
- 化气岁运：真化条件/所忌/泄气覆盖；月令置换类口径 UNSUPPORTED。
- 暗冲格外格（飞天禄马/井栏叉/刑合）：候选 + 两说（外格说 vs 伤官变格说）。
- 争合：家族计数（一侧 ≥2）落地；妒合无独立引文，并入争合两说。

## UNSUPPORTED（明确不做）

- 自由人生事件预测、医疗/寿命/灾祸、投资/赌博判断（任务书永久禁令）。
- 流时（时辰以下粒度）。
- RAG/Vector DB、Chatbot Agent、用户系统、支付、云同步、遥测。

## 数据口径提示

- 1147 命例中 1045 可解析四柱；165 可重放（有结构化岁运）；「原书明确
  采用 vs Engine 检出」严格对照需 raw OCR（BLOCKED）。
- 旺衰多方法（dimension/weighted/fuyi）分歧是真实方法论差异（ADR-059
  实证），引擎并列呈现、不裁决。

## AI Provider 配置的部署边界（M41-hotfix）

**支持的部署形态：单用户本机运行**（默认）。安全边界如下：

- **配置操作（set/test/clear）仅接受回环客户端**（127.0.0.1/::1）。这是
  服务端 socket 级判定，不可经请求头伪造；**CORS 不是鉴权**，仅是浏览器
  侧附带约束。`dev_start.py` 显式绑定 `127.0.0.1:8000`。
- 局域网/公网部署默认被拒绝（403 AI_CONFIG_LOCAL_ONLY）。运维若显式设置
  `TIANZE_ALLOW_REMOTE_AI_CONFIG=1` 自担风险放行，**必须**同时在反向代理
  层完成鉴权与身份隔离——本项目不内建账户系统（单用户假设）。
- API Key 仅存后端进程内存：不落盘、不写日志、接口只回显尾 4 位、
  前端无 localStorage/cookie 持久化（已代码审计 + 测试锁定）。
- Base URL SSRF 防护：仅 http(s)、拒绝内网/环回/链路本地（「本地模型」
  预设显式豁免回环，对应单用户本机 Ollama 场景）；连接测试不跟随重定向
  （3xx 判失败）；set 与 test 双重校验。
- **已知残余风险（如实声明）**：SSRF 校验与实际请求各自解析 DNS，存在
  理论 DNS-rebinding TOCTOU 窗口；单用户本机模式下接受此残余，未做
  IP 钉扎传输层。
- 环境变量 `TIANZE_LLM_API_KEY` 优先于 UI 配置；两者并存时 set 响应与
  status 均明示"实际使用环境变量"，避免保存成功却不生效的误导。
- 预设兼容性：全部 `verified: false`——本项目无真实云 Key，未经实测的
  提供商不标"已兼容"（协议层由本地 Mock 全链路验证，见
  apps/api/tests/test_ai_config_security.py）。
- **BLOCKED**：真实云端 Provider 实测成绩（无外网凭据，不伪造）。
