---
id: python.control-flow.if-elif-else
concept: python.control-flow
title: if / elif / else 条件分支
prerequisites: [python.syntax.values.variables-and-types]
version: 1
---

## 解决什么问题
让学习者用条件让程序「根据不同情况走不同路」，理解布尔表达式、缩进和「先匹配谁先走」。

## 最小示例

```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 60:
    grade = "B"
else:
    grade = "C"

print(grade)
```

## 交互演示
课件规格：翻页 → 「分支 = 岔路口」→ 逐行点 `if`/`elif`/`else` 看执行路径 → 缩进的重要性（同缩进 = 同一块）→ 比较运算符表（> < >= <= == !=）→ 小测：给定 score 预测输出。

## 练习
`$USER_DIR/workspace/demos/python/02_if/`：写一个「温度穿衣建议」或「成绩评等级」，至少三种分支，自己跑几个边界值（59 / 60 / 90）。

## 常见误区
- 忘记冒号 `:` 或缩进不一致
- 以为 `elif` 是必须的（可只有 if，或多 if 串联）
- 用 `=` 代替 `==` 做比较

## 提取记录
- 2026-08-20 v1 种子原子
