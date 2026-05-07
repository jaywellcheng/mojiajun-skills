---
name: yaogun-rensheng-comic-planning
description: 窑滚人生搞笑漫画系列策划全链路——从墨创脚本策划→大威审核→墨青出图。含锁定角色造型规范、DeepSeek prompt模板、task_queue派发模式。
category: mojiajun
tags: [comic, yaogun-rensheng, mochuang, deepseek, character-visuals, content-pipeline]
---

# 窑滚人生漫画策划全链路

## 概述

窑滚人生 = 陶瓷角色拟人化搞笑漫画系列。墨创（内容策划）用DeepSeek生成4格分镜脚本+配文，大威审核后墨青出图。

## 角色造型规范（不可变，来自EP1概念图）

> 参考文件夹：`/Users/jaywell/Desktop/墨家军资料库/窑滚人生/`
> 造型概念图：`窑滚人生_角色造型概念图.png`
> Q版概念图：`窑滚人生_Q版造型概念图.png`

### 青隐（青花瓷）— 佛系躺平，爱吐槽
- **正片**：黑色长发微卷凌乱，长脸线条柔和，深蓝色宽袖汉服长袍+白色内衬+青花蓝纹图案，高挑修长，双臂交叉胸前，冷峻内敛眼神深邃
- **Q版**：深蓝色发髻+白色蝴蝶结发饰，蓝白汉服长袍+浅蓝花卉刺绣，温和微笑，双臂交叉
- **性格**：全程躺平喝茶，事不关己，最后一句暴击收尾

### 软彩（粉彩瓷）— 热情话多，容易激动
- **正片**：深棕色双麻花辫+粉色花朵发饰，圆脸可爱，粉色洛丽塔长裙+多层荷叶边+蕾丝花边+蝴蝶结，娇小身材，双手叉腰，笑容灿烂露齿
- **Q版**：棕色长卷发+粉色花朵发饰，粉色连衣裙+金色花纹+蝴蝶结，笑容灿烂，双手叉腰
- **性格**：本地人回老家，热情拉人到处玩，临走被妈塞满后备箱

### 米通（玲珑瓷）— 老实憨厚，经常被坑
- **正片**：银白色长发波浪披肩，小巧瓜子脸，白色长裙+镂空蕾丝设计+淡蓝金色星点花纹，娇小纤细，双手交叠胸前，害羞内向怯生生
- **Q版**：银白色长直发+蓝色小花珠串装饰，白色长裙+淡蓝花纹，温柔恬静，双手合十胸前
- **性格**：老实人被安排得明明白白，累瘫但不懂拒绝

### 窑变（颜色釉）— 热情奔放，玩疯了
- **正片**：橙红色短发蓬松凌乱有动感，长脸线条柔和，深红→深绿渐变长袍+流苏碎布装饰+不规则边缘，身材高大修长，双臂张开手掌向上，笑容开朗自信张扬
- **Q版**：橙红色短发蓬松，彩虹渐变长袍（橙→绿→蓝过渡）+星光斑点，笑容开朗露齿，双臂张开
- **性格**：假期玩疯了完全不想收假，精力无限

## DeepSeek Prompt模板

墨创的comic_planner.py已部署在CORE-01：`/home/ubuntu/mojiajun-queue/agent_outputs/mochuang/comic_planner.py`

System prompt必须注入完整的CHARACTER_VISUALS规范（见上面），确保每期角色造型一致。

### Payload格式

```json
{
  "theme": "五一最后一天假期结束",
  "series": "窑滚人生",
  "grids": 4,
  "tone": "轻松幽默吐槽，45岁中年男人视角，真实不煽情",
  "roles": {
    "软彩": "热情话多，本地人回老家过五一，临走被妈塞满土特产",
    "米通": "老实憨厚，被软彩拉着5天跑8个景点累瘫",
    "窑变": "热情奔放，假期玩疯了不想收假",
    "青隐": "佛系躺平，全程喝茶没挪窝，最后暴击收尾"
  },
  "note_req": "逻辑自洽，第4格反转。角色造型严格按EP1规范。"
}
```

### 输出格式（严格JSON）

```json
{
  "title": "本期标题",
  "episode": "集数",
  "grids": [
    {"grid": 1, "scene": "场景", "style": "正片", "characters": ["角色"], "action": "动作", "dialogue": "[角色名]对白(≤20字)"}
  ],
  "q_bonus": {"style": "Q版", "scene": "场景", "dialogue": "科普一句(≤25字)"},
  "note_text": "配文(100-200字，45岁男人视角，结尾引导评论)"
}
```

## 工作流

```
大威/小川定主题
    ↓
墨创策划（task_queue: comic_script）
    ↓ DeepSeek生成脚本+配文
大威审核 ← 【人控环节，不自动化】
    ↓ 通过
墨青出图（待对接：出封面Prompt + 生成6格图）
    ↓
大威发布
```

## Task_queue派发

task_type: `comic_script`
target_agent: `mochuang`
module: `comic_planner.plan`

```sql
INSERT INTO task_queue (task_id, target_agent, task_type, payload, status, priority, created_at) 
VALUES (CONCAT('comic_', UNIX_TIMESTAMP()), 'mochuang', 'comic_script', '<JSON payload>', 'pending', 5, NOW());
```

## 结果读取

墨创产出保存在：`/home/ubuntu/mojiajun-queue/agent_outputs/mochuang/comic_plan_*.json`

```bash
ssh ubuntu@159.75.12.11 "ls -t agent_outputs/mochuang/comic_plan_*.json | head -1 | xargs python3 -m json.tool"
```

## 费用

DeepSeek chat模型，每期脚本约800-1000 tokens，$0.001级别。

## 审核要点

1. 逻辑自洽：同一角色的场景不能矛盾（如不能同时"在外旅游"和"回老家被妈塞东西"）
2. 第4格反转笑点是否成立
3. 配文是否45岁男人视角、不用"姐妹们"
4. 角色造型是否引用了EP1规范
5. 结尾是否引导评论互动

## 相关文件

- 本地造型参考：`/Users/jaywell/Desktop/墨家军资料库/窑滚人生/`
- CORE-01模块：`/home/ubuntu/mojiajun-queue/agent_outputs/mochuang/comic_planner.py`
- 注册位置：`module_dispatcher.py` line 46
- Skill：`mojiajun-agent-module-deployment` — 模块部署通用模式
- Skill：`mojiajun-comic-series-production` — 漫画生产全链路（气泡、出图等）
