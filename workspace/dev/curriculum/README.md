# 知识库架构（Curriculum）

## 一、知识库是什么

知识库 = **「教什么」的内容**，和 skills（「怎么教」的方法）分开：

| | 是什么 | 在哪 |
|---|---|---|
| skills | 教学**方法/流程**（建档、讲课、辅导…） | `workspace/.codex/skills/` |
| 知识库 | 教学**内容**（知识点、路线、概念图） | `workspace/curriculum/` |

知识库以 **Markdown 文件为主**（知识原子 + 学习路线），配两个 JSON（概念图）。**HTML 翻页课件是知识原子的「演示形态」，和 Markdown 原子成对存在、保持同步。**

## 二、目录层级

```
curriculum/
├── README.md                # 本文件
├── ATOMS.md                 # 知识原子的格式规范
├── shared/concept-map.json  # 跨语言通用概念（执行模型/控制流/函数/测试/调试/git）
├── python/
│   ├── concept-map.json     # Python 核心概念图（14 个概念）
│   ├── learning-paths/      # 学习路线（入门→项目→精通）
│   ├── atoms/               # 核心语言知识原子（.md，含配对 .deck.html）
│   └── libraries/           # 库/框架层级
│       ├── langchain/       #   每个库：README.md（是什么/前置/路线）+ atoms/
│       ├── langgraph/
│       ├── fastapi/
│       └── numpy-pandas/
└── go/
    ├── concept-map.json     # Go 核心概念图（15 个概念）
    ├── learning-paths/
    ├── atoms/
    └── libraries/
        ├── gin/
        ├── grpc/
        └── cobra/
```

**新增一个学习项目 = 新增一个文件夹**：语言/库一级建 `README.md` + `atoms/`，知识原子往里填。要学 Java，就建 `java/` 同理。

## 三、一个知识原子的两种形态（要同步）

一个知识点有两份资产，**改一份要同步改另一份**：

1. **Markdown 原子**（`<atom-id>.md`）—— 知识的**源头**：解决什么问题、最小示例、练习、常见误区。
2. **HTML 翻页课件**（`<atom-id>.deck.html`，和原子放同一目录）—— 知识的**演示**：一页页蹦出来的交互课件。

规则：
- 原子是「事实源」，deck 是「呈现」。改原子的知识点/示例/误区 → 同步改 deck；
- 改 deck 的讲解方式 → 回写原子的「交互演示」小节。
- 两者一起 git 提交，保持同版本。

## 四、知识库自生长（knowledge-curator）

教一个 curriculum 里没有的主题时，不是「现讲现忘」，而是**边教边沉淀**：

```
学新主题（如 Java / LangChain）
  → 发现 curriculum 没这个层级 → 建文件夹 + README
  → plan 模式生成学习大纲（learning-path）
  → 按大纲生成并教完一个完整章节（concept-teaching）
  → 章节运行验收通过 → 存成可复用资产（.md + .deck.html + 结构化讲义缓存）
  → 讲得不好/有误区 → 反向修订原子
```

这条链路由 `knowledge-curator` skill 与服务端验收钩子共同负责：未完成或未验证的内容不会入库；同主题、路线、能力层级与章节范围一致时优先复用已验收资产，减少模型调用。

## 五、现状盘点（Go + Python 覆盖度）

| 层 | 状态 |
|---|---|
| 概念图（结构） | ✅ 全面：Python 14 + Go 15 + shared 6 个概念，覆盖到 web/llm-apps/http/database |
| 知识原子（内容） | ⚠️ 薄：Python 5 + Go 6 个种子原子，只覆盖「入门」 |
| 库级（LangChain 等） | ❌ 空：层级已建好，原子靠自生长边教边补 |

**结论：结构够、内容不够。** 入门原子已备好，进阶 + 库级内容靠「边教边沉淀」逐步长全。
