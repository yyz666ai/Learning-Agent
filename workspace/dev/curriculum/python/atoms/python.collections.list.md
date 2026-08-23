---
id: python.collections.list
concept: python.collections
title: 列表 list
prerequisites: [python.control-flow.for-range, python.syntax.values.variables-and-types]
version: 1
---

## 解决什么问题
让学习者用 list 存一组有序数据，掌握索引、切片、append、遍历，并理解「复制 list 变量」和「复制元素」的区别。

## 最小示例

```python
todos = ["学变量", "学循环", "学函数"]
todos.append("学列表")

print(todos[0])        # 学变量
print(todos[1:3])      # ['学循环', '学函数']

for item in todos:
    print("待办：", item)
```

## 交互演示
课件规格：翻页 → 「list = 一排贴了门牌号的格子（索引从 0 起）」→ 索引/切片/append 逐行演示 → 遍历 → 「变量名只是指向列表的标签」→ 小测：给定切片预测结果。

## 练习
`$USER_DIR/workspace/demos/python/04_list/`：建一个购物清单，练习增删改查 + 遍历打印，再验证 `b = a` 后改 b 会不会影响 a（理解引用）。

## 常见误区
- 索引从 0 开始，`list[1]` 是第二个
- 以为 `b = a` 会复制一份（实际是同一列表的两个名字）
- 切片 `[1:3]` 不包含索引 3

## 提取记录
- 2026-08-20 v1 种子原子
