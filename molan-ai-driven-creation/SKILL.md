---
name: molan-ai-driven-creation
description: molan AI驱动创作引擎——DeepSeek API生成差异化小红书笔记，替代固定模板。use_ai=True触发，自动fallback到模板。
version: 1.0.0
tags:
  - mojiajun
  - molan
  - ai-creation
  - deepseek
---

# molan AI驱动创作引擎

## 使用

在payload中加 `"use_ai": true` 即可触发AI创作：

```python
payload = {
    "description": "景德镇冷粉测评",
    "style": "真实调侃",
    "note_type": "story",
    "target": "美食探店用户",
    "use_ai": True,
}
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| description | ✅ | 创作指令，描述要写什么 |
| style | 否 | 风格要求，默认"真实本地人视角" |
| note_type | 否 | story/guide/product/review |
| target | 否 | 目标用户 |
| use_ai | ✅ | 必须=True |

## 位置

CORE-01: `/home/ubuntu/mojiajun-queue/agent_outputs/molan/xiaohongshu_note.py`
- `ai_create_note()` — AI创作函数
- `create()` L320 — 入口，use_ai=True时走AI分支

## 恢复

xiaohongshu_note.py含ai_create_note函数 + create函数L320有AI分支判断。
