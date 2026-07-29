# app-shell-layout Specification

## Purpose
TBD - created by archiving change web-layout-shell. Update Purpose after archive.
## Requirements
### Requirement: App Shell 三栏布局
系统 SHALL 提供 Sidebar + Header + Content 三栏布局作为已认证页面的外壳容器。Sidebar 宽度 220px，Header 高度 56px，Content 区域 flex:1 自适应并支持滚动。AppLayout 组件 SHALL 在需要 Layout 的页面中按需引入，而非在全局 `layout.tsx` 中渲染。

#### Scenario: 已认证用户访问首页
- **WHEN** 已认证用户访问 `/`
- **THEN** 页面展示 Sidebar（含 Logo、菜单）+ Header（含页面标题、用户头像 DropdownMenu）+ Content 区域

#### Scenario: 未认证用户访问登录页
- **WHEN** 未认证用户访问 `/login`
- **THEN** 页面不展示 AppLayout，仅展示登录表单

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
Sidebar 底部 SHALL 不再展示用户信息和退出登录操作。用户信息和退出登录 SHALL 移至 Header 右上角的 DropdownMenu 中。

#### Scenario: 用户信息展示
- **WHEN** 已认证用户查看 Sidebar 底部
- **THEN** Sidebar 底部不展示用户头像、用户名、角色信息和退出登录操作

### Requirement: Header 页面标题
Header 左侧 SHALL 展示当前页面的标题，标题文本通过 i18n 获取。Header 右上角 SHALL 展示语言切换按钮（独立 DropdownMenu，只显示 localeAbbr 文字）和用户头像 DropdownMenu。用户头像 DropdownMenu 触发按钮只显示头像（圆形，显示用户名首字母），DropdownMenu 内第一项显示用户必要信息（用户名、角色），后续包含主题切换、系统设置、退出登录等操作项。

#### Scenario: 首页 Header 标题
- **WHEN** 已认证用户访问首页
- **THEN** Header 左侧展示"智能对话"标题，右侧展示语言切换按钮和用户头像按钮

#### Scenario: 用户头像 DropdownMenu 展开
- **WHEN** 用户点击 Header 右上角头像按钮
- **THEN** 展开下拉菜单，第一项显示用户名和角色（不可点击），后续为主题切换、系统设置、退出登录操作

#### Scenario: 退出登录
- **WHEN** 用户在 DropdownMenu 中点击"退出登录"
- **THEN** 执行退出登录操作，跳转至登录页

### Requirement: 菜单激活状态
当前路由对应的菜单项 SHALL 有激活样式高亮，其余菜单项为默认样式。

#### Scenario: 首页菜单激活
- **WHEN** 用户在首页（`/`）
- **THEN** "智能对话"菜单项显示激活样式（高亮背景色），其余菜单项为默认样式

### Requirement: Layout 组件从 components 目录抽离
AppLayout、AppSidebar、AppHeader、ThemeSwitcher、LanguageSwitcher 等 Layout 组件 SHALL 位于 `apps/web/components/layout/` 目录下。`layout.tsx` 不再引入 AppLayout，由各页面按需引入。

#### Scenario: 组件目录结构
- **WHEN** 查看 `apps/web/components/layout/` 目录
- **THEN** 存在 `app-layout.tsx`、`app-sidebar.tsx`、`app-header.tsx`、`theme-switcher.tsx`、`language-switcher.tsx` 等 Layout 组件文件

#### Scenario: 全局 layout 不包含 AppLayout
- **WHEN** 查看 `apps/web/app/layout.tsx`
- **THEN** 不包含 AppLayout 组件的引入和渲染

### Requirement: 菜单项点击导航
点击菜单项 SHALL 导航到对应的 href 路由。使用 Next.js 的 `Link` 组件进行客户端导航。

#### Scenario: 点击菜单项导航
- **WHEN** 用户点击 Sidebar 中的菜单项
- **THEN** 使用 Next.js Link 导航到该菜单项的 href 路由，菜单激活状态随之更新

#### Scenario: 菜单项指向未实现页面
- **WHEN** 用户点击本次未实现的页面菜单项（如"知识库管理"）
- **THEN** 导航到对应路由（如 `/knowledge`），页面可能显示 404，这是可接受的

### Requirement: 国际化切换按钮文字显示
国际化切换按钮的触发元素 SHALL 只显示 `localeAbbr` 中的 value 值（如"中"/"EN"），不使用图标。

#### Scenario: 中文环境下切换按钮显示
- **WHEN** 当前语言为中文（zh-CN）
- **THEN** 国际化切换按钮显示"中"文字

#### Scenario: 英文环境下切换按钮显示
- **WHEN** 当前语言为英文（en-US）
- **THEN** 国际化切换按钮显示"EN"文字

### Requirement: 菜单项无圆角样式
Sidebar 菜单项 SHALL 使用无圆角样式，不使用 `rounded-md` 等圆角 class。

#### Scenario: 菜单项样式
- **WHEN** 已认证用户查看 Sidebar 菜单
- **THEN** 菜单项为直角样式，无圆角

