---
name: mojiajun-workflow-rework-loop
description: 墨家军内容审核回路——审核驳回自动回退重写，含3次熔断机制。CORE-01 agent_worker hook + 小川本地 task_batcher.dispatch_with_rework() 双端配合。
version: 1.1.0
tags:
  - mojiajun
  - workflow
  - review-loop
  - rework
  - circuit-breaker
---

# 墨家军内容审核回路

## 概述

解决"审核不通过只能人工打回"的痛点，实现自动回退→重写→再审核的闭环。

```
墨蓝创作(xiaohongshu_note) → 墨红审核(pre_publish_check)
                                  ├─ 通过 → 标记可发布
                                  └─ 驳回 → agent_worker hook 自动生成重写任务
                                            payload 带修改意见
                                            墨蓝重新创作
                                            ↓ 连续3次驳回
                                          熔断！人工介入
```

## 架构

| 组件 | 位置 | 作用 |
|------|------|------|
| agent_worker.py hook (L217) | CORE-01 | module dispatch成功后检测驳回→INSERT回退任务 |
| style_auditor.pre_publish_check() | CORE-01 | 单篇笔记发布前审核，返回 passed+feedback |
| task_batcher.dispatch_with_rework() | 小川本地 | 轮询检测整个创作+审核回路 |

## ⚠️ 注意：Ralph Loop 已取代此功能

审核回路已升级为通用Ralph Loop验收系统（`mojiajun-ralph-loop` v2.0）。

| | 旧审核回路 | 新Ralph Loop |
|---|---|---|
| 触发范围 | 仅审核类 | 所有task_type |
| 验收方式 | 人工pass/fail | 机器可验证的12种运算符 |
| 重试上限 | 固定3次 | 可配置max_attempts |
| 完成标记 | 无 | <promise>DONE</promise> |
| 上下文 | 累积 | 全新(参数过滤) |
| 看板 | 无 | 6列Kanban |

**请使用 `mojiajun-ralph-loop` 的 `acceptance_criteria` 替代旧的审核回路。**

agent_worker.py 的 execute_task 方法中，module dispatch 成功后会直接 `return result`（原L217），**跳过所有后续代码**。Hook 必须注入在 `return result` 之前（L216-L217之间），不能放在方法末尾。

2026-04-27曾因此bug导致hook从未触发，已修复。详见技能 `mojiajun-module-dispatch-pitfalls`。

## CORE-01 hook 逻辑

agent_worker.py L216-L217之间（module dispatch成功后、return之前）：

1. 检测 task_type 是否为 quality_audit 或 pre_publish_check
2. 从 result.module_result 提取 passed 标记
3. 如果驳回：
   - 提取 feedback/issues/suggestions 作为修改意见
   - 检查 retry_count：>=3 → 熔断告警，不再重试
   - <3 → INSERT 新任务到 task_queue (target_agent=molan, task_type=xiaohongshu_note)
   - 新任务的 payload 包含 rework_reason 和 original_task_id

## pre_publish_check 函数

位于 CORE-01: `/home/ubuntu/mojiajun-queue/agent_outputs/mohong/style_auditor.py`

审核维度：
- 红线词检查（虚假宣传、医疗暗示、极限词、平台敏感词）
- 基础质量（标题长度、正文字数、标签数量）
- 风格检查（真实感加分、营销腔减分、煽情腔减分）
- 综合评分 + passed/failed 判定

## 端到端验证方法

```bash
# 1. 插入测试审核任务（到CORE-01）
# 2. 等待worker执行
# 3. 检查重写任务是否自动生成
ssh ubuntu@159.75.12.11 'mysql -h 127.0.0.1 -u xiaochuan -p"xiaochuan_2026_mjj" mojiajun \
  -e "SELECT task_id, target_agent, task_type, status, LEFT(payload,120) FROM task_queue WHERE payload LIKE \"%驳回修改%\" ORDER BY created_at DESC LIMIT 3"'
```

## 部署恢复

Mac重建后：
1. 确保 CORE-01 agent_worker.py 含审核回路 hook（L216-L217之间）
2. 确保 style_auditor.py 含 pre_publish_check 函数
3. 恢复 task_batcher.py 到小川本地
4. `hermes skills install mojiajun-workflow-rework-loop`
