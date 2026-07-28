## Why

当前 Web 端首页只有一个简单的欢迎页面，缺少整体应用外壳（App Shell）布局。根据原型设计，系统需要 Sidebar + Header + Content 三栏布局来承载后续所有业务页面。同时，主题切换和国际化功能虽然已有基础（next-themes + message JSON 文件），但尚未在 Layout 中暴露用户入口，也未接入 i18n 运行时。现在需要建立 Layout 基础架构，为后续所有页面提供统一的布局容器和基础设施。

## What Changes

- 新增 App Shell Layout 组件体系：AppSidebar、AppHeader、AppLayout，从 `apps/web/components/` 中抽离
- 菜单以配置声明式方式定义（支持角色过滤），统一管理路由和菜单映射
- 接入 i18n 运行时（next-intl），替换现有硬编码中文文本
- 在 Header 中暴露主题切换入口（亮色/暗色/跟随系统）和语言切换入口
- 改造 `layout.tsx` 为带 Sidebar + Header 的完整布局
- 更新 `messages/zh-CN.json` 和 `messages/en-US.json`，添加 Layout 相关翻译内容
- 更新首页 `page.tsx` 为使用新 Layout 的占位内容

## Capabilities

### New Capabilities
- `app-shell-layout`: 应用外壳布局，包含 Sidebar、Header、Content 三栏结构，菜单配置声明，角色过滤，响应式基础
- `i18n-runtime`: 国际化运行时接入（next-intl），语言切换，翻译文件整合
- `theme-switcher`: 主题切换 UI 入口（亮色/暗色/跟随系统），集成到 Header

### Modified Capabilities
- `user-auth`: Layout 中 Sidebar 用户信息展示需要读取 auth store 的 user 数据，菜单角色过滤依赖 user.role

## Impact

- **代码变更**：`apps/web/app/layout.tsx`、`apps/web/app/page.tsx` 需重构
- **新增组件**：`apps/web/components/` 下新增 AppLayout、AppSidebar、AppHeader 等组件
- **新增依赖**：需安装 `next-intl` 及相关配置
- **UI 组件**：`packages/ui/` 可能需添加 sidebar、avatar、dropdown-menu 等 shadcn 组件
- **翻译文件**：`apps/web/messages/` 下的 JSON 文件需更新（从 LingDiary 内容替换为 AI 客服系统内容）
- **中间件**：`apps/web/middleware.ts` 可能需要增加 i18n 路由前缀处理
