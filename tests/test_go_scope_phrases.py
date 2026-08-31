"""Go composite titles are now data for the semantic reviewer."""
import pytest
from tests.test_scope_instructional_titles import validate

@pytest.mark.parametrize("title,concepts,texts", [
    ("`package main` 与 `func main` 的启动约定", ["package main","func main","启动约定"], ["package main 声明程序包；func main() 是入口。", "启动约定：程序从 func main 开始，不是任意名称的函数。"]),
    ("`go` 子命令族：`version` / `run` / `build`", ["go version","go run","go build"], ["go version 检查安装；go run 运行；go build 生成可执行文件。", "再次使用 go version 核对版本，用 go run 验证更改。"]),
])
def test_go_phrases_do_not_require_literal_title_repetition(title, concepts, texts):
    report = validate(title, texts)
    assert report.coverage[0].status == "covered"
