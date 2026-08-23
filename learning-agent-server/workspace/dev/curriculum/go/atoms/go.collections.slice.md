---
id: go.collections.slice
concept: go.collections
title: Slice 切片
prerequisites: [go.control-flow.for-only, go.syntax.values.variables-zero-value]
version: 1
---

## 解决什么问题
让学习者用 slice 存变长有序数据，掌握 append、索引、for range，并理解「slice 是底层数组的视图」这一 Go 特色（复制 slice 会共享底层）。

## 最小示例

```go
package main

import "fmt"

func main() {
	todos := []string{"学变量", "学循环"}
	todos = append(todos, "学切片")

	fmt.Println(todos[0])
	fmt.Println(todos[1:3]) // ["学循环" "学切片"]

	for i, item := range todos {
		fmt.Println(i, item)
	}
}
```

## 交互演示
课件规格：翻页 → 「slice = 会自动变长的一排格子」→ append 会返回新 slice → 切片 `[1:3]` 左闭右开 → for range 拿 (索引, 值) → 「slice 共享底层数组」用一张图讲 → 小测。

## 练习
`$USER_DIR/workspace/demos/go/04_slice/`：建一个清单做增删（用 append + 切片拼接）、遍历打印；再实验 `b := a` 后改 b[0] 看 a 变没变。

## 常见误区
- 忘记接收 append 的返回值（`todos = append(todos, x)` 而不是 `append(todos, x)`）
- 以为 `b := a` 复制了全部元素（共享底层数组）
- 混淆 slice 长度 len 和容量 cap

## 提取记录
- 2026-08-20 v1 种子原子
