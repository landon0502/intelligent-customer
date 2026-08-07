"use client"

import { Fragment } from "react"
import type { UIMessage } from "ai"
import { Streamdown } from "streamdown"
import { ToolCallStatus } from "./tool-call-status"

interface MessageBubbleProps {
  message: UIMessage
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
            return (
              <Streamdown isAnimating={true} key={i}>
                {textPart.text}
              </Streamdown>
            )
          }

          if (part.type.startsWith("tool-")) {
            const toolPart = part as {
              type: string
              toolCallId: string
              toolName: string
              state: "call" | "partial-call" | "result" | "output-error"
              args?: unknown
              result?: unknown
            }
            return <ToolCallStatus key={i} toolPart={toolPart} />
          }

          return null
        })}
      </div>
    </div>
  )
}
