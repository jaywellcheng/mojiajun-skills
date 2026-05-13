---
name: mojiajun-self-review-pipeline
description: 内容自审管线 — 生成后同一模型自审+自动修复+AI痕迹检测，替代子Agent审查模式
category: mojiajun
---

# 墨家军内容自审管线

## 一句话
生成内容后，同一模型在上下文内自审 → 打分 → 自动修复 → AI痕迹检测，不另起子Agent。

## 借鉴来源
Superpowers v5.1 inline self-review + Oh My OpenCode Comment Checker

## 管线流程

```
ai_create_note()
  ├─ ① Few-shot锚点（真实爆款示例）
  ├─ ② 思维链预推理（目标→痒点→角度→情绪→核心信息）
  ├─ ③ DeepSeek 生成
  ├─ ④ 行内自审（7条标准：标题/结构/风格/红线词/互动/标签/真实感）
  ├─ ⑤ 自动修复（score<90时当场修正）
  └─ ⑥ AI痕迹检测（15+规则：模板句式/空洞形容词/营销腔/emoji/细节缺失/句子节奏）
```

## 模块位置

| 模块 | 路径 | 作用 |
|------|------|------|
| self_review.py | agent_outputs/mozi/ | 自审引擎+review_xhs_note |
| ai_slop_detector.py | agent_outputs/mozi/ | 15+规则检测AI痕迹 |
| few_shot_library.py | agent_outputs/mozi/ | 爆款示例库+思维链推理 |
| xiaohongshu_note.py | agent_outputs/molan/ | 已注入三个模块的调用 |

## 关键参数

- 自审标准：XHS_NOTE_CRITERIA（7条）
- AI痕迹：15+正则规则，毫秒级，零API
- Few-shot：4类（story/guide/product/review）
- CoT：5步推理（读者画像→痒点→角度→情绪→核心信息）

## 效果

旧流程：生成 → 派发墨渊审查 → 打回 → 重写（2个Agent，来回调度）
新流程：生成 → 当场自审 → 当场修复（1个Agent，同一上下文）

实测：AI痕迹从23分（severe）→ 92分（none），耗时仅增~8s
