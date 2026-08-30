# 跨平台启动、后台诊断与交互报告 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task. One implementation worker at a time; specification review then code-quality review. Work in main as explicitly requested; root owns commits.

**Goal:** Windows 和 Mac 共用业务入口，诊断不再依赖长 HTTP 连接，用户可交互查看真实测试证据。

**Architecture:** 统一 subprocess 入口和 UTF-8 stdin；独立持久化诊断任务注册表，短请求创建/查询/取消；静态 HTML 嵌入脱敏 JSON 数据并支持本机复核草稿。

**Tech Stack:** Python/FastAPI、pytest、原生 JavaScript/Node tests、静态 HTML。

## 2026-08-30 执行状态

Task 1/2 的实现、先失败后修复的回归以及独立代码审查已完成；Task 3 的离线HTML、附件、假DOM交互测试与证据整理已完成。真实Windows端到端未执行，报告真实浏览器验收被工具策略阻断，因此这两项不能勾为完成。下列原始清单保留作为已批准的验收合同；逐项实际证据和最终结果以 `run-evidence.md`、交互报告及 `progress.yaml` 为准，未签署人工Gate。

## Task 1：跨平台边界

Files: create `backend/platform_runtime.py`, `backend/startup.py`, `run.cmd`, `tests/test_platform_runtime.py`; modify `run.sh`, `backend/codex_driver.py`, `backend/deployment_check.py`, `backend/main.py` 的目录打开处理及 README 双语。

- [ ] 先写失败测试：Windows npm shim 路径含中文/空格，缺 Node，原生入口，四条 Codex 路径 stdin 传长中文 prompt 且保留 read-only；缺 venv 与错误端口；无 GUI 返回路径而非误称打开。
- [ ] 执行 `.venv/bin/python -m pytest tests/test_platform_runtime.py -q` 留存首次失败。
- [ ] 实现共用 `codex_command()` 返回 argv 列表；Windows shim 定位本地已安装 package 入口，以 Node 执行，不使用 shell 字符串；driver 以 `-` + UTF-8 stdin 传 prompt，部署检查复用 resolver。
- [ ] run.sh/run.cmd 只选择 venv Python，再调用 `backend.startup`，该模块依序检查、publish、启动；启动失败必须非零退出，不永久修改 PowerShell 策略。
- [ ] pytest 通过后做规范审查、质量审查。原生 Windows 仍记未验证；记录 Mac 结果，不改写外部 29 秒数据。

## Task 2：诊断后台任务

Files: create `backend/diagnosis_jobs.py`, `tests/test_diagnosis_jobs.py`, `frontend/js/diagnosis-job.js`, `tests/diagnosis-job.test.cjs`; modify onboarding endpoints/JS, eval caller.

- [ ] 先写失败测试：受控模型阻塞时 start 返回202；重复 request_id 只生成一次；取消/会话修订/项目切换不得写 diagnostic.json；刷新恢复最新答题结果；重启 running 标 interrupted；错误保留重试信息。
- [ ] `.venv/bin/python -m pytest tests/test_diagnosis_jobs.py -q` 记录红灯。
- [ ] 新建任务接口以 user/session/revision/submission hash 绑定；磁盘原子保存，完成前锁内重新校验绑定；最多一次结构修复、模型调用有时限。旧同步接口兼容，不承诺抗代理超时。
- [ ] 浏览器每次短请求设 timeout，轮询读后端真实阶段；启动响应丢失复用请求标识；页面恢复复用任务而非重新生成；旧 epoch 不更新当前 UI；未知网络状态明确显示重连，不显示固定92%。
- [ ] 运行 Python + Node 目标测试；规范和质量审查修复后再回归。

## Task 3：可重建交互报告与证据

Files: create `tools/build_detect_report.py`, `tests/test_detect_report.py`, `projects/learning-agent/detect/outputs/report/` 的 HTML/JSON/JSONL；更新 detect 索引和状态。

- [ ] 为报告写数据契约测试：每 Case 对应唯一 GT，评分引用 run/evidence；安全转义 `</script>`；缺证据不记 PASS；人审默认 pending。
- [ ] HTML 包含过滤、搜索、详情、初始失败/复测、评语本机保存、JSON/JSONL 导出；文件可离线打开，正文 textContent 防止输入注入；存储失败明确提示。
- [ ] 用独立临时目录运行受控35秒诊断，记录 start/status 耗时、最终题目与重复调用数。不是模型速度基准。
- [ ] 执行 `.venv/bin/python -m pytest -q`、`node --test tests/*.test.cjs`、workspace 校验和部署检查，分别记录真实结果。
- [ ] 浏览器验证报告筛选/详情/下载/复核草稿、桌面/移动布局，以及诊断页面正常/中断状态。缺运行器保留 UNVERIFIABLE。
- [ ] 生成报告后审查文件差异与敏感数据；仅提交本轮文件，不上传 .agents 或私人用户目录。按用户既有请求推 main；不签署人工 Gate。

## Evidence contract / 用例与运行口径

- SUT baseline: `32ffe836fe7e043e1c325b2baa935ef737288474`；候选代码记录 diff hash，报告另记录生成时间。
- eval_set: platform、diagnosis-reliability、report-interaction；每 case 绑定 platform / risk / GT / test selector。
- 确定性单测每次完整运行一次；受控35秒探针一次；失败修复后重跑保留独立 run id。
- 运行记录和机器判定分离；机器通过≠人审通过；无 Windows runner 不加入已测通过率分母。
- 真实大模型抽样仅测试合成用户，GT 不传给被测模型；模型输出和耗时单独记录。既有历史 Plan/lesson 样本标 historical，不冒充本轮复测。
- 不收集私有推理过程、密钥或真实用户画像。Owner 复核待进行，不伪造批准。
