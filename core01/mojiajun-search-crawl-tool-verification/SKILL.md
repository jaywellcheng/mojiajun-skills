---
name: mojiajun-search-crawl-tool-verification
description: 验证墨家军CORE-01服务器上搜索和爬虫工具的可用性，排查并修复常见问题（缺依赖、缺Key、网络限制等）
category: mojiajun
tags: [mojiajun, search, crawl, verification, troubleshooting, tool-health]
---

# 墨家军搜索/爬虫工具验证流程

## 背景

墨家军CORE-01服务器上有多个搜索和爬虫工具部署包，但实际可用性需要逐一验证。每个工具有各自的问题点：
- DuckDuckGo走Bing API，国内服务器被墙
- Tavily依赖API Key配置
- Scrapling依赖curl_cffi等动态库
- Crawl4AI依赖Playwright浏览器二进制文件

## 验证流程

### Step 1: 确认已安装的包

```bash
ssh ubuntu@159.75.12.11 'pip3 list 2>/dev/null | grep -iE "crawl|scrap|tavil|duck|selenium|playwr|beautif|request|httpx|aiohttp"'
```

### Step 2: 检查模块注册表

查看 module_dispatcher.py 中的 TASK_MODULE_MAP，确认哪些搜索/爬虫模块已注册：

```bash
ssh ubuntu@159.75.12.11 'cat /home/ubuntu/mojiajun-queue/module_dispatcher.py 2>/dev/null | grep -A2 "tavily|crawl|scrap"'
```

### Step 3: 逐个验证

#### 3a. 验证Tavily

先检查.env里有没有Key：

```bash
ssh ubuntu@159.75.12.11 'grep TAVILY_API_KEY /home/ubuntu/mojiajun-queue/.env'
```

如果没配，追加Key：

```bash
ssh ubuntu@159.75.12.11 'echo "TAVILY_API_KEY=你的key" >> /home/ubuntu/mojiajun-queue/.env'
```

验证搜索功能（注意参数名是`query`不是`keywords`）：

```bash
ssh ubuntu@159.75.12.11 'cd /home/ubuntu/mojiajun-queue && python3 -c "import os; os.environ[\"TAVILY_API_KEY\"]=open(\".env\").read(); from agent_outputs.moqing.tavily_search import search; print(search(query=\"test\", max_results=2))"'
```

#### 3b. 验证DuckDuckGo

如果报错 `DuckDuckGoSearchException` 且含 `bing.com` 域名 → 国内网络被墙，放弃此工具，用Tavily替代。

#### 3c. 验证Scrapling

```bash
ssh ubuntu@159.75.12.11 'python3 -c "from scrapling import Fetcher; f=Fetcher(); r=f.get(\"https://httpbin.org/html\",timeout=15); print(r.status)"'
```

常见错误：
- `ModuleNotFoundError: No module named 'curl_cffi'` → 装 `pip3 install curl_cffi --break-system-packages`
- `Fetcher` 用法在v0.3有更新，注意API文档

#### 3d. 验证Crawl4AI

```bash
# 先检查导入
ssh ubuntu@159.75.12.11 'python3 -c "from crawl4ai import AsyncWebCrawler; print(\"import OK\")"'

# 再检查浏览器
ssh ubuntu@159.75.12.11 'ls ~/.cache/ms-playwright/ 2>/dev/null || echo "无Playwright浏览器"'
```

常见错误：
- `Executable doesn't exist at ...` → 需要安装Playwright浏览器（~200MB），双线：`playwright install chromium` 或上传Chrome for Testing
- `ModuleNotFoundError: No module named 'nest_asyncio'` → 用单独的.py文件跑，不要用 -c 参数内嵌asyncio

### Step 4: 修复后重启Worker

修改.env后必须重启墨家军Worker才能生效：

```bash
ssh ubuntu@159.75.12.11 "cd /home/ubuntu/mojiajun-queue && for pid in \$(ps aux | grep 'agent_worker.py' | grep -v grep | awk '{print \$2}'); do kill \"\$pid\"; done && sleep 2 && for agent in mocheng mohong mojin molan moyuan mozi moqing mochuang; do nohup python3 -B agent_worker.py \"\$agent\" > /dev/null 2>&1 & done && sleep 2 && echo \"Worker数量: \$(ps aux | grep agent_worker | grep -v grep | wc -l)\""
```

预期输出：`Worker数量: 8`

### Step 5: 验证完整调用链路

确认墨家军Worker能通过module_dispatcher调用工具：

**重要：** 由于SSH命令引号嵌套容易出错（特别是Python脚本中含有f-string、中文和反斜杠），验证脚本应写成单独的文件用scp上传再执行，不要用 `-c` 内嵌或heredoc：

```bash
# 本地写脚本
cat > /tmp/verify_tool.py << 'PYEOF'
import sys, os, json
sys.path.insert(0, "/home/ubuntu/mojiajun-queue/agent_outputs/moqing")
with open("/home/ubuntu/mojiajun-queue/.env") as f:
    for line in f:
        if line.startswith("TAVILY_API_KEY"):
            os.environ["TAVILY_API_KEY"] = line.strip().split("=", 1)[1]
            break
from tavily_search import search
res = search(query="景德镇陶瓷", max_results=3)
data = json.loads(res)
print("成功:", data.get("success"))
print("条数:", data.get("result_count"))
PYEOF

# scp上传
scp /tmp/verify_tool.py ubuntu@159.75.12.11:/tmp/verify_tool.py

# 在服务器上执行
ssh ubuntu@159.75.12.11 'python3 /tmp/verify_tool.py'
```

## 已知问题速查

| 工具 | 典型错误 | 修复方法 |
|:----|:--------|:--------|
| DuckDuckGo | `DuckDuckGoSearchException: bing.com return None` | 国内服务器被墙，无法修复，用Tavily替代 |
| Tavily | `TAVILY_API_KEY 未配置` | 追加Key到.env并重启Worker |
| Tavily | `TypeError: search() got an unexpected keyword argument 'x'` | 参数名是 `query` 不是 `keywords` |
| Scrapling | `No module named 'curl_cffi'` | `pip3 install curl_cffi --break-system-packages` |
| Crawl4AI | `Executable doesn't exist` | 需要装Playwright浏览器或Chrome for Testing (~200MB)。注意：**国内服务器无法直接下载**（playwright源和Google CDN均被墙），需要用户在本地用VPN下载 Linux64 版的 chrome-linux64.zip 然后 scp 上传安装 |
| Crawl4AI | `ModuleNotFoundError` for asyncio | 用 `.py` 文件跑，不用 `-c` 内嵌 |

## 最终的可用组合（已验证 2026-04-27）

- ✅ **Tavily** → 搜索全网（热点、竞品、素材）— Key已配，Worker已重启
- ✅ **Scrapling** → 页面解析（CSS选择器提取内容）
- ⚠️ **Crawl4AI** → 抓渲染页面（需额外装浏览器）
- ❌ **DuckDuckGo** → 放弃（国内网络限制）
