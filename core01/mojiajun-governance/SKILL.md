---
name: mojiajun-governance
description: 墨家军治理系统 — 预算熔断（Agent月度预算+自动阻断）+ 审批门（关键操作发布前须大威审批），含Web治理中心UI
category: mojiajun
tags: [governance, budget, approval, circuit-breaker, paperclip]
created: 2026-05-06
author: 小川
---

# 墨家军治理系统

> 借鉴 Paperclip 的预算控制 + 审批链理念，为墨家军8个Agent添加治理层。

## 核心能力

### 💰 预算熔断
- 每个Agent月度预算上限（默认¥50/月）
- 花费 ≥ 80% → 预警（仍放行）
- 花费 ≥ 100% → 自动熔断，拒绝新任务
- 每月1号自动重置
- Web看板实时显示每个Agent的进度条+状态

### ✅ 审批门
- content_publish / comic_publish / external_deploy → 必须审批
- auto_psd_layers / semantic_bookmark → 自动放行
- 审批通过 → 任务恢复pending执行
- 审批拒绝 → 任务标记failed
- Web界面一键通过/拒绝

### 派发前自动检查
`pre_dispatch_check(agent_id, task_type, task_id, payload)` 每次派任务前跑：
1. 查预算 → 超了直接block
2. 查审批 → 需审批的自动入队

## 部署位置
- 模块: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/governance.py`
- Web: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/governance.html`
- 访问: `http://159.75.12.11:9600/governance`
- API: `http://159.75.12.11:9600/api/governance?action=...`
- module_dispatcher: `"governance": ("mozi", "governance", "main")`

## 数据库表
- `agent_budgets` — 每Agent月度预算+实时花费
- `approval_queue` — 审批队列
- `approval_rules` — 哪些task_type需要审批

## API 操作

```
# 预算
/api/governance?action=budget_stats       # 所有Agent预算概览
/api/governance?action=budget_check&agent_id=molan  # 检查单个
/api/governance?action=budget_set&agent_id=molan&monthly_cny=100  # 调整预算
/api/governance?action=record_cost&agent_id=molan&cost_cny=0.5   # 记录花费

# 审批
/api/governance?action=pending_approvals   # 待审批列表
/api/governance?action=approve&task_id=xxx  # 通过
/api/governance?action=reject&task_id=xxx&reason=... # 拒绝
/api/governance?action=needs_approval&task_type=...  # 检查是否需要审批
/api/governance?action=approval_stats       # 审批统计

# 综合治理
/api/governance?action=pre_dispatch&agent_id=molan&task_type=content_publish&task_id=xxx&payload={...}
```

## 集成到task_queue派发流

在agent_worker派发前加一行：
```python
from agent_outputs.mozi.governance import pre_dispatch_check
check = pre_dispatch_check(agent_id, task_type, task_id, payload)
if not check["allowed"]:
    # 被预算或审批拦截，不派发
    return check
```

## 踩坑
- port 9601被腾讯云安全组拦截 → 合并到9600端口的dashboard避免开新端口
- 中文搜索分词用双字滑动窗口(bigram)，不依赖分词器
- Flask路由用send_from_directory serve静态HTML
