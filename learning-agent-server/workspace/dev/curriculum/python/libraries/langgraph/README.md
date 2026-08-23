# LangGraph（图/状态机编排 Agent）

## 是什么
用「图 + 状态」来编排多步 Agent 流程的库：节点是步骤、边是流向、状态在节点间流转。适合做**每步可控**的 Agent（这也是你学习项目里「harness」那类东西的 Python 版思路）。

## 前置
- LangChain 基础（`libraries/langchain`）或 Python 函数/类扎实
- 理解「状态 + 控制流」概念（`shared.programming.control-flow`）

## 学什么（路线骨架）
1. State 与 Node（状态图基础）
2. 边与条件路由
3. 循环与中断（interrupt）
4. 持久化与 Checkpointer
5. 子图 / 多 Agent 协作

## 原子
见 `atoms/`（初始为空，边教边沉淀）。
