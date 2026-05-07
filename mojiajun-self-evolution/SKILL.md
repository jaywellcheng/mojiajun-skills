---
name: mojiajun-self-evolution
description: 墨家军自进化五步闭环 + LCM记忆体系v4 + GPT Image 2中文渲染诊断 + 拆解优化方法论 + 信号路由。全Phase 1-3部署状态。
tags:
  - mojiajun
  - self-evolution
  - memory
  - optimization
  - gpt-image-2
  - routing
  - lcm
---

# 墨家军自进化 + 记忆体系 v4

## 架构总览

```
自进化闭环: ①TasteFilter → ②临时验证区 → ③Eval → ④遗忘 → ⑤Skill触发
记忆体系:   四层加载 + 200行截断 + 四级压缩 + LLM-Map + 会话钩子
智能路由:   信号提取 → 模型路由 → Ralph目标导向
```

## Phase 1-3 全部部署 ✅ (2026-05-04)

| Phase | 模块数 | 交付 |
|:---|:---:|:---|
| P1 存储+工具+纲领 | 6 | dag_nodes表 / lcm三工具 / schema / 截断 / 纲领 / 瘦身 |
| P2 并行+钩子+安全 | 5 | lcm_map / session_hooks / 四层分级 / 安全扫描 / delegate |
| P3 监控+学习+路由 | 4 | context_monitor / 持续学习 / 同步脚本 / signal_router |
| **CORE-01 生产** | **8 .py** | 全部在 `/home/ubuntu/mojiajun-queue/` |
| **Skill 存档** | **9 refs** | `mojiajun-memory-system` + `mojiajun-self-evolution` |

---

## GPT Image 2 中文渲染诊断流程

### 问题：哪个引擎能原生渲染简体中文？

### 诊断路径
```
Step 1: Gemini (nano-banana via Crun)
  → 中文100%乱码 "天青浅"→"天精謎" ❌

Step 2: MJ/FLUX
  → 已知中文必乱码 ❌

Step 3: GPT Image 2 (Crun)
  → Internal Error，端点暂挂

Step 4: GPT Image 2 (OpenRouter: openai/gpt-5.4-image-2)
  → HTTP 403 "not available in your region"
  → 所有 OpenRouter 图模型对中国区域封锁

Step 5: ByteDance Seedream 4.5 (OpenRouter)
  → HTTP 404 模型不可用

Step 6: GPT Image 2 (Crun 恢复)
  → 三图全满分 ✅
  → "天青浅·松鼠杯" 逐字正确
  → "景德镇三日攻略" 0错误
```

### 结论
- **GPT Image 2 = 唯一能原生渲染正确简体中文的模型**
- 从中国接入: Crun API 可用 (间歇性故障), OpenRouter 锁区
- 成本: Gemini 免费但中文乱码; GPT Image 2 收费但中文完美
- prompt-forge Skill 的 TYPOGRAPHY LOCK 已验证有效

### 接入路径
- Crun: `openai/gpt-image-2` (需等恢复)
- 直连 OpenAI: 不支持银联卡
- 重试脚本: CORE-01 `retry_gpt2.py`

---

## 拆解优化方法论

### 核心发现
大Skill整坨优化无效 (200行+多段结构, MIPROv2找不到突变空间)。
**正确做法**: 拆成 1000-2000 字符的单一任务 mini-Skill, MIPROv2+LLMJudge。

### 五单元实战结果

| 子模块 | 基线 | 最优 | 提升 | 类型 |
|--------|:----:|:----:|:----:|:---|
| title-crafter | 56% | 73% | **+30.3%** | 创造性 |
| comic-script-crafter | 72% | 86% | **+18.6%** | 创造性 |
| note-body-crafter | 83% | 90% | **+8.1%** | 半结构化 |
| cover-prompt-crafter | 87% | 92% | **+5.4%** | 强规则 |
| comment-crafter | 98% | 98% | +0% | 强规则 |

### 规律
- 创造性任务 (标题/漫画脚本) → 优化空间 18-30%
- 半结构化任务 (笔记正文) → 优化空间 8%
- 强规则任务 (封面Prompt/评论区) → 优化空间 0-5%

### 复现命令
```bash
cd ~/code/hermes-agent-self-evolution
python3 -m evolution.skills.evolve_skill \
  --skill title-crafter --hermes-repo ~/.hermes \
  --iterations 5 --eval-source synthetic \
  --optimizer-model deepseek/deepseek-chat \
  --eval-model deepseek/deepseek-chat
```

---

## 信号提取 + 模型路由

### 来源: oh-my-claudecode (28 agents + 28 skills)

### TaskSignalExtractor
从任务描述提取完整画像: 复杂度/质量要求/风险/执行策略/上下文压力

### ModelRouter 三维决策
1. **任务复杂度** — 信号提取器输出
2. **上下文膨胀** — >32K强制降级到flash
3. **用户交互模式** — quick_iteration→flash / careful→reasoner

### Agent覆盖
| Agent | 默认模型 | 原因 |
|:---|:---|:---|
| moyuan | reasoner | 数据分析需强推理 |
| moqing/molan | chat | 出图/创作平衡 |
| mohong/mocheng | flash | 执行/监控用快的 |

### 调用
```python
from signal_router import TaskSignalExtractor, ModelRouter
router = ModelRouter()
d = router.route("分析爆款数据找出3个标题公式", agent="moyuan")
# → reasoner (HIGH)
```

---

## 部署踩坑 (2026-05-04 8条)

1. **dspy 2.6 不含 GEPA** → 需 3.0+Python 3.10+; Python 3.9 锁死
2. **关键词重叠 fitness 无效** → 复杂 Skill 必须 LLM-as-judge
3. **SkillModule 整坨传文本** → 必须拆 mini-Skill
4. **YAML frontmatter 校验误报** → 非阻塞，文件已保存
5. **DAG 节点 ID 碰撞** → 加微秒级时间戳 + 随机后缀
6. **pymysql source_id INT 溢出** → 大数据用 0 占位
7. **OpenRouter 图模型全锁区** → Crun 是唯一可用中转
8. **macOS Downloads 文件夹不可访问** → 拖到 Desktop 再操作

---

## Phase 4: 三大自进化新机制 (2026-05-05)

基于"AI Agent自我改进的六条路"方法论，一晚部署三条新机制：

### 4a. 对抗训练 (Adversarial Learning)
- **架构**：墨创（出题方）从xhs_sample_library抽2条标题 → 墨蓝（解题方）用DeepSeek判断哪条更好 → 真实互动数据打分
- **模块**：`adversarial_learner.py`，task_type=`adversarial_learn`
- **数据源**：211条带互动数据的标题
- **评分公式**：点赞×0.4 + 收藏×0.5 + 评论×0.1
- **每轮产出**：correct/not + 洞察（如"用'无广'建立信任，用'藏不住'制造稀缺")
- **模式**：墨创出题→墨蓝判断→数据验证→对错都记录→洞察积累→更新skill

### 4b. 编排自优化 (Prompt Self-Optimization)
- **架构**：AI读取当前system_prompt → 分析结构 → 提出改进版 → 保存版本历史
- **模块**：`prompt_optimizer.py`，task_type=`prompt_optimize`
- **版本管理**：`VERSIONS_DIR/v_YYYYMMDD_HHMMSS/` 存原版+改进版+改动说明
- **已验证**：AI成功分析comic_planner的CHARACTER_VISUALS，提出4项改进（合并重复、增加互动约束、情绪提示、去冗余）
- **安全边界**：改进版保存为候选，不自动替换生产版本

### 4c. 自我修改 (Self-Modification)
- **架构**：AI诊断系统短板 → 生成新Python模块 → 保存到待审核目录 → 人工激活
- **模块**：`self_modify.py`，task_type=`self_modify`
- **安全沙箱**：生成的代码写入`self_generated_skills/pending_*.py`，绝不自动执行
- **已验证**：AI诊断出"对抗学习30%准确率根因=缺失败分析"，生成了`failure_lesson_extractor`模块
- **审核流程**：大威检查代码→确认安全→手动部署到module_dispatcher

### 三机制协同闭环
```
对抗训练(4a) → 发现准确率低 → 编排自优化(4b)改进prompt → 自我修改(4c)生成新模块
       ↑                                                              ↓
       └────────────── 洞察回流 → 更新skill ←──────────────────────┘
```

### 模块注册
```python
# module_dispatcher.py 新增三行
"adversarial_learn":  ("mochuang", "adversarial_learner",  "train_round"),
"prompt_optimize":    ("mochuang", "prompt_optimizer",     "optimize_prompt"),
"self_modify":        ("mochuang", "self_modify",          "self_modify"),
```

## 部署日期
2026-05-04 — 自进化闭环 + 拆解优化 + LCM记忆v4 + GPT Image 2诊断 + 信号路由 全Phase 1-3
2026-05-05 — Phase 4: 对抗训练 + 编排自优化 + 自我修改 全部署
