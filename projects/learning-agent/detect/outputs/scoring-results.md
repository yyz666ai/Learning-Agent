# 机器初判与硬门

批次：`20260830-cross-platform-diagnosis-r1`。

| 最新状态 | 聚合Case数 | 含义 |
| --- | ---: | --- |
| PASS | 14 | 在该Case声明的环境和证据范围内满足合同 |
| FAIL | 0 | 最新运行没有未关闭的已执行失败；历史失败仍保留 |
| UNVERIFIABLE | 1 | 缺少原生Windows端到端运行证据 |
| BLOCKED | 1 | 报告真实浏览器验收受工具安全策略阻断 |

不能把“14通过”解读成所有功能已完成，也不能用14/16估计产品成功率。Case为按风险聚合，不是随机采样；与685项Python、39项Node测试不是同一分母。

所有run判定包含case_id、gt_id、run_id、理由、证据位置与grader；`scores.jsonl` 中 `review_status=pending`、`valid_score=null`。没有Owner复核，**有效人工评分数量0**，不计算人审通过率。

根因归类和首败保留：确认200→409、取消恢复、旧e2e接口夹具、Plan列表标题误拒绝、课件首轮覆盖不足。课件经过一次模型修复才通过，不把第二次结果反写为第一次成功。

硬门：原生Windows部署验收、报告真实浏览器验收及Owner签署未满足，因此正式Detect结论为 **INSUFFICIENT_EVIDENCE**；代码回归结果可交付，不伪造上线批准。
