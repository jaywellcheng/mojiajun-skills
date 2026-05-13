---
name: mojiajun-workflow-dag-engine
description: 墨家军Workflow DAG引擎——支持分支/并行/条件路由的任务编排。含WorkflowDAG+环检测+ast白名单安全沙箱+Kanban桥接。
category: mojiajun
tags: [workflow, dag, orchestration, kanban, condition-evaluator]
---

# Workflow DAG 引擎

将墨家军任务系统从线性队列升级为有向无环图（DAG），支持分支、并行、条件路由。

## 架构

```
trigger_workflow("wf_id")
  └── WorkflowDAG(nodes, edges)          # 节点/边定义
        └── DAGExecutor.start()          # 初始化workflow_runs
              └── dag_to_tasks()         # ready节点→task_queue
                    └── agent_worker     # 执行任务
                          └── on_task_complete()  # 回调→激活下游
```

## 三个核心类（workflow_engine.py）

### WorkflowDAG
- `__init__(workflow_id, nodes, edges)` — nodes含id/task_type/agent/payload，edges含from/to/condition
- `_validate_no_cycles()` — DFS环检测，有环抛ValueError
- `get_ready_nodes(run_state)` — 返回依赖已满足的节点
- `topological_order()` — BFS拓扑排序
- `get_edge_condition(src, tgt)` — 获取条件表达式

### DAGExecutor
- `start()` → run_id — 初始化运行记录，激活无依赖节点
- `on_node_complete(run_id, node_id, result)` — 更新状态、评估条件边、激活下游
- 状态机: pending→ready→running→completed/failed/skipped
- 自动检测全部完成

### ConditionEvaluator（安全沙箱）
- `eval(expr, context)` — 求值条件表达式
- `$result.xxx` → `repr()` 内联为Python值（非`json.dumps`，避免`true`→`True`问题）
- `$status` → `repr()` 内联
- ast白名单：只允许 Compare/BoolOp/Name/Constant/Load
- 禁止 Call/Import/Attribute/Subscript → 抛ConditionSecurityError

## 条件求值关键坑：repr vs json.dumps

`$result.ok` 展开时必须用 `repr()` 而非 `json.dumps()`：

```python
# ❌ json.dumps → Python eval报错 NameError: name 'true' is not defined
json.dumps(True)  # → "true"

# ✅ repr → Python eval正确
repr(True)  # → "True"
repr("ok")  # → "'ok'"
```

## Kanban桥接（workflow_bridge.py）

三个对外函数：

| 函数 | 作用 |
|------|------|
| `trigger_workflow(workflow_id)` | DB加载定义→构造DAG→启动→返回run_id |
| `dag_to_tasks(dag, run_id)` | ready节点→INSERT task_queue（含target_agent字段） |
| `on_task_complete(run_id, node_id, result)` | worker回调→激活下游→新节点入列 |

## 文件位置

```
CORE-01:
  ~/mojiajun-queue/workflow_engine.py   (270行, 6/6测试通过)
  ~/mojiajun-queue/workflow_bridge.py   (220行, 端到端通过)

数据库:
  workflow_definitions (workflow_id, nodes JSON, edges JSON)
  workflow_runs (run_id, workflow_id, node_id, task_id, status, result)
```

## agent_worker hook

在task_memory hook后追加（agent_worker.py ~608行）：
```python
try:
    workflow_id = task.get("workflow_id")
    if workflow_id:
        from workflow_bridge import on_task_complete
        on_task_complete(workflow_id, task_type, result)
except Exception as e:
    logger.warning(f"[Workflow] hook failed: {e}")
```

## Spec/Plan/Tasks 文档

```
~/.hermes/specs/
  workflow-dag-2026-05-10-specify.md
  workflow-dag-2026-05-10-plan.md
  workflow-dag-2026-05-10-tasks.md
```

## 测试结果

```
✅ Test 1: topology OK
✅ Test 2: cycle detected: Cycle detected: B → A
✅ Test 3: ready nodes OK
✅ Test 4: condition eval OK
✅ Test 5: security sandbox OK
✅ Test 6: executor start+callback OK (A→B: ['B'])
🎉 All tests passed!
```
