---
name: mojiajun-team-memory-sync
description: 墨家军团队记忆同步 — 本地Mac(小川)与CORE-01间知识文件双向同步，sha256增量+200KB分桶+密钥扫描+冲突重试
version: 1.0.0
tags: [mojiajun, team-memory-sync, rsync, sha256, knowledge-sync]
---

# 墨家军 teamMemorySync 团队记忆同步

## 概述

借鉴 Claude Code teamMemorySync。本地Mac（小川）与CORE-01服务器间知识文件双向增量同步。

## 核心设计

### 1. 同步机制（sha256增量）

| 方向 | 机制 |
|------|------|
| **Pull** | rsync --dry-run + --itemize-changes 检测变更 → 选择性同步 → 更新sha256映射 |
| **Push** | compute_delta() 对比 local vs server_checksums → 增量文件列表 → rsync上传 |

ETag和HTTP API预留但未实现，当前全部走SSH+rsync。

### 2. 冲突处理

- Push分桶时rsync失败 → 重试(MAX_RETRIES=2)
- 每次重试前先pull()拉取最新 → 重新compute_delta
- 只推送仍有差异的文件 → conflict_count递增

### 3. 批量策略

| 参数 | 值 |
|------|-----|
| BATCH_LIMIT | 200KB/桶 |
| FILE_LIMIT | 250KB（超大跳过） |
| MAX_ENTRIES | 10000 |

### 4. 安全扫描

上传前 scan_secrets() 匹配8类敏感信息：
API key / AWS AKIA / GitHub Token / Bearer Token / 私钥 / 数据库密码 / 明文密码 / JWT

发现密钥仅告警不阻止，支持 `--no-secret` 跳过。

### 5. 状态持久化

`sync_state.json` 记录: etag / checksums / server_checksums / last_sync_at / sync_count / conflict_count

## 关键函数

| 函数 | 作用 |
|------|------|
| `pull()` | 从CORE-01拉取 |
| `push()` | 推送到CORE-01 |
| `sync()` | 双向同步 |
| `compute_delta()` | 计算增量文件列表 |
| `bucket_files()` | 按200KB分桶 |
| `scan_secrets()` | 安全扫描 |
| `validate_knowledge()` | 知识完整性校验 |
| `show_status()` | 查看同步状态 |

## 两个版本

| 版本 | 文件 | 用途 | 大小 |
|------|------|------|------|
| **知识同步版** | CORE-01 `/home/ubuntu/mojiajun-queue/team_memory_sync.py` | knowledge/下.md文件双向同步，200KB分桶，密钥扫描 | 449行 |
| **容灾记忆版** | 本地Mac `~/.hermes/scripts/disaster_recovery_sync.py` | ~/.claude/ ↔ /home/ubuntu/.claude.server/ 记忆同步，SHA256增量+rsync，Last-Write-Wins冲突解决，排除credentials.json | ~260行 |

### 容灾记忆版 (disaster_recovery_sync.py) 特性

| 功能 | 实现 |
|------|------|
| 环境自动检测 | uname检测 → local_mac 或 core01，自动切换路径和SSH目标 |
| Pull | rsync --dry-run --itemize-changes 检测变更 → 执行rsync → 更新checksums |
| Push | compute_all_checksums → 对比remote_checksums → rsync增量推送 |
| Sync | 先pull再push，双向 |
| Force Sync | 接管前使用，跳过冲突检查，强制全量同步 |
| 冲突解决 | Last-Write-Wins（比mtime），旧版存conflicts/目录 |
| 安全排除 | credentials.json、.DS_Store、*.log自动跳过 |
| 状态持久化 | sync_state.json 记录checksums/sync_count/conflict_count/时间戳 |

CLI: `python3 disaster_recovery_sync.py {pull|push|sync|force|status}`

### 代码位置

知识同步版: CORE-01 `/home/ubuntu/mojiajun-queue/team_memory_sync.py` (449行)
容灾记忆版: 本地Mac `~/.hermes/scripts/disaster_recovery_sync.py` (~260行)，部署到CORE-01: `/home/ubuntu/scripts/disaster_recovery_sync.py`
