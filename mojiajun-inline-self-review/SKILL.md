---
name: mojiajun-inline-self-review
description: 行内自审模式——同一模型在上下文中审查自己的输出并自动修复，借鉴 Superpowers v5.1。生成后自审+AI痕迹检测串联，秒级完成。
category: mojiajun
tags: [self-review, quality, content, inline, superpowers, anti-ai-slop]
---

# 行内自审模式 v2

## 一句话
AI生成内容后，同一模型在自己的上下文里审查输出、发现并修复问题，不另起子Agent。2026-05-06升级：串联AI痕迹检测器。

## 核心思想（借鉴Superpowers v5.1 + oh-my-opencode Comment Checker）

传统：生成→派发子Agent审查→打回→重写（来回调度成本高）
v1：生成→当场自审→当场修复（同一上下文）
v2：生成→自审→修复→**AI痕迹检测**（毫秒级规则引擎）

## 实现

模块：
- `agent_outputs/mozi/self_review.py` — 自审引擎
- `agent_outputs/mozi/ai_slop_detector.py` — AI痕迹检测

### 自审查标准（7条）
1. 标题吸引力 — 心理开关≥2个
2. 正文结构 — 100-300字分段
3. 风格一致 — 天青浅人设
4. 红线词检查 — 9个禁用词
5. 互动引导 — 末尾提问
6. 标签质量 — 3-7个含核心词
7. 真实感 — 具体细节不AI腔

### AI痕迹检测规则（15+条，零API调用）
- AI模板句式："不得不说""姐妹们""谁懂啊"
- 空洞形容词："超美""绝了""太棒了""无敌好"
- 营销腔："限时""不买后悔""按头安利"
- emoji密度>3%触发
- 缺少细节：数字/时间/地点/人物
- 句子节奏：标准差<100触发
- 段落结构：3段式/5段式规整

### 注入molan
```python
# xiaohongshu_note.py: ai_create_note()
from agent_outputs.mozi.self_review import review_xhs_note
from agent_outputs.mozi.ai_slop_detector import check_and_flag

result = review_xhs_note(result)   # 自审+修复
result = check_and_flag(result)    # AI痕迹检测
```

### 实测
- 故意输入含5个红线词的营销文 → 7个问题检出+修复
- 正常内容 → 86分，3个小问题自动修正
- AI痕迹检测：营销文23分(severe)，人类风100分(none)
- 总耗时：~8s（DeepSeek审查）+ <1ms（规则检测）

## 位置
CORE-01: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/self_review.py`
CORE-01: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/ai_slop_detector.py`
