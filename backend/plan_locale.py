"""Translate only the Plan wire-format labels, never its authored contents."""
import re

LABELS = {
    'Current task': '当前任务', 'Learning outcomes': '学习成果', 'Teaching strategy': '教学策略',
    'Knowledge coverage map': '知识覆盖地图', 'Final acceptance criteria': '最终达成标准',
    'Capstone project': '毕业项目', 'Stages': '阶段', 'Knowledge points': '知识点',
    'What to learn': '本阶段要学', 'Practice': '练习', 'Completion evidence': '完成证据',
    'Estimated sessions': '预计课次', 'Session minutes': '单次分钟', 'Homework minutes': '课外练习分钟',
    'Session breakdown': '分次安排', 'Required knowledge points': '必要知识点',
    'Why now': '为什么现在学', 'Deliverable': '真实产出', 'Acceptance method': '验收方式',
}


def plan_labels(markdown, *, english=False):
    mapping = {v:k for k,v in LABELS.items()} if english else LABELS
    lines = []
    fence = None
    for line in markdown.splitlines(keepends=True):
        if re.match(r'^\s*(```|~~~)', line):
            fence = None if fence else line.lstrip()[:3]
        if not fence:
            for source, target in mapping.items():
                line = re.sub(r'^(#{2,4}[ \t]+)' + re.escape(source) + r'[ \t]*(?=\n?$)', lambda m:m[1]+target, line, flags=re.I)
                line = re.sub(r'^(-\s+)' + re.escape(source) + r'\s*[：:]\s*', lambda m:m[1]+target+(': ' if english else '：'), line, flags=re.I)
            if english:
                line = re.sub(r'^(#{2,3}\s+)阶段\s*(\d+)\s*[：:]?\s*', r'\1Stage \2: ', line)
            else:
                line = re.sub(r'^(#{2,3}\s+)(?:Stage|Chapter|Phase)\s+(\d+)\s*[:：.-]?\s*', r'\1阶段 \2：', line, flags=re.I)
        lines.append(line)
    return ''.join(lines)


def english_plan_contract():
    return 'English Plan labels (use exactly these labels, content remains personalized):\n' + '\n'.join(f'{zh} = {en}' for en,zh in LABELS.items()) + '\nStage headings: ### Stage N: Title\n'
