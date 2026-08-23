---
id: go.syntax.values.variables-zero-value
concept: go.syntax.values
title: 变量、类型与零值
prerequisites: [go.syntax.values.first-program]
version: 1
---

## 解决什么问题
让学习者理解 Go 的静态类型与「零值」：`var` 声明的变量会自动获得类型对应的零值（int→0、string→""、bool→false），并用 `:=` 做短声明。

## 最小示例

```go
package main

import "fmt"

func main() {
	var name string        // 零值 ""
	var age int            // 零值 0
	lang := "Go"           // := 短声明，自动推断

	fmt.Println(name, age, lang)
	fmt.Println(name == "", age == 0)
}
```

## 交互演示
课件规格：翻页 → 「Go 的变量类型是钉死的」→ 零值表（int/string/bool/float）→ `var` vs `:=` 对比 → 逐行点看 `fmt.Println` 输出 → 小测：预测某个 `var` 后的零值。

## 练习
`$USER_DIR/workspace/demos/go/01_variables/`：声明几个不同类型的变量（不赋值）打印零值；再用 `:=` 声明并赋值，验证两种写法。

## 常见误区
- 以为零值 = 未初始化不可用（零值可直接用）
- 在函数外乱用 `:=`（包级只能 `var`）
- 给已声明变量重复 `:=`（同作用域下会报「no new variables」）

## 提取记录
- 2026-08-20 v1 种子原子
