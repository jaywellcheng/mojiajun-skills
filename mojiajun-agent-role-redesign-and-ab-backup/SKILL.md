---
name: mojiajun-agent-role-redesign-and-ab-backup
description: >-
  墨家军8个Agent的重新定岗、角色职责矩阵和AB角替补机制。
  将闲置Agent融入双轨学习闭环，为核心Agent建立故障自动切换方案。
tags:
  - mojiajun
  - agent-architecture
  - high-availability
  - role-design
  - backup-mechanism
---

# 墨家军8个Agent重新定岗 + AB角替补方案

## 角色矩阵

| Agent | 角色 | 核心职责 | 状态 | 替补 |
|:------|:-----|:---------|:----:|:----:|
| 墨渊 (moyuan) | 数据科学家 | 分析采集数据、运行学习循环、维护洞察引擎 | ✅ 核心 | 墨橙 |
| 墨蓝 (molan) | 内容创作者 | 基于双轨洞察创作笔记、维护标题库 | ✅ 已接入DeepSeek API | 墨创 |
| 墨青 (moqing) | 视觉设计师 | 封面方案+图片生成、匹配风格指南 | ✅ v2封面方案 | 墨红 |
| 墨红 (mohong) | 质检员 | 产出质量审核、风格一致性、发布前把关 | ✅ 可审计Agent产出 | 墨子 |
| 墨子 (mozi) | 仪表盘 | 学习进度展示、报告可视化、趋势图 | ✅ 生成HTML看板 | 墨红 |
| 墨创 (mochuang) | 策略参谋 | 内容日历、系列策划、发布节奏管理 | ⚠️ 可产出但读库需切换 | 墨蓝 |
| 墨橙 (mocheng) | 反馈协调员 | 数据采集、外部数据同步、反馈录入 | ✅ | 墨渊 |
| 墨金 (mojin) | 创新引擎 | 新热点发现、兴趣缺口探查、反套路内容驱动 | ❌ 待启动 | 墨创 |

## AB角映射表（在module_dispatcher中使用）

```python
_BACKUP_MAP = {
    # 核心数据分析
    "sample_analysis":["moyuan","mocheng"],
    "data_analysis":  ["moyuan","mocheng"],
    "dual_cycle":     ["moyuan","mocheng"],
    
    # 内容创作
    "xiaohongshu_note":["molan","mochuang"],
    "v2_story_note":   ["molan","mochuang"],
    
    # 图片生成
    "image_generator": ["moqing","mohong"],
    "gen_image":       ["moqing","mohong"],
    
    # 审核
    "quality_audit":    ["mohong","mozi"],
    "pre_publish_check":["mohong","mozi"],
    
    # 策划
    "strategy_plan":   ["mochuang","molan"],
    "content_planner": ["mochuang","molan"],
    
    # 反馈
    "feedback_sync":   ["mocheng","moyuan"],
    "daily_summary":   ["mocheng","moyuan"],
    
    # 仪表盘
    "dashboard_report": ["mozi","mohong"],
    
    # 创新
    "trend_mining":    ["mojin","mochuang"],
    "topic_miner":     ["mojin","mochuang"],
}
```

## AB角逻辑实现（内嵌在dispatch函数中）

```python
# 在 dispatch() 函数体最前面
_cands = _BACKUP_MAP.get(task_type, None)
if _cands and target_agent and target_agent in _cands:
    _cands = [target_agent] + [c for c in _cands if c != target_agent]
if _cands:
    for _a in _cands:
        try:
            _ch = pymysql.connect(**DB)
            _cc = _ch.cursor()
            _cc.execute("SELECT last_heartbeat FROM agent_status WHERE agent_id=%s", (_a,))
            _rr = _cc.fetchone()
            _ch.close()
            if _rr and _rr[0]:
                _hs = _rr[0] if isinstance(_rr[0],str) else str(_rr[0])
                _idl = (datetime.now()-datetime.strptime(_hs[:19],"%Y-%m-%d %H:%M:%S")).total_seconds()/60
                if _idl < 5:
                    if _a != target_agent:
                        logger.info(f"AB角切换: {task_type} A角不可用，{_a}(B角)接管")
                        target_agent = _a
                    break
            else:
                break
        except:
            break
```

**原理**: 查agent_status表的last_heartbeat字段，超过5分钟无心跳的Agent视为宕机，自动切换到B角。

## regist_roles 注册方式

在 module_dispatcher.py 的 TASK_MODULE_MAP 中注册新角色的task_type：

```python
# --- Agent新角色注册 ---
"strategy_plan":   ("mochuang","content_planner",       "generate_calendar"),
"dashboard_report":("mozi",    "dashboard_generator",    "generate"),
"quality_audit":   ("mohong",  "style_auditor",          "audit_style"),
"pre_publish_check":("mohong", "style_auditor",          "pre_publish_check"),
"feedback_sync":   ("mocheng", "data_collector",         "sync_feedback"),
"daily_summary":   ("mocheng", "data_collector",         "daily_summary"),
"trend_mining":    ("mojin",   "topic_miner",            "mine_trends"),
"gap_analysis":    ("mojin",   "topic_miner",            "gap_analysis"),
```

## 宕机应急流程

1. 系统检测到A角Agent无心跳超过5分钟
2. dispatch()自动将对应task_type的任务派给B角
3. B角加载A角的模块（通过import动态加载）
4. 通知大威：XX Agent已切换为YY代管
5. A角恢复后，下次心跳更新自动切回

## 仪表盘改造

墨子(mozi)的dashboard_generator改造为展示：
- Agent活跃度（每个Agent近2日任务数）
- 学习日志（最近learning_log记录，标记已发布/未发布）
- 真实反馈数据（note_feedback表的内容）
- 任务趋势（按小时的计数）

```html
# 生成的仪表盘在:
/home/ubuntu/mojiajun-queue/agent_outputs/mozi/dashboard.html
```

## 踩坑记录

### 坑1：AB角代码的作用域问题

初始实现把 `_BACKUP_MAP` 定义在dispatch函数外部，但dispatch内部引用了全局变量 `resolve_agent` 函数，而该函数又引用了 `pymysql`——导致dispatch导入时报 `NameError`。

**解决方案**: 把 `_BACKUP_MAP` 定义为模块级常量，AB角检查逻辑完全内联到dispatch函数体中，不依赖外部函数：

```python
# 模块级（在TASK_MODULE_MAP之后）
_BACKUP_MAP = {"sample_analysis":["moyuan","mocheng"], ...}

# dispatch函数体内（第一行）
_cands = _BACKUP_MAP.get(task_type, None)
if _cands:
    for _a in _cands:
        # 心跳检查 ...
        if _a != target_agent:
            target_agent = _a
```

### 坑2：Agent Worker改造时的文件损坏

直接用 `sed` + 文件替换方式修改 `agent_worker.py` 时，由于转义字符和缩进问题，导致文件语法错误。恢复时 `.bak` 指向的是旧版本（4月22日），最新版本的恢复需要通过 `.bak.chat` 文件。

**恢复方案**: 恢复顺序：`agent_worker.py.bak.chat`（最新）→ `agent_worker.py.bak3.20260423` → `代理器.py.bak`（最旧）。恢复后立即用 `py_compile.compile()` 验证语法。

### 坑3：通过ssh执行多行命令时的引号转义

部署代码到CORE-01时，ssh + python -c + 多层嵌套引号导致bash解析错误。经验：复杂Python代码用文件传输（scp→本地执行）替代ssh内联执行。

### 坑4：墨蓝生成内容风格跑偏（小红书 vs 公众号）

第一次用DeepSeek生成笔记时，输出了"45岁回景德镇路上，一碗冷粉就让我破防"这种公众号风格的标题和正文。大威指出小红书没人这么写内容。

**原因**：墨蓝的system prompt只要求"真实生活感"，但完全没有注入双轨学习的爆款数据反馈——它不知道真正的爆款标题是什么样、什么风格能火。

**解决方案**：
1. 墨渊从数据库分析真实爆款数据，提炼5个标题公式和风格指南
2. 爆款样本和风格要求写入 `dual_insight_inject.txt` 注入到墨蓝prompt中
3. 明确列出"你的内容必须避开什么"（禁止煽情词、公众号长段落）
4. 重新生成后改善明显：标题变为"45岁回景德镇，第一次做陶瓷，手抖得像20岁"

### 坑5：DeepSeek API Key配置到CORE-01时写入失败

用 `echo 'DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY' >> .env` 追加时，`$DEEPSEEK_API_KEY` 在本地SSH终端中没有展开，写进文件的是字符串"$DEEPSEEK_API_KEY"本身。

**解决方案**: 直接写入Key明文到.env，然后用 `python3 -c "with open('.env') as f: ..."` 读取验证长度。

### 坑6：墨蓝engine.py中读.env的路径问题

engine.py中通过 `os.environ.get("DEEPSEEK_API_KEY")` 读环境变量，但墨蓝模块是在子进程中运行的，子进程不继承shell的export变量。需要用 `source .env` 或直接文件解析的方式加载。

**解决方案**: 在engine.py的模块初始化部分，用以下方式加载：
```python
with open("/home/ubuntu/mojiajun-queue/.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k] = v
```

## 使用验证

```bash
# 查看所有task_type（包含新角色）
python3 -c "from module_dispatcher import list_task_types; print(list_task_types())"

# 测试dispatch新角色
python3 -c "from module_dispatcher import dispatch; print(dispatch('dashboard_report', {}, 'mozi'))"

# 查看Agent心跳
mysql -h127.0.0.1 -uxiaochuan -pxiaochuan_2026_mjj mojiajun -e "SELECT agent_id, last_heartbeat FROM agent_status;"
```

## 双轨学习洞察注入

墨蓝、墨青、墨红在创作/质检前必须引用最新的双轨洞察。洞察从以下路径读取：

- 墨蓝: `/home/ubuntu/mojiajun-queue/agent_outputs/molang_v2/dual_insight_inject.txt`
- 墨青: `/home/ubuntu/mojiajun-queue/agent_outputs/moqing_v2/dual_insight.txt`
- 墨红: `/home/ubuntu/mojiajun-queue/agent_outputs/mohong/dual_insight.txt`

每日数据更新后，执行一次：
```bash
python3 /home/ubuntu/mojiajun-queue/agent_outputs/moyuan/dual_insight_and_inject.py
```

这会重新分析所有数据、产出新洞察、覆盖各Agent的inject文件。
