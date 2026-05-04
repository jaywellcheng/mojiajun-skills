---
name: mojiajun-extract-memories
description: 墨家军自动记忆提取系统 — Cursor增量机制+五级门控+Coalescing合流+主Agent互斥检测+安全沙箱，从MySQL提取新数据经DeepSeek分析后写入memdir
version: 1.0.0
tags: [mojiajun, extract-memories, memdir, cursor, coalescing]
---

# 墨家军 extractMemories 自动记忆提取

## 概述

借鉴 Claude Code extractMemories。从MySQL数据源增量提取新数据，通过DeepSeek AI分析提炼洞察，写入memdir知识库。

## 核心设计

### 1. Cursor增量机制
- 每个监控表维护 `created_at` 游标
- 只提取游标之后的新记录
- 游标持久化到 `extract_memories_state.json`
- 避免重复处理

### 2. 五级门控（Cheapest First）

| 门 | 参数 | 说明 |
|----|------|------|
| 节流门 | THROTTLE_EVERY_N=3 | 每3次触发执行1次 |
| 时间门 | MIN_MINUTES=15 | 距上次提取≥15分钟 |
| 扫描节流 | SCAN_THROTTLE=120s | 两次扫描间隔≥2分钟 |
| 数据门 | ≥3条新记录 | 所有表总计 |
| 互斥锁 | fcntl.flock | 防止并发提取 |

### 3. Coalescing合流
- 提取进行中时，新请求暂存 `pending_context`
- 下次提取时合并处理
- 30分钟过期丢弃

### 4. 主Agent互斥检测
- 写入memdir前检查其他Agent是否已写入
- 已写入则放弃，避免重复

### 5. 安全沙箱
- MySQL仅允许SELECT（拒绝INSERT/UPDATE/DELETE/DDL）
- 写入仅通过 `memdir_manager.py add` 代理

## 关键函数

| 函数 | 作用 |
|------|------|
| `load_state()` / `save_state()` | 持久化Cursor和元数据 |
| `check_gates()` | 五级门控检查 |
| `extract_new_rows()` | 从MySQL提取新行 |
| `call_deepseek()` | 调用DeepSeek分析 |
| `parse_knowledge_items()` | 解析KNOWLEDGE指令 |
| `write_to_memdir()` | 写入知识文件 |
| `execute_extract()` | 主流程：提取→合流→分析→解析→互斥检测→写入 |

## 使用方式

```bash
python3 extract_memories.py run     # 正常触发
python3 extract_memories.py force   # 强制触发(跳过部分门控)
python3 extract_memories.py status  # 查看状态
```

## 代码位置

CORE-01: `/home/ubuntu/mojiajun-queue/extract_memories.py` (544行)
