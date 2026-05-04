---
name: mojiajun-self-collection-full-loop
description: 墨家军自主采集全链路搭建与故障排查 — Tavily搜索→格式化→入库→分析闭环，不依赖小墨手动导入
category: mojiajun
---

# 墨家军自主采集全链路

## 概述

让墨家军自给自足，不依赖小墨手动采集和导入数据。通过Tavily搜索+collector模块完成自主采集→入库→可分析的全闭环。

## 架构

```
module_dispatcher → collector.execute() 
  → search_tavily(query) → 返回结构化items
  → save_to_xhs_library(items) → utf8mb4入库
  → 墨家军Agent读库分析 → 产出报告
```

## 采集任务定义（COLLECT_TASKS）— 2026-04-27更新为8个

在 `agent_outputs/collector.py` 中定义了8组任务（从5组扩展而来）：

| 任务ID | 名称 | sample_type | 关键词 |
|--------|------|-------------|--------|
| ceramic_hot | 陶瓷热点 | 陶瓷 | 景德镇陶瓷 手工 2026 / 景德镇 青花瓷 热门 / 景德镇 陶瓷 爆款 |
| ceramic_cup | 陶瓷杯/主人杯 | 陶瓷 | 手工陶瓷杯 主人杯 推荐 / 景德镇 茶杯 主人杯 手工 / 陶瓷杯 好物 分享 |
| sale_goods | 卖货好物 | 卖货 | 好物分享 杯子 家居 推荐 / 送礼 陶瓷 礼物 推荐 / 平价 好物 陶瓷 杯子 |
| low_fan_viral | 低粉爆款 | 低粉爆款 | 景德镇 手工 推荐 好物 平价 / 陶瓷 DIY 手工 体验 攻略 / 景德镇 小众 宝藏 店铺 |
| jingdezhen_travel | 景德镇旅游 | 热点 | 景德镇 旅游 攻略 2026 / 景德镇 陶瓷 体验 推荐 / 景德镇 周末 去哪玩 |
| china_ceramic_history | 中国陶瓷历史知识 | 知识 | 中国陶瓷史 青花瓷 起源 / 景德镇陶瓷 历史 工艺 传承 / 中国瓷器 发展史 名窑 种类 |
| jdz_ceramic_knowledge | 景德镇陶瓷知识 | 知识 | 景德镇 陶瓷 工艺 种类 介绍 / 景德镇 青花 粉彩 颜色釉 玲珑 / 景德镇 制瓷 工序 七十二道 |
| jdz_current_news | 景德镇时事消息 | 时事 | 景德镇 最新消息 2026 / 景德镇 陶瓷 新闻 动态 / 景德镇 活动 展览 市集 2026 |

## 部署步骤

### 1. 创建collector.py

放到 `/home/ubuntu/mojiajun-queue/agent_outputs/collector.py`

关键代码结构：
- `execute(params)` — 模块统一入口，被module_dispatcher调用
- `run_collect(task_ids=None)` — 执行全部或指定任务
- `search_tavily(query)` — 调用Tavily搜索
- `save_to_xhs_library(items, sample_type, keywords)` — utf8mb4入库，自动去重

### 2. 注册到module_dispatcher

在 `TASK_MODULE_MAP` 中增加：
```python
"mojiajun_collect": ("moqing", "collector", "execute"),
```

### 3. 确保TAVILY_API_KEY配置

写入 `/home/ubuntu/mojiajun-queue/.env`:
```
TAVILY_API_KEY=your_key_here
```

### 4. 重启Worker让配置生效

```bash
cd /home/ubuntu/mojiajun-queue
for pid in $(ps aux | grep agent_worker.py | grep -v grep | awk '{print $2}'); do kill "$pid"; done
sleep 2
for agent in mocheng mohong mojin molan moyuan mozi moqing mochuang; do
    nohup python3 -B agent_worker.py "$agent" > /dev/null 2>&1 &
done
```

## 调用方式

通过module_dispatcher直接调度（注意：payload参数必须包在args字段）：

```python
from module_dispatcher import dispatch
result = dispatch("mojiajun_collect", {"args": {"action": "run_all"}})
```

支持的action：
- `run_all` — 执行全部8组任务
- `run_tasks` — 执行指定任务，需传 `task_ids` 参数

## 已知坑和修复

### 坑1：数据分布跨两个数据库（关键！）
小墨采集的数据和墨家军自采的数据可能分布在两个不同的MySQL库中：

- **ceramic_db.xhs_sample_library** — collector模块写入的库，新采集数据在这
- **mojiajun.xhs_sample_library** — 小墨之前采集的历史数据可能在这（量更大）
- **mojiajun.xhs_explosive_notes** — 爆款笔记数据（可能有94+条）
- **mojiajun.hotspot_data** — 热点数据（可能有27+条）

**分析时必须两个库都查，否则数据量对不上！**

```bash
# 查ceramic_db
docker exec -i ceramic-mysql mysql -u root -pXXX --default-character-set=utf8mb4 ceramic_db -e "SELECT count(*) FROM xhs_sample_library;"

# 查mojiajun
docker exec -i ceramic-mysql mysql -u root -pXXX --default-character-set=utf8mb4 mojiajun -e "SELECT count(*) FROM xhs_sample_library;"
```

### 坑2：payload参数必须包在args里
dispatch的模式1从 `payload.get("args", {})` 取参数，直接传 `{"query": "..."}` 不会被解析。
**修复**: 传 `{"args": {"query": "..."}}`。

### 坑3：入库中文乱码
pymysql连接MySQL时如果charset没指定utf8mb4，中文会变成乱码。
**修复**: `pymysql.connect(charset="utf8mb4")` + 表字段用 `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`。

### 坑4：表结构不匹配
旧表可能缺少content/url/source/content_hash等字段，INSERT会报 `Unknown column`。
**修复**: 用 `INSERT IGNORE` + 只写存在的字段。如果缺字段，用ALTER TABLE加。

### 坑5：Tavily搜索函数参数名
tavily_search模块的search()接收的是 `query` 参数，不是 `keywords`。
**修复**: 调用时用 `search(query="...")`。

### 坑5：Docker exec查看中文乱码
`docker exec -i mysql` 默认字符集不是utf8mb4，显示中文会变成`????`。
**修复**: 加 `--default-character-set=utf8mb4` 参数。

### 坑6：CORE-01国内服务器无法下载Chrome
Crawl4AI需要浏览器，但国内服务器连不上Google和playwright源。
**修复**: 本地用VPN下载Chrome for Testing Linux版 → scp上传 → 解压到 `/usr/local/share/chrome-linux64/` → 设置 `CHROME_PATH` 环境变量。

### 坑7：macOS Downloads目录文件权限
scp读取 `/Users/xxx/Downloads/` 下的文件会被macOS安全机制拦截（Operation not permitted）。
**修复**: 让用户手动把文件从Downloads拖到桌面，再从桌面scp上传。

### 坑8：xhs_sample_library旧表缺content字段
小墨最早创建的表结构和collector模块的新版不一致，缺少content/url/source/content_hash等字段。
**修复**: 不要依赖content字段（旧表没有），写入时只写title/summary/url/source等已有字段。如果需要新增字段，用ALTER TABLE逐个加，注意旧表可能已有tags/note_id等字段。

### 坑9：Docker exec查看数据库中文乱码
`docker exec -i mysql` 默认字符集不是utf8mb4，显示中文会变成 `é™¶ç"·` 或 `????`。
**修复**: 加 `--default-character-set=utf8mb4` 参数。如果显示的sample_type是乱码但计数正常，说明数据本身是对的，只是显示问题。可以用 `LENGTH(sample_type)` 判断哪些行是正常中文（中文占3字节，正常分类如"陶瓷"长度为9，"卖货"长度为6）。

## 重要经验总结

### 经验1：采集工具 vs 真实爆款数据

Tavily搜索采集的是**通用网页结果**（新闻、电商、攻略），不是小红书/抖音的**真实爆款数据**。两者是互补关系：
- **Tavily自采** → 行业动态、知识科普、旅游攻略、时事新闻（适合作为创作素材储备）
- **小墨采集** → 小红书真实互动数据（点赞/收藏/评论），带情绪驱动和种草感（适合爆款规律分析）

**结论**：两者不能互相替代。墨家军自采负责日常知识储备，小墨采集负责爆款数据输入。

### 经验2：数据可能分布在两个MySQL库中

数据采集和入库要同时查两个库才能得到完整视图：

- **ceramic_db库** — collector模块写入的目标库
  - `xhs_sample_library`：Tavily自采数据（148条+）
  - `hot_list`：每日热点（44条）
  - `knowledge_items`：墨典知识库（313条）

- **mojiajun库** — 墨家军系统库
  - `xhs_sample_library`：小墨采集的带真实互动数据的样本（167条，有likes/collects/comments字段）
  - `xhs_explosive_notes`：爆款笔记（94条）
  - `hotspot_data`：热点数据（27条）
  - `knowledge_base`：知识库（232条）

两个库的xhs_sample_library表结构不同：mojiajun库有note_id/content/collects等字段，ceramic_db库有summary/url/source/content_hash等字段。

**分析时必须两个库都查，才能拿到完整的数据全貌。否则可能只看到1/3的数据量。**

### 经验3：小墨导入数据的编码问题

小墨通过自己方式导入的数据，如果编码不对会存成乱码（如 `é™¶ç"·` 代表"陶瓷"）。这类数据在MySQL里显示乱码但实际字节是正确的，加 `--default-character-set=utf8mb4` 可正常显示。

判断是否是乱码行的技巧：`SELECT id, LENGTH(sample_type) FROM xhs_sample_library`，正常"陶瓷"长度为9（utf8mb4下每个中文字3字节），乱码长度不同。

### 经验4：远程脚本调试技巧

SSH远程执行Python脚本时，**不要用 `-c` 参数内嵌代码**（引号嵌套、中文、反斜杠会让转义崩溃），也不要用heredoc。正确做法：

```bash
# 1. 本地写.py文件
# 2. scp上传到服务器
# 3. ssh执行
```

### 经验5：macOS文件权限限制

macOS限制Hermes读取 `/Users/xxx/Downloads/` 目录（Operation not permitted）。**修复**：让用户把文件拖到桌面后再操作。

## 验证测试

```bash
# 单独验证Tavily模块
python3 -c "
from agent_outputs.moqing.tavily_search import search
import json
res = search(query='景德镇陶瓷', max_results=3)
print(json.loads(res))
"

# 验证全链路采集
cd /home/ubuntu/mojiajun-queue
python3 -c "
from agent_outputs.collector import execute
import json
result = execute({'action': 'run_all'})
print(json.dumps(json.loads(result), ensure_ascii=False, indent=2))
"

# 验证入库数据
docker exec -i ceramic-mysql mysql -u root -pceramic_2026 --default-character-set=utf8mb4 ceramic_db -e "select sample_type, count(*) from xhs_sample_library where source='tavily' group by sample_type;"
```
