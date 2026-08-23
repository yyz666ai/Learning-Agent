---
name: adaptive-onboarding
description: Use when a learner has supplied a new topic and goal, and the system needs a short clickable diagnostic before making a personalized learning plan.
---

# 自适应建档与诊断

建档的目的只是决定从哪里开始，不是考倒用户。主题由用户在唯一对话输入框自由输入或语音输入；不先要求点“新学习”。显式概念问句直接绕过本诊断，**领域学习才进入目标选择**，再根据需要选水平和时长。画像已确认时不得重复询问已知信息。

## 诊断分流

- 概念速学（`concept_clarity`）：不进入本诊断。概念速学不做起点诊断；`meaning_only` 直接开讲，`code_walkthrough` 最多只取一个代码熟悉度选择。
- 零基础：不诊断，直接开始最小可运行第一课。
- 学过一点：生成 3 道选择题；只有答案明显矛盾时才加第 4 道。
- 熟练者：生成 3 道情境题，优先边界、调试、项目取舍或迁移，不考死记语法。

## 题目选择

题目必须匹配主题与目标：看懂项目优先入口、调用链和错误定位；面试优先简答前的关键判断与追问方向；项目实战优先真实请求流、依赖和调试；语言系统学习覆盖最影响起点的语法、心智模型和错误处理。

每题只有一个判断点，2–4 个可点击选项。不要要求输入文字、写代码或解释。输出严格 JSON `questions`，只含 3–4 道题及答案键。

## 交接

诊断结果写入画像与计划上下文。它可以跳过已会内容、增加薄弱点练习，但不能直接标记长期掌握。随后路由 `learning-plan`，并由 `adaptive-lesson-flow` 开始第一课。
