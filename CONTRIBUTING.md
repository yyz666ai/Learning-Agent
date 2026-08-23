# Contributing to Learning Agent

[简体中文](#简体中文) · [English](#english)

## 简体中文

感谢你参与 Learning Agent 的知识库共创。这个仓库不仅接受代码 PR，也欢迎教师、学习者和工程师贡献更清楚的解释、更真实的项目、更好的题目与常见误区。

### 贡献类型

| 类型 | 修改位置 | 示例 |
|---|---|---|
| 知识原子 | `learning-agent-server/workspace/dev/curriculum/<topic>/atoms/` | Go 指针、Python 生成器、RAG 检索 |
| 学习路线 | `curriculum/<topic>/learning-paths/` | 从零到工程师、面试冲刺 |
| 框架/库 | `curriculum/<topic>/libraries/<library>/` | LangGraph、FastAPI、Gin |
| 教学 Skill | `workspace/dev/.codex/skills/<skill>/` | 出题、讲代码、复习、项目辅导 |
| 教学政策 | `workspace/dev/references/` | 掌握标准、提示政策、策展政策 |
| 产品代码 | `frontend/`、`backend/`、`tests/` | UI、API、状态机、流式输出 |

### 知识原子要求

先阅读 [`ATOMS.md`](learning-agent-server/workspace/dev/curriculum/ATOMS.md)。一个知识原子至少包含：

- 唯一 `id`、对应 `concept`、标题、先修和版本；
- “解决什么问题”，先建立直觉；
- 可运行、足够小、带教学注释的示例；
- 交互演示或 HTML PPT 设计；
- 课堂理解题与课后独立练习；
- 常见误区与边界；
- 可核验的官方文档、标准、论文或权威仓库来源。

不要提交：未经验证的模型幻觉、真实用户对话、个人信息、API Key、受版权保护的大段原文，或无法运行的示例。

### 修改 Skill 的要求

Skill 管“怎么教”，不是某个知识点的事实内容。修改 Skill 时必须同步：

1. `SKILL.md` 中的行为规则；
2. `evals/evals.json` 中至少一个能暴露旧行为问题的案例；
3. `tests/test_teaching_contract.py` 或相关契约测试；
4. 必要时更新 `AGENTS.md` 路由，但不要把具体课程内容写进总路由。

### PR 流程

```bash
git clone https://github.com/<your-name>/Learning-Agent.git
cd Learning-Agent
git checkout -b curriculum/<short-topic>

cd learning-agent-server
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 修改后校验
python workspace/dev/tools/validate_workspace.py
python -m pytest -q
python -m backend.publish
```

提交信息建议：

```text
curriculum: add Go pointer receiver atom
skill: improve beginner environment guidance
fix: prevent duplicate learning projects
docs: expand DeepSeek setup guide
```

### PR 检查清单

- [ ] 没有密钥、Token、真实用户数据和本机绝对路径；
- [ ] 知识事实有可核验来源；
- [ ] 示例可以运行并包含必要注释；
- [ ] 选择题答案存在且与选项一致；
- [ ] 课堂练习和课后练习明确分开；
- [ ] Workspace validator 通过；
- [ ] 完整测试通过；
- [ ] PR 描述说明“为什么这样更容易学会”。

## English

Learning Agent welcomes code contributions and community-maintained curriculum. You can add knowledge atoms, learning paths, framework coverage, diagrams, quizzes, assignments, misconceptions, interview questions, teaching Skills, tests, or product improvements.

Before opening a pull request:

1. Keep teaching policy in `.codex/skills/` and factual curriculum in `curriculum/`.
2. Use authoritative sources for version-sensitive facts.
3. Keep examples runnable, small, and well commented.
4. Never commit secrets, learner records, private conversations, or machine-specific absolute paths.
5. Run:

```bash
cd learning-agent-server
.venv/bin/python workspace/dev/tools/validate_workspace.py
.venv/bin/python -m pytest -q
.venv/bin/python -m backend.publish
```

In the PR description, explain what learning problem the change solves and how you verified it.
