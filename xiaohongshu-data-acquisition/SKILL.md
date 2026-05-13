---
name: xiaohongshu-data-acquisition
description: 小红书数据采集全路径实测结论——什么能通、什么不通、推荐方案
category: mojiajun
tags: [xiaohongshu, scraping, data-collection, content-acquisition]
---

# 小红书数据采集全路径

## 一句话
经过实测对比，采集小红书真实笔记内容的最佳路径是 Coze官方插件 或 千瓜/新榜等付费平台，开源爬虫和直接API调用在当前鉴权机制下不可行。

## 已验证路径（按推荐度排序）

### 方式1：Coze扣子平台（推荐首选）
- Coze有小红书官方集成插件
- 可搜索、获取笔记详情、评论
- 走官方通道，稳定合法
- 小墨（墨家军云端Agent）在Coze上，直接可用

### 方式2：千瓜数据（付费，可靠）
- `qian-gua.com`
- 全维度小红书数据：笔记、达人、趋势
- 月费数千元起
- 适合规模化运营阶段

### 方式3：新榜（付费）
- `newrank.cn`
- 小红书蒲公英官方代理商
- 内容营销+数据分析

### 方式4：CORE-01采集管道（趋势分析用）
- Tavily搜索 → 只能搜到"关于小红书"的SEO文章，搜不到真实笔记
- Scrapling/Crawl4AI → 可抓网页，但小红书需登录Cookie
- 适用场景：竞品分析文章、行业报告（非小红书原生内容）

## 已证伪路径

| 路径 | 结果 | 原因 |
|------|------|------|
| 开源爬虫 (lorenzowne/xiaohongshu-scraper) | ❌ 空壳仓库 | 营销引流，无实际代码 |
| 开源爬虫 (Ramun-123/all-in-one-rednote) | ❌ 有代码但鉴权失败 | API返回500 "jarvis-gateway" |
| 直接调小红书API | ❌ | 需Cookie + X-s签名 |
| Tavily搜索小红书笔记 | ❌ | 只能搜到外部SEO文章 |
| 浏览器硬爬（无Cookie） | ❌ 确认不可行 | 即使CloakBrowser过反爬，搜索结果的`__INITIAL_STATE__`无笔记数据 |
| 浏览器硬爬（有Cookie） | ⚠️ 未实测 | 注入登录Cookie后可能可行，有封号风险 |

## 下一次该怎么做
1. 先问小墨（Coze Agent）能不能拉到数据
2. 如果Coze不通，评估千瓜/新榜的预算
3. 不要浪费时间试GitHub开源爬虫——小红书鉴权机制已全面升级

## 2026-05-09 CloakBrowser headless 实测
- CloakBrowser 能过反爬，搜索页面加载 663KB HTML，`__INITIAL_STATE__` 中有 `search.feeds` 等结构
- 但搜索结果通过**登录态 XHR 动态加载**，`__INITIAL_STATE__` 中 noteId 数量为 0，explore links 为 0
- **结论：即使过反爬，headless + 无 Cookie 拿不到任何笔记数据。** 登录 Cookie 是硬门槛。

## 2026-05-06 实测记录
- 尝试了两个GitHub爬虫仓库
- 直接调用 `web_api/sns/v1/search/notes` → 500
- Tavily搜索"小红书 爆款 职场女性" → 全是教程文
- 结论：外部采集不可行，走官方通道
