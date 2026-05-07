---
name: adversarial-learning-analysis-mode
description: 对抗学习核心发现——分析模式（问"为什么"）vs 预测模式（问"哪个"），前者产出7条高质量洞察，后者准确率30%。2026-05-05更新：CORE-01实操验证，增加完整代码模板。
category: mojiajun
tags: [adversarial-learning, self-evolution, insights, methodology]
---

# 对抗学习：分析模式 > 预测模式

## 核心发现（2026-05-05 CORE-01实战验证）

用211条真实小红书爆款标题训练AI时，两种模式对比：

| 模式 | 问题 | 准确率 | 洞察产出/10轮 |
|------|------|:--:|:--:|
| v1 预测模式 | "哪条标题更好？" | 30% | 3条 |
| v2 分析模式 | "为什么这条更好？" | N/A | **7条** |

**根因**：标题数据天然高噪声——内容质量、图片、发布时间、作者影响力都搅在一起。二元判断注定低准确率。但让AI分析"为什么"，无论判断对错都能产出高质量洞察。

## 完整代码模板

部署位置：`agent_outputs/mochuang/adversarial_learner.py`
注册：`module_dispatcher.py` 添加 `"adversarial_learn": ("mochuang", "adversarial_learner", "train_round")`

### 关键设计决策

**1. 样本选择——确保区分度**
```python
# ✅ 一条爆款+一条普通
(SELECT * FROM xhs_sample_library WHERE likes > 30000 ORDER BY RAND() LIMIT 1)
UNION ALL
(SELECT * FROM xhs_sample_library WHERE likes < 5000 AND likes > 0 ORDER BY RAND() LIMIT 1)
# 然后 random.shuffle() 打乱顺序，避免位置偏差
```

**2. 评分公式——log压缩防极端值**
```python
# ✅ log1p压缩，避免超级爆款淹没区分度
return math.log1p(likes) * 0.6 + math.log1p(collects) * 0.3 + math.log1p(comments) * 0.1
```

**3. System Prompt——问"为什么"不问"哪个"**
```python
system_prompt = """你是小红书爆款标题分析师。给你两条标题和它们的点赞数据，分析为什么数据更好的那条赢了。

分析维度：心理开关强度、具体画面感、收藏价值、评论驱动力

输出JSON：{"analysis": {"key_difference": "决定性差异（20字）"}, "insight": "可提炼为标题公式的一句话洞察（30字）"}"""

# 关键：告诉AI真实答案，让它分析原因而非猜测
user_prompt = f"标题1（赞{likes1}）：{title1}\n标题2（赞{likes2}）：{title2}\n实际标题{winner}效果更好。请分析为什么。"
```

**4. 必须自加载.env（worker环境变量不全）**
```python
_env_file = Path("/home/ubuntu/mojiajun-queue/.env")
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        ...
```

## 产出洞察质量示例（10轮实测）
```
1. "具体数字+情绪词+长期价值，比单纯地点推荐更能激发点击与收藏"
2. "用夸张拟人制造画面感和互动欲，远胜于干巴巴描述物品"
3. "反常识+具体场景+高情绪词 = 爆款标题公式"
4. "用'无法表达'制造好奇，奶茶点单强关联生活高频需求"
5. "高赞标题=强烈情绪冲突+具体场景，引发向往和代入感"
6. "具体场景+反常识/高性价比+晒单互动，比单纯地名信息更易引爆"
7. "实用清单类比文艺描述更能激发互动"
```

## 远程部署铁律（shell heredoc避坑）

```bash
# ❌ SSH heredoc中Python f-string/花括号/引号必然冲突
ssh host "python3 << 'EOF'
... f\"{var}\" ...  # 被shell解释
EOF"

# ✅ 三步法：本地写文件 → base64编码 → SSH解码执行
base64 -i /tmp/script.py | ssh host "base64 -d | python3"

# ✅ 或：scp文件 → SSH执行
scp /tmp/script.py host:/tmp/ && ssh host "python3 /tmp/script.py"
```

## 适用场景

| 场景 | 数据源 | 分析目标 |
|------|--------|---------|
| 标题优化 | xhs_sample_library (211条) | 提炼标题公式 |
| 内容策略 | notes_published | 哪种内容类型转化好 |
| 封面设计 | media_assets | 什么视觉风格获赞高 |
| 发布时间 | task_queue | 最佳发布时段 |

## 与学术对齐

对应 Self-Evolving Agents 综述中的 **Online Exploration** 路径 + **Model-Environment Co-Evolution**——Agent通过与环境（真实标题数据）交互获取反馈，提炼可复用的洞察而非做低精度预测。
