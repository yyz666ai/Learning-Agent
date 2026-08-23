---
id: go.syntax.values.first-program
concept: go.syntax.values
title: 你的第一个 Go 程序
prerequisites: []
version: 1
---

## 解决什么问题
零基础学习者的第一课：程序是什么（给电脑的菜谱），以及六行 Hello World 每行的岗位。让学习者在 10 分钟内完成"写→跑→改"完整循环。

## 最小示例

```go
package main

import "fmt"

func main() {
	fmt.Println("Hello, Go!")
}
```

## 交互演示
课件：`user-data/workspace/demos/decks/lesson-01-hello-go.html`
- 翻页结构：封面 → 程序=菜谱 → 逐行点击拆解（重点交互）→ 运行四步教学（开终端→cd→go run→看输出）+ 终端模拟（打字机动效）→ 三个"改一改"变体 tabs → 小测 2 题 → 练习衔接
- **翻页检测门**：关键页设置 checkpoint，点「下一页」时弹题（选择或代码题），答对放行（含跳过兜底）；代码题用**前端规则判断**（正则要素检查 + L0 级逐条提示），不接外部 API、不需要后端
- 逐行拆解要点：package main（入口包）/ import fmt（借工具）/ func main（起点）/ Println（打印+换行）/ }（结束）
- 比喻库：菜谱比喻（程序）、工具箱比喻（fmt）、"执行力满分理解力为零"（bug 由来）
- 课件工程规范（踩坑记录）：固定 1280×720 画布 + JS 整体缩放防溢出；内容区 justify-content:flex-start 避免标题下大空洞；pre 必须 pre-wrap + max-width:100%，网格子项 min-width:0，否则长代码横向顶破布局

## 练习
`user-data/workspace/demos/go/00_hello/main.go`：改问候语 / 加自我介绍 / 猜测并验证 `Println("1+2 =", 1+2)`

## 常见误区
- 以为程序从文件第一行开始执行（实际从 main 函数开始）
- 分不清"字符串"（引号内原样打印）和"数字"（先计算再打印）
- 大小写敏感：println ≠ Println
- 以为 import 是可有可无的装饰（不用 fmt 就别 import，用了就必须 import）

## 提取记录
- 2026-08-16 v1 首次提取（来源：首个建档学习者第 1 课，零基础起点）
