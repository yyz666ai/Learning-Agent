# 知识原子（Knowledge Atoms）

## 是什么

知识原子是**最小可复用的教学单元**：一个原子 = 一个知识点 + 讲解 + 最小示例 + 交互演示规格 + 练习 + 常见误区。它比 concept-map 里的概念（如 `python.control-flow`）细得多——一个概念通常拆成 5–15 个原子。

核心价值：**讲得好的课只造一次**。某次会话里打磨出的优质讲解、动效课件、练习和误区记录，提取为原子后，后续所有用户、所有会话直接复用，不再从零重建。

## 位置与命名

```
curriculum/python/atoms/python.control-flow.for-range.md
curriculum/go/atoms/go.control-flow.for-only.md
```

- 路径：`curriculum/<lang>/atoms/<原子ID>.md`
- 原子 ID 规则：`<语言>.<所属概念concept-map ID>.<子主题>`，全小写，连字符分隔
- 每个原子的 `concept` 字段必须能在 `<lang>/concept-map.json` 中找到对应概念

## 文件格式

```markdown
---
id: python.control-flow.for-range
concept: python.control-flow        # 必须存在于 concept-map.json
title: for 循环与 range
prerequisites: [python.syntax.values]  # 原子 ID 或概念 ID，可空
version: 1
---

## 解决什么问题
一两句话，先讲"没有它会怎样"。

## 最小示例
能运行的最短代码，不超过 15 行。

## 交互演示
给课件生成器的规格：翻页结构、逐行步进、对照语言（如对照 Go 版原子）、小测题目。
可指向已生成的 deck：user-data/workspace/demos/decks/<name>.html

## 练习
指向 user-data/workspace/demos/ 下的练习文件，标注 TODO 位置。

## 常见误区
- 误区描述（来自 concept-map 初始集或学习历史提取）

## 提取记录
- 2026-08-16 v1 首次提取（来源：v0.2 交互课件试点会话）
```

## 提取与进化规则（事件驱动）

见 `references/curation-policy.md`。要点：

1. **触发**：同类问题/误区在多个会话或多名用户中反复出现，或某次讲解被验证效果好（用户答对迁移题）。
2. **动作**：新增/修订原子、追加误区条目、调整练习难度，以 git 提交落地，提交信息注明共性证据。
3. **边界**：curriculum 层（atoms、misconceptions、learning-paths）可直接改 + commit 留痕；AGENTS.md、Skills、Schema 等规则层的修改仍需用户显式确认。
