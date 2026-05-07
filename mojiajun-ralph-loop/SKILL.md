---
name: mojiajun-ralph-loop
description: 墨家军 Ralph Loop — 验收达标检测+自动重试+熔断+依赖提升+Triage+Kanban+记忆系统增强
version: 2.1.0
tags:
  - mojiajun
  - ralph-loop
  - acceptance
  - circuit-breaker
  - kanban
  - memory
  - self-healing
---

# 墨家军 Ralph Loop

## 核心理念

> **AI Agent 不可靠，但足够的迭代可以让它变得可靠。**

```
Agent 执行 → 自动验证 → 不达标 → 自动分析错误 → 自动修正 → 重试 → 真达标才结束
                                                                      ↑
                                                              ┌──────────────┐
                                                              │ 连续N次失败   │
                                                              │ → 熔断，Blocked │
                                                              └──────────────┘
```

## 架构

| 组件 | 位置 | 作用 |
|------|------|------|
| `acceptance_validator.py` | CORE-01 | 验收引擎：12种运算符+完成标记检测+熔断 |
| `agent_worker.py` 多处hook | CORE-01 | Ralph验收+依赖提升+Triage推送 |
| `module_dispatcher.py` | CORE-01 | 自动过滤 _ralph_*/_rework_* 前缀参数 |
| `evolution_ralph_wrapper.py` | CORE-01 | 自进化5步骤包装器 |
| `dashboard.py + static/kanban.html` | CORE-01 | 6列Kanban看板 |
| `task_batcher.py` | 小川本地 | insert_task支持acceptance_criteria |

## 全部功能清单

### P0 — 验收引擎
- 12种运算符: eq, neq, gt, gte, lt, lte, in, not_in, contains, regex, exists, not_exists
- 完成标记检测: `<promise>DONE</promise>` 多种变体
- 熔断: 可配置max_attempts，超限自动停止
- worker挂钩: module dispatch成功后自动验收

### P1 — 上下文清零
- module_dispatcher自动过滤 _ralph_* / _rework_* 前缀参数
- agent_worker Ralph钩子防args嵌套: `payload.get("args", payload)` 取内层
- rework_context同时放顶层和args，未来LLM Agent可用

### P2 — 自进化循环Ralph化
- 5步骤验收标准: taste_filter / temp_insight_verify / sys_eval_report / forget_check / skill_trigger
- cron走包装器: 不达标自动重试

### K1 — 依赖自动提升
- 上游完成→下游 `deferred` 自动变 `pending`
- 工作原理: complete_task后UPDATE WHERE depends_on=刚完成的任务

### K2 — Triage状态
- 新任务默认 `triage`
- worker空闲时(每12个周期)自动推送 triage→pending
- 有验收标准的优先推送

### K3 — 6列Kanban看板
- 地址: `http://159.75.12.11:9600/kanban`
- 6列: 📥Triage → 📋Pending → ⚙️Processing → ✅Done
- 特殊列: 🔗Deferred(等依赖) / ❌Failed / 🛑Blocked(熔断)
- 10秒自动刷新
- 每个任务卡片: Agent、类型、验收标记✓、重试次数↻、存活时间、依赖链

## 使用方式

### 派发带验收标准的任务
```python
from task_batcher import insert_task
insert_task(
    target_agent="molan",
    task_type="xiaohongshu_note",
    payload={"topic": "景德镇冷粉"},
    acceptance_criteria={
        "rules": [
            {"field": "title_switches", "op": "gte", "value": 2},
            {"field": "redline_hits", "op": "eq", "value": 0},
        ],
        "require_marker": True,
        "completion_marker": "DONE",
        "max_attempts": 5,
    }
)
```

### 验收标准格式
```json
{
  "rules": [
    {"field": "字段路径(支持点号)", "op": "运算符", "value": "期望值", "desc": "描述"}
  ],
  "require_marker": true,
  "completion_marker": "DONE",
  "max_attempts": 5
}
```

## 常见坑

### JSON双重编码
向MySQL JSON列写入时，**不要** `json.dumps()`:
```python
# ❌ 错误: _ac_json = json.dumps(_ac)
# ✅ 正确: _ac_json = _ac  # 直接传dict
```

### args嵌套
重试任务payload的args会嵌套。正确取法:
```python
_src = payload.get("args", payload) if isinstance(payload.get("args"), dict) else payload
```

### SSH下的MySQL命令
避免内联SQL的转义地狱。用 `scp` + `.sql` 文件:
```bash
scp query.sql server:/tmp/
ssh server 'mysql DB < /tmp/query.sql'
```

### status ENUM扩展
如需新状态值，先ALTER TABLE:
```sql
ALTER TABLE task_queue MODIFY status 
  enum('triage','pending','processing','deferred','completed','failed','blocked') 
  DEFAULT 'triage';
```

## agent_worker.py hook注入点

| 注入位置 | Hook | 作用 |
|---------|------|------|
| execute_task: module dispatch成功后 | Ralph验收 | 自动验收+生成重试任务 |
| run(): complete_task后 | 依赖提升 | 上游完成→下游pending |
| run(): 空闲循环(%12) | Triage推送 | triage→pending |

## 部署文件

| 文件 | CORE-01路径 |
|------|------------|
| agent_worker.py | /home/ubuntu/mojiajun-queue/agent_worker.py |
| acceptance_validator.py | /home/ubuntu/mojiajun-queue/acceptance_validator.py |
| module_dispatcher.py | /home/ubuntu/mojiajun-queue/module_dispatcher.py |
| evolution_ralph_wrapper.py | /home/ubuntu/mojiajun-queue/evolution_ralph_wrapper.py |
| dashboard.py | /home/ubuntu/mojiajun-dashboard/dashboard.py |
| kanban.html | /home/ubuntu/mojiajun-dashboard/static/kanban.html |
