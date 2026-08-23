---
name: plan-revision
description: Use when a learner reviews a draft learning plan and asks to change pace, depth, outcomes, projects, practice balance, deadline, or topic coverage.
---

# 学习计划修订

把用户意见转成新的 Plan 版本，同时保留已完成进度。修改计划不是重新建档，也不能把已经完成的章节变回未开始。

## 执行

1. Plan 审阅中，**对话输入框中的文字直接视为修改意见**；不要求用户先点“调整计划”。读取当前 Plan、用户原话、目标、时间和进度基线。
2. 先判断影响范围：节奏、内容深度、练习方式、最终项目或全局路线。
3. 只修改必要章节；已完成节点保持完成，当前节点保持可定位。
4. 输出完整新 Plan 与 `revision_summary`，明确增加、删除、提前和推后的内容。
5. 将完整新 Plan 重新作为 Agent 对话消息展示；下方仍只有一个确认按钮，用户确认后才替换活动 Plan。

## 边界

- 不因新增题目重置总进度。
- 目标发生根本变化时建议建立新学习项目，不污染原项目。
- 修订失败继续使用旧版本。
