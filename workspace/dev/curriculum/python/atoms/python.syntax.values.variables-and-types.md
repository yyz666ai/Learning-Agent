---
id: python.syntax.values.variables-and-types
concept: python.syntax.values
title: 变量、值与类型
prerequisites: [python.syntax.values.first-program]
version: 1
---

## 解决什么问题
让学习者理解「变量是贴了名字的值」以及 Python 常见的几种值类型（int / float / str / bool），能自己声明、赋值、打印，并预测 `+` 在不同类型上的行为。

## 最小示例

```python
name = "小狐狸"
age = 3
height = 1.2
is_learning = True

print(name, age, height, is_learning)
print(type(name), type(age))
```

## 交互演示
课件规格：翻页 → 「变量 = 贴名字的盒子（但盒子可以换内容）」→ 类型四宫格（int/float/str/bool）→ 逐行点击看 `type()` 结果 → `+` 的两种行为（数字相加 vs 字符串拼接）→ 小测 2 题（前端规则判断）。

## 练习
`$USER_DIR/workspace/demos/python/01_variables/`：声明自己的名字/年龄/身高，打印；再预测并验证 `"3" + 4` 会怎样（应报错）。

## 常见误区
- 以为变量一旦是数字就永远是数字（Python 变量可重新绑定不同类型）
- 以为 `"3" + 4` 会得到 7（字符串和数字不能直接相加）
- 分不清 `=`（赋值）和 `==`（比较）

## 提取记录
- 2026-08-20 v1 种子原子（配合 environment-setup 阶段 0/1 路线）
