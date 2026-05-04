---
name: content-quality-cumulative-measurement
description: 小红书内容质量累积测量方法论——为什么不做实时A/B而做风格标签累积对比，以及评分公式设计（大威打分30%+数据自动分70%）
version: 1.0.0
tags:
  - mojiajun
  - content-quality
  - scoring
  - style-tagging
  - p2-5
  - p0-2
---

# 内容质量累积测量方法论

## 为什么不做实时A/B

原方案：每轮产2篇不同风格→同时发布→等数据→对比。三个硬伤：

| 问题 | 说明 |
|------|------|
| 同一账号发2篇同主题 | 像刷屏，用户体验差 |
| 样本量太小 | 1对1对比毫无统计意义 |
| 反馈周期太长 | 发布后等3-5天才闭环 |

## 替代方案：风格标签+累积对比

核心思路：每篇笔记打风格标签，积累10+篇后自然形成跨风格对比。

```
每轮Sprint一个 tone → 加 style_tag 字段打标
  → 积累5-10篇 → retro_report 按风格出对比报告
  → autodream 读对比数据 → 自动偏向高效风格
```

三层递进：
- L1: 风格标签+追踪（20分钟，立即可用）
- L2: 累积对比分析（30分钟，发5篇后见效）
- L3: 自动调优（20分钟，L2生效后）

## 风格自动打标

5种标签：搞笑调侃、实用攻略、情感共鸣、工艺故事、干货分享

4层启发式打标：
1. L1: tone 参数直接匹配
2. L2: 标题风格信号强（≥2个关键词）→标题优先
3. L3: 正文+标题联合关键词打分，score≥1.5阈值
4. L4: 兜底返回"实用攻略"

关键词库（按标签）：
- 搞笑调侃：搞笑、笑死、哈哈、段子、调侃、吐槽、离谱
- 实用攻略：攻略、步骤、教程、怎么、如何、指南、必看
- 情感共鸣：治愈、温暖、感动、想起、小时候、回忆、慢
- 工艺故事：师傅、手艺、制作、窑、烧、釉、泥、匠
- 干货分享：知识、科普、原理、解析、干货、技巧

## 内容质量评分公式

```
综合分 = 大威打分 × 0.3 + 数据均分 × 0.7
数据均分 = (标题分 + 正文分 + 配图分) / 3
```

| 维度 | 指标 | 阈值(分) |
|------|------|---------|
| 标题分 | 点击率=阅读/曝光 | <2%=1, 2-4%=2, 4-7%=3, 7-12%=4, ≥12%=5 |
| 正文分 | 互动率=(赞+评+藏+转)/阅读 | <1%=1, 1-2.5%=2, 2.5-5%=3, 5-10%=4, ≥10%=5 |
| 配图分 | 收藏率=收藏/阅读 | <0.5%=1, 0.5-1.5%=2, 1.5-3%=3, 3-6%=4, ≥6%=5 |

大威打分：每周导出真实数据后，手动给每篇打1-5分。

## 数据库表

content_quality_scores 关键字段：
- title_score, body_score, cover_score (TINYINT 1-5)
- owner_score (大威打分)
- data_avg, overall_score (DECIMAL)
- snapshot_* (6个原始数据快照，保证可复现)
- UNIQUE KEY uk_note_id (幂等)

## 数据闭环

```
笔记发布 → style_tagger 打标 → notes_published.style_tag
                    ↓
autodream ← retro_style_report 累积对比 ← note_feedback
    ↓
DeepSeek 分析 → tone推荐 → memdir
    ↓
内容发布 ← 大威每周导出数据打分 ← content_quality_scores
    ↓
autodream 读分数 → 分析瓶颈维度 → 自动调 prompt
```

## 代码位置

墨家军资料库/05_模块代码/
├── p2-5/  (风格标签+累积对比)
│   ├── migration_l1.sql
│   ├── style_tagger.py
│   ├── retro_style_report.py
│   ├── moyuan_style_patch.py
│   ├── autodream_style_enhance.py
│   └── tone_recommendation_template.md
└── p0-2/  (内容质量评分)
    ├── migration_p02.sql
    ├── score_calculator.py
    ├── retro_score_integration.py
    └── autodream_score_patch.py

## 关键决策记录

- **不做实时A/B**：样本量太小+同账号刷屏+反馈太慢
- **大威打分30%权重**：大威确认"每篇发布后以实际数据来打分，我的打分占3成"
- **阈值可配置**：TITLE/BODY/COVER_THRESHOLDS 用常量定义在文件顶部，大威可调整
- **数据快照**：snapshot_* 字段保存算分时的实时数据，后续数据变化不影响已算分
