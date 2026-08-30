# 教学闭环修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement the bounded tasks below; preserve the existing main worktree and unrelated changes.

**Goal:** 修复实测发现的课件生成误判与课堂恢复缺口，实现引用课件提问，并使追加练习和模拟面试遵循用户的真实目标。

**Architecture:** Python 校验、保存版本及学习事实；前端只展示可恢复的事实和引用草稿；Skills 规定教学行为。生成、恢复、引用、练习各自有回归测试，不以隐藏错误或移除质量门禁代替修复。

**Tech Stack:** FastAPI / Pydantic / Python pytest；原生 JavaScript / Node test；Codex runtime + DeepSeek；隔离评测目录。

基线和已批准设计见 `LESSON_EVALUATION.md`、`LESSON_USE_CASES.md`。所有真实模型复测记录在忽略上传的 evals/runs 下；不读取或改写真实用户学习数据。

## 1. 生成与研究可靠性

- [x] 在 lesson_generator 与对应测试复现改写标题被误判、伪造覆盖证据及长代码缺少铺垫。
- [x] 修正覆盖判定，保留每知识点证据和结构门禁；限制修复次数。
- [x] 检查研究工具的实际响应、超时及来源校验，禁止把“即将搜索”的文字当研究成果。
- [x] 运行生成回归，记录尚需真实模型验证的边界。

## 2. 引用提问与恢复

- [x] 在 backend/lesson_context.py 独立实现课件内容版本、引用验证和已回答题目恢复，新增行为测试。
- [x] 在 main.py 接入引用请求及课件响应；用户目录的对话事件是恢复源。
- [x] 在 frontend/js/lesson-selection.js 接入文字/代码选中、提问按钮、可移除引用草稿；app.js 发送上下文。
- [x] artifact.js 恢复相同题目版本的通过记录；防止旧版本解锁新题。
- [x] Node 状态/模拟 DOM 测试取消、输入保留、失败时引用不丢、切换项目、失效引用；真实拖选端到端仍未验收。

## 3. 教学行为与追加练习

- [x] SupplementalPracticeRequest 保存完整 instruction；练习类型不强制为选择题，数量遵循用户请求。
- [x] 编程练习包含目标、渐进提示、验收标准和安全练习路径；加入课件及题库。
- [x] 模拟面试一次一问，回答后点评和追问；显式索要答案可以给参考答案，但不算独立掌握。
- [x] 修订对应 Skills 与 Python prompt，移除已发现的旧版 deck/终端门禁及固定题量冲突；不宣称穷尽所有规则冲突。

## 4. 验收

- [x] 运行全量 pytest 和 Node 行为测试。
- [x] 隔离运行初学、进阶、面试三类真实模型链路，记录耗时、产物和内容评价（测试执行完成不代表全部内容通过）。
- [ ] 浏览器验证课件、引用提问、刷新恢复、练习追加。
- [x] 独立规格审查和代码审查，更新评测文档，清楚区分通过与未通过；未完成的项目不打勾。

## 验收状态

代码层与隔离服务完成自动化/真实接口验证；浏览器答题刷新恢复通过。原浏览器输入已保留；另开测试页的实际拖选仍未成功验收，因此不能勾选完整浏览器验收项。具体内容缺陷、修订结果、原始失败和真实耗时见 `LESSON_EVALUATION.md` 的实施后复测章节。未修改线上真实用户状态，未把这些局部测试说成全部课程无缺陷。
