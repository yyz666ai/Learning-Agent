# 持久化 Agent 记忆、面试建档与讲义追加练习设计

## 目标

让每个用户和每个学习项目拥有完整、可恢复的数据边界；让 onboarding 的 slot filling、用户修正和对话记忆落到用户目录；让面试岗位、技术栈和自带题目来源真正影响 Plan；让右侧对话框可以通过 Codex harness 为当前 HTML PPT 追加练习。

## 架构原则

采用混合式 Agent 架构：Skill 决定教学意图、追问和内容策略；Codex + DeepSeek 生成 Plan、讲义和题目；Python 只负责 Schema、持久化、路径隔离、去重、版本替换和进度安全。

## 用户与项目数据

每个用户仍以 `userdir/u_<user_id>/` 为唯一写入根。活动项目和归档项目必须包含 `projects/`、`practice-bank/`、`interview-bank/`、`memory/`、`reviews/`、`plans/`、`lessons/`、`curriculum.json`、`profile.md`、`profile.json` 和 `onboarding/`，切换项目时整体替换，不能混用题库或真实练习文件。

用户事实采用三种互补格式：

- JSON：当前事实，例如 `profile.json`、`onboarding/intent-state.json`。
- JSONL：追加事件，例如 `onboarding/intent-events.jsonl`、`memory/conversation-events.jsonl`。
- Markdown：给用户阅读，例如 `profile.md`、课堂笔记和复习讲义。

浏览器 localStorage 只做界面缓存，不再是对话事实源。

## 面试 onboarding

意图槽位新增：

- `target_role`：目标岗位。
- `tech_stack`：岗位对应技术栈，可由用户自由输入或动态选项填充。
- `interview_question_source`：`unknown`、`has_questions`、`none`。

面试路线只有在岗位、真实基础、技术栈和题目来源明确后才生成 Plan。已经在一句话中说明的槽位不得重复询问。缺失时一次只问一个：先问最影响课程范围的技术栈，再问是否有已收集面试题。

如果用户有题，界面邀请直接粘贴，题目先进入个人 Interview Bank，再生成 Plan；如果没有，Plan 前执行 `new-topic-research`，根据岗位与技术栈建立题图。用户后来追加题目时合并 Plan，但保留完成进度。

## 对话与讲义修改

普通对话的用户消息和最终 Agent 回复都追加到 `memory/conversation-events.jsonl`。存在当前 lesson 时，问题和回答继续写入课堂笔记。

用户要求“再出几道题”时，后端通过项目内 Codex CLI 读取 `practice-drill` 和 `quiz-designer` Skill 生成题目。Python 校验题目、答案和重复项后：

1. 加入统一题库；
2. 如果请求携带当前 lesson id，将新题作为 `check` 页面插入现有 mastery 页之前；
3. 原子保存新讲义和答案，失败时旧讲义不变；
4. 前端重新加载当前 PPT，并保留当前课程与已完成进度。

## 错误边界

- 模型输出不合法：不写题库、不替换讲义。
- lesson id 与当前课程不一致：只加入题库，不修改 PPT，并明确返回状态。
- 项目切换失败：恢复旧项目快照。
- slot 证据不是用户原话或已确认状态：拒绝进入 Plan。
- Skill 修改只有 publish 后才进入运行快照。

## 验收

- 刷新 onboarding 后可以恢复未完成槽位。
- `profile.json` 包含岗位、技术栈和题目来源。
- 两个学习项目的题库和真实练习目录互不串用。
- “AI 前端面试，初学”只补问技术栈和题目来源，不问通用学习目标。
- “再出 3 道题并加到当前 PPT”使用 Codex harness，题库和 PPT 同时增加，失败时旧数据不变。
- GitHub 仍不包含用户目录和私人对话。
