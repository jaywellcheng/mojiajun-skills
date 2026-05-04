---
name: mojiajun-learning-loop-orchestrator
description: 墨家军闭环调度器 — 检测knowledge更新后自动派发分析→创作→质检下游任务链，让Agent从"等任务"变"自己找活干"
version: 1.0.0
tags: [mojiajun, orchestrator, closed-loop, task-chain, auto-dispatch]
---

# 墨家军闭环调度器

## 核心价值

墨家军从"等任务"变成"自己找活干"。autoDream/extractMemories产出新知识后，自动触发下游Agent分析→创作→质检。

## 闭环链路

```
autoDream(每6h) / extractMemories(触发式)
        ↓ 产出新知识 → 更新 knowledge/INDEX.md
        ↓
闭环调度器(每30min)
        ↓ 检测到 INDEX.md mtime 变化 + 距上次派发≥30min
        ↓
  ① 墨渊 → analyze_new_knowledge → 深度分析新知识 (¥0.61)
  ② 墨蓝 → v2_story_note → 基于洞察创作笔记 (¥0.61)
  ③ 墨红 → quality_audit → 质检审计产出 (¥0.21)
        ↓ 总成本: ¥1.43/轮
   Agent Worker 自动抢单 → 执行 → 写回 result
```

## 节流控制

- 30分钟内不重复派发
- 只有 INDEX.md 真正变化了才触发
- 每次最多派3个任务

## 部署信息

- 代码: `/home/ubuntu/mojiajun-queue/learning_loop_orchestrator.py`
- 状态: `/home/ubuntu/mojiajun-queue/orchestrator_state.json`
- Cron: `*/30 * * * * cd /home/ubuntu/mojiajun-queue && python3 learning_loop_orchestrator.py >> /tmp/orchestrator.log 2>&1`

## 费用

- 每轮 ¥1.43（3个Agent任务）
- 自动触发频率取决于autoDream/extractMemories产出新知识的频率
- 预期每天1轮 = ¥1.43/天
