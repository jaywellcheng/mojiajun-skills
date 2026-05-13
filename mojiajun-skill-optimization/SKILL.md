---
name: mojiajun-skill-optimization
description: 墨家军Skill优化方法论 — 大Skill拆成1000-2000字符的单一任务mini-Skill，用MIPROv2+LLMJudge逐个优化。包含完整工作流、评分策略、拆解原则、5单元实测数据。
tags:
  - mojiajun
  - skill-optimization
  - miprov2
  - llm-judge
  - dspy
  - evolution
source: NousResearch/hermes-agent-self-evolution + 墨家军实战验证
updated: 2026-05-04
---

# 墨家军 Skill 优化方法论

## 核心发现

**大Skill整坨优化无效**（200行+多段结构，MIPROv2找不到突变空间）。
**正确做法**：拆成1000-2000字符的单一任务 mini-Skill，逐个用 MIPROv2+LLMJudge 优化。

## 为什么关键词重叠评分不行

默认 fitness metric 用关键词重叠率打分。对简单 Skill（如 arxiv 搜索：输入"找论文2402.03300"→输出"查询API返回BibTeX"）有效。但对复杂编排 Skill（8Agent协作+标题公式库+心理开关+四阶段策略），所有变异都卡在30%。

**修法**：代码里已有 `LLMJudge` 类（三维度打分：correctness 0.5 + procedure_following 0.3 + conciseness 0.2），但只在GEPA路径启用。需接入 MIPROv2 metric。

### 具体修改

**fitness.py**：新增 `SkillFitnessLLM` 类
```python
class SkillFitnessLLM:
    def __init__(self, skill_text, config):
        self.judge = LLMJudge(config)
    def __call__(self, example, prediction, trace=None):
        # 调 LLMJudge.score() 做三维度打分
        # LLM失败时 fallback 到关键词重叠
```

**evolve_skill.py**：MIPROv2 fallback 路径替换 metric
```python
llm_fitness = SkillFitnessLLM(skill["body"], config)
optimizer = dspy.MIPROv2(metric=llm_fitness, auto="light")
```

## 拆解原则

| 原则 | 说明 |
|:---|:---|
| **单一任务** | 只做一件事（标题创作 / Prompt生成 / 正文结构） |
| **1000-2000字符** | 超过2000 → 拆；不到1000 → 太薄，优化无意义 |
| **独立可测** | 给定输入→产出输出，LLMJudge 能清晰评判 |
| **有对错标准** | 规则明确的任务（评论区）基线高但提升空间小 |

## 完整工作流

```bash
# 1. 拆出 mini-Skill → ~/.hermes/skills/social-media/{name}/SKILL.md

# 2. 依赖
pip3 install dspy openai pyyaml click rich

# 3. Clone NousResearch 仓库
cd ~/code && git clone https://github.com/NousResearch/hermes-agent-self-evolution.git

# 4. 修改 fitness.py（加 SkillFitnessLLM）+ evolve_skill.py（用 LLMJudge）

# 5. 运行优化
export DEEPSEEK_API_KEY="sk-xxx"
cd ~/code/hermes-agent-self-evolution
python3 -m evolution.skills.evolve_skill \
  --skill {name} --hermes-repo ~/.hermes \
  --iterations 5 --eval-source synthetic \
  --optimizer-model deepseek/deepseek-chat \
  --eval-model deepseek/deepseek-chat
```

## 五单元实测数据（2026-05-04）

| 子模块 | 基线 | 最优 | 提升 | 耗时 | 类型 | 规律 |
|--------|:----:|:----:|:----:|:----:|:---|:---|
| title-crafter 标题创作 | 56% | 73% | **+30.3%** | 282s | 创造性 | 优化空间最大 |
| comic-script-crafter 漫画脚本 | 72% | 86% | **+18.6%** | 199s | 创造性 | 结构+创意 |
| note-body-crafter 笔记正文 | 83% | 90% | **+8.1%** | 226s | 半结构化 | 有规则有发挥 |
| cover-prompt-crafter 封面Prompt | 87% | 92% | **+5.4%** | 259s | 强规则 | 规则明确 |
| comment-crafter 评论区 | 98% | 98% | **+0%** | 153s | 强规则 | 基线已优秀 |

**规律：创造性任务 18-30%，半结构化 8%，强规则 0-5%。**

## 三次迭代踩坑

### 第1轮（关键词评分）：整坨Skill，全30%死水
- mojiajun-xiaohongshu（5541字符），fitness metric=关键词重叠
- 结果：评分全程持平 +0%，无法区分好坏

### 第2轮（LLMJudge）：整坨Skill，有区分度但无变异
- 同Skill，换上 LLMJudge
- 结果：评分 70-95% 有区分度，但 MIPROv2 找不到优于原文的变异
- 根因：SkillModule 把 5000+ 字符整坨传参，MIPROv2 变异空间受限

### 第3轮（拆解+LLMJudge）：mini-Skill，显著提升
- title-crafter（1880字符），单任务
- 结果：+30.3% 提升
- 验证：拆解是对的

## 踩坑记录

1. **dspy 3.0 需要 Python 3.10+** — GEPA 不可用，自动 fallback MIPROv2
2. **fitness metric 太简陋** — 必须 LLM-as-judge
3. **SkillModule 整坨传文本** — 必须拆成 mini-Skill
4. **优化产物不是新 SKILL.md** — MIPROv2 优化编译后程序（few-shot选择），文件字节相同
5. **YAML frontmatter 约束误报** — 非阻塞，文件已保存

## 集成

优化后的 mini-Skill 存入主 Skill 的 references/optimized/，双端部署：

```
mojiajun-xiaohongshu/references/optimized/
├── title-crafter.md       (+30.3%)
├── comic-script-crafter.md (+18.6%)
├── note-body-crafter.md   (+8.1%)
├── cover-prompt-crafter.md (+5.4%)
└── comment-crafter.md     (基线优秀)
```

## 后续

每2周用新爆款数据重新生成评测集，跑一轮优化。标题公式会过时，新数据让 mini-Skill 继续进化。
