---
name: visual-explainer
description: Use when a programming concept depends on sequence, state change, branching, data flow, ownership, hierarchy, lifecycle, or several components interacting.
---

# 可视化讲解

图只服务一个关键判断。流程、状态变化、调用顺序、分支和组件关系优先用 Mermaid，让学习者先看到全貌，再进入代码。

## 选择图型

- 执行步骤或条件分支：`flowchart` 流程图。
- 请求、回调或消息先后：`sequenceDiagram`。
- 状态迁移：`stateDiagram-v2`。
- 模块依赖或目录：`flowchart` 或 `classDiagram`，保持节点少。

## 教学要求

1. 图前先提出要观察的问题，图后只解释最关键的 2–4 个关系。
2. 节点使用学习者能理解的中文，首次出现的代码名用括号补充。
3. Mermaid 必须可以独立渲染；不把整份代码塞进图。
4. LangGraph、请求链、状态机和并发顺序等主题，只要图能显著降低理解成本，就在代码之前安排图。
5. 图后紧跟一个点击判断或最小代码映射，确认学习者能把图和代码对应起来。
