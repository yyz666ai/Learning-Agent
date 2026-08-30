# Dataset / Case / GT 映射

状态：执行草稿，等待 Owner 复核；不代表已通过 Detect Gate。

本轮按风险选取确定性契约测试、受控慢模型和真实模型抽样，不进行随机抽样估计总体通过率。报告中的一个 Case 可以映射多个参数化测试；Case 数量不等于 pytest 测试数量。

| eval_set | Case 范围 | GT 来源 | 执行方式 |
| --- | --- | --- | --- |
| platform | 启动入口、Windows npm 包装器、中文长输入、超时清理、文件夹与提醒 | 已批准跨平台设计；shell=False、错误码与 UTF-8 往返契约 | Mac 实进程 + Windows 离线模拟 |
| diagnosis | 短启动、去重、刷新、取消、旧目标、确认重试、服务重启 | 已批准会话与任务边界；旧结果不得写入新目标 | Python HTTP/注册表测试 + Node 网络/状态测试 |
| latency | 模型等待35秒时请求耗时；真实诊断一次 | 启动不等待模型、只生成一次、完整有效题目 | 独立临时目录、ASGI TestClient |
| report | Case/GT/Run/Score 分离、证据、过滤、详情、草稿、导出 | detect 输出合同；未知不记PASS、人审不伪造 | Python renderer 测试 + Node 假DOM逻辑测试 |
| learning-chain | 已确认小白Go画像 → Plan → 确认 → 第一课 | 既有课程结构校验与课件合同 | 真实Codex调用；失败时后续阶段不算执行 |
| acceptance-gaps | 原生Windows全链路、报告真实浏览器验收 | 必须有对应环境的真实运行记录 | 缺证据分别记 UNVERIFIABLE / BLOCKED |

每个具体 Case、输入、期望和 run_id 见报告附件 `cases.jsonl`、`ground_truth.jsonl`、`runs.jsonl`。GT 由批准的设计合同确定，不把 GT 或裁判结论传给被测模型；真实模型仅接收教学/诊断任务及合成画像。

不测试真实用户私有目录；用户提供的 Windows 29–33秒仅作外部线索，不作为当前候选版本的测量值。真实题目抽样仅证明该样本成功，不证明覆盖全部技术栈或所有用户目标。
