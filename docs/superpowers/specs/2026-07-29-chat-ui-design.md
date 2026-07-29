---
comet_change: chat-ui
role: technical-design
canonical_spec: openspec
archived-with: 2026-07-29-chat-ui
status: final
---

# Chat UI 深度技术设计

## 架构

ChatPage 作为 AppLayout main 区域的子内容渲染。AppLayout 的 `<main>` 使用 `p-6`，chat 页面需要 full-bleed 布局——ChatPage 用负 margin 抵消 padding，不修改 AppLayout 影响其他页面。

```
AppLayout
└── SidebarInset
    └── main (p-6, chat 页面通过 -m-6 抵消)
        └── ChatPage (flex h-full)
            ├── SessionList (w-64 shrink-0, border-r)
            └── ChatMain (flex-1 flex-col)
                ├── MessageArea (flex-1 overflow-y-auto p-5)
                └── ChatInput (border-t p-4)
```

## 组件详细设计

### ChatPage (`components/chat/chat-page.tsx`)

页面容器，管理所有会话状态。

**状态：**
- `sessions: Session[]` — 初始化为 `mockSessions`
- `currentSessionId: string | null` — 当前活跃会话

**回调：**
- `handleSelectSession(id)` — 设置 currentSessionId
- `handleNewSession()` — 创建空会话并切换
- `handleDeleteSession(id)` — 移除会话，若删除当前会话则切换到第一个
- `handleSendMessage(text)` — 添加用户消息 + 触发模拟 AI 响应

**流式模拟实现：**
```typescript
const timerRef = useRef<ReturnType<typeof setTimeout>>();

// 清理定时器
useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

function streamResponse(session, fullText, toolCalls) {
  let charIdx = 0;
  function typeChar() {
    if (charIdx < fullText.length) {
      const chunk = Math.min(2, fullText.length - charIdx);
      // 直接更新 sessions state 中的 message content
      charIdx += chunk;
      timerRef.current = setTimeout(typeChar, 30);
    }
  }
  // 如有 toolCall：先 1.2s spinner → done → 0.4s 后开始流式
  if (toolCalls) {
    // step 1: push assistant msg with toolCalls[0].status='calling'
    // step 2: 1200ms 后 toolCall.status='done'
    // step 3: 400ms 后开始 typeChar
  } else {
    typeChar();
  }
}
```

### SessionList (`components/chat/session-list.tsx`)

**Props：** `sessions`, `currentSessionId`, `onSelect`, `onNew`, `onDelete`

**布局：**
- 顶部：标题 + 新建会话按钮（虚线边框、primary 色）
- 中间：会话列表（overflow-y-auto）
- 会话项：标题（单行截断）+ 时间，hover 显示删除按钮（×），active 背景高亮

**样式：** `w-64 bg-background border-r flex flex-col`

### MessageArea (`components/chat/message-area.tsx`)

**Props：** `messages: Message[]`

**布局：** `flex-1 overflow-y-auto p-5`

**自动滚动：**
```typescript
const bottomRef = useRef<HTMLDivElement>(null);
useEffect(() => {
  bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
}, [messages]);
```
消息列表底部放 `<div ref={bottomRef} />`。

**空状态：** 无消息时居中显示"开始新对话"提示。

### MessageBubble (`components/chat/message-bubble.tsx`)

**Props：** `message: Message`

**用户消息：**
- 外层：`flex justify-end`
- 气泡：`bg-primary text-primary-foreground rounded-xl rounded-br-sm max-w-[70%] px-3.5 py-2.5`
- 纯文本渲染（换行转 `<br>`）

**助手消息：**
- 外层：`flex justify-start`
- 气泡：`bg-background border rounded-xl rounded-bl-sm max-w-[70%] px-3.5 py-2.5`
- react-markdown 渲染内容

**Markdown 组件自定义：**
```typescript
const markdownComponents = {
  // 表格样式
  table: ({ children }) => <table className="border-collapse text-sm my-2 w-full">{children}</table>,
  th: ({ children }) => <th className="border px-2 py-1 bg-muted text-left">{children}</th>,
  td: ({ children }) => <td className="border px-2 py-1">{children}</td>,
  // 代码块
  code: ({ children, className }) => <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{children}</code>,
  // 引用块
  blockquote: ({ children }) => <blockquote className="border-l-3 border-muted-foreground/30 pl-3 text-muted-foreground my-2">{children}</blockquote>,
};
```

### ToolCallStatus (`components/chat/tool-call-status.tsx`)

**Props：** `toolCalls: ToolCall[]`

**调用中：**
- 黄色背景：`bg-yellow-50 border border-yellow-200 rounded-lg px-3.5 py-2`
- 内容：spinner（CSS animation rotate）+ display 文字

**完成：**
- 绿色背景：`bg-green-50 border border-green-200 rounded-lg px-3.5 py-2`
- 内容：✓ + summary

### ChatInput (`components/chat/chat-input.tsx`)

**Props：** `onSend: (text: string) => void`, `disabled?: boolean`

**textarea 自适应高度：**
```typescript
const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
  const el = e.target;
  el.style.height = 'auto';
  el.style.height = Math.min(Math.max(el.scrollHeight, 40), 120) + 'px';
};
```

**键盘事件：**
```typescript
const handleKeyDown = (e: React.KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
};
```

**发送按钮：** `disabled={disabled || !inputText.trim()}`

## 数据结构 (`config/mock-chat.ts`)

```typescript
export interface ToolCall {
  name: string;
  display: string;
  status: 'calling' | 'done';
  summary: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  time: string;
  toolCalls?: ToolCall[];
}

export interface Session {
  id: string;
  title: string;
  time: string;
  messages: Message[];
}
```

**mockGetAIResponse 函数：** 根据关键词匹配返回预设响应：
- 问候语（你好/hi/hello）→ 随机问候
- 退货/换货/售后 → 知识库检索 + 退货政策
- 订单/物流/快递 → 订单查询
- 商品/产品/手机 → 商品信息
- 其他 → 默认回复

**3 个预设会话：** 退货政策咨询、订单查询、商品咨询（与原型一致）

## 页面集成

### page.tsx 改造

```typescript
"use client";
import { useEffect } from "react";
import { useAuthStore } from "@/store/auth";
import { AppLayout } from "@/components/layout/app-layout";
import { ChatPage } from "@/components/chat/chat-page";

export default function Page() {
  const { initAuth, loading, isAuthenticated } = useAuthStore();

  useEffect(() => { initAuth(); }, [initAuth]);

  if (loading) return <AppLayout><div>加载中...</div></AppLayout>;
  if (!isAuthenticated) return null; // 路由守卫处理

  return (
    <AppLayout>
      <ChatPage />
    </AppLayout>
  );
}
```

ChatPage 根元素用 `-m-6 h-[calc(100%+3rem)]` 抵消 main 的 p-6。

### i18n 翻译键

```json
// zh-CN
{ "chat": { "sessionList": "会话列表", "newSession": "+ 新建会话", "placeholder": "输入消息，Enter 发送，Shift+Enter 换行...", "send": "发 送", "emptySession": "选择或创建一个会话开始对话" } }

// en-US
{ "chat": { "sessionList": "Sessions", "newSession": "+ New Chat", "placeholder": "Type a message, Enter to send, Shift+Enter for new line...", "send": "Send", "emptySession": "Select or create a session to start chatting" } }
```

## 测试策略

1. **单元测试**：`mockGetAIResponse` 关键词匹配（5 种场景）
2. **组件测试**：ChatInput Enter/Shift+Enter 行为、空消息禁用
3. **集成验证**：`turbo build` 通过、`vitest run` 通过
