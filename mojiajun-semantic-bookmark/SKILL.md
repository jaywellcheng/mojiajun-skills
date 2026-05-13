---
name: mojiajun-semantic-bookmark
description: 墨家军语义收藏夹 — URL→Crawl4AI抓全文→DeepSeek摘要+标签→MySQL→语义搜索，解决收藏吃灰
category: mojiajun
tags: [bookmark, semantic-search, crawl4ai, deepseek, collection]
created: 2026-04-29
updated: 2026-05-06
author: 小川
---

# 墨家军语义收藏夹

> 借鉴 Tabbit 的语义收藏理念：不存链接，存全文+AI摘要+标签，支持自然语言搜索。

## 核心能力
- **一键收藏**：粘贴URL → Crawl4AI抓全文 → DeepSeek自动摘要+打标签 → MySQL存储
- **语义搜索**：MySQL LIKE预筛 + 中文双字滑动窗口分词 + DeepSeek精排
- **Web搜索界面**：`http://159.75.12.11:9600/bookmarks`
- **支持去重**：URL hash防重复收藏

## 部署位置
- 模块: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/semantic_bookmark.py`
- Web: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/bookmarks.html`
- module_dispatcher: `"semantic_bookmark": ("mozi", "semantic_bookmark", "main")`

## 数据库表
- `semantic_bookmarks` — 收藏记录（url/hash/title/content/summary/tags/note）

## API
```
/api/bookmarks?action=add&url=...&note=...      # 收藏
/api/bookmarks?action=search&query=...&limit=15  # 搜索
/api/bookmarks?action=list&limit=20              # 最近收藏
/api/bookmarks?action=delete&id=...              # 删除
/api/bookmarks?action=stats                      # 统计
```

## 抓取优先级
1. Crawl4AI（完整渲染）→ 2. requests+html2text → 3. requests纯文本

## 中文搜索技巧
- 中文查询无空格时自动拆成双字bigram滑动窗口
- "AI代理框架" → 搜 ["AI代理框架", "AI", "I代", "代理", "理框", "框架"]
- 确保中文子串匹配

## 最新踩坑 (2026-05-06)
- Crawl4AI的Playwright浏览器在服务器上不可用 → catch所有异常，自动fallback到requests
- DeepSeek API Key需手动从.env加载（worker不自动加载env）
- MySQL密码用xiaochuan用户（不是root）
- port 9601被腾讯云安全组拦截 → 改为dashboard端口9600
- 收藏夹+技能市场+治理中心全部挂在9600端口的dashboard上，避免开新端口
