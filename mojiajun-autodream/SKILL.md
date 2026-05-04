---
name: mojiajun-autodream
description: 墨家军自主学习系统 — 借鉴Claude Code autoDream设计，四道门控(时间/节流/数据/互斥锁)，自动采集数据→AI分析→写入memdir知识库
version: 1.0.0
tags: [mojiajun, autodream, learning, memdir, self-evolution]
---

# 墨家军 autoDream 自主学习系统

## 概述

借鉴 Claude Code autoDream 设计。墨家军空闲时自动触发：采集近期数据 → DeepSeek AI分析 → 提炼洞察 → 写入memdir知识库。

## 四道门控（Cheapest First）

| 门 | 参数 | 成本 | 说明 |
|----|------|------|------|
| 时间门 | MIN_HOURS=6 | 近乎免费 | 距上次dream≥6小时 |
| 扫描节流 | SCAN_THROTTLE=10min | 极低 | 10分钟内不重复扫描 |
| 数据门 | MIN_NEW_ITEMS=5 | 需查MySQL+文件系统 | 至少5条新数据 |
| 互斥锁 | fcntl.flock | 文件锁 | 防止并发dream |

任意一道门关闭即跳过，按开销从低到高检查。

## Dream全流程（10步）

```
load_state → is_gate_open(四门) → collect_context(Python预采集)
→ build_dream_prompt → call_deepseek(API分析, temperature=0.3)
→ 解析 KNOWLEDGE:/UPDATE: 指令 → memdir_manager.py add 写入
→ memdir_manager.py rebuild 重建索引 → 更新state/cursor → release_lock
```

## 数据源

- MySQL: hotspot_data, daily_ai_news, xhs_sample_library
- 文件系统: knowledge/ 下各分类 .md 文件
- AI引擎: DeepSeek API (deepseek-chat)

## 触发方式

作为 agent_worker.py post-task hook 或 cron 调用

## 代码位置

CORE-01: `/home/ubuntu/mojiajun-queue/autodream.py` (458行)
