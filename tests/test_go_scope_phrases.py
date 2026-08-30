import pytest
from backend.curriculum import KnowledgePoint
from backend.lesson_manifest import build_starter_lesson
from backend.lesson_generator import _scope_concepts, _validate_scope_evidence

@pytest.mark.parametrize("title,concepts,texts", [
    ("`package main` 与 `func main` 的启动约定", ["package main","func main","启动约定"], ["package main 声明程序包；func main() 是入口。", "启动约定：程序从 func main 开始，不是任意名称的函数。"]),
    ("`go` 子命令族：`version` / `run` / `build`", ["go version","go run","go build"], ["go version 检查安装；go run 运行；go build 生成可执行文件。", "再次使用 go version 核对版本，用 go run 验证更改。"]),
])
def test_structured_go_phrases_cover_components_without_copying_full_title(title,concepts,texts):
    assert _scope_concepts(title)==concepts
    point=KnowledgePoint(id="scope",title=title,outcome="解释",practice="运行",mastery_criteria="结果正确")
    bundle=build_starter_lesson(topic="Go",language="go",session_minutes=20,goal_route="foundation_engineer")
    bundle.manifest.covered_knowledge_point_ids=["scope"]
    for page,text in zip(bundle.manifest.pages,texts):
        page.markdown=text;page.code="";page.title="不构成正文证据"
    payload={"scope_evidence":[{"knowledge_point_id":"scope","page_ids":[p.id for p in bundle.manifest.pages[:2]]}]}
    _validate_scope_evidence(payload,bundle,[point])
    for page in bundle.manifest.pages[:2]:page.markdown=page.markdown.replace(concepts[-1],"未覆盖")
    with pytest.raises(ValueError):_validate_scope_evidence(payload,bundle,[point])
    for page in bundle.manifest.pages[:2]:page.markdown="无关内容";page.title=title
    with pytest.raises(ValueError):_validate_scope_evidence(payload,bundle,[point])
