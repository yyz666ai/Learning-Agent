# Codex 定时任务提示词

在用户确认运行频率后，把下面整段作为 Codex 定时任务的提示词；工作目录应设置为 Learning Agent 项目根目录。

```text
在 Learning Agent 项目中使用 $spaced-review。读取 user-data/reviews/review-schedule.json，选择最多五个到期知识点并准备今天的复习。不得修改目标代码，不得把未作答内容标记为完成，并且只能写入 user-data/。如果没有到期内容，简短报告即可，不得修改掌握状态。
```

## 定时任务边界

- 创建定时任务前必须由用户确认频率、时间和时区。
- 定时运行只准备复习，不假装用户已经作答。
- 任务产生的提醒应回到同一 Learning Agent 工作区继续完成。
