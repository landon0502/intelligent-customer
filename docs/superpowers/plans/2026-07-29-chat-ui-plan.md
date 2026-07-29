---
change: chat-ui
design-doc: docs/superpowers/specs/2026-07-29-chat-ui-design.md
base-ref: c9a20e15ed8531cb168198c1b97778219dc0a102
---

# Chat UI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 AppLayout 框架内实现完整的 Chat UI 页面，包含会话列表、消息展示、流式模拟响应和工具调用状态展示。

**Architecture:** ChatPage 作为 AppLayout main 区域的子内容渲染，通过负 margin 抵消父级 p-6 实现 full-bleed 布局。所有会话状态由 ChatPage 管理，子组件通过 props 接收数据和回调。流式响应通过 setTimeout 逐字模拟，工具调用通过状态机（calling → done → 流式文本）展示。

**Tech Stack:** React 19, Next.js 16, next-intl (i18n), zustand (auth), vitest + @testing-library/react (测试), react-markdown + remark-gfm (Markdown 渲染), lucide-react (图标)

## Global Constraints

- 使用 `next-intl` 的 `useTranslations` 处理所有用户可见文本，翻译键添加到 `apps/web/messages/zh-CN.json` 和 `apps/web/messages/en-US.json`
- 组件使用 `"use client"` 指令（Next.js 客户端组件）
- 样式使用 Tailwind CSS v4（项目已配置 `@tailwindcss/postcss`）
- 测试框架为 vitest + jsdom + @testing-library/react，配置在 `apps/web/vitest.config.ts`
- 路径别名 `@/` 映射到 `apps/web/`
- UI 组件来自 `@intelligent-customer/ui` 包（workspace 依赖）
- 不修改 AppLayout 组件本身，ChatPage 通过负 margin 抵消 padding

---

## File Structure

| 文件 | 职责 | 操作 |
|------|------|------|
| `apps/web/config/mock-chat.ts` | 数据类型定义 + mock 数据 + mockGetAIResponse 函数 | 创建 |
| `apps/web/components/chat/chat-page.tsx` | 页面容器，管理会话状态和流式响应 | 创建 |
| `apps/web/components/chat/session-list.tsx` | 会话列表侧栏 | 创建 |
| `apps/web/components/chat/message-area.tsx` | 消息展示区，自动滚动 | 创建 |
| `apps/web/components/chat/message-bubble.tsx` | 单条消息气泡，Markdown 渲染 | 创建 |
| `apps/web/components/chat/tool-call-status.tsx` | 工具调用状态展示 | 创建 |
| `apps/web/components/chat/chat-input.tsx` | 输入框，自适应高度 + 键盘事件 | 创建 |
| `apps/web/app/page.tsx` | 页面入口，替换欢迎信息为 ChatPage | 修改 |
| `apps/web/messages/zh-CN.json` | 中文翻译键 | 修改 |
| `apps/web/messages/en-US.json` | 英文翻译键 | 修改 |
| `apps/web/__tests__/mock-chat.test.ts` | mockGetAIResponse 单元测试 | 创建 |
| `apps/web/__tests__/chat-input.test.tsx` | ChatInput 组件测试 | 创建 |

---

### Task 1: 安装依赖 + 创建数据层

**Files:**
- Create: `apps/web/config/mock-chat.ts`
- Create: `apps/web/__tests__/mock-chat.test.ts`

**Interfaces:**
- Consumes: 无（首个任务）
- Produces: `ToolCall`, `Message`, `Session` 类型；`mockSessions` 常量；`mockGetAIResponse(text: string): { content: string; toolCalls?: ToolCall[] }` 函数

- [x] **Step 1: 安装 react-markdown 和 remark-gfm**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web add react-markdown remark-gfm
```

- [x] **Step 2: 创建 mock-chat.ts — 类型定义**

创建 `apps/web/config/mock-chat.ts`：

```typescript
export interface ToolCall {
  name: string;
  display: string;
  status: "calling" | "done";
  summary: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
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

- [x] **Step 3: 创建 mock-chat.ts — mockGetAIResponse 函数**

在 `apps/web/config/mock-chat.ts` 中追加：

```typescript
export function mockGetAIResponse(text: string): {
  content: string;
  toolCalls?: ToolCall[];
} {
  const lower = text.toLowerCase();

  if (/你好|hi|hello/.test(lower)) {
    const greetings = [
      "你好！我是智能客服助手，有什么可以帮您的吗？",
      "您好！欢迎咨询，请问有什么问题？",
      "Hi！很高兴为您服务，请告诉我您的需求。",
    ];
    return {
      content: greetings[Math.floor(Math.random() * greetings.length)],
    };
  }

  if (/退货|换货|售后/.test(lower)) {
    return {
      content:
        "根据我们的退货政策，商品在购买后 **7 天内** 可以无理由退货。\n\n退货流程：\n1. 在订单详情页点击「申请退货」\n2. 填写退货原因\n3. 等待审核通过\n4. 寄回商品\n5. 收到退款\n\n> 退货运费由买家承担，商品需保持原包装完好。",
      toolCalls: [
        {
          name: "search_knowledge_base",
          display: "搜索知识库：退货政策",
          status: "done",
          summary: "找到退货政策文档 3 篇",
        },
      ],
    };
  }

  if (/订单|物流|快递/.test(lower)) {
    return {
      content:
        "正在为您查询订单信息...\n\n| 订单号 | 状态 | 预计到达 |\n|--------|------|----------|\n| ORD-20240115 | 运输中 | 1月18日 |\n| ORD-20240110 | 已签收 | - |\n\n如需查看详细物流信息，请提供具体订单号。",
      toolCalls: [
        {
          name: "query_order",
          display: "查询订单状态",
          status: "done",
          summary: "查询到 2 条订单记录",
        },
      ],
    };
  }

  if (/商品|产品|手机/.test(lower)) {
    return {
      content:
        "为您推荐以下商品：\n\n**智能手机 Pro Max**\n- 价格：¥5,999\n- 存储：256GB\n- 屏幕：6.7 英寸 OLED\n\n**智能手表 S3**\n- 价格：¥1,299\n- 续航：7 天\n- 防水：IP68\n\n如需了解更多详情，请告诉我具体商品名称。",
      toolCalls: [
        {
          name: "search_products",
          display: "搜索商品信息",
          status: "done",
          summary: "找到 2 个相关商品",
        },
      ],
    };
  }

  return {
    content:
      "感谢您的咨询。我目前可以帮您处理以下问题：\n\n- 退货/换货/售后问题\n- 订单/物流查询\n- 商品信息咨询\n\n请描述您的具体需求，我会尽力为您解答。",
  };
}
```

- [x] **Step 4: 创建 mock-chat.ts — mockSessions 常量**

在 `apps/web/config/mock-chat.ts` 中追加：

```typescript
export const mockSessions: Session[] = [
  {
    id: "s1",
    title: "退货政策咨询",
    time: "2024-01-15 14:30",
    messages: [
      {
        id: "m1",
        role: "user",
        content: "你好，我想了解一下退货政策",
        time: "14:30",
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "根据我们的退货政策，商品在购买后 **7 天内** 可以无理由退货。\n\n退货流程：\n1. 在订单详情页点击「申请退货」\n2. 填写退货原因\n3. 等待审核通过\n4. 寄回商品\n5. 收到退款\n\n> 退货运费由买家承担，商品需保持原包装完好。",
        time: "14:30",
        toolCalls: [
          {
            name: "search_knowledge_base",
            display: "搜索知识库：退货政策",
            status: "done",
            summary: "找到退货政策文档 3 篇",
          },
        ],
      },
    ],
  },
  {
    id: "s2",
    title: "订单查询",
    time: "2024-01-15 10:15",
    messages: [
      {
        id: "m3",
        role: "user",
        content: "帮我查一下最近的订单",
        time: "10:15",
      },
      {
        id: "m4",
        role: "assistant",
        content:
          "正在为您查询订单信息...\n\n| 订单号 | 状态 | 预计到达 |\n|--------|------|----------|\n| ORD-20240115 | 运输中 | 1月18日 |\n| ORD-20240110 | 已签收 | - |\n\n如需查看详细物流信息，请提供具体订单号。",
        time: "10:15",
        toolCalls: [
          {
            name: "query_order",
            display: "查询订单状态",
            status: "done",
            summary: "查询到 2 条订单记录",
          },
        ],
      },
    ],
  },
  {
    id: "s3",
    title: "商品咨询",
    time: "2024-01-14 16:00",
    messages: [
      {
        id: "m5",
        role: "user",
        content: "有什么手机推荐吗？",
        time: "16:00",
      },
      {
        id: "m6",
        role: "assistant",
        content:
          "为您推荐以下商品：\n\n**智能手机 Pro Max**\n- 价格：¥5,999\n- 存储：256GB\n- 屏幕：6.7 英寸 OLED\n\n**智能手表 S3**\n- 价格：¥1,299\n- 续航：7 天\n- 防水：IP68\n\n如需了解更多详情，请告诉我具体商品名称。",
        time: "16:00",
        toolCalls: [
          {
            name: "search_products",
            display: "搜索商品信息",
            status: "done",
            summary: "找到 2 个相关商品",
          },
        ],
      },
    ],
  },
];
```

- [x] **Step 5: 编写 mockGetAIResponse 单元测试**

创建 `apps/web/__tests__/mock-chat.test.ts`：

```typescript
import { describe, it, expect } from "vitest";
import { mockGetAIResponse } from "@/config/mock-chat";

describe("mockGetAIResponse", () => {
  it("问候语关键词返回问候响应", () => {
    const result = mockGetAIResponse("你好");
    expect(result.content).toBeTruthy();
    expect(result.toolCalls).toBeUndefined();
  });

  it("英文 hi 也匹配问候", () => {
    const result = mockGetAIResponse("hi");
    expect(result.content).toBeTruthy();
    expect(result.toolCalls).toBeUndefined();
  });

  it("退货关键词返回退货政策 + toolCall", () => {
    const result = mockGetAIResponse("我想退货");
    expect(result.content).toContain("退货");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0].name).toBe("search_knowledge_base");
  });

  it("订单关键词返回订单查询 + toolCall", () => {
    const result = mockGetAIResponse("查一下我的订单");
    expect(result.content).toContain("订单");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0].name).toBe("query_order");
  });

  it("商品关键词返回商品推荐 + toolCall", () => {
    const result = mockGetAIResponse("推荐手机");
    expect(result.content).toContain("商品");
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0].name).toBe("search_products");
  });

  it("无匹配关键词返回默认回复", () => {
    const result = mockGetAIResponse("随便聊聊");
    expect(result.content).toContain("咨询");
    expect(result.toolCalls).toBeUndefined();
  });
});
```

- [x] **Step 6: 运行测试确认通过**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web test -- --run __tests__/mock-chat.test.ts
```

Expected: 6 tests PASS

- [x] **Step 7: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/config/mock-chat.ts apps/web/__tests__/mock-chat.test.ts && git commit -m "feat(chat): add mock data layer with types, sessions, and AI response function"
```

---

### Task 2: ChatInput 输入框组件

**Files:**
- Create: `apps/web/components/chat/chat-input.tsx`
- Create: `apps/web/__tests__/chat-input.test.tsx`

**Interfaces:**
- Consumes: 无
- Produces: `ChatInput` 组件，props: `onSend: (text: string) => void`, `disabled?: boolean`

- [x] **Step 1: 编写 ChatInput 组件测试**

创建 `apps/web/__tests__/chat-input.test.tsx`：

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatInput } from "@/components/chat/chat-input";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = {
      placeholder: "Type a message, Enter to send, Shift+Enter for new line...",
      send: "Send",
    };
    return map[key] ?? key;
  },
}));

describe("ChatInput", () => {
  it("Enter 键发送消息", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/Enter/);
    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSend).toHaveBeenCalledWith("hello");
  });

  it("Shift+Enter 不发送消息（换行）", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/Enter/);
    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("空消息禁用发送按钮", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });

  it("disabled prop 禁用输入和按钮", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} disabled />);
    const textarea = screen.getByPlaceholderText(/Enter/);
    const button = screen.getByRole("button");
    expect(textarea).toBeDisabled();
    expect(button).toBeDisabled();
  });

  it("发送后清空输入框", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);
    const textarea = screen.getByPlaceholderText(/Enter/) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "hello" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(textarea.value).toBe("");
  });
});
```

- [x] **Step 2: 运行测试确认失败**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web test -- --run __tests__/chat-input.test.tsx
```

Expected: FAIL — module not found

- [x] **Step 3: 实现 ChatInput 组件**

创建 `apps/web/components/chat/chat-input.tsx`：

```typescript
"use client";

import { useState, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const t = useTranslations("chat");
  const [inputText, setInputText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInputText(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height =
        Math.min(Math.max(el.scrollHeight, 40), 120) + "px";
    },
    []
  );

  const handleSend = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "40px";
    }
  }, [inputText, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className="border-t p-4">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={inputText}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={t("placeholder")}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-lg border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
          style={{ height: "40px" }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !inputText.trim()}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none"
          aria-label={t("send")}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
```

- [x] **Step 4: 运行测试确认通过**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web test -- --run __tests__/chat-input.test.tsx
```

Expected: 5 tests PASS

- [x] **Step 5: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/components/chat/chat-input.tsx apps/web/__tests__/chat-input.test.tsx && git commit -m "feat(chat): add ChatInput component with auto-resize and keyboard handling"
```

---

### Task 3: ToolCallStatus 工具调用状态组件

**Files:**
- Create: `apps/web/components/chat/tool-call-status.tsx`

**Interfaces:**
- Consumes: `ToolCall` 类型（来自 Task 1 的 `apps/web/config/mock-chat.ts`）
- Produces: `ToolCallStatus` 组件，props: `toolCalls: ToolCall[]`

- [x] **Step 1: 实现 ToolCallStatus 组件**

创建 `apps/web/components/chat/tool-call-status.tsx`：

```typescript
"use client";

import type { ToolCall } from "@/config/mock-chat";

interface ToolCallStatusProps {
  toolCalls: ToolCall[];
}

export function ToolCallStatus({ toolCalls }: ToolCallStatusProps) {
  return (
    <div className="space-y-1.5 mt-2">
      {toolCalls.map((tc, i) =>
        tc.status === "calling" ? (
          <div
            key={`${tc.name}-${i}`}
            className="bg-yellow-50 border border-yellow-200 rounded-lg px-3.5 py-2 flex items-center gap-2 text-sm"
          >
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
            <span>{tc.display}</span>
          </div>
        ) : (
          <div
            key={`${tc.name}-${i}`}
            className="bg-green-50 border border-green-200 rounded-lg px-3.5 py-2 flex items-center gap-2 text-sm"
          >
            <span className="text-green-600">&#10003;</span>
            <span>{tc.summary}</span>
          </div>
        )
      )}
    </div>
  );
}
```

- [x] **Step 2: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/components/chat/tool-call-status.tsx && git commit -m "feat(chat): add ToolCallStatus component with calling/done states"
```

---

### Task 4: MessageBubble 消息气泡组件

**Files:**
- Create: `apps/web/components/chat/message-bubble.tsx`

**Interfaces:**
- Consumes: `Message` 类型（来自 Task 1）；`ToolCallStatus` 组件（来自 Task 3）
- Produces: `MessageBubble` 组件，props: `message: Message`

- [x] **Step 1: 实现 MessageBubble 组件**

创建 `apps/web/components/chat/message-bubble.tsx`：

```typescript
"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/config/mock-chat";
import { ToolCallStatus } from "./tool-call-status";

const markdownComponents = {
  table: ({ children }: { children?: React.ReactNode }) => (
    <table className="border-collapse text-sm my-2 w-full">{children}</table>
  ),
  th: ({ children }: { children?: React.ReactNode }) => (
    <th className="border px-2 py-1 bg-muted text-left">{children}</th>
  ),
  td: ({ children }: { children?: React.ReactNode }) => (
    <td className="border px-2 py-1">{children}</td>
  ),
  code: ({
    children,
    className,
  }: {
    children?: React.ReactNode;
    className?: string;
  }) => (
    <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{children}</code>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className="border-l-3 border-muted-foreground/30 pl-3 text-muted-foreground my-2">
      {children}
    </blockquote>
  ),
};

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="bg-primary text-primary-foreground rounded-xl rounded-br-sm max-w-[70%] px-3.5 py-2.5">
          {message.content.split("\n").map((line, i) => (
            <React.Fragment key={i}>
              {i > 0 && <br />}
              {line}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="bg-background border rounded-xl rounded-bl-sm max-w-[70%] px-3.5 py-2.5">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {message.content}
        </ReactMarkdown>
        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallStatus toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  );
}
```

- [x] **Step 2: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/components/chat/message-bubble.tsx && git commit -m "feat(chat): add MessageBubble with Markdown rendering and tool call display"
```

---

### Task 5: MessageArea 消息展示区组件

**Files:**
- Create: `apps/web/components/chat/message-area.tsx`

**Interfaces:**
- Consumes: `Message` 类型（来自 Task 1）；`MessageBubble` 组件（来自 Task 4）
- Produces: `MessageArea` 组件，props: `messages: Message[]`

- [x] **Step 1: 实现 MessageArea 组件**

创建 `apps/web/components/chat/message-area.tsx`：

```typescript
"use client";

import { useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import type { Message } from "@/config/mock-chat";
import { MessageBubble } from "./message-bubble";

interface MessageAreaProps {
  messages: Message[];
}

export function MessageArea({ messages }: MessageAreaProps) {
  const t = useTranslations("chat");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-muted-foreground">{t("emptySession")}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-5">
      <div className="space-y-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
```

- [x] **Step 2: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/components/chat/message-area.tsx && git commit -m "feat(chat): add MessageArea with auto-scroll and empty state"
```

---

### Task 6: SessionList 会话列表侧栏组件

**Files:**
- Create: `apps/web/components/chat/session-list.tsx`

**Interfaces:**
- Consumes: `Session` 类型（来自 Task 1）
- Produces: `SessionList` 组件，props: `sessions: Session[]`, `currentSessionId: string | null`, `onSelect: (id: string) => void`, `onNew: () => void`, `onDelete: (id: string) => void`

- [x] **Step 1: 实现 SessionList 组件**

创建 `apps/web/components/chat/session-list.tsx`：

```typescript
"use client";

import { useTranslations } from "next-intl";
import { Plus, X } from "lucide-react";
import type { Session } from "@/config/mock-chat";

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onNew,
  onDelete,
}: SessionListProps) {
  const t = useTranslations("chat");

  return (
    <div className="w-64 bg-background border-r flex flex-col">
      <div className="p-3 border-b flex items-center justify-between">
        <h2 className="text-sm font-medium">{t("sessionList")}</h2>
        <button
          onClick={onNew}
          className="inline-flex items-center gap-1 text-xs text-primary border border-dashed border-primary rounded-md px-2 py-1 hover:bg-primary/5"
        >
          <Plus className="h-3 w-3" />
          {t("newSession")}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => onSelect(session.id)}
            className={`group px-3 py-2.5 cursor-pointer border-b last:border-b-0 ${
              session.id === currentSessionId
                ? "bg-primary/5 border-l-2 border-l-primary"
                : "hover:bg-muted/50"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm truncate flex-1">{session.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(session.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground p-0.5"
                aria-label="Delete session"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <span className="text-xs text-muted-foreground">{session.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [x] **Step 2: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/components/chat/session-list.tsx && git commit -m "feat(chat): add SessionList with new/delete/select interactions"
```

---

### Task 7: ChatPage 页面容器 + 流式模拟响应

**Files:**
- Create: `apps/web/components/chat/chat-page.tsx`

**Interfaces:**
- Consumes: `Session`, `Message`, `ToolCall` 类型 + `mockSessions`, `mockGetAIResponse`（来自 Task 1）；`SessionList`（Task 6）；`MessageArea`（Task 5）；`ChatInput`（Task 2）
- Produces: `ChatPage` 组件（无 props，自包含状态管理）

- [x] **Step 1: 实现 ChatPage 组件**

创建 `apps/web/components/chat/chat-page.tsx`：

```typescript
"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Session, Message, ToolCall } from "@/config/mock-chat";
import { mockSessions, mockGetAIResponse } from "@/config/mock-chat";
import { SessionList } from "./session-list";
import { MessageArea } from "./message-area";
import { ChatInput } from "./chat-input";

let nextId = 100;
function genId() {
  return `id-${nextId++}`;
}

export function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>(mockSessions);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    mockSessions[0]?.id ?? null
  );
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    []
  );

  const currentSession = sessions.find((s) => s.id === currentSessionId) ?? null;

  const handleSelectSession = useCallback((id: string) => {
    setCurrentSessionId(id);
  }, []);

  const handleNewSession = useCallback(() => {
    const newSession: Session = {
      id: genId(),
      title: "新会话",
      time: new Date().toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }),
      messages: [],
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
  }, []);

  const handleDeleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (id === currentSessionId) {
          setCurrentSessionId(next[0]?.id ?? null);
        }
        return next;
      });
    },
    [currentSessionId]
  );

  const handleSendMessage = useCallback(
    (text: string) => {
      if (!currentSessionId) return;

      const userMsg: Message = {
        id: genId(),
        role: "user",
        content: text,
        time: new Date().toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };

      const response = mockGetAIResponse(text);
      const assistantId = genId();

      // Step 1: add user message + assistant message (with toolCalls in calling state if any)
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== currentSessionId) return s;
          const toolCalls: ToolCall[] | undefined = response.toolCalls
            ? response.toolCalls.map((tc) => ({ ...tc, status: "calling" as const }))
            : undefined;
          const assistantMsg: Message = {
            id: assistantId,
            role: "assistant",
            content: "",
            time: new Date().toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
            }),
            toolCalls,
          };
          return { ...s, messages: [...s.messages, userMsg, assistantMsg] };
        })
      );

      // Step 2: if toolCalls, show spinner for 1.2s then mark done
      if (response.toolCalls) {
        timerRef.current = setTimeout(() => {
          setSessions((prev) =>
            prev.map((s) => {
              if (s.id !== currentSessionId) return s;
              return {
                ...s,
                messages: s.messages.map((m) => {
                  if (m.id !== assistantId) return m;
                  return {
                    ...m,
                    toolCalls: response.toolCalls!.map((tc) => ({
                      ...tc,
                      status: "done" as const,
                    })),
                  };
                }),
              };
            })
          );

          // Step 3: after 0.4s, start streaming text
          timerRef.current = setTimeout(() => {
            streamResponse(response.content);
          }, 400);
        }, 1200);
      } else {
        streamResponse(response.content);
      }

      function streamResponse(fullText: string) {
        let charIdx = 0;
        function typeChar() {
          if (charIdx < fullText.length) {
            const chunk = Math.min(2, fullText.length - charIdx);
            const nextContent = fullText.slice(0, charIdx + chunk);
            charIdx += chunk;
            setSessions((prev) =>
              prev.map((s) => {
                if (s.id !== currentSessionId) return s;
                return {
                  ...s,
                  messages: s.messages.map((m) => {
                    if (m.id !== assistantId) return m;
                    return { ...m, content: nextContent };
                  }),
                };
              })
            );
            timerRef.current = setTimeout(typeChar, 30);
          }
        }
        typeChar();
      }
    },
    [currentSessionId]
  );

  return (
    <div className="flex h-full -m-6" style={{ height: "calc(100% + 3rem)" }}>
      <SessionList
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
      />
      <div className="flex-1 flex flex-col">
        {currentSession ? (
          <>
            <MessageArea messages={currentSession.messages} />
            <ChatInput onSend={handleSendMessage} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">选择或创建一个会话开始对话</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [x] **Step 2: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/components/chat/chat-page.tsx && git commit -m "feat(chat): add ChatPage with session management and streaming simulation"
```

---

### Task 8: 页面集成 + i18n 翻译键

**Files:**
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/messages/zh-CN.json`
- Modify: `apps/web/messages/en-US.json`

**Interfaces:**
- Consumes: `ChatPage` 组件（来自 Task 7）；`useAuthStore`（现有）；`AppLayout`（现有）

- [x] **Step 1: 添加 i18n 翻译键到 zh-CN.json**

在 `apps/web/messages/zh-CN.json` 中，在 `"language"` 块之后追加 `"chat"` 键：

```json
{
  "common": {
    "appName": "AI 客服系统",
    "tagline": "智能客服，贴心服务",
    "loading": "加载中...",
    "logout": "退出登录",
    "settings": "系统设置",
    "roleAdmin": "管理员",
    "roleUser": "普通用户"
  },
  "layout": {
    "menuChat": "智能对话",
    "menuGroupManagement": "管理",
    "menuKnowledge": "知识库管理",
    "menuUsers": "用户管理",
    "menuConfig": "系统配置",
    "menuTools": "工具配置"
  },
  "theme": {
    "toggle": "切换主题",
    "light": "浅色",
    "dark": "深色",
    "system": "跟随系统"
  },
  "language": {
    "zhCN": "简体中文",
    "enUS": "English",
    "switch": "语言切换"
  },
  "chat": {
    "sessionList": "会话列表",
    "newSession": "+ 新建会话",
    "placeholder": "输入消息，Enter 发送，Shift+Enter 换行...",
    "send": "发送",
    "emptySession": "选择或创建一个会话开始对话"
  }
}
```

- [x] **Step 2: 添加 i18n 翻译键到 en-US.json**

在 `apps/web/messages/en-US.json` 中，在 `"language"` 块之后追加 `"chat"` 键：

```json
{
  "common": {
    "appName": "AI Customer Service",
    "tagline": "Smart Service, Thoughtful Care",
    "loading": "Loading...",
    "logout": "Log Out",
    "settings": "Settings",
    "roleAdmin": "Admin",
    "roleUser": "User"
  },
  "layout": {
    "menuChat": "Smart Chat",
    "menuGroupManagement": "Management",
    "menuKnowledge": "Knowledge Base",
    "menuUsers": "User Management",
    "menuConfig": "System Config",
    "menuTools": "Tool Config"
  },
  "theme": {
    "toggle": "Toggle Theme",
    "light": "Light",
    "dark": "Dark",
    "system": "System"
  },
  "language": {
    "zhCN": "简体中文",
    "enUS": "English",
    "switch": "Switch Language"
  },
  "chat": {
    "sessionList": "Sessions",
    "newSession": "+ New Chat",
    "placeholder": "Type a message, Enter to send, Shift+Enter for new line...",
    "send": "Send",
    "emptySession": "Select or create a session to start chatting"
  }
}
```

- [x] **Step 3: 改造 page.tsx**

替换 `apps/web/app/page.tsx` 的内容为：

```typescript
"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import { AppLayout } from "@/components/layout/app-layout";
import { ChatPage } from "@/components/chat/chat-page";

export default function Page() {
  const { initAuth, loading } = useAuthStore();
  const t = useTranslations("common");

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">{t("loading")}</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <ChatPage />
    </AppLayout>
  );
}
```

- [x] **Step 4: 提交**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && git add apps/web/app/page.tsx apps/web/messages/zh-CN.json apps/web/messages/en-US.json && git commit -m "feat(chat): integrate ChatPage into home route with i18n support"
```

---

### Task 9: 构建验证

**Files:**
- 无新文件

**Interfaces:**
- Consumes: 所有前序任务的产物

- [ ] **Step 1: 运行 vitest 全量测试**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web test -- --run
```

Expected: 所有测试 PASS

- [ ] **Step 2: 运行 Next.js 构建**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web build
```

Expected: 构建成功，无类型错误

- [ ] **Step 3: 运行 typecheck**

```bash
cd /Users/superhuan/Documents/project/intelligent-customer && pnpm --filter web typecheck
```

Expected: 无类型错误

- [ ] **Step 4: 提交（如有修复）**

仅在修复了构建/测试问题时提交。如果全部通过则跳过此步骤。
