"""Explicit transport doubles, not a substitute for real-model semantic evals."""
import json


def review_response(prompt, *, missing=False):
    data = json.loads(prompt.split("待审数据：\n", 1)[1])
    return json.dumps({"coverage": [{
        "knowledge_point_id": point["id"],
        "status": "missing" if missing else "covered",
        "reason": "测试模型报告：缺少所需讲解" if missing else "测试模型报告：页面已解释目标内容",
        "page_ids": [] if missing else [data["pages"][0]["id"]],
    } for point in data["knowledge_points"]]}, ensure_ascii=False)
