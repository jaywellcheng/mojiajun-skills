# 新增 API 端点

## 适用场景
为现有 Flask/FastAPI 服务新增一个或多个 API 端点。

## 小川填写区（3个槽位）

- 目标文件: `[FILL]`
- 改动描述: `[FILL]`
- 额外约束: `[FILL]`

## 自动生成区（以下是固定的AS prompt结构）

【任务】为目标文件新增 API 端点：`[FILL]`

【目标文件】[FILL]

【具体改动】
1. 新增路由处理函数，使用 `@app.route(...)` 或 `@router.get(...)` 装饰器
2. 请求参数校验：类型检查 + 必填字段验证
3. 返回标准 JSON 响应：`{"code": 0, "data": ..., "msg": "ok"}` 或错误格式 `{"code": -1, "msg": "error description"}`
4. 修正/补充 imports 确保无缺失

【约束】
- 代码简洁不超100行
- 只用stdlib除非指定
- 异常处理完整（每个端点 try/except，返回 500 JSON错误）
- 不修改已有端点逻辑
- 遵循项目现有路由风格和响应格式
- [FILL]

【验收标准】
- python3 直接运行不报错
- curl 测试返回预期 JSON
- 错误输入返回合理错误码而非 crash
- imports 完整无缺失
