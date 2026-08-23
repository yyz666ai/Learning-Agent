# Python 学习路线（入门 → 项目 → 精通）

> 这是一条「默认路线骨架」，会根据诊断证据调整；每个阶段以「能独立完成的产出」收尾，产出即证据。
> 概念 ID 见 `python/concept-map.json`，概念的详细讲解（知识原子）见 `python/atoms/`。

## 阶段 0 · 环境与第一个程序
- 目标：装好 Python、会跑、会改第一个程序。
- Skill：`environment-setup`（参考 `references/environment-setup.md`）+ `concept-teaching`。
- 概念：`shared.programming.execution` → `python.syntax.values`。
- 产出：终端里 `python3 --version` 通过；改出一句自己的问候语并运行。

## 阶段 1 · 基础语法
- 概念顺序：`shared.programming.control-flow` → `python.control-flow` → `shared.programming.functions` → `python.functions` → `python.collections`。
- 产出：用变量、if/for、函数、list 写一个「猜数字」或「待办清单」小脚本（50 行内），能跑能改。

## 阶段 2 · 进阶组织
- 概念顺序：`python.modules` → `python.errors` → `python.files-json` → `python.objects-types`。
- 产出：把阶段 1 的脚本拆成多模块 + 读写 JSON 存数据 + 加异常处理 + 用类组织一个核心模型。

## 阶段 3 · 工程能力
- 概念：`python.testing-debugging`（+ `shared.engineering.testing` / `shared.engineering.debugging` / `shared.engineering.version-control`）。
- 产出：给自己写的小项目补 3–5 个单元测试，并从一次失败信息定位并修掉一个 bug。

## 阶段 4 · 项目实战（project-practice）
- 候选项目（按兴趣选一个，从零搭，每个项目对应一个方向）：
  - CLI 工具：命令行待办 / 记账（`python.modules`、`files-json`）
  - 爬虫与数据：抓一个网站存成 JSON/CSV（`python.data`、`files-json`）
  - Web API：一个 REST 接口（`python.web`）
  - LLM 应用：带验证的最小 prompt 工作流（`python.llm-apps`）
- 产出：一个能演示的完整小项目 + 一个「变体」独立完成。

## 阶段 5 · 精通/专项（按目标选分支）
- 并发异步：`python.async`
- 算法与复杂度：`python.algorithms`
- 更深的 Web / 数据 / LLM 应用：`python.web`、`python.data`、`python.llm-apps` 的进阶原子

## 判定原则
- 每阶段不是「看完概念」就算过，而是「能独立产出并解释」。执行 `references/mastery-policy.md`。
- 只正式支持 Python、Go；跨语言共享概念见 `shared/concept-map.json`。
