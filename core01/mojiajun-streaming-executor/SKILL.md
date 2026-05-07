---
name: mojiajun-streaming-executor
description: 墨家军并发工具执行器 — 六状态机+并发安全分类+级联取消+结果保序，借鉴Claude Code StreamingToolExecutor设计
version: 1.0.0
tags: [mojiajun, streaming-executor, concurrency, state-machine, cascade-cancel]
---

# 墨家军 StreamingToolExecutor 并发工具执行器

## 概述

借鉴 Claude Code StreamingToolExecutor。状态机驱动的多工具并发执行框架——安全工具并行、独占工具串行、失败级联取消、结果按提交顺序输出。

## 核心设计

### 1. 六状态机 (TaskState)

```
queued → executing → completed/failed/cancelled → yielded
```

追踪从入队到最终输出的完整状态转换。

### 2. 并发安全分类

| 类型 | 模块示例 | 并发方式 |
|------|---------|---------|
| 并发安全 | molan, moqing, kb_retriever | Semaphore并行 |
| 独占 | autodream, extract_memories, mysql_writer | asyncio.Lock串行 |

`_infer_safety()` 自动推断，默认乐观（并发安全）。

### 3. 级联取消

- Per-tool AbortController（含 threading.Event）
- SiblingGroup：任一工具失败 → `abort_all()` 取消同级
- 被取消task生成标准化synthetic error
- `cancel_all()` 支持全局取消

### 4. 结果保序

`execute_all()` 按 `add_task` 提交顺序 yield 结果，内部 `asyncio.gather` 并发但输出维持顺序。

### 5. 双执行模式

| 模式 | 机制 |
|------|------|
| executor_func | 自定义函数在 ThreadPoolExecutor 运行 |
| _execute_subprocess | subprocess 动态加载 agent_outputs 下的 run/main 函数 |

## 关键类/函数

| 类/函数 | 作用 |
|---------|------|
| `TaskState` | 枚举：queued/executing/completed/failed/cancelled/yielded |
| `AbortController` | Per-tool 取消控制 |
| `SiblingGroup` | 同级任务组管理 |
| `ConcurrentTaskExecutor` | 主执行器类 |
| `add_task()` | 添加任务 |
| `execute_all()` | 并发执行所有任务 |
| `cancel_all()` | 全局取消 |
| `run_tasks_concurrently()` | 便捷入口 |
| `run_tasks_sync()` | 同步入口 |

## 代码位置

CORE-01: `/home/ubuntu/mojiajun-queue/streaming_executor.py` (524行)
