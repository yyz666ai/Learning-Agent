# Learning Agent Server

> 项目的完整介绍、安装教程、API 安全配置和知识库 PR 指南请从仓库根目录的 [`README.md`](../README.md) 开始。English documentation: [`README_EN.md`](../README_EN.md).

一个跑在本机的学习 Agent：网页当入口，FastAPI 后端桥负责流式交互，**全局已装的 Codex CLI** 当无头引擎，DeepSeek API 当模型。剧本（workspace）只读、用户数据（userdir）唯一可写。

## 先搞清楚：它和你的 Codex 是什么关系

- Codex 是**全局原生安装**的官方 CLI（`/usr/local/bin/codex`），本仓库**不包含 Codex 本体**，也不改动它。
- 本仓库只做一件事：用环境变量 `CODEX_HOME`，给"它 spawn 出来的 Codex"指一份**单独的配置**（DeepSeek）。这跟你终端里自己敲 `codex`（读 `~/.codex`，ChatGPT 登录态那套）**完全分开、互不影响**。
- 所以 `config.toml` 里的 DeepSeek 配置，**只对这个项目 spawn 的 Codex 生效**：它不是全局配置，也不是"整个项目的配置"，更不会动到你原生的 codex。项目本身没有配置文件，配置是给"被 spawn 的那个 Codex 实例"用的。

## 目录结构

```
learning-agent-server/
├── frontend/                 # ① 前端（零依赖 SPA）
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js             #    聊天 + Markdown/deck 渲染 + 课件/作业沉淀 + 进度抽屉
├── backend/                  # ② 后端桥（stdlib HTTP，无第三方依赖）
│   ├── main.py               #    入口：serve 前端 + /api/health /api/state /api/chat /api/grade
│   ├── codex_driver.py       #    spawn codex + 三注入（cwd/CODEX_HOME/USER_DIR）+ 读 .secrets.env
│   ├── llm.py                #    直连 DeepSeek 判题（/chat/completions，不经过 codex）
│   └── publish.py            #    workspace/dev → workspace/releases/rYYYYMMDD-NNN
├── templates/                # ③ CODEX_HOME 配置模板
│   └── codex-home-config.toml
├── workspace/                # ④ 剧本
│   ├── dev/                  #    母本（可写）：AGENTS.md + manifest.json + .codex/skills/ + curriculum/ + references/ + memory/ + tools/
│   └── releases/             #    发布快照（只读，跑给用户看）— gitignored
├── userdir/                  # ⑤ 用户数据（唯一可写）— gitignored
│   └── u_yang/
│       ├── .codex-runtime/home/   # CODEX_HOME（DeepSeek 配置 + Codex 会话状态）
│       ├── learning-state.json    # 学习状态
│       ├── profile.md             # 学习者画像
│       ├── memory/                # 记忆摘要
│       └── workspace/demos/       # 练习产物
├── chat.sh / dev.sh          # 命令行入口（用户侧 / 作者侧）
├── .secrets.env              # DeepSeek key — gitignored（绝不提交）
└── .gitignore
```

## 快速上手

```bash
cd learning-agent-server

# 第一次：创建项目依赖环境
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# A) 网页入口（推荐）：起后端 → 浏览器打开 http://127.0.0.1:8787
./run.sh                          # 可选端口参数：./run.sh 9000

# B) 命令行入口：直接中文对话
./chat.sh                         # 用户侧（站进只读快照，学习用）
./dev.sh                          # 作者侧（站进 workspace/dev，改剧本/策展用）
```

网页首次打开是单窗口聊天引导；确认目标后进入左侧学习大纲、讲义与右侧教练的学习工作台。聊天和生成状态均通过 SSE 流式返回。

## 后端 API

| 端点 | 方法 | 作用 |
|---|---|---|
| `/api/health` | GET | 存活检查 |
| `/api/state?user_id=` | GET | 读学习状态 + 画像 |
| `/api/onboarding/intent` | POST | 读取意图 Skill，用无思考 Flash 做结构化 slot filling |
| `/api/chat` | POST | 聊天 → `codex exec`（读状态、跑技能、写记忆） |
| `/api/grade` | POST | 直连 DeepSeek 判题（前端当前未接线，保留给后续） |

调用分两层：`/api/onboarding/intent` 读取发布快照里的 `learning-intent-router/SKILL.md`，通过 `llm.py` 直连 `deepseek-v4-flash`，显式关闭 thinking 并校验 JSON，只处理首次输入和追问的快速路由；Plan、资料研究、讲义、答疑与课程修订仍由 `/api/chat` 或相应生成端点走完整 Codex agent（读状态 + Skills + 工具 + 写记忆）。`/api/grade` 也是轻量直连 DeepSeek，但前端当前未接线。

## 三层读写规则

| 层 | 目录 | 放什么 | 读写 |
|---|---|---|---|
| Global | `userdir/u_xxx/.codex-runtime/home/`（CODEX_HOME） | Codex 配置（DeepSeek）+ 会话状态 | 系统读写 |
| Workspace | `workspace/releases/r…/` | AGENTS.md + 教学 skills + 课程/政策 | 只读，只从 dev 发布产生 |
| User | `userdir/u_xxx/` | 状态 / 画像 / 记忆 / 练习产物 | 可写（唯一） |

- **用户记忆在 userdir，不在 workspace**：`learning-state.json`（状态）、`profile.md`（画像）、`memory/`（记忆）、`workspace/demos/`（练习产物）。
- **workspace 只读，只改 userdir**：agent 运行时永不改 workspace；改课程/技能走作者策展（`workspace/dev` + `dev.sh`），再 `publish.py` 发布新版本生效。

## 模型与密钥

- 模型声明在 `templates/codex-home-config.toml`（模板，不含密钥），首次运行时由 `codex_driver.py` 复制到 `userdir/u_yang/.codex-runtime/home/config.toml`。
- key 存在 `.secrets.env`（gitignored），由 `codex_driver.py` / `chat.sh` / `dev.sh` 读进环境变量 `DEEPSEEK_API_KEY` 再注入进程；`config.toml` 里只有 `env_key = "DEEPSEEK_API_KEY"` 这个"引用"，不存明文。
- 切 Codex Agent 模型：改 `config.toml` 的 `model`，可选 `deepseek-v4-flash`（快/省）或 `deepseek-v4-pro`（更强推理）。onboarding 快路由固定使用 Flash + `thinking=disabled`，避免一句澄清问题触发长推理。

## 教学技能（workspace/dev/.codex/skills/）

`learner-onboarding`（首次建档）、`adaptive-onboarding`（按主题、目标和基础生成 3–4 道点击诊断题）、`environment-setup`（环境配置）、`learning-plan`（学习路线）、`codebase-learning-plan`（看懂现有项目）、`adaptive-lesson-flow`（完整章节讲义、点击题、逐项运行验收）、`knowledge-curator`（验收后的共享知识库沉淀与复用）、`project-practice`（小项目练习）、`concept-teaching`（讲概念）、`code-learning`（读代码）、`exercise-coach`（做题引导）、`assignment-review`（批改）、`spaced-review`（间隔复习）、`learning-progress`（进度复盘）。

路由规则和门禁见 `workspace/dev/AGENTS.md`；课程在 `workspace/dev/curriculum/`，政策在 `workspace/dev/references/`。
