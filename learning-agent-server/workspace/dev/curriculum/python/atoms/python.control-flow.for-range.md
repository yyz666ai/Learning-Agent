---
id: python.control-flow.for-range
concept: python.control-flow
title: for 循环与 range
prerequisites: [python.syntax.values]
version: 1
---

## 解决什么问题

重复做同一件事 100 次，不该复制粘贴 100 行代码。Python 的 `for` 为"遍历"而生：它依次从任何可迭代对象里取元素，取完自动结束，不需要自己维护计数器。

## 最小示例

```python
for i in range(3):
    print(f"第 {i} 轮")

fruits = ["苹果", "香蕉"]
for fruit in fruits:
    print(fruit)
```

## 交互演示

课件 deck：`user-data/workspace/demos/decks/loops-python-vs-go.html`

翻页结构：封面 → 为什么需要循环 → Python for 逐行执行 → Go for 对照 → 双栏步进执行器（按钮逐行对照）→ 陷阱对照（改循环变量不影响迭代；range 是惰性的）→ 随堂小测 2 题 → 练习衔接。

风语气调：轻松幽默，用"工具人 i"等比喻，陷阱页用故意翻车的例子。

## 练习

`user-data/workspace/demos/python/03_loops.py`（倒计时、九九乘法表、求和三个 TODO）

## 常见误区

- 以为 `for i in range(3)` 里改 `i` 会影响下一轮迭代（不会，每轮重新赋值）
- 以为 `range(1, 5)` 包含 5（不包含，左闭右开）
- 在循环里想同时拿下标和值时手写 `fruits[i]`（应该用 `enumerate(fruits)`）

## 提取记录

- 2026-08-16 v1 首次提取（来源：v0.2 交互课件试点会话，配套 Go 对照原子）
