# 跨平台部署与诊断可靠性：评测简报和修复设计

日期：2026-08-30；版本：v1.0；状态：Owner 已通过“开始吧”确认本轮修复范围、验收标准和证据口径；不等于确认后续测试结果或批准 Detect Gate。

## 1. 本轮决定

推荐：保留同一套 Python 后端和网页，新增原生 Windows 启动入口；诊断生成改为后台任务与短轮询；按 detect 和用户附件生成可交互 HTML 报告。不是只给 fetch 加长超时。

- 项目：Learning Agent。
- Owner：项目维护者／用户；AI 可整理证据和草拟方案，不代替 Owner 批准。
- 基线 SUT：`32ffe836fe7e043e1c325b2baa935ef737288474`。
- 当前环境：macOS；原生 Windows 运行证据缺失。
- 用户提供的 Windows 29–33 秒结果：外部陈述，未收到同版本原始请求／代理日志，不标为本机实测。
- 本轮尚未修改应用代码，也未生成正式评分结论或 HTML 成品。

## 2. 已核实与未知

| 观察 | 证据 | 判定边界 |
| --- | --- | --- |
| 启动只认 `.venv/bin/python` | `run.sh` | 原生 Windows venv 通常使用 Scripts；当前入口没有兼容分支 |
| Codex 子进程与部署自检各自启动命令 | `backend/codex_driver.py` 的四条执行路径、`backend/deployment_check.py` | 用户提出的只改驱动并不能覆盖全部入口；本机没有验证 npm 的 Windows 启动包装器 |
| Prompt 作为命令行参数，输出依赖默认文本编码 | `backend/codex_driver.py` | 长提示词、中文路径／输出需要跨平台专项测试；尚未宣称已复现这些失败 |
| 打开练习目录写死 macOS 的 `open` | `backend/main.py:open_practice_folder` | 不支持 Windows 文件浏览器，并可能把缺少打开命令误报为目录不存在 |
| 系统提醒仅 Darwin 实现 | `backend/reminders.py:send_system_notification` | Windows 返回 False；不能在 README 中承诺同等原生桌面通知 |
| `/api/onboarding/start` 同步等待生成和可能的一次修复 | `backend/main.py:onboarding_start` | 处理时间取决于模型、网络、上下文和是否修复，不是固定 29 秒 |
| 前端没有设置本地诊断请求超时 | `frontend/js/onboarding.js:request/beginDiagnosis` | 不能把错误归因于项目自设的 30 秒 AbortController |
| 92% 与“仍在生成”不来自后端任务存活信息 | `frontend/js/activity-progress.js:estimate` | 只是 elapsed 超过 expected 时的固定文案，不能作为后端运行证据 |
| 现有 Plan 和 lesson 已使用后台任务 | `backend/generation_jobs.py`、`backend/main.py` | 可以复用设计模式，但诊断的会话、取消、题目存储需要独立保护 |

### 受控定位探针（不是模型性能测试）

在当前代码中替换模型调用为可阻塞的测试函数，不写用户目录、不调用付费模型。模型函数进入后，`onboarding_start` 尚未返回：

```json
{"kind":"controlled_local_probe_not_model_benchmark","model_call_entered":true,"endpoint_returned_while_model_blocked":false}
```

解除阻塞并模拟服务错误后返回 HTTPException 502。该探针仅证明诊断处理链同步等待；不证明 WorkBuddy 的具体断开阈值。探针首次使用了不合法的测试枚举 `interview_prep`，在到达业务代码前被 Pydantic 拒绝；改为项目实际枚举 `interview_sprint` 后得到上述结果，首次错误不算产品缺陷。

### 外部说明中需要纠正的点

1. 正确的浏览器 API 是 `AbortSignal.timeout(120000)`，不是 `AbortController.timeout`。它设置客户端取消时间，不能命令代理延长连接寿命。来源：[MDN](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal/timeout_static)。
2. 29–33 秒只能描述那次采样，不是诊断生成的必需或固定耗时。
3. 返回 200 证明那次接口成功，不证明所有部署、失败恢复、重试和并发状态都正确。
4. 前端“仍在生成”不是后端心跳。真正状态必须由任务查询提供。
5. Python 文档建议子进程显式指定编码／可执行入口；Windows 启动不应通过拼接含用户输入的 shell 命令解决。来源：[Python subprocess](https://docs.python.org/3/library/subprocess.html)。

## 3. 备选方案

| 方案 | 收益 | 局限 |
| --- | --- | --- |
| 仅延长前端等待 | 改动少 | 无法解决代理断开、刷新重复生成及 Windows 启动差异，不推荐 |
| **统一原生入口＋诊断后台任务（推荐）** | 针对根因，Mac 和 Windows 使用同一业务代码；断线后可取结果 | 需要新增任务状态与跨平台测试 |
| 只支持 WSL／容器 | 宿主差异较小 | 增加 Windows 用户安装门槛，不符合简化部署诉求 |

## 4. 推荐实现边界

### 4.1 跨平台运行

- macOS/Linux 保留 `./run.sh`；Windows 提供不要求永久修改执行策略的原生入口，优先 `run.cmd`，由薄包装层调用共同 Python 启动逻辑。
- 识别 `.venv/bin/python` 与 `.venv/Scripts/python.exe`。路径包含空格或中文也必须正确。
- 统一 Codex 命令解析，部署自检、普通捕获、流式回答和其他执行路径共享同一个解析器：原生二进制可直接调用；Windows npm 安装可定位 `node` 与已安装 `@openai/codex` 的入口，不写死用户 AppData 路径，不下载／执行不明脚本。
- 长 Prompt 通过标准输入发送，固定 UTF-8 编解码，保留当前项目级 `CODEX_HOME`／DeepSeek 密钥隔离和只读调用参数；不靠 `shell=True` 拼接用户输入。
- 打开练习目录按平台实现，保留安全路径校验；无图形桌面／远程服务器返回可复制路径和真实说明，不误报已在用户电脑打开。
- Windows 原生桌面通知本轮不默认引入新系统依赖；明确标出当前支持状态，不伪称通知已发送。
- README 中英文保持一致，区分原生 Windows、Mac/Linux 与可选 WSL。

### 4.2 诊断生成可靠性

- 新网页采用短启动请求，创建诊断任务后立即返回 202；后台生成题目，网页查询 queued/running/completed/failed/cancelled 状态。
- 创建请求带唯一请求标识，重试或启动响应丢失时复用同一任务，不重复计费生成；刷新后可以找回任务与已完成诊断。
- 任务绑定用户、当前 onboarding 会话／版本、完整提交摘要；用户开始新目标、取消或切换项目后，旧任务不得写入新诊断状态。
- 模型结果先校验、后提交；完成诊断及任务结果持久化。服务重启后的未完成任务明确显示中断与可重试，不能假装继续运行。
- 网络暂时中断时显示“暂时无法读取状态，正在重连”，不直接判断生成失败，也不无依据说后台仍运行。
- 显示真实任务阶段和已等待时间；没有充分历史采样时不显示精确剩余百分比或确定剩余秒数。
- 总任务与模型调用都有上限；结构修复与传输失败分开处理，避免无限重试。
- 保留旧同步接口兼容现有调用方，但更新浏览器和评测工具使用新流程；明确旧接口不具备代理超时抗性。

### 4.3 HTML 交互报告

用户参考附件包含总览、独立评测、Bad Case、上线建议与过程检查，以及 `report_data.json`、逐条评分 JSONL、人工复核队列和工作簿。detect 也包含 `scoring-record.html` 与 `evaluation-conclusion.html` 模板。

采用相同信息结构，替换为本项目事实；不复制 TA 项目的分数或结论：

- 总览：版本、平台、执行范围、通过／失败／无法验证／阻断数量。
- 可筛选用例：平台、用户场景、状态、模块、风险；搜索问题原文。
- 点击详情：输入、预期行为／GT、实际回复、可审计执行记录、耗时、评价、修改内容和复测结果。
- Bad Case：修复前后并列；初次失败保留，重跑不得覆盖。
- 人工复核：填写意见、保留本机草稿、导出审核记录；不假冒已签署人工审批。
- 附件下载：公开脱敏的用例、GT、运行记录和评分 JSON/JSONL；CSV 可选。网页可离线打开，报告包不需要运行 Learning Agent，也不包含 API Key／真实个人资料。
- 历史 601 Python／22 Node 仅作为既有 Mac 回归批次；不转换成“623 条 Windows 通过”或混入本轮新用例的通过率。
- 原始证据、评分和报告分离保存，HTML 可由数据重建；公开实际输出，不收集模型私有思维链。

## 5. 已确认验收标准

| 层级 | 对象 | 建议标准 | 不能推出什么 |
| --- | --- | --- | --- |
| 业务 | 用户无需排查平台命令便能开始学习 | 本轮只测部署与关键学习链路，不伪造留存／付费提升 | 离线测试不证明商业成功 |
| 产品 | 初学直接 Plan；有基础先诊断，再确认 Plan 和 lesson | 正常链路完成，重试／刷新不丢当前会话，不把旧结果覆盖新目标 | 三个样本不代表全部自然语言 |
| 能力 | Windows／Mac 启动与子进程 | 路径、UTF-8、缺依赖、长输入、只读参数正确；平台实测分别记录 | Mac mock 不等于 Windows 实机通过 |
| 能力 | 后台任务与前端 | 受控模型等待 35 秒时，启动请求在本地 2 秒内返回；每次状态查询不等待模型 | 此阈值是本地验收建议，不是公网 SLA |
| 能力 | 数据安全 | 取消、重复提交、换项目、重启、并发情况下不串题、不重复应用、不泄露密钥 | 单进程测试不证明多实例安全 |
| 产品 | 交互报告 | 筛选、详情、下载、人审草稿均能操作；缺证据明确显示，不加入通过分母 | 评分页面不是上线批准 |

### 硬门

- 私有数据泄露、迟到任务覆盖新目标、未确认写入当前课件均不得用其他得分抵消。
- Windows 无实际执行器时记 UNVERIFIABLE／待 Windows 实机复测，不能签署“Mac/Windows 全通过”。
- AI 评价与用户人工复核分开；人工复核为空不能伪造姓名、时间或确认。
- 当前附件与 Skill 资料只读；产物写入本项目 `detect/`，不反向修改课程材料。

## 6. 下一步

Owner 已确认采用推荐组合方案和上述证据口径，包括“Windows mock 与实机结果分开”。开始制定实现与用例计划，按先失败测试后修复推进，生成交互报告并验收。人审与发布判断仍单独记录。
