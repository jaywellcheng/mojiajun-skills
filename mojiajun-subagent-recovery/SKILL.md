---
name: mojiajun-subagent-recovery
description: DeepSeek v4子进程中断后的接替流程——子进程因reasoning_content 400错误中断时，检查已有产出、接替继续、避免重复工作的标准方法
version: 1.0.0
---

# 子进程中断接替流程

## 场景

使用 delegate_task 派子进程时，DeepSeek v4-pro 的 reasoning_content 400 错误会导致子进程突然中断。此时：
- 子进程标记为 `failed` 或 `max_iterations`
- 但**工具调用已经执行了部分操作**（SSH命令已发送、文件可能已写入等）
- 直接重试会重复操作，浪费token

## 标准接替流程

### 1. 读工具trace（不要直接重试）

子进程返回的 tool_trace 记录了每一步操作。先看它做了什么：

```python
# tool_trace 字段：
# - tool: 工具名
# - args_bytes: 参数大小
# - result_bytes: 返回大小
# - status: ok/error
```

关键信息：
- 最后成功的操作是什么
- 哪个操作失败/超时了
- 有没有 error 状态的操作

### 2. 派新子进程接替（不是重试）

新子进程的 context 必须写明：
- **前任干到哪了**（从tool_trace推断）
- **当前服务器的实际状态需要先检查**
- **不要重复已有操作**
- **从断点继续**

```python
delegate_task(
    goal="接替中断的子进程，继续完成XXX",
    context="""
    上一个子进程已经完成了：
    - SSH到CORE-01成功
    - 执行了autodream.py（已运行）
    - 查询了task_queue（可能已有新数据）
    
    你需要：
    1. 先检查当前状态（不要假定前任的结果）
    2. 如果前任已经完成的操作——跳过
    3. 如果前任的操作结果不可用——重做
    4. 从断点继续
    """,
    toolsets=['terminal']
)
```

### 3. 接替子进程须知

| 规则 | 原因 |
|------|------|
| 先查状态再动手 | 前任可能已经把事干完了 |
| 不要假定"任务失败=没干活" | tool_trace显示11次调用已经执行了 |
| context写清楚断点 | 新子进程不知道前任做了什么 |
| 不要用相同的goal+context | 否则就是纯重试，浪费token |

## 实际案例

### 案例1：激活自主学习闭环（今天）

- 子进程1：11次工具调用后400错误，已运行autodream.py、修改时间门、查状态
- 接替子进程2：先检查autodream_state.json和task_queue → 发现autoDream已跑成#4 → 跳过重跑 → 直接派活给Agent → 3个任务被秒级认领

### 案例2：memory_api修复（今天）

- SSH heredoc中Python脚本执行+py_compile误在本地跑
- 解决：分离SSH命令和本地验证，用SSH远程执行py_compile而非本地

## 注意事项

- 400错误不可恢复（不要设重试），直接接替
- 子进程tool_trace是唯一的信息源，必须仔细读
- 接替比"重试"省钱——重试会重复所有已完成操作
