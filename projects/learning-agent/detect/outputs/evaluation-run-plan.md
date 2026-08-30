# 运行计划与复现

基线：`32ffe836fe7e043e1c325b2baa935ef737288474`。候选：本轮 main 工作目录；最终报告记录核心源文件 SHA-256。单服务进程，Mac 本机 Python 虚拟环境和 Node。Windows 行为通过显式 platform_name、系统调用替身验证，不称 Windows 实机测试。

## 确定性回归

```sh
.venv/bin/python -m pytest -q
node --test tests/*.test.cjs
.venv/bin/python workspace/dev/tools/validate_workspace.py
.venv/bin/python -m backend.deployment_check
bash -n run.sh
git diff --check
```

修复前失败与修复后运行分别保留；全套测试执行一次最终回归，不用重复直到碰巧成功作为通过标准。平台测试使用本轮创建的子进程，不结束用户正在运行的8787服务。

## 延迟和真实模型探针

```sh
.venv/bin/python tools/verify_diagnosis_jobs.py --mode controlled --output /tmp/diagnosis-controlled-new.json
.venv/bin/python tools/verify_diagnosis_jobs.py --mode live --output /tmp/diagnosis-live-new.json
.venv/bin/python tools/evaluate_lessons.py --case beginner --timeout 360
```

第一项：受控35秒假模型；第二项会调用已配置的项目DeepSeek API并产生费用。两项均使用临时合成用户，不访问真实学习者目录。HTTP耗时通过本地 ASGI TestClient 计时，因此不能用于证明 WorkBuddy 代理或公网表现。

第三项：从**已确认画像测试夹具**开始，不是自然语言意图识别全链路；先检查 Plan，成功才确认并生成第一课。原始提示词/生成内容留在被 Git 忽略的 `evals/runs/`；公共报告只保留脱敏结果、问题位置与测量值。回放原响应时必须标记 replay，不计为新模型生成成功。

## 边界

- 每个诊断调用有120秒上限；最多一次结构修复。网络失败不假扮结构错误无限重试。
- 浏览器短请求8秒超时；结果未知时复用请求标识查询。取消阻止提交，但不能承诺立刻终止已发出的收费模型调用。
- Node报告交互测试是**假DOM**，不是截图验收。内置浏览器拒绝打开本轮本地报告文件，遵守限制不换端口或工具绕过；真实视觉/下载验收记BLOCKED。
- 所有评分都是机器初判，Owner签署之前 `review_status=pending`、`valid_score=null`。
- 原始批次不可覆盖；HTML由固定JSON重建，后续复测用新目录。
