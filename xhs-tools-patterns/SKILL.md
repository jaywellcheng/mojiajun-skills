---
name: xhs-tools-patterns
description: 小红书工具站通用模式：会话记忆、访问码保护、产品限价、Nginx API转发
---

# 工具站通用模式

## 聊天机器人会话记忆

问题：每轮对话独立，机器人反复问同一个问题。

解法：JSON文件存会话历史
- 前端生成 session_id：Math.random().toString(36).slice(2,10)
- 后端存 history 到 data/sessions/{id}.json
- 每次请求带最近10条发给DeepSeek
- 系统提示词改为分步推进，不重复提问
- 预算<2000 → 引导自助API，不收集联系方式

## 付费工具访问码保护

- 所有工具页加 ?key=opc2026tool 参数
- 无key或错key → 403
- 工具页不挂导航链接，付费后单独发URL
- 主页产品卡片无链接（非付费用户点了没反应）

## 产品限价展示

- 主页卡片内联显示使用限制：每日30次、限5个博主、不限次数
- 工具页header也显示用量
- 后端ratelimit.py：JSON文件按key+日期计数，每日重置

## Nginx API转发

- GW-01 Nginx location /api/xhs/ → CORE-01:8890/api/
- 转发时注入 X-API-Key header 解决认证问题
- 超时设90秒（DeepSeek分析慢）
- CORE-01 iptables需放行VPN网段
