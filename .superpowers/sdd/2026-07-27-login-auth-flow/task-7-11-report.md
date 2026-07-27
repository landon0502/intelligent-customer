# Task 7-11 实施报告

## 状态: DONE

## Task 7: 创建前端 auth service 和 auth store

**提交哈希:** 721e541

**变更文件:**
- 新建: `apps/web/services/auth.ts` — auth service (loginApi, registerApi, getMeApi)
- 新建: `apps/web/store/auth.ts` — Zustand auth store (login, register, fetchUser, logout, initAuth)
- 新建: `apps/web/__tests__/auth-store.test.ts` — 3 个测试用例
- 新建: `apps/web/vitest.config.ts` — vitest 配置
- 修改: `apps/web/package.json` — 添加 test 脚本, 安装 vitest/jsdom/@testing-library/react/@vitejs/plugin-react
- 修改: `pnpm-lock.yaml`

**测试结果:** 3/3 通过

---

## Task 8: 添加 401 响应拦截器

**提交哈希:** 2c12c17

**变更文件:**
- 修改: `apps/web/lib/fetch/index.ts` — 添加 handleAuthError + resetAuthRedirect, 注册 401 拦截器, toast 跳过 401
- 新建: `apps/web/__tests__/interceptor-401.test.ts` — 3 个测试用例

**测试结果:** 3/3 通过 (总计 6/6)

---

## Task 9: 安装 shadcn 组件并实现登录/注册页面

**提交哈希:** e053ee2

**变更文件:**
- 修改: `apps/web/app/login/page.tsx` — 完整登录/注册页面实现
- 新建: `packages/ui/src/components/card.tsx` — shadcn Card 组件
- 新建: `packages/ui/src/components/input.tsx` — shadcn Input 组件
- 新建: `packages/ui/src/components/label.tsx` — shadcn Label 组件
- 修改: `packages/ui/src/styles/globals.css` — shadcn 样式更新
- 修改: `apps/web/package.json` — 添加 react-hook-form, @hookform/resolvers, zod
- 修改: `pnpm-lock.yaml`

**构建结果:** 通过

**备注:** shadcn form 组件未生成（base-nova 风格可能不支持），但登录页面直接使用 react-hook-form 的 useForm + register，不需要 form 组件。

---

## Task 10: 创建 Next.js Middleware 路由守卫

**提交哈希:** 30591d2

**变更文件:**
- 新建: `apps/web/middleware.ts` — 路由守卫 middleware

**构建结果:** 通过 (Middleware 被正确识别为 ƒ Proxy)

---

## Task 11: 在首页添加退出登录按钮

**提交哈希:** e3220da

**变更文件:**
- 修改: `apps/web/app/page.tsx` — 添加用户信息显示、退出登录按钮、initAuth 加载

**构建结果:** 通过

---

## 最终验证

- **测试:** 6/6 通过 (auth-store: 3, interceptor-401: 3)
- **构建:** 通过 (next build 成功, 3 个路由 + middleware)
- **风险信号:** 无

## 额外变更（计划外但必要）

- 安装了 vitest + jsdom + @testing-library/react + @vitejs/plugin-react（计划中未提及但测试基础设施需要）
- 创建了 vitest.config.ts（测试配置）
- 在 lib/fetch/index.ts 中导出了 resetAuthRedirect（测试需要重置 _isRedirecting 标志）
