# 运行证据账本

日期：2026-08-30。全部公共证据使用合成用户，真实学习者目录和API密钥未进入报告。

## 已完成的运行

| 运行 | 实际结果 | 证据 |
| --- | --- | --- |
| 首次全量Python回归 | 673通过、1失败；e2e旧夹具缺新接口session_id | BC-05、`tests/test_e2e_learning_smoke.py` |
| 修复后全量Python回归 | 679通过，10.07秒；1条Starlette测试客户端弃用警告 | 最终Plan兼容补丁前的全套运行 |
| JavaScript回归 | 39通过，约0.217秒 | `node --test tests/*.test.cjs` |
| 工作区校验 | 23 Skills、35 concepts、0 errors；journey_count=0 | `workspace/dev/tools/validate_workspace.py` |
| 部署自检 | Codex、DeepSeek配置、Skills与工具检查通过 | `python -m backend.deployment_check`；不是模型生成测试 |
| Bash语法与diff空白检查 | 返回0 | `bash -n run.sh`、`git diff --check` |
| 受控35秒最终探针 | 启动202／0.0107秒；最慢查询0.1195秒；总35.227秒；模型1次／35.002秒 | `evidence/controlled-35s-final.json` |
| 真实AI前端诊断最终探针 | 启动202／0.0103秒；最慢查询0.166秒；总22.549秒；模型1次／22.346秒 | `evidence/live-diagnosis-final.json` |
| 原始真实小白Plan | 262.03秒；validation_failed；未进入课件阶段 | 本地`evals/runs/20260830-200459-lesson-retest`；公共原因见BC-07 |

`controlled-35s-r1/r2`和`live-diagnosis-r1`保留早期迭代证据；它们早于最终确认收据修复，不冒充最终候选。两个final探针包含当时核心源码SHA-256。并行进行的本机测试可能影响毫秒级时延，因此数字是样本，不是SLA。

## 代码审查

- 跨平台：规范与质量复查通过；真实POSIX进程树测试补齐后复测。Windows API行为是模拟。
- 诊断：规范复查发现完整submission、旧指针恢复、旧答案守卫问题，修复后14项当时测试通过。
- 诊断质量复查：新增取消/确认收据/epoch修复后，由另一审查者独立运行后端19项、前端12项，未发现阻断问题；磁盘故障事务恢复未验证。
- 报告：规范与质量复查修正空白证据、NaN、原型敏感ID、焦点问题；Python12项及Node假DOM3项通过。不能据此宣称截图/浏览器下载通过。

## 不能声称已完成的验收

- 没有原生Windows机器/runner，不是“Windows已实测通过”。
- 没有WorkBuddy同版本代理日志，不能确认它的具体超时阈值。
- 内置浏览器拒绝本地报告URL，未绕过限制；真实视觉与浏览器交互验收BLOCKED。
- 没有Owner签署，人审数量0。

Plan格式修复后的回放、课件以及最后一次全量结果，见后续追加记录和报告对应run；不覆盖上表首次失败。

## 最终追加记录

- 最终候选全量：**685项Python通过，9.24秒**；**39项Node通过，0.189秒**。仍有一条Starlette测试客户端弃用警告。工作区、部署、shell和diff检查再次通过。候选源文件指纹见 `final-verification.json`。
- Plan格式回归：新增5项先失败后通过，仅对精确列表包装做规范化，后续完整性检查未降低；独立复审通过。
- 原Plan响应和原研究材料回放：0.01秒通过，21章66知识点；深研究校验6来源9覆盖域。它不是新模型生成。
- 新课件首轮：313.20秒，因一个知识点未列出至少两个相关页面而校验失败；wire-format自动规范化无效，进入一次模型修复。
- 新课件修复：77.90秒，随后成功。课件阶段合计391.13秒，12页（5讲解、2示例、3点击题、1编程练习、1总结），覆盖3个知识点；真实练习目录中有README.md和main.go。详见 `evidence/beginner-plan-lesson-retest.json`。
- 回放工具同步修正：带原研究材料一起回放，避免缺文件导致假失败；互斥的两种回放模式在参数阶段拒绝，1项回归先红后绿。原始模型输出继续只留在Git忽略的evals/runs。
- HTML报告已构建，16个聚合Case最新初判为14 PASS、1 UNVERIFIABLE、1 BLOCKED；保留首次失败与后续复测。人审仍未签署。
