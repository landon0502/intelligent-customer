# app-shell-layout Specification

## Purpose
TBD - created by archiving change web-layout-shell. Update Purpose after archive.
## Requirements
### Requirement: App Shell 三栏布局
系统 SHALL 提供 Sidebar + Header + Content 三栏布局作为所有已认证页面的外壳容器。Sidebar 宽度 220px，Header 高度 56px，Content 区域 flex:1 自适应并支持滚动。

#### Scenario: 已认证用户访问首页
- **WHEN** 已认证用户访问 `/`
- **THEN** 页面展示 Sidebar（含 Logo、菜单、用户信息）+ Header（含页面标题、主题切换、语言切换）+ Content 区域

#### Scenario: Content 区域自适应
- **WHEN** 浏览器窗口大小变化
- **THEN** Sidebar 宽度固定 220px，Header 高度固定 56px，Content 区域自适应填充剩余空间

### Requirement: Sidebar 包含 Logo 区域
Sidebar 顶部 SHALL 展示应用 Logo 和名称。Logo 区域与 Header 同高（56px），底部有分隔线。

#### Scenario: Logo 区域展示
- **WHEN** 已认证用户看到 Sidebar
- **THEN** 顶部展示机器人图标（🤖）和"AI 客服"文字，高度与 Header 一致

### Requirement: 菜单配置声明式定义
菜单项 SHALL 通过配置数组声明，每个菜单项包含 `key`（唯一标识）、`labelKey`（i18n 翻译键）、`href`（路由）、`icon`（图标组件）、`roles`（可选，允许访问的角色列表）。菜单分组通过 `type: 'group'` 声明。

#### Scenario: 菜单配置定义
- **WHEN** 开发者在 `config/menu.ts` 中定义菜单配置数组
- **THEN** Sidebar 按配置顺序渲染菜单项，支持分组、图标、国际化标签

#### Scenario: 新增菜单项
- **WHEN** 在配置数组中新增一个菜单项
- **THEN** Sidebar 自动渲染新增菜单项，无需修改组件代码

### Requirement: 菜单角色过滤
系统 SHALL 根据当前登录用户的 `role` 过滤菜单项。当菜单项配置了 `roles` 时，仅对匹配角色的用户可见；未配置 `roles` 的菜单项对所有用户可见。

#### Scenario: 管理员查看菜单
- **WHEN** `user.role === 'admin'` 的用户查看 Sidebar
- **THEN** 显示"智能对话"和"管理"分组下的所有菜单项（知识库管理、用户管理、系统配置、工具配置）

#### Scenario: 普通用户查看菜单
- **WHEN** `user.role === 'user'` 的用户查看 Sidebar
- **THEN** 仅显示"智能对话"菜单项，不显示"管理"分组

### Requirement: Sidebar 底部用户信息
Sidebar 底部 SHALL 展示当前登录用户的头像、用户名、角色信息，以及退出登录操作。

#### Scenario: 用户信息展示
- **WHEN** 已认证用户查看 Sidebar 底部
- **THEN** 显示用户头像（占位圆形）、用户名、角色标签和"退出登录"文字

### Requirement: Header 页面标题
Header 左侧 SHALL 展示当前页面的标题，标题文本通过 i18n 获取。

#### Scenario: 首页 Header 标题
- **WHEN** 用户访问首页
- **THEN** Header 左侧展示"智能对话"标题（中文环境）或"Smart Chat"（英文环境）

### Requirement: 菜单激活状态
当前路由对应的菜单项 SHALL 有激活样式高亮，其余菜单项为默认样式。

#### Scenario: 首页菜单激活
- **WHEN** 用户在首页（`/`）
- **THEN** "智能对话"菜单项显示激活样式（高亮背景色），其余菜单项为默认样式

### Requirement: Layout 组件从 components 目录抽离
AppLayout、AppSidebar、AppHeader 等 Layout 组件 SHALL 位于 `apps/web/components/` 目录下，而非直接写在 `layout.tsx` 中。`layout.tsx` 仅作为组合入口。

#### Scenario: 组件目录结构
- **WHEN** 查看 `apps/web/components/` 目录
- **THEN** 存在 `app-layout.tsx`、`app-sidebar.tsx`、`app-header.tsx` 等 Layout 组件文件

### Requirement: 菜单项点击导航
点击菜单项 SHALL 导航到对应的 href 路由。使用 Next.js 的 `Link` 组件进行客户端导航。

#### Scenario: 点击菜单项导航
- **WHEN** 用户点击 Sidebar 中的菜单项
- **THEN** 使用 Next.js Link 导航到该菜单项的 href 路由，菜单激活状态随之更新

#### Scenario: 菜单项指向未实现页面
- **WHEN** 用户点击本次未实现的页面菜单项（如"知识库管理"）
- **THEN** 导航到对应路由（如 `/knowledge`），页面可能显示 404，这是可接受的

