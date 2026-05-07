---
name: ai-slop-detector
description: 检测内容中的AI生成痕迹——15+规则引擎（模板句式/空洞形容词/营销腔/emoji密度/细节缺失/句子节奏），毫秒级完成，零API调用。借鉴oh-my-opencode Comment Checker理念。
category: mojiajun
tags: [content-quality, ai-detection, slop, self-review, xiaohongshu]
created: 2026-05-06
author: 小川
---

# AI痕迹检测器

## 一句话
纯规则引擎检测文案中的AI生成痕迹，输出人类感得分(0-100)和具体问题定位。

## 检测规则（15+条）

| 类别 | 规则 | 示例 |
|------|------|------|
| 模板句式 | 9条 | "不得不说""姐妹们听我说""谁懂啊" |
| 空洞形容词 | 8条 | "超美""绝了""太棒了""无敌好" |
| 营销腔 | 5条 | "限时""手慢无""按头安利""不买后悔" |
| emoji密度 | >3%触发 | AI倾向过度使用emoji |
| 细节缺失 | 数字/时间/地点/人物 | 具体度<1.5分触发 |
| 句子节奏 | 长度方差 | 过于均匀=AI特征 |
| 段落结构 | 3段式/5段式 | 过度规整=编排痕迹 |

## 使用

```python
from agent_outputs.mozi.ai_slop_detector import detect_ai_slop, check_and_flag

# 检测文本
r = detect_ai_slop("不得不说这款真的太美了！姐妹们听我说...")
# {"human_score": 23, "slop_level": "severe", "issues": [...]}

# 一站式检测笔记
note = check_and_flag({"note_title": "...", "note_content": "..."})
# note["_ai_slop"] = 检测结果，note["_ai_slop_warning"] = 严重时警告
```

## 定位
- 模块：`agent_outputs/mozi/ai_slop_detector.py`
- 已集成：self_review.py 的 review_xhs_note() 末尾自动调用
- module_dispatcher：`"ai_slop_detect": ("mozi", "ai_slop_detector", "main")`

## 得分等级
| 得分 | 等级 | 建议 |
|------|------|------|
| 90-100 | none | 直接发 |
| 75-89 | low | 微调 |
| 55-74 | medium | 改几处 |
| 35-54 | high | 重写 |
| 0-34 | severe | 必须重写 |
