# 学习 Agent 产品需求文档（PRD v2）

> 更新日期：2026-08-20
> 本文是当前系统的权威需求文档。`docs/` 里的旧文档是历史版本，以此文为准。
> 已批准但尚未完成的“对话驱动学习剧场、动态双 PPT、Anki 复习、提醒与档案”重构，以 `docs/superpowers/specs/2026-08-20-chat-first-adaptive-learning-design.md` 为实施目标；完成后再合并回本文。

---

## 0. 一句话定位

一个跑在本机的学习 Agent：**浏览器聊天当入口，backend 当桥，Codex CLI 当引擎，DeepSeek 当模型**。核心能力：从零教 Python / Go、以看懂某个项目为终点、边教边把知识沉淀成自己的知识库。

## 1. 目标用户与四大场景

| 场景 | 描述 | 走的链路 |
|---|---|---|
| ① 小白 · 知识库已有 | 学的内容库里已有原子 | 建档 → 计划 → 讲原子 → 辅导 → 批改 |
| ② 小白 · 知识库没有 | 学的内容库里没有（如 Java/LangChain） | 建档 → 联网搜官方文档 → 出大纲 → 边教边生成原子+HTML课件 |
| ③ 小白 · 基于项目 | 给一个代码仓库，为看懂它而学 | 建档 → 读代码逆向规划 → 讲具体代码 → 项目练习 |
| ④ 熟练者 · 精进 | 有基础，想刷题/精进 | 出题刷题 → 卡点提示 → 批改 → 复习循环 |

## 2. 核心架构

```
浏览器（frontend，卡通风单页）
   │  HTTP（/api/chat、/api/grade、/api/state）
   ▼
backend（指挥员，stdlib HTTP，550 行）
   │  spawn `codex exec`（命令行喊 Codex，注入三参数）
   ▼
Codex CLI（租来的引擎，读文件照做，模型=DeepSeek）
   ├── 读 workspace/releases/current/（课本：AGENTS.md + skills + curriculum，只读）
   ├── 读/写 userdir/u_yang/（记忆本，唯一可写）
   └── CODEX_HOME = userdir/u_yang/.codex-runtime/home/（引擎记忆）
```

**关键原则**：引擎（Codex）一行不改、只用命令行遥控；你写的代码只有 frontend + backend；差异化全部在「剧本（skills+curriculum）+ 记忆（userdir）」。

## 3. 目录结构

```
learning-agent-server/
├── frontend/          # 前端（index.html + css/style.css + js/app.js）
├── backend/           # 后端（main.py + codex_driver.py + llm.py + publish.py）
├── templates/         # DeepSeek 配置模板（CODEX_HOME 投影来源）
├── workspace/         # 课本（剧本）
│   ├── dev/           #   母本（作者改，git 管）· AGENTS.md + .codex/skills + curriculum + references
│   └── releases/      #   发布区
│       └── current/   #   当前只读快照（Codex 只站这里）—— 单版本，发布即覆盖
├── userdir/           # 用户记忆（唯一可写，gitignored）
│   └── u_yang/
│       ├── learning-state.json / profile.md / plans / projects / history
│       └── .codex-runtime/home/   # CODEX_HOME（引擎记忆）
├── projects/          # 练习项目（学习者做项目的地方）
├── PRD.md             # 本文
└── .secrets.env       # API key（gitignored）
```

## 4. 前端（卡通风单页）

- **单条对话流**（不是多面板）：顶栏 + 对话流 + 输入框。
- **左侧栏**：新聊天、会话列表、课件列表、作业列表、我的进度。
- **Markdown 渲染** + **翻页课件**（```` ```deck ```` → iframe 内嵌，可收起/关闭）。
- **课件/作业自动沉淀**到左侧栏，点开弹窗回看。
- 多会话存浏览器 localStorage。

## 5. 后端与发布机制

### 后端（stdlib，零依赖）
- `main.py`：`POST /api/chat`（转 Codex + 带历史）、`POST /api/grade`（直连 DeepSeek 判题）、`GET /api/state`（读状态）、静态文件。
- `codex_driver.py`：三注入（cwd / CODEX_HOME / USER_DIR / DEV_CURRICULUM + key）、`chat()` 提取干净回复。
- `llm.py`：直连 DeepSeek。
- `publish.py`：发布流水线。

### 发布机制（关键，不是 Codex 的功能，是自建的）
```
你改 workspace/dev（母本）
  → 跑 python backend/publish.py
  → 把 dev 按白名单复制到 workspace/releases/current/
  → backend spawn Codex 时 -C 指到 current
  → Codex 下次就用新剧本
```
- 发布是**自建的 Python 脚本**，Codex 不知道「发布/版本」这回事，它只是被 `-C` 指到哪个文件夹就读哪个。
- 单人使用：**单版本**（`current`，发布即覆盖），不做版本回滚。
- 要版本回滚时：恢复 publish.py 的版本化（生成 `rYYYYMMDD-NNN`），再让 backend / chat.sh 的 `-C` 指向旧版本目录即可。

## 6. Skills 体系（13 个，怎么教）

skills = 教学**方法**，纯文本 `SKILL.md`，Codex 从 `.codex/skills/` 自动发现、按 AGENTS.md 路由表触发。

| 闭环 | skill |
|---|---|
| 建档 | learner-onboarding（先摸情况，问 ≤2 个问题） |
| 环境 | environment-setup（分系统装 Python/Go） |
| 计划 | learning-plan（倒推阶段）/ codebase-learning-plan（项目逆向） |
| 讲课 | concept-teaching（比喻+示例+预测+练习+翻页课件）/ code-learning（讲具体代码） |
| 练习 | exercise-coach（L0–L5 提示）/ practice-drill（出题刷题） |
| 验收 | assignment-review（批改） |
| 复习 | spaced-review / learning-progress |
| 项目 | project-practice（项目实战，建在 projects/） |
| 沉淀 | knowledge-curator（联网搜→出大纲→边教边写原子） |

配套政策在 `references/`：教学流程、L0–L5 提示、掌握判定（L5 独立迁移才算掌握）、状态契约、策展边界等。

## 7. 知识库（curriculum，教什么）

- **概念图** `concept-map.json`：Python 14 + Go 15 + shared 6 个概念（含先修关系）。
- **知识原子** `atoms/*.md`：最小教案（解决什么/示例/练习/误区/提取记录）。
- **学习路线** `learning-paths/`：入门→项目→精通，6 阶段。
- **库层级** `libraries/{langchain,langgraph,fastapi,numpy-pandas,gin,grpc,cobra}/`：每个库 README + atoms。
- **双形态同步**：一个知识点 = `.md`（事实源）+ `.deck.html`（翻页课件演示），改一个同步改另一个，一起提交。
- **自生长** `knowledge-curator`：教库里没有的主题时，`tools/web_search.py`（DeepSeek 原生 web_search）搜官方文档 → 出大纲 → 边教边把原子写进 `$DEV_CURRICULUM`（dev 母本），有问题反向修订。

## 8. 用户记忆（userdir，唯一可写）

三层记忆：

| 层 | 位置 | 内容 |
|---|---|---|
| 业务记忆 | `userdir/u_yang/`（learning-state.json + profile.md + plans + history） | 学到哪/掌握/计划/误区 |
| 引擎记忆 | `.codex-runtime/home/`（CODEX_HOME） | Codex 会话/sqlite |
| 对话记忆 | 前端 localStorage + 后端 history 注入 | 最近 12 条，防重复问 |

- **状态契约**：写状态走「解析→校验 revision→原子替换→读回→追加事件」四步，任一步失败回滚。
- **单用户**：现在写死 `yang`；多用户时每用户一个 `userdir/u_xxx/`。
- **三层读写**：Global（CODEX_HOME）系统读写；Workspace（releases/current）只读；User（userdir）唯一可写。

## 9. 判题三层（成本可控）

| 层 | 位置 | 成本 |
|---|---|---|
| 前端原生 | 练习闯关/打字 | 0 积分 |
| 直连 DeepSeek | `/api/grade` | 少量 token |
| 完整 agent | `/api/chat` | 走完整 harness |

## 10. 运行方式

```bash
# 启动（唯一要起的）
cd learning-agent-server && python backend/main.py   # → http://127.0.0.1:8787

# 改剧本 + 发布
# 1) 改 workspace/dev 里的文件
# 2) python backend/publish.py   # 复制到 releases/current

# 命令行交互（可选）
./chat.sh   # 用户侧    ./dev.sh   # 作者侧改剧本
```

## 11. 非目标（当前不做）

- 不做多用户鉴权（写死单用户 yang）。
- FastAPI SSE 已发送状态与消息事件；当前 Codex CLI 仍可能整段交付正文，逐 token 输出取决于 harness 是否暴露增量。
- 不做 OS 级硬只读（现在靠副本隔离 + 指令），将来 Docker `:ro`。
- 不做会话常驻（一次性 exec），将来 `app-server --stdio`。
- 不改 Codex 源码、不接飞书、不用 LangGraph。

## 12. 当前状态与待办

已完成：五层架构、前端、后端、13 个 skill、知识库骨架 + 自生长、四大场景路由、判题三层、记忆三层、联网搜索（DeepSeek 原生）。

待办（按优先级）：
1. 流式输出（SSE），解决「等很久以为没反应」。
2. 会话常驻（app-server），用原生记忆替代历史注入补丁。
3. 多用户（URL 带 user_id 起步）。
4. 硬只读（Docker `:ro`）。
5. 版本回滚（若需要，恢复 publish 版本化 + 指针切换）。
6. 补齐进阶 + 库级知识原子（靠自生长边教边填）。
