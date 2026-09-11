"use client"

import { useRef, useEffect } from "react"
import { useTranslations } from "next-intl"
import type { ChatStatus, UIMessage } from "ai"
import { MessageBubble, PendingBubble } from "./message-bubble"

interface MessageAreaProps {
  messages: UIMessage[]
  status: ChatStatus
}

export function MessageArea({ messages, status }: MessageAreaProps) {
  const t = useTranslations("chat")
  const bottomRef = useRef<HTMLDivElement>(null)

  // status=submitted 期间后端还没吐出任何 chunk，assistant 消息尚未创建，
  // 需要额外渲染占位气泡；消息一旦存在就交给 MessageBubble 自行判断等待态。
  const needsPendingBubble =
    (status === "submitted" || status === "streaming") &&
    messages[messages.length - 1]?.role !== "assistant"

  useEffect(() => {
    bottomRef.current?.scrollIntoView()
  }, [messages, needsPendingBubble])

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground">{t("emptySession")}</p>
      </div>
    )
  }

  return (
    <div className="relative flex-1">
      <div className="absolute top-0 right-0 bottom-0 left-0 overflow-y-auto p-5">
        <div className="space-y-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} status={status} />
          ))}
          {needsPendingBubble && <PendingBubble />}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  )
}
