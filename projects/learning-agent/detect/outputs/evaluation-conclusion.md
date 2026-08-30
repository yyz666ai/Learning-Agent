# 结论：跨平台与诊断可靠性

## 本轮已实现

1. Mac/Linux的run.sh和Windows的run.cmd共享Python启动流程；统一Codex命令解析、UTF-8 stdin和子进程超时清理。
2. 网页诊断改为202后台任务+短轮询；持久化任务与回答，重试复用请求ID，取消和跨目标保护，确认收据恢复，旧响应不改新页面。
3. 目录/提醒返回真实平台能力；不再把HTTP成功或偏好保存说成系统操作成功。
4. 修复真实Plan中知识点标题被列表包裹时的误拒绝，不放宽课程完整性要求。
5. 离线HTML报告支持筛选、输入/GT/实际结果对照、首败与复测、草稿及JSON/JSONL附件导出。按detect证据结构分离原始run、机器评分和人工复核。

## 实测回答

- **能避免这类长诊断HTTP连接吗？** 新网页路径可以：受控35秒模型等待时，start约0.011秒返回；重复start只调用模型一次。不能据此倒推出WorkBuddy的确切代理超时设置。
- **模型是否变快？** 不据此承诺。真实AI前端诊断最终抽样22.55秒；小白第一章课件约391秒，包含一次自动修复。后台任务提高的是等待与恢复可靠性，不是生成速度。
- **Plan与课件是否跑通？** 本轮同一失败Plan及研究材料回放通过；显式确认后新生成12页课件并落盘练习。Plan不是重新生成，课件不是浏览器视觉验收，不代表全部路线或教学质量已验证。
- **Windows是否已经测试完成？** 没有。新增入口与离线Windows契约测试通过，但没有原生Windows机器执行安装→诊断→Plan→课件→练习的全流程。

## 自动验证

最终Python685项、Node39项通过；工作区校验23 Skills/35 concepts/0 errors，部署自检通过。报告16聚合Case最新14 PASS、1 UNVERIFIABLE、1 BLOCKED。原始失败保留在各case的run记录里。

## 使用方式

更新仓库后重启服务并刷新页面：Mac/Linux使用 `./run.sh`，原生Windows使用 ` .\run.cmd`。只运行一个服务进程。旧版同步onboarding兼容端点和课件修订候选仍需代理保留合适超时；取消不保证模型马上停止计费。

下载后用系统浏览器打开 [交互报告](report/index.html)。GitHub代码页不直接执行HTML。报告的真实浏览器验收因工具安全限制未完成，不应把假DOM自动测试当成截图验收。

## Gate与交接

正式Detect Gate：**INSUFFICIENT_EVIDENCE**。代码修改与回归证据可供使用和复核，不自动代表Owner批准上线。下一步由维护者补充原生Windows/实际代理日志、真实浏览器报告验收并签署复核；磁盘中途故障、多实例调度、全部模型/用户路线质量仍不在本次证明范围内。

详细口径：[Dataset](evaluation-dataset.md) · [Run Plan](evaluation-run-plan.md) · [Evidence](run-evidence.md) · [Scoring](scoring-results.md) · [Bad Case](bad-case-analysis.md) · [Human Review](human-review.md)。
