"use strict";
(function (root) {
  // Explicit, reviewed UI copy only. Course bodies, chat and code are never scanned.
  const dictionary = {
  "结课说明": "Completion instructions",
  "参考答案": "Reference answer",
  "回答结构": "Answer structure",
  "常见遗漏": "Common omissions",
  "常见追问": "Follow-up questions",
  "回答要点": "Answer points",
  "课堂选择题已经完成。课后练习已留在项目目录，你可以自己练；完成后的代码、运行结果或问题直接发到右侧输入栏即可。": "Classroom questions are complete. Homework is in your project folder for independent practice. Share your code, results or questions in the chat on the right.",
  "必答选择题都已通过，你已经抓住了这个概念的核心。": "All required questions are passed. You have understood the core of this concept.",
  "这些选择题还需要先答对：{0}。回到对应页面直接点击选项，不需要写文字回答。": "First answer these questions correctly: {0}. Return to their pages and click an option; no written answer is needed.",
  "回到选择题再试": "Return to the questions and retry",
  "开始下一章": "Start next chapter",
  "开始下一章：{0}": "Start next chapter: {0}",
  "做一道针对性练习": "Try a focused exercise",
  "换一种讲法": "Try another explanation",
  "查看课程总结": "View course summary",
  "刚完成的{0}使用{1}生成。原结果已保留；切换界面不会自动翻译，可按需查看翻译副本。": "The completed {0} was generated in {1}. The original result is preserved. Changing the interface does not translate it automatically; you can request a translated copy when needed.",
  "诊断": "assessment",
  "计划": "plan",
  "课件": "lesson",
  "中文": "Chinese",
  "系统通知需要保持本机服务运行，并在系统设置中允许通知。": "System notifications require the local service to stay running and notification permission in system settings.",
  "当前平台尚不支持系统通知；提醒偏好仍可保存，但不会发送通知。": "System notifications are not supported on this platform. Reminder preferences can be saved, but notifications will not be sent.",
  "当前环境不能打开文件夹，请手动打开此路径。": "This environment cannot open folders. Please open this path manually.",
  "当前环境没有可用桌面，请手动打开此路径。": "No desktop is available in this environment. Please open this path manually.",
  "请手动打开此路径。": "Please open this path manually.",
  "系统未能打开文件夹，请手动打开此路径。": "The system could not open the folder. Please open this path manually.",
  "翻译副本": "Translated copy",
  "查看原文": "View original",
  "这是只读翻译副本；原文、代码、笔记和作答记录保持不变。关闭即可返回原文。": "This is a read-only translated copy. The original, code, notes and answer records are unchanged. Close it to return to the original.",
  "翻译当前 Plan": "Translate this plan",
  "翻译当前章课件": "Translate this chapter",
  "正在准备翻译副本，原文不会被修改。": "Preparing a translated copy. The original will not be changed.",
  "仅将{0}翻译为{1}并保存副本，可能需要模型调用。不会翻译历史聊天或其他章节。继续吗？": "Translate only {0} into {1} and save a copy? This may use a model call. Past conversations and other chapters will not be translated.",
  "当前 Plan": "the current plan",
  "当前章课件": "the current chapter",
  "翻译副本已就绪；原文保持不变。": "Translated copy ready. The original is unchanged.",
  "原文已经变化，这份译本未显示。请重新翻译当前版本。": "The original has changed, so this translation was not displayed. Translate the current version again.",
  "翻译未完成，原文保持不变。可以重试；详细原因见诊断报告。": "Translation did not complete. The original is unchanged. Retry, or export a diagnostic report for details.",
  "{0} 秒": "{0} sec",
  "{0} 分钟": "{0} min",
  "超出常见时间，仍在生成": "Taking longer than usual; still generating",
  "已完成 92% · 剩余 8% · 已等待 {0} · 超出常见时间，仍在生成": "92% complete · 8% remaining · Elapsed {0} · Taking longer than usual; still generating",
  "已完成 {0}% · 剩余 {1}% · 已等待 {2} · 预计还需 {3}": "{0}% complete · {1}% remaining · Elapsed {2} · About {3} left",
  "这一步完成后会告诉你接下来做什么。": "When this step finishes, we will show you what to do next.",
  "当前：{0}": "Current: {0}",
  "下一步已经为你准备好了。": "Your next step is ready.",
  "本次等待已结束": "This wait has ended",
  "当前：已完成": "Current: complete",
  "正在生成你的学习大纲": "Creating your learning outline",
  "正在判断你真正要达到的结果…": "Understanding the outcome you want…",
  "正在核对可靠资料和必要知识点…": "Checking reliable sources and essential knowledge…",
  "正在根据你的目标排列学习顺序…": "Ordering the lessons around your goal…",
  "正在检查大纲是否有跳步或遗漏…": "Checking the outline for gaps or skipped steps…",
  "正在把结果整理成可确认的 Plan…": "Preparing a plan for your confirmation…",
  "正在生成完整章节": "Generating the complete chapter",
  "正在按大纲生成讲解、中文注释代码和选择题…": "Creating explanations, commented code and questions from the outline…",
  "正在拆分本章知识点和顺序…": "Organizing this chapter's concepts and sequence…",
  "正在生成逐页讲解与代码演示…": "Creating page-by-page explanations and code examples…",
  "正在检查选择题答案和中文注释…": "Checking answers and code comments…",
  "正在整理课后练习和项目目录…": "Preparing homework and project folders…",
  "诊断已停止": "Assessment stopped",
  "正在重新连接": "Reconnecting",
  "正在校准起点": "Finding your starting point",
  "只用几道小题找到合适的第一课；用时取决于模型与网络。": "A few short questions help us choose your first lesson; timing depends on the model and network.",
  "显示服务器最近一次状态；不估算完成百分比。": "Showing the latest server status; no estimated completion percentage.",
  "大纲 {0} / {1}": "Outline {0} / {1}",
  "我先列出修改范围。请确认生成修改稿；你检查并点击「应用修改」后，才会替换当前课件。之后仍可撤销。": "I will outline the changes first. Confirm to generate a draft, then review it and click “Apply changes” to replace the lesson. You can still undo it later.",
  "修改请求尚未建立，原课件没有变化。请查看课件上方提示后重试。": "The change request was not created. Your original lesson is unchanged. Check the notice above the lesson and retry.",
  "正在回应": "Responding",
  "正在组织讲解": "Preparing an explanation",
  "教练正在结合你的当前进度生成回复。": "Your coach is composing a response based on your current progress.",
  "连接暂时中断，请稍后再试。": "Connection interrupted. Please try again shortly.",
  "学习引擎暂时不可用。": "The learning engine is temporarily unavailable.",
  "没有收到完整回答，请重试。": "No complete reply was received. Please retry.",
  "讲解已送达": "Explanation delivered",
  "可以继续提问，或按讲义里的下一步操作。 ": "Ask another question or follow the next step in the lesson. ",
  "连接没有成功：{0}\n\n你刚才的内容还在，可以直接重试。": "Connection failed: {0}\n\nYour input is preserved. You can retry directly.",
  "这次没有完成": "Not completed this time",
  "你的输入已保留，点击发送即可重试。": "Your input is preserved. Click Send to retry.",
  "已连接": "Connected",
  "阶段 1：建立直觉": "Stage 1: Build intuition",
  "我的": "My",
  "{0}学习计划": "{0} learning plan",
  "计划会根据练习证据持续调整": "The plan adapts to evidence from your practice",
  "{0} / {1} 知识点": "{0} / {1} concepts",
  "{0} / {1} 阶段": "{0} / {1} stages",
  "课堂进度 {0}%": "Class progress {0}%",
  "预计还需 {0} 分钟": "About {0} minutes left",
  "{0} 个知识点": "{0} concepts",
  "正在学习：{0}": "Learning: {0}",
  "已完成": "Completed",
  "正在学习": "In progress",
  "待解锁": "Locked",
  "计划正在生成。": "Your plan is being generated.",
  "我把这个概念的学习顺序整理好了：": "Here is the learning sequence for this concept:",
  "我把建议的学习路线整理好了：": "Here is the suggested learning path:",
  "{0}\n\n{1}\n\n---\n\n需要调整时，直接在下面告诉我要增加、删除或改变什么。": "{0}\n\n{1}\n\n---\n\nTo adjust it, tell me below what you would like to add, remove or change.",
  "正在确认学习计划": "Confirming the learning plan",
  "随时可以继续": "Ready whenever you are",
  "上次 {0}": "Last used {0}",
  "切换学习项目失败，请重试。": "Could not switch projects. Please retry.",
  "正在打开当前学习": "Opening your current project",
  "正在切换学习项目": "Switching learning projects",
  "大纲、讲义和进度会一起恢复。": "The outline, lesson and progress will be restored together.",
  "项目没有打开": "Project did not open",
  "原项目仍然保留，可以稍后重试。": "Your original project is preserved. Please retry later.",
  "未命名项目": "Untitled project",
  "删除「{0}」？": "Delete “{0}”?",
  "项目暂时没有删除成功。": "The project could not be deleted.",
  "学习项目已删除，共享教案仍然保留": "Learning project deleted; shared teaching materials are preserved",
  "未命名学习项目": "Untitled learning project",
  "当前学习 · {0}": "Current project · {0}",
  "学习项目": "Learning projects",
  "管理{0}": "Manage {0}",
  "删除": "Delete",
  "正在准备讲义": "Preparing the lesson",
  "先读取你的大纲和进度，再生成当前这一小节。": "Reading your outline and progress before generating this section.",
  "第一课已经打开。先看讲义中的第一小步；遇到题目直接点击，答案会在题目下方立即出现。": "Your first lesson is open. Start with the first small step. Click a question's options to see feedback below it.",
  "讲义已准备好": "Lesson ready",
  "从第 1 页开始；最后一页会明确告诉你在哪里提交。 ": "Start on page 1; the final page explains where to submit. ",
  "讲义暂时未准备好": "Lesson not ready yet",
  "请稍后重试，当前学习状态不会丢失。 ": "Please retry shortly. Your learning progress is preserved. ",
  "当前课程暂时无法安全备份。": "Could not safely back up the current course.",
  "新课程已创建，但旧课程暂时没有归档成功。请稍后重试。 ": "The new course was created, but the previous course could not be archived. Please retry. ",
  "已回到原来的课程；你的新主题选择仍会保留在对话记录里。 ": "Returned to your original course. Your new topic remains in the conversation history. ",
  "新课程没有生成成功，原课程恢复也需要重试。 ": "The new course was not generated, and restoring the original also needs a retry. ",
  "原课程恢复失败，请重试。": "Could not restore the original course. Please retry.",
  "输入你现在想解决的事": "What would you like to work on?",
  "想继续以前的内容，直接点左边的学习项目。\n\n想学新东西，就在下面随便说——概念、项目、面试、API 或者一个具体问题都可以。": "To continue earlier work, select a learning project on the left.\n\nTo learn something new, tell me below—a concept, project, interview, API or specific question.",
  "例如：下周面试 Java 后端，或我想用 LangGraph 做客服 Agent…": "For example: a Java backend interview next week, or building a support agent with LangGraph…",
  "计划确认失败，请重试。 ": "Could not confirm the plan. Please retry. ",
  "计划已确认，但旧课程暂时没有归档成功。请重试。": "The plan was confirmed, but the previous course could not be archived. Please retry.",
  "学习服务未连接": "Learning service disconnected",
  "这份概念速学方案还在等你确认。确认后就会直接开始概念讲解。": "This quick concept plan is waiting for confirmation. Once confirmed, the explanation will begin.",
  "这份学习计划还在等你确认。你可以先阅读；确认后才会开始生成第一章。": "This learning plan is waiting for confirmation. Read it first; chapter generation starts only after you confirm.",
  "Plan 等待确认": "Plan awaiting confirmation",
  "开课前": "Before class",
  "确认并开始": "Confirm and start",
  "锁定范围，开始概念讲解": "Confirm the scope and start the concept explanation",
  "锁定当前大纲，开始生成第一章": "Confirm this outline and generate chapter 1",
  "连接失败": "Connection failed",
  "暂时没能连接学习服务：{0}。请确认后台服务正在运行。": "Could not connect to the learning service: {0}. Check that the backend is running.",
  "后台服务运行时，可在服务所在的 macOS 电脑接收系统通知；请允许系统通知权限。": "While the backend is running, the host Mac can receive system notifications. Allow notifications in system settings.",
  "当前系统暂不支持桌面提醒；学习和复习不受影响。": "Desktop reminders are not supported on this system; learning and review are unaffected.",
  "提醒没有保存成功": "Could not save the reminder",
  "当前系统暂不支持桌面提醒。": "Desktop reminders are not supported on this system.",
  "每日提醒已保存": "Daily reminder saved",
  "每日提醒已关闭": "Daily reminder disabled",
  "收起学习项目": "Collapse learning projects",
  "展开学习项目": "Expand learning projects",
  "本章 {0} / {1}": "Chapter {0} / {1}",
  "已经为你打开：**{0}**。从第 1 页开始，继续按讲义里的提示往下走。": "Opened: **{0}**. Start on page 1 and follow the lesson prompts.",
  "课件仍在后台生成，请稍后点击重试继续读取。": "The lesson is still generating in the background. Retry shortly to check the same task.",
  "第 {0} 页：{1}": "Page {0}: {1}",
  "正在检查这道题…马上告诉你哪里对、下一步怎么做。 ": "Checking your answer… Feedback and next steps will appear here. ",
  "正在检查这道题": "Checking this question",
  "答案会显示在题目下方；不需要再去别处提交。 ": "Feedback appears below the question; there is no need to submit elsewhere. ",
  "暂时无法批改，请再试一次。": "Could not check your answer. Please retry.",
  "答对了。": "Correct.",
  "{0} 下一步：900ms 后自动进入下一页。": "{0} Next: moving to the next page in 900 ms.",
  "答对了": "Correct",
  "这一页已通过，马上进入下一小步。 ": "This page is passed. Moving to the next small step. ",
  "还差一点。": "Not quite yet.",
  "{0} 下一步：再选一次；需要提示可以点右侧“给我提示”。": "{0} Next: choose again. For help, click “Give me a hint” on the right.",
  "还差一点": "Not quite yet",
  "答案提示已经显示在题目下方，可以马上再试。 ": "Feedback is below the question. You can try again now. ",
  "暂时无法检查：{0}。下一步：点击选项重试。": "Could not check: {0}. Next: click an option to retry.",
  "检查没有完成": "Check incomplete",
  "你的选择没有丢失，重新点击即可。 ": "Your choice is preserved. Click it again to retry. ",
  "直接点击一个选项。答对后会自动进入下一页；答错可以马上重选。": "Click an option. A correct answer advances automatically; otherwise you can choose again immediately.",
  "这是课后练习，不是课堂门禁。打开练习文件夹自己完成；代码、结果或问题直接发到右侧输入栏。": "This is homework, not a class gate. Open the practice folder and work independently. Send code, results or questions in the chat on the right.",
  "这个概念的必答题通过后，点击“完成这个概念”即可。": "After passing this concept's required questions, click “Complete this concept”.",
  "课堂到这里结束。课后自己练；愿意讨论时，把代码、运行结果或问题直接发到右侧输入栏。": "The class ends here. Practice independently, then share code, results or questions in the chat whenever you want to discuss them.",
  "先读这段代码，确认它做什么；理解后点击下一页继续。": "Read the code and identify what it does, then click Next page.",
  "读完这一页，抓住它解决的问题，再点击下一页。": "Read this page, identify the problem it solves, then click Next page.",
  "打开练习文件夹，自己完成这道课后练习。": "Open the practice folder and complete this exercise independently.",
  "#### 参考答案\n\n{0}\n\n**回答结构**\n\n{1}": "#### Reference answer\n\n{0}\n\n**Answer structure**\n\n{1}",
  "\n\n**常见遗漏**\n\n{0}": "\n\n**Common omissions**\n\n{0}",
  "\n\n**常见追问**\n\n{0}": "\n\n**Common follow-up questions**\n\n{0}",
  " · 重点": " · Key point",
  "笔记 {0}{1}": "Note {0}{1}",
  "我的问题：{0}": "My question: {0}",
  "教练总结：{0}": "Coach summary: {0}",
  "第 {0} 页 / 共 {1} 页": "Page {0} of {1}",
  "当前小步": "Current step",
  "这一页需要先答对，才能继续看后面的内容。直接点击一个选项即可。": "Answer this question correctly before continuing. Click an option to answer.",
  "必答选择题都答对就能完成；不需要写代码、粘贴终端输出或额外解释。": "Pass the required multiple-choice questions to finish. No code, terminal output or extra explanation is required.",
  "本章课堂已经讲完。课后练习留在真实项目里，你可以自己消化；完成后的代码、运行结果或问题直接发到右侧输入栏。系统不再检查打印输出。 ": "This chapter's class is complete. Homework remains in your real project for independent practice. Send code, results or questions in the chat. Printed output is not checked. ",
  "完成这个概念": "Complete this concept",
  "完成课堂，进入下一章": "Complete class and continue",
  "这道练习属于其他课程，请先在设置里切换到对应学习项目。": "This exercise belongs to another course. Switch to its learning project in Settings first.",
  "本章 1 / {0}": "Chapter 1 / {0}",
  "本章约 {0} 次 · 每次 {1} 分钟": "About {0} sessions · {1} minutes each",
  "建议每次 {0} 分钟 · 本章课次待估": "Suggested session: {0} minutes · Chapter count pending",
  "课程尚未就绪": "Course not ready",
  "准备没有完成": "Preparation incomplete",
  "课程生成失败": "Course generation failed",
  "这次课程没有生成完成。": "This course did not finish generating.",
  "{0}学习进度没有丢失，可以直接重试。": "{0} Your learning progress is preserved. You can retry directly.",
  "正在检查当前知识点，并生成这一节的讲解与练习。 ": "Checking the current concepts and creating explanations and exercises. ",
  "详细课程大纲没有生成成功。": "The detailed course outline was not generated successfully.",
  "项目已经切换": "Project switched",
  "迟到课件已丢弃，正在读取当前项目。 ": "Discarded a late lesson result; loading the current project. ",
  "项目已经切换，请确认当前学习计划后再生成讲义。": "Project switched. Confirm the current learning plan before generating the lesson.",
  "课程暂时没有准备好。": "The course is not ready yet.",
  "先阅读这一页；有题时直接点击答案。 ": "Read this page first; click an answer when a question appears. ",
  "讲义生成失败": "Lesson generation failed",
  "已在讲义区显示失败原因和重试按钮。": "The lesson area shows the error and a retry button.",
  "课堂已经完成": "Class complete",
  "再练一小步": "Practice one more step",
  "换个角度重新理解": "Revisit from another perspective",
  "正在确认概念检测": "Checking concept mastery",
  "正在保存课堂进度": "Saving class progress",
  "只确认课堂选择题；课后练习不会做输出检测。 ": "Only classroom questions are checked; homework output is not tested. ",
  "本章评价没有成功，请重试。": "Chapter evaluation failed. Please retry.",
  "课堂进度已保存": "Class progress saved",
  "还有课堂题未完成": "Required questions remain",
  "课后练习已留好。点击“{0}”继续。": "Homework is ready. Click “{0}” to continue.",
  "回到课堂选择题再试一次。 ": "Return to the classroom question and try again. ",
  "课堂进度没有保存": "Class progress was not saved",
  "选择题记录仍在，可以直接重试。 ": "Your answers are preserved. You can retry directly. ",
  "请用更循序渐进的方式重新讲解当前课件": "Explain the current lesson again in smaller, more gradual steps",
  "正在生成下一小节": "Generating the next section",
  "正在根据这次评价准备下一份讲义和练习。 ": "Preparing the next lesson and exercises based on this evaluation. ",
  "已安全丢弃旧课件，并读取当前课程。 ": "Safely discarded the old lesson and loaded the current course. ",
  "下一步课程没有生成成功，请重试。": "The next lesson could not be generated. Please retry.",
  "下一小节已准备好": "Next section ready",
  "从讲义第 1 页开始；每一步都会告诉你接下来做什么。 ": "Start on page 1. Each step will explain what to do next. ",
  "下一小节没有生成": "Next section was not generated",
  "当前讲义仍保留，点击按钮即可重试。 ": "Your current lesson is preserved. Click the button to retry. ",
  "文件夹暂时无法打开。": "Could not open the folder.",
  "已请求系统打开": "Asked the system to open it",
  "请手动打开": "Please open it manually",
  "当前环境不能打开文件夹。": "This environment cannot open folders.",
  "重试打开": "Retry opening",
  "打开练习文件夹": "Open practice folder",
  "<i class=\"bi bi-arrow-clockwise\" aria-hidden=\"true\"></i>正在重新生成…": "<i class=\"bi bi-arrow-clockwise\" aria-hidden=\"true\"></i>Regenerating…",
  "<i class=\"bi bi-arrow-clockwise\" aria-hidden=\"true\"></i>重新生成课程": "<i class=\"bi bi-arrow-clockwise\" aria-hidden=\"true\"></i>Regenerate course",
  "复制代码": "Copy code",
  "✓ 已复制": "✓ Copied",
  "复制失败": "Copy failed",
  "这轮诊断已不属于当前页面。": "This assessment no longer belongs to the current page.",
  "诊断状态暂时不可用，请重试。": "Assessment status is temporarily unavailable. Please retry.",
  "暂时无法读取状态，正在重连。尚不能确认后台是否完成。": "Cannot read status. Reconnecting; background completion is not yet confirmed.",
  "已排队，等待生成诊断题": "Queued; waiting to generate assessment questions",
  "正在生成与你的目标相关的诊断题": "Generating assessment questions related to your goal",
  "正在校验题目与选项": "Validating questions and options",
  "正在修正题目结构": "Repairing question structure",
  "诊断题已准备好": "Assessment questions ready",
  "这轮诊断已取消": "This assessment was cancelled",
  "诊断暂时未完成": "Assessment not completed",
  "服务重启，原任务已中断": "The service restarted; the original task was interrupted",
  " · 已等待 {0} 秒": " · Elapsed {0} sec",
  "正在读取诊断任务状态": "Reading assessment task status",
  "暂时无法确认诊断结果。你的请求标识已保留，点击重试将读取同一任务，不会重复生成。": "Cannot confirm the assessment result yet. Your request ID is preserved; Retry checks the same task without generating a duplicate.",
  "答案待生成": "Answer pending",
  "讲解草稿": "Explanation draft",
  "已有讲解": "Explanation ready",
  "尚未练习": "Not practiced",
  "没想起来": "Forgot",
  "有点困难": "Some difficulty",
  "顺利": "Smooth",
  "课堂选择题": "Classroom question",
  "课后作业": "Homework",
  "追加练习": "Additional practice",
  "面试题": "Interview question",
  "重要问题": "Important question",
  "错题 · 再做一遍": "Incorrect · Try again",
  "已掌握": "Mastered",
  "待完成": "Pending",
  "逐题从头讲": "Explain each from scratch",
  "每道题先建立直觉，再练面试表达": "Build intuition for each question, then practice interview delivery",
  "系统学习": "Systematic learning",
  "按知识依赖重排，补齐相关知识体系": "Order by prerequisites and fill related knowledge gaps",
  "先测后学": "Assess first, then learn",
  "先像真实面试一样回答，再针对薄弱处讲": "Answer like a real interview first, then focus on weak areas",
  "已掌握 {0} / 共 {1} 题": "Mastered {0} / {1} questions",
  "练习": "Practice",
  "已收录 {0} 道新题，想怎么掌握？": "Added {0} new questions. How would you like to learn them?",
  "选 1 项就开始": "Choose one to start",
  "学习方式暂时没有保存成功": "Could not save your learning method",
  "好，我们按「{0}」开始。我先带你完成第一道，后续相关知识会自动接入大纲。": "Let's start with “{0}”. I will guide you through the first question and connect related knowledge to the outline.",
  "面试题暂时没有收录成功": "Could not save the interview questions",
  "已整理 {0} 道题：新增 {1} 道，重复 {2} 道。原文也已经保留。": "Organized {0} questions: {1} new, {2} duplicates. The original text is preserved.",
  "复习题暂时没有加载成功": "Could not load review questions",
  "今日 {0} 题": "Today: {0} questions",
  "稍后重试": "Retry later",
  "本轮复习完成": "Review session complete",
  "薄弱点已经重新安排": "Weak areas have been rescheduled",
  "今天的复习完成了": "Today's review is complete",
  "做得好。做错或回忆困难的内容会更早再次出现，你可以继续在对话框要求 **再出几道题**。": "Well done. Incorrect or difficult material will appear again sooner. You can ask for **more questions** in the chat.",
  "本轮复习完成。困难内容已经重新安排，不会因为打开过卡片就算作掌握。": "Review complete. Difficult material has been rescheduled. Opening a card alone does not count as mastery.",
  "复习 {0} / {1}": "Review {0} / {1}",
  "练习题": "Practice question",
  "{0} · 先回忆，再看答案": "{0} · Recall first, then reveal",
  "今天暂时没有到期复习题": "No reviews are due today",
  "答案暂时没有加载成功": "Could not load the answer",
  "\n\n> 上次易错记录：选择了 {0}": "\n\n> Previous mistake: selected {0}",
  "### 参考答案\n\n**{0}**\n\n{1}{2}": "### Reference answer\n\n**{0}**\n\n{1}{2}",
  "稍微有点困难": "A little difficult",
  "复习记录没有保存成功": "Could not save the review record",
  "这道面试题现在掌握得怎么样？": "How well do you recall this interview question now?",
  "用于安排复习": "Used to schedule reviews",
  "红色 · 很快再出现": "Red · Review again soon",
  "黄色 · 缩短复习间隔": "Yellow · Shorter review interval",
  "绿色 · 延长复习间隔": "Green · Longer review interval",
  "掌握情况暂时没有保存成功": "Could not save your mastery rating",
  "已记录。复习时间会根据这次回忆难度自动安排。": "Recorded. Your next review is scheduled based on how difficult recall felt.",
  "讲解生成失败，请稍后重试": "Could not generate the explanation. Please retry later",
  "面试题 · 系统讲解": "Interview question · Full explanation",
  "从会看，到会答，再到能应对追问": "From understanding to answering and handling follow-ups",
  "练习题库": "Question bank",
  "课堂、课后和面试统一回顾": "Review classroom, homework and interview questions together",
  "选择左侧的一道题": "Select a question on the left",
  "题库还是空的": "The question bank is empty",
  "已经收录 **{0} 道练习**。做错的题会明确标记“再做一遍”；点一项就回到它所在的课程页。": "Saved **{0} exercises**. Incorrect answers are marked “Try again”. Select one to return to its lesson page.",
  "开始一节课后，课堂题和课后作业会自动收录在这里。": "Classroom questions and homework are saved here automatically after you start a lesson.",
  "标题": "Heading",
  "文字": "Text",
  "操作未完成，请保留草稿后重试。": "The operation did not complete. Keep your draft and retry.",
  "草稿暂存失败，请勿关闭页面。": "Could not save the draft locally. Do not close this page.",
  "编辑模式，点击切回只读": "Editing mode; click to return to read-only",
  "只读模式，点击编辑本页": "Read-only mode; click to edit this page",
  "还有未保存的课件修改。放弃这些修改并离开吗？": "There are unsaved lesson edits. Discard them and leave?",
  "已有选择题请在右侧说明修改要求，确认候选题与答案校验后再应用。": "To change an existing question, describe your request in the chat, then confirm the candidate question and validated answer before applying.",
  "已恢复本页未保存草稿。": "Restored this page's unsaved draft.",
  "编辑只影响本页；已有选择题保持只读，可在右侧申请追加新题。": "Edits affect only this page. Existing questions remain read-only; request additional questions in the chat.",
  "已保存新版本，可撤销。 ": "New version saved. You can undo it. ",
  "原始课件": "Original lesson",
  "生成课件": "Generated lesson",
  "手动编辑": "Manual edit",
  "教练修改": "Coach revision",
  "恢复版本": "Restored version",
  "课件版本": "Lesson version",
  "当前版本": "Current version",
  "恢复此版本": "Restore this version",
  "课件已恢复，学习记录仍保留。": "Lesson restored. Your learning records are preserved.",
  "仅生成修改稿，原课件保持不变。": "Generate a draft only; keep the original lesson unchanged.",
  "待确认修改范围": "Confirm the change scope",
  "正在生成候选稿，尚未替换原版": "Generating a candidate; the original is unchanged",
  "候选稿已就绪，请检查后应用": "Candidate ready; review before applying",
  "修改已应用，可从顶部撤销": "Changes applied; undo is available above",
  "已取消，原课件未修改": "Cancelled; the original lesson is unchanged",
  "生成未完成，原课件保持不变": "Generation incomplete; the original lesson is preserved",
  "确认生成修改稿": "Confirm draft generation",
  "应用修改": "Apply changes",
  "保留原版 · 取消": "Keep original · Cancel",
  "页面变更": "Page change",
  "原内容\n": "Original content\n",
  "新增页": "New page",
  "修改稿\n": "Draft changes\n",
  "已移除": "Removed",
  "返回编辑": "Back to editing",
  "预览": "Preview",
  "提问": "Ask",
  "引用选中内容并提问": "Quote the selection and ask a question",
  "课件引用": "Lesson reference",
  "<figure class=\"markdown-code-frame\"><figcaption><span>{0}</span><button type=\"button\" class=\"markdown-copy-code\" aria-label=\"复制这段代码\">复制代码</button></figcaption><pre><code class=\"language-{1}\">{2}</code></pre></figure>": "<figure class=\"markdown-code-frame\"><figcaption><span>{0}</span><button type=\"button\" class=\"markdown-copy-code\" aria-label=\"Copy this code\">Copy code</button></figcaption><pre><code class=\"language-{1}\">{2}</code></pre></figure>",
  "连接暂时中断，你刚才的内容已保留。": "Connection interrupted. Your input is preserved.",
  "课程生成状态暂时无法读取。": "Course generation status is temporarily unavailable.",
  "课程生成暂时中断，请直接重试。": "Course generation was interrupted. Please retry.",
  "详细课程研究与生成超过 11 分钟，请重试；你刚才的主题和目标都已保留。": "Course research and generation exceeded 11 minutes. Retry; your topic and goals are preserved.",
  "重新开始诊断": "Restart assessment",
  "重试": "Retry",
  "了解「{0}」": "Learn about “{0}”",
  "点一下就可以": "Just click an option",
  "直接补充你的需求…": "Add your requirements directly…",
  "补充你的实际需求，Enter 发送": "Add your actual requirements; Enter to send",
  "发送": "Send",
  "你现在想解决什么？直接输入就行。可以是一个概念、一个项目、一场面试，也可以是“我想用 LangGraph 做客服 Agent”这样的具体结果。": "What would you like to achieve? Type it directly—a concept, project, interview, or specific outcome such as “build a support agent with LangGraph”.",
  "例如：下周面试 Java 后端，或用 LangGraph 做客服 Agent…": "For example: a Java backend interview next week, or a support agent with LangGraph…",
  "已恢复 {0} 道已入库面试题，继续生成针对性计划。": "Restored {0} saved interview questions. Continuing with a targeted plan.",
  "已经收录 {0} 道真实面试题，请生成针对性计划": "{0} real interview questions are saved. Please create a targeted plan",
  "继续上次没有完成的建档：把你收集的面试题直接粘贴到输入框，我会先去重入库，再生成针对性 Plan。": "Continue the unfinished setup: paste your interview questions below. I will remove duplicates, save them, then create a targeted plan.",
  "直接粘贴面试题，支持编号列表或多行问题…": "Paste interview questions as a numbered list or multiple lines…",
  "继续上次没有完成的建档：{0}": "Continue the unfinished setup: {0}",
  "选一个最接近的；也可以直接输入修改或补充": "Choose the closest option, or type a change or addition",
  "已恢复上次进度": "Previous progress restored",
  "也可以直接输入你真正想要的结果…": "You can also type the outcome you really want…",
  "直接粘贴资料；暂时没有就输入“没有”…": "Paste your material, or type “none” if you have none…",
  "直接输入你的想法…": "Type your thoughts directly…",
  "暂时无法检查已有学习项目。": "Could not check existing learning projects.",
  "正在理解你的需求": "Understanding your needs",
  "正在结合你刚才的话和前面对话判断下一步。": "Using your latest message and earlier conversation to choose the next step.",
  "正在区分是答疑、面试、项目还是系统学习…": "Checking whether you need an answer, interview prep, a project or systematic learning…",
  "正在检查你已经说过哪些信息，避免重复追问…": "Checking information you already provided to avoid repeated questions…",
  "选一个最接近的；也可以直接打字修改或补充": "Choose the closest option, or type changes and additions",
  "正在理解需求": "Understanding your request",
  "不想选也没关系，直接输入你真正想要的结果…": "No need to choose; you can type the outcome you want…",
  "还差一个关键决定": "One key decision remains",
  "点选项或直接打字都可以。": "Choose an option or type your answer.",
  "直接粘贴资料；暂时没有也可以说明…": "Paste your material, or tell me if you do not have any…",
  "等待你的资料": "Waiting for your material",
  "等你补充": "Waiting for your input",
  "直接在输入框回复即可。": "Reply directly in the message box.",
  "你已经有一个「{0}」学习项目，不需要再建一个重复项目。": "You already have a “{0}” learning project. No duplicate is needed.",
  "继续已有项目": "Continue the existing project",
  "从现有 {0}% 进度继续": "Continue from {0}% progress",
  "把新目标合并进去": "Merge the new goal",
  "保留已完成进度，调整后续 Plan": "Keep completed progress and adjust the remaining plan",
  "选一个；想换主题也可以直接输入": "Choose one, or type a different topic",
  "已有同主题项目": "Existing project on this topic",
  "找到了已有学习项目": "Found an existing learning project",
  "继续学习或把新目标合并进去，不会创建副本。": "Continue it or merge your new goal without creating a duplicate.",
  "已保存 {0} 道面试题，接下来把它们纳入学习方案。": "Saved {0} interview questions. Next, we will include them in your plan.",
  "请根据已收录的题目继续制定计划": "Please continue planning from the saved questions",
  "把你收集的面试题直接粘贴到输入框即可；可以一次发多道，我会先去重收录，再生成针对性 Plan。": "Paste your interview questions below, several at once if you like. I will remove duplicates, save them, then create a targeted plan.",
  "等待你粘贴面试题": "Waiting for interview questions",
  "题目会先保存到你的个人题库。 ": "Questions will first be saved to your personal bank. ",
  "已切换到对应处理方式": "Switched to the appropriate workflow",
  "不会为这句话新建学习计划。": "This message will not create a new learning plan.",
  "意图还没有分析完成": "Request analysis incomplete",
  "你的输入和已填信息都还在，可以直接重试。": "Your input and collected information are preserved. Please retry.",
  "真实选择题，直接点击": "Multiple-choice assessment; click an option",
  "诊断 {0} / 最多 4": "Assessment {0} / up to 4",
  "你已经有一定基础，我会先问你 3–4 道小题，快速确认从哪里开始，然后就进入学习。": "You already have some experience. I will ask 3–4 short questions to find your starting point, then we will begin learning.",
  "第一题准备好了": "First question ready",
  "直接点击输入框上方的选项即可。": "Click an option above the message box.",
  "正在判断你的起点": "Finding your starting point",
  "这会决定哪些内容快进、哪些内容慢讲。": "This determines which content to move through quickly and which to explain carefully.",
  "下一道诊断题已准备好": "Next assessment question ready",
  "再点一题，就能更准确地开始。": "One more answer will help us choose a better starting point.",
  "开始概念讲解": "Start the concept explanation",
  "生成第一章讲义": "Generate chapter 1",
  "路线已经清楚了。我会先生成完整 `plan.md` 给你确认，确认后才开始第一章。": "The route is clear. I will create a complete `plan.md` for your confirmation before starting chapter 1.",
  "模型还没有生成合格的详细课程大纲，请点击重试。": "The model has not produced a valid detailed outline. Please click Retry.",
  "这份短方案已经显示。确认后我就开始概念讲解；不会再问时长或做起点诊断。": "The short plan is displayed. Confirm to begin the explanation; there will be no further duration questions or starting assessment.",
  "完整计划已经显示。先看看是否符合你的目标；需要修改就直接在下面说。": "The complete plan is displayed. Check it against your goal; type any changes below.",
  "满意就开始；要改直接在下面说": "Start if satisfied; type changes below",
  "专属大纲已生成": "Personalized outline generated",
  "请先阅读并确认，课程不会自动开始。": "Read and confirm first. The course will not start automatically.",
  "详细课程暂时没有生成成功，请重试。": "The detailed course was not generated successfully. Please retry.",
  "生成暂时中断": "Generation interrupted",
  "你的选择已保留，可以直接重试。": "Your choices are preserved. You can retry directly.",
  "正在锁定学习计划": "Confirming your learning plan",
  "确认后马上为你准备第一章。": "Chapter 1 preparation begins immediately after confirmation.",
  "学习计划已确认": "Learning plan confirmed",
  "第一章已经开始生成。": "Chapter 1 generation has started.",
  "计划还没有确认": "Plan not confirmed yet",
  "当前草案仍然保留，可以重试。": "Your current draft is preserved. You can retry.",
  "正在按你的意见调整 Plan": "Adjusting the plan to your feedback",
  "已完成的路线不会被清空。": "Completed progress will not be cleared.",
  "这次修改没有生成合格的新计划，请换一种说法再试。": "This revision did not produce a valid plan. Please rephrase and retry.",
  "计划已经按你的意见更新。请再看一遍，满意后点确认；还可以继续调整。": "The plan has been updated. Review it again, then confirm if satisfied or request more changes.",
  "满意就开始；还要改就继续输入": "Start if satisfied; otherwise type more changes",
  "Plan 已更新": "Plan updated",
  "请阅读新版计划并确认。": "Read the updated plan and confirm.",
  "计划修改暂时中断": "Plan revision interrupted",
  "旧草案还在，可以直接重试。": "Your previous draft is preserved. Please retry.",
  "保留已有学习进度，并合并这次的新目标：{0}": "Preserve existing progress and merge this new goal: {0}",
  "这几道是用来定起点的点击题，直接点上方选项就行；做完后继续用输入框问任何问题。": "These questions locate your starting point. Click the options above; afterwards you can use the message box for any questions.",
  "Learning Agent · 一步一步学会": "Learning Agent · Learn step by step",
  "跳到对话输入框": "Skip to the message box",
  "还没有学习项目。直接在右侧输入你想学什么。": "No learning projects yet. Type what you want to learn on the right.",
  "大纲": "Outline",
  "大纲 1 / 1": "Outline 1 / 1",
  "题库覆盖率": "Question bank coverage",
  "已掌握 0 / 共 0 题": "Mastered 0 / 0 questions",
  "课堂题、作业与面试题": "Classroom, homework and interview questions",
  "刷新": "Refresh",
  "开始一节课后，课堂选择题和课后作业会自动记录在这里。": "Classroom questions and homework are recorded here automatically after you start a lesson.",
  "开始复习": "Start review",
  "今日 0 题": "Today: 0 questions",
  "学习方案": "Learning plan",
  "正在准备学习方案": "Preparing your learning plan",
  "计划会随着你的表现持续调整": "Your plan adapts as you learn",
  "总进度": "Overall progress",
  "0 / 0 课": "0 / 0 lessons",
  "预计还需 25 分钟": "About 25 minutes left",
  "查看完整方案": "View full plan",
  "设置与提醒": "Settings and reminders",
  "本章 1 / 1": "Chapter 1 / 1",
  "掌握 0%": "Mastery 0%",
  "本页标题": "Page title",
  "加粗": "Bold",
  "斜体": "Italic",
  "高亮": "Highlight",
  "下划线": "Underline",
  "正文 · Markdown": "Body · Markdown",
  "代码 · 原样保存，不添加文字格式": "Code · Saved verbatim, without text formatting",
  "正文预览": "Body preview",
  "取消": "Cancel",
  "保存新版本": "Save new version",
  "第 1 页 / 共 1 页": "Page 1 of 1",
  "先建立直觉": "Build intuition first",
  "课程准备中": "Preparing your course",
  "这次课程没有生成完成，学习进度没有丢失。": "The course did not finish generating. Your progress is preserved.",
  "重新生成课程": "Regenerate course",
  "本页请做": "On this page",
  "本节练习目录": "Practice folder",
  "打开文件夹": "Open folder",
  "我的课堂笔记": "My class notes",
  "对话中的重点会自动写到这里": "Key points from the conversation are saved here automatically",
  "面试表达练习": "Interview delivery practice",
  "把知识说成面试答案": "Turn knowledge into interview answers",
  "复习 1 / 1": "Review 1 / 1",
  "回忆优先，不急着看答案": "Recall first; do not rush to reveal",
  "先在心里回答、口述，或直接在右侧对话框说出你的答案。": "Answer silently, aloud, or in the chat on the right before revealing.",
  "查看答案": "Reveal answer",
  "这次回忆起来有多顺？": "How easy was it to recall?",
  "1 天后再复习": "Review in 1 day",
  "3 天后再复习": "Review in 3 days",
  "7 天后再复习": "Review in 7 days",
  "课堂结束": "Class complete",
  "课后自己练一练": "Practice independently",
  "课后练习": "Homework practice",
  "上一页": "Previous page",
  "下一页": "Next page",
  "返回当前课程": "Return to current course",
  "先聊聊你想学什么": "Tell me what you want to learn",
  "学习导航": "Learning navigation",
  "打开 PPT": "Open slides",
  "连接中": "Connecting",
  "正在准备": "Preparing",
  "正在估算所需时间": "Estimating the wait",
  "当前：正在建立任务": "Current: creating task",
  "换个说法": "Explain differently",
  "给我提示": "Give me a hint",
  "再练一道": "One more exercise",
  "模拟面试": "Mock interview",
  "点一下就可以，不用打字": "Just click; no typing needed",
  "重新连接": "Reconnect",
  "给学习教练发消息": "Message your learning coach",
  "Enter 发送 · Shift+Enter 换行": "Enter to send · Shift+Enter for a new line",
  "持续更新": "Continuously updated",
  "完整学习方案": "Complete learning plan",
  "学习空间": "Learning space",
  "设置与档案": "Settings and profile",
  "当前学习": "Current learning",
  "查看完整 Plan": "View full plan",
  "课程路线、练习与完成标准": "Course path, practice and completion criteria",
  "今日回顾": "Today's review",
  "0 个知识点": "0 concepts",
  "学习提醒": "Learning reminders",
  "设置每日学习与复习时间": "Set daily learning and review times",
  "课件与支持": "Lessons and support",
  "课件版本记录": "Lesson version history",
  "查看或恢复之前的课件版本": "View or restore earlier lesson versions",
  "导出 Markdown": "Export Markdown",
  "下载当前已保存的课件": "Download the currently saved lesson",
  "导出 Bug 报告": "Export bug report",
  "下载诊断 JSON，不含对话内容，不会自动上传": "Download diagnostic JSON; no chat content or automatic upload",
  "学习档案": "Learning archive",
  "当前计划": "Current plan",
  "每日学习": "Daily learning",
  "开启提醒": "Enable reminders",
  "提醒时间": "Reminder time",
  "提醒内容": "Reminder content",
  "学习与复习": "Learning and review",
  "继续学习": "Continue learning",
  "今日复习": "Today's review",
  "正在读取当前系统的通知支持情况。": "Checking notification support on this system.",
  "保存提醒": "Save reminder",
  "删除学习项目": "Delete learning project",
  "确定删除？": "Confirm deletion?",
  "将删除这个项目的个人计划、进度、笔记、错题与作业。": "This deletes this project's personal plan, progress, notes, mistakes and homework.",
  "共享知识库中的教案不会被删除。": "Shared knowledge-library teaching materials will not be deleted.",
  "删除项目": "Delete project",
  "答对了，继续下一页。": "Correct. Continue to the next page.",
  "恢复只影响课件，代码、对话和历史作答会保留。": "Restoring affects only the lesson. Code, chat and past answers are preserved.",
  "确认恢复课件？": "Restore this lesson?",
  "恢复只影响课件；你的代码、对话和历史作答不会删除。修改过的题目需要重新作答。": "Restoring affects only the lesson. Your code, chat and past answers will not be deleted. Changed questions must be answered again.",
  "暂不恢复": "Not now",
  "确认恢复": "Confirm restore",
  "学习大纲": "Learning outline",
  "添加学习项目": "Add learning project",
  "大纲翻页": "Outline pages",
  "查看上方大纲": "Previous outline page",
  "查看下方大纲": "Next outline page",
  "课件编辑": "Lesson editing",
  "撤销课件修改": "Undo lesson edit",
  "收起 PPT": "Collapse slides",
  "编辑本页课件": "Edit this lesson page",
  "正文格式": "Body formatting",
  "一级标题": "Heading level 1",
  "二级标题": "Heading level 2",
  "三级标题": "Heading level 3",
  "退出复习": "Exit review",
  "课程页码": "Lesson pages",
  "调整讲义和对话宽度": "Resize lesson and conversation panes",
  "AI 学习教练": "AI learning coach",
  "打开学习导航与项目": "Open learning navigation and projects",
  "打开 PPT，返回当前页": "Open slides at the current page",
  "课件修改确认": "Confirm lesson changes",
  "请换一个更生活化的说法。": "Explain this using a more everyday example.",
  "先别告诉我答案，给我一个最小提示。": "Do not reveal the answer yet; give me the smallest useful hint.",
  "根据我刚才的表现，再出一道同难度练习。": "Based on my latest performance, give me another exercise at the same difficulty.",
  "开始模拟面试，请根据当前课程一次只问一道简答题。": "Start a mock interview based on the current course, asking one short-answer question at a time.",
  "可选回答": "Available answers",
  "移除课件引用": "Remove lesson reference",
  "问当前课程，或直接输入想学的新知识…": "Ask about this course, or type something new you want to learn…",
  "关闭学习方案": "Close learning plan",
  "关闭设置": "Close settings",
  "可切换的学习项目": "Available learning projects",
  "关闭学习提醒": "Close reminders",
  "取消删除": "Cancel deletion",
  "关闭版本记录": "Close version history",
  "界面语言": "Interface language",
  "选择界面语言": "Choose interface language",
  "本次已切换，但偏好尚未保存。请重试。": "Language changed for this session, but your preference was not saved. Please retry.",
  "历史课程和对话保留原语言；新内容使用当前语言。": "Existing courses and conversations keep their original language. New content uses your current language.",
  "复制这段代码": "Copy this code"
};
  function createI18n(options = {}) {
    const doc = options.document;
    const host = options.window;
    const userId = options.userId || "yang";
    const storage = options.storage;
    const fetcher = options.fetcher;
    const cacheKey = `learning-agent.locale.v1.${userId}`;
    let locale = "zh-CN", saveStatus = "saved", revision = 0, saveQueue = Promise.resolve(), jobNotice = null;
    const preferenceTimeoutMs = Math.max(1, Number(options.preferenceTimeoutMs) || 4000);
    try { if (storage?.getItem(cacheKey) === "en") locale = "en"; } catch (_) { /* Private mode can disable storage. */ }
    const bindings = new Map();
    const validLocale = value => value === "en" ? "en" : "zh-CN";
    function t(key, params = {}) {
      const text = locale === "en" && Object.hasOwn(dictionary, key) ? dictionary[key] : String(key ?? "");
      return text.replace(/\{(\w+)\}/g, (match, name) => params[name] == null ? match : String(params[name]));
    }
    function bind(node, property, render) {
      if (!node) return;
      if (!bindings.has(node)) bindings.set(node, new Map());
      const binding = {render, lastValue:undefined};
      bindings.get(node).set(property, binding);
      // Dynamic content takes ownership from its initial static placeholder.
      if (property === "textContent" || property === "innerHTML") node.removeAttribute?.("data-i18n");
      else node.removeAttribute?.(`data-i18n-${property.replace(/^@/, "")}`);
      const value = render();
      if (property.startsWith("@")) node.setAttribute(property.slice(1), value);
      else node[property] = value;
      binding.lastValue = property.startsWith("@") ? node.getAttribute?.(property.slice(1)) ?? value : node[property];
      return value;
    }
    function apply(scope = doc) {
      scope?.querySelectorAll?.('[data-i18n]').forEach(node => { node.textContent = t(node.dataset.i18n); });
      for (const attribute of ["title", "aria-label", "placeholder", "data-prompt"]) {
        scope?.querySelectorAll?.(`[data-i18n-${attribute}]`).forEach(node => node.setAttribute(attribute, t(node.getAttribute(`data-i18n-${attribute}`))));
      }
    }
    function refresh() {
      if (doc) { doc.documentElement.lang = locale; doc.title = t("Learning Agent · 一步一步学会"); }
      apply();
      for (const [node, properties] of bindings) {
        if (node.isConnected === false) { bindings.delete(node); continue; }
        for (const [property, binding] of properties) {
          const present = property.startsWith("@") ? node.getAttribute?.(property.slice(1)) ?? binding.lastValue : node[property];
          if (present !== binding.lastValue) { properties.delete(property); continue; }
          const value = binding.render();
          if (property.startsWith("@")) node.setAttribute(property.slice(1), value);
          else node[property] = value;
          binding.lastValue = property.startsWith("@") ? node.getAttribute?.(property.slice(1)) ?? value : node[property];
        }
      }
      doc?.querySelectorAll?.('[data-locale]').forEach(node => node.setAttribute('aria-checked', String(node.dataset.locale === locale)));
      const status = doc?.getElementById('languageSaveStatus');
      if (status) { status.textContent = saveStatus === 'unsaved' ? t('本次已切换，但偏好尚未保存。请重试。') : ''; status.hidden = saveStatus !== 'unsaved'; }
      const retry = doc?.getElementById('languageSaveRetry');
      if (retry) retry.hidden = saveStatus !== 'unsaved';
      const jobStatus = doc?.getElementById('languageJobNotice');
      if (jobStatus) {
        jobStatus.hidden = !jobNotice || jobNotice.locale === locale;
        jobStatus.textContent = jobStatus.hidden ? '' : t('刚完成的{0}使用{1}生成。原结果已保留；切换界面不会自动翻译，可按需查看翻译副本。', {0:t(({diagnosis:'诊断',plan:'计划',lesson:'课件'})[jobNotice.kind] || '课件'),1:jobNotice.locale==='en'?'English':t('中文')});
      }
    }
    function withLocale(options = {}, snapshot = locale) {
      const headers = new Headers(options.headers || {});
      if (!headers.has('X-Learning-Locale')) headers.set('X-Learning-Locale', validLocale(snapshot));
      return {...options, headers};
    }
    function apiFetch(input, init = {}) {
      if (!fetcher) return Promise.reject(new Error('No fetch implementation'));
      const origin = host?.location?.origin || 'http://localhost';
      const url = new URL(typeof input === 'string' ? input : input.url, origin);
      if (url.origin === origin && url.pathname.startsWith('/api/')) {
        const merged = {...init, headers: init.headers || (typeof input === 'object' ? input.headers : undefined)};
        return fetcher(input, withLocale(merged));
      }
      return fetcher(input, init);
    }
    async function preferenceRequest(work) {
      const controller = new AbortController();
      let timer;
      const deadline = new Promise((_, reject) => { timer = setTimeout(() => {controller.abort();reject(new Error('Preference request timed out'));}, preferenceTimeoutMs); });
      try { return await Promise.race([Promise.resolve().then(() => work(controller.signal)), deadline]); }
      finally { clearTimeout(timer); }
    }
    async function setLocale(value, {persist = true} = {}) {
      locale = validLocale(value); const currentRevision = ++revision; const snapshot = locale;
      try { storage?.setItem(cacheKey, locale); } catch (_) { /* Server remains authoritative. */ }
      refresh();
      if (host?.CustomEvent) doc?.dispatchEvent(new host.CustomEvent('learning:localechange', {detail: {locale}}));
      if (!persist || !fetcher) return locale;
      saveQueue = saveQueue.catch(() => {}).then(async () => {
        try {
          const response = await preferenceRequest(signal => fetcher('/api/preferences', {method:'PUT', signal, headers:{'Content-Type':'application/json'}, body:JSON.stringify({user_id:userId,locale:snapshot})}));
          if (!response.ok) throw new Error('Preference save failed');
          if (currentRevision === revision) saveStatus = 'saved';
        } catch (_) { if (currentRevision === revision) saveStatus = 'unsaved'; }
        if (currentRevision === revision) refresh();
      });
      await saveQueue;
      return locale;
    }
    async function loadPreference() {
      const startRevision = revision;
      if (!fetcher) return;
      try {
        const value = await preferenceRequest(async signal => {
          const response = await fetcher(`/api/preferences?user_id=${encodeURIComponent(userId)}`, {signal});
          return response.ok ? response.json() : null;
        });
        if (!value) return;
        if (revision === startRevision) await setLocale(value.locale, {persist:false});
      } catch (_) { /* Use this user's local cache until the server is available. */ }
    }
    function mount() {
      const button = doc?.getElementById('languageMenuButton'), menu = doc?.getElementById('languageMenu');
      if (!button || !menu) { refresh(); return; }
      const items = [...menu.querySelectorAll('[data-locale]')];
      const close = (focus = false) => { menu.hidden = true; button.setAttribute('aria-expanded','false'); if (focus) button.focus(); };
      const open = () => { menu.hidden = false; button.setAttribute('aria-expanded','true'); items.find(item => item.dataset.locale === locale)?.focus(); };
      button.addEventListener('click', () => menu.hidden ? open() : close());
      button.addEventListener('keydown', event => { if (['ArrowDown','ArrowUp'].includes(event.key)) {event.preventDefault();open();} });
      items.forEach(item => item.addEventListener('click', () => { setLocale(item.dataset.locale); close(true); }));
      menu.addEventListener('keydown', event => {
        if (event.key === 'Escape') { event.preventDefault(); close(true); }
        if (event.key === 'Tab') close();
        if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
          event.preventDefault(); const index = items.indexOf(doc.activeElement);
          items[event.key === 'Home' ? 0 : event.key === 'End' ? items.length-1 : (index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length].focus();
        }
      });
      doc.addEventListener('click', event => { if (!menu.contains(event.target) && !button.contains(event.target)) close(); });
      doc.addEventListener('keydown', event => { if (event.key === 'Escape' && !menu.hidden) close(true); });
      doc.getElementById('languageSaveRetry')?.addEventListener('click', () => setLocale(locale));
      refresh();
    }
    function errorText(value) {
      const original = String(value?.message || value || '');
      if (Object.hasOwn(dictionary, original)) return t(original);
      if (locale === 'en' && /\p{Script=Han}/u.test(original)) return 'The operation did not complete. Please retry. Export a diagnostic report in Settings for the original error details.';
      return original;
    }
    function completionText(value) {
      const original = String(value ?? '');
      const next = original.match(/^开始下一章：([\s\S]+)$/);
      if (next) return t('开始下一章：{0}', {0:next[1]});
      const missing = original.match(/^这些选择题还需要先答对：([\s\S]+)。回到对应页面直接点击选项，不需要写文字回答。$/);
      if (missing) return t('这些选择题还需要先答对：{0}。回到对应页面直接点击选项，不需要写文字回答。', {0:missing[1]});
      return t(original);
    }
    function noticeJobLocale(kind, value) { jobNotice = {kind,locale:validLocale(value)}; refresh(); }
    return {t, bind, apply, refresh, mount, setLocale, getLocale:()=>locale, withLocale, fetch:apiFetch, loadPreference, errorText, completionText, noticeJobLocale, persistenceStatus:()=>saveStatus, dictionary};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {createI18n, dictionary};
  if (root?.document) {
    let storage; try {storage=root.localStorage;} catch (_) { /* Disabled storage. */ }
    const i18n = createI18n({window:root, document:root.document, storage, fetcher:root.fetch?.bind(root), userId:new URLSearchParams(root.location.search).get('user_id') || 'yang'});
    root.LearningI18n = i18n;
    if (root.fetch) root.fetch = i18n.fetch;
    i18n.mount();
    i18n.ready = i18n.loadPreference();
  }
}(typeof window === 'undefined' ? null : window));
