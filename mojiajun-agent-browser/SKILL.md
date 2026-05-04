---
name: mojiajun-agent-browser
description: 墨家军 agent-browser 工具 — 基于 Vercel agent-browser CLI 的浏览器自动化模块，为 AI Agent 提供网页交互能力（快照/点击/填充/截图/语义查找）。Mac本地已可用，CORE-01待装Chrome。
version: 1.0.0
tags:
  - mojiajun
  - browser
  - automation
  - agent-browser
  - tool
---

# 墨家军 agent-browser 工具

## 概述

集成 Vercel Labs 的 [agent-browser](https://github.com/vercel-labs/agent-browser)（30.7k star），为墨家军提供浏览器自动化能力。

**核心能力**：
- 快照：页面可访问性树（带 ref ID），AI 友好
- 语义查找：`find role button click --name "提交"`
- 交互：click/fill/type/scroll/press
- 截图：支持全页+标注
- 网络拦截、Cookie 管理

## 架构

```
墨家军 task_queue → module_dispatcher → mojiajun_agent_browser.py
                                              ↓
                                    agent-browser CLI (Rust)
                                              ↓
                                    Chrome CDP (headless)
```

## 当前状态

| 环境 | 状态 | 说明 |
|------|------|------|
| Mac 本地 | ✅ 可用 | brew install agent-browser，模块路径 `05_模块代码/小川本地/` |
| CORE-01 | ✅ 已激活 (2026-04-27) | agent-browser CLI 已装，Chrome 指向 Playwright Chromium，`--no-sandbox` 已配 |

## 已注册的 task_type

```
agent_browser_open       → mocheng/mojiajun_agent_browser.py → entry(action="open")
agent_browser_snapshot    → mocheng/mojiajun_agent_browser.py → entry(action="snapshot")
agent_browser_screenshot  → mocheng/mojiajun_agent_browser.py → entry(action="screenshot")
agent_browser_click       → mocheng/mojiajun_agent_browser.py → entry(action="click")
agent_browser_fill        → mocheng/mojiajun_agent_browser.py → entry(action="fill")
agent_browser_extract     → mocheng/mojiajun_agent_browser.py → entry(action="get_text")
```

## 使用示例（Mac本地）

```python
from mojiajun_agent_browser import open_page, snapshot, screenshot, close_browser

open_page("https://example.com")
snap = snapshot()  # 获取带 ref ID 的页面结构
screenshot("/tmp/page.png")
close_browser()
```

## CORE-01 部署步骤

**Chrome ✅ 已有**：`/home/ubuntu/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome`（Crawl4AI 留下的 Playwright Chromium）

只需装 agent-browser CLI：
```bash
# 1. 确保 Node.js >= 18
node -v

# 2. 安装 agent-browser
npm install -g agent-browser

# 3. 配置 Chromium 路径
echo 'export AGENT_BROWSER_EXECUTABLE_PATH=/home/ubuntu/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome' >> ~/.bashrc
source ~/.bashrc

# 4. 验证
agent-browser open https://example.com && agent-browser get title
```

## 模块文件位置

- Mac 本地：`墨家军资料库/05_模块代码/小川本地/mojiajun_agent_browser.py`
- CORE-01：`/home/ubuntu/mojiajun-queue/agent_outputs/mocheng/mojiajun_agent_browser.py`

## daemon 注意事项

agent-browser 使用 daemon 模式：
- 首次 `open` 启动后台守护进程
- 后续命令连接到同一 daemon
- Python 调用时需用 `_ensure_daemon()` 检测/启动（`start_new_session=True` 分离进程）
- 结束用 `close` 或 `close --all`

**重要**：daemon 残留会导致新参数（如 `--args`）被忽略，提示 `--args ignored: daemon already running`。
每次采集前必须先 `agent-browser close --all` 清理，再 `open` 带参数重新启动。

## 依赖

- agent-browser CLI (brew/npm/cargo)
- Chrome/Chromium（`--executable-path` 或 `AGENT_BROWSER_EXECUTABLE_PATH` 环境变量）

## CORE-01 已配置速查 (2026-04-27)

| 项目 | 值 |
|------|-----|
| agent-browser | `/usr/bin/agent-browser` (npm -g) |
| Chrome | `/home/ubuntu/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome` |
| bashrc | `AGENT_BROWSER_EXECUTABLE_PATH` + `AGENT_BROWSER_ARGS="--no-sandbox,--disable-gpu"` |
| 采集脚本 | `/home/ubuntu/mojiajun-queue/agent_browser_collect.py` |
| 采集产出 | `/home/ubuntu/mojiajun-queue/agent_browser_collections/` |

## 踩坑记录

### 1. `--args` 必须用逗号分隔（不是空格）
```bash
# ❌ 错误——空格分隔不生效，Chrome 依然报 sandbox 错误
agent-browser open URL --args "--no-sandbox --disable-gpu"

# ✅ 正确——逗号分隔
agent-browser open URL --args "--no-sandbox,--disable-gpu"

# ✅ 或用环境变量
export AGENT_BROWSER_ARGS="--no-sandbox,--disable-gpu"
```
help 文档明确写了 `e.g., --args "--no-sandbox,--disable-blink-features=AutomationControlled"`，容易忽略。

### 2. `--no-sandbox` 在服务器/VPS 环境基本必加
报错：`FATAL: No usable sandbox!`。服务器无桌面环境，必须 `--no-sandbox` + `--disable-gpu`。

### 3. 小心 `pkill -f chrome` 炸 SSH
SSH 命令字符串里如果包含 "chrome"（如指定 executable path），`pkill -f chrome` 会杀掉 SSH 自身。用 `ps aux | grep | awk` 精确匹配 PID。

### 4. Python 模块需注入 `AGENT_BROWSER_ARGS`
worker 进程不 source bashrc，必须在 `entry()` 的 env dict 中显式设置 `AGENT_BROWSER_ARGS`，否则 agent-browser 调用不带 `--no-sandbox`。
