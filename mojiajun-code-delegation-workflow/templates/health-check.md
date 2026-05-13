# 健康检查脚本

## 适用场景
编写/修改服务健康检查脚本——HTTP端点探测、进程存活检查、资源监控等。

## 小川填写区（3个槽位）

- 目标文件: `[FILL]`
- 改动描述: `[FILL]`
- 额外约束: `[FILL]`

## 自动生成区（以下是固定的AS prompt结构）

【任务】编写/修改健康检查脚本：`[FILL]`

【目标文件】[FILL]

【具体改动】
1. 实现健康检查函数，检查目标服务的可用性
2. 检查项包括：HTTP端点返回200、进程存活、端口监听、磁盘/内存阈值
3. 输出结构化结果：JSON格式 `{"status":"ok"|"degraded"|"down", "checks":{...}, "timestamp":"ISO8601"}`
4. 返回码：ok=0, degraded=1, down=2
5. 支持命令行参数：--timeout, --endpoint, --verbose

【约束】
- 代码简洁不超100行
- 只用stdlib（urllib/subprocess/psutil如需指定）除非指定
- 超时处理：每个检查项有独立 timeout，不互相阻塞
- 异常处理完整：网络不可达、超时、权限不足 都有明确错误输出
- [FILL]

【验收标准】
- python3 直接运行不报错
- 正常服务返回 exit 0 + JSON status=ok
- 异常服务返回非0 exit + JSON status=down
- --verbose 模式输出详细检查过程
