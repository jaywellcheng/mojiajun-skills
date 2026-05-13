---
name: mojiajun-agent-activation-checklist
description: 让墨家军Agent从模块存在到真正能产出的全链路跑通检查清单。验证每个Agent的模块导入、参数调用、数据来源、输出格式。
category: mojiajun
---

# 墨家军Agent激活检查清单

## 检查流程

### 第一步：模块存在性检查
查看Agent模块能否import，导出哪些函数。

### 第二步：参数签名检查
查看入口函数的参数名，确保和调用时一致。
常见坑：query vs keywords vs topic，execute(params) vs execute(**kwargs)

### 第三步：环境变量检查
Key必须完整写入.env，不能用变量展开（$KEY）方式。
读.env需要在脚本内逐行读取并设到os.environ。

### 第四步：实际产出检查
不只看导入成功，必须产出真实可用内容。
验收标准：墨蓝要出完整笔记正文，不只是占位符上下文。

### 第五步：数据来源检查
确认模块读的是哪个库。真实爆款数据在mojiajun库，自主采集在ceramic_db库。

## 常见故障

| 现象 | 修复 |
|:----|:-----|
| 产出为空但导入成功 | 在代码中添加从.env读取Key的逻辑 |
| missing positional argument | 参数名不匹配，检查函数签名 |
| 产出缺数据 | 读错了库，切换数据源 |

## 当前状态（2026-04-27）

墨蓝: ✅ 完整笔记 | 墨青: ✅ 封面方案 | 墨红: ✅ 质检报告 | 墨子: ✅ 仪表盘 | 墨创: ⚠️ 需换数据源 | 墨金: ❌ 未激活
