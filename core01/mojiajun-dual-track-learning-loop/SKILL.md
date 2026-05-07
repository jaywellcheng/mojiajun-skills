---
name: mojiajun-dual-track-learning-loop
description: 墨家军双轨学习闭环架构——"术(爆款数据)+道(200本书)"的完整设计、实现和部署方案
tags:
  - mojiajun
  - learning-loop
  - dual-track
  - knowledge-engine
  - insight-engine
  - agent-system-architecture
---

# 墨家军双轨学习闭环

## 核心概念

墨家军不是"套模板出内容"的Agent平台。它的核心竞争力在于**双轨学习闭环**：

```
轨道A — 爆款数据（术）："现在什么能火"
轨道B — 200本书（道）："为什么人类会这样反应"

术会变（小红书算法、热点迁移），
道相对稳定（影响力/心流/定位等底层理论不会过时）。
双轨融合 = 独一份的竞争力。
```

## 三大断层（为什么之前学习闭环不成立）

### 断层1：数据→知识的转化是单向的
- 小墨采集 → 库 → 墨渊分析 → analysis_reports表（没人读）
- ❌ 分析结果存起来就完了，其他Agent从不读

### 断层2：墨蓝写笔记不参考爆款数据
- 只搜索书本知识库（关键词"慢生活""心流"），跟小红书爆款不搭边
- 知识库232条是运维笔记+书籍摘要，即使搜到也不是爆款洞察

### 断层3：墨青出图不看内容类型
- 写攻略还是写产品，封面风格没有差异化
- 所有笔记用的封面方案相同

## 改造内容

### 新增模块（3核1调）

| 模块 | 路径 | 功能 |
|------|------|------|
| 爆款洞察引擎 | `agent_outputs/moyuan/xhs_insight_engine.py` | 从analysis_reports提炼标题公式、风格指南、爆款样本 |
| 书籍知识引擎 | `agent_outputs/mocheng_knowledge/engine.py` | 7个场景包，跨书交叉提炼观点+金句 |
| 双轨调度器 | `dual_learning_cycle.py` | 一次循环跑完术+道，产出融合指导 |

### 注册的task_type（module_dispatcher）

```python
# --- 学习闭环v2模块 ---
"v2_insight":       ("moyuan",   "xhs_insight_engine",      "build_creation_context"),
"v2_story_note":    ("molang_v2","engine",                  "create"),
"v2_cover_plan":    ("moqing_v2","engine",                  "create"),
"v2_learning_cycle":("moyuan",   "learning_cycle",          "run_learning_cycle"),
# --- 双轨学习循环 ---
"dual_cycle":      ("moyuan",   "dual_learning_cycle",   "dual_learning_cycle"),
"book_insight":    ("mocheng_knowledge","engine",        "display_scene_knowledge"),
"book_match":      ("mocheng_knowledge","engine",        "match_scene"),
```

### Agent Worker增强

在 `agent_worker.py` 中注入：

1. **进度反馈** — `update_progress()` 实时更新task_queue的progress/current_command/last_progress_update字段
2. **Token成本预警** — `estimate_task_cost()` 预估token消耗，阈值：≤2元自动、2-5元小川判断、≥5元报大威
3. **任务依赖** — `check_dependency()` 检查payload.depends_on字段，依赖未完成返回deferred
4. **成本记录** — task_queue新增cost_cny字段

### 补充17本书的核心观点

涉及的书籍：影响力、思考快与慢、心流、习惯的力量、定位、从0到1、精益创业、创新者的窘境、乌合之众、刻意练习、禅与摩托车维修艺术、原则、沉思录、道德经、失控、黑客与画家、奇点临近

每本书补了3-6条核心观点+3条金句，观点直接与天青浅运营场景对齐。

## 知识引擎场景包

7个应用场景，每个关联多本书交叉检索：

| 场景 | 关联书籍 | 应用 |
|------|---------|------|
| 小红书内容运营 | 影响力、心流、习惯的力量 | 写笔记时的方向指导 |
| 创业与品牌 | 定位、从0到1、精益创业 | 品牌定位、产品策略 |
| 用户心理与行为 | 思考快与慢、乌合之众、刻意练习 | 用户画像、决策机制 |
| 工艺与匠心 | 禅与摩托车维修艺术、心流 | 手作内容的价值支撑 |
| 人生与哲学 | 沉思录、道德经 | 人设内容的深度 |
| 效率与系统 | 原则、失控 | 墨家军架构设计 |
| 科技创新 | 黑客与画家、奇点临近 | 技术路线参考 |

## 使用方式

```bash
# 手动触发双轨学习循环
cd /home/ubuntu/mojiajun-queue && python3 dual_learning_cycle.py

# 查看学习日志
python3 learning_cycle.py progress

# 通过task_queue触发
# task_type: dual_cycle, target_agent: moyuan
```

## 真实反馈闭环（2026-04-26补上）

### 问题

learning_log只记录"已产出"，没有真实用户反馈数据。系统不知道产出的内容到底好不好。

### 解决方案

1. **note_feedback表** — 存储从后台导出的发布数据（曝光量、观看量、点赞、评论、收藏、分享、互动率）

```sql
CREATE TABLE note_feedback (
    id INT PRIMARY KEY AUTO_INCREMENT,
    note_title VARCHAR(255),
    publish_date DATE,
    check_date DATE,
    views INT DEFAULT 0,
    exposure INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    collects INT DEFAULT 0,
    shares INT DEFAULT 0,
    click_rate DECIMAL(5,3),
    engagement_rate DECIMAL(5,2),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

2. **feedback_tool.py** — 导入+分析工具，位于 `/home/ubuntu/mojiajun-queue/feedback_tool.py`

```bash
# 分析已有反馈数据
python3 feedback_tool.py analyze

# 同步到learning_log
python3 feedback_tool.py sync
```

3. **使用流程**: 大威发布笔记后3-7天导出数据 → 通过feedback_tool导入 → 系统分析"哪篇有效/为什么有效" → 下一轮循环优化

### Token成本预警阈值

在 agent_worker.py 中实现：

| 金额 | 决策者 | 说明 |
|:----|:------|:-----|
| ≤2元 | 自动执行 | 日常任务（笔记创作、分析、生图）都在此范围 |
| 2-5元 | 小川判断 | 高价值任务（双轨循环、全量分析）自动放行 |
| ≥5元 | 报大威审批 | 大额消耗由大威确认是否值得 |

### 墨蓝v2双轨洞察注入（2026-04-26改造）

在 `xiaohongshu_note.py` 的 `create()` 函数中注入双轨洞察：

```python
def create(**kwargs):
    topic = kwargs.get("topic", "") or kwargs.get("reference_title", "")
    if topic and _HAS_DUAL:
        ctx = build_creation_context(topic)
        if ctx.get("reference_titles"):
            kwargs.setdefault("_ref_titles", ctx["reference_titles"][:3])
        if ctx.get("title_formulas"):
            kwargs.setdefault("_ref_formulas", ctx["title_formulas"][:3])
        if ctx.get("style_guide"):
            kwargs.setdefault("visual_style", ctx["style_guide"]["default_style"])
    # ... 后续逻辑不变
```

效果：每次创作笔记时自动参考当前爆款标题公式和风格指南。

## 2026-04-27实操更新

### 核心知识库 vs 原始数据区分离

之前没有区分"原始数据"和"核心知识库"，现在严格分离：

```
原始数据区（小墨/Tavily/Agent随便写，标记"待审核"）
     ↓ 大威审核确认
核心知识库（所有Agent只读，只有大威/小川能写）
     ↓ 只读调用
所有Agent（墨蓝/墨青/墨红/墨子/墨创等）
```

**三张核心表**（ceramic_db库）：

| 表 | 用途 | 权限 |
|:---|:-----|:-----|
| core_knowledge_items | 书摘精华+双轨洞察+工艺知识 | Agent只读 |
| core_samples | 爆款样本数据 | Agent只读 |
| material_library | 旅游/时事/低粉等素材 | Agent可读（非核心） |

所有Agent通过task_queue执行任务时，应从核心库读取数据，不从原始区读。

### 每日审核流程

```
1. 原始数据自动入库 → 标记"pending"
2. 小川每日汇总审核清单（Markdown格式）
3. 大威逐条确认
4. 小川执行写入核心库
5. 入库日志记录到 core_library_log
```

审核清单模板位于 `墨家军产出文件/审核清单/` 目录。

### 数据来源

| 数据源 | 写入位置 | 入库规则 |
|:------|:--------|:---------|
| 小墨采集 | mojiajun.xhs_sample_library | 自动入库，标记待审核 |
| Tavily自采 | ceramic_db.xhs_sample_library | 自动入库，标记待审核 |
| 墨渊洞察 | 分析后写入 core_knowledge_items | 需大威确认 |
| 墨蓝产出 | 存本地JSON | 需大威确认后才入 core_samples |
| 墨红质检 | 入 stress_test_log / cross_validation_log | 自动入库（训练数据） |

### 双轨洞察分发现状

双轨洞察（标题公式+风格指南+心理开关+内容原则）通过以下方式分发到各Agent：

1. 墨渊分析 → 生成 `dual_insight.json`
2. 写入 core_knowledge_items（经大威确认后）
3. 各Agent的模块中读取核心库数据
4. 墨蓝的engine.py已接入DeepSeek API，调用时注入双轨洞察到system prompt

**墨蓝的engine.py关键改进**：
- 增加 `_call_deepseek()` 函数，从 `.env` 读取 DEEPSEEK_API_KEY
- `generate_story_note()` 在构建prompt时注入双轨洞察（标题公式+风格指南+心理开关）
- 出错时回退到context模式（只输出创作上下文，不生成正文）

### 墨蓝创作质量验证

2026-04-27完成72道工序科普笔记20遍压力测试：
- 成功率：20/20 (100%)
- 平均质量分：99/100
- 平均耗时：6.5秒/轮
- 平均正文长度：380字
- 20篇均带MJ Prompt

### 交叉验证流程

对核心库知识做质量校验：
1. 墨蓝针对知识内容出刁钻问题
2. 墨渊搜证回答
3. 核对程序判定「一致/部分矛盾/矛盾」
4. 不一致的标记待大威仲裁

2026-04-27抽测20条，发现主要问题是"提问/回答超出原文范围"而非知识错误。

## 已知问题（2026-04-27更新）

1. **反馈闭环不完整** — 同上，still待接入发布数据
2. **跨库查询** — 数据散落在ceramic_db和mojiajun两个库，Agent查询时需要指定库
3. **物料库独立性** — material_library目前只是存放素材，没有与创作流程自动关联
4. **知识入库依赖人工** — 大威确认环节是关键瓶颈，需将标准逐步规则化
5. **墨蓝写作风格控制** — 仍会偶尔出现煽情词（"破防""泪目"），需在prompt中持续强化约束

## 关键文件路径

```
/home/ubuntu/mojiajun-queue/
├── agent_worker.py                  # 改造后（进度反馈+Token预警+依赖检查）
├── dual_learning_cycle.py           # 双轨调度器
├── learning_cycle.py                # 学习循环调度器
├── module_dispatcher.py             # 注册了7个v2/dual/book task_type
├── HERMES.md                        # 项目上下文
├── agent_outputs/
│   ├── moyuan/
│   │   ├── xhs_insight_engine.py    # 爆款洞察引擎
│   │   └── analyze_new_data.py      # 新版分析器
│   ├── mocheng_knowledge/
│   │   └── engine.py                # 200本书知识引擎
│   ├── molang_v2/
│   │   └── engine.py                # 墨蓝v2创作引擎
│   └── moqing_v2/
│       └── engine.py                # 墨青v2封面引擎
```

## 数据流

```
小墨采集 → xhs_sample_library → 墨渊分析 → analysis_reports
                                        ↓
                              xhs_insight_engine(提炼标题公式+风格)
  +-------------------------------------+
  | 双轨融合:                           |
  | 术(哪类标题能火) + 道(为什么能火)      |
  +-------------------------------------+
  ↓                   ↓
墨蓝(笔记创作)      墨青(封面方案)
  ↓
learning_log(记录)
  ↓
下一轮循环(优化)
```

## 部署验证

```bash
# 测试双引擎加载
cd /home/ubuntu/mojiajun-queue && python3 -c '
import sys; sys.path.insert(0,"agent_outputs")
from moyuan.xhs_insight_engine import build_creation_context
from mocheng_knowledge.engine import KnowledgeSynthesizer
ctx = build_creation_context("景德镇")
ks = KnowledgeSynthesizer()
k = ks.get_scene_knowledge("小红书内容运营")
print(f"数据引擎: {len(ctx[\"title_formulas\"])}公式")
print(f"知识引擎: {k[\"books_found\"]}本书, {len(k.get(\"key_insights\",[]))}观点")
ks.close()
'

# 查看进度反馈
mysql -h127.0.0.1 -uxiaochuan -pxiaochuan_2026_mjj mojiajun -e "SELECT id, task_type, status, progress, cost_cny, LEFT(current_command,30) FROM task_queue ORDER BY id DESC LIMIT 5;"
```
