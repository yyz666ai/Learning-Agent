---
id: go.functions.multi-return
concept: go.functions
title: 函数与多返回值
prerequisites: [go.control-flow.if-switch]
version: 1
---

## 解决什么问题
让学习者定义带参数和返回值的函数，掌握 Go 独有的「多返回值 + 惯用 (value, error)」模式，并解释值传递。

## 最小示例

```go
package main

import (
	"errors"
	"fmt"
)

func divide(a, b int) (int, error) {
	if b == 0 {
		return 0, errors.New("不能除以 0")
	}
	return a / b, nil
}

func main() {
	result, err := divide(10, 2)
	if err != nil {
		fmt.Println("出错：", err)
		return
	}
	fmt.Println("结果：", result)
}
```

## 交互演示
课件规格：翻页 → 「函数 = 机器」→ 参数与返回类型声明 → 多返回值（先结果后 error）→ `if err != nil` 惯用法 → 值传递一句话 → 小测。

## 练习
`$USER_DIR/workspace/demos/go/03_functions/`：写 `add/sub/mul/div` 四个函数（div 返回 error），在 main 里调用并处理错误。

## 常见误区
- 以为多返回值是「返回一个数组」（是独立的两个值）
- 忽略 error（不检查 `if err != nil`）
- 以为传入函数的结构体会被函数修改（值传递，除非传指针）

## 提取记录
- 2026-08-20 v1 种子原子
