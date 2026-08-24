---
name: new-topic-research
description: Use when a learner requests a library, framework, API, project, interview domain, or other topic whose reliable teaching assets are missing or may be version-sensitive.
---

# 新主题研究

当知识库没有可靠内容，或库、框架、API 会随版本变化时，先建立可信事实，再规划课程。研究不是给学习者堆链接，而是为教学决策提供最小、可追溯的依据。

## 判断

- 目标型短课且知识库已有同版本资产：可以直接复用，不重复搜索。
- 选择“完整掌握”或高级工程师路线时，即使知识库已有基础内容，也要核对知识覆盖、当前版本、工程实践与毕业项目需要的官方资料。
- 当日已完成且通过深度字段校验的 `sources.json` 可直接复用；重试 Plan 时不重复搜索。复用前必须确认顶层 `topic` 与本轮用户主题一致；不得因目录名相似而复用另一主题。文件缺失、过期、版本不清或覆盖不足才重新上网。
- 新库、新框架、新 API、陌生项目或版本敏感内容：必须研究。
- 用户提供的帖子、截图和面试题只能作为线索，不能替代官方文档。

## 研究动作

1. 先用 `python tools/web_search.py "<主题> official documentation getting started"` 搜索。
2. 优先官方文档、官方仓库、标准或原始论文；必要时用 `curl` 读取具体页面。
3. 只收集影响学习路线的事实：当前版本、先修、最小安装、核心心智模型、运行机制、测试调试、工程边界、性能安全、最小运行例和常见破坏性差异。
   面试路线必须使用“完整目标岗位 + 已确认技术栈”限定范围：优先官方技术文档、公开岗位能力要求和权威工程资料；公开面经只用来发现题型与表达场景，不把无来源答案当作事实。研究结果同时列出岗位能力域、技术栈核心主题、常见追问链和初学者先修缺口。
4. 输出结构化 `sources.json`，必须写入调用任务给出的**完整精确路径**；不要自己翻译主题、推测 slug 或另建相似目录。字段必须严格使用：
   - 顶层：`topic`, `researched_at`, `version`, `sources`, `teaching_facts`, `coverage_areas`, `prerequisites`, `graduation_project`；
   - 每个 source：`id`, `title`, `url`, `kind`；
   - 每个 teaching fact：`statement`, `source_ids`；
   每个事实必须引用一个已存在的 source id，不要改成 `fact` / `source` 等近义字段。
   顶层 `topic` 必须与用户的原始学习主题一致；路线、起点、学习范围只是元数据，不得追加到 `topic` 或放进括号。
5. 完整掌握路线的 `coverage_areas` 至少覆盖五个真正不同的能力域。`graduation_project` 可以是详细字符串，也可以是含 `name`、`goal`、`evidence` 的对象；必须是可验收的大型综合产出。
6. 把研究结果交给 `learning-plan`；每章生成时只注入与本章相关的来源事实，不要在研究阶段直接生成整章课件。

## 边界

- 搜索失败时停止生成正式 Plan，保留用户输入并允许重试。
- 不复制大段文档；用自己的话提炼并保留短引用来源。
- 未验证的信息标为不确定，不能写入共享知识库。
