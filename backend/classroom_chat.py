"""Explicit classroom modes; generation stays with the configured Codex agent."""
import re


def chat_mode(message: str, events: list[dict]) -> str:
    if re.search(r"(?:结束|退出|停止|暂停).{0,6}(?:模拟)?面试", message):
        return "learning"
    if re.search(r"(?:开始|进行|来一场|帮我|给我).{0,8}模拟面试|(?:扮演|当).{0,4}面试官", message):
        return "interview"
    # A failed generation must not advance or establish an interview session.
    previous = next((event for event in reversed(events) if event.get("role") == "assistant"), {})
    return "interview" if previous.get("chat_mode") == "interview" else "learning"


INTERVIEW_POLICY = (
    "当前是用户主动要求的文字模拟面试，不是普通答疑。扮演面试官，一次只问一道开放简答题。"
    "第一轮优先使用用户收集的问题，其次用当前课件面试题；没有题库则围绕已学内容出题，不假称来自真实公司。"
    "后续先针对用户实际答案简短点评正确点和遗漏，再只追问一个问题，循序加深。"
    "未作答不提前展示参考答案；用户明确要答案则展示并标注参考，不记为独立掌握，下一轮提供变体验证。"
    "不要要求选择A/B/C，不承诺录音或回听；收到结束面试请求就总结已有表现，不捏造分数。"
)

ANSWER_POLICY = (
    "用户只说不会时先给最小提示；用户明确索要参考答案或完整解法时可以展示并解释，标注为参考答案。"
    "参考答案、复制或运行通过都不是独立掌握证据。之后可建议做一道变体，不能强迫额外答题才能继续浏览。"
)
