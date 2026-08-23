# 掌握度策略契约

## 状态

`unseen → introduced → practicing → provisional → mastered` 是正常进展。出现遗忘、重复误区或迁移失败时进入 `needs_review`；复习后可以回到 `practicing` 或 `provisional`。

## 证据要求

- `introduced`：完成教学并通过一次理解检查。
- `practicing`：已经产生自己的练习尝试。
- `provisional`：至少有一次 `independent` 独立完成证据。
- `mastered`：同时具有 `independent` 和 `delayed_review` 证据，并且没有未解决的同类误区。
- `needs_review`：延迟复测失败、同类错误复发或高度依赖提示。

测试通过不等于掌握。复制答案、L4 参考实现、Agent 代写和仅凭口头自信都不能提升到 `provisional` 或 `mastered`。

## 必需写入

每次状态变化记录证据类型、结果、最高提示等级、发生时间和产物路径。证据不足时保持原状态并说明缺口。

## 失败行为

证据文件不存在、时间无效或辅助程度不明时，不提升状态。
