# 墨家军 Skill 库

墨家军 AI Agent 团队的自定义技能库。

## 结构

```
mojiajun-skills/
├── README.md
├── backlog/               # 跨会话任务追踪系统
├── core01/                # CORE-01 专用技能
├── local/                 # 本地 Mac 专用技能
├── shared/                # 通用技能
├── mojiajun/              # 墨家军核心技能包
├── mojiajun-*/            # 各子技能
├── xiaochuan-*/           # 小川相关技能
├── xiaohongshu-*/         # 小红书运营技能
├── xiaoma/                # 小马辅导技能
├── baoyu-comic/           # 知识漫画生成
├── deerflow-*/            # DeerFlow 架构参考
└── lyra2-*/               # NVIDIA Lyra 3D 储备
```

## 部署

技能部署在 Hermes Agent 的 `~/.hermes/skills/` 目录下。
本地 Mac 和 CORE-01 各有部署，此仓库为统一源码。

## 来源

- 本地 Mac：`~/.hermes/skills/`
- CORE-01：`~/.hermes/skills/`（通过 SSH 同步）
