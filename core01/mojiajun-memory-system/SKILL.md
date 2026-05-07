---
name: mojiajun-memory-system
description: 墨家军记忆体系 — LCM四级压缩+DAG摘要+会话钩子+LLM-Map并行引擎。基于v4升级方案实现。
tags:
  - mojiajun
  - memory
  - lcm
  - dag
  - compression
  - session
version: 1.0.0
date: 2026-05-04
---

# 墨家军记忆体系

## 架构总览

```
活动上下文（行为纲领→规则→记忆→技能，四层分级加载）
    │
    ├── 软阈值8K / 硬阈值32K → 后台异步压缩
    │
    ▼
不可变存储（DAG摘要网络 + LLM-Map并行引擎 + 会话钩子）
```

## 模块清单

| 模块 | CORE-01路径 | 功能 | Phase |
|:---|:---|:---|:--|
| lcm_tools.py | `/home/ubuntu/mojiajun-queue/` | lcm_expand/describe/compact/explore | P1 |
| memory_truncate.py | `/home/ubuntu/mojiajun-queue/` | MEMORY.md 200行截断 | P1 |
| schema_validator.py | `/home/ubuntu/mojiajun-queue/` | Schema校验+微压缩(Level 0) | P1 |
| session_hooks.py | `/home/ubuntu/mojiajun-queue/` | 会话保存/加载/清理 | P2 |
| lcm_map.py | `/home/ubuntu/mojiajun-queue/` | 16路并行LLM处理引擎 | P2 |
| phase2_utils.py | `/home/ubuntu/mojiajun-queue/` | 四层分级+安全扫描+delegate校验 | P2 |

## 数据库表

| 表 | 库 | 用途 |
|:---|:---|:---|
| dag_nodes | ceramic_db | DAG摘要节点（四级压缩） |
| session_summaries | ceramic_db | 会话钩子持久化 |

## 行为纲领

| 文件 | 位置 |
|:---|:---|
| 墨蓝_program.md | Desktop + CORE-01 |
| 墨青_program.md | Desktop + CORE-01 |

## 调用示例

```bash
# LCM工具
python3 lcm_tools.py compact --tokens 100000
python3 lcm_tools.py expand <node_id>
python3 lcm_tools.py describe <node_id>
python3 lcm_tools.py explore large_file.json

# 会话钩子
python3 session_hooks.py save --project mojiajun --session xxx --summary "..."
python3 session_hooks.py load --project mojiajun

# LLM-Map
python3 lcm_map.py run --input data.jsonl --prompt "提取实体"

# 安全扫描
python3 phase2_utils.py scan
```

## 设计文档

| 文件 | 位置 |
|:---|:---|
| 墨家军记忆体系升级方案_v4.md | Desktop |
| 系统提示瘦身方案.md | Desktop |
