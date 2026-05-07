---
name: hermes-agent-self-evolution-integration
description: 将NousResearch/hermes-agent-self-evolution的GEPA/MIPROv2优化管道集成到墨家军Skill体系——踩坑全记录与正确姿势。
tags:
  - mojiajun
  - self-evolution
  - dspy
  - gepa
  - skill-optimization
---

# Hermes Agent Self-Evolution 集成指南

## 核心认知

NousResearch的Self-Evolution优化**Skill文本写法**（prompt怎么更精准），墨家军的5步闭环管理**Skill知识来源**（什么该进系统）。两者互补不重叠。

## 仓库

```
https://github.com/NousResearch/hermes-agent-self-evolution
本地clone: ~/code/hermes-agent-self-evolution
```

## 踩坑记录

### 坑1：Python版本锁死GEPA

- dspy 3.0+ 要求 Python >= 3.10
- macOS自带 Python 3.9.6 → GEPA不可用，自动fallback到MIPROv2
- **解决**: 需Python 3.10+环境（pyenv/miniconda）

### 坑2：关键词评分对复杂Skill无效

`skill_fitness_metric` 默认用词重叠率评分。对简单Skill（arxiv搜索）有效，对复杂编排Skill（mojiajun-xiaohongshu 204行5000+字符）完全无效——分数卡在30%不变。

**解决**: 用 `SkillFitnessLLM` 类（已在fitness.py中实现）替换关键词评分：
```python
from evolution.core.fitness import SkillFitnessLLM
fitness = SkillFitnessLLM(skill["body"], config)
optimizer = dspy.MIPROv2(metric=fitness, auto="light")
```

### 坑3：MIPROv2无法变异复杂Skill

即使LLMJudge能区分好坏（70-95%），MIPROv2对200行+结构化Skill（YAML头+表格+多节工作流）找不到有意义的变异——产物逐字节等于原版。

**根因**: SkillModule把整个Skill当成一个instruction参数，MIPROv2的变异空间太受限。

**解决**: 拆解Skill为可独立评测的子单元（如"标题公式"段、"心理开关库"段），单独优化每个子单元。

### 坑4：DeepSeek + DSPy配置

```bash
export DEEPSEEK_API_KEY=sk-xxx
# 模型格式: deepseek/deepseek-chat
python3 -m evolution.skills.evolve_skill \
  --skill mojiajun-xiaohongshu \
  --hermes-repo ~/.hermes \
  --optimizer-model deepseek/deepseek-chat \
  --eval-model deepseek/deepseek-chat
```

DSPy通过litellm调用DeepSeek，自动识别 `deepseek/` 前缀。

### 坑5：find_skill路径匹配

`find_skill()` 按目录名匹配Skill：`skills/{name}/SKILL.md`。墨家军Skill在 `~/.hermes/skills/social-media/mojiajun-xiaohongshu/SKILL.md`，所以：
- `--hermes-repo ~/.hermes` → 搜索 `~/.hermes/skills/` 递归
- `--skill mojiajun-xiaohongshu` → 匹配目录名 `mojiajun-xiaohongshu`

### 坑6：YAML frontmatter约束误报

约束校验器 `skill_structure` 检查YAML frontmatter时存在误报——实际保留了frontmatter但校验器报缺失。这是上游bug，不影响产出。

## LLMJudge评分维度

```
composite = 0.5 × correctness      (回答正确吗)
          + 0.3 × procedure       (按流程走了吗)
          + 0.2 × conciseness     (简洁吗)
          - length_penalty         (太长扣分)
```

## 已验证的两套方案

| 方案 | 状态 | 适用场景 |
|:---|:---|:---|
| GEPA + LLMJudge | ⏳ 需Python 3.10+ | 复杂Skill，读执行轨迹做精准变异 |
| MIPROv2 + LLMJudge | ✅ 可用 | 简单Skill（<100行），小段文字优化 |
| MIPROv2 + 关键词 | ❌ 不用 | 仅适用于极简单Skill |

## 下一步：拆解Skill分段优化

对复杂Skill的最可行路径：拆出独立可评测的子单元单独跑MIPROv2。例如：
- `mojiajun-xiaohongshu` → 拆出"标题创作规则"段、"心理开关库"段
- 每段50-80行 → MIPROv2可有效变异
- LLMJudge对每段生成针对性测试集

## 相关Skill

- `mojiajun-self-evolution` — 墨家军自进化5步闭环（管知识流）
- 本Skill — NousResearch优化管道（管文本优化）
