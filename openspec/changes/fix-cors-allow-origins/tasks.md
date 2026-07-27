## 1. 修复 CORS 配置

- [x] 1.1 修正 `main.py` 中 CORSMiddleware 的 `allow_origins` 传参：去除多余的方括号包裹

## 2. 验证

- [x] 2.1 确认 CORS preflight 返回 200 且包含 `Access-Control-Allow-Origin` 头
