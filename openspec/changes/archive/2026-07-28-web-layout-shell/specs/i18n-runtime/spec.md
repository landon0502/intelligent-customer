## ADDED Requirements

### Requirement: next-intl 运行时接入
系统 SHALL 使用 next-intl 作为国际化运行时，通过 `NextIntlClientProvider` 在 root layout 注入，所有客户端组件可通过 `useTranslations()` hook 获取翻译文本。

#### Scenario: useTranslations 获取翻译
- **WHEN** 客户端组件调用 `useTranslations('layout')`
- **THEN** 返回 `layout` 命名空间下的翻译函数，可正确解析翻译键

### Requirement: 翻译消息文件按 AI 客服系统组织
翻译消息文件 SHALL 按 AI 客服系统的业务领域组织，移除 LingDiary 遗留内容。至少包含 `common`、`layout`、`theme`、`language` 命名空间。

#### Scenario: zh-CN 翻译文件内容
- **WHEN** 查看 `apps/web/messages/zh-CN.json`
- **THEN** 包含 `common.appName`（"AI 客服系统"）、`layout` 下各菜单项翻译、`theme` 下主题切换翻译等，无 LingDiary 相关内容

#### Scenario: en-US 翻译文件内容
- **WHEN** 查看 `apps/web/messages/en-US.json`
- **THEN** 包含 `common.appName`（"AI Customer Service"）、`layout` 下各菜单项英文翻译、`theme` 下主题切换英文翻译等

### Requirement: 语言切换入口
Header 右侧 SHALL 展示语言切换入口，用户可切换界面语言。切换后 Layout 及所有使用 `useTranslations` 的文本即时更新。

#### Scenario: 切换到英文
- **WHEN** 用户点击语言切换入口选择"English"
- **THEN** Sidebar 菜单项、Header 标题等所有 Layout 文本切换为英文

#### Scenario: 切换回中文
- **WHEN** 用户点击语言切换入口选择"简体中文"
- **THEN** 所有 Layout 文本切换回中文

### Requirement: 语言偏好持久化
用户选择的语言 SHALL 持久化到 cookie，刷新页面后保持上次选择的语言。

#### Scenario: 刷新后语言保持
- **WHEN** 用户切换语言为英文后刷新页面
- **THEN** 页面仍以英文展示

### Requirement: 无 locale 路由前缀
语言切换 SHALL 不改变 URL 路径（不使用 `/[locale]` 前缀路由模式）。语言偏好仅通过 cookie 传递。

#### Scenario: 语言切换不改变 URL
- **WHEN** 用户在首页切换语言
- **THEN** URL 仍为 `/`，不变为 `/en/` 或 `/zh-CN/`

### Requirement: 语言切换通过 router.refresh 触发重渲染
语言切换 SHALL 通过设置 cookie 后调用 `router.refresh()` 触发 Server Component 重新渲染，从而加载新 locale 的 messages。

#### Scenario: 切换语言触发 refresh
- **WHEN** 用户选择新语言
- **THEN** 系统设置 `NEXT_LOCALE` cookie 为新 locale 值，并调用 `router.refresh()`，Server Component 重新读取 cookie 并加载对应 messages
