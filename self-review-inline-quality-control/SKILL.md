---
name: self-review-inline-quality-control
description: 行内自审模式——同一AI模型在生成后立即审查自己的输出并自动修复，不另起子Agent。借鉴Superpowers v5.1 inline self-review，7条标准审查→发现问题→当场修复。适用于任何AI内容生成管线。
category: mojiajun
tags: [self-review, quality, inline, superpowers, molan, content-pipeline]
created: 2026-05-06
author: 小川
---

# 行内自审（Inline Self-Review）

## 一句话
AI生成内容后，同一个模型在同一个上下文里立刻审查+修复，不另起子Agent。

## 为什么用
- Subagent QA：25min（来回调度+上下文重建）
- 行内自审：~8s（同一上下文，追加一轮消息）
- 多抓3-5个问题（模型对自己的输出最熟悉）

## 核心模块
CORE-01: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/self_review.py`

### 通用引擎 `self_review(content, criteria, content_type)`
```python
from agent_outputs.mozi.self_review import self_review

result = self_review(
    content={"title": "标题", "body": "正文"},
    criteria={"标题吸引力": "是否触发2个心理开关", "真实感": "是否像活人写的"},
    content_type="note",
)
# result["content"] → 修复后的内容
# result["review"]  → {score, issues_found, issues_fixed, verdict}
```

### 预设审查标准

| 标准集 | 用途 | 条数 |
|--------|------|------|
| `XHS_NOTE_CRITERIA` | 小红书笔记 | 7条 |
| `TITLE_CRITERIA` | 标题专项 | 5条 |

### 小红书专用 `review_xhs_note(note_dict)`
```python
from agent_outputs.mozi.self_review import review_xhs_note
note = {"note_title": "...", "note_content": "...", "tags": [...]}
fixed_note = review_xhs_note(note)
# fixed_note["_self_review"] → 审查元数据
```

## 注入方式

在生成管线的 return 前加一行：
```python
result = review_xhs_note(result)
return result
```

## 踩坑

1. **导入路径**：模块在 mozi/ 目录，调用方在 molan/。需要 `sys.path.insert(0, "/home/ubuntu/mojiajun-queue")`
2. **API Key**：自审也调用DeepSeek。确保 `.env` 已加载
3. **修复兜底**：自审失败不应中断主流程，加 try/except
4. **审查标准要具体**：模板化的标准（"内容质量好"）不如具体可执行的标准（"标题是否触发2个心理开关"）

## 实测数据

| 输入 | 得分 | 发现 | 修复 | 耗时 |
|------|------|------|------|------|
| 营销腔笔记（7个问题） | 20→86 | 7 | 全部 | ~14s |
| 正常笔记 | 86 | 3 | 2 | ~8s |

## 与墨渊分工

旧：墨蓝生成 → 墨渊审查 → 打回
新：墨蓝生成 → 行内自审修复 → 墨渊（仅处理深度问题）

## 全链路（v2新增：AI痕迹检测 + Few-shot + CoT）

```
ai_create_note()
  ├─ ① Few-shot锚点（从示例库取1-2篇爆款笔记作风格锚点）
  ├─ ② 思维链预推理（目标→痒点→角度→情绪曲线→核心信息）
  ├─ ③ DeepSeek生成（带锚点+策略指导）
  ├─ ④ 行内自审（7条标准，自动修复）
  └─ ⑤ AI痕迹检测（15+规则，毫秒级）
```

模块位置：
- 自审引擎：`mozi/self_review.py`
- AI痕迹检测：`mozi/ai_slop_detector.py`
- Few-shot+CoT：`mozi/few_shot_library.py`

## 踩坑

1. **导入路径**：模块在 mozi/ 目录，调用方在 molan/。需要 `sys.path.insert(0, "/home/ubuntu/mojiajun-queue")`
2. **API Key**：自审也调用DeepSeek。确保 `.env` 已加载
3. **修复兜底**：自审失败不应中断主流程，加 try/except
4. **审查标准要具体**：模板化的标准不如具体可执行的标准
5. **emoji正则**：Python 3.12+ 不支持复杂Unicode范围正则，改用字符级 ord() 检测
6. **f-string注入**：向已有代码注入带花括号的f-string时，需注意原有字符串的引号闭合
7. **Few-shot锚点质量决定上限**：AI写的示例 → AI学AI → 越来越平。应该用真实爆款笔记做锚点
