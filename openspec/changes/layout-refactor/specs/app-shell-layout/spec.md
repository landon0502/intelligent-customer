## MODIFIED Requirements

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

### Requirement: Sidebar 底部用户信息
Sidebar 底部 SHALL 不再展示用户信息和退出登录操作。用户信息和退出登录 SHALL 移至 Header 右上角的 DropdownMenu 中。

#### Scenario: Sidebar 底部无用户信息
- **WHEN** 已认证用户查看 Sidebar 底部
- **THEN** Sidebar 底部不展示用户头像、用户名、角色信息和退出登录操作

### Requirement: Header 页面标题与用户菜单
Header 左侧 SHALL 展示当前页面的标题，标题文本通过 i18n 获取。Header 右上角 SHALL 展示用户头像 DropdownMenu，触发按钮只显示头像（圆形，显示用户名首字母），DropdownMenu 内第一项显示用户必要信息（用户名、角色），后续包含语言切换、主题切换、退出登录等操作项。

#### Scenario: 首页 Header 标题与用户菜单
- **WHEN** 已认证用户访问首页
- **THEN** Header 左侧展示"智能对话"标题，右侧展示用户头像按钮

#### Scenario: 用户头像 DropdownMenu 展开
- **WHEN** 用户点击 Header 右上角头像按钮
- **THEN** 展开下拉菜单，第一项显示用户名和角色（不可点击），后续为语言切换、主题切换、退出登录操作

#### Scenario: 退出登录
- **WHEN** 用户在 DropdownMenu 中点击"退出登录"
- **THEN** 执行退出登录操作，跳转至登录页

### Requirement: Layout 组件从 components/layout 目录组织
AppLayout、AppSidebar、AppHeader、ThemeSwitcher、LanguageSwitcher 等 Layout 组件 SHALL 位于 `apps/web/components/layout/` 目录下。`layout.tsx` 不再引入 AppLayout，由各页面按需引入。

#### Scenario: 组件目录结构
- **WHEN** 查看 `apps/web/components/layout/` 目录
- **THEN** 存在 `app-layout.tsx`、`app-sidebar.tsx`、`app-header.tsx`、`theme-switcher.tsx`、`language-switcher.tsx` 等 Layout 组件文件

#### Scenario: 全局 layout 不包含 AppLayout
- **WHEN** 查看 `apps/web/app/layout.tsx`
- **THEN** 不包含 AppLayout 组件的引入和渲染

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

## REMOVED Requirements

（无移除的 Requirements）
