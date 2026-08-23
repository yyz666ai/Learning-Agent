---
id: go.pointers.basics
concept: go.pointers
title: 指针基础：地址、& 和 *
prerequisites: [go.syntax.values.variables-zero-value, go.functions.multi-return]
version: 1
---

## 解决什么问题

普通变量保存值，指针保存这个值在内存中的地址。它让函数能修改同一份数据，也避免复制较大的值。

## 最小示例

```go
package main // 声明可独立运行的程序包

import "fmt" // 引入打印工具，便于观察值和地址

func main() { // 程序从 main 函数开始
    score := 60       // score 直接保存整数 60
    pointer := &score // &score 取出 score 的内存地址
    *pointer = 90     // *pointer 沿着地址找回原值并修改它
    fmt.Println(score) // 原变量现在是 90
}
```

## 课堂检查

- `&value` 是“取地址”，`*pointer` 是“沿地址读或写值”。
- 指针的零值是 `nil`，解引用 `nil` 指针会引发运行时错误。
- Go 不支持 C 风格的指针算术。

## 课后练习

写一个最小程序：建立整数、获取地址、通过指针修改它，并在每行写中文注释。

## 常见误区

- 混淆“指针本身”和“指针指向的值”。
- 在没有检查 `nil` 时直接解引用。
