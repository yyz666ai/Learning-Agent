---
name: project-scaffolder
description: Use when a learning plan requires runnable chapter files, a multi-lesson coding course, a project-based route, or a workspace the learner will open in an editor.
---

# 课程项目脚手架

一个学习主题对应一个课程根目录，让学习者可以直接用 Cursor 或 Trae 打开，并在同一个项目里完成所有章节。

## 目录合同

```text
projects/<topic>-learning-path/
├── README.md
├── plan.md
├── course.json
├── 01-<chapter>/
│   ├── README.md
│   ├── diagrams/
│   ├── src/
│   ├── exercises/
│   └── notes/
└── final-project/
```

## 规则

- 页面告诉用户打开课程根目录，不让用户猜内部绝对路径。
- 每章只创建自己的文件；重新生成讲义不能覆盖用户已经编辑的文件。
- 带详细中文注释的示例代码放 `src/`，课后独立练习放 `exercises/`，个人问题与总结放 `notes/`；不为打印输出单建验收目录。
- 项目语言有惯用结构时遵循惯例，但保留统一的课程入口文件。
- `README.md` 说明如何打开、运行、学习和提交，不包含隐藏答案。
