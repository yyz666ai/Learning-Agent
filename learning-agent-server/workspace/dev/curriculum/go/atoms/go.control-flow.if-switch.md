---
id: go.control-flow.if-switch
concept: go.control-flow
title: if 与 switch
prerequisites: [go.syntax.values.variables-zero-value]
version: 1
---

## 解决什么问题
让学习者用 `if`/`else if`/`else` 和 `switch` 表达分支，理解 Go 的 `if` 可以带初始化语句、`switch` 不需要 break。

## 最小示例

```go
package main

import "fmt"

func main() {
	score := 85

	if score >= 90 {
		fmt.Println("A")
	} else if score >= 60 {
		fmt.Println("B")
	} else {
		fmt.Println("C")
	}

	switch {
	case score >= 90:
		fmt.Println("优秀")
	case score >= 60:
		fmt.Println("及格")
	default:
		fmt.Println("加油")
	}
}
```

## 交互演示
课件规格：翻页 → 「if = 岔路口」→ Go 的 if 可带 `if n := ...; n > 0` 初始化 → switch 的 case 自动终止（无需 break）→ 对比 if-else 链 → 小测。

## 练习
`$USER_DIR/workspace/demos/go/02_if/`：写一个「分数评等级」，用 if-else 和 switch 各实现一遍，跑几个边界值。

## 常见误区
- 在 `if (x > 0)` 里加括号（Go 风格不写括号，写了也能编译但不地道）
- 以为 switch 的 case 会 fall-through 到下一个 case（Go 默认 break）
- 忘记花括号或写错缩进

## 提取记录
- 2026-08-20 v1 种子原子
