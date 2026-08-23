---
name: lesson-revision
description: Use when a learner says the current deck is too shallow, too long, too textual, too difficult, inaccurate, poorly paced, missing diagrams, or asks to regenerate or change specific lesson pages.
---

# 讲义修订

把学习者的自然语言反馈变成局部、可撤回的新讲义版本。先理解问题，再修改真正受影响的页面；不把一次意见变成所有课程的永久规则。

## 执行

1. 读取当前页、整章 Manifest、用户原话、已通过题目和运行要求。
2. 判断反馈属于深度、节奏、图解、代码、题目、错误或可读性。
3. 只重新生成受影响页面；保持未修改页面 ID、答案键和输出要求稳定。
4. 输出 `revision_summary` 和新版本草案，在对话框提供 `应用新版本` 与 `继续旧版本`。
5. 应用新版本时保留旧版本、当前章节、已完成进度和用户文件；失败时继续显示旧讲义。

## 教学修订优先级

- “看不懂长代码”：先用 `progressive-code-teaching` 拆分。
- “不知道怎么流转”：用 `visual-explainer` 加 Mermaid。
- “讲得太浅”：补因果、边界和可运行变化，不堆定义。
- “题目不合适”：用 `quiz-designer` 改关键判断，不单纯增加题量。

完成章节并通过验收后，改进版才交给 `knowledge-curator` 沉淀。
