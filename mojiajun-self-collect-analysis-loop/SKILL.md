---
name: mojiajun-self-collect-analysis-loop
description: 墨家军自主采集→入库→分析→产出 全链路搭建与修复实战指南。包含Tavily/Scrapling/Crawl4AI的工具修复、编码乱码解决、双库数据整合、采集任务模板、模块调度参数传递修复等。
---

# 墨家军自主采集→分析 全链路搭建与修复

## 适用场景
需要让墨家军Agent自主采集信息、格式化入库、分析产出的完整闭环。

## 核心要点

### 1. 搜索工具修复（2026-04-27实测）

| 工具 | 状态 | 修复方式 |
|:----|:----|:---------|
| **Tavily** | ✅ 国内可用 | 注册获取API Key，配置到CORE-01的.env文件，重启Worker |
| **Scrapling** | ✅ 国内可用 | `pip3 install curl_cffi --break-system-packages` 补依赖 |
| **Crawl4AI** | ✅ 需要Chrome | 下载Chrome for Testing Linux版→scp上传→解压到`/usr/local/share/chrome-linux64/`→`export CHROME_PATH=...` |
| **DuckDuckGo** | ❌ 被墙放弃 | 国内服务器连不上Bing API，用Tavily替代 |

**Crawl4AI浏览器安装关键点**：
- Google源和playwright源在中国服务器上下载失败
- 解决方案：本地（Mac）通过VPN下载chrome-linux64.zip → scp到服务器 → 解压到/usr/local/share/
- 路径配置：`export CHROME_PATH=/usr/local/share/chrome-linux64/chrome`
- 系统依赖：`libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxcb1 libxkbcommon0 libgbm1 libpango-1.0-0 libcairo2`等（新版Ubuntu包名有变，缺什么装什么）

### 2. MySQL入库编码坑

**乱码问题**：MySQL客户端（docker exec）默认连接编码不是utf8mb4，导致中文显示乱码。

**解决方案**：
```bash
# 连接时必须指定编码
docker exec -i ceramic-mysql mysql -u root -p密码 --default-character-set=utf8mb4 数据库名

# Python入库时charset必须指定utf8mb4
pymysql.connect(charset="utf8mb4")
```

**实际坑**：docker exec不加`--default-character-set=utf8mb4`时，终端的SELECT结果中文显示为问号或乱码。但库里实际数据是好的，用Python读出来正常。

### 3. module_dispatcher 参数传递

**关键发现**：dispatch的payload参数必须包在`args`字段里面。

```python
# ❌ 错误方式
dispatch("tavily_search", {"query": "关键词", "max_results": 5})

# ✅ 正确方式 - params必须套在args里
dispatch("tavily_search", {"args": {"query": "关键词", "max_results": 5}})
```

原因：module_dispatcher的`_load_and_exec`函数里，从payload取参数逻辑是：
```python
func_args = payload.get("args", {}) if isinstance(payload, dict) else {}
```

### 4. 采集模块架构

核心模块 `collector.py`（部署在 `agent_outputs/collector.py`）结构：

- **COLLECT_TASKS**：预定义的采集任务列表（每个任务含id/name/keywords/sample_type/max_results/priority）
- **search_tavily()**：调用Tavily搜索，返回格式化items
- **save_to_xhs_library()**：入库，自动去重（content_hash），utf8mb4编码
- **execute()**：统一入口，被module_dispatcher调度
- **run_collect()**：批量执行所有或指定任务

### 5. 双库数据整合

小墨采集的数据在mojiajun库，墨家军自采的数据在ceramic_db库。两个库都要查才能拿到完整数据。

**mojiajun库关键表**：
- xhs_sample_library（167条小墨采集的爆款样本，有likes/collects/comments真实互动数据）
- xhs_explosive_notes（94条爆款笔记）
- hotspot_data（27条热点数据）
- knowledge_base（232条知识库）

**ceramic_db库关键表**：
- xhs_sample_library（148条Tavily自采数据）
- hot_list（44条每日热点）
- knowledge_items（313条知识条目）

### 6. 去重策略

入库时用content_hash（SHA256(title+url)取前32位）做UNIQUE KEY，INSERT IGNORE自动去重。

## 任务调度模板

注册到module_dispatcher：
```python
"mojiajun_collect": ("moqing", "collector", "execute"),
```

调用示例：
```python
# 跑全部8个任务
{"action": "run_all"}

# 跑指定任务
{"action": "run_tasks", "task_ids": ["ceramic_hot", "jdz_current_news"]}
```

## 已验证的全链路

collection → search(Tavily) → format → save_to_mysql(utf8mb4,dedup) → dispatch_analysis → produce_report

## 采集任务完整清单（2026-04-27更新为8个）

| task_id | 名称 | sample_type | 关键词示例 | 优先级 |
|---------|------|-------------|-----------|:------:|
| ceramic_hot | 陶瓷热点 | 陶瓷 | 景德镇陶瓷 手工, 青花瓷 热门, 陶瓷 爆款 | P1 |
| ceramic_cup | 陶瓷杯/主人杯 | 陶瓷 | 手工陶瓷杯 主人杯 推荐, 茶杯 手工 | P2 |
| sale_goods | 卖货好物 | 卖货 | 好物分享 杯子 家居, 送礼 陶瓷 | P3 |
| low_fan_viral | 低粉爆款 | 低粉爆款 | 手工 推荐 好物 平价, DIY 体验 攻略 | P4 |
| jingdezhen_travel | 景德镇旅游 | 热点 | 旅游 攻略, 陶瓷 体验, 周末 去哪玩 | P5 |
| china_ceramic_history | 中国陶瓷历史知识 | 知识 | 陶瓷史 青花瓷 起源, 瓷器 发展史 名窑 | P6 |
| jdz_ceramic_knowledge | 景德镇陶瓷知识 | 知识 | 陶瓷 工艺 种类, 青花 粉彩 颜色釉 玲珑 | P7 |
| jdz_current_news | 景德镇时事消息 | 时事 | 最新消息, 陶瓷 新闻 动态, 活动 展览 市集 | P8 |

## 数据分布（截至2026-04-27）

**mojiajun库（小墨采集——爆款样本，有likes/collects/comments真实互动数据）**：
- xhs_sample_library: 167条（陶瓷类30+卖货60+景德镇30+手绘陶瓷15+青花瓷15+低粉爆款2+未分类15）
- xhs_explosive_notes: 94条
- hotspot_data: 27条
- knowledge_base: 232条
- daily_ai_news: 70条

**ceramic_db库（墨家军自采）**：
- xhs_sample_library: 148条（陶瓷30+卖货15+低粉爆款15+热点15+知识30+时事15+小墨旧数据28）
- hot_list: 44条
- knowledge_items: 313条

两个库的xhs_sample_library表结构不同，mojiajun库有likes/collects/comments真实互动数据，ceramic_db库的Tavily数据没有互动指标。

## 墨蓝v2引擎改造要点

engine.py的generate_story_note原版只输出"创作上下文"（选题、风格、标签），不生成笔记正文。

**改造方式**：加入DeepSeek API调用，真正生成标题+正文+MJ Prompt。

```python
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"

def _call_deepseek(system_prompt, user_prompt):
    import requests
    resp = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 4096
        },
        timeout=60
    )
```

**关键点**：
- 从.env读取DEEPSEEK_API_KEY（直接读文件，因为shell环境变量可能没加载）
- 输出期望笔记标题、正文、MJ Prompt、标签、心理开关
- AI失败时回退到上下文模式（不卡死）
- 笔记正文要求300-500字，真实生活感，45岁景德镇人口吻

## agent 角色文档管理

所有Agent的定位、状态、AB角替补方案已归档在：
- 墨家军产出文件/Agent角色定位与替补方案.md
- 墨家军产出文件/Agent真实能力摸底.md

这些文档要常翻、持续更新，不是写完就放着的。
