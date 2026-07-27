## Context

CORSMiddleware 在 FastAPI 中根据 `allow_origins` 列表匹配请求 Origin。当前代码因嵌套列表导致所有 Origin 匹配失败。

## Goals / Non-Goals

**Goals:**
- 修正 `allow_origins` 传参，使 CORS preflight 正确返回 `Access-Control-Allow-Origin` 头

**Non-Goals:**
- 不修改 CORS 配置项本身（`settings.CORS_ORIGINS` 定义正确）
- 不修改前端请求方式或 Next.js rewrites 配置
- 不修改 `allow_methods`、`allow_headers` 等其他 CORS 参数

## Decisions

### D1: 直接使用 `settings.CORS_ORIGINS`

**选择**：`allow_origins=settings.CORS_ORIGINS`
**理由**：`settings.CORS_ORIGINS` 已是 `list[str]`，无需再包裹。这是最直接的修复。

## Risks / Trade-offs

- 无风险：`settings.CORS_ORIGINS` 的类型和值已在 `config.py` 中正确定义
