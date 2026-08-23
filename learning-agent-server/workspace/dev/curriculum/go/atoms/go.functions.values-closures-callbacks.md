---
id: go.functions.values-closures-callbacks
concept: go.functions
title: 函数值、函数类型、闭包与回调
prerequisites: [go.functions.multi-return, go.pointers.basics]
version: 1
---

## 解决什么问题

Go 使用函数值和函数类型，让函数可以被保存、传参和返回。这是实现回调、策略和中间件的基础，不是 C/C++ 式函数指针。

## 最小示例

```go
package main // 声明可运行程序包

import "fmt" // 引入打印工具

type Operation func(int, int) int // 定义一种函数类型，不是 C 式指针

func apply(a, b int, operation Operation) int { // 把函数当作参数传入
    return operation(a, b) // 在这里回调具体函数
}

func multiplier(factor int) func(int) int { // 返回一个闭包
    return func(value int) int { // 匿名函数记住外层的 factor
        return value * factor
    }
}

func main() { // 程序入口
    add := func(a, b int) int { return a + b } // 把匿名函数存入变量
    fmt.Println(apply(2, 3, add))               // 传入函数值，结果是 5
    double := multiplier(2)                    // 闭包保留 factor=2
    fmt.Println(double(4))                     // 输出 8
}
```

## 课堂检查

- 函数类型由参数和返回值共同决定。
- 闭包会捕获外层作用域中的变量，要注意共享变量的生命周期和并发访问。

## 课后练习

实现一个 `filter`：接收整数切片和判断函数，返回符合条件的元素。

## 常见误区

- 把 Go 函数值叫成“函数指针”，并误以为它支持指针算术。
- 忽略闭包捕获的是变量，不是每次都复制一份值。
