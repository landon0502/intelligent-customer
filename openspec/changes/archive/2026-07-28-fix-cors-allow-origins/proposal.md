## Why

前端请求后端 API 时遇到跨域问题。虽然后端配置了 `CORSMiddleware`，但 CORS preflight（OPTIONS）请求始终返回 `400 Disallowed CORS origin`，浏览器因此阻止所有跨域请求。Next.js rewrites 也无法生效（因为前端 `baseURL` 指向绝对地址 `http://localhost:8001`，请求不经过 Next.js 代理）。

## 根因分析

`apps/service/app/main.py` 第 51 行注册 CORSMiddleware 时：

```python
allow_origins=[settings.CORS_ORIGINS],
```

`settings.CORS_ORIGINS` 已经是 `list[str]`（`config.py` 中 `.split(",")` 产生），此处再用方括号包裹，导致 `allow_origins` 实际值为嵌套列表 `[['http://localhost:3000']]`。

CORSMiddleware 匹配时执行 `origin in self.allow_origins`，即 `"http://localhost:3000" in [['http://localhost:3000']]` → `False`，所以所有 Origin 都被判定为 `Disallowed`，preflight 返回 400。

## 修复目标

修正 `main.py` 中 `allow_origins` 的传参，去除多余的方括号包裹，使 CORSMiddleware 能正确匹配允许的 Origin。

## What Changes

- 修复 `apps/service/app/main.py` 中 CORSMiddleware 的 `allow_origins` 传参：`[settings.CORS_ORIGINS]` → `settings.CORS_ORIGINS`

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
（无 — 不改变 spec 验收场景，仅修复实现 bug）

## Impact

- **后端代码**：`apps/service/app/main.py`（单行修复）
- **API**：无接口变更
- **依赖**：无
