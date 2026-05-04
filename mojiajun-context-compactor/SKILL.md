---
name: mojiajun-context-compactor
description: 墨家军上下文压缩系统 — 三种策略(autoCompact/sessionMemoryCompact/microCompact)+图片剥离+压缩后恢复，降token使用量
version: 1.0.0
tags: [mojiajun, context-compaction, token-saving, auto-compact, micro-compact]
---

# 墨家军 context_compactor 上下文压缩

## 概述

借鉴 Claude Code compact。三种压缩策略降低对话token使用量，支持图片/附件剥离和压缩后关键信息恢复。

## 三种压缩策略

| 策略 | 触发条件 | 机制 |
|------|----------|------|
| **autoCompact** | token超过80%阈值 | 旧消息发DeepSeek生成摘要，保留最近N条 |
| **sessionMemoryCompact** | 按API轮次分组 | 保留最近N轮，旧轮次压缩为会话记忆 |
| **microCompact** | 每次API调用后 | LRU缓存去重，重复内容替换为 `[cached: N chars]` |

## 压缩前剥离

- 图片 → `[image]` 占位符（支持多模态数组+base64 URI）
- 超大附件 → 截断为200字符预览+大小标注

## 压缩后恢复 (Post-Compact Restore)

| 恢复类型 | 机制 |
|----------|------|
| 关键文件 | 恢复最多5个高相关性文件 |
| 技能描述 | 恢复加载的技能 |
| 执行计划 | 恢复当前计划 |

## Token估算

- 字符串: `len/3+1`
- 图片: 85 tokens
- 列表/字典: 递归累加
- 每条消息: +4固定开销

## 关键类/函数

| 类/函数 | 作用 |
|---------|------|
| `ContextCompactor` | 主类，封装所有策略 |
| `ContextCompactor.compact()` | 主入口 |
| `ContextCompactor.should_compact()` | 阈值判断 |
| `CompactResult` | 数据类(success/strategy/tokens/messages/summary) |
| `MicroCompactCache` | LRU缓存(容量20) |
| `estimate_tokens()` | Token递归估算 |
| `strip_images_from_messages()` | 图片剥离 |
| `auto_compact_messages()` | 便捷入口 |

## 代码位置

CORE-01: `/home/ubuntu/mojiajun-queue/context_compactor.py` (419行)
