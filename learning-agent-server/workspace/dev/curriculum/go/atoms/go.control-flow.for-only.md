---
id: go.control-flow.for-only
concept: go.control-flow
title: Go 的 for——唯一的关键字，三种形态
prerequisites: [go.syntax.values]
version: 1
---

## 解决什么问题

Go 设计者的哲学：一种循环就够了。Go 没有 `while`、没有 `do-while`，只有 `for`——但用三种写法覆盖全部场景。学会拆解这三种形态，就能读懂任何 Go 循环。

## 最小示例

```go
// 形态 1：C 式（初始; 条件; 步进）
for i := 0; i < 3; i++ {
    fmt.Printf("第 %d 轮\n", i)
}

// 形态 2：while 式（只有条件）
n := 3
for n > 0 {
    n--
}

// 形态 3：无限循环
for {
    break // 记得跳出来
}

// 遍历：for range
fruits := []string{"苹果", "香蕉"}
for index, fruit := range fruits {
    fmt.Println(index, fruit)
}
```

## 交互演示

课件 deck：`user-data/workspace/demos/decks/loops-python-vs-go.html`（与 Python 原子共用一套双栏步进演示）

翻页结构见 Python 版原子。Go 侧重点：三种形态对照表、range 的值拷贝陷阱（`fruit` 是副本，改它不影响切片）。

## 练习

`user-data/workspace/demos/go/02_loops/main.go`（倒计时、九九乘法表、求和三个 TODO）

## 常见误区

- 找 `while` 关键字（Go 没有，`for 条件 { }` 就是 while）
- `for i, v := range s` 里改 `v` 以为会改到 `s[i]`（v 是副本，要改就 `s[i] = ...`）
- 遍历 map 以为有固定顺序（每次运行顺序可能不同）

## 提取记录

- 2026-08-16 v1 首次提取（来源：v0.2 交互课件试点会话，配套 Python 对照原子）
