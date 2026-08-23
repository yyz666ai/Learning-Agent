---
id: go.pointers.parameters-receivers
concept: go.pointers
title: 指针参数、返回指针与指针接收者
prerequisites: [go.pointers.basics]
version: 1
---

## 解决什么问题

把指针作为参数或方法接收者，可以修改调用方持有的同一个值。Go 也允许安全返回局部变量的指针，编译器会负责它的生命周期。

## 最小示例

```go
package main // 声明可运行程序包

import "fmt" // 引入打印工具

type Counter struct { // 定义一个保存计数的结构体
    Value int
}

func (counter *Counter) Add(step int) { // 指针接收者修改原 Counter
    counter.Value += step // 对原值累加，不是修改副本
}

func newCounter() *Counter { // 返回指向新 Counter 的指针
    return &Counter{} // Go 保证返回后该值仍然有效
}

func main() { // 程序入口
    counter := newCounter() // 拿到指针，并保留对同一对象的引用
    counter.Add(2)          // Go 自动解引用后调用方法
    fmt.Println(counter.Value) // 打印 2
}
```

## 课堂检查

- 需要修改接收者，或结构体较大时，通常使用指针接收者。
- 值接收者操作副本；指针接收者可修改原值。

## 课后练习

为 `Account` 结构体写一个指针接收者方法 `Deposit`，让它真正修改余额。

## 常见误区

- 应该修改原值时误用值接收者。
- 把“返回局部变量指针”误当成 Go 中的悬空指针。
