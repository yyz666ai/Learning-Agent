# Product Design QA — Learning Agent 学习工作台

## Comparison target

- Source visual truth and implementation screenshots were reviewed locally. Generated QA screenshots and comparison artifacts are intentionally excluded from the public repository; reproducible checks remain in `tests/` and `evals/` source files.
- URL: `http://127.0.0.1:8791/`
- Viewport: 1440 × 1024 CSS px, device density 1. Mobile check: 390 × 844 CSS px.
- Source pixels: 1487 × 1058. Source normalized to 1440 × 1024 for comparison. Implementation pixels: 1440 × 1024.
- State: source shows the selected Go beginner example; implementation intentionally shows the real active learner state from `learning-plan.md` (Python + LangChain, stage 0). Layout and interaction state are equivalent even though dynamic subject copy differs.

## Findings

No actionable P0, P1, or P2 differences remain.

- Fonts and typography: the final pass uses the target's restrained sans-serif hierarchy, comparable headline scale, compact UI labels, and readable body leading. Dynamic Python copy wraps to two lines without clipping.
- Spacing and layout rhythm: the 300 px roadmap, fluid lesson workspace, and 360 px coach panel preserve the selected three-column composition. Dividers, square cards, restrained borders, and minimal elevation match the visual direction.
- Colors and tokens: warm ivory, charcoal, muted terracotta, sage, and dusty blue map directly to CSS tokens. No gradients or ornamental shadows were introduced.
- Image quality: the lesson illustration is a real generated raster asset with a solid matching ivory background, correct 5:3 crop, and no checkerboard/transparency halo. No emoji, custom SVG, CSS illustration, or placeholder art is used.
- Copy and content: learner-facing copy explains why to study, what to do, how to submit evidence, and how evaluation works. Real plan and current-task content replace mock text.
- States and interactions: plan dialog, lesson/practice/notes tabs, generated-module-exercise entry, persistent review handout, HTML deck dialog, mobile roadmap, and mobile coach drawer were exercised successfully. Browser console error check returned zero errors.
- Onboarding and diagnosis: the selected one-screen direction is implemented with real choice buttons. Zero beginners enter the first lesson in one step; experienced learners complete three stable click-only answers before the lesson appears. No chat typing is used for diagnosis.
- Accessibility and responsiveness: semantic regions, labels, alt text, visible focus treatment, reduced-motion support, and a skip link are present. At 390 × 844, the central lesson remains readable and both side panels open as independent drawers without overlap.

## Focused comparison evidence

The central hero, lesson objective, current task, and illustration were cropped from both artifacts and compared together. The final implementation retains the target's headline/asset balance, horizontal section divider, compact task callout, and warm editorial density. A separate focused icon pass was unnecessary because the implementation intentionally uses text controls and the only visible brand mark is typographic; there is no substituted icon artwork to inspect.

## Comparison history

### Iteration 1 — blocked

- Earlier P2: the dynamic lesson title wrapped to three lines and pushed the current task below the first viewport.
- Fix: shortened adaptive lesson titles and moved the current task ahead of the concept cards; reduced task-callout padding.
- Post-fix evidence: `.design-qa-implementation-02.png` and `.design-qa-comparison-02.png` show the task restored to the first-screen learning sequence.

### Iteration 2 — blocked

- Earlier P2: the serif display typography was a visible mismatch from the selected target's sans-serif UI and changed the product character.
- Fix: aligned display headings to the same Chinese system sans-serif stack and reduced the hero maximum size to 50 px.
- Post-fix evidence: `.design-qa-implementation-03.png`, `.design-qa-comparison-03.png`, and `.design-qa-focus-comparison-03.png` show the corrected hierarchy and wrapping.

### Iteration 3 — passed

- Earlier P2 discovered during final mobile flow testing: after the third diagnostic answer, the preserved page scroll position placed the lesson title underneath the sticky navigation.
- Fix: focus the lesson workspace without scrolling, then explicitly reset the document to the top when onboarding confirmation completes.
- Post-fix evidence: `evals/implementation-learning-mobile-scroll-fixed.png` shows the complete lesson title below the sticky header at 390 × 844, with `scrollY = 0` and no horizontal overflow.

### Iteration 4 — passed

- No actionable P0, P1, or P2 findings remain across the required fidelity surfaces.
- P3 follow-up: a later iteration could add a compact desktop phase-collapse control if long community curricula routinely exceed ten stages; the current seven-stage real plan remains fully usable.

### Iteration 5 — passed

- Earlier P1: the final PPT page ended with an inactive next-page state and only a prose hint in the coach, so the learner could not tell whether to answer, run code, or continue.
- Fix: the final page now owns a visible evidence field plus `提交并评价 / 换一种讲法 / 我卡住了`; it hides the dead-end next button, focuses the evidence field, and mirrors the model-returned named CTA above the chat composer.
- Earlier P1: starting a new project removed the learning workspace without an obvious cancel path.
- Fix: the chat-first new-project state includes a persistent `← 返回当前课程` and restores the exact prior PPT page, chat context, evidence, feedback and CTA.
- Visual comparison: the combined before/after image shows the same warm editorial three-column language, while replacing ambiguous whitespace and prose-only guidance with a compact action card in the lesson column. No new P0/P1/P2 fidelity issue was introduced.

## Implementation checklist

- [x] Match selected three-column proportions and editorial palette.
- [x] Use the learner's persistent plan and current task.
- [x] Provide streamed coaching, exercise submission, and feedback states.
- [x] Provide plan, practice, notes, deck, and responsive drawer interactions.
- [x] Verify desktop and mobile rendering, primary interactions, and console errors.

## 2026-08-22 Natural Organic onboarding pass

- Source visual truth: user-provided before-state screenshots plus the Natural Organic token specification from the design request.
- Implementation evidence: desktop 1280 × 720 and mobile 390 × 844 states were reviewed locally; generated screenshots are not published.
- Full-view comparison evidence: both the 3024 × 1740 before-state and the 1280 × 720 implementation were opened together for visual review. They intentionally differ in composition according to the approved redesign: duplicate branding and the bottom project popover were removed; the project list became a persistent rail; the composer grew wider; user copy became a compact content-width chip.
- Focused region evidence: the implementation screenshot keeps the composer, three-option tray, compact right-aligned user message, direct sidebar project region, and single brand mark readable in one viewport. A second focused crop was unnecessary because all changed controls are legible at the desktop capture size.
- Fonts and typography: the overused Inter stack was removed. The result uses a Chinese-friendly Avenir/PingFang sans stack for body copy and Songti serif for editorial labels and headings. Input text is 16px, agent body is 15px, and mobile copy wraps without clipping.
- Spacing and layout rhythm: the composer is capped at 900px instead of 720px; options sit directly above it; the user bubble shrinks to content width; the onboarding project rail uses the remaining vertical space while the learning state caps that region at 168px so the outline remains primary.
- Colors and tokens: warm cream `#faf6f1`, earth brown `#5c4033`, sage `#8b9d77`, warm tan and stone borders replace the flatter gray/terracotta-only treatment. No prohibited blue/purple/cyan classes, pure black, gradient classes, Inter, or heavy shadow tokens were found.
- Interaction states: add-project, settings, voice, send, project drawer, choice hover/focus, and responsive drawer have visible affordances. The existing reduced-motion rule covers the new transitions.
- Responsive behavior: the first mobile pass found that a general 48vh lesson rule overrode the onboarding shell and left the composer halfway up the page. The selector now excludes onboarding; the second 390 × 844 capture shows the composer pinned near the bottom. The mobile project button opens the real shared project rail.
- Runtime behavior: “我想学 Go” produced three model-generated choices above the composer, the user message rendered without a “你” label, and browser console warning/error inspection returned an empty list.

### Comparison history for this pass

- Iteration 1 — blocked (P1): project history was hidden in a footer popover, two Agent identities competed in the top-left area, the three-dot control had no useful action, and the user bubble had a redundant label.
- Fix: moved projects into a first-class sidebar region; removed the repeated coach brand and dead menu; made user messages content-width and label-free; widened and restyled the composer and dynamic choices.
- Iteration 2 — blocked (P2): at 390 × 844 the onboarding conversation inherited the learning split-view height, placing the composer in the middle of the viewport.
- Fix: scoped the 48vh split-view rule away from `.is-onboarding` and re-captured the mobile state.
- Iteration 3 — passed: no actionable P0/P1/P2 issue remains in the requested initial page, dynamic choice, user-message, sidebar-project, desktop, or mobile states.

final result: passed

## 2026-08-23 零基础 HTML PPT 环境准备

- 触发范围：仅零基础且需要实际运行代码的第一章；纯概念 `meaning_only` 不触发，环境验证完成后的后续章节不重复整套安装。
- PPT 位置：第一次运行代码前插入「环境准备」页，而不是只在聊天框提示。页面必须说明需要下载的软件及用途、官方入口、版本验证命令、课程项目目录、编辑器打开方式和首次运行命令。
- 平台策略：画像有操作系统时只展示对应平台；未知时提供 macOS / Windows / Linux 三个紧凑分支，不猜测平台、不编造版本和下载地址。
- Plan：零基础代码路线的第一章包含可验收的环境准备阶段；验证后写入 `environment_ready`，该证据不等于概念掌握。
- Skill：同步更新 `adaptive-lesson-flow`、`environment-setup`、`learning-plan`，并补充环境准备官方入口参考和两类行为用例。
- Generator：首章零基础课件提示新增强制环境页契约，确保环境说明进入 HTML PPT。

## 2026-08-23 学习聚焦、Markdown 与统一题库

- Onboarding slot filling：`plan.md` 不等所有 slot 填满才生成。只有主题 `topic` 和最终成果 `desired_outcome` 是决定路线的必需信息；其他 slot 只在会改变课程时追问。
- Markdown：支持 H1–H6，修复 `####` 原样露出；普通 fenced code 进入带语言标签的深色代码框，并有“✓ 已复制”反馈；支持 `==高亮==`。
- 生成等待：显示已完成百分比、剩余百分比、已等待时间、估算 ETA 和当前步骤。这是根据历史同类请求的估算，未完成前上限仍为 92%，不伪装服务端真实阶段精度。
- 左栏：学习态隐藏“学习项目”和 Plan dock，项目切换与完整 Plan 保留在设置中；Onboarding 首页仍显示历史项目。品牌栏压到 48px，导航和翻页控件缩小，大纲文字放大。
- 统一练习题库：课堂选择题和课后作业在课程加载时自动入库，与面试题合并显示。答错标记“错题 · 再做一遍”，答对标记“已掌握”，同时保留答错次数与尝试历史。
- 教学 Skill：`adaptive-lesson-flow` 约束每页最多 2 处加粗和 1 处高亮；课程生成 prompt 同步此规则。
- Go 知识库：新增指针基础、指针参数/接收者、函数值/闭包/回调三个知识原子；当前 `yang` 课程新增第 5 章且保留 `int-string-bool` 为当前知识点。
- Automated evidence：完整回归 296 passed，workspace validator 0 errors，仅 1 条上游 Starlette 弃用警告。
- Live evidence：服务重启后 `/api/health` 返回 200；`yang` 当前 10 页讲义加载成功，自动收录 3 道课堂选择题 + 1 道课后作业。浏览器实测学习态左栏只显示大纲/练习题库，12 章大纲可独立翻页，Plan 中原样 `####` 数量为 0、正常 H4 为 39，浏览器控制台无 warning/error。

## 2026-08-23 课程生成可见性与左栏空间修复

- Source visual truth: 用户截图显示学习项目区在学习态占据左栏顶部、课程长时间停在“课程准备中”，以及麦克风/发送按钮过大。
- P1 root cause: `/api/lesson/generate` 已返回 502，具体是模型课件中一段代码缺少中文注释，被质量校验拒绝；前端未渲染持久失败态，造成“仍在生成”的错觉。
- Fix: 保留中文注释质量门槛，对“仅缺少注释”这一可确定修复情况自动补全后重新校验；其他错误记录阶段/类型，并在讲义区显示持久的失败说明与“重新生成课程”按钮。
- Waiting feedback: 大纲和章节生成现在显示动态进度条、已等待时间和预估剩余时间；估时根据本机最近 5 次同类任务的中位耗时逐步校正，未完成前上限停在 92%，不伪装成完。
- Sidebar: 学习态中项目列表移至 Plan 之后、设置之前，默认折叠为 46px 的单行入口；大纲/题库仍占据主要滚动空间。Onboarding 首页仍展开历史项目，方便直接继续。
- Composer: 桌面端麦克风和发送按钮缩至 36px，标准 Bootstrap Icons 加粗；移动端保留 44px 触摸目标。
- Live evidence: `yang` 的 Go 第一章在修复后 127.1 秒内完成，生成 6 页讲义、3 个代码页和 2 道选择题；所有代码页通过中文注释检查。浏览器实测中等待卡显示“已等待 2 秒 · 预计还需 3 分钟”，完成后自动进入第 1/6 页，无控制台错误。
- Layout evidence at 1440×900: 大纲独立区高 588px；学习项目折叠区高 45px 且位于左栏底部；麦克风和发送按钮均为 36×36px。
- Automated evidence: full suite 287 passed; one upstream Starlette deprecation warning, no product failure.

## 2026-08-22 Mermaid、等待反馈与左栏 Plan 增量

- Source visual truth: 用户截图显示 `flowchart TD` 被作为普通代码显示，以及“课程准备中”缺少动态等待反馈。
- P1 root cause: Markdown renderer 对所有 fenced block 使用同一 `<pre><code>` 分支，没有 Mermaid hydration。Fix: `mermaid` fence 输出 diagram container，动态对话、Plan、讲义、作业与题库更新后统一调用 hydration。
- P2: 左栏顶部的项目标题与进度卡挤压大纲。Fix: 摘要迁移到大纲/题库之后的默认折叠 dock，只保留标题和进度，完整 Plan 由内部按钮打开。
- P2: loading page 使用静态标题。Fix: 三点依次变化的动态省略号，reduced-motion 下自动降级。
- Automated evidence: 281 tests passed；workspace publish validation returned 0 errors.

## 2026-08-22 Corporate Clean alignment pass

- Source visual truth: user-provided current-state screenshots together with the complete Corporate Clean token specification from the design request.
- Implementation evidence: desktop 1280 × 720 and mobile 390 × 844 states were reviewed locally; generated screenshots are not published.
- P1 found in source state: the agent copy, choice tray, and composer used unrelated width caps, producing visibly different left edges. Fix: all onboarding content now shares one centered `1040px` grid. Runtime measurement returned identical composer and agent bounds (`272–1248px`, width `976px`) with zero horizontal overflow.
- P1 found in source state: text glyphs and hand-built shapes were used as icons. Fix: Bootstrap Icons now supplies the brand, add, menu, info, microphone, send, close, settings, folder, and navigation icons.
- P2 found in source state: irregular organic radii, serif labels, cream/brown tokens, and slow transitions conflicted with the selected enterprise direction. Fix: blue/white/slate palette, system sans typography, 8–12px radii, subtle borders/shadows, and 150–200ms interaction feedback.
- Choice-state review: the outer blob card was removed. Three compact bordered rows now sit directly above the composer, share its full width, keep detail text behind accessible info controls, and leave the composer available for typed corrections.
- Responsive review: at 390 × 844, `body.scrollWidth`, `window.innerWidth`, and the document viewport all measured `390px`; no horizontal overflow or clipped primary control was found.
- Runtime review: the dynamic onboarding request returned three relevant Go learning goals; all standard icons rendered; browser console warning/error inspection returned an empty list.

### Comparison history for this pass

- Iteration 1 — blocked (P1): organic styling, simulated icons, and mismatched content widths remained visible.
- Fix: replaced the visual tokens and icon source, then consolidated the chat content into one grid.
- Iteration 2 — passed: desktop dynamic-choice and mobile initial states show aligned content, restrained Corporate Clean styling, working focus/hover affordances, and no P0/P1/P2 issue.

final result: passed
