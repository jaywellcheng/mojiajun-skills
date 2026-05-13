---
name: mojiajun-external-skill-internalization
description: 将外部GitHub仓库的Agent Skill文件（如pm-skills）内化为墨家军skill。用平行subagent并行干活，不是AS1/AS2。
tags:
  - mojiajun
  - pm
  - skill-internalization
source: 墨家军实战验证 2026-05-08
---

# 外部Skill内化流程

## 核心原则

**AS1/AS2（Aider+DeepSeek）只能写代码，不能创建新文件。**
Aider对新建文件有已知bug（文件名混乱、写到错误路径）。
创建新SKILL.md → 用 `delegate_task` 平行派发 subagent。

## 四步法

### 第一步：调研
- `web_search` + `web_extract` 搞清楚外部repo有什么技能
- 列出所有技能清单，跟大威确认哪些需要

### 第二步：写任务书
为每个 subagent 写一个任务文件（放 `~/cc1-workspace/`），必须包含：

```markdown
## 源材料 URL（用 web_extract 获取）
- 每个原始 SKILL.md 的 raw URL

## 输出路径
- 明确到 `~/.hermes/skills/mojiajun/{name}/SKILL.md`

## 格式规范
- YAML frontmatter 模板（name/description/tags/source）

## 必须绑定的业务
- OPC AI / CHANANCE / 小红书 等具体场景
- 每个框架给一个"大威可以直接用"的具体示例

## 风格参考
- 参考现有 skill（如 mojiajun-marketing）的风格
- 表格+短句+实操模板，不写论文
```

### 第三步：平行派发
用 `delegate_task` 的 `tasks` 数组模式，2-3个子Agent同时跑：

```
delegate_task(tasks=[
  {goal: "创建 pm-pricing 和 pm-monetization", context: "读取任务文件...", toolsets: ["terminal","file","web"]},
  {goal: "创建 pm-value-proposition 和 pm-battlecard", context: "读取任务文件...", toolsets: ["terminal","file","web"]},
])
```

每个 subagent 给 `["terminal","file","web"]` 工具集。

### 第四步：审核
- 逐个 `read_file` 检查产出
- 检查项：格式、字数1000-2000、业务绑定、可操作模板
- 通过 → 完成；不通过 → 单独再派 subagent 修

## 划清边界

| 任务类型 | 工具 | 原因 |
|----------|------|------|
| 新建SKILL.md等内容文件 | delegate_task subagent | Aider新建文件有bug |
| 修改现有代码（几行改动） | AS1/AS2（Aider） | Aider擅长diff编辑 |
| 复杂代码新建（多函数） | 小川亲自写核心 | Aider DeepSeek格式不稳定 |

## 实测案例

- 2026-05-08：pm-skills → 墨家军5个技能（pricing/monetization/value-prop/battlecard/growth-loops），前4个2 subagent并行，第5个单独派。6分钟完成，质量高。参考 `mojiajun-marketing` 风格。
