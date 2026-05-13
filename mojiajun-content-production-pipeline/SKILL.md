---
name: mojiajun-content-production-pipeline
description: 小红书内容生产全链路 — 本地AI写软文→CORE-01任务派发→墨蓝生成笔记→墨青生成MJ Prompt→TT+API出图→封面合成→素材归档
category: mojiajun
tags: [content-pipeline, xiaohongshu, multi-agent, image-generation, mojiajun]
---

# 墨家军内容生产全链路

## Overview

Complete pipeline for producing a Xiaohongshu post with AI-generated images:

```
User prompt → Molan writes note → Smart engine selection → 
Moqing generates images → CoverMaker creates cover → 
Media assets archived → User review & publish
```

## Step-by-Step

### 1. Create a Note with Images

```python
from agent_outputs.moyuan.api_toolkit.content_pipeline import create_note_task

result = create_note_task(
    title="深圳今天出大太阳，我却想吃一碗景德镇的冷粉",
    content="深圳今天阳光明媚...（正文内容）",
    images_desc=[
        {"desc": "深圳阳台外城市远景，蓝天白云，现代高楼", "purpose": "封面"},
        {"desc": "一碗景德镇冷粉的特写，橘子皮榨菜油辣椒", "purpose": "配图"},
    ]
)
print(f"Note: {result['note_id']}, {result['total_images']} images queued")
```

### 2. Check Pipeline Status

```python
from agent_outputs.moyuan.api_toolkit.content_pipeline import check_pipeline_status

status = check_pipeline_status(result["note_id"])
print(f"Completed: {status['tasks']['completed']}/{status['tasks']['total']}")
```

### 3. Smart Engine Selection

The system auto-selects the best engine:

```python
from agent_outputs.moyuan.api_toolkit.smart_engine import suggest_engine

# For covers/Xiaohongshu → GPT Image 2
# For artistic/stylized → Midjourney (TT API)
# For fast/cheap → FLUX (Fal.ai)
suggestion = suggest_engine("一张小红书封面", purpose="封面")
print(f"Using: {suggestion['name']} (${suggestion['cost']})")
```

### 4. Cover Art Generation

```python
from agent_outputs.moyuan.api_toolkit.cover_maker import make_cover

# Add title text to an image
result = make_cover(
    "/path/to/generated/image.jpg",
    "深圳今天出大太阳",
    "我却想吃一碗景德镇的冷粉"
)
```

### 5. Media Archiving

Every generated image is auto-archived to `media_assets` table:

```sql
SELECT category, COUNT(*) FROM media_assets GROUP BY category;
```

## Xiaohongshu Content Strategy

Based on analysis of 151+ sample notes:

### Title Patterns (7 Weapons)

1. **反常悬念法**: `好抽象的茶漏` — triggers curiosity + surprise
2. **预期偏差法**: `烧完哭了，怎么会是这个颜色` — highest comment rate (13.3%)
3. **地域锚定法**: `P人熬夜进化J人整理景德镇旅游攻略` — highest collect rate (77.8%)
4. **低姿态分享法**: `晒出拼多多买到最成功的小东西` — best conversion
5. **情感痛点法**: `没有老公在身边的旅行一点都不开心` — 18% comment rate
6. **直击痛点法**: `10个厨房爽点这才是真正的直击痛点` — high collect rate
7. **反向收割法**: `景德镇看上这2个万花杯，该怎么选？` — good engagement

### Content Type Priority

| Phase | Type | Purpose |
|-------|------|---------|
| Early (1-10) | 攻略类 | Collect rate 77.8%, build following |
| Mid (11-30) | 制陶过程+好物种草 | Engagement + trust |
| Late (30+) | 软性植入产品 | Monetization |

### Writing Tips for 45-year-old Jingdezhen native in Shenzhen

- Write in first person, authentic voice
- Reference real details: 冷粉 with 橘子皮+榨菜+油辣椒, not 萝卜干 or 热油
- Use real weather, real locations (长圳, 南山福田罗湖)
- Avoid "姐妹们" — 45岁中年男人视角
- Trigger nostalgia with specific food memories
- End with open question to drive comments

## Common Pitfalls

- **Fal.ai CDN delay**: Wait 60s before downloading Ideogram Character results
- **GPT Image 2 queue**: Can take 3-6 minutes per image on Crun.AI
- **MJ cref face mismatch**: Not reliable for real person photos — use Fal Ideogram instead
- **SiliconFlow FLUX**: Disabled on China site, use international site for FLUX access
- **Worker result回写**: Module results may appear empty in task_queue if dispatcher returns `success: False`; check worker logs
