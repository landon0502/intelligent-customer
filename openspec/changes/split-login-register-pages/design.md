## Context

当前登录页 `/login` 使用 `mode` 状态（`"login" | "register"`）在登录和注册两个表单之间切换。这种设计导致 URL 无法反映用户当前所处的流程，且组件代码耦合度高（200+ 行单文件，双 schema、双 form 实例、条件渲染）。

现有基础设施：
- 后端 API `/api/auth/login` 和 `/api/auth/register` 已独立，无需修改
- `useAuthStore` 已提供 `login()` 和 `register()` 两个独立方法
- Next.js middleware 已实现 Cookie 检查 + 重定向逻辑

## Goals / Non-Goals

**Goals:**
- 登录和注册各自拥有独立 URL（`/login` 和 `/register`）
- 每个页面代码独立、简洁，移除 `mode` 状态和条件渲染
- middleware 放行 `/register` 路由，已登录用户访问 `/register` 重定向到首页
- 页面间通过链接跳转（非状态切换），保留"没有账户？注册"/"已有账户？登录"引导

**Non-Goals:**
- 不修改后端 API
- 不修改 auth store 逻辑
- 不新增第三方依赖
- 不修改 token 管理或 401 拦截器

## Decisions

### D1: 路由结构 — `/login` + `/register` 独立页面

**选择**：创建 `apps/web/app/register/page.tsx` 独立页面
**替代方案**：使用动态路由 `/auth/[type]` 统一入口
**理由**：两个页面逻辑差异大（注册多一个确认密码字段、不同 schema、不同提交函数），独立页面更清晰，且符合 Next.js App Router 的约定。统一入口虽代码复用多，但增加不必要的抽象复杂度。

### D2: 共享样式和布局 — 各自独立实现

**选择**：两个页面各自实现完整的 Card 布局
**替代方案**：抽取共享的 AuthCard 组件
**理由**：当前两个页面代码量小（各约 80 行），过早抽象会增加维护成本。若后续添加第三方登录、忘记密码等功能导致页面复杂度增加，再行抽取。

### D3: Middleware 放行 — 白名单方式

**选择**：middleware 中将 `/register` 加入未登录可访问的白名单
**理由**：与 `/login` 一致，未登录用户可访问 `/register`，已登录用户访问 `/register` 重定向到首页。

## Risks / Trade-offs

- **[链接一致性]** → 退出登录后的重定向仍指向 `/login`（auth store logout 中 `window.location.href = "/login"`），这是预期行为
- **[SEO/可分享性改善]** → 注册链接可直接分享，无需用户先进入登录页再切换模式
