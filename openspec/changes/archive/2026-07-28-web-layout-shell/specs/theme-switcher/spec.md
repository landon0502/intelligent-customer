## ADDED Requirements

### Requirement: Header 主题切换 UI 入口
Header 右侧 SHALL 展示主题切换入口，提供亮色、暗色、跟随系统三个选项。当前激活的主题应有视觉标识。

#### Scenario: 切换到暗色模式
- **WHEN** 用户点击主题切换入口选择"深色"
- **THEN** 整个 Layout（Sidebar、Header、Content）切换为暗色配色，html 元素添加 `dark` class

#### Scenario: 切换到亮色模式
- **WHEN** 用户点击主题切换入口选择"浅色"
- **THEN** 整个 Layout 切换为亮色配色，html 元素移除 `dark` class

#### Scenario: 切换到跟随系统
- **WHEN** 用户点击主题切换入口选择"跟随系统"
- **THEN** Layout 根据操作系统当前配色方案自动切换

### Requirement: 主题切换图标
主题切换入口 SHALL 使用图标（太阳/月亮）直观表示当前主题状态，点击展开下拉选择。

#### Scenario: 暗色模式下图标
- **WHEN** 当前主题为暗色
- **THEN** 主题切换入口显示太阳图标

#### Scenario: 亮色模式下图标
- **WHEN** 当前主题为亮色
- **THEN** 主题切换入口显示月亮图标

### Requirement: 主题切换标签国际化
主题切换下拉菜单中的选项标签 SHALL 使用 i18n 翻译。

#### Scenario: 中文环境主题标签
- **WHEN** 当前语言为中文
- **THEN** 三个选项显示"浅色"、"深色"、"跟随系统"

#### Scenario: 英文环境主题标签
- **WHEN** 当前语言为英文
- **THEN** 三个选项显示"Light"、"Dark"、"System"
