## 1. 页面拆分

- [x] 1.1 精简 `/login` 页面：移除 `mode` 状态、注册表单、`registerForm`、`confirmPassword` 相关代码，仅保留登录表单，底部添加"没有账户？注册"链接跳转到 `/register`
- [x] 1.2 创建 `/register` 页面 `apps/web/app/register/page.tsx`：包含注册表单（用户名、密码、确认密码）和 zod 校验，提交调用 `useAuthStore().register()`，底部添加"已有账户？登录"链接跳转到 `/login`

## 2. 路由守卫更新

- [x] 2.1 更新 middleware：未登录用户允许访问 `/register`；已登录用户访问 `/login` 或 `/register` 均重定向到首页

## 3. 验证

- [x] 3.1 确认构建通过且现有测试不受影响
