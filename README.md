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
| 个性化 Plan | 根据目标、基础、节奏和最终成果生成 `plan.md`，确认后才进入课程 |
| 自适应 HTML PPT | 按知识密度决定页数，支持 Markdown、代码高亮、Mermaid 与页面内行动提示 |
| 课堂与课后分离 | 课堂点击选择题检验理解；课后练习保存在真实项目目录，不阻塞下一章 |
| 统一题库 | 自动收录课堂题、错题、课后作业、追加练习、重点问题和面试题 |
| Anki 式复习 | 题库内点击“开始复习”，按“没想起来 / 稍微有点困难 / 顺利”安排下次复习 |
| 对话追加练习 | 在课程中直接说“针对这个点再出几道题”，生成 3 道经校验的题并加入题库 |
| 面试训练 | 可导入自有题；没有题时，每章仍生成带参考答案、回答结构与追问的简答题 |
| 流式交互 | FastAPI + SSE 持续返回消息，并显示长任务的阶段、进度与预计等待时间 |
| 知识库共创 | Skills、知识原子、路线与题目可通过 PR 扩充；复核后的内容可进入公共知识库 |

完整产品范围见 [产品需求文档](product/PRD.md)，不同用户的完整路径见 [工作流说明](product/WORKFLOWS.md)。

<div align="center">
  <img src="assets/learning-agent-ui.jpg" width="920" alt="Learning Agent interface" />
</div>

## 快速安装

### 1. 安装 Codex

任选一种：

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

建议使用 macOS、Linux，或 Windows 的 WSL 2；Python 需要 3.10 或更高版本。

### 3. 配置 DeepSeek API

```bash
cp .secrets.env.example .secrets.env
```

打开项目根目录下的 `.secrets.env`，只需填写一行：

```dotenv
DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
```

这个配置只属于当前项目。真实密钥和本地学习记录均已被 Git 忽略，不会上传到仓库；无需配置 OpenAI API，也无需登录 Codex。

### 4. 启动

```bash
./run.sh
```

首次启动会自动准备教学知识库。随后打开：

<http://127.0.0.1:8787>

## 怎么用

1. 在输入框直接说目标，例如“我想从零学 Go”“帮我看懂这个 LangGraph 项目”或“准备 Java 后端面试”。
2. 如果信息还不够，Agent 只会给出 3–4 个紧凑选项来确认关键需求。
3. 先查看生成的学习计划；满意后确认，不满意可直接在对话框里要求修改。
4. 按 HTML PPT 学习，完成课堂选择题，并在生成的项目目录中亲手运行代码。
5. 遇到问题直接在对话框提问；问题、错题、作业和掌握情况会保存到本地学习档案。
6. 想多练时直接说“针对这个点再出几道题”；打开左侧“题库”，可开始 Anki 式复习。
7. 下次打开页面，直接从左侧已有学习项目继续。

本地记录保存在 `userdir/`，关闭网页或重启服务不会清空。该目录不会提交到 GitHub。

### workspace 发布快照

这里的 `publish` 不是上传 GitHub，也不是发布 npm / PyPI 包。它会把 `workspace/dev/manifest.json` 白名单中已验证的 Skills 和知识库文件，复制成当前服务使用的稳定快照 `workspace/releases/current/`。开发中的临时文件、用户数据和密钥不会进入快照；首次启动如果没有快照，`run.sh` 会自动生成。

## 项目结构

```text
Learning-Agent/
├── backend/       # FastAPI、Codex 调用、计划与课程状态
├── frontend/      # 对话、HTML PPT、大纲与题库界面
├── workspace/dev/ # 教学 Skills、知识库与课程内容
├── templates/     # 项目内 Codex / DeepSeek 配置模板
├── tests/         # 自动化测试，保障知识库 PR 与教学流程
├── projects/      # 示例与课程项目资源
├── run.sh         # 一键启动
└── requirements.txt
```

## 测试与知识库共创

`tests/` 会保留在开源仓库中，它用于验证教学流程、选择题答案、代码注释、路径安全与知识库 PR，避免贡献内容破坏现有学习体验。

```bash
.venv/bin/python -m pytest -q
.venv/bin/python workspace/dev/tools/validate_workspace.py
```

欢迎贡献新的知识原子、课程路线、面试题、练习、常见误区、教学 Skills 与产品改进。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE)
