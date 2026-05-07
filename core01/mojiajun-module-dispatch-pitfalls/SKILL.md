---
name: mojiajun-module-dispatch-pitfalls
description: 墨家军module_dispatcher两大隐藏Bug——dispatch参数提取导致函数收空参、module dispatch提前return跳过hook。每次新增模块或修改agent_worker必须自查。
version: 1.0.0
tags:
  - mojiajun
  - debugging
  - module-dispatcher
  - pitfalls
  - agent-worker
---

# 墨家军 Module Dispatch 两大隐藏Bug

## Bug 1：dispatch参数提取导致函数收空参

**位置**: `module_dispatcher.py` L195

**原代码**:
```python
func_args = payload.get("args", {}) if isinstance(payload, dict) else {}
```

**问题**: 如果payload是 `{"title":"...","body":"...","tags":[...]}`，`payload.get("args", {})` 返回 `{}`，函数收到**所有参数为空**。

**症状**: 函数正常运行但结果全错（比如审核函数红线词命中为空，但直接import调用却正常）。

**修复**:
```python
func_args = payload.get("args", payload) if isinstance(payload, dict) else {}
```

**教训**: 每次新增模块函数时，确认payload结构。如果不用 `args` 包装，确保dispatch能fallback。

---

## Bug 2：Module Dispatch 提前 return 跳过所有 Hook

**位置**: `agent_worker.py` L216-L217

**原代码**:
```python
update_progress(task_id, 100, "完成")
return result  # ← 提前返回！
```

**问题**: module dispatch成功后直接 `return result`，**所有后续代码都不执行**——包括审核回路hook、风格进化hook等。

**症状**: hook代码语法正确、逻辑正确、位置"看起来"正确，但从未触发。数据库有result，但hook没有日志输出。

**修复**: 在 `return result` 之前插入hook代码（L216-L217之间），不要在方法末尾放module dispatch相关hook。

**验证方法**: 
```bash
# 检查agent_worker.py中module dispatch的return位置
ssh ubuntu@159.75.12.11 "grep -n 'module_result.*return result\|update_progress.*100.*return result' agent_worker.py"
```

---

## 自查清单（每次修改agent_worker.py或新增模块后）

- [ ] **参数传递**: 新模块的payload是否包含 `args` 包装？还是没有就用fallback？
- [ ] **Hook位置**: 所有hook代码是在module dispatch的 `return result` 之前还是之后？
- [ ] **直接调用测试**: `from module_dispatcher import dispatch; dispatch(task_type, payload, agent)` 验证参数正确传递
- [ ] **端到端测试**: 实际入队一个任务，等worker执行完，检查result中的module_result是否符合预期
- [ ] **日志检查**: worker日志中是否有hook的输出（如"审核驳回→生成重写任务"）

---

## 历史记录

- 2026-04-27：两个bug在审核回路验证时同时暴露，耗时约30分钟排查。Bug1通过模拟hook逻辑脚本发现参数为空，Bug2通过搜索agent_worker.py中所有return result位置发现提前返回。
- 涉及模块：pre_publish_check、style_auditor、module_dispatcher、agent_worker
