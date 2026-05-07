---
name: mojiajun-remote-bridge
description: 墨家军远程桥接 — 本地Mac(小川)↔CORE-01的SSH命令执行+文件传输+任务派发，双重保障(paramiko/subprocess)+指数退避重连
version: 1.0.0
tags: [mojiajun, remote-bridge, ssh, file-transfer, task-dispatch]
---

# 墨家军 remote_bridge 远程桥接

## 概述

本地Mac（小川）与 CORE-01 (159.75.12.11) 之间的命令执行、文件传输、任务派发基础设施。

## 连接机制

| 特性 | 实现 |
|------|------|
| 优先路径 | paramiko (Python SSH库) + SCPClient |
| 回退路径 | subprocess + 系统 ssh/scp 命令 |
| 重连策略 | 最多3次，指数退避 (2s → 4s → 8s) |
| 保活 | ServerAliveInterval=30s, ServerAliveCountMax=3 |

## RemoteBridge 类 6大能力

| 方法 | 功能 | 重试 |
|------|------|------|
| `execute(cmd, timeout)` | 远程执行命令 | 自动3次 |
| `deploy_file(local, remote)` | 推送文件/目录到CORE-01 | 自动3次 |
| `fetch_file(remote, local)` | 从CORE-01拉取文件/目录 | 自动3次 |
| `check_health()` | 健康检查：SSH + API状态(agents在线/任务总数) | — |
| `dispatch_task(type, payload)` | 三种派发：http(任务队列)/direct(直接执行)/mysql(写task_queue表) | — |
| `close()` | 资源释放，支持上下文管理器 | — |

## 任务派发三种模式

| 模式 | 说明 |
|------|------|
| **http** | 通过任务队列HTTP API派发 |
| **direct** | SSH直接执行 |
| **mysql** | 直接写 task_queue 表 |

## 便捷函数

```python
from remote_bridge import bridge_execute, bridge_deploy, bridge_fetch, bridge_health, bridge_dispatch

bridge_execute("ls -la /home/ubuntu/")
bridge_deploy("/local/file.py", "/remote/path/")
bridge_health()  # 返回SSH连通性+API状态
bridge_dispatch("http", {"task_type": "v2_story_note", "payload": {...}})
```

## 代码位置

CORE-01: `/home/ubuntu/mojiajun-queue/remote_bridge.py` (314行)
