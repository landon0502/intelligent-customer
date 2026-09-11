"use client"

import { Fragment, type ReactNode } from "react"
import { useTranslations } from "next-intl"
import type { ChatStatus, UIMessage } from "ai"
import { isToolUIPart } from "ai"
import { Streamdown } from "streamdown"
import { ToolCallStatus } from "./tool-call-status"

interface MessageBubbleProps {
  message: UIMessage
  status: ChatStatus
}

/** assistant 消息是否已有可渲染内容（文本或工具调用） */
function hasRenderableContent(message: UIMessage): boolean {
  return message.parts.some((part) =>
    part.type === "text" ? part.text.trim().length > 0 : isToolUIPart(part)
  )
}

/** assistant 气泡外壳，等待态与正文态共用 */
function AssistantBubble({ children }: { children: ReactNode }) {
  return (
    <div className="flex justify-start">
      <div className="flex max-w-[70%] flex-col gap-2 rounded-xl rounded-bl-sm border bg-background px-3.5 py-2.5">
        {children}
      </div>
    </div>
  )
}

function TypingIndicator() {
  const t = useTranslations("chat")
  return (
    <span
      role="status"
      className="flex items-center gap-2 text-sm text-muted-foreground"
    >
      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted-foreground/40 border-t-transparent" />
      <span>{t("thinking")}</span>
    </span>
  )
}

/**
 * 等待 assistant 首字输出时的占位气泡。
 * useChat 在收到首个 chunk 前不会创建 assistant 消息（status=submitted），
 * 此时列表里没有可供 MessageBubble 渲染的消息，由 MessageArea 用它过渡。
 */
export function PendingBubble() {
  return (
    <AssistantBubble>
      <TypingIndicator />
    </AssistantBubble>
  )
}

export function MessageBubble({ message, status }: MessageBubbleProps) {
  const isUser = message.role === "user"

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] rounded-xl rounded-br-sm bg-primary px-3.5 py-2.5 text-primary-foreground">
          {message.parts
            .filter(
              (p): p is Extract<typeof p, { type: "text" }> => p.type === "text"
            )
            .map((p, i) => (
              <Fragment key={i}>
                {i > 0 && <br />}
                {p.text}
              </Fragment>
            ))}
        </div>
      </div>
    )
  }

  // assistant 消息已创建但首个 chunk 还没写入 parts 时，同样展示等待态
  const isAwaitingAnswer =
    (status === "submitted" || status === "streaming") &&
    !hasRenderableContent(message)

  return (
    <AssistantBubble>
      {isAwaitingAnswer ? (
        <TypingIndicator />
      ) : (
        message.parts.map((part, i) => {
          if (part.type === "text") {
            const textPart = part as Extract<typeof part, { type: "text" }>
            return (
              <Streamdown
                isAnimating={true}
                key={i}
                mode="streaming" // ← 关键：启用流式模式
                parseIncompleteMarkdown={true} // ← 关键：自动补全不完整的 Markdown
                controls={{ table: false, code: false }}
              >
                {textPart.text}
              </Streamdown>
            )
          }

          if (isToolUIPart(part)) {
            return <ToolCallStatus key={i} toolPart={part} />
          }

          return null
        })
      )}
    </AssistantBubble>
  )
}
