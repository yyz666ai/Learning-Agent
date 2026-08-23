# 策展政策（Curation Policy）

## 总原则：默认不改，共性反复才反向沉淀

workspace（skills + curriculum + references）是「剧本」，运行时**只读**。默认不修改；只有当共性需求/误区**反复出现**时，才由作者反向沉淀新知识。策展是**事件驱动**，不是定时任务。

## 触发条件（满足其一才改）

1. 同类问题或误区在**多个会话 / 多个用户**中反复出现（≥2 次，或明显普遍）。
2. 某次讲解/练习被验证有效（用户在 L5 独立迁移题答对）→ 提取为知识原子。
3. 用户明确指出课程缺口（"这里没讲清楚"）。

## 两种策展模式

1. **反向沉淀（作者侧，默认）**：共性需求/误区反复出现时，作者在 dev 改，发布生效。
2. **自生长（运行时，`knowledge-curator`）**：教一个 curriculum 里没有的主题时，agent 边教边把知识原子写进 `curriculum/`（atoms/learning-paths/README），git 留痕。这是知识库「越长越全」的机制。

## 分层边界（谁能改什么）

| 层 | 位置 | 运行时 | 策展权 |
|---|---|---|---|
| 业务 skills（方法/流程） | `workspace/.codex/skills/` | 只读 | 作者改 + 用户确认 + 发布生效 |
| 知识内容（课程/原子） | `workspace/curriculum/` | **可自生长**（knowledge-curator 写 atoms） | 作者可 commit；agent 自生长需「教学需要 + 有证据」 |
| 政策/规则（references、AGENTS.md、schemas、tools） | `workspace/references/` 等 | 只读 | 必须用户显式确认 |
| 用户记忆（数据） | `$USER_DIR/`（userdir） | **可写（唯一）** | 永不因策展被改 |

## 动作流程

1. 定位共性证据（来自 `$USER_DIR/history/` 的误区/提问记录）。
2. 作者在 `workspace/dev` 修改：新增/修订知识原子、追加误区、调整练习（curriculum 层可直接 commit）；改 skills / references / AGENTS.md 前需用户确认。
3. git commit，提交信息注明触发原因 + 共性证据来源。
4. 发布新版本生效（`backend/publish.py`）；用户端仍用旧版本，可回滚。

## 硬边界

- 运行时 agent **永不写 skills / references / AGENTS.md / schemas / tools**；只有 `knowledge-curator` 可写 `curriculum/`（且仅 atoms/learning-paths/README，需有教学证据）。
- 被要求"改课程"时：若属于知识内容，可走自生长；若涉及规则/方法，明确告知需作者 + 用户确认。
- 用户学习状态（`$USER_DIR/`）永不因策展被修改。
- 一次策展只针对一类信号，不顺手大改无关内容。
- Markdown 原子与 HTML deck 必须同步：改一个，同步改另一个（`.md` ↔ `.deck.html`）。
- harness 通用 skills（`$CODEX_HOME/skills/`，如 html-artifact、web-research）不归本政策管——那是 Codex/harness 自带能力。
