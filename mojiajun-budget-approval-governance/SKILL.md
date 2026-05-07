---
name: mojiajun-budget-approval-governance
description: 墨家军预算熔断+审批门——每个Agent月度预算上限，80%预警/100%阻断，发布类任务须大威审批。借鉴Paperclip的治理模式。Web界面 http://159.75.12.11:9600/governance
category: mojiajun
tags: [governance, budget, approval, paperclip, agent-management]
created: 2026-05-06
author: 小川
---

# 墨家军治理系统（预算熔断 + 审批门）

## 一句话
Agent花超了自动停，发布前必须大威点头。

## 预算熔断

### 规则
| 花费 | 行为 |
|------|------|
| < 80% | ✅ 正常派发 |
| 80-99% | ⚠️ 预警，仍放行 |
| ≥ 100% | 🔒 熔断，拒绝新任务 |
| 每月1号 | 自动重置 |

### 使用
```python
from agent_outputs.mozi.governance import check_budget, record_cost

# 派发前检查
ok, reason = check_budget("molan")
if not ok: return {"error": reason}

# 任务完成后记录
record_cost("molan", 0.02, task_id="xxx")
```

### 调整预算
```python
from agent_outputs.mozi.governance import set_budget
set_budget("molan", 100.0)  # 月预算改为100元
```

## 审批门

### 需审批的任务类型
- `content_publish` — 发布笔记
- `comic_publish` — 发布漫画
- `external_deploy` — 外部部署

### 使用
```python
from agent_outputs.mozi.governance import needs_approval, submit_for_approval, approve_task

# 检查+提交
if needs_approval("content_publish"):
    submit_for_approval(task_id, "content_publish", "molan", title="标题", summary="摘要")
    # task_queue状态自动变为blocked

# 大威审批
approve_task(task_id, approved_by="dawei")  # 通过→恢复pending
reject_task(task_id, reason="这篇太营销了")  # 拒绝→failed
```

## 综合治理检查 `pre_dispatch_check()`
```python
from agent_outputs.mozi.governance import pre_dispatch_check

r = pre_dispatch_check("molan", "content_publish", "task_001", {"title": "新笔记"})
# {
#   "allowed": False,
#   "blocked_by": "approval",        # 或 "budget"
#   "block_reason": "等待大威审批",
#   "needs_approval": True,
#   "approval_id": 3
# }
```

## Web界面
http://159.75.12.11:9600/governance

两个Tab：
- 💰 预算熔断 — 8个Agent实时花费进度条+状态
- ✅ 审批门 — 待审批列表，一键通过/拒绝

## 数据库表
- `agent_budgets` — 预算配置+实时花费
- `approval_queue` — 审批队列
- `approval_rules` — 审批规则

## 部署
- 模块: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/governance.py`
- module_dispatcher: `governance → mozi/governance.main()`
- 8个Agent默认月预算 ¥50/月
