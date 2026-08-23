---
id: python.functions.def-and-return
concept: python.functions
title: 定义函数与 return
prerequisites: [python.control-flow.if-elif-else]
version: 1
---

## 解决什么问题
让学习者把一段逻辑封装成可复用的函数，分清「参数（输入）」「return（输出）」和「print（只是显示）」。

## 最小示例

```python
def add(a, b):
    return a + b

result = add(3, 4)
print(result)      # 7
print(add(3, 4))   # 也是 7，因为先算 return 再 print
```

## 交互演示
课件规格：翻页 → 「函数 = 机器：投原料（参数），出产品（return）」→ 逐行点看 `return` 如何把值交回调用处 → 对比 `print` vs `return`（关键）→ 作用域一句带过 → 小测。

## 练习
`$USER_DIR/workspace/demos/python/03_functions/`：写 `max_of_three(a,b,c)` 和 `is_even(n)`，并解释「为什么不 print 而是 return」。

## 常见误区
- 把 `print` 当 `return`（打印 ≠ 返回，函数默认 return None）
- 忘记 `return` 导致拿到 `None`
- 以为函数外的变量在函数内改会「永久生效」

## 提取记录
- 2026-08-20 v1 种子原子
