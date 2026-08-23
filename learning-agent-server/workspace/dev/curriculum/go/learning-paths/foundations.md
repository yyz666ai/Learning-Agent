# Go 学习路线（入门 → 项目 → 精通）

> 默认路线骨架，会按诊断证据调整；每阶段以「能独立完成的产出」收尾，产出即证据。
> 概念 ID 见 `go/concept-map.json`，概念详解（知识原子）见 `go/atoms/`。

## 阶段 0 · 环境与第一个程序
- 目标：装好 Go、会 `go run`、会改第一个程序。
- Skill：`environment-setup`（参考 `references/environment-setup.md`）+ `concept-teaching`。
- 概念：`shared.programming.execution` → `go.syntax.values`。
- 产出：`go version` 通过；改出自己的问候语并 `go run` 成功。

## 阶段 1 · 基础语法
- 概念顺序：`shared.programming.control-flow` → `go.control-flow` → `shared.programming.functions` → `go.functions` → `go.collections`。
- 产出：用变量、if/for/switch、多返回值函数、slice/map 写一个「猜数字」或「字数统计」CLI（50–100 行），能跑能改。

## 阶段 2 · 指针、函数值、类型与错误（Go 的核心心法）
- 概念顺序：`go.pointers.basics` → `go.pointers.parameters-receivers` → `go.functions.values-closures-callbacks` → `go.structs-methods` → `go.interfaces` → `go.errors-defer`。
- 产出：用 struct 建模 + 一个小 interface（如两个实现可互换）+ 显式 error 传播，讲清「指针 vs 值」「interface 是行为契约」。

## 阶段 3 · 工程能力
- 概念顺序：`go.packages-modules` → `go.testing-debugging`（+ `shared.engineering.version-control`）。
- 产出：按 cmd/internal 分层组织一个小项目，写表驱动测试，从失败定位并修一个 bug。

## 阶段 4 · 项目实战（project-practice）
- 候选项目（按兴趣选一个，从零搭）：
  - CLI 工具：TODO / 文件处理（`go.packages-modules`、`go.errors-defer`）
  - HTTP API：一个 REST 服务（`go.http`、`go.interfaces`）
  - 并发程序：多任务下载 / 批量抓取（`go.goroutines`、`go.channels`、`go.context`）
  - **mini Agent harness**：一个读配置、调 Provider、执行工具的极简循环
- 产出：一个能演示的完整小项目 + 一个「变体」独立完成。

## 阶段 5 · 精通/专项（按目标选分支）
- 并发：`go.goroutines` → `go.channels` → `go.context`
- 服务端：`go.http` → `go.database`
- 目标代码理解：结合 `codebase-learning-plan` 逐章啃一个真实项目（由学习者提供路径）

## 判定原则
- 每阶段看「独立产出 + 解释」，执行 `references/mastery-policy.md`；运行通过不等于掌握。
- 只正式支持 Python、Go；跨语言共享概念见 `shared/concept-map.json`。
