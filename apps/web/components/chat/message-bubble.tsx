"use client"

import { Fragment } from "react"
import type { UIMessage } from "ai"
import { isToolUIPart } from "ai"
import { Streamdown } from "streamdown"

interface MessageBubbleProps {
  message: UIMessage
}

/**
 * 内联渲染工具调用 part（临时方案，Task 6 将适配 ToolCallStatus 组件）
 */
function InlineToolPart({
  part,
}: {
  part: Parameters<typeof isToolUIPart>[0] & { type: string }
}) {
  // 提取工具名：type 格式为 "tool-{name}" 或 "dynamic-tool"
  const toolName = part.type.startsWith("tool-")
    ? part.type.slice(5)
    : "dynamic-tool"

  // 从 part 中安全提取 state
  const state = "state" in part ? (part as { state: string }).state : "unknown"

  const isCalling = state === "input-streaming" || state === "input-available"
  const isDone = state === "output-available"
  const isError = state === "output-error"

  if (isCalling) {
    return (
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3.5 py-2 text-sm">
        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
        <span className="text-black">调用工具: {toolName}</span>
      </div>
    )
  }

  if (isError) {
    const errorText =
      "errorText" in part
        ? String((part as { errorText: string }).errorText)
        : "未知错误"
    return (
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2 text-sm">
        <span className="text-red-600">✗</span>
        <span className="text-black">
          工具 {toolName} 执行失败: {errorText}
        </span>
      </div>
    )
  }

  if (isDone) {
    const output =
      "output" in part ? (part as { output: unknown }).output : null
    const summary = output ? String(output) : `工具 ${toolName} 执行完成`
    return (
      <div className="mt-2 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3.5 py-2 text-sm">
        <span className="text-green-600">&#10003;</span>
        <span className="text-black">{summary}</span>
      </div>
    )
  }

  // 其他状态（approval 等）暂不处理
  return null
}

export function MessageBubble({ message }: MessageBubbleProps) {
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

  return (
    <div className="flex justify-start">
      <div className="max-w-[70%] rounded-xl rounded-bl-sm border bg-background px-3.5 py-2.5">
        {message.parts.map((part, i) => {
          if (part.type === "text") {
            const textPart = part as Extract<typeof part, { type: "text" }>
            return <Streamdown key={i}>{textPart.text}</Streamdown>
          }

          if (isToolUIPart(part)) {
            return (
              <InlineToolPart
                key={i}
                part={
                  part as Parameters<typeof isToolUIPart>[0] & { type: string }
                }
              />
            )
          }

          return null
        })}
      </div>
    </div>
  )
}
