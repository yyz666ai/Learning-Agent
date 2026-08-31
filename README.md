<div align="center">
  <img src="assets/learning-agent-logo.png" width="120" alt="Learning Agent Logo" />
  <h1>Learning Agent</h1>
  <p><strong>从目标理解、学习计划到互动讲义、练习与复习的一站式 Agentic AI 学习系统。</strong></p>
  <p><a href="README.md">简体中文</a> · <a href="README_EN.md">English</a></p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-2563EB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/FastAPI-SSE-059669?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Codex-CLI-111827?style=flat-square&logo=openai&logoColor=white" alt="Codex CLI" />
    <a href="LICENSE"><img src="https://img.shields.io/github/license/yyz666ai/Learning-Agent?style=flat-square" alt="MIT License" /></a>
  </p>
</div>

---

## 这是什么

Learning Agent 会先理解你想学什么、目前会多少、最后想达到什么结果，再生成个性化 `plan.md`。确认计划后，它会用 HTML PPT、可点击选择题、带中文注释的代码和真实练习项目，一步一步带你学习。

- 自由输入目标，不必先填写一堆固定表单；
- 根据目标和基础生成不同深度的学习方案；
- 课堂选择题、课后练习、错题与复习卡片统一记录；
- 支持概念学习、从零入门、项目实战、能力精进和面试训练；
- 教学 Skills 与知识库都在 `workspace/dev/`，可以通过 PR 持续共创。

## 已实现能力

| 能力 | 当前行为 |
| --- | --- |
| Agentic Onboarding | 从自由输入做意图识别与 slot filling，只补齐真正影响计划的信息 |
| 个性化 Plan | 根据目标、基础、节奏和最终成果生成 `plan.md`；章节课次与单次分钟分开记录，多次课章节不按知识点数量累加预算 |
| 自适应 HTML PPT | 按知识密度决定页数，支持 Markdown、代码高亮、Mermaid 与页面内行动提示 |
| 课堂与课后分离 | 课堂点击选择题检验理解；课后练习保存在真实项目目录，不阻塞下一章 |
| 统一题库 | 自动收录课堂题、错题、课后作业、追加练习、重点问题和面试题 |
| Anki 式复习 | 题库内点击“开始复习”，按“没想起来 / 稍微有点困难 / 顺利”安排下次复习 |
| 课件编辑 | 默认只读；进入编辑后修改当前页标题、Markdown 和教学代码，预览后保存，支持 H1/H2/H3、加粗、斜体、高亮和下划线 |
| 确认式 AI 修订 | 修改讲义、修订题目和追加练习先生成提议；确认生成候选稿，再检查差异并确认应用，普通答疑不替换课件 |
| 历史与 Markdown 导出 | 手动保存和 AI 应用保留版本；可撤销或恢复历史，导出同版本可读 Markdown，不包含私有判题答案键 |
| 对话追加练习 | 在课程中说明题型和数量，通过提议、候选、应用流程追加选择题或编程／项目练习，并同步题库 |
| 面试训练 | 可导入自有题；没有题时，每章仍生成带参考答案、回答结构与追问的简答题 |
| 流式交互 | FastAPI + SSE 持续返回消息，并显示长任务的阶段、进度与预计等待时间 |
| 知识库共创 | Skills、知识原子、路线与题目可通过 PR 扩充；复核后的内容可进入公共知识库 |

完整产品范围见 [产品需求文档](product/PRD.md)，不同用户的完整路径见 [工作流说明](product/WORKFLOWS.md)；如果只想看一份总览，可直接阅读 [产品与系统总说明](product/LEARNING_AGENT_SYSTEM_GUIDE.md)。模型、阿里云年度成本以及 Codex / Skills / Python / 知识库的真实执行边界见 [成本与执行工作流](product/COST_AND_EXECUTION_WORKFLOW.md)；知识原子动态组合、个性化 HTML PPT、Plan 降本与云端收费的目标架构见 [知识库与个性化课件设计](product/KNOWLEDGE_BASE_PERSONALIZED_DECK_DESIGN.md)。

<div align="center">
  <img src="assets/learning-agent-ui.jpg" width="920" alt="Learning Agent interface" />
</div>

## 快速安装

### 1. 安装 Codex

先安装 Python 3.10+；使用 npm 安装 Codex 时还需要 Node.js（LTS）。macOS / Linux 任选一种，原生 Windows 使用 npm：

```bash
npm install -g @openai/codex
# 或
brew install codex

codex --version
```

这里只需要安装 Codex 命令。运行本项目不需要执行 `codex login`，也不需要修改你电脑上的全局 Codex 配置。

### 2. 下载项目并安装依赖

```bash
git clone https://github.com/yyz666ai/Learning-Agent.git
cd Learning-Agent

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

上面是 macOS / Linux 命令。原生 Windows 在 PowerShell 中下载项目后执行（无需激活虚拟环境，也无需更改 PowerShell 执行策略）：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. 配置 DeepSeek API

```bash
cp .secrets.env.example .secrets.env
```

Windows PowerShell 使用 `Copy-Item .secrets.env.example .secrets.env`。

打开项目根目录下的 `.secrets.env`，只需填写一行：

```dotenv
DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
```

这个配置只属于当前项目。真实密钥和本地学习记录均已被 Git 忽略，不会上传到仓库；无需配置 OpenAI API，也无需登录 Codex。

### 4. 启动

```bash
./run.sh
```

Windows PowerShell 或命令提示符：

```powershell
.\run.cmd
```

自定义端口可用 `./run.sh 8899` 或 `.\run.cmd 8899`。两种入口均使用项目 `.venv`，校验失败会停止并保留错误码，不会继续发布或启动。

每次启动都会先检查 Codex、DeepSeek 配置和教学文件，再同步当前版本的 Skills 与知识库，避免拉取更新后继续使用旧快照。随后打开：

<http://127.0.0.1:8787>

前端网页和后端由同一个服务提供，不需要再启动一个前端开发服务器。启动窗口会打印 Plan / 课件生成的开始、结束、耗时、工具调用数和 token 用量；`reasoning_output_tokens=0` 表示这次调用没有产生思考 token。这些生成设置仅影响本项目的调用，不修改个人 Codex 配置。

如果部署在服务器或局域网，并需要从其他设备访问：

```bash
LEARNING_AGENT_HOST=0.0.0.0 ./run.sh
```

再通过服务器域名或局域网 IP 的 `8787` 端口访问。网页中的基础诊断、Plan 与 HTML PPT 初次生成使用后台任务和短轮询：启动请求立即返回任务标识，刷新后读取原任务，不必保持几十秒的 HTTP 连接。诊断显示服务器实际阶段与等待时间，不用虚构百分比代表模型进度。网络短暂中断时先查询原任务，避免重复生成；服务重启后被中断的诊断可以重试。

课件修订候选和旧版 `/api/onboarding/start` 兼容接口仍是同步请求，反向代理需为这些请求保留足够超时。请只运行一个服务进程：诊断调度及编辑事务目前不支持多 worker／多实例。取消诊断会阻止旧结果写入；已发出的模型调用可能继续运行到返回或超时，并不保证取消后立即停止计费。

平台边界：文件夹按钮使用本机文件管理器；无桌面环境或打开失败时只返回路径，不声称已经打开。原生 Windows 的系统提醒尚未实现。Windows 命令解析与启动契约有离线模拟测试，尚未完成真实 Windows 端到端验收；macOS / Linux 仍使用 `run.sh`，WSL 也可使用该入口。

## 怎么用

1. 在输入框直接说目标，例如“我想从零学 Go”“帮我看懂这个 LangGraph 项目”或“准备 Java 后端面试”。
2. 如果信息还不够，Agent 只会给出 3–4 个紧凑选项来确认关键需求。
3. 先查看生成的学习计划；满意后确认，不满意可直接在对话框里要求修改。
4. 按 HTML PPT 学习，完成课堂选择题，并在生成的项目目录中亲手运行代码。
5. 遇到问题直接在对话框提问；问题、错题、作业和掌握情况会保存到本地学习档案。
6. 想多练时直接说“针对这个点再出几道题”；打开左侧“题库”，可开始 Anki 式复习。
7. 下次打开页面，直接从左侧已有学习项目继续。

本地记录保存在 `userdir/`，关闭网页或重启服务不会清空。该目录不会提交到 GitHub。

### 中文 / English

- 默认中文。点击页面右上角的**地球图标**，选择 **English** 或 **中文**；刷新后保留选择。
- 界面立即切换；此后创建的引导提问、Plan、课件、练习和答疑按选择的语言生成。生成中的任务沿用开始时的语言，不会因为切换而重新调用模型。
- 已有课程、用户笔记和历史对话保留原文。完整学习方案窗口和课件操作中的“翻译为当前语言”会先确认范围，再生成**当前 Plan 或当前章**的只读译本；关闭译本即可返回原版。不会批量重做整门课程。
- 翻译不修改原始课程、作答记录、题目 ID 或代码。原文更新后需要重新确认翻译；保存语言偏好失败会显示重试提示。
- 语言偏好保存在 `userdir/u_<id>/preferences.json`，译本保存在该目录的 `translations/`。界面语言 `locale` 与 Python / Go 等编程语言 `language` 是两个独立字段。
- 本版本语言功能的验收与真实调用耗时见 [中英文验收记录](docs/superpowers/plans/2026-08-31-bilingual-validation.md)。这是本地应用的语言支持，不代表已具备可直接公开售卖的账户、支付与配额系统。

### 修改课件与恢复版本

- 默认只读仍可翻页、选文提问和答题。点击“编辑”后才出现格式工具与草稿；保存产生新版本，取消不应用草稿。代码单独编辑，不套用正文格式。
- 修改题干、选项或答案走右侧修订提议，不直接编辑结构化题目。先确认生成，再查看候选差异并应用；生成授权不等于替换授权。
- “撤销上次修改”和历史恢复会恢复课件及配套答案；不会删除学习者代码或历史作答。题目改变后不沿用旧题通过状态，恢复旧题时按相应题目版本恢复证据。
- Markdown 导出含版本与页面 ID，可在外部阅读；不是自动导入通道。外部修改不会自行覆盖活动课件，高亮／下划线在其他阅读器中的显示取决于扩展支持。
- 一章可以包含多次课；课内预算与课后练习分开。允许继续浏览下一章不等于已经掌握课后任务。

本次实现、真实生成与记录回放的区别、浏览器验证进度和已知边界见 [发布验证报告](projects/learning-agent/design/outputs/SAFE_EDITING_RELEASE_VALIDATION.md)。自动化测试通过不保证所有未来模型输出或所有学习路线均正确。

### workspace 发布快照

这里的 `publish` 不是上传 GitHub，也不是发布 npm / PyPI 包。它会把 `workspace/dev/manifest.json` 白名单中已验证的 Skills 和知识库文件，复制成当前服务使用的稳定快照 `workspace/releases/current/`。开发中的临时文件、用户数据和密钥不会进入快照；`run.sh` 每次启动都会重新生成快照，确保 Git 更新后的教学规则立即生效。

## 项目结构

```text
Learning-Agent/
├── backend/       # FastAPI、Codex 调用、计划与课程状态
├── frontend/      # 对话、HTML PPT、大纲与题库界面
├── workspace/dev/ # 教学 Skills、知识库与课程内容
├── templates/     # 项目内 Codex / DeepSeek 配置模板
├── tests/         # 自动化测试，保障知识库 PR 与教学流程
├── projects/      # 示例与课程项目资源
├── run.sh         # macOS / Linux 启动
├── run.cmd        # 原生 Windows 启动
└── requirements.txt
```

## 测试与知识库共创

想用自己配置的 DeepSeek 实测生成速度，可运行：

```bash
# 会消耗 API 额度；只创建隔离的测试目录，不改自己的学习进度
python tools/evaluate_lessons.py --case beginner
# 还可以选 advanced、interview 或 all
```

它会从已确认的测试画像开始，调用真实模型生成 Plan，模拟明确确认，再生成首章课件；不代表测试了自然语言 onboarding。每一步耗时、原始模型输出和成功/失败原因保存到 `evals/runs/`（已忽略，不上传 GitHub）。修复原理、样本耗时及测试边界见 [生成性能与可靠性报告](docs/generation-performance-2026-08-30.md)。

`tests/` 会保留在开源仓库中，它用于验证教学流程、选择题答案、代码注释、路径安全与知识库 PR，避免贡献内容破坏现有学习体验。

```bash
.venv/bin/python -m pytest -q
node --test tests/*.test.cjs
.venv/bin/python workspace/dev/tools/validate_workspace.py
```

欢迎贡献新的知识原子、课程路线、面试题、练习、常见误区、教学 Skills 与产品改进。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 交互式兼容性报告

下载仓库后，用浏览器打开 [Detect 报告](projects/learning-agent/detect/outputs/report/index.html)：支持平台／状态筛选、查看每次失败与复测、保存本机复核草稿和导出附件。GitHub 代码页不会执行 HTML，需要下载后打开。报告明确区分真实模型、受控测试、Windows 模拟和未验证项；机器通过不代表人工批准。

重建报告：`python tools/build_detect_report.py projects/learning-agent/detect/outputs/report/report_data.json /tmp/new-detect-report`（Windows 把输出路径改为一个新的空目录）。不会覆盖已有证据批次。完整口径见 [运行计划](projects/learning-agent/detect/outputs/evaluation-run-plan.md)。

## License

[MIT](LICENSE)
